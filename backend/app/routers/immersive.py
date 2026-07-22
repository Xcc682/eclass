"""Unified API for the full-screen history and study-tour book readers."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.domain import GeneratedReport, TourRecord, TourSite
from app.models.history import HistoryLearningRecord, HistoryScenario
from app.models.immersive import ImmersiveBook, ImmersiveProgress, ImmersiveSpread
from app.models.user import User
from app.security import get_current_user
from app.services.ai_service import ai_service, validate_generated_text


router = APIRouter(prefix="/api/v1/immersive", tags=["沉浸式历史场景书"])
SPREAD_TYPES = {"cover", "cinematic", "exploration", "dialogue", "decision", "archive", "reflection", "ending"}


class ProgressRequest(BaseModel):
    current_spread: int | None = Field(default=None, ge=0, le=200)
    discovered_hotspot: str | None = Field(default=None, max_length=100)
    choice_spread_id: str | None = Field(default=None, max_length=100)
    choice_option_id: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=5000)
    sound_enabled: bool | None = None
    captions_enabled: bool | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    spread_id: str | None = Field(default=None, max_length=100)


def _loads(raw: str | None, fallback):
    try:
        return json.loads(raw or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _progress(db: Session, user: User, book: ImmersiveBook, create: bool = True) -> ImmersiveProgress | None:
    row = db.scalar(select(ImmersiveProgress).where(
        ImmersiveProgress.user_id == user.id,
        ImmersiveProgress.book_id == book.id,
    ))
    if not row and create:
        row = ImmersiveProgress(user_id=user.id, book_id=book.id)
        db.add(row)
        db.flush()
    return row


def _progress_payload(row: ImmersiveProgress | None) -> dict:
    return {
        "current_spread": row.current_spread if row else 0,
        "discovered_hotspots": _loads(row.discovered_json, []) if row else [],
        "choice": _loads(row.choice_json, {}) if row else {},
        "note": row.note if row else "",
        "qa_history": _loads(row.qa_json, []) if row else [],
        "sound_enabled": bool(row and row.sound_enabled),
        "captions_enabled": True if row is None else bool(row.captions_enabled),
        "completed": bool(row and row.completed),
        "related_record_id": row.related_record_id if row else None,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


def _spread_payload(row: ImmersiveSpread) -> dict:
    return {
        "id": row.id,
        "order_index": row.order_index,
        "type": row.spread_type,
        "layout": row.layout,
        "image_url": row.image_url,
        "thumbnail_url": row.thumbnail_url,
        "audio_url": row.audio_url,
        "narration": row.narration,
        "scene": _loads(row.scene_json, {}),
        "sources": _loads(row.source_refs_json, []),
    }


def _book_summary(row: ImmersiveBook, progress: ImmersiveProgress | None) -> dict:
    return {
        "id": row.id,
        "module": row.module,
        "source_id": row.source_id,
        "title": row.title,
        "subtitle": row.subtitle,
        "era": row.era,
        "location": row.location,
        "cover_url": row.cover_url,
        "version": row.version,
        "duration": row.duration_estimate,
        "order_index": row.order_index,
        "progress": _progress_payload(progress),
    }


def _published_book(db: Session, book_id: str) -> ImmersiveBook:
    book = db.get(ImmersiveBook, book_id)
    if not book or book.status != "published":
        raise HTTPException(status_code=404, detail="书卷不存在或尚未发布")
    return book


def _spreads(db: Session, book_id: str) -> list[ImmersiveSpread]:
    return list(db.scalars(select(ImmersiveSpread).where(ImmersiveSpread.book_id == book_id).order_by(ImmersiveSpread.order_index)).all())


@router.get("/books")
def list_books(module: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if module not in {"history", "tour"}:
        raise HTTPException(status_code=422, detail="module 仅支持 history 或 tour")
    books = list(db.scalars(select(ImmersiveBook).where(
        ImmersiveBook.module == module,
        ImmersiveBook.status == "published",
    ).order_by(ImmersiveBook.order_index)).all())
    progress_rows = {row.book_id: row for row in db.scalars(select(ImmersiveProgress).where(
        ImmersiveProgress.user_id == user.id,
        ImmersiveProgress.book_id.in_([book.id for book in books] or [""]),
    )).all()}
    return {"code": 0, "data": [_book_summary(book, progress_rows.get(book.id)) for book in books]}


@router.get("/books/{book_id}")
def get_book(book_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _published_book(db, book_id)
    progress = _progress(db, user, book)
    spreads = _spreads(db, book.id)
    if len(spreads) < 2 or any(row.spread_type not in SPREAD_TYPES for row in spreads):
        raise HTTPException(status_code=503, detail="书卷内容不完整，请联系内容管理员")
    return {"code": 0, "data": {**_book_summary(book, progress), "spreads": [_spread_payload(row) for row in spreads]}}


def _sync_history_choice(db: Session, user: User, book: ImmersiveBook, option_id: str) -> None:
    try:
        option_index = int(option_id.rsplit("-", 1)[-1])
    except (ValueError, IndexError):
        return
    record = db.scalar(select(HistoryLearningRecord).where(
        HistoryLearningRecord.user_id == user.id,
        HistoryLearningRecord.scenario_id == book.source_id,
    ))
    if not record:
        record = HistoryLearningRecord(user_id=user.id, scenario_id=book.source_id, progress=10)
        db.add(record)
    record.choice_index = option_index
    record.progress = max(record.progress or 0, 70)


@router.patch("/books/{book_id}/progress")
def update_progress(book_id: str, data: ProgressRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _published_book(db, book_id)
    spreads = _spreads(db, book.id)
    progress = _progress(db, user, book)
    assert progress is not None
    if data.current_spread is not None:
        if data.current_spread >= len(spreads):
            raise HTTPException(status_code=422, detail="页码超出书卷范围")
        progress.current_spread = data.current_spread
    if data.discovered_hotspot:
        valid_hotspots = {
            item.get("id")
            for spread in spreads
            for item in _loads(spread.scene_json, {}).get("hotspots", [])
        }
        if data.discovered_hotspot not in valid_hotspots:
            raise HTTPException(status_code=422, detail="场景线索不存在")
        discovered = set(_loads(progress.discovered_json, []))
        discovered.add(data.discovered_hotspot)
        progress.discovered_json = json.dumps(sorted(discovered), ensure_ascii=False)
    if data.choice_spread_id or data.choice_option_id:
        if not data.choice_spread_id or not data.choice_option_id:
            raise HTTPException(status_code=422, detail="选择页与选项必须同时提交")
        decision = next((row for row in spreads if row.id == data.choice_spread_id and row.spread_type == "decision"), None)
        options = _loads(decision.scene_json, {}).get("options", []) if decision else []
        if not any(item.get("id") == data.choice_option_id for item in options):
            raise HTTPException(status_code=422, detail="历史观察选项不存在")
        progress.choice_json = json.dumps({"spread_id": data.choice_spread_id, "option_id": data.choice_option_id}, ensure_ascii=False)
        if book.module == "history":
            _sync_history_choice(db, user, book, data.choice_option_id)
    if data.note is not None:
        progress.note = data.note.strip()
    if data.sound_enabled is not None:
        progress.sound_enabled = data.sound_enabled
    if data.captions_enabled is not None:
        progress.captions_enabled = data.captions_enabled
    progress.updated_at = datetime.utcnow()
    return {"code": 0, "data": _progress_payload(progress)}


@router.post("/books/{book_id}/ask")
async def ask_in_book(book_id: str, data: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _published_book(db, book_id)
    spreads = _spreads(db, book.id)
    spread = next((item for item in spreads if item.id == data.spread_id), None) if data.spread_id else spreads[min(len(spreads) - 1, _progress(db, user, book).current_spread)]
    if not spread:
        raise HTTPException(status_code=422, detail="当前跨页不存在")
    sources = _loads(spread.source_refs_json, [])
    scene = _loads(spread.scene_json, {})
    context = "\n".join(filter(None, [spread.narration, scene.get("archive_excerpt", ""), *(item.get("excerpt", "") for item in sources)]))
    try:
        if book.module == "history":
            answer = await ai_service.history_ask(book.title, data.question, context)
        else:
            grounded_question = f"请结合当前场景资料回答：{data.question}\n当前资料：{context}"
            answer = await ai_service.tour_ask(book.title, grounded_question)
        answer = validate_generated_text(answer, "场景问答")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 史官暂时无法回答：{exc}") from exc
    progress = _progress(db, user, book)
    history = _loads(progress.qa_json, [])
    history.append({"q": data.question, "a": answer, "spread_id": spread.id, "created_at": datetime.utcnow().isoformat()})
    progress.qa_json = json.dumps(history[-30:], ensure_ascii=False)
    progress.updated_at = datetime.utcnow()
    if book.module == "history":
        record = db.scalar(select(HistoryLearningRecord).where(
            HistoryLearningRecord.user_id == user.id,
            HistoryLearningRecord.scenario_id == book.source_id,
        ))
        if not record:
            record = HistoryLearningRecord(user_id=user.id, scenario_id=book.source_id, progress=10)
            db.add(record)
        record.qa_json = progress.qa_json
        record.progress = max(record.progress or 0, 40)
    else:
        record = db.get(TourRecord, progress.related_record_id) if progress.related_record_id else None
        if not record:
            record = TourRecord(user_id=user.id, site_id=book.source_id, qa_json="[]", completed=False)
            db.add(record)
            db.flush()
            progress.related_record_id = record.id
        record.qa_json = progress.qa_json
    return {"code": 0, "data": {"answer": answer, "qa_history": history[-30:]}}


@router.post("/books/{book_id}/complete")
async def complete_book(book_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _published_book(db, book_id)
    spreads = _spreads(db, book.id)
    progress = _progress(db, user, book)
    assert progress is not None
    if progress.completed:
        report = ""
        if progress.related_record_id:
            record = db.get(TourRecord, progress.related_record_id)
            report = record.report if record else ""
        return {"code": 0, "data": {"completed": True, "already_completed": True, "report": report, "record_id": progress.related_record_id}}
    if progress.current_spread < len(spreads) - 1:
        raise HTTPException(status_code=409, detail="请先翻阅至本卷最后一页")
    if not _loads(progress.discovered_json, []):
        raise HTTPException(status_code=409, detail="请先在场景中发现至少一处历史线索")

    now = datetime.utcnow()
    if book.module == "history":
        choice = _loads(progress.choice_json, {})
        if not choice.get("option_id"):
            raise HTTPException(status_code=409, detail="请先完成本卷的观察视角选择")
        scenario = db.get(HistoryScenario, book.source_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="关联党史场景不存在")
        record = db.scalar(select(HistoryLearningRecord).where(
            HistoryLearningRecord.user_id == user.id,
            HistoryLearningRecord.scenario_id == book.source_id,
        ))
        if not record:
            record = HistoryLearningRecord(user_id=user.id, scenario_id=book.source_id, progress=70)
            db.add(record)
        if not record.completed:
            record.completed = True
            record.progress = 100
            record.completed_at = now
            user.total_points += 2
        progress.completed = True
        progress.completed_at = now
        progress.updated_at = now
        return {"code": 0, "data": {"completed": True, "already_completed": False, "points": 2, "report": "", "record_id": None}}

    if len(progress.note.strip()) < 20 and not _loads(progress.qa_json, []):
        raise HTTPException(status_code=409, detail="请完成一次追问，或写下不少于 20 字的研学手记")
    site = db.get(TourSite, book.source_id)
    if not site:
        raise HTTPException(status_code=404, detail="关联研学点位不存在")
    qa = _loads(progress.qa_json, [])
    qa_lines = [f"Q:{row.get('q', '')} A:{row.get('a', '')}" for row in qa]
    if progress.note.strip():
        qa_lines.append(f"研学手记：{progress.note.strip()}")
    try:
        report_text = validate_generated_text(await ai_service.tour_report(site.name, qa_lines), "研学报告")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"报告生成失败，进度已保留且不会发放虚假积分：{exc}") from exc
    record = db.get(TourRecord, progress.related_record_id) if progress.related_record_id else None
    if not record:
        record = TourRecord(user_id=user.id, site_id=book.source_id, qa_json=progress.qa_json, completed=False)
        db.add(record)
        db.flush()
    record.qa_json = progress.qa_json
    record.report = report_text
    record.completed = True
    record.completed_at = now
    progress.related_record_id = record.id
    progress.completed = True
    progress.completed_at = now
    progress.updated_at = now
    user.total_points += 3
    db.add(GeneratedReport(
        user_id=user.id,
        report_type="tour",
        title=f"{site.name}研学报告",
        content_json=json.dumps({"report": report_text, "book_id": book.id, "note": progress.note}, ensure_ascii=False),
    ))
    return {"code": 0, "data": {"completed": True, "already_completed": False, "points": 3, "report": report_text, "record_id": record.id}}
