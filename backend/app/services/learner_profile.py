"""学员学习档案：把散落在各模块的练习记录汇总成可查询的画像。

知识问答里的自主检索 Agent 通过工具调用读取这里的数据，从而在回答中结合
「这个学生之前练过什么、哪里薄弱」给出针对性内容。所有查询都以当前用户为准，
按记录 ID 取详情时还会再校验归属，避免跨用户读取。
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.debate import DebateMessage, DebatePracticeRecord, DebateTopic
from app.models.domain import TourRecord, TourSite
from app.models.immersive import ImmersiveBook, ImmersiveProgress
from app.models.interview import InterviewMessage, InterviewPracticeRecord, InterviewScenario
from app.models.knowledge import KnowledgeMessage, KnowledgeSession

MODULE_LABELS = {
    "interview": "入党谈话",
    "debate": "思政辩论",
    "tour": "红色研学",
    "book": "党史书卷",
    "knowledge": "知识问答",
}

MODULE_ALIASES = {
    "interview": "interview", "谈话": "interview", "入党谈话": "interview",
    "debate": "debate", "辩论": "debate", "思政辩论": "debate",
    "tour": "tour", "研学": "tour", "红色研学": "tour",
    "book": "book", "书卷": "book", "immersive": "book", "党史书卷": "book",
    "knowledge": "knowledge", "问答": "knowledge", "知识问答": "knowledge",
}

SCAN_LIMIT = 40
DETAIL_TEXT_LIMIT = 240


def normalize_module(value: object) -> str | None:
    text = str(value or "").strip().lower()
    return MODULE_ALIASES.get(text)


def _loads(raw: object, fallback: object) -> object:
    if not raw:
        return fallback
    try:
        return json.loads(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


def _day(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d") if value else ""


def _clip(text: object, limit: int = DETAIL_TEXT_LIMIT) -> str:
    value = str(text or "").strip().replace("\n", " ")
    return value[:limit] + ("…" if len(value) > limit else "")


def _record(module: str, record_id: str, title: str, *, score: int | None,
            rounds: int | None, status: str, at: datetime | None, **extra: object) -> dict:
    item = {
        "module": module,
        "module_label": MODULE_LABELS[module],
        "record_id": record_id,
        "title": title,
        "score": score,
        "rounds": rounds,
        "status": status,
        "date": _day(at),
    }
    item.update({key: value for key, value in extra.items() if value not in (None, "")})
    return item


def collect_records(db: Session, user_id: str) -> list[dict]:
    """按时间倒序汇总用户在各模块的练习记录。"""
    items: list[dict] = []

    interview_rows = db.execute(
        select(InterviewPracticeRecord, InterviewScenario.title)
        .join(InterviewScenario, InterviewScenario.id == InterviewPracticeRecord.scenario_id)
        .where(InterviewPracticeRecord.user_id == user_id)
        .order_by(InterviewPracticeRecord.started_at.desc())
        .limit(SCAN_LIMIT)
    ).all()
    items += [
        _record("interview", row.id, title, score=row.overall_score, rounds=row.total_rounds,
                status=row.status, at=row.completed_at or row.started_at, phase=row.current_phase)
        for row, title in interview_rows
    ]

    debate_rows = db.execute(
        select(DebatePracticeRecord, DebateTopic.title)
        .join(DebateTopic, DebateTopic.id == DebatePracticeRecord.topic_id)
        .where(DebatePracticeRecord.user_id == user_id)
        .order_by(DebatePracticeRecord.started_at.desc())
        .limit(SCAN_LIMIT)
    ).all()
    items += [
        _record("debate", row.id, title, score=row.overall_score, rounds=row.total_rounds,
                status=row.status, at=row.completed_at or row.started_at,
                stance="正方" if row.stance == "pro" else "反方")
        for row, title in debate_rows
    ]

    tour_rows = db.execute(
        select(TourRecord, TourSite.name)
        .join(TourSite, TourSite.id == TourRecord.site_id)
        .where(TourRecord.user_id == user_id)
        .order_by(TourRecord.created_at.desc())
        .limit(SCAN_LIMIT)
    ).all()
    items += [
        _record("tour", row.id, title, score=None,
                rounds=len(_loads(row.qa_json, [])),
                status="completed" if row.completed else "in_progress",
                at=row.completed_at or row.created_at)
        for row, title in tour_rows
    ]

    book_rows = db.execute(
        select(ImmersiveProgress, ImmersiveBook.title)
        .join(ImmersiveBook, ImmersiveBook.id == ImmersiveProgress.book_id)
        .where(ImmersiveProgress.user_id == user_id)
        .order_by(ImmersiveProgress.updated_at.desc())
        .limit(SCAN_LIMIT)
    ).all()
    items += [
        _record("book", row.id, title, score=None, rounds=None,
                status="completed" if row.completed else "in_progress",
                at=row.completed_at or row.updated_at)
        for row, title in book_rows
    ]

    session_rows = db.execute(
        select(KnowledgeSession)
        .where(KnowledgeSession.user_id == user_id)
        .order_by(KnowledgeSession.updated_at.desc())
        .limit(SCAN_LIMIT)
    ).scalars().all()
    items += [
        _record("knowledge", row.id, row.title, score=None, rounds=None,
                status="completed", at=row.updated_at)
        for row in session_rows
    ]

    items.sort(key=lambda item: item["date"], reverse=True)
    return items


def _report_insights(db: Session, user_id: str) -> tuple[list[dict], str]:
    """从最近一份已完成的报告里提取最薄弱的维度与点评要点。"""
    for model, field in ((InterviewPracticeRecord, "report_json"), (DebatePracticeRecord, "feedback_json")):
        row = db.scalars(
            select(model)
            .where(model.user_id == user_id, model.status == "completed")
            .order_by(model.completed_at.desc())
            .limit(1)
        ).first()
        report = _loads(getattr(row, field, None), {}) if row else {}
        if not isinstance(report, dict) or not report:
            continue
        scores = report.get("dimension_scores")
        weakest: list[dict] = []
        if isinstance(scores, dict):
            parsed = [(name, value) for name, value in scores.items() if isinstance(value, int)]
            for name, value in sorted(parsed, key=lambda pair: pair[1])[:2]:
                weakest.append({"name": name, "score": value})
        advice = "；".join(str(item) for item in (report.get("weaknesses") or [])[:2])
        if advice:
            weakest.append({"name": "报告点评", "score": None, "note": _clip(advice)})
        return weakest, _clip(report.get("suggestion"), 160)
    return [], ""


def profile_summary(db: Session, user_id: str) -> dict:
    records = collect_records(db, user_id)
    modules: dict[str, dict] = {}
    for module, label in MODULE_LABELS.items():
        subset = [item for item in records if item["module"] == module]
        scores = [item["score"] for item in subset if isinstance(item["score"], int)]
        modules[module] = {
            "label": label,
            "count": len(subset),
            "completed": sum(1 for item in subset if item["status"] == "completed"),
            "average_score": round(sum(scores) / len(scores)) if scores else None,
            "last_date": subset[0]["date"] if subset else "",
        }
    weakest, advice = _report_insights(db, user_id)
    return {
        "total_practices": len(records),
        "modules": modules,
        "weakest_dimensions": weakest,
        "latest_advice": advice,
        "recent_practices": records[:5],
    }


def list_records(db: Session, user_id: str, module: str | None = None, limit: int = 8) -> dict:
    records = collect_records(db, user_id)
    if module:
        records = [item for item in records if item["module"] == module]
    return {"module": module or "全部", "records": records[:limit], "total": len(records)}


def _message_pairs(messages: list[dict], limit: int = 10) -> list[dict]:
    pairs: list[dict] = []
    pending_question = ""
    for item in messages:
        text = _clip(item["content"])
        if item["role"] == "user":
            pairs.append({"question": pending_question, "answer": text})
            pending_question = ""
        else:
            pending_question = text
    return [pair for pair in pairs if pair["answer"]][-limit:]


def record_detail(db: Session, user_id: str, module: str, record_id: str) -> dict:
    """取一次练习的关键内容；记录不属于当前用户时一律当作不存在。"""
    if module == "interview":
        row = db.get(InterviewPracticeRecord, record_id)
        if not row or row.user_id != user_id:
            return {"error": "练习记录不存在"}
        messages = db.scalars(
            select(InterviewMessage).where(InterviewMessage.record_id == row.id)
            .order_by(InterviewMessage.created_at).limit(40)
        ).all()
        report = _loads(row.report_json, {})
        scenario = db.get(InterviewScenario, row.scenario_id)
        return {
            "module": "interview",
            "title": scenario.title if scenario else "",
            "status": row.status,
            "score": row.overall_score,
            "turns": _message_pairs([{"role": m.role, "content": m.content} for m in messages]),
            "weaknesses": (report.get("weaknesses") or [])[:3] if isinstance(report, dict) else [],
        }
    if module == "debate":
        row = db.get(DebatePracticeRecord, record_id)
        if not row or row.user_id != user_id:
            return {"error": "练习记录不存在"}
        messages = db.scalars(
            select(DebateMessage).where(DebateMessage.record_id == row.id)
            .order_by(DebateMessage.created_at).limit(40)
        ).all()
        feedback = _loads(row.feedback_json, {})
        topic = db.get(DebateTopic, row.topic_id)
        return {
            "module": "debate",
            "title": topic.title if topic else "",
            "stance": "正方" if row.stance == "pro" else "反方",
            "status": row.status,
            "score": row.overall_score,
            "turns": _message_pairs([{"role": m.role, "content": m.content} for m in messages]),
            "weaknesses": (feedback.get("weaknesses") or [])[:3] if isinstance(feedback, dict) else [],
        }
    if module == "tour":
        row = db.get(TourRecord, record_id)
        if not row or row.user_id != user_id:
            return {"error": "练习记录不存在"}
        site = db.get(TourSite, row.site_id)
        qa = _loads(row.qa_json, [])
        return {
            "module": "tour",
            "title": site.name if site else "",
            "status": "completed" if row.completed else "in_progress",
            "turns": [
                {"question": _clip(item.get("question") or item.get("q")),
                 "answer": _clip(item.get("answer") or item.get("a"))}
                for item in qa[-8:] if isinstance(item, dict)
            ],
            "report": _clip(row.report, 400),
        }
    if module == "book":
        row = db.get(ImmersiveProgress, record_id)
        if not row or row.user_id != user_id:
            return {"error": "练习记录不存在"}
        book = db.get(ImmersiveBook, row.book_id)
        discovered = _loads(row.discovered_json, [])
        return {
            "module": "book",
            "title": book.title if book else "",
            "status": "completed" if row.completed else "in_progress",
            "clues_found": len(discovered) if isinstance(discovered, list) else 0,
            "note": _clip(row.note, 300),
        }
    if module == "knowledge":
        row = db.get(KnowledgeSession, record_id)
        if not row or row.user_id != user_id:
            return {"error": "练习记录不存在"}
        messages = db.scalars(
            select(KnowledgeMessage).where(KnowledgeMessage.session_id == row.id)
            .order_by(KnowledgeMessage.created_at.desc()).limit(8)
        ).all()
        return {
            "module": "knowledge",
            "title": row.title,
            "questions": [_clip(m.content, 120) for m in reversed(messages) if m.role == "user"],
        }
    return {"error": "未知模块"}


def interview_context(db: Session, user_id: str) -> str:
    """给谈话考官的一段背景：历史练习与薄弱点，长度有上界。"""
    summary = profile_summary(db, user_id)
    modules = summary["modules"]
    parts: list[str] = []
    done = modules["interview"]
    if done["count"]:
        avg = f"，平均 {done['average_score']} 分" if done["average_score"] else ""
        parts.append(f"此前参加过 {done['count']} 次入党谈话{avg}")
    weak = [item for item in summary["weakest_dimensions"] if item.get("score") is not None]
    if weak:
        parts.append("上次报告中较薄弱的维度：" + "、".join(f"{item['name']}（{item['score']}）" for item in weak))
    if summary["latest_advice"]:
        parts.append(f"上次建议：{summary['latest_advice']}")
    others = [m for m in ("debate", "tour", "book") if modules[m]["count"]]
    if others:
        parts.append("其他练习：" + "、".join(f"{modules[m]['label']} {modules[m]['count']} 次" for m in others))
    if not parts:
        return ""
    return (
        "以下是该学员的历史练习记录（由系统从数据库读取，可能为空）："
        + "；".join(parts)
        + "。请据此调整提问：优先追问此前答得薄弱的方面，避免重复已充分考察的问题；"
        "不要向学生透露这些记录的存在方式，也不要编造记录之外的内容。"
    )[:600]
