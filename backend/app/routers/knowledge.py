"""Knowledge library, RAG question answering and content administration APIs."""
from __future__ import annotations

import json
import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.domain import GeneratedReport
from app.models.knowledge import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeFavorite,
    KnowledgeIngestionJob,
    KnowledgeMessage,
    KnowledgeSession,
    KnowledgeTemplate,
    KnowledgeView,
)
from app.models.user import User
from app.security import get_current_user, require_role
from app.services.ai_service import ai_service
from app.services.knowledge_service import (
    ALLOWED_MIME_TYPES,
    SUPPORTED_EXTENSIONS,
    process_document,
    purge_document_indexes,
    retrieval_status,
    retrieve,
    retrieve_async,
    sha256_bytes,
    _ensure_fts,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["知识库"])
content_manager = require_role("teacher", "admin")
logger = logging.getLogger("app.knowledge")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    category: str | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    category: str | None = None
    session_id: str | None = None


class GenerateRequest(BaseModel):
    template_id: str
    requirements: str = Field(default="", max_length=3000)
    personal_background: str = Field(default="", max_length=3000)


class TemplateHistoryUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=30000)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)


class DocumentUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    category: str = Field(min_length=1, max_length=100)
    source: str = Field(min_length=1, max_length=200)
    source_url: str = Field(default="", max_length=1000)
    summary: str = Field(default="", max_length=2000)
    version: int = Field(default=1, ge=1, le=9999)


def _storage_dir() -> Path:
    configured = Path(settings.KNOWLEDGE_STORAGE_DIR)
    if not configured.is_absolute():
        configured = Path(__file__).resolve().parents[2] / configured
    configured.mkdir(parents=True, exist_ok=True)
    return configured.resolve()


def _document_payload(doc: KnowledgeDocument, include_content: bool = False, favorite: bool = False) -> dict:
    data = {
        "id": doc.id,
        "title": doc.title,
        "category": doc.category,
        "summary": doc.summary,
        "source": doc.source,
        "source_url": doc.source_url,
        "status": doc.status,
        "version": doc.version,
        "file_name": doc.file_name,
        "mime_type": doc.mime_type,
        "view_count": doc.view_count,
        "chunk_count": doc.chunk_count,
        "processing_error": doc.processing_error,
        "is_favorite": favorite,
        "published_at": doc.published_at.isoformat() if doc.published_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }
    if include_content:
        data["content"] = doc.content
    return data


def _favorite_ids(db: Session, user_id: str, document_ids: list[str]) -> set[str]:
    if not document_ids:
        return set()
    return set(db.scalars(select(KnowledgeFavorite.document_id).where(
        KnowledgeFavorite.user_id == user_id,
        KnowledgeFavorite.document_id.in_(document_ids),
    )).all())


@router.get("/status")
def get_retrieval_status(_: User = Depends(get_current_user)):
    return {"code": 0, "data": retrieval_status()}


@router.get("/documents")
def get_documents(
    category: str | None = None,
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="newest", pattern="^(newest|popular|title)$"),
    db: Session = Depends(get_db),
):
    filters = [KnowledgeDocument.status == "published"]
    if category:
        filters.append(KnowledgeDocument.category == category)

    if q:
        # Try FTS5 first; fall back to ILIKE for Chinese text
        matched_ids: list[str] = []
        total = 0
        if _ensure_fts():
            scoring_sql = text("""
                SELECT d.id, MAX(bm25(knowledge_chunks_fts)) AS score
                FROM knowledge_chunks_fts
                JOIN knowledge_chunks c ON c.id = knowledge_chunks_fts.chunk_id
                JOIN knowledge_documents d ON d.id = c.document_id
                WHERE knowledge_chunks_fts MATCH :query AND d.status = 'published'
                GROUP BY d.id
            """)
            ids_with_scores = dict(db.execute(scoring_sql, {"query": q}).all())  # type: ignore[arg-type]
            matched_ids = sorted(ids_with_scores.keys(), key=lambda doc_id: ids_with_scores[doc_id], reverse=True)
            total = len(matched_ids)

        if not matched_ids:
            # Fallback to ILIKE with title-first heuristic ordering
            pattern = f"%{q}%"
            ilike_filters = [KnowledgeDocument.status == "published",
                or_(KnowledgeDocument.title.ilike(pattern), KnowledgeDocument.summary.ilike(pattern), KnowledgeDocument.content.ilike(pattern))]
            if category:
                ilike_filters.append(KnowledgeDocument.category == category)
            raw = db.scalars(select(KnowledgeDocument).where(*ilike_filters).order_by(
                KnowledgeDocument.title.ilike(pattern).desc(),
                KnowledgeDocument.published_at.desc(),
            )).all()
            total = len(raw)
            rows = raw[(page - 1) * page_size: page * page_size]
            return {"code": 0, "data": [_document_payload(row) for row in rows], "pagination": {"page": page, "page_size": page_size, "total": total}}

        ids_page = matched_ids[(page - 1) * page_size: page * page_size]
        rows = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.id.in_(ids_page))).all()
        rows_by_id = {row.id: row for row in rows}
        rows_sorted = [rows_by_id[doc_id] for doc_id in ids_page if doc_id in rows_by_id]
        return {"code": 0, "data": [_document_payload(row) for row in rows_sorted], "pagination": {"page": page, "page_size": page_size, "total": total}}

    if category:
        filters.append(KnowledgeDocument.category == category)
    statement = select(KnowledgeDocument).where(*filters)
    if sort == "popular":
        statement = statement.order_by(KnowledgeDocument.view_count.desc())
    elif sort == "title":
        statement = statement.order_by(KnowledgeDocument.title.asc())
    else:
        statement = statement.order_by(KnowledgeDocument.published_at.desc(), KnowledgeDocument.created_at.desc())
    total = db.scalar(select(func.count()).select_from(KnowledgeDocument).where(*filters)) or 0
    rows = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return {"code": 0, "data": [_document_payload(row) for row in rows], "pagination": {"page": page, "page_size": page_size, "total": total}}


@router.get("/manage/documents")
def manage_documents(
    document_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    _: User = Depends(content_manager),
    db: Session = Depends(get_db),
):
    filters = []
    if document_status:
        filters.append(KnowledgeDocument.status == document_status)
    total = db.scalar(select(func.count()).select_from(KnowledgeDocument).where(*filters)) or 0
    rows = db.scalars(select(KnowledgeDocument).where(*filters).order_by(KnowledgeDocument.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"code": 0, "data": [_document_payload(row) for row in rows], "pagination": {"page": page, "page_size": page_size, "total": total}}


@router.post("/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=500),
    category: str = Form(..., min_length=1, max_length=100),
    source: str = Form(..., min_length=1, max_length=200),
    source_url: str = Form(default="", max_length=1000),
    version: int = Form(default=1, ge=1),
    user: User = Depends(content_manager),
    db: Session = Depends(get_db),
):
    original_name = Path(file.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="仅支持 PDF、DOCX、TXT 和 Markdown 文件")
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail="文件 MIME 类型不受支持")
    max_size = settings.KNOWLEDGE_MAX_UPLOAD_MB * 1024 * 1024
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"文件不能超过 {settings.KNOWLEDGE_MAX_UPLOAD_MB}MB")
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    checksum = sha256_bytes(content)
    existing = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.checksum == checksum))
    if existing:
        raise HTTPException(status_code=409, detail={
            "code": "DUPLICATE_DOCUMENT",
            "message": f"相同文件已上传：{existing.title}。可直接编辑已有资料，或删除后重新上传。",
            "document": _document_payload(existing),
        })

    stored_path = _storage_dir() / f"{uuid.uuid4().hex}{suffix}"
    stored_path.write_bytes(content)
    document = KnowledgeDocument(
        title=title.strip(), category=category.strip(), source=source.strip(), source_url=source_url.strip(),
        version=version, status="processing", file_name=original_name, file_path=str(stored_path),
        mime_type=file.content_type or "application/octet-stream", checksum=checksum, uploader_id=user.id,
    )
    db.add(document)
    db.flush()
    job = KnowledgeIngestionJob(document_id=document.id, status="queued", progress=0)
    db.add(job)
    db.flush()
    background_tasks.add_task(process_document, document.id, job.id)
    return {"code": 0, "data": {"document": _document_payload(document), "job_id": job.id}}


@router.get("/ingestion-jobs/{job_id}")
def get_ingestion_job(job_id: str, user: User = Depends(content_manager), db: Session = Depends(get_db)):
    job = db.get(KnowledgeIngestionJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="处理任务不存在")
    document = db.get(KnowledgeDocument, job.document_id)
    if user.role != "admin" and document and document.uploader_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看该处理任务")
    return {"code": 0, "data": {
        "id": job.id,
        "document_id": job.document_id,
        "document_title": document.title if document else "",
        "file_name": document.file_name if document else None,
        "document_status": document.status if document else None,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }}


@router.post("/documents/{doc_id}/publish")
def publish_document(doc_id: str, user: User = Depends(content_manager), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    if document.status != "pending_review":
        raise HTTPException(status_code=409, detail="只有待审核文档可以发布")
    document.status = "published"
    document.reviewer_id = user.id
    document.published_at = datetime.utcnow()
    return {"code": 0, "data": _document_payload(document)}


@router.post("/documents/{doc_id}/reject")
def reject_document(doc_id: str, data: RejectRequest, user: User = Depends(content_manager), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    if document.status not in {"pending_review", "published"}:
        raise HTTPException(status_code=409, detail="当前状态不能驳回")
    document.status = "rejected"
    document.reviewer_id = user.id
    document.processing_error = data.reason
    return {"code": 0, "data": _document_payload(document)}


@router.put("/documents/{doc_id}")
def update_document(doc_id: str, data: DocumentUpdateRequest, _: User = Depends(content_manager), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    active_job = db.scalar(select(KnowledgeIngestionJob.id).where(
        KnowledgeIngestionJob.document_id == document.id,
        KnowledgeIngestionJob.status.in_(("queued", "processing")),
    ))
    if active_job:
        raise HTTPException(status_code=409, detail="文档正在解析或重建索引，请在任务完成后编辑")

    title = data.title.strip()
    category = data.category.strip()
    source = data.source.strip()
    if not title or not category or not source:
        raise HTTPException(status_code=422, detail="标题、分类和权威来源不能为空")
    document.title = title
    document.category = category
    document.source = source
    document.source_url = data.source_url.strip()
    document.summary = data.summary.strip()
    document.version = data.version
    return {"code": 0, "data": _document_payload(document)}


@router.post("/documents/{doc_id}/resubmit")
def resubmit_document(doc_id: str, _: User = Depends(content_manager), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    if document.status != "rejected":
        raise HTTPException(status_code=409, detail="只有已驳回资料可以重新提交审核")
    document.status = "pending_review"
    document.processing_error = None
    document.reviewer_id = None
    return {"code": 0, "data": _document_payload(document)}


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, _: User = Depends(content_manager), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    active_job = db.scalar(select(KnowledgeIngestionJob.id).where(
        KnowledgeIngestionJob.document_id == document.id,
        KnowledgeIngestionJob.status.in_(("queued", "processing")),
    ))
    if active_job:
        raise HTTPException(status_code=409, detail="文档正在解析或重建索引，暂时不能删除")

    file_path = Path(document.file_path).resolve() if document.file_path else None
    index_warnings = purge_document_indexes(document.id)
    db.execute(delete(KnowledgeFavorite).where(KnowledgeFavorite.document_id == document.id))
    db.execute(delete(KnowledgeView).where(KnowledgeView.document_id == document.id))
    db.execute(delete(KnowledgeIngestionJob).where(KnowledgeIngestionJob.document_id == document.id))
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
    db.delete(document)
    db.commit()

    file_warning = None
    if file_path and _storage_dir() in file_path.parents and file_path.is_file():
        try:
            file_path.unlink()
        except OSError:
            file_warning = "原始文件未能自动清理，请联系管理员处理"
    warnings = [*index_warnings, *([file_warning] if file_warning else [])]
    return {"code": 0, "data": {"id": doc_id, "deleted": True, "warnings": warnings}}


@router.post("/documents/{doc_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
def reindex_document(doc_id: str, background_tasks: BackgroundTasks, _: User = Depends(content_manager), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document or not document.file_path:
        raise HTTPException(status_code=404, detail="文档或原始文件不存在")
    active_job = db.scalar(select(KnowledgeIngestionJob).where(
        KnowledgeIngestionJob.document_id == document.id,
        KnowledgeIngestionJob.status.in_({"queued", "processing"}),
    ).order_by(KnowledgeIngestionJob.created_at.desc()))
    if active_job:
        raise HTTPException(status_code=409, detail="该文档已有索引任务正在执行，请稍后查看进度")

    previous_status = document.status
    final_status = "pending_review" if previous_status == "failed" else previous_status
    failure_status = previous_status
    document.processing_error = None
    job = KnowledgeIngestionJob(document_id=document.id, status="queued", progress=0)
    db.add(job)
    db.flush()
    background_tasks.add_task(
        process_document,
        document.id,
        job.id,
        final_status,
        failure_status,
        False,
    )
    return {"code": 0, "data": {
        "job_id": job.id,
        "document_id": document.id,
        "document_status": previous_status,
    }}


@router.get("/documents/{doc_id}/download")
def download_document(doc_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document or not document.file_path or (document.status != "published" and user.role not in {"teacher", "admin"}):
        raise HTTPException(status_code=404, detail="文件不存在")
    path = Path(document.file_path).resolve()
    if _storage_dir() not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=document.file_name or path.name, media_type=document.mime_type)


@router.get("/documents/{doc_id}")
def get_document(doc_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document or (document.status != "published" and user.role not in {"teacher", "admin"}):
        raise HTTPException(status_code=404, detail="文档不存在")
    document.view_count = (document.view_count or 0) + 1
    db.add(KnowledgeView(user_id=user.id, document_id=document.id))
    favorite = db.scalar(select(KnowledgeFavorite.id).where(KnowledgeFavorite.user_id == user.id, KnowledgeFavorite.document_id == document.id)) is not None
    return {"code": 0, "data": _document_payload(document, include_content=True, favorite=favorite)}


@router.get("/documents/{doc_id}/chunks/{chunk_index}")
def get_document_chunk(doc_id: str, chunk_index: int, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, doc_id)
    if not document or document.status != "published":
        raise HTTPException(status_code=404, detail="文档不存在")
    chunk = db.scalar(select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc_id, KnowledgeChunk.chunk_index == chunk_index))
    if not chunk:
        raise HTTPException(status_code=404, detail="引用片段不存在")
    return {"code": 0, "data": {"id": chunk.id, "document_id": doc_id, "chunk_index": chunk.chunk_index, "content": chunk.content}}


@router.post("/search")
def search_knowledge(data: SearchRequest, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    hits = retrieve(db, data.query, data.category, limit=30)
    seen: set[str] = set()
    documents = []
    for hit in hits:
        if hit["document_id"] in seen:
            continue
        seen.add(hit["document_id"])
        document = db.get(KnowledgeDocument, hit["document_id"])
        if document:
            item = _document_payload(document, include_content=True)
            item["excerpt"] = hit["content"][:240]
            documents.append(item)
    return {"code": 0, "data": documents}


@router.post("/ask")
async def ask_knowledge(data: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(KnowledgeSession, data.session_id) if data.session_id else None
    if session and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    if not session:
        session = KnowledgeSession(user_id=user.id, title=data.question[:60])
        db.add(session)
        db.flush()
    try:
        contexts = await asyncio.wait_for(
            retrieve_async(data.question, data.category, limit=6, use_vector=True),
            timeout=settings.KNOWLEDGE_RETRIEVAL_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("[knowledge] vector_retrieval_timeout fallback=keyword_only")
        try:
            contexts = await asyncio.wait_for(
                retrieve_async(data.question, data.category, limit=6, use_vector=False),
                timeout=settings.KNOWLEDGE_KEYWORD_FALLBACK_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.exception("[knowledge] keyword_fallback_failed error=%s", exc.__class__.__name__)
            raise HTTPException(status_code=503, detail="知识库检索暂不可用，请稍后重试") from exc
    except Exception as exc:
        logger.warning("[knowledge] hybrid_retrieval_failed fallback=keyword_only error=%s", exc.__class__.__name__)
        try:
            contexts = await asyncio.wait_for(
                retrieve_async(data.question, data.category, limit=6, use_vector=False),
                timeout=settings.KNOWLEDGE_KEYWORD_FALLBACK_TIMEOUT_SECONDS,
            )
        except Exception as fallback_exc:
            logger.exception("[knowledge] keyword_fallback_failed error=%s", fallback_exc.__class__.__name__)
            raise HTTPException(status_code=503, detail="知识库检索暂不可用，请稍后重试") from fallback_exc
    # Relevance filter: LLM judges each chunk, keeps only score >= 5, sorts by relevance
    if contexts:
        try:
            logger.info("[knowledge] relevance_filter_start candidates=%s", len(contexts))
            contexts = await asyncio.wait_for(
                ai_service.relevance_filter(data.question, contexts),
                timeout=settings.KNOWLEDGE_LLM_TIMEOUT_SECONDS,
            )
            logger.info("[knowledge] relevance_filter_done kept=%s", len(contexts))
        except Exception as exc:
            logger.warning("[knowledge] relevance_filter_failed fallback=all error=%s: %s", exc.__class__.__name__, exc)

    citations = [{
        "index": index,
        "document_id": item["document_id"],
        "document_title": item["title"],
        "source": item["source"],
        "source_url": item["source_url"],
        "chunk_id": item["chunk_id"],
        "chunk_index": item["chunk_index"],
        "excerpt": item["content"][:300],
        "relevance_score": item.get("relevance_score"),
        "relevance_reason": item.get("relevance_reason", ""),
    } for index, item in enumerate(contexts, start=1)]
    if contexts:
        try:
            logger.info("[knowledge] llm_answer_start citations=%s", len(citations))
            answer = await asyncio.wait_for(
                ai_service.knowledge_answer(data.question, contexts),
                timeout=settings.KNOWLEDGE_LLM_TIMEOUT_SECONDS,
            )
            logger.info("[knowledge] llm_answer_done citations=%s", len(citations))
        except asyncio.TimeoutError as exc:
            logger.warning("[knowledge] llm_answer_timeout")
            raise HTTPException(status_code=503, detail="AI 回答超时，请稍后重试；资料依据已检索完成但未生成回答") from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="AI 服务暂不可用，请稍后重试") from exc
    else:
        answer = "当前知识库没有足够依据。"
    db.add(KnowledgeMessage(session_id=session.id, role="user", content=data.question))
    db.add(KnowledgeMessage(session_id=session.id, role="assistant", content=answer, citations_json=json.dumps(citations, ensure_ascii=False)))
    session.updated_at = datetime.utcnow()
    return {"code": 0, "data": {"answer": answer, "session_id": session.id, "citations": citations}}


@router.post("/favorites/{document_id}")
def add_favorite(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = db.get(KnowledgeDocument, document_id)
    if not document or document.status != "published":
        raise HTTPException(status_code=404, detail="文档不存在")
    existing = db.scalar(select(KnowledgeFavorite).where(KnowledgeFavorite.user_id == user.id, KnowledgeFavorite.document_id == document_id))
    if not existing:
        db.add(KnowledgeFavorite(user_id=user.id, document_id=document_id))
    return {"code": 0, "data": {"document_id": document_id, "is_favorite": True}}


@router.delete("/favorites/{document_id}")
def remove_favorite(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(delete(KnowledgeFavorite).where(KnowledgeFavorite.user_id == user.id, KnowledgeFavorite.document_id == document_id))
    return {"code": 0, "data": {"document_id": document_id, "is_favorite": False}}


@router.get("/favorites")
def get_favorites(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(KnowledgeDocument).join(KnowledgeFavorite, KnowledgeFavorite.document_id == KnowledgeDocument.id).where(
        KnowledgeFavorite.user_id == user.id, KnowledgeDocument.status == "published",
    ).order_by(KnowledgeFavorite.created_at.desc())).all()
    return {"code": 0, "data": [_document_payload(row, favorite=True) for row in rows]}


@router.get("/recent")
def get_recent(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    views = db.execute(select(KnowledgeView, KnowledgeDocument).join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeView.document_id).where(
        KnowledgeView.user_id == user.id, KnowledgeDocument.status == "published",
    ).order_by(KnowledgeView.viewed_at.desc()).limit(100)).all()
    seen: set[str] = set()
    data = []
    for view, document in views:
        if document.id in seen:
            continue
        seen.add(document.id)
        item = _document_payload(document)
        item["viewed_at"] = view.viewed_at.isoformat()
        data.append(item)
        if len(data) >= 30:
            break
    return {"code": 0, "data": data}


@router.get("/sessions")
def get_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(KnowledgeSession).where(KnowledgeSession.user_id == user.id).order_by(KnowledgeSession.updated_at.desc())).all()
    return {"code": 0, "data": [{"id": row.id, "title": row.title, "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()} for row in rows]}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(KnowledgeSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = db.scalars(select(KnowledgeMessage).where(KnowledgeMessage.session_id == session.id).order_by(KnowledgeMessage.created_at.asc())).all()
    return {"code": 0, "data": {"id": session.id, "title": session.title, "messages": [{"id": item.id, "role": item.role, "content": item.content, "citations": json.loads(item.citations_json or "[]"), "created_at": item.created_at.isoformat()} for item in messages]}}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(KnowledgeSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    db.execute(delete(KnowledgeMessage).where(KnowledgeMessage.session_id == session.id))
    db.delete(session)
    return {"code": 0, "data": {"id": session_id, "deleted": True}}


@router.get("/templates")
def get_templates(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(KnowledgeTemplate).where(KnowledgeTemplate.active.is_(True)).order_by(KnowledgeTemplate.order_index)).all()
    return {"code": 0, "data": [{"id": row.id, "name": row.name, "desc": row.description, "prompt": row.prompt} for row in rows]}


@router.post("/templates/generate")
async def generate_template(data: GenerateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    template = db.get(KnowledgeTemplate, data.template_id)
    if not template or not template.active:
        raise HTTPException(status_code=404, detail="模板不存在")
    context = f"写作要点：{template.prompt}\n个人背景：{data.personal_background or '未提供'}\n具体要求：{data.requirements or '无'}"
    try:
        content = await ai_service.generate_template(template.name, context)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="AI 服务暂不可用，请稍后重试") from exc
    report = GeneratedReport(user_id=user.id, report_type="knowledge_template", title=template.name, content_json=json.dumps({
        "content": content, "template_id": template.id, "personal_background": data.personal_background, "requirements": data.requirements,
    }, ensure_ascii=False))
    db.add(report)
    db.flush()
    return {"code": 0, "data": {"id": report.id, "title": template.name, "content": content}}


@router.get("/templates/history")
def template_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(GeneratedReport).where(
        GeneratedReport.user_id == user.id, GeneratedReport.report_type == "knowledge_template",
    ).order_by(GeneratedReport.created_at.desc())).all()
    return {"code": 0, "data": [{"id": row.id, "title": row.title, "content": json.loads(row.content_json or "{}").get("content", ""), "created_at": row.created_at.isoformat()} for row in rows]}


@router.put("/templates/history/{report_id}")
def update_template_history(report_id: str, data: TemplateHistoryUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(GeneratedReport, report_id)
    if not report or report.user_id != user.id or report.report_type != "knowledge_template":
        raise HTTPException(status_code=404, detail="生成记录不存在")
    payload = json.loads(report.content_json or "{}")
    payload["content"] = data.content
    payload["edited"] = True
    report.content_json = json.dumps(payload, ensure_ascii=False)
    return {"code": 0, "data": {"id": report.id, "content": data.content}}


@router.delete("/templates/history/{report_id}")
def delete_template_history(report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = db.get(GeneratedReport, report_id)
    if not report or report.user_id != user.id or report.report_type != "knowledge_template":
        raise HTTPException(status_code=404, detail="生成记录不存在")
    db.delete(report)
    return {"code": 0, "data": {"id": report_id, "deleted": True}}
