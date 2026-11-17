"""入党谈话路由：场景列表、练习流程、逐轮应答、提示与评估报告。"""
import json
import random
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.domain import GeneratedReport
from app.models.interview import InterviewMessage, InterviewPracticeRecord, InterviewScenario
from app.models.user import User
from app.security import get_current_user, get_optional_user
from app.services import learner_profile, safety, vision
from app.services.ai_service import DIMENSIONS, ai_service, validate_interview_report, validate_interview_turn
from app.services.point_service import award_points

router = APIRouter(prefix="/api/v1/interviews", tags=["入党谈话"])

PHASE_PLAN = ["开场寒暄", "自我认知", "入党动机", "理论考察", "理论考察", "情景假设"]
TOTAL_QUESTIONS = len(PHASE_PLAN)
FLOW_VERSION = 2
ACTIVE_STATUSES = ("in_progress", "awaiting_report")


class StartRequest(BaseModel):
    scenario_id: str = "1"
    restart: bool = False


class RespondRequest(BaseModel):
    content: str = Field(min_length=1, max_length=3000)
    submission_id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=8, max_length=64)
    images: list[str] = Field(default_factory=list, max_length=2)


def _json(value: str | None, fallback):
    try:
        parsed = json.loads(value or "")
        return parsed if isinstance(parsed, type(fallback)) else fallback
    except (TypeError, json.JSONDecodeError):
        return fallback


def _active_key(user_id: str, scenario_id: str) -> str:
    return f"{user_id}:interview:{scenario_id}"


def _message_query(record_id: str):
    return select(InterviewMessage).where(InterviewMessage.record_id == record_id).order_by(
        InterviewMessage.created_at, InterviewMessage.role.desc(), InterviewMessage.id
    )


def _accepted_count(messages: list[InterviewMessage]) -> int:
    return sum(1 for item in messages if item.role == "user" and item.delivery_status == "sent")


def _sync_progress(record: InterviewPracticeRecord, messages: list[InterviewMessage]) -> int:
    answered = min(_accepted_count(messages), TOTAL_QUESTIONS)
    record.total_rounds = answered
    record.current_step = answered
    record.current_phase = PHASE_PLAN[min(answered, TOTAL_QUESTIONS - 1)]
    if answered >= TOTAL_QUESTIONS and record.status == "in_progress":
        record.status = "awaiting_report"
    if record.status in {"completed", "abandoned"}:
        record.active_key = None
    return answered


def _valid_record_filter():
    return (
        InterviewPracticeRecord.flow_version == FLOW_VERSION,
        InterviewPracticeRecord.is_legacy.is_(False),
    )


def scenario_payload(s: InterviewScenario, db: Session | None = None, user: User | None = None) -> dict:
    payload = {
        "id": s.id, "title": s.title, "description": s.description, "difficulty": s.difficulty,
        "estimated_duration": s.estimated_duration, "ai_role_name": s.ai_role_name, "ai_role_title": s.ai_role_title,
    }
    if not db or not user:
        return {**payload, "best_score": None, "completion_status": "not_started", "attempts": 0, "has_active_practice": False}

    scenario_column = func.coalesce(InterviewPracticeRecord.requested_scenario_id, InterviewPracticeRecord.scenario_id)
    common = (
        InterviewPracticeRecord.user_id == user.id,
        scenario_column == s.id,
        *_valid_record_filter(),
    )
    best = db.scalar(select(func.max(InterviewPracticeRecord.overall_score)).where(
        *common, InterviewPracticeRecord.status == "completed", InterviewPracticeRecord.total_rounds == TOTAL_QUESTIONS,
    ))
    completed = int(db.scalar(select(func.count()).select_from(InterviewPracticeRecord).where(
        *common, InterviewPracticeRecord.status == "completed", InterviewPracticeRecord.total_rounds == TOTAL_QUESTIONS,
        InterviewPracticeRecord.report_json.is_not(None),
    )) or 0)
    active = db.scalar(select(InterviewPracticeRecord.id).where(
        *common, InterviewPracticeRecord.status.in_(ACTIVE_STATUSES),
    ).limit(1))
    return {
        **payload, "best_score": best, "completion_status": "completed" if completed else "not_started",
        "attempts": completed, "has_active_practice": bool(active),
    }


def owned_record(db: Session, practice_id: str, user: User) -> InterviewPracticeRecord:
    record = db.get(InterviewPracticeRecord, practice_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="练习不存在")
    return record


def _empty_evaluation() -> dict:
    return {"dimensions": {name: {
        "weighted_sum": 0.0, "weight": 0.0, "evidence_count": 0,
        "raw_score": None, "trend": "pending", "latest_evidence": "",
    } for name in DIMENSIONS}}


def _load_evaluation(record: InterviewPracticeRecord) -> dict:
    value = _json(record.live_evaluation_json, {})
    if not isinstance(value.get("dimensions"), dict):
        return _empty_evaluation()
    base = _empty_evaluation()
    for name in DIMENSIONS:
        if isinstance(value["dimensions"].get(name), dict):
            base["dimensions"][name].update(value["dimensions"][name])
    return base


def _update_evaluation(record: InterviewPracticeRecord, observations: dict) -> dict:
    evaluation = _load_evaluation(record)
    for name in DIMENSIONS:
        observation = observations.get(name, {}) if isinstance(observations, dict) else {}
        evidence = str(observation.get("evidence", "")).strip()
        if not observation.get("observed") or not evidence:
            continue
        try:
            score = max(0, min(100, int(observation.get("score", 0))))
            confidence = max(0.1, min(1.0, float(observation.get("confidence", 0.5))))
        except (TypeError, ValueError):
            continue
        row = evaluation["dimensions"][name]
        previous = row.get("raw_score")
        row["weighted_sum"] = round(float(row.get("weighted_sum", 0)) + score * confidence, 3)
        row["weight"] = round(float(row.get("weight", 0)) + confidence, 3)
        row["evidence_count"] = int(row.get("evidence_count", 0)) + 1
        current = round(row["weighted_sum"] / row["weight"])
        row["raw_score"] = current
        row["trend"] = "up" if previous is not None and current > previous + 2 else "down" if previous is not None and current < previous - 2 else "stable"
        row["latest_evidence"] = evidence[:180]
    record.live_evaluation_json = json.dumps(evaluation, ensure_ascii=False)
    return evaluation


def _public_evaluation(value: dict) -> dict:
    dimensions = {}
    for name in DIMENSIONS:
        row = value.get("dimensions", {}).get(name, {})
        count = int(row.get("evidence_count", 0))
        dimensions[name] = {
            "score": int(row["raw_score"]) if count >= 2 and row.get("raw_score") is not None else None,
            "evidence_count": count,
            "trend": row.get("trend", "pending") if count >= 2 else "pending",
            "latest_evidence": row.get("latest_evidence", ""),
        }
    return {"dimensions": dimensions, "disclaimer": "AI 训练预估，不代表党组织正式评价"}


def _message_payload(message: InterviewMessage) -> dict:
    analysis = _json(message.analysis_json, {})
    return {
        "id": message.id, "role": message.role, "content": message.content,
        "analysis": analysis, "ai_analysis": analysis, "round_number": message.round_number,
        "submission_id": message.submission_id, "delivery_status": message.delivery_status,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _practice_payload(record: InterviewPracticeRecord, scenario: InterviewScenario, messages: list[InterviewMessage], resumed: bool = False) -> dict:
    answered = _sync_progress(record, messages)
    last_ai = next((item for item in reversed(messages) if item.role == "ai" and item.delivery_status == "sent"), None)
    terminal = answered >= TOTAL_QUESTIONS or record.status in {"awaiting_report", "completed"}
    current_question = None if terminal else answered + 1
    return {
        "id": record.id, "scenario": scenario_payload(scenario), "first_question": last_ai.content if last_ai else "",
        "messages": [_message_payload(item) for item in messages if item.delivery_status != "failed"],
        "status": record.status, "phase": record.current_phase,
        "phase_index": min(answered, TOTAL_QUESTIONS - 1),
        "question_index": current_question or TOTAL_QUESTIONS,
        "answered_count": answered, "current_question_number": current_question,
        "total_questions": TOTAL_QUESTIONS, "is_completed": terminal, "resumed": resumed,
        "live_evaluation": _public_evaluation(_load_evaluation(record)),
        "flow_version": record.flow_version, "is_legacy": bool(record.is_legacy),
        "has_report": bool(record.report_json), "report_status": record.report_status,
    }


def _turn_payload(record: InterviewPracticeRecord, user_message: InterviewMessage, ai_message: InterviewMessage) -> dict:
    analysis = _json(ai_message.analysis_json, {})
    state = analysis.get("turn_state", {}) if isinstance(analysis.get("turn_state"), dict) else {}
    answered = int(state.get("answered_count", record.total_rounds or 0))
    current_question = state.get("current_question_number")
    return {
        "question": ai_message.content, "analysis": analysis,
        "is_completed": bool(state.get("is_completed", answered >= TOTAL_QUESTIONS)),
        "status": state.get("status", record.status), "phase": state.get("phase", record.current_phase),
        "phase_index": int(state.get("phase_index", min(answered, TOTAL_QUESTIONS - 1))),
        "question_index": int(current_question or TOTAL_QUESTIONS),
        "answered_count": answered, "current_question_number": current_question,
        "total_questions": TOTAL_QUESTIONS,
        "live_evaluation": analysis.get("live_evaluation", _public_evaluation(_load_evaluation(record))),
        "user_message": _message_payload(user_message), "ai_message": _message_payload(ai_message),
    }


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
    requested = db.get(InterviewScenario, data.scenario_id)
    if not requested:
        raise HTTPException(status_code=404, detail="场景不存在")
    key = _active_key(user.id, requested.id)
    active = db.scalar(select(InterviewPracticeRecord).where(
        InterviewPracticeRecord.active_key == key,
        InterviewPracticeRecord.status.in_(ACTIVE_STATUSES),
        *_valid_record_filter(),
    ).limit(1))
    if active and not data.restart:
        scenario = db.get(InterviewScenario, active.scenario_id)
        messages = db.scalars(_message_query(active.id)).all()
        return {"code": 0, "data": _practice_payload(active, scenario, messages, resumed=True)}
    if active:
        active.status = "abandoned"
        active.active_key = None
        db.commit()

    scenario = requested
    if requested.difficulty == "random":
        candidates = db.scalars(select(InterviewScenario).where(InterviewScenario.difficulty != "random")).all()
        if candidates:
            scenario = random.choice(candidates)
    try:
        context = learner_profile.interview_context(db, user.id)
        result = validate_interview_turn(await ai_service.interview_start(scenario.difficulty, learner_context=context))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc

    record = InterviewPracticeRecord(
        user_id=user.id, scenario_id=scenario.id, requested_scenario_id=requested.id,
        status="in_progress", current_phase=PHASE_PLAN[0], current_step=0, total_rounds=0,
        live_evaluation_json=json.dumps(_empty_evaluation(), ensure_ascii=False),
        flow_version=FLOW_VERSION, is_legacy=False, active_key=key, report_status="idle",
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        winner = db.scalar(select(InterviewPracticeRecord).where(InterviewPracticeRecord.active_key == key).limit(1))
        if not winner:
            raise
        winner_scenario = db.get(InterviewScenario, winner.scenario_id)
        return {"code": 0, "data": _practice_payload(winner, winner_scenario, db.scalars(_message_query(winner.id)).all(), resumed=True)}
    first_question = result.get("question", "同学你好，请先做个自我介绍。")
    db.add(InterviewMessage(
        record_id=record.id, role="ai", content=first_question, round_number=1, delivery_status="sent",
        analysis_json=json.dumps({"comment": result.get("comment", ""), "phase": PHASE_PLAN[0], "follow_up_type": result.get("follow_up_type", "")}, ensure_ascii=False),
    ))
    db.flush()
    return {"code": 0, "data": _practice_payload(record, scenario, db.scalars(_message_query(record.id)).all())}


@router.post("/practice/{practice_id}/respond")
async def respond(practice_id: str, data: RespondRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    verdict = safety.check_input(data.content)
    if not verdict.allowed:
        raise HTTPException(status_code=400, detail=verdict.reason)
    try:
        images = vision.sanitize_images(data.images)
    except vision.ImageInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    record = owned_record(db, practice_id, user)
    if record.is_legacy or record.flow_version != FLOW_VERSION:
        raise HTTPException(status_code=409, detail="旧版谈话仅供查看，请重新开始新版练习")

    prior_user = db.scalar(select(InterviewMessage).where(
        InterviewMessage.record_id == record.id, InterviewMessage.role == "user",
        InterviewMessage.submission_id == data.submission_id,
    ))
    if prior_user:
        prior_ai = db.scalar(select(InterviewMessage).where(
            InterviewMessage.record_id == record.id, InterviewMessage.role == "ai",
            InterviewMessage.submission_id == data.submission_id,
        ))
        if prior_user.delivery_status == "sent" and prior_ai and prior_ai.delivery_status == "sent":
            return {"code": 0, "data": _turn_payload(record, prior_user, prior_ai)}
        if prior_user.delivery_status == "pending" and prior_user.created_at and prior_user.created_at > datetime.utcnow() - timedelta(seconds=90):
            raise HTTPException(status_code=409, detail="这条回答仍在处理中，请稍候")

    existing = db.scalars(_message_query(record.id)).all()
    answered = _sync_progress(record, existing)
    if record.status != "in_progress" or answered >= TOTAL_QUESTIONS:
        raise HTTPException(status_code=409, detail="谈话已完成，请生成或查看报告")

    round_number = answered + 1
    if prior_user:
        prior_user.content = data.content
        prior_user.round_number = round_number
        prior_user.delivery_status = "pending"
        prior_user.created_at = datetime.utcnow()
        user_message = prior_user
    else:
        user_message = InterviewMessage(
            record_id=record.id, role="user", content=data.content, round_number=round_number,
            submission_id=data.submission_id, delivery_status="pending",
        )
        db.add(user_message)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.scalar(select(InterviewMessage).where(
            InterviewMessage.record_id == record.id, InterviewMessage.role == "user",
            InterviewMessage.round_number == round_number,
        ))
        if duplicate and duplicate.submission_id != data.submission_id:
            raise HTTPException(status_code=409, detail="本轮已有回答正在处理，请刷新会话") from None
        raise

    record = owned_record(db, practice_id, user)
    existing = db.scalars(_message_query(record.id)).all()
    conversation = [{"role": item.role, "content": item.content} for item in existing if item.delivery_status == "sent"]
    conversation.append({"role": "user", "content": data.content})
    evaluated_step = answered
    evaluated_phase = PHASE_PLAN[evaluated_step]
    final_turn = round_number >= TOTAL_QUESTIONS
    next_step = TOTAL_QUESTIONS if final_turn else round_number
    next_phase = PHASE_PLAN[min(next_step, TOTAL_QUESTIONS - 1)]
    try:
        result = validate_interview_turn(await ai_service.interview_respond(
            conversation, (db.get(InterviewScenario, record.scenario_id) or InterviewScenario(difficulty="intermediate")).difficulty,
            phase=next_phase, evaluated_phase=evaluated_phase, final_turn=final_turn,
            images=images or None,
        ))
    except Exception as exc:
        failed = db.get(InterviewMessage, user_message.id)
        if failed:
            failed.delivery_status = "failed"
            db.commit()
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc

    user_message = db.get(InterviewMessage, user_message.id)
    user_message.delivery_status = "sent"
    evaluation = _update_evaluation(record, result.get("observations", {}))
    public_evaluation = _public_evaluation(evaluation)
    record.current_step = round_number
    record.current_phase = next_phase
    record.total_rounds = round_number
    if final_turn:
        record.status = "awaiting_report"
    current_question = None if final_turn else round_number + 1
    turn_state = {
        "status": record.status, "phase": next_phase, "phase_index": min(round_number, TOTAL_QUESTIONS - 1),
        "answered_count": round_number, "current_question_number": current_question,
        "is_completed": final_turn,
    }
    analysis = {
        "comment": result.get("comment", ""), "phase": next_phase, "evaluated_phase": evaluated_phase,
        "follow_up_type": result.get("follow_up_type", ""), "scenario": result.get("scenario", ""),
        "observations": result.get("observations", {}), "live_evaluation": public_evaluation,
        "snapshot_scores": {name: row["score"] for name, row in public_evaluation["dimensions"].items() if row["score"] is not None},
        "turn_state": turn_state,
    }
    ai_message = InterviewMessage(
        record_id=record.id, role="ai", content=result.get("question", "本次谈话已完成。" if final_turn else "请继续。"),
        round_number=round_number, submission_id=data.submission_id, delivery_status="sent",
        analysis_json=json.dumps(analysis, ensure_ascii=False),
    )
    db.add(ai_message)
    db.commit()
    return {"code": 0, "data": _turn_payload(record, user_message, ai_message)}


@router.post("/practice/{practice_id}/end")
async def end_practice(practice_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    if record.report_json:
        return {"code": 0, "data": _json(record.report_json, {})}
    if record.is_legacy or record.flow_version != FLOW_VERSION:
        raise HTTPException(status_code=409, detail="旧版未完成谈话不能生成新版报告，请重新开始练习")
    messages = db.scalars(_message_query(record.id)).all()
    answered = _sync_progress(record, messages)
    if answered != TOTAL_QUESTIONS:
        raise HTTPException(status_code=400, detail=f"完成全部{TOTAL_QUESTIONS}题谈话后才能生成完整报告")

    cutoff = datetime.utcnow() - timedelta(minutes=2)
    claimed = db.execute(update(InterviewPracticeRecord).where(
        InterviewPracticeRecord.id == record.id,
        InterviewPracticeRecord.report_json.is_(None),
        or_(InterviewPracticeRecord.report_status != "generating", InterviewPracticeRecord.report_started_at < cutoff),
    ).values(report_status="generating", report_started_at=datetime.utcnow())).rowcount
    db.commit()
    if not claimed:
        refreshed = owned_record(db, practice_id, user)
        if refreshed.report_json:
            return {"code": 0, "data": _json(refreshed.report_json, {})}
        raise HTTPException(status_code=409, detail="报告正在生成，请稍后查看")

    conversation = [{"role": item.role, "content": item.content} for item in messages if item.delivery_status == "sent"]
    try:
        report = validate_interview_report(await ai_service.interview_report(conversation))
    except Exception as exc:
        db.execute(update(InterviewPracticeRecord).where(InterviewPracticeRecord.id == practice_id).values(report_status="failed", report_started_at=None))
        db.commit()
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc

    record = owned_record(db, practice_id, user)
    evaluation = _load_evaluation(record)
    scores = dict(report.get("dimension_scores", {}))
    for name in DIMENSIONS:
        row = evaluation["dimensions"][name]
        if row.get("raw_score") is not None and int(row.get("evidence_count", 0)) >= 2:
            scores[name] = int(row["raw_score"])
        else:
            scores[name] = max(0, min(100, int(scores.get(name, 0))))
    report["dimension_scores"] = scores
    analysis_by_name = {item.get("name"): item for item in report.get("dimension_analysis", []) if isinstance(item, dict)}
    report["dimension_analysis"] = [
        {**analysis_by_name.get(name, {}), "name": name, "score": scores[name], "suggestion": analysis_by_name.get(name, {}).get("suggestion", "继续积累具体事例与理论依据")}
        for name in DIMENSIONS
    ]
    report["overall_score"] = round(sum(scores.values()) / len(DIMENSIONS))
    report["grade"] = "优秀" if report["overall_score"] >= 85 else "良好" if report["overall_score"] >= 70 else "需努力"
    report["total_rounds"] = answered
    report["disclaimer"] = "AI 训练预估，不代表党组织正式评价"

    previous = db.scalar(select(InterviewPracticeRecord).where(
        InterviewPracticeRecord.user_id == user.id,
        InterviewPracticeRecord.scenario_id == record.scenario_id,
        InterviewPracticeRecord.status == "completed", InterviewPracticeRecord.id != record.id,
        InterviewPracticeRecord.total_rounds == TOTAL_QUESTIONS,
        InterviewPracticeRecord.report_json.is_not(None), *_valid_record_filter(),
    ).order_by(InterviewPracticeRecord.completed_at.desc()).limit(1))
    delta = {}
    if previous:
        previous_report = _json(previous.report_json, {})
        previous_scores = previous_report.get("dimension_scores", {})
        for name in DIMENSIONS:
            if name in previous_scores:
                delta[name] = scores[name] - int(previous_scores[name])
        delta["overall_score"] = report["overall_score"] - int(previous_report.get("overall_score", 0))
    report["delta"] = delta
    report["has_previous"] = bool(delta)

    payload = json.dumps(report, ensure_ascii=False)
    record.status = "completed"
    record.completed_at = datetime.utcnow()
    record.overall_score = report["overall_score"]
    record.report_json = payload
    record.report_status = "completed"
    record.report_started_at = None
    record.active_key = None
    existing_report = db.scalar(select(GeneratedReport).where(
        GeneratedReport.report_type == "interview", GeneratedReport.source_record_id == record.id,
    ))
    if not existing_report:
        scenario = db.get(InterviewScenario, record.scenario_id)
        db.add(GeneratedReport(
            user_id=user.id, report_type="interview", source_record_id=record.id,
            title=scenario.title if scenario else "入党谈话", score=record.overall_score, content_json=payload,
        ))
    award_points(
        db, user,
        module="interview", event_type="practice_completed", source_id=record.id,
        points=max(record.overall_score // 10, 1), description="完成入党谈话训练",
        metadata={"score": record.overall_score, "scenario_id": record.scenario_id},
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        winner = owned_record(db, practice_id, user)
        if winner.report_json:
            return {"code": 0, "data": _json(winner.report_json, {})}
        raise
    return {"code": 0, "data": report}


@router.get("/practice/{practice_id}/report")
def get_report(practice_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    if not record.report_json:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    return {"code": 0, "data": _json(record.report_json, {})}


@router.get("/practice/{practice_id}")
def get_practice(practice_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    scenario = db.get(InterviewScenario, record.scenario_id)
    messages = db.scalars(_message_query(record.id)).all()
    return {"code": 0, "data": _practice_payload(record, scenario, messages, resumed=True)}


@router.post("/practice/{practice_id}/hint")
async def get_hint(practice_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, practice_id, user)
    messages = db.scalars(_message_query(record.id)).all()
    last_ai_question = next((item.content for item in reversed(messages) if item.role == "ai" and item.delivery_status == "sent"), "")
    try:
        hint = await ai_service.interview_hint(last_ai_question)
    except Exception:
        hint = "可以先说明你的判断，再结合一个具体经历或理论依据展开。"
    return {"code": 0, "data": {"hint": hint}}


@router.get("/history")
def get_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(InterviewPracticeRecord).where(
        InterviewPracticeRecord.user_id == user.id,
    ).order_by(InterviewPracticeRecord.started_at.desc())).all()
    scenarios = {row.id: row for row in db.scalars(select(InterviewScenario)).all()}
    data = []
    for row in rows:
        messages = db.scalars(_message_query(row.id)).all()
        answered = _sync_progress(row, messages)
        scenario = scenarios.get(row.scenario_id)
        data.append({
            "id": row.id, "scenario_id": row.scenario_id,
            "requested_scenario_id": row.requested_scenario_id,
            "scenario_title": scenario.title if scenario else "谈话练习",
            "status": row.status, "phase": row.current_phase,
            "question_index": None if answered >= TOTAL_QUESTIONS else answered + 1,
            "answered_count": answered, "total_questions": TOTAL_QUESTIONS,
            "score": row.overall_score, "rounds": answered,
            "flow_version": row.flow_version, "is_legacy": bool(row.is_legacy),
            "has_report": bool(row.report_json), "report_status": row.report_status,
            "started_at": row.started_at.isoformat(),
        })
    return {"code": 0, "data": data}
