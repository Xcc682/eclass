import json
from datetime import date, timedelta

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.debate import DebatePracticeRecord
from app.models.domain import GeneratedReport, TourRecord
from app.models.history import HistoryLearningRecord, HistoryScenario
from app.models.interview import InterviewPracticeRecord
from app.models.user import User
from app.routers.auth import user_payload
from app.security import get_current_user

router = APIRouter(prefix="/api/v1/users", tags=["用户"])


class ProfileUpdate(BaseModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=100)
    school: str | None = Field(default=None, max_length=100)
    college: str | None = Field(default=None, max_length=100)
    political_status: str | None = Field(default=None, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=512)


def count(db: Session, model, user_id: str, completed_only: bool = False) -> int:
    query = select(func.count()).select_from(model).where(model.user_id == user_id)
    if completed_only and hasattr(model, "completed"):
        query = query.where(model.completed.is_(True))
    return int(db.scalar(query) or 0)


def report_content(report: GeneratedReport) -> dict:
    try:
        value = json.loads(report.content_json or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def growth_payload(db: Session, user: User) -> dict:
    interviews = db.scalars(select(InterviewPracticeRecord).where(
        InterviewPracticeRecord.user_id == user.id,
        InterviewPracticeRecord.status == "completed",
    )).all()
    debates = db.scalars(select(DebatePracticeRecord).where(
        DebatePracticeRecord.user_id == user.id,
        DebatePracticeRecord.status == "completed",
    )).all()
    histories = db.scalars(select(HistoryLearningRecord).where(
        HistoryLearningRecord.user_id == user.id,
        HistoryLearningRecord.completed.is_(True),
    )).all()
    tours = db.scalars(select(TourRecord).where(
        TourRecord.user_id == user.id,
        TourRecord.completed.is_(True),
    )).all()
    reports = db.scalars(select(GeneratedReport).where(
        GeneratedReport.user_id == user.id,
    ).order_by(GeneratedReport.created_at.desc())).all()

    dimension_values: dict[str, list[int]] = {}
    for report in reports:
        scores = report_content(report).get("dimension_scores", {})
        if not isinstance(scores, dict):
            continue
        for name, value in scores.items():
            try:
                score = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= score <= 100:
                dimension_values.setdefault(str(name), []).append(score)
    ability_dimensions = [
        {"name": name, "score": round(sum(values) / len(values))}
        for name, values in dimension_values.items()
    ]

    activity_dates = {
        value.date()
        for value in [
            *(row.completed_at for row in interviews),
            *(row.completed_at for row in debates),
            *(row.completed_at for row in histories),
            *(row.completed_at for row in tours),
        ]
        if value is not None
    }
    streak_days = 0
    cursor = date.today()
    while cursor in activity_dates:
        streak_days += 1
        cursor -= timedelta(days=1)

    activities = []
    for report in reports[:30]:
        activities.append({
            "id": report.id,
            "type": report.report_type,
            "title": f"完成{report.title}",
            "score": report.score,
            "time": report.created_at.isoformat(),
        })
    for row in histories:
        scenario = db.get(HistoryScenario, row.scenario_id)
        if row.completed_at:
            activities.append({
                "id": row.id,
                "type": "history",
                "title": f"完成《{scenario.title if scenario else '党史情景'}》",
                "score": None,
                "time": row.completed_at.isoformat(),
            })
    activities.sort(key=lambda item: item["time"], reverse=True)
    rank = int(db.scalar(select(func.count()).select_from(User).where(User.total_points > user.total_points)) or 0) + 1
    interview_scores = [row.overall_score for row in interviews if row.overall_score is not None]
    return {
        "total_interviews": len(interviews),
        "total_history_scenarios": len(histories),
        "total_debates": len(debates),
        "total_tours": len(tours),
        "total_reports": len(reports),
        "total_points": user.total_points,
        "average_interview_score": round(sum(interview_scores) / len(interview_scores)) if interview_scores else None,
        "streak_days": streak_days,
        "rank": rank,
        "ability_dimensions": ability_dimensions,
        "activities": activities[:30],
    }


@router.get("/profile")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = user_payload(user)
    data["growth"] = growth_payload(db, user)
    return {"code": 0, "data": data}


@router.put("/profile")
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(user, key, value)
    payload = user_payload(user); payload["growth"] = growth_payload(db, user)
    return {"code": 0, "data": payload, "message": "更新成功"}


@router.get("/growth")
def get_growth(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"code": 0, "data": growth_payload(db, user)}


@router.get("/achievements")
def get_achievements(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    growth = growth_payload(db, user)
    definitions = [
        ("初次练习", "🎯", growth["total_interviews"] >= 1),
        ("理论达人", "📚", growth["total_history_scenarios"] >= 3),
        ("辩论能手", "⚡", growth["total_debates"] >= 1),
        ("研学先锋", "🏛️", growth["total_tours"] >= 1),
        ("学习先锋", "⭐", user.total_points >= 30),
    ]
    return {"code": 0, "data": [{"name": n, "icon": i, "earned": e} for n, i, e in definitions]}


@router.get("/reports")
def get_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reports = db.scalars(
        select(GeneratedReport).where(GeneratedReport.user_id == user.id).order_by(GeneratedReport.created_at.desc())
    ).all()
    return {"code": 0, "data": [
        {"id": r.id, "type": r.report_type, "title": r.title, "score": r.score, "content": r.content_json, "created_at": r.created_at.isoformat()}
        for r in reports
    ]}
