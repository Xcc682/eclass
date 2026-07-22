import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.debate import DebateMessage, DebatePracticeRecord, DebateTopic
from app.models.domain import GeneratedReport
from app.models.user import User
from app.security import get_current_user
from app.services.ai_service import ai_service, validate_debate_feedback, validate_topics

router = APIRouter(prefix="/api/v1/debates", tags=["思政辩论"])

# 4-stage debate: opening(1 round) → cross_exam(1 round) → rebuttal(1 round) → closing(1 round)
STAGE_ORDER = ["opening", "cross_exam", "rebuttal", "closing"]
STAGE_MAX_ROUNDS = {"opening": 1, "cross_exam": 1, "rebuttal": 1, "closing": 1}

# Transition messages keyed by the PREVIOUS stage (the one user just completed)
STAGE_TRANSITIONS = {
    "opening": "立论阶段完成！接下来进入【质询】环节——针对AI对手的立论提出1个尖锐问题。",
    "cross_exam": "质询阶段完成！接下来进入【驳论】环节——直接指出AI论证中的逻辑漏洞。",
    "rebuttal": "驳论阶段完成！接下来进入【总结】环节——做一段有感染力的总结陈词。",
    "closing": "辩论全部4个阶段已完成！点击下方按钮生成AI评估报告。",
}


class StartRequest(BaseModel):
    topic_id: str
    stance: str = Field(pattern=r"^(pro|con)$")


class ArgumentRequest(BaseModel):
    argument: str = Field(min_length=1, max_length=3000)


def topic_payload(topic: DebateTopic) -> dict:
    return {"id": topic.id, "title": topic.title, "category": topic.category,
            "difficulty": topic.difficulty, "context": topic.context,
            "pro_hint": topic.pro_hint, "con_hint": topic.con_hint}


def owned(db: Session, session_id: str, user: User) -> DebatePracticeRecord:
    record = db.get(DebatePracticeRecord, session_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="辩论会话不存在")
    return record


def next_stage(current: str) -> str:
    """Return the next stage after the given one."""
    try:
        idx = STAGE_ORDER.index(current)
        return STAGE_ORDER[idx + 1] if idx + 1 < len(STAGE_ORDER) else "finished"
    except ValueError:
        return current


@router.get("/topics")
def get_topics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    topics = db.scalars(select(DebateTopic).where(
        or_(DebateTopic.status == "published", DebateTopic.owner_id == user.id)
    ).order_by(DebateTopic.created_at.desc())).all()
    return {"code": 0, "data": [topic_payload(topic) for topic in topics]}


@router.post("/topics/generate")
async def generate_topics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        generated = validate_topics(await ai_service.debate_generate_topics())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    rows = []
    for item in generated:
        topic = DebateTopic(title=item["title"], category=item["category"],
                            difficulty=item["difficulty"], context=item["context"],
                            pro_hint=item["pro_hint"], con_hint=item["con_hint"],
                            is_ai_generated=True, owner_id=user.id,
                            status="published" if user.role in {"teacher", "admin"} else "private")
        db.add(topic)
        db.flush()
        rows.append(topic_payload(topic))
    return {"code": 0, "data": rows}


@router.post("/practice/start")
async def start_debate(data: StartRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    topic = db.get(DebateTopic, data.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="辩题不存在")
    if topic.status != "published" and topic.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权使用该辩题")

    record = DebatePracticeRecord(user_id=user.id, topic_id=topic.id,
                                   stance=data.stance, status="in_progress",
                                   current_stage="opening")
    topic.usage_count += 1
    db.add(record)
    db.flush()

    # AI generates the opening argument (real opening, not hint text)
    try:
        opening = await ai_service.debate_open(topic.title, data.stance)
    except Exception:
        opening = topic.con_hint if data.stance == "pro" else topic.pro_hint
        if not opening:
            opening = "请先陈述你的核心观点。"

    db.add(DebateMessage(record_id=record.id, stage="opening", role="ai",
                          content=opening, round_number=0))

    stance_label = "正方" if data.stance == "pro" else "反方"
    return {"code": 0, "data": {
        "id": record.id,
        "first_argument": opening,
        "stage": "opening",
        "stage_label": "立论",
        "stance": data.stance,
        "stance_label": stance_label,
        "topic": topic_payload(topic),
    }}


@router.post("/practice/{session_id}/argue")
async def submit_argument(session_id: str, data: ArgumentRequest,
                          user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned(db, session_id, user)
    if record.status != "in_progress":
        raise HTTPException(status_code=409, detail="辩论已结束")

    messages = db.scalars(select(DebateMessage).where(
        DebateMessage.record_id == record.id
    ).order_by(DebateMessage.created_at)).all()

    topic = db.get(DebateTopic, record.topic_id)
    current_stage = record.current_stage

    # Count user messages in this stage
    stage_user_count = sum(1 for m in messages if m.role == "user" and m.stage == current_stage)
    max_in_stage = STAGE_MAX_ROUNDS.get(current_stage, 1)

    # Add user message
    user_message = DebateMessage(
        record_id=record.id, stage=current_stage, role="user",
        content=data.argument, round_number=len(messages) + 1
    )
    db.add(user_message)

    # Build conversation history for AI
    conversation = [{"role": m.role, "content": m.content,
                      "stance": record.stance if m.role == "user"
                      else ("con" if record.stance == "pro" else "pro")}
                     for m in messages]

    # AI responds with stage-appropriate behavior
    try:
        answer = await ai_service.debate_argue(
            topic.title, record.stance, data.argument, conversation, stage=current_stage
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc

    db.add(DebateMessage(record_id=record.id, stage=current_stage, role="ai",
                          content=answer, round_number=len(messages) + 1))

    # Check if stage should advance
    stage_complete = (stage_user_count + 1) >= max_in_stage
    old_stage = current_stage
    phase_transition = ""

    if stage_complete:
        new_stage = next_stage(current_stage)
        record.current_stage = new_stage
        phase_transition = STAGE_TRANSITIONS.get(old_stage, "")
        if new_stage == "finished":
            record.status = "completed"
    else:
        new_stage = current_stage

    record.total_rounds = len(messages) + 1

    return {"code": 0, "data": {
        "argument": answer,
        "stage": old_stage,
        "next_stage": new_stage,
        "stage_complete": stage_complete,
        "phase_transition": phase_transition,
        "is_finished": new_stage == "finished",
    }}


@router.post("/practice/{session_id}/end")
async def end_debate(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned(db, session_id, user)
    if record.feedback_json:
        return {"code": 0, "data": json.loads(record.feedback_json)}

    messages = db.scalars(select(DebateMessage).where(
        DebateMessage.record_id == record.id
    ).order_by(DebateMessage.created_at)).all()

    # Require at least 4 user messages (one per stage)
    if sum(1 for m in messages if m.role == "user") < 4:
        completed_stages = set(m.stage for m in messages if m.role == "user")
        missing = [s for s in STAGE_ORDER if s not in completed_stages]
        raise HTTPException(status_code=400,
            detail=f"请在完成全部4个阶段后生成评估。还缺少：{'、'.join(missing)}")

    topic = db.get(DebateTopic, record.topic_id)
    conversation = [{"role": m.role, "content": m.content,
                      "stance": record.stance if m.role == "user"
                      else ("con" if record.stance == "pro" else "pro")}
                     for m in messages]

    try:
        feedback = validate_debate_feedback(
            await ai_service.debate_feedback(topic.title, conversation, user_stance=record.stance)
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc

    score = int(feedback.get("overall_score", 0))
    record.status = "completed"
    record.completed_at = datetime.utcnow()
    record.overall_score = score
    record.feedback_json = json.dumps(feedback, ensure_ascii=False)
    user.total_points += max(score // 10, 1)
    db.add(GeneratedReport(user_id=user.id, report_type="debate", title=topic.title,
                            score=score, content_json=record.feedback_json))

    return {"code": 0, "data": feedback}


@router.get("/practice/{session_id}/feedback")
def get_feedback(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned(db, session_id, user)
    if not record.feedback_json:
        raise HTTPException(status_code=404, detail="评估尚未生成")
    return {"code": 0, "data": json.loads(record.feedback_json)}


@router.get("/practice/{session_id}")
def get_practice(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned(db, session_id, user)
    topic = db.get(DebateTopic, record.topic_id)
    messages = db.scalars(select(DebateMessage).where(
        DebateMessage.record_id == record.id
    ).order_by(DebateMessage.created_at)).all()
    return {"code": 0, "data": {
        "id": record.id, "status": record.status, "stage": record.current_stage,
        "stance": record.stance, "topic": topic_payload(topic),
        "messages": [{"id": m.id, "role": m.role, "content": m.content,
                       "stage": m.stage, "round": m.round_number} for m in messages],
    }}


@router.get("/history")
def debate_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(DebatePracticeRecord).where(
        DebatePracticeRecord.user_id == user.id
    ).order_by(DebatePracticeRecord.started_at.desc())).all()
    topics = {row.id: row for row in db.scalars(select(DebateTopic)).all()}
    return {"code": 0, "data": [
        {"id": row.id, "topic_id": row.topic_id,
         "topic_title": topics[row.topic_id].title if row.topic_id in topics else "辩论练习",
         "stance": row.stance, "status": row.status, "stage": row.current_stage,
         "score": row.overall_score, "rounds": row.total_rounds,
         "started_at": row.started_at.isoformat()}
        for row in rows
    ]}
