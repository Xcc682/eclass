"""思政辩论路由：辩题生成、分阶段交锋、证据检索与裁判报告。"""
import json
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.debate import DebateMessage, DebatePracticeRecord, DebateTopic
from app.models.domain import GeneratedReport
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.user import User
from app.security import get_ai_user, get_current_user
from app.services import safety, vision
from app.services.ai_service import ai_service, validate_debate_feedback, validate_debate_turn, validate_topics
from app.services.knowledge_service import retrieve
from app.services.point_service import award_points

router = APIRouter(prefix="/api/v1/debates", tags=["思政辩论"])
logger = logging.getLogger("app.debates")

QUICK_STEPS = [
    {"key": "user_opening", "stage": "opening", "label": "立论陈词"},
    {"key": "user_question", "stage": "cross_exam", "label": "主动质询"},
    {"key": "user_rebuttal", "stage": "rebuttal", "label": "核心驳论"},
    {"key": "user_closing", "stage": "closing", "label": "总结陈词"},
]
FULL_STEPS = [
    {"key": "user_opening", "stage": "opening", "label": "立论陈词"},
    {"key": "user_question", "stage": "cross_exam", "label": "主动质询"},
    {"key": "user_counter_answer", "stage": "cross_exam", "label": "回答反质询"},
    {"key": "user_rebuttal", "stage": "rebuttal", "label": "核心驳论"},
    {"key": "user_defense", "stage": "rebuttal", "label": "补充防守"},
    {"key": "user_closing", "stage": "closing", "label": "总结陈词"},
]
STAGE_LABELS = {"opening": "立论", "cross_exam": "质询", "rebuttal": "驳论", "closing": "总结"}
STAGE_TRANSITIONS = {
    "opening": "立论完成，进入质询环节。请针对对手立论中的前提、证据或逻辑提出问题。",
    "cross_exam": "质询完成，进入驳论环节。请围绕刚才暴露的核心分歧展开反驳。",
    "rebuttal": "攻防完成，进入总结环节。请收束已有论证，不再引入新的主要论点。",
    "closing": "四个阶段已经全部完成，正在生成本场训练评估。",
}
FLOW_VERSION = 2
ACTIVE_STATUSES = ("in_progress", "awaiting_feedback")


class StartRequest(BaseModel):
    topic_id: str
    stance: str = Field(pattern=r"^(pro|con)$")
    mode: str = Field(default="quick", pattern=r"^(quick|full)$")
    restart: bool = False


class EvidenceRef(BaseModel):
    chunk_id: str


class ArgumentRequest(BaseModel):
    argument: str = Field(min_length=1, max_length=3000)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list, max_length=3)
    submission_id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=8, max_length=64)
    images: list[str] = Field(default_factory=list, max_length=2)


class EvidenceSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)


def _json(value: str | None, fallback):
    try:
        parsed = json.loads(value or "")
        return parsed if isinstance(parsed, type(fallback)) else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _steps(mode: str) -> list[dict]:
    return FULL_STEPS if mode == "full" else QUICK_STEPS


def _active_key(user_id: str, topic_id: str, stance: str) -> str:
    return f"{user_id}:debate:{topic_id}:{stance}"


def _message_query(record_id: str):
    return select(DebateMessage).where(DebateMessage.record_id == record_id).order_by(
        DebateMessage.created_at, DebateMessage.role.desc(), DebateMessage.id
    )


def _accepted_count(messages: list[DebateMessage]) -> int:
    return sum(1 for item in messages if item.role == "user" and item.delivery_status == "sent")


def _sync_progress(record: DebatePracticeRecord, messages: list[DebateMessage]) -> int:
    steps = _steps(record.mode or "quick")
    completed = min(_accepted_count(messages), len(steps))
    record.total_rounds = completed
    record.current_step = completed
    if completed >= len(steps):
        record.current_stage = "finished"
        if record.status == "in_progress":
            record.status = "awaiting_feedback"
    elif record.status == "in_progress":
        record.current_stage = steps[completed]["stage"]
    if record.status in {"completed", "abandoned"}:
        record.active_key = None
    return completed


def topic_payload(topic: DebateTopic) -> dict:
    return {
        "id": topic.id, "title": topic.title, "category": topic.category,
        "difficulty": topic.difficulty, "context": topic.context,
        "pro_hint": topic.pro_hint, "con_hint": topic.con_hint,
    }


def owned(db: Session, session_id: str, user: User) -> DebatePracticeRecord:
    record = db.get(DebatePracticeRecord, session_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="辩论会话不存在")
    return record


def _normalize_argument_map(value) -> dict[str, list[str]]:
    source = value if isinstance(value, dict) else {}
    normalized = {}
    for key in ("claims", "evidence", "reasoning", "gaps"):
        items = source.get(key, [])
        normalized[key] = [str(item).strip() for item in items if str(item).strip()][:8] if isinstance(items, list) else []
    return normalized


def _normalize_coach(value) -> dict[str, str]:
    source = value if isinstance(value, dict) else {}
    return {key: str(source.get(key, "")).strip() for key in ("stage_fit", "strength", "next_action")}


def _message_payload(message: DebateMessage) -> dict:
    return {
        "id": message.id, "role": message.role, "content": message.content,
        "stage": message.stage, "round": message.round_number,
        "analysis": _json(message.analysis_json, {}), "evidence": _json(message.evidence_json, []),
        "submission_id": message.submission_id, "delivery_status": message.delivery_status,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _session_payload(record: DebatePracticeRecord, topic: DebateTopic, messages: list[DebateMessage], resumed: bool = False) -> dict:
    steps = _steps(record.mode or "quick")
    completed = _sync_progress(record, messages)
    terminal = completed >= len(steps) or record.status in {"awaiting_feedback", "completed"}
    current = steps[completed] if not terminal else {"key": "finished", "stage": "finished", "label": "已完成"}
    return {
        "id": record.id, "status": record.status, "stage": record.current_stage,
        "step": current["key"], "step_label": current["label"], "step_index": completed,
        "completed_steps": completed, "total_steps": len(steps), "mode": record.mode or "quick",
        "stance": record.stance, "topic": topic_payload(topic),
        "messages": [_message_payload(item) for item in messages if item.delivery_status != "failed"],
        "resumed": resumed, "is_finished": terminal,
        "flow_version": record.flow_version, "is_legacy": bool(record.is_legacy),
        "has_report": bool(record.feedback_json), "report_status": record.report_status,
    }


def _turn_payload(record: DebatePracticeRecord, user_message: DebateMessage, ai_message: DebateMessage) -> dict:
    user_analysis = _json(user_message.analysis_json, {})
    ai_analysis = _json(ai_message.analysis_json, {})
    state = ai_analysis.get("turn_state", {}) if isinstance(ai_analysis.get("turn_state"), dict) else {}
    completed = int(state.get("completed_steps", record.total_rounds or 0))
    steps = _steps(record.mode or "quick")
    return {
        "argument": ai_message.content, "round": user_message.round_number,
        "stage": user_message.stage, "next_stage": state.get("next_stage", record.current_stage),
        "step": user_analysis.get("step", ""), "step_label": user_analysis.get("step_label", ""),
        "next_step": state.get("next_step", "finished"), "step_index": completed,
        "completed_steps": completed, "total_steps": len(steps),
        "stage_complete": bool(state.get("stage_complete", False)),
        "phase_transition": state.get("phase_transition", ""),
        "is_finished": bool(state.get("is_finished", completed >= len(steps))),
        "status": state.get("status", record.status),
        "coach_feedback": user_analysis.get("coach_feedback", {}),
        "argument_map": user_analysis.get("argument_map", {}),
        "citations": _json(user_message.evidence_json, []),
        "user_message_id": user_message.id, "ai_message_id": ai_message.id,
    }


def _resolve_evidence(db: Session, refs: list[EvidenceRef]) -> list[dict]:
    citations = []
    seen = set()
    for ref in refs[:3]:
        if ref.chunk_id in seen:
            continue
        seen.add(ref.chunk_id)
        chunk = db.get(KnowledgeChunk, ref.chunk_id)
        document = db.get(KnowledgeDocument, chunk.document_id) if chunk else None
        if not chunk or not document or document.status != "published":
            raise HTTPException(status_code=400, detail="引用资料不存在或尚未发布")
        citations.append({
            "chunk_id": chunk.id, "chunk_index": chunk.chunk_index,
            "document_id": document.id, "document_title": document.title,
            "source": document.source, "source_url": document.source_url,
            "excerpt": chunk.content[:300],
        })
    return citations


@router.get("/topics")
def get_topics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    topics = db.scalars(select(DebateTopic).where(
        or_(DebateTopic.status == "published", DebateTopic.owner_id == user.id)
    ).order_by(DebateTopic.created_at.desc())).all()
    return {"code": 0, "data": [topic_payload(topic) for topic in topics]}


@router.post("/topics/generate")
async def generate_topics(user: User = Depends(get_ai_user), db: Session = Depends(get_db)):
    try:
        generated = validate_topics(await ai_service.debate_generate_topics())
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    rows = []
    for item in generated:
        topic = DebateTopic(
            title=item["title"], category=item["category"], difficulty=item["difficulty"],
            context=item["context"], pro_hint=item["pro_hint"], con_hint=item["con_hint"],
            is_ai_generated=True, owner_id=user.id,
            status="published" if user.role in {"teacher", "admin"} else "private",
        )
        db.add(topic)
        db.flush()
        rows.append(topic_payload(topic))
    return {"code": 0, "data": rows}


@router.post("/practice/start")
async def start_debate(data: StartRequest, user: User = Depends(get_ai_user), db: Session = Depends(get_db)):
    topic = db.get(DebateTopic, data.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="辩题不存在")
    if topic.status != "published" and topic.owner_id != user.id:
        raise HTTPException(status_code=403, detail="无权使用该辩题")
    key = _active_key(user.id, topic.id, data.stance)
    active = db.scalar(select(DebatePracticeRecord).where(
        DebatePracticeRecord.active_key == key, DebatePracticeRecord.status.in_(ACTIVE_STATUSES),
        DebatePracticeRecord.flow_version == FLOW_VERSION, DebatePracticeRecord.is_legacy.is_(False),
    ).limit(1))
    if active and not data.restart:
        messages = db.scalars(_message_query(active.id)).all()
        payload = _session_payload(active, topic, messages, resumed=True)
        payload.update({
            "first_argument": messages[0].content if messages else "",
            "stage_label": "已结束" if active.current_stage == "finished" else STAGE_LABELS.get(active.current_stage, active.current_stage),
            "stance_label": "正方" if active.stance == "pro" else "反方",
        })
        return {"code": 0, "data": payload}
    if active:
        active.status = "abandoned"
        active.active_key = None
        db.commit()

    record = DebatePracticeRecord(
        user_id=user.id, topic_id=topic.id, stance=data.stance, status="in_progress",
        current_stage="opening", mode=data.mode, current_step=0, total_rounds=0,
        flow_version=FLOW_VERSION, is_legacy=False, active_key=key, report_status="idle",
    )
    topic.usage_count += 1
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        winner = db.scalar(select(DebatePracticeRecord).where(DebatePracticeRecord.active_key == key).limit(1))
        if not winner:
            raise
        return {"code": 0, "data": _session_payload(winner, topic, db.scalars(_message_query(winner.id)).all(), resumed=True)}
    try:
        opening = await ai_service.debate_open(topic.title, data.stance)
    except Exception:
        opening = (topic.con_hint if data.stance == "pro" else topic.pro_hint) or "请先陈述你的核心观点。"
    db.add(DebateMessage(
        record_id=record.id, stage="opening", role="ai", content=opening, round_number=0,
        analysis_json="{}", evidence_json="[]", delivery_status="sent",
    ))
    db.flush()
    payload = _session_payload(record, topic, db.scalars(_message_query(record.id)).all())
    payload.update({"first_argument": opening, "stage_label": "立论", "stance_label": "正方" if data.stance == "pro" else "反方"})
    return {"code": 0, "data": payload}


@router.post("/practice/{session_id}/evidence/search")
def search_evidence(session_id: str, data: EvidenceSearchRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    owned(db, session_id, user)
    hits = retrieve(db, data.query, limit=12)
    citations = []
    for item in hits:
        document = db.get(KnowledgeDocument, item["document_id"])
        if not document or document.status != "published":
            continue
        citations.append({
            "chunk_id": item["chunk_id"], "chunk_index": item["chunk_index"],
            "document_id": document.id, "document_title": document.title,
            "source": document.source, "source_url": document.source_url,
            "excerpt": item["content"][:300],
        })
        if len(citations) >= 8:
            break
    return {"code": 0, "data": citations}


@router.post("/practice/{session_id}/argue")
async def submit_argument(session_id: str, data: ArgumentRequest, user: User = Depends(get_ai_user), db: Session = Depends(get_db)):
    verdict = safety.check_input(data.argument)
    if not verdict.allowed:
        raise HTTPException(status_code=400, detail=verdict.reason)
    try:
        images = vision.sanitize_images(data.images)
    except vision.ImageInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record = owned(db, session_id, user)
    if record.is_legacy or record.flow_version != FLOW_VERSION:
        raise HTTPException(status_code=409, detail="旧版辩论仅供查看，请重新开始新版训练")

    prior_user = db.scalar(select(DebateMessage).where(
        DebateMessage.record_id == record.id, DebateMessage.role == "user",
        DebateMessage.submission_id == data.submission_id,
    ))
    if prior_user:
        prior_ai = db.scalar(select(DebateMessage).where(
            DebateMessage.record_id == record.id, DebateMessage.role == "ai",
            DebateMessage.submission_id == data.submission_id,
        ))
        if prior_user.delivery_status == "sent" and prior_ai and prior_ai.delivery_status == "sent":
            return {"code": 0, "data": _turn_payload(record, prior_user, prior_ai)}
        if prior_user.delivery_status == "pending" and prior_user.created_at and prior_user.created_at > datetime.utcnow() - timedelta(seconds=90):
            raise HTTPException(status_code=409, detail="这条陈词仍在处理中，请稍候")

    messages = db.scalars(_message_query(record.id)).all()
    completed = _sync_progress(record, messages)
    steps = _steps(record.mode or "quick")
    if record.status != "in_progress" or completed >= len(steps):
        raise HTTPException(status_code=409, detail="赛程已结束，请生成或查看评估报告")
    step = steps[completed]
    citations = _resolve_evidence(db, data.evidence_refs)
    round_number = completed + 1
    if prior_user:
        prior_user.content = data.argument
        prior_user.stage = step["stage"]
        prior_user.round_number = round_number
        prior_user.evidence_json = json.dumps(citations, ensure_ascii=False)
        prior_user.delivery_status = "pending"
        prior_user.created_at = datetime.utcnow()
        user_message = prior_user
    else:
        user_message = DebateMessage(
            record_id=record.id, stage=step["stage"], role="user", content=data.argument,
            round_number=round_number, submission_id=data.submission_id, delivery_status="pending",
            analysis_json=json.dumps({"step": step["key"], "step_label": step["label"]}, ensure_ascii=False),
            evidence_json=json.dumps(citations, ensure_ascii=False),
        )
        db.add(user_message)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(select(DebateMessage).where(
            DebateMessage.record_id == record.id, DebateMessage.role == "user",
            DebateMessage.round_number == round_number,
        ))
        if duplicate and duplicate.submission_id != data.submission_id:
            raise HTTPException(status_code=409, detail="本步骤已有陈词正在处理，请刷新会话") from None
        raise

    record = owned(db, session_id, user)
    topic = db.get(DebateTopic, record.topic_id)
    messages = db.scalars(_message_query(record.id)).all()
    conversation = [{
        "role": item.role, "content": item.content,
        "stance": record.stance if item.role == "user" else ("con" if record.stance == "pro" else "pro"),
    } for item in messages if item.delivery_status == "sent"]
    try:
        turn = validate_debate_turn(await ai_service.debate_argue(
            topic.title, record.stance, data.argument, conversation,
            stage=step["stage"], step=step["key"], evidence=citations, images=images or None,
        ))
    except Exception as exc:
        failed = db.get(DebateMessage, user_message.id)
        if failed:
            failed.delivery_status = "failed"
            db.commit()
        logger.exception("Debate AI request failed: session_id=%s step=%s", session_id, step["key"])
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc

    user_message = db.get(DebateMessage, user_message.id)
    coach = _normalize_coach(turn.get("coach_feedback"))
    argument_map = _normalize_argument_map(turn.get("argument_map"))
    user_message.delivery_status = "sent"
    user_message.analysis_json = json.dumps({
        "step": step["key"], "step_label": step["label"],
        "coach_feedback": coach, "argument_map": argument_map,
    }, ensure_ascii=False)
    next_index = completed + 1
    finished = next_index >= len(steps)
    next_stage = "finished" if finished else steps[next_index]["stage"]
    stage_complete = finished or next_stage != step["stage"]
    transition = STAGE_TRANSITIONS.get(step["stage"], "") if stage_complete else f"继续【{STAGE_LABELS.get(step['stage'], step['stage'])}】阶段的下一项训练。"
    record.current_step = next_index
    record.current_stage = next_stage
    record.total_rounds = next_index
    if finished:
        record.status = "awaiting_feedback"
    state = {
        "completed_steps": next_index, "next_stage": next_stage,
        "next_step": "finished" if finished else steps[next_index]["key"],
        "stage_complete": stage_complete, "phase_transition": transition,
        "is_finished": finished, "status": record.status,
    }
    ai_message = DebateMessage(
        record_id=record.id, stage=step["stage"], role="ai", content=turn["argument"],
        round_number=round_number, submission_id=data.submission_id, delivery_status="sent",
        analysis_json=json.dumps({"step": step["key"], "turn_state": state}, ensure_ascii=False), evidence_json="[]",
    )
    db.add(ai_message)
    db.commit()
    return {"code": 0, "data": _turn_payload(record, user_message, ai_message)}


@router.post("/practice/{session_id}/end")
async def end_debate(session_id: str, user: User = Depends(get_ai_user), db: Session = Depends(get_db)):
    record = owned(db, session_id, user)
    if record.feedback_json:
        return {"code": 0, "data": _json(record.feedback_json, {})}
    if record.is_legacy or record.flow_version != FLOW_VERSION:
        raise HTTPException(status_code=409, detail="旧版未完成辩论不能生成新版报告，请重新开始训练")
    messages = db.scalars(_message_query(record.id)).all()
    completed = _sync_progress(record, messages)
    expected = len(_steps(record.mode or "quick"))
    if completed != expected or record.status != "awaiting_feedback":
        raise HTTPException(status_code=400, detail="请完成全部辩论步骤后生成评估")

    cutoff = datetime.utcnow() - timedelta(minutes=2)
    claimed = db.execute(update(DebatePracticeRecord).where(
        DebatePracticeRecord.id == record.id, DebatePracticeRecord.feedback_json.is_(None),
        or_(DebatePracticeRecord.report_status != "generating", DebatePracticeRecord.report_started_at < cutoff),
    ).values(report_status="generating", report_started_at=datetime.utcnow())).rowcount
    db.commit()
    if not claimed:
        refreshed = owned(db, session_id, user)
        if refreshed.feedback_json:
            return {"code": 0, "data": _json(refreshed.feedback_json, {})}
        raise HTTPException(status_code=409, detail="评估报告正在生成，请稍后查看")

    topic = db.get(DebateTopic, record.topic_id)
    conversation = [{
        "role": item.role, "content": item.content,
        "stance": record.stance if item.role == "user" else ("con" if record.stance == "pro" else "pro"),
    } for item in messages if item.delivery_status == "sent"]
    try:
        feedback = validate_debate_feedback(await ai_service.debate_feedback(topic.title, conversation, user_stance=record.stance))
    except Exception as exc:
        db.execute(update(DebatePracticeRecord).where(DebatePracticeRecord.id == session_id).values(report_status="failed", report_started_at=None))
        db.commit()
        logger.exception("Debate AI feedback failed: session_id=%s", session_id)
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc

    feedback["overall_score"] = round(sum(feedback["dimension_scores"].values()) / len(feedback["dimension_scores"]))
    feedback["grade"] = "优秀" if feedback["overall_score"] >= 85 else "良好" if feedback["overall_score"] >= 70 else "需努力"
    exchanges = feedback.get("key_exchanges", []) if isinstance(feedback.get("key_exchanges"), list) else []
    user_messages = [item for item in messages if item.role == "user" and item.delivery_status == "sent"]
    ai_by_round = {item.round_number: item for item in messages if item.role == "ai" and item.delivery_status == "sent"}
    for index, exchange in enumerate(exchanges):
        if not isinstance(exchange, dict) or not user_messages:
            continue
        source = user_messages[min(index, len(user_messages) - 1)]
        paired = ai_by_round.get(source.round_number)
        exchange["message_ids"] = [source.id] + ([paired.id] if paired else [])
        exchange["round"] = source.round_number
    feedback["key_exchanges"] = exchanges
    payload = json.dumps(feedback, ensure_ascii=False)

    record = owned(db, session_id, user)
    record.status = "completed"
    record.completed_at = datetime.utcnow()
    record.overall_score = feedback["overall_score"]
    record.feedback_json = payload
    record.report_status = "completed"
    record.report_started_at = None
    record.active_key = None
    existing_report = db.scalar(select(GeneratedReport).where(
        GeneratedReport.report_type == "debate", GeneratedReport.source_record_id == record.id,
    ))
    if not existing_report:
        db.add(GeneratedReport(
            user_id=user.id, report_type="debate", source_record_id=record.id,
            title=topic.title, score=record.overall_score, content_json=payload,
        ))
    award_points(
        db, user,
        module="debate", event_type="practice_completed", source_id=record.id,
        points=max(record.overall_score // 10, 1), description="完成思政辩论训练",
        metadata={"score": record.overall_score, "topic_id": record.topic_id, "mode": record.mode},
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = owned(db, session_id, user)
        if winner.feedback_json:
            return {"code": 0, "data": _json(winner.feedback_json, {})}
        raise
    return {"code": 0, "data": feedback}


@router.get("/practice/{session_id}/feedback")
def get_feedback(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned(db, session_id, user)
    if not record.feedback_json:
        raise HTTPException(status_code=404, detail="评估尚未生成")
    return {"code": 0, "data": _json(record.feedback_json, {})}


@router.get("/practice/{session_id}")
def get_practice(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned(db, session_id, user)
    topic = db.get(DebateTopic, record.topic_id)
    messages = db.scalars(_message_query(record.id)).all()
    return {"code": 0, "data": _session_payload(record, topic, messages, resumed=True)}


@router.get("/history")
def debate_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(DebatePracticeRecord).where(
        DebatePracticeRecord.user_id == user.id
    ).order_by(DebatePracticeRecord.started_at.desc())).all()
    topics = {row.id: row for row in db.scalars(select(DebateTopic)).all()}
    data = []
    for row in rows:
        messages = db.scalars(_message_query(row.id)).all()
        completed = _sync_progress(row, messages)
        expected = len(_steps(row.mode or "quick"))
        data.append({
            "id": row.id, "topic_id": row.topic_id,
            "topic_title": topics[row.topic_id].title if row.topic_id in topics else "辩论练习",
            "stance": row.stance, "status": row.status, "stage": row.current_stage,
            "mode": row.mode, "step_index": completed, "completed_steps": completed, "total_steps": expected,
            "score": row.overall_score, "rounds": completed,
            "flow_version": row.flow_version, "is_legacy": bool(row.is_legacy),
            "has_report": bool(row.feedback_json), "report_status": row.report_status,
            "started_at": row.started_at.isoformat(),
        })
    return {"code": 0, "data": data}
