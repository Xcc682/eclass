import json
import random
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.domain import GeneratedReport
from app.models.interview import InterviewMessage, InterviewPracticeRecord, InterviewScenario
from app.models.user import User
from app.security import get_current_user, get_optional_user
from app.services.ai_service import ai_service, validate_interview_report, validate_interview_turn, DIMENSIONS

router = APIRouter(prefix="/api/v1/interviews", tags=["入党谈话"])


class StartRequest(BaseModel):
    scenario_id: str = "1"


class RespondRequest(BaseModel):
    content: str = Field(min_length=1, max_length=3000)


def scenario_payload(s: InterviewScenario, db: Optional[Session] = None, user: Optional[User] = None) -> dict:
    payload = {"id": s.id, "title": s.title, "description": s.description, "difficulty": s.difficulty,
               "estimated_duration": s.estimated_duration, "ai_role_name": s.ai_role_name, "ai_role_title": s.ai_role_title}
    if db and user:
        best = db.scalar(select(func.max(InterviewPracticeRecord.overall_score)).where(
            InterviewPracticeRecord.scenario_id == s.id,
            InterviewPracticeRecord.user_id == user.id,
            InterviewPracticeRecord.status == "completed"
        ))
        count = db.scalar(select(func.count()).select_from(InterviewPracticeRecord).where(
            InterviewPracticeRecord.scenario_id == s.id,
            InterviewPracticeRecord.user_id == user.id,
            InterviewPracticeRecord.status == "completed"
        ))
        payload["best_score"] = best
        payload["completion_status"] = "completed" if count else "not_started"
        payload["attempts"] = count or 0
    else:
        payload["best_score"] = None
        payload["completion_status"] = "not_started"
        payload["attempts"] = 0
    return payload


def owned_record(db: Session, practice_id: str, user: User) -> InterviewPracticeRecord:
    record = db.get(InterviewPracticeRecord, practice_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="练习不存在")
    return record


@router.get("/scenarios")
def get_scenarios(user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(InterviewScenario).order_by(InterviewScenario.created_at)).all()
    return {"code": 0, "data": [scenario_payload(row, db, user) for row in rows]}


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    row = db.get(InterviewScenario, scenario_id)
    if not row:
        raise HTTPException(status_code=404, detail="场景不存在")
    return {"code": 0, "data": scenario_payload(row, db, user)}


@router.post("/practice/start")
async def start_practice(data: StartRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scenario = db.get(InterviewScenario, data.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="场景不存在")
    difficulty = scenario.difficulty
    if difficulty == "random":
        candidates = db.scalars(select(InterviewScenario).where(InterviewScenario.difficulty != "random")).all()
        scenario = random.choice(candidates)
        difficulty = scenario.difficulty
    try:
        result = validate_interview_turn(await ai_service.interview_start(difficulty))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    record = InterviewPracticeRecord(user_id=user.id, scenario_id=scenario.id, status="in_progress")
    db.add(record)
    db.flush()
    first_question = result.get("question", "同学你好，请先做个自我介绍。")
    phase = result.get("phase", "开场寒暄")
    db.add(InterviewMessage(record_id=record.id, role="ai", content=first_question, round_number=1,
                            analysis_json=json.dumps({"comment": result.get("comment", ""), "phase": phase, "follow_up_type": result.get("follow_up_type", "")}, ensure_ascii=False)))
    record.total_rounds = 1
    return {"code": 0, "data": {"id": record.id, "scenario": scenario_payload(scenario, db, user), "first_question": first_question, "phase": phase}}


@router.post("/practice/{practice_id}/respond")
async def respond(practice_id: str, data: RespondRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    if record.status != "in_progress":
        raise HTTPException(status_code=409, detail="练习已结束")
    scenario = db.get(InterviewScenario, record.scenario_id)
    difficulty = scenario.difficulty if scenario else "intermediate"
    existing = db.scalars(select(InterviewMessage).where(InterviewMessage.record_id == record.id).order_by(InterviewMessage.created_at)).all()
    round_number = sum(1 for m in existing if m.role == "user") + 1
    user_message = InterviewMessage(record_id=record.id, role="user", content=data.content, round_number=round_number)
    db.add(user_message)
    conversation = [{"role": m.role, "content": m.content} for m in existing] + [{"role": "user", "content": data.content}]
    try:
        result = validate_interview_turn(await ai_service.interview_respond(conversation, difficulty))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    question = result.get("question", "请继续。")
    comment = result.get("comment", "")
    ended = result.get("finished", False) or round_number >= 6
    phase = result.get("phase", "")
    follow_up = result.get("follow_up_type", "")
    scenario = result.get("scenario", "")
    snapshot = result.get("snapshot_scores", {})
    db.add(InterviewMessage(record_id=record.id, role="ai", content=question, round_number=round_number,
                            analysis_json=json.dumps({"comment": comment, "phase": phase, "follow_up_type": follow_up, "snapshot_scores": snapshot, "scenario": scenario}, ensure_ascii=False)))
    record.total_rounds = round_number
    return {"code": 0, "data": {"question": question, "analysis": {"comment": comment, "phase": phase, "follow_up_type": follow_up, "snapshot_scores": snapshot, "scenario": scenario}, "is_completed": ended}}


@router.post("/practice/{practice_id}/end")
async def end_practice(practice_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    if record.report_json:
        return {"code": 0, "data": json.loads(record.report_json)}
    messages = db.scalars(select(InterviewMessage).where(InterviewMessage.record_id == record.id).order_by(InterviewMessage.created_at)).all()
    conversation = [{"role": m.role, "content": m.content} for m in messages]
    if sum(1 for m in messages if m.role == "user") < 2:
        raise HTTPException(status_code=400, detail="至少需要回答2次才能生成报告")
    try:
        report = validate_interview_report(await ai_service.interview_report(conversation))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    record.status = "completed"
    record.completed_at = datetime.utcnow()
    record.overall_score = int(report.get("overall_score", 0))
    record.report_json = json.dumps(report, ensure_ascii=False)
    user.total_points += max(record.overall_score // 10, 1)

    # Historical comparison: find previous completed report for same scenario
    previous = db.scalar(select(InterviewPracticeRecord).where(
        InterviewPracticeRecord.user_id == user.id,
        InterviewPracticeRecord.scenario_id == record.scenario_id,
        InterviewPracticeRecord.status == "completed",
        InterviewPracticeRecord.id != record.id,
    ).order_by(InterviewPracticeRecord.completed_at.desc()).limit(1))

    delta = {}
    if previous and previous.report_json:
        prev_report = json.loads(previous.report_json)
        prev_scores = prev_report.get("dimension_scores", {})
        curr_scores = report.get("dimension_scores", {})
        prev_overall = int(prev_report.get("overall_score", 0))
        for dim in DIMENSIONS:
            if dim in curr_scores and dim in prev_scores:
                delta[dim] = int(curr_scores[dim]) - int(prev_scores[dim])
        delta["overall_score"] = record.overall_score - prev_overall
    report["delta"] = delta
    report["has_previous"] = previous is not None and bool(delta)

    scenario = db.get(InterviewScenario, record.scenario_id)
    db.add(GeneratedReport(user_id=user.id, report_type="interview", title=scenario.title if scenario else "入党谈话", score=record.overall_score, content_json=record.report_json))
    return {"code": 0, "data": report}


@router.get("/practice/{practice_id}/report")
def get_report(practice_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    if not record.report_json:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    return {"code": 0, "data": json.loads(record.report_json)}


@router.get("/practice/{practice_id}")
def get_practice(practice_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    scenario = db.get(InterviewScenario, record.scenario_id)
    messages = db.scalars(select(InterviewMessage).where(InterviewMessage.record_id == record.id).order_by(InterviewMessage.created_at)).all()
    return {"code": 0, "data": {
        "id": record.id, "status": record.status, "scenario": scenario_payload(scenario), "score": record.overall_score,
        "messages": [{"id": message.id, "role": message.role, "content": message.content, "analysis": json.loads(message.analysis_json or "{}"), "round_number": message.round_number, "created_at": message.created_at.isoformat()} for message in messages],
    }}


@router.post("/practice/{practice_id}/hint")
async def get_hint(practice_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    messages = db.scalars(select(InterviewMessage).where(InterviewMessage.record_id == record.id).order_by(InterviewMessage.created_at)).all()
    last_ai_question = ""
    for m in reversed(messages):
        if m.role == "ai":
            last_ai_question = m.content
            break
    try:
        hint = await ai_service.interview_hint(last_ai_question)
    except Exception:
        hint = "结合个人经历、理论学习与真实思想认识，用具体事例回答。"
    return {"code": 0, "data": {"hint": hint}}


@router.get("/history")
def get_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(InterviewPracticeRecord).where(InterviewPracticeRecord.user_id == user.id).order_by(InterviewPracticeRecord.started_at.desc())).all()
    scenarios = {row.id: row for row in db.scalars(select(InterviewScenario)).all()}
    return {"code": 0, "data": [{"id": r.id, "scenario_id": r.scenario_id, "scenario_title": scenarios[r.scenario_id].title if r.scenario_id in scenarios else "谈话练习", "status": r.status, "score": r.overall_score, "rounds": r.total_rounds, "started_at": r.started_at.isoformat()} for r in rows]}
