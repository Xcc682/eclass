"""用户路由：个人资料、成长指数、积分明细、成就与历史报告。"""
import json
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.debate import DebatePracticeRecord, DebateTopic
from app.models.domain import GeneratedReport, TourRecord, TourSite
from app.models.history import HistoryLearningRecord, HistoryScenario
from app.models.immersive import ImmersiveBook, ImmersiveProgress, ImmersiveSpread
from app.models.interview import InterviewPracticeRecord, InterviewScenario
from app.models.user import User
from app.routers.auth import user_payload
from app.security import get_current_user
from app.services.point_service import POINT_MODULES, point_summary

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


FORMAL_REPORT_TYPES = {"interview", "debate", "tour"}


def _valid_interviews(db: Session, user_id: str) -> list[InterviewPracticeRecord]:
    return list(db.scalars(select(InterviewPracticeRecord).where(
        InterviewPracticeRecord.user_id == user_id,
        InterviewPracticeRecord.status == "completed",
        InterviewPracticeRecord.flow_version == 2,
        InterviewPracticeRecord.is_legacy.is_(False),
        InterviewPracticeRecord.total_rounds == 6,
        InterviewPracticeRecord.report_json.is_not(None),
    )).all())


def _valid_debates(db: Session, user_id: str) -> list[DebatePracticeRecord]:
    return list(db.scalars(select(DebatePracticeRecord).where(
        DebatePracticeRecord.user_id == user_id,
        DebatePracticeRecord.status == "completed",
        DebatePracticeRecord.flow_version == 2,
        DebatePracticeRecord.is_legacy.is_(False),
        DebatePracticeRecord.feedback_json.is_not(None),
        or_(
            (DebatePracticeRecord.mode == "quick") & (DebatePracticeRecord.total_rounds == 4),
            (DebatePracticeRecord.mode == "full") & (DebatePracticeRecord.total_rounds == 6),
        ),
    )).all())


def _completed_tours(db: Session, user_id: str) -> list[TourRecord]:
    return list(db.scalars(select(TourRecord).where(
        TourRecord.user_id == user_id,
        TourRecord.completed.is_(True),
        TourRecord.report != "",
    )).all())


def _formal_report_payloads(
    db: Session, user_id: str, scope: Literal["current", "legacy"] = "current",
) -> list[dict]:
    generated = {
        (row.report_type, row.source_record_id): row
        for row in db.scalars(select(GeneratedReport).where(
            GeneratedReport.user_id == user_id,
            GeneratedReport.report_type.in_(FORMAL_REPORT_TYPES),
            GeneratedReport.source_record_id.is_not(None),
        )).all()
    }
    scenarios = {row.id: row for row in db.scalars(select(InterviewScenario)).all()}
    topics = {row.id: row for row in db.scalars(select(DebateTopic)).all()}
    sites = {row.id: row for row in db.scalars(select(TourSite)).all()}
    if scope == "legacy":
        interviews = list(db.scalars(select(InterviewPracticeRecord).where(
            InterviewPracticeRecord.user_id == user_id,
            or_(InterviewPracticeRecord.is_legacy.is_(True), InterviewPracticeRecord.flow_version != 2),
        )).all())
        interviews = [row for row in interviews if row.report_json or ("interview", row.id) in generated]
        debates = list(db.scalars(select(DebatePracticeRecord).where(
            DebatePracticeRecord.user_id == user_id,
            or_(DebatePracticeRecord.is_legacy.is_(True), DebatePracticeRecord.flow_version != 2),
        )).all())
        debates = [row for row in debates if row.feedback_json or ("debate", row.id) in generated]
        tours: list[TourRecord] = []
    else:
        interviews = _valid_interviews(db, user_id)
        debates = _valid_debates(db, user_id)
        tours = _completed_tours(db, user_id)

    payloads: list[dict] = []
    for record in interviews:
        report = generated.get(("interview", record.id))
        scenario = scenarios.get(record.scenario_id)
        payloads.append({
            "id": report.id if report else f"interview:{record.id}", "type": "interview",
            "title": report.title if report else scenario.title if scenario else "入党谈话报告",
            "score": record.overall_score, "content": report.content_json if report else record.report_json or "{}",
            "source_record_id": record.id, "is_legacy": scope == "legacy",
            "context": {"practice_id": record.id, "scenario_id": record.scenario_id},
            "created_at": _iso(record.completed_at or record.started_at),
        })
    for record in debates:
        report = generated.get(("debate", record.id))
        topic = topics.get(record.topic_id)
        payloads.append({
            "id": report.id if report else f"debate:{record.id}", "type": "debate",
            "title": report.title if report else topic.title if topic else "思政辩论报告",
            "score": record.overall_score, "content": report.content_json if report else record.feedback_json or "{}",
            "source_record_id": record.id, "is_legacy": scope == "legacy",
            "context": {
                "session_id": record.id, "topic_id": record.topic_id,
                "topic_title": topic.title if topic else "思政辩论报告",
                "stance": record.stance, "mode": record.mode,
            },
            "created_at": _iso(record.completed_at or record.started_at),
        })
    for record in tours:
        report = generated.get(("tour", record.id))
        site = sites.get(record.site_id)
        payloads.append({
            "id": report.id if report else f"tour:{record.id}", "type": "tour",
            "title": report.title if report else f"{site.name if site else '红色研学'}研学报告",
            "score": report.score if report else None,
            "content": report.content_json if report else json.dumps({"report": record.report}, ensure_ascii=False),
            "source_record_id": record.id, "is_legacy": False,
            "context": {
                "record_id": record.id, "site_id": record.site_id,
                "site_name": site.name if site else "红色研学",
            },
            "created_at": _iso(record.completed_at or record.created_at),
        })
    payloads.sort(key=lambda row: row["created_at"], reverse=True)
    return payloads


MODULE_DEFINITIONS = {
    "interview": {"label": "入党谈话", "weight": 30, "description": "沟通表达、理论理解与情境应对"},
    "debate": {"label": "思政辩论", "weight": 30, "description": "论证结构、知识运用与思辨深度"},
    "history": {"label": "党史情景", "weight": 20, "description": "历史脉络、关键事件与理论素养"},
    "tour": {"label": "红色研学", "weight": 20, "description": "现场观察、实践理解与研学反思"},
}
LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")


def _average(values: list[int | float]) -> int | None:
    valid = [float(value) for value in values if value is not None]
    return round(sum(valid) / len(valid)) if valid else None


def _level(score: int) -> str:
    if score >= 85:
        return "精研"
    if score >= 65:
        return "熟练"
    if score >= 35:
        return "进阶"
    if score > 0:
        return "起步"
    return "待开启"


def _dimension_average(values: dict[str, list[int]], *names: str) -> int | None:
    scores = [score for name in names for score in values.get(name, [])]
    return _average(scores)


def _weighted_evidence(signals: list[tuple[int | None, float, str]]) -> tuple[int, list[str]]:
    available = [(value, weight, label) for value, weight, label in signals if value is not None]
    if not available:
        return 0, []
    denominator = sum(weight for _, weight, _ in available)
    score = round(sum(int(value) * weight for value, weight, _ in available) / denominator)
    return score, [label for _, _, label in available]


def _local_date(value: datetime) -> date:
    utc_value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return utc_value.astimezone(LOCAL_TIMEZONE).date()


def growth_payload(db: Session, user: User) -> dict:
    interviews = _valid_interviews(db, user.id)
    debates = _valid_debates(db, user.id)
    history_rows = db.scalars(select(HistoryLearningRecord).where(
        HistoryLearningRecord.user_id == user.id,
        HistoryLearningRecord.completed.is_(True),
    )).all()
    tour_rows = _completed_tours(db, user.id)
    histories = list({row.scenario_id: row for row in history_rows}.values())
    tours = list({row.site_id: row for row in tour_rows}.values())
    current_reports = _formal_report_payloads(db, user.id, "current")
    legacy_reports = _formal_report_payloads(db, user.id, "legacy")
    dimension_values: dict[str, dict[str, list[int]]] = {"interview": {}, "debate": {}}
    for report in current_reports:
        if report["type"] not in dimension_values:
            continue
        try:
            report_data = json.loads(report["content"] or "{}") if isinstance(report["content"], str) else report["content"]
        except (TypeError, json.JSONDecodeError):
            report_data = {}
        scores = report_data.get("dimension_scores", {}) if isinstance(report_data, dict) else {}
        if not isinstance(scores, dict):
            continue
        for name, value in scores.items():
            try:
                score = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= score <= 100:
                dimension_values[report["type"]].setdefault(str(name), []).append(score)

    interview_dimensions = dimension_values["interview"]
    debate_dimensions = dimension_values["debate"]
    interview_scores = [row.overall_score for row in interviews if row.overall_score is not None]
    debate_scores = [row.overall_score for row in debates if row.overall_score is not None]
    history_total = int(db.scalar(select(func.count()).select_from(HistoryScenario)) or 0)
    tour_total = int(db.scalar(select(func.count()).select_from(TourSite)) or 0)
    history_mastery = round(min(len(histories) / history_total, 1) * 100) if history_total else 0
    tour_mastery = round(min(len(tours) / tour_total, 1) * 100) if tour_total else 0
    point_data = point_summary(db, user)

    module_scores = {
        "interview": _average(interview_scores) or 0,
        "debate": _average(debate_scores) or 0,
        "history": history_mastery,
        "tour": tour_mastery,
    }
    completed_counts = {
        "interview": len(interviews), "debate": len(debates),
        "history": len(histories), "tour": len(tours),
    }
    total_available = {"interview": None, "debate": None, "history": history_total, "tour": tour_total}
    module_growth = []
    for key in POINT_MODULES:
        definition = MODULE_DEFINITIONS[key]
        score = module_scores[key]
        module_growth.append({
            "key": key,
            "label": definition["label"],
            "description": definition["description"],
            "weight": definition["weight"],
            "points": point_data["by_module"].get(key, 0),
            "completed_count": completed_counts[key],
            "total_available": total_available[key],
            "mastery_score": score,
            "average_score": _average(interview_scores) if key == "interview" else _average(debate_scores) if key == "debate" else None,
            "level": _level(score),
        })

    growth_index = round(sum(
        module_scores[key] * MODULE_DEFINITIONS[key]["weight"] / 100 for key in POINT_MODULES
    ))
    covered_modules = sum(1 for key in POINT_MODULES if completed_counts[key] > 0)

    theoretical_score, theoretical_evidence = _weighted_evidence([
        (_dimension_average(interview_dimensions, "理论掌握"), .55, "谈话·理论掌握"),
        (history_mastery if histories else None, .45, "党史情景完成度"),
    ])
    communication_score, communication_evidence = _weighted_evidence([
        (_dimension_average(interview_dimensions, "表达逻辑"), .5, "谈话·表达逻辑"),
        (_dimension_average(debate_dimensions, "语言表达"), .5, "辩论·语言表达"),
    ])
    critical_score, critical_evidence = _weighted_evidence([
        (_dimension_average(interview_dimensions, "思想认识"), .25, "谈话·思想认识"),
        (_dimension_average(debate_dimensions, "逻辑严谨性", "知识运用", "思辨深度"), .75, "辩论·论证与思辨"),
    ])
    practice_score, practice_evidence = _weighted_evidence([
        (_dimension_average(interview_dimensions, "应变能力"), .4, "谈话·应变能力"),
        (tour_mastery if tours else None, .6, "红色研学完成度"),
    ])
    ability_dimensions = [
        {"name": "理论素养", "score": theoretical_score, "evidence": theoretical_evidence},
        {"name": "表达沟通", "score": communication_score, "evidence": communication_evidence},
        {"name": "思辨能力", "score": critical_score, "evidence": critical_evidence},
        {"name": "实践认知", "score": practice_score, "evidence": practice_evidence},
    ]

    activity_dates = {
        _local_date(value)
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
    for report in current_reports[:30]:
        activities.append({
            "id": report["id"],
            "type": report["type"],
            "title": f"完成{report['title']}",
            "score": report["score"],
            "time": report["created_at"],
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
    return {
        "total_interviews": len(interviews),
        "total_history_scenarios": len(histories),
        "total_debates": len(debates),
        "total_tours": len(tours),
        "total_reports": len(current_reports) + len(legacy_reports),
        "current_reports": len(current_reports),
        "legacy_interviews": int(db.scalar(select(func.count()).select_from(InterviewPracticeRecord).where(
            InterviewPracticeRecord.user_id == user.id, InterviewPracticeRecord.is_legacy.is_(True),
            InterviewPracticeRecord.report_json.is_not(None),
        )) or 0),
        "legacy_debates": int(db.scalar(select(func.count()).select_from(DebatePracticeRecord).where(
            DebatePracticeRecord.user_id == user.id, DebatePracticeRecord.is_legacy.is_(True),
            DebatePracticeRecord.feedback_json.is_not(None),
        )) or 0),
        "total_points": user.total_points,
        "average_interview_score": round(sum(interview_scores) / len(interview_scores)) if interview_scores else None,
        "streak_days": streak_days,
        "rank": rank,
        "ability_dimensions": ability_dimensions,
        "ability_profile": {
            "dimensions": ability_dimensions,
            "coverage": round(covered_modules / len(POINT_MODULES) * 100),
            "disclaimer": "综合能力来自有效训练证据，不等同于积分，也不作为正式组织评价。",
        },
        "module_growth": module_growth,
        "growth_index": {
            "score": growth_index,
            "coverage": round(covered_modules / len(POINT_MODULES) * 100),
            "covered_modules": covered_modules,
            "total_modules": len(POINT_MODULES),
            "weights": {key: MODULE_DEFINITIONS[key]["weight"] for key in POINT_MODULES},
            "method": "谈话30% + 辩论30% + 党史20% + 研学20%",
        },
        "point_summary": point_data,
        "activities": activities[:30],
    }


@router.get("/profile")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = user_payload(user)
    data["growth"] = growth_payload(db, user)
    data["features"] = {
        "notifications_available": True,
        "yiban_binding_available": False,
        "yiban_bound": bool(user.yiban_id),
    }
    return {"code": 0, "data": data}


@router.put("/profile")
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(user, key, value)
    payload = user_payload(user)
    payload["growth"] = growth_payload(db, user)
    payload["features"] = {
        "notifications_available": True,
        "yiban_binding_available": False,
        "yiban_bound": bool(user.yiban_id),
    }
    return {"code": 0, "data": payload, "message": "更新成功"}


@router.get("/growth")
def get_growth(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"code": 0, "data": growth_payload(db, user)}


@router.get("/points")
def get_points(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"code": 0, "data": point_summary(db, user, limit=50)}


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


def _iso(value: datetime | None) -> str:
    return (value or datetime.utcnow()).isoformat()


@router.get("/practices")
def get_practices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    formal_reports = list(db.scalars(select(GeneratedReport).where(
        GeneratedReport.user_id == user.id,
        GeneratedReport.report_type.in_(FORMAL_REPORT_TYPES),
    )).all())
    report_sources = {
        report.report_type: {
            row.source_record_id for row in formal_reports
            if row.report_type == report.report_type and row.source_record_id
        }
        for report in formal_reports
    }
    for report_type in FORMAL_REPORT_TYPES:
        report_sources.setdefault(report_type, set())

    scenarios = {row.id: row for row in db.scalars(select(InterviewScenario)).all()}
    topics = {row.id: row for row in db.scalars(select(DebateTopic)).all()}
    sites = {row.id: row for row in db.scalars(select(TourSite)).all()}
    items: list[dict] = []

    interviews = db.scalars(select(InterviewPracticeRecord).where(
        InterviewPracticeRecord.user_id == user.id,
    )).all()
    for row in interviews:
        has_report = row.id in report_sources["interview"] or bool(row.report_json)
        answered = max(0, min(int(row.total_rounds or 0), 6))
        is_legacy = bool(row.is_legacy or row.flow_version != 2)
        if is_legacy:
            status = "legacy"
        elif row.status == "completed" and has_report and answered == 6:
            status = "completed"
        elif row.status == "completed" or answered >= 6:
            status = "awaiting_report"
        else:
            status = "in_progress"
        scenario = scenarios.get(row.scenario_id)
        items.append({
            "id": row.id, "module": "interview", "source_id": row.scenario_id,
            "title": scenario.title if scenario else "入党谈话训练", "status": status,
            "score": row.overall_score, "completed_steps": answered, "total_steps": 6,
            "progress_percent": round(answered / 6 * 100), "has_report": has_report,
            "is_legacy": is_legacy, "updated_at": _iso(row.completed_at or row.started_at),
            "context": {"scenario_id": row.scenario_id, "practice_id": row.id},
        })

    debates = db.scalars(select(DebatePracticeRecord).where(
        DebatePracticeRecord.user_id == user.id,
    )).all()
    for row in debates:
        total = 4 if row.mode == "quick" else 6
        completed = max(0, min(int(row.total_rounds or 0), total))
        has_report = row.id in report_sources["debate"] or bool(row.feedback_json)
        is_legacy = bool(row.is_legacy or row.flow_version != 2)
        if is_legacy:
            status = "legacy"
        elif row.status == "completed" and has_report and completed == total:
            status = "completed"
        elif row.status == "awaiting_feedback" or row.status == "completed" or completed >= total:
            status = "awaiting_report"
        else:
            status = "in_progress"
        topic = topics.get(row.topic_id)
        items.append({
            "id": row.id, "module": "debate", "source_id": row.topic_id,
            "title": topic.title if topic else "思政辩论训练", "status": status,
            "score": row.overall_score, "completed_steps": completed, "total_steps": total,
            "progress_percent": round(completed / total * 100), "has_report": has_report,
            "is_legacy": is_legacy, "updated_at": _iso(row.completed_at or row.started_at),
            "context": {
                "topic_id": row.topic_id, "topic_title": topic.title if topic else "思政辩论训练",
                "session_id": row.id, "stance": row.stance, "mode": row.mode,
            },
        })

    books = {row.id: row for row in db.scalars(select(ImmersiveBook).where(
        ImmersiveBook.module.in_({"history", "tour"}),
    )).all()}
    spread_counts = dict(db.execute(select(
        ImmersiveSpread.book_id, func.count(ImmersiveSpread.id),
    ).group_by(ImmersiveSpread.book_id)).all())
    tour_records = {row.id: row for row in db.scalars(select(TourRecord).where(
        TourRecord.user_id == user.id,
    )).all()}
    seen_sources: set[tuple[str, str]] = set()
    progress_rows = db.scalars(select(ImmersiveProgress).where(
        ImmersiveProgress.user_id == user.id,
    )).all()
    for row in progress_rows:
        book = books.get(row.book_id)
        if not book:
            continue
        key = (book.module, book.source_id)
        seen_sources.add(key)
        total = max(int(spread_counts.get(book.id, 0)), 1)
        current = max(0, min(int(row.current_spread or 0), total - 1))
        percent = 100 if row.completed else round(current / max(total - 1, 1) * 100)
        related_tour = tour_records.get(row.related_record_id or "") if book.module == "tour" else None
        has_report = bool(related_tour and related_tour.completed and related_tour.report)
        if row.completed and (book.module == "history" or has_report):
            status = "completed"
        elif book.module == "tour" and current >= total - 1:
            status = "awaiting_report"
        else:
            status = "in_progress"
        items.append({
            "id": row.id, "module": book.module, "source_id": book.source_id,
            "title": book.title, "status": status, "score": None,
            "completed_steps": current + 1, "total_steps": total, "progress_percent": percent,
            "has_report": has_report, "is_legacy": False, "updated_at": _iso(row.updated_at),
            "context": {
                "book_id": book.id, "record_id": row.related_record_id,
                "site_id": book.source_id, "site_name": sites.get(book.source_id).name if sites.get(book.source_id) else book.title,
            },
        })

    history_rows = db.scalars(select(HistoryLearningRecord).where(
        HistoryLearningRecord.user_id == user.id,
    )).all()
    history_scenarios = {row.id: row for row in db.scalars(select(HistoryScenario)).all()}
    for row in history_rows:
        key = ("history", row.scenario_id)
        if key in seen_sources:
            continue
        seen_sources.add(key)
        scenario = history_scenarios.get(row.scenario_id)
        percent = max(0, min(int(row.progress or 0), 100))
        items.append({
            "id": row.id, "module": "history", "source_id": row.scenario_id,
            "title": scenario.title if scenario else "党史情景学习", "status": "completed" if row.completed else "in_progress",
            "score": None, "completed_steps": 1 if row.completed else 0, "total_steps": 1,
            "progress_percent": percent, "has_report": False, "is_legacy": False,
            "updated_at": _iso(row.completed_at or row.started_at),
            "context": {"book_id": f"history-{row.scenario_id}"},
        })

    for row in tour_records.values():
        key = ("tour", row.site_id)
        if key in seen_sources:
            continue
        site = sites.get(row.site_id)
        has_report = bool(row.completed and row.report)
        items.append({
            "id": row.id, "module": "tour", "source_id": row.site_id,
            "title": site.name if site else "红色研学", "status": "completed" if has_report else "in_progress",
            "score": None, "completed_steps": 1 if row.completed else 0, "total_steps": 1,
            "progress_percent": 100 if row.completed else 0, "has_report": has_report,
            "is_legacy": False, "updated_at": _iso(row.completed_at or row.created_at),
            "context": {
                "book_id": f"tour-{row.site_id}", "record_id": row.id,
                "site_id": row.site_id, "site_name": site.name if site else "红色研学",
            },
        })

    items.sort(key=lambda item: item["updated_at"], reverse=True)
    summary = {
        "total": len(items),
        "in_progress": sum(item["status"] == "in_progress" for item in items),
        "awaiting_report": sum(item["status"] == "awaiting_report" for item in items),
        "completed": sum(item["status"] == "completed" for item in items),
        "legacy": sum(item["is_legacy"] for item in items),
    }
    return {"code": 0, "data": {"summary": summary, "items": items}}


@router.get("/reports")
def get_reports(
    scope: Literal["current", "legacy"] = "current",
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    return {"code": 0, "data": _formal_report_payloads(db, user.id, scope)}
