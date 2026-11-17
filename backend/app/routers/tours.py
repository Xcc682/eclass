"""红色研学路由：研学点位、导览讲解、手记与研学报告生成。"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.domain import GeneratedReport, TourRecord, TourSite
from app.models.immersive import ImmersiveProgress
from app.models.user import User
from app.security import get_current_user
from app.services import vision
from app.services.ai_service import ai_service, validate_generated_text
from app.services.point_service import award_points

router = APIRouter(prefix="/api/v1/tours", tags=["红色研学"])


class SiteRequest(BaseModel):
    site_id: str


class AskRequest(SiteRequest):
    question: str = Field(min_length=1, max_length=1000)
    record_id: str | None = None
    images: list[str] = Field(default_factory=list, max_length=2)


class ReportRequest(SiteRequest):
    qa_history: list[str] = []
    record_id: str | None = None


def payload(site: TourSite) -> dict:
    return {"id": site.id, "name": site.name, "location": site.location, "description": site.description,
            "emoji": site.emoji, "facts": json.loads(site.facts_json or "[]")}


@router.get("/sites")
def get_sites(db: Session = Depends(get_db)):
    rows = db.scalars(select(TourSite).order_by(TourSite.order_index)).all()
    return {"code": 0, "data": [payload(row) for row in rows]}


@router.get("/sites/{site_id}")
def get_site(site_id: str, db: Session = Depends(get_db)):
    site = db.get(TourSite, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="景点不存在")
    return {"code": 0, "data": payload(site)}


@router.post("/sessions/start")
def start_session(data: SiteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(TourSite, data.site_id):
        raise HTTPException(status_code=404, detail="景点不存在")
    record = db.scalar(
        select(TourRecord)
        .where(
            TourRecord.user_id == user.id,
            TourRecord.site_id == data.site_id,
            TourRecord.completed.is_(False),
        )
        .order_by(TourRecord.created_at.desc())
    )
    if record:
        return {"code": 0, "data": {
            "id": record.id,
            "site_id": record.site_id,
            "qa_history": json.loads(record.qa_json or "[]"),
            "completed": False,
            "resumed": True,
        }}
    record = TourRecord(user_id=user.id, site_id=data.site_id, qa_json="[]", completed=False)
    db.add(record)
    db.flush()
    return {"code": 0, "data": {"id": record.id, "site_id": record.site_id, "qa_history": [], "completed": False, "resumed": False}}


def owned_record(db: Session, record_id: str, user: User) -> TourRecord:
    record = db.get(TourRecord, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="研学记录不存在")
    return record


def _immersive_note(db: Session, record_id: str) -> str:
    """Return the note the student wrote in the immersive book, if any."""
    row = db.scalar(select(ImmersiveProgress).where(ImmersiveProgress.related_record_id == record_id))
    return (row.note or "").strip() if row else ""


@router.post("/intro")
async def get_intro(data: SiteRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    site = db.get(TourSite, data.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="景点不存在")
    try:
        intro = validate_generated_text(await ai_service.tour_intro(site.name), "景点讲解")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    return {"code": 0, "data": {"intro": intro}}


@router.post("/ask")
async def ask_question(data: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    site = db.get(TourSite, data.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="景点不存在")
    try:
        images = vision.sanitize_images(data.images)
    except vision.ImageInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        answer = validate_generated_text(await ai_service.tour_ask(site.name, data.question, images=images or None), "研学回答")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    if data.record_id:
        record = owned_record(db, data.record_id, user)
        if record.completed:
            raise HTTPException(status_code=409, detail="研学记录已完成")
        history = json.loads(record.qa_json or "[]")
        history.append({"q": data.question, "a": answer})
        record.qa_json = json.dumps(history, ensure_ascii=False)
    return {"code": 0, "data": {"answer": answer}}


@router.post("/generate-report")
async def generate_report(data: ReportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    site = db.get(TourSite, data.site_id)
    if not site:
        raise HTTPException(status_code=404, detail="景点不存在")
    record = owned_record(db, data.record_id, user) if data.record_id else db.scalar(
        select(TourRecord).where(
            TourRecord.user_id == user.id,
            TourRecord.site_id == data.site_id,
        ).order_by(TourRecord.created_at.desc()).limit(1)
    )
    if record and record.completed and record.report:
        return {"code": 0, "data": {"id": record.id, "report": record.report}}
    stored_history = json.loads(record.qa_json or "[]") if record else []
    qa_history = [f"Q:{item.get('q','')} A:{item.get('a','')}" for item in stored_history] or data.qa_history
    if record:
        note = _immersive_note(db, record.id)
        if note:
            qa_history = list(qa_history) + [f"研学手记：{note}"]
    try:
        report_text = validate_generated_text(await ai_service.tour_report(site.name, qa_history), "研学报告")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"AI 服务暂不可用：{exc}") from exc
    if record is None:
        record = TourRecord(user_id=user.id, site_id=site.id, qa_json=json.dumps(data.qa_history, ensure_ascii=False))
        db.add(record)
        db.flush()
    record.report = report_text
    record.completed = True
    record.completed_at = datetime.utcnow()
    award_points(
        db, user,
        module="tour", event_type="site_completed", source_id=site.id,
        points=3, description="完成红色研学",
        metadata={"site_id": site.id, "record_id": record.id},
    )
    content = json.dumps({"report": report_text}, ensure_ascii=False)
    existing_report = db.scalar(select(GeneratedReport).where(
        GeneratedReport.report_type == "tour", GeneratedReport.source_record_id == record.id,
    ))
    if not existing_report:
        db.add(GeneratedReport(
            user_id=user.id, report_type="tour", source_record_id=record.id,
            title=site.name, content_json=content,
        ))
    return {"code": 0, "data": {"id": record.id, "report": report_text}}


@router.get("/sessions/{record_id}")
def get_session(record_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = owned_record(db, record_id, user)
    return {"code": 0, "data": {"id": record.id, "site_id": record.site_id, "qa_history": json.loads(record.qa_json or "[]"), "report": record.report, "completed": record.completed, "note": _immersive_note(db, record.id)}}


@router.get("/history")
def tour_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(TourRecord).where(TourRecord.user_id == user.id).order_by(TourRecord.created_at.desc())).all()
    sites = {site.id: site for site in db.scalars(select(TourSite)).all()}
    return {"code": 0, "data": [{
        "id": row.id,
        "site_id": row.site_id,
        "site_name": sites[row.site_id].name if row.site_id in sites else "红色研学点",
        "completed": row.completed,
        "qa_count": len(json.loads(row.qa_json or "[]")),
        "created_at": row.created_at.isoformat(),
    } for row in rows]}
