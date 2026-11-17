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
from app.services.point_service import award_points

router = APIRouter(prefix="/api/v1/immersive", tags=["沉浸式历史场景书"])
SPREAD_TYPES = {"cover", "cinematic", "exploration", "dialogue", "decision", "detour", "archive", "reflection", "ending"}
BRANCH_FLOW_VERSION = 5


class ProgressRequest(BaseModel):
    current_spread: int | None = Field(default=None, ge=0, le=200)
    discovered_hotspot: str | None = Field(default=None, max_length=100)
    choice_spread_id: str | None = Field(default=None, max_length=100)
    choice_option_id: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=5000)
    sound_enabled: bool | None = None
    captions_enabled: bool | None = None


class ChoiceRequest(BaseModel):
    decision_spread_id: str = Field(min_length=1, max_length=100)
    option_id: str = Field(min_length=1, max_length=100)
    submission_id: str = Field(min_length=8, max_length=100)


class AdvanceRequest(BaseModel):
    from_spread_id: str = Field(min_length=1, max_length=100)
    direction: str = Field(pattern=r"^(next|back|jump)$")
    target_spread_id: str | None = Field(default=None, max_length=100)


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


def _graph(book: ImmersiveBook) -> dict:
    return _loads(book.graph_json, {})


def _ensure_route_state(row: ImmersiveProgress, book: ImmersiveBook, spreads: list[ImmersiveSpread]) -> dict:
    graph = _graph(book)
    start = graph.get("start") or (spreads[0].id if spreads else "")
    ending = graph.get("ending") or (spreads[-1].id if spreads else "")
    state = _loads(row.route_state_json, {})
    if row.completed:
        state.setdefault("current", ending)
        state.setdefault("visited", [ending])
        state.setdefault("unlocked", [ending])
        state.setdefault("solved_decisions", list(graph.get("required_decisions", [])))
    elif row.flow_version < BRANCH_FLOW_VERSION or not state.get("current"):
        state = {
            "current": start, "visited": [start], "unlocked": [start], "trail": [],
            "solved_decisions": [], "decisions": {}, "attempts": {}, "wrong_routes": [],
            "submissions": {},
        }
    for key, fallback in (
        ("visited", []), ("unlocked", []), ("trail", []), ("solved_decisions", []),
        ("decisions", {}), ("attempts", {}), ("wrong_routes", []), ("submissions", {}),
    ):
        state.setdefault(key, fallback)
    valid_ids = {spread.id for spread in spreads}
    if state.get("current") not in valid_ids:
        state["current"] = ending if row.completed else start
    row.current_spread_id = state["current"]
    row.flow_version = BRANCH_FLOW_VERSION
    row.route_state_json = json.dumps(state, ensure_ascii=False)
    index_by_id = {spread.id: index for index, spread in enumerate(spreads)}
    row.current_spread = index_by_id.get(state["current"], 0)
    return state


def _progress_payload(row: ImmersiveProgress | None, book: ImmersiveBook | None = None,
                      spreads: list[ImmersiveSpread] | None = None) -> dict:
    state = _ensure_route_state(row, book, spreads or []) if row and book and spreads is not None else {}
    graph = _graph(book) if book else {}
    solved = set(state.get("solved_decisions", []))
    milestones = [{**item, "solved": item.get("id") in solved} for item in graph.get("milestones", [])]
    return {
        "current_spread": row.current_spread if row else 0,
        "current_spread_id": state.get("current") or (row.current_spread_id if row else None),
        "discovered_hotspots": _loads(row.discovered_json, []) if row else [],
        "choice": _loads(row.choice_json, {}) if row else {},
        "route": {
            "visited_spread_ids": state.get("visited", []),
            "unlocked_spread_ids": state.get("unlocked", []),
            "solved_decisions": state.get("solved_decisions", []),
            "decisions": state.get("decisions", {}),
            "attempts": state.get("attempts", {}),
            "wrong_routes": state.get("wrong_routes", []),
            "milestones": milestones,
            "required_count": len(graph.get("required_decisions", [])),
            "solved_count": len(solved.intersection(graph.get("required_decisions", []))),
        },
        "flow_version": row.flow_version if row else BRANCH_FLOW_VERSION,
        "note": row.note if row else "",
        "qa_history": _loads(row.qa_json, []) if row else [],
        "sound_enabled": bool(row and row.sound_enabled),
        "captions_enabled": True if row is None else bool(row.captions_enabled),
        "completed": bool(row and row.completed),
        "related_record_id": row.related_record_id if row else None,
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


def _spread_payload(row: ImmersiveSpread) -> dict:
    scene = _loads(row.scene_json, {})
    if scene.get("options"):
        scene["options"] = [{"id": item.get("id"), "label": item.get("label", "")} for item in scene["options"]]
    return {
        "id": row.id,
        "order_index": row.order_index,
        "type": row.spread_type,
        "layout": row.layout,
        "image_url": row.image_url,
        "thumbnail_url": row.thumbnail_url,
        "audio_url": row.audio_url,
        "narration": row.narration,
        "scene": scene,
        "sources": _loads(row.source_refs_json, []),
    }


def _book_summary(row: ImmersiveBook, progress: ImmersiveProgress | None,
                  spreads: list[ImmersiveSpread] | None = None) -> dict:
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
        "progress": _progress_payload(progress, row, spreads) if spreads is not None else _progress_payload(progress),
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
    return {"code": 0, "data": [_book_summary(book, progress_rows.get(book.id), _spreads(db, book.id)) for book in books]}


@router.get("/books/{book_id}")
def get_book(book_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _published_book(db, book_id)
    progress = _progress(db, user, book)
    spreads = _spreads(db, book.id)
    if len(spreads) < 2 or any(row.spread_type not in SPREAD_TYPES for row in spreads):
        raise HTTPException(status_code=503, detail="书卷内容不完整，请联系内容管理员")
    return {"code": 0, "data": {**_book_summary(book, progress, spreads), "spreads": [_spread_payload(row) for row in spreads]}}


def _sync_history_choice(db: Session, user: User, book: ImmersiveBook, option_id: str) -> None:
    try:
        option_index = max(0, int(option_id.rsplit("-", 1)[-1]) - 1)
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
    state = _ensure_route_state(progress, book, spreads)
    if data.current_spread is not None:
        if book.version >= BRANCH_FLOW_VERSION and data.current_spread != progress.current_spread:
            raise HTTPException(status_code=409, detail="新版书卷必须通过路线接口翻页")
        if data.current_spread >= len(spreads):
            raise HTTPException(status_code=422, detail="页码超出书卷范围")
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
        if book.version >= BRANCH_FLOW_VERSION:
            raise HTTPException(status_code=409, detail="新版书卷请选择对应剧情路线")
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
    progress.route_state_json = json.dumps(state, ensure_ascii=False)
    return {"code": 0, "data": _progress_payload(progress, book, spreads)}


def _move_route(progress: ImmersiveProgress, state: dict, spreads: list[ImmersiveSpread], target: str,
                *, remember: bool = True) -> None:
    valid_ids = {spread.id for spread in spreads}
    if target not in valid_ids:
        raise HTTPException(status_code=503, detail="剧情路线配置不完整")
    current = state.get("current")
    if remember and current and current != target:
        state.setdefault("trail", []).append(current)
        state["trail"] = state["trail"][-80:]
    state["current"] = target
    for key in ("visited", "unlocked"):
        values = state.setdefault(key, [])
        if target not in values:
            values.append(target)
    progress.current_spread_id = target
    progress.current_spread = next((index for index, row in enumerate(spreads) if row.id == target), 0)
    progress.route_state_json = json.dumps(state, ensure_ascii=False)
    progress.flow_version = BRANCH_FLOW_VERSION
    progress.updated_at = datetime.utcnow()


@router.post("/books/{book_id}/choices")
def choose_route(book_id: str, data: ChoiceRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _published_book(db, book_id)
    spreads = _spreads(db, book.id)
    progress = _progress(db, user, book)
    assert progress is not None
    state = _ensure_route_state(progress, book, spreads)
    graph = _graph(book)
    node = graph.get("nodes", {}).get(data.decision_spread_id, {})
    if not node.get("decision"):
        raise HTTPException(status_code=422, detail="当前节点不是路线选择")
    submissions = state.setdefault("submissions", {})
    if data.submission_id in submissions:
        saved = submissions[data.submission_id]
        target_row = next((row for row in spreads if row.id == saved["next_spread_id"]), None)
        return {"code": 0, "data": {**saved, "spread": _spread_payload(target_row), "progress": _progress_payload(progress, book, spreads)}}
    if state.get("current") != data.decision_spread_id:
        raise HTTPException(status_code=409, detail="请先抵达对应的路线选择场景")
    option = node.get("options", {}).get(data.option_id)
    if not option:
        raise HTTPException(status_code=422, detail="路线选项不存在")
    discovered = set(_loads(progress.discovered_json, []))
    missing = [clue for clue in node.get("required_clues", []) if clue not in discovered]
    if missing:
        raise HTTPException(status_code=409, detail="请先找齐当前判断所需的现场线索")
    attempts = state.setdefault("attempts", {})
    attempts[data.decision_spread_id] = int(attempts.get(data.decision_spread_id, 0)) + 1
    attempt_count = attempts[data.decision_spread_id]
    correct = bool(option.get("correct"))
    if correct:
        solved = state.setdefault("solved_decisions", [])
        if data.decision_spread_id not in solved:
            solved.append(data.decision_spread_id)
        state.setdefault("decisions", {})[data.decision_spread_id] = data.option_id
        hint = ""
        result = "correct"
    else:
        wrong_routes = state.setdefault("wrong_routes", [])
        wrong_routes.append({
            "decision_spread_id": data.decision_spread_id, "option_id": data.option_id,
            "target_spread_id": option["target"], "attempt": attempt_count,
        })
        hints = node.get("hints", [])
        hint = hints[min(max(attempt_count - 1, 0), len(hints) - 1)] if hints else "回到现场重新核对证据。"
        result = "detour"
    _move_route(progress, state, spreads, option["target"])
    payload = {
        "result": result, "next_spread_id": option["target"], "feedback": option.get("feedback", ""),
        "hint": hint, "hint_level": min(3, attempt_count),
    }
    submissions[data.submission_id] = payload
    if len(submissions) > 60:
        for key in list(submissions)[:-60]:
            submissions.pop(key, None)
    progress.route_state_json = json.dumps(state, ensure_ascii=False)
    if book.module == "history" and correct:
        _sync_history_choice(db, user, book, data.option_id)
    target_row = next(row for row in spreads if row.id == option["target"])
    return {"code": 0, "data": {**payload, "spread": _spread_payload(target_row), "progress": _progress_payload(progress, book, spreads)}}


@router.post("/books/{book_id}/advance")
def advance_route(book_id: str, data: AdvanceRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _published_book(db, book_id)
    spreads = _spreads(db, book.id)
    progress = _progress(db, user, book)
    assert progress is not None
    state = _ensure_route_state(progress, book, spreads)
    if state.get("current") != data.from_spread_id:
        raise HTTPException(status_code=409, detail="页面状态已变化，请刷新后继续")
    graph = _graph(book)
    if data.direction == "back":
        trail = state.setdefault("trail", [])
        if not trail:
            raise HTTPException(status_code=409, detail="已经到达本卷起点")
        target = trail.pop()
        _move_route(progress, state, spreads, target, remember=False)
    elif data.direction == "jump":
        target = data.target_spread_id or ""
        if target not in state.get("unlocked", []):
            raise HTTPException(status_code=403, detail="该场景尚未解锁")
        _move_route(progress, state, spreads, target)
    else:
        node = graph.get("nodes", {}).get(data.from_spread_id, {})
        if node.get("decision") and data.from_spread_id not in state.get("solved_decisions", []):
            raise HTTPException(status_code=409, detail="请先根据现场证据作出选择")
        target = node.get("next")
        if not target:
            raise HTTPException(status_code=409, detail="已经到达当前路线终点")
        _move_route(progress, state, spreads, target)
    target_row = next(row for row in spreads if row.id == state["current"])
    return {"code": 0, "data": {"spread": _spread_payload(target_row), "progress": _progress_payload(progress, book, spreads)}}


@router.post("/books/{book_id}/ask")
async def ask_in_book(book_id: str, data: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = _published_book(db, book_id)
    spreads = _spreads(db, book.id)
    progress = _progress(db, user, book)
    state = _ensure_route_state(progress, book, spreads)
    spread_id = data.spread_id or state.get("current")
    if spread_id not in state.get("unlocked", []):
        raise HTTPException(status_code=403, detail="该场景尚未解锁")
    spread = next((item for item in spreads if item.id == spread_id), None)
    if not spread:
        raise HTTPException(status_code=422, detail="当前跨页不存在")
    sources = _loads(spread.source_refs_json, [])
    scene = _loads(spread.scene_json, {})
    event = scene.get("event") or {}
    timeline = scene.get("timeline") or []
    event_context = "；".join(filter(None, [
        event.get("date"), event.get("place"), event.get("title"),
        event.get("summary"), event.get("meaning"),
    ]))
    timeline_context = "\n".join(
        f"{item.get('date', '')} {item.get('place', '')}：{item.get('title', '')}。{item.get('summary', '')}"
        for item in timeline
    )
    context = "\n".join(filter(None, [
        event_context, spread.narration, timeline_context,
        scene.get("archive_excerpt", ""), *(item.get("excerpt", "") for item in sources),
    ]))
    try:
        if book.module == "history":
            answer = await ai_service.history_ask(book.title, data.question, context)
        else:
            grounded_question = f"请结合当前场景资料回答：{data.question}\n当前资料：{context}"
            answer = await ai_service.tour_ask(book.title, grounded_question)
        answer = validate_generated_text(answer, "场景问答")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 史官暂时无法回答：{exc}") from exc
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
    state = _ensure_route_state(progress, book, spreads)
    graph = _graph(book)
    if state.get("current") != graph.get("ending"):
        raise HTTPException(status_code=409, detail="请先沿正确路线抵达本卷最后一页")
    required_decisions = set(graph.get("required_decisions", []))
    solved_decisions = set(state.get("solved_decisions", []))
    if not required_decisions.issubset(solved_decisions):
        raise HTTPException(status_code=409, detail="请先完成路线、证据与判断三个关键选择")
    if not _loads(progress.discovered_json, []):
        raise HTTPException(status_code=409, detail="请先在场景中发现至少一处历史线索")

    now = datetime.utcnow()
    if book.module == "history":
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
        db.flush()
        award_points(
            db, user,
            module="history", event_type="scenario_completed", source_id=book.source_id,
            points=2, description="完成党史情景学习",
            metadata={"scenario_id": book.source_id, "book_id": book.id, "record_id": record.id},
        )
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
    qa_lines.append(
        f"路线复盘：完成3个关键判断，经历{len(state.get('wrong_routes', []))}次支线回溯，"
        f"发现{len(_loads(progress.discovered_json, []))}处现场线索。"
    )
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
    award_points(
        db, user,
        module="tour", event_type="site_completed", source_id=book.source_id,
        points=3, description="完成红色研学",
        metadata={"site_id": book.source_id, "book_id": book.id, "record_id": record.id},
    )
    db.add(GeneratedReport(
        user_id=user.id,
        report_type="tour",
        source_record_id=record.id,
        title=f"{site.name}研学报告",
        content_json=json.dumps({"report": report_text, "book_id": book.id, "note": progress.note}, ensure_ascii=False),
    ))
    return {"code": 0, "data": {"completed": True, "already_completed": False, "points": 3, "report": report_text, "record_id": record.id}}
