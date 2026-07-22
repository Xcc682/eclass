import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.history import HistoryLearningRecord, HistoryScenario
from app.models.user import User
from app.security import get_current_user
from app.services.ai_service import ai_service, validate_generated_text

router = APIRouter(prefix="/api/v1/history", tags=["党史情景"])


class AskRequest(BaseModel):
    scenario_id: str
    question: str = Field(min_length=1, max_length=1000)


class ChoiceRequest(BaseModel):
    option_index: int = Field(ge=0, le=20)


def learning_record(db: Session, user: User, scenario_id: str, create: bool = False):
    record = db.scalar(select(HistoryLearningRecord).where(HistoryLearningRecord.user_id == user.id, HistoryLearningRecord.scenario_id == scenario_id))
    if not record and create:
        record = HistoryLearningRecord(user_id=user.id, scenario_id=scenario_id, progress=10)
        db.add(record); db.flush()
    return record


def payload(row: HistoryScenario, record: HistoryLearningRecord | None = None) -> dict:
    return {
        "id": row.id, "year": row.year_from, "era": row.era, "title": row.title,
        "description": row.description, "background": row.background or row.description,
        "duration": row.duration_estimate,
        "knowledge_points": json.loads(row.knowledge_points_json or "[]"),
        "decision_points": json.loads(row.decision_points_json or "{}"),
        "completed": bool(record and record.completed),
        "progress": record.progress if record else 0,
        "choice_index": record.choice_index if record else None,
        "qa_history": json.loads(record.qa_json or "[]") if record else [],
    }


@router.get("/scenarios")
def get_scenarios(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(HistoryScenario).order_by(HistoryScenario.order_index)).all()
    records = {record.scenario_id: record for record in db.scalars(select(HistoryLearningRecord).where(HistoryLearningRecord.user_id == user.id)).all()}
    return {"code": 0, "data": [payload(row, records.get(row.id)) for row in rows]}


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(HistoryScenario, scenario_id)
    if not row:
        raise HTTPException(status_code=404, detail="场景不存在")
    return {"code": 0, "data": payload(row, learning_record(db, user, scenario_id, create=True))}


@router.post("/ask")
async def ask_question(data: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scenario = db.get(HistoryScenario, data.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="场景不存在")
    try:
        context = f"{scenario.background}\n{scenario.description}\n{scenario.knowledge_points_json}"
        answer = validate_generated_text(await ai_service.history_ask(scenario.title, data.question, context), "党史回答")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    record = learning_record(db, user, scenario.id, create=True)
    history = json.loads(record.qa_json or "[]"); history.append({"q": data.question, "a": answer}); record.qa_json = json.dumps(history[-20:], ensure_ascii=False); record.progress = max(record.progress, 40)
    return {"code": 0, "data": {"answer": answer}}


@router.post("/scenarios/{scenario_id}/choice")
def save_choice(scenario_id: str, data: ChoiceRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    scenario = db.get(HistoryScenario, scenario_id)
    if not scenario: raise HTTPException(status_code=404, detail="场景不存在")
    options = json.loads(scenario.decision_points_json or "{}").get("options", [])
    if data.option_index >= len(options): raise HTTPException(status_code=422, detail="选项不存在")
    record = learning_record(db, user, scenario_id, create=True); record.choice_index = data.option_index; record.progress = max(record.progress, 70)
    return {"code": 0, "data": {"option_index": data.option_index, "feedback": options[data.option_index].get("feedback", ""), "progress": record.progress}}


@router.post("/scenarios/{scenario_id}/complete")
def complete_scenario(scenario_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(HistoryScenario, scenario_id):
        raise HTTPException(status_code=404, detail="场景不存在")
    record = learning_record(db, user, scenario_id, create=True)
    if record.choice_index is None:
        raise HTTPException(status_code=409, detail="请先完成情景选择，再进行学习打卡")
    if not record.completed:
        record.completed = True
        record.progress = 100
        record.completed_at = datetime.utcnow()
        user.total_points += 2
    return {"code": 0, "data": {"completed": True, "progress": 100}}


@router.get("/timeline")
def get_timeline(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(HistoryScenario).order_by(HistoryScenario.year_from)).all()
    records = {record.scenario_id: record for record in db.scalars(select(HistoryLearningRecord).where(HistoryLearningRecord.user_id == user.id)).all()}
    return {"code": 0, "data": [payload(row, records.get(row.id)) for row in rows]}
