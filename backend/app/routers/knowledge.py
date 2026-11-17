"""Knowledge library, RAG question answering and content administration APIs."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
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
from app.services import knowledge_agent, safety, vision
from app.services.ai_service import ai_service
from app.services.knowledge_service import (
    ALLOWED_MIME_TYPES,
    SUPPORTED_EXTENSIONS,
    _ensure_fts,
    process_document,
    purge_document_indexes,
    retrieval_status,
    retrieve,
    retrieve_async,
    sha256_bytes,
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
    submission_id: str | None = Field(default=None, min_length=8, max_length=64)
    document_ids: list[str] = Field(default_factory=list, max_length=20)
    images: list[str] = Field(default_factory=list, max_length=2)


class SessionUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class MessageFeedbackRequest(BaseModel):
    helpful: bool
    reason: str = Field(default="", max_length=500)


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


_FOLLOW_UP_RE = re.compile(r"^(它|这个|这条|上述|上一个|刚才|其中|两者|那|那么)|有什么区别|再说|继续|具体一点|为什么呢")
_INLINE_CITATION_RE = re.compile(r"\[(\d+)\]")
_FOLLOW_UP_DIRECTIONS = ("历史", "背景", "意义", "作用", "影响", "时间", "人物", "要求", "流程", "条件", "区别", "原因", "案例")
_ASSISTANT_INTRO = (
    "我是“思政情景工坊”的知识库助手。我可以从已审核资料中检索思政学习问题，"
    "并给出可点击、可追溯的原文依据。你可以选择全部资料、指定分类或当前资料来提问；"
    "如果现有资料不足以支持结论，我会明确说明，不会凭空补充。"
)


def _assistant_intro(topic: str) -> dict:
    prefix = "你好，" if topic == "greeting" else ""
    content = f"{prefix}{_ASSISTANT_INTRO}"
    return {
        "answer": content,
        "answer_blocks": [
            {"type": "heading", "text": "关于我", "citations": []},
            {"type": "paragraph", "text": content, "citations": []},
        ],
        "citations": [],
        "used_citation_indexes": [],
        "follow_up_suggestions": [],
    }


def _safe_json(value: str | None, fallback):
    try:
        parsed = json.loads(value or "")
        return parsed
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def _retrieval_query(question: str, history: list[KnowledgeMessage]) -> str:
    if not _FOLLOW_UP_RE.search(question.strip()):
        return question
    previous = next((item.content for item in reversed(history) if item.role == "user"), "")
    return f"{previous}\n追问：{question}" if previous else question


def _legacy_blocks(content: str, citation_count: int) -> tuple[list[dict], list[int], str]:
    content = re.sub(r"\[(\d+)\](?:\s*\[\1\])+", r"[\1]", content or "")
    content = _INLINE_CITATION_RE.sub(
        lambda match: match.group(0) if 1 <= int(match.group(1)) <= citation_count else "",
        content,
    )
    blocks: list[dict] = []
    used: list[int] = []
    for raw_line in re.split(r"\n+", content):
        line = raw_line.strip()
        if not line:
            continue
        citations = []
        for value in _INLINE_CITATION_RE.findall(line):
            number = int(value)
            if number not in citations:
                citations.append(number)
            if number not in used:
                used.append(number)
        text_value = _INLINE_CITATION_RE.sub("", line).strip()
        kind = "list_item" if re.match(r"^(?:[-•]|\d+[.、])", text_value) else "paragraph"
        text_value = re.sub(r"^(?:[-•]|\d+[.、])\s*", "", text_value)
        if text_value:
            blocks.append({"type": kind, "text": text_value, "citations": citations})
    return blocks, used, content.strip()


def _supported_suggestions(values: object, evidence_text: str, question: str = "") -> list[str]:
    if not isinstance(values, list):
        return []
    suggestions: list[str] = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            continue
        suggestion = item.strip()
        new_directions = [word for word in _FOLLOW_UP_DIRECTIONS if word in suggestion and word not in question]
        if evidence_text and any(word not in evidence_text for word in new_directions):
            continue
        suggestions.append(suggestion)
        if len(suggestions) >= 3:
            break
    return suggestions


def _recover_structured_answer(raw: object) -> dict | None:
    """Parse JSON answers and salvage complete blocks from a truncated model response."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.replace("**", "")
    if not cleaned.startswith("{"):
        return None
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r'"blocks"\s*:\s*\[', cleaned)
    if not match:
        return None
    decoder = json.JSONDecoder()
    position = match.end()
    blocks: list[dict] = []
    while position < len(cleaned):
        while position < len(cleaned) and cleaned[position] in " \t\r\n,":
            position += 1
        if position >= len(cleaned) or cleaned[position] == "]":
            break
        if cleaned[position] != "{":
            break
        try:
            value, position = decoder.raw_decode(cleaned, position)
        except json.JSONDecodeError:
            break
        if isinstance(value, dict):
            blocks.append(value)
    return {"blocks": blocks, "follow_up_suggestions": []} if blocks else None


def _grouped_citation_order(indexes: list[int], citations: list[dict]) -> list[int]:
    """Keep document groups together, then number citations in their display order."""
    citation_by_index = {
        citation.get("index"): citation
        for citation in citations
        if isinstance(citation, dict) and isinstance(citation.get("index"), int)
    }
    groups: dict[str, list[int]] = {}
    for index in indexes:
        citation = citation_by_index.get(index)
        if not citation:
            continue
        document_key = str(citation.get("document_id") or f"citation:{index}")
        group = groups.setdefault(document_key, [])
        if index not in group:
            group.append(index)
    return [index for group in groups.values() for index in group]


def _remap_citation_display(
    citations: list[dict], blocks: list[dict], content: str,
) -> tuple[list[dict], list[dict], str]:
    """Return citations, blocks and text with one shared, sequential display order."""
    used: list[int] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        for value in block.get("citations", []):
            try:
                index = int(value)
            except (TypeError, ValueError):
                continue
            if index not in used:
                used.append(index)
    if not used:
        for value in _INLINE_CITATION_RE.findall(content or ""):
            index = int(value)
            if index not in used:
                used.append(index)

    ordered = _grouped_citation_order(used, citations)
    remap = {old: new for new, old in enumerate(ordered, start=1)}
    citation_by_index = {
        citation.get("index"): citation
        for citation in citations
        if isinstance(citation, dict)
    }
    selected: list[dict] = []
    for old in ordered:
        citation = citation_by_index.get(old)
        if citation:
            copied = dict(citation)
            copied["index"] = remap[old]
            selected.append(copied)

    normalized_blocks: list[dict] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        copied = dict(block)
        copied["citations"] = sorted(set(
            remap[int(value)]
            for value in block.get("citations", [])
            if str(value).isdigit() and int(value) in remap
        ))
        normalized_blocks.append(copied)
    if normalized_blocks:
        lines: list[str] = []
        for block in normalized_blocks:
            marks = "".join(f"[{index}]" for index in block.get("citations", []))
            prefix = "- " if block.get("type") == "list_item" else ""
            suffix = "" if block.get("type") == "heading" else marks
            lines.append(f"{prefix}{block.get('text', '')}{suffix}")
        normalized_content = "\n".join(lines)
    else:
        normalized_content = _INLINE_CITATION_RE.sub(
            lambda match: f"[{remap[int(match.group(1))]}]" if int(match.group(1)) in remap else "",
            content or "",
        )
    return selected, normalized_blocks, normalized_content


def _normalize_answer(raw: object, citations: list[dict], question: str = "", contexts: list[dict] | None = None) -> dict:
    recovered = _recover_structured_answer(raw)
    if recovered is not None:
        raw = recovered
    if not isinstance(raw, dict):
        blocks, used, answer = _legacy_blocks(str(raw or ""), len(citations))
        if not used:
            return {
                "answer": "当前知识库没有足够依据。你可以换一种更具体的问法，或先在资料库中搜索相关文件。",
                "answer_blocks": [], "citations": [], "used_citation_indexes": [], "follow_up_suggestions": [],
            }
        selected, blocks, answer = _remap_citation_display(citations, blocks, answer)
        return {"answer": answer, "answer_blocks": blocks, "citations": selected,
                "used_citation_indexes": list(range(1, len(selected) + 1)), "follow_up_suggestions": []}

    valid_blocks: list[dict] = []
    used_original: list[int] = []
    for item in raw.get("blocks", []) if isinstance(raw.get("blocks"), list) else []:
        if not isinstance(item, dict):
            continue
        kind = item.get("type") if item.get("type") in {"heading", "paragraph", "list_item"} else "paragraph"
        text_value = re.sub(r"\[(\d+)\]", "", str(item.get("text", ""))).strip()
        raw_indexes = item.get("citations") if isinstance(item.get("citations"), list) else []
        indexes: list[int] = []
        for value in raw_indexes:
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= number <= len(citations) and number not in indexes:
                indexes.append(number)
                if number not in used_original:
                    used_original.append(number)
        if not text_value or (kind != "heading" and not indexes):
            continue
        valid_blocks.append({"type": kind, "text": text_value, "citations": indexes})

    if not valid_blocks or not used_original:
        return {
            "answer": "当前知识库没有足够依据。你可以换一种更具体的问法，或先在资料库中搜索相关文件。",
            "answer_blocks": [], "citations": [], "used_citation_indexes": [], "follow_up_suggestions": [],
        }
    grouped_order = _grouped_citation_order(used_original, citations)
    remap = {old: new for new, old in enumerate(grouped_order, start=1)}
    selected = []
    for old in grouped_order:
        citation = dict(citations[old - 1])
        citation["index"] = remap[old]
        selected.append(citation)
    lines = []
    for block in valid_blocks:
        block["citations"] = sorted({remap[index] for index in block["citations"]})
        marks = "".join(f"[{index}]" for index in block["citations"])
        prefix = "- " if block["type"] == "list_item" else ""
        lines.append(f"{prefix}{block['text']}{marks if block['type'] != 'heading' else ''}")
    evidence_text = "\n".join(str(item.get("content", "")) for item in (contexts or []))
    suggestions = _supported_suggestions(raw.get("follow_up_suggestions", []), evidence_text, question)
    return {"answer": "\n".join(lines), "answer_blocks": valid_blocks, "citations": selected,
            "used_citation_indexes": list(range(1, len(selected) + 1)), "follow_up_suggestions": suggestions}


LEARNER_TOOLS = {"get_learning_profile", "list_my_practices", "get_practice_detail"}


def _uncited_answer(raw: object) -> dict | None:
    """不带知识库引用的答案：用于学习档案问答与图片解读。

    这两类内容分别来自本人练习记录与用户上传的图片，都不是可引用的已审核资料；
    只有模型确实给出了正文时才启用，否则返回 None 交给「资料不足」处理。
    """
    recovered = _recover_structured_answer(raw)
    value = recovered if recovered is not None else raw
    blocks: list[dict] = []
    suggestions: list[str] = []
    if isinstance(value, dict):
        for item in value.get("blocks", []) if isinstance(value.get("blocks"), list) else []:
            if not isinstance(item, dict):
                continue
            kind = item.get("type") if item.get("type") in {"heading", "paragraph", "list_item"} else "paragraph"
            text_value = re.sub(r"\[(\d+)\]", "", str(item.get("text", ""))).strip()
            if text_value:
                blocks.append({"type": kind, "text": text_value, "citations": []})
        candidates = value.get("follow_up_suggestions")
        suggestions = [str(item).strip()[:80] for item in candidates if str(item).strip()][:3] if isinstance(candidates, list) else []
    elif isinstance(value, str) and value.strip():
        blocks = [{"type": "paragraph", "text": value.strip(), "citations": []}]
    if not blocks:
        return None
    lines = [("- " if block["type"] == "list_item" else "") + block["text"] for block in blocks]
    return {
        "answer": "\n".join(lines),
        "answer_blocks": blocks,
        "citations": [],
        "used_citation_indexes": [],
        "follow_up_suggestions": suggestions,
    }


def _message_payload(item: KnowledgeMessage) -> dict:
    citations = _safe_json(item.citations_json, [])
    answer_data = _safe_json(item.answer_json, {})
    recovered = _recover_structured_answer(item.content) if item.role == "assistant" else None
    if recovered is not None:
        normalized = _normalize_answer(recovered, citations)
        content = normalized["answer"]
        citations = normalized["citations"]
        answer_data = {
            "answer_blocks": normalized["answer_blocks"],
            "used_citation_indexes": normalized["used_citation_indexes"],
            "follow_up_suggestions": normalized["follow_up_suggestions"],
            "degraded": bool(answer_data.get("degraded", False)),
        }
    elif item.role == "assistant" and not answer_data.get("answer_blocks"):
        blocks, _, normalized = _legacy_blocks(item.content, len(citations))
        citations, blocks, content = _remap_citation_display(citations, blocks, normalized)
        answer_data = {
            "answer_blocks": blocks,
            "used_citation_indexes": list(range(1, len(citations) + 1)),
        }
    elif item.role == "assistant":
        citations, blocks, content = _remap_citation_display(
            citations, answer_data.get("answer_blocks", []), item.content,
        )
        answer_data["answer_blocks"] = blocks
        answer_data["used_citation_indexes"] = list(range(1, len(citations) + 1))
    else:
        content = item.content
    follow_up_suggestions = _supported_suggestions(
        answer_data.get("follow_up_suggestions", []),
        "\n".join(str(citation.get("excerpt", "")) for citation in citations),
    )
    default_kind = "rag"
    if item.role == "assistant" and not citations and str(content).startswith("当前知识库没有足够依据"):
        default_kind = "no_evidence"
    return {
        "id": item.id, "role": item.role, "content": content, "citations": citations,
        "answer_blocks": answer_data.get("answer_blocks", []),
        "follow_up_suggestions": follow_up_suggestions,
        "response_kind": answer_data.get("response_kind", default_kind),
        "selected_tool": answer_data.get("selected_tool"),
        "degraded": bool(answer_data.get("degraded", False)),
        "submission_id": item.submission_id, "status": item.status or "sent", "error": item.error,
        "feedback": item.feedback, "created_at": item.created_at.isoformat(),
    }


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
def get_retrieval_status(_: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = retrieval_status()
    data["published_documents"] = db.scalar(select(func.count()).select_from(KnowledgeDocument).where(
        KnowledgeDocument.status == "published"
    )) or 0
    data["indexed_chunks"] = db.scalar(select(func.count()).select_from(KnowledgeChunk).join(
        KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id
    ).where(KnowledgeDocument.status == "published")) or 0
    data["llm_configured"] = bool(settings.LLM_API_KEY)
    return {"code": 0, "data": data}


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
        # Try FTS5 first; fall back to ILIKE for Chinese text. Malformed FTS
        # syntax (quotes, operators) must not surface as a 500 on this public
        # endpoint, so any FTS error falls through to the ILIKE branch below.
        matched_ids: list[str] = []
        total = 0
        if _ensure_fts():
            try:
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
            except Exception as exc:
                logger.warning("[knowledge] FTS document query failed, falling back to ILIKE: %s", exc)

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


def _finish_answer(
    *,
    db: Session,
    session: KnowledgeSession,
    user_message: KnowledgeMessage,
    submission_id: str,
    normalized: dict,
    degraded: bool,
    selected_tool: str,
    started_at: float,
    tool_trace: list[dict] | None = None,
    response_kind: str | None = None,
) -> dict:
    """落库并组装问答接口的统一返回结构，固定检索与 Agent 两条链路共用。"""
    normalized = dict(normalized)
    normalized["answer"] = safety.mask_output(normalized["answer"])
    normalized["answer_blocks"] = [
        {**block, "text": safety.mask_output(block["text"])}
        if isinstance(block, dict) and isinstance(block.get("text"), str) else block
        for block in normalized.get("answer_blocks") or []
    ]
    answer_meta = {
        "answer_blocks": normalized["answer_blocks"],
        "used_citation_indexes": normalized["used_citation_indexes"],
        "follow_up_suggestions": normalized["follow_up_suggestions"],
        "response_kind": response_kind or ("rag" if normalized["citations"] else "no_evidence"),
        "selected_tool": selected_tool,
        "degraded": degraded,
        "tool_trace": tool_trace or [],
    }
    assistant_message = KnowledgeMessage(
        session_id=session.id, role="assistant", content=normalized["answer"],
        citations_json=json.dumps(normalized["citations"], ensure_ascii=False),
        answer_json=json.dumps(answer_meta, ensure_ascii=False),
        submission_id=submission_id, status="sent",
    )
    db.add(assistant_message)
    user_message = db.get(KnowledgeMessage, user_message.id)
    user_message.status = "sent"
    user_message.error = None
    session.updated_at = datetime.utcnow()
    db.flush()
    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    logger.info("[knowledge] ask_done request_id=%s degraded=%s evidence=%s elapsed_ms=%s",
                submission_id, degraded, len(normalized["citations"]), elapsed_ms)
    return {"code": 0, "data": {
        "answer": normalized["answer"], "session_id": session.id, "message_id": assistant_message.id,
        "submission_id": submission_id, "status": "sent", "citations": normalized["citations"],
        "answer_blocks": normalized["answer_blocks"],
        "used_citation_indexes": normalized["used_citation_indexes"],
        "follow_up_suggestions": normalized["follow_up_suggestions"],
        "response_kind": answer_meta["response_kind"],
        "selected_tool": selected_tool,
        "degraded": degraded, "cached": False,
        "tool_trace": answer_meta["tool_trace"],
    }}


@router.post("/ask")
async def ask_knowledge(data: AskRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    verdict = safety.check_input(data.question)
    if not verdict.allowed:
        raise HTTPException(status_code=400, detail=verdict.reason)
    try:
        images = vision.sanitize_images(data.images)
    except vision.ImageInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    started_at = time.perf_counter()
    submission_id = data.submission_id or uuid.uuid4().hex
    session = db.get(KnowledgeSession, data.session_id) if data.session_id else None
    if session and session.user_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问该会话")
    if not session:
        session = KnowledgeSession(user_id=user.id, title=data.question[:60])
        db.add(session)
        db.flush()

    existing_user = db.scalar(select(KnowledgeMessage).where(
        KnowledgeMessage.session_id == session.id,
        KnowledgeMessage.role == "user",
        KnowledgeMessage.submission_id == submission_id,
    ))
    existing_answer = db.scalar(select(KnowledgeMessage).where(
        KnowledgeMessage.session_id == session.id,
        KnowledgeMessage.role == "assistant",
        KnowledgeMessage.submission_id == submission_id,
    ))
    if existing_answer and existing_answer.status == "sent":
        payload = _message_payload(existing_answer)
        return {"code": 0, "data": {
            "answer": payload["content"], "session_id": session.id, "message_id": existing_answer.id,
            "submission_id": submission_id, "status": "sent", "citations": payload["citations"],
            "answer_blocks": payload["answer_blocks"],
            "used_citation_indexes": list(range(1, len(payload["citations"]) + 1)),
            "follow_up_suggestions": payload["follow_up_suggestions"],
            "response_kind": payload["response_kind"],
            "selected_tool": payload["selected_tool"],
            "degraded": payload["degraded"], "cached": True,
        }}
    if existing_user and existing_user.status == "pending":
        age = (datetime.utcnow() - (existing_user.updated_at or existing_user.created_at)).total_seconds()
        if age < 90:
            raise HTTPException(status_code=409, detail={"code": "SUBMISSION_PROCESSING", "message": "该问题仍在处理中，请稍后查看历史"})
        existing_user.status = "failed"
        existing_user.error = "上次请求未完成，可以重新发送"

    history = db.scalars(select(KnowledgeMessage).where(
        KnowledgeMessage.session_id == session.id,
        KnowledgeMessage.status == "sent",
    ).order_by(KnowledgeMessage.created_at.desc()).limit(6)).all()
    history = list(reversed(history))
    retrieval_query = _retrieval_query(data.question, history)
    document_ids = list(dict.fromkeys(data.document_ids))
    if document_ids:
        available = set(db.scalars(select(KnowledgeDocument.id).where(
            KnowledgeDocument.id.in_(document_ids), KnowledgeDocument.status == "published"
        )).all())
        document_ids = [item for item in document_ids if item in available]
        if not document_ids:
            raise HTTPException(status_code=404, detail="指定资料不存在或尚未发布")

    user_message = existing_user or KnowledgeMessage(
        session_id=session.id, role="user", content=data.question,
        submission_id=submission_id, status="pending",
    )
    user_message.content = data.question
    user_message.status = "pending"
    user_message.error = None
    if not existing_user:
        db.add(user_message)
    session.updated_at = datetime.utcnow()
    db.commit()

    history_payload = [{"role": item.role, "content": item.content} for item in history]
    degraded = False
    selected_tool = "search_knowledge"
    tool_call: dict = {
        "name": "search_knowledge",
        "arguments": {"query": retrieval_query},
        "tool_call_id": f"fallback-{submission_id}",
    }
    tool_started_at = time.perf_counter()
    if images:
        # 带图的提问一律走资料检索 + 图片解读，避免被意图路由误判为「询问助手能力」
        logger.info("[knowledge] tool_selection_skipped request_id=%s reason=images", submission_id)
    else:
        try:
            tool_call = await asyncio.wait_for(
                ai_service.select_knowledge_tool(data.question, history_payload),
                timeout=min(12.0, settings.KNOWLEDGE_LLM_TIMEOUT_SECONDS),
            )
            selected_tool = tool_call["name"]
            logger.info(
                "[knowledge] tool_selection_done request_id=%s tool=%s elapsed_ms=%s",
                submission_id, selected_tool, int((time.perf_counter() - tool_started_at) * 1000),
            )
        except Exception as exc:
            degraded = True
            logger.warning(
                "[knowledge] tool_selection_fallback request_id=%s error=%s fallback=search_knowledge elapsed_ms=%s",
                submission_id, exc.__class__.__name__, int((time.perf_counter() - tool_started_at) * 1000),
            )

    citations: list[dict] = []
    contexts: list[dict] = []
    if selected_tool == "describe_assistant":
        normalized = _assistant_intro(str(tool_call.get("arguments", {}).get("topic", "identity")))
        response_kind = "assistant_intro"
    else:
        selected_tool = "search_knowledge"
        tool_query = str(tool_call.get("arguments", {}).get("query") or retrieval_query).strip()
        if "\n追问：" in retrieval_query and retrieval_query.split("\n追问：", 1)[0] not in tool_query:
            tool_query = f"{retrieval_query}\n检索改写：{tool_query}"
        retrieval_query = tool_query[:1000]
        if settings.KNOWLEDGE_AGENT_ENABLED:
            # 意图已确认为查资料：交给自主检索 Agent 决定检索词与调用轮次，
            # 任一环节失败都退回下面的固定检索，保证问答始终有结果。
            agent_started_at = time.perf_counter()
            try:
                agent_result = await asyncio.wait_for(
                    knowledge_agent.run(data.question, history_payload, data.category, document_ids or None, db,
                                        user_id=user.id, images=images or None),
                    timeout=settings.KNOWLEDGE_AGENT_TIMEOUT_SECONDS,
                )
                logger.info(
                    "[knowledge] agent_done request_id=%s steps=%s tools=%s evidence=%s elapsed_ms=%s",
                    submission_id, agent_result.steps,
                    ",".join(str(item.get("tool")) for item in agent_result.trace) or "none",
                    len(agent_result.contexts),
                    int((time.perf_counter() - agent_started_at) * 1000),
                )
                agent_contexts = agent_result.contexts[:6]
                used_learner_tools = any(
                    str(entry.get("tool") or "") in LEARNER_TOOLS for entry in agent_result.trace
                )
                allow_uncited = used_learner_tools or bool(images)
                agent_kind = "rag"
                agent_answer = None
                if agent_contexts:
                    agent_citations = [{
                        "index": index,
                        "document_id": item["document_id"],
                        "document_title": item["title"],
                        "source": item["source"],
                        "source_url": item["source_url"],
                        "chunk_id": item["chunk_id"],
                        "chunk_index": item["chunk_index"],
                        "excerpt": item["content"][:300],
                    } for index, item in enumerate(agent_contexts, start=1)]
                    agent_answer = _normalize_answer(agent_result.answer, agent_citations, data.question, agent_contexts)
                if (not agent_answer or not agent_answer["citations"]) and allow_uncited:
                    # 读了本人档案或解读图片、答案又没有命中知识库引用：保留正文但不附引用，
                    # 避免把个性化分析与图片解读误判为「资料不足」
                    uncited = _uncited_answer(agent_result.answer)
                    if uncited is not None:
                        agent_answer = uncited
                        agent_kind = "multimodal" if images and not used_learner_tools else "personalized"
                if agent_answer is None or (not agent_answer["citations"] and agent_kind not in {"personalized", "multimodal"}):
                    agent_kind = "no_evidence"
                    agent_answer = {
                        "answer": "当前知识库没有足够依据。你可以换一种更具体的问法，或先在资料库中搜索相关文件。",
                        "answer_blocks": [], "citations": [], "used_citation_indexes": [], "follow_up_suggestions": [],
                    }
                return _finish_answer(
                    db=db, session=session, user_message=user_message, submission_id=submission_id,
                    normalized=agent_answer, degraded=False, selected_tool="search_knowledge",
                    started_at=started_at, tool_trace=agent_result.trace, response_kind=agent_kind,
                )
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning(
                    "[knowledge] agent_fallback request_id=%s error=%s elapsed_ms=%s",
                    submission_id, exc.__class__.__name__,
                    int((time.perf_counter() - agent_started_at) * 1000),
                )

        retrieval_started_at = time.perf_counter()
        try:
            contexts = await asyncio.wait_for(
                retrieve_async(retrieval_query, data.category, limit=6, use_vector=True, document_ids=document_ids),
                timeout=settings.KNOWLEDGE_RETRIEVAL_TIMEOUT_SECONDS,
            )
        except TimeoutError:
            logger.warning("[knowledge] vector_retrieval_timeout request_id=%s fallback=keyword_only", submission_id)
            degraded = True
            try:
                contexts = await asyncio.wait_for(
                    retrieve_async(retrieval_query, data.category, limit=6, use_vector=False, document_ids=document_ids),
                    timeout=settings.KNOWLEDGE_KEYWORD_FALLBACK_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                logger.exception("[knowledge] keyword_fallback_failed request_id=%s error=%s", submission_id, exc.__class__.__name__)
                user_message = db.get(KnowledgeMessage, user_message.id)
                user_message.status, user_message.error = "failed", "知识库检索暂不可用，请稍后重试"
                db.commit()
                raise HTTPException(status_code=503, detail="知识库检索暂不可用，请稍后重试") from exc
        except Exception as exc:
            logger.warning("[knowledge] hybrid_retrieval_failed request_id=%s fallback=keyword_only error=%s", submission_id, exc.__class__.__name__)
            degraded = True
            try:
                contexts = await asyncio.wait_for(
                    retrieve_async(retrieval_query, data.category, limit=6, use_vector=False, document_ids=document_ids),
                    timeout=settings.KNOWLEDGE_KEYWORD_FALLBACK_TIMEOUT_SECONDS,
                )
            except Exception as fallback_exc:
                logger.exception("[knowledge] keyword_fallback_failed request_id=%s error=%s", submission_id, fallback_exc.__class__.__name__)
                user_message = db.get(KnowledgeMessage, user_message.id)
                user_message.status, user_message.error = "failed", "知识库检索暂不可用，请稍后重试"
                db.commit()
                raise HTTPException(status_code=503, detail="知识库检索暂不可用，请稍后重试") from fallback_exc
        contexts = sorted(contexts, key=lambda c: c.get("score", 0), reverse=True)[:6]
        logger.info(
            "[knowledge] retrieval_done request_id=%s evidence=%s elapsed_ms=%s",
            submission_id, len(contexts), int((time.perf_counter() - retrieval_started_at) * 1000),
        )
        citations = [{
            "index": index,
            "document_id": item["document_id"],
            "document_title": item["title"],
            "source": item["source"],
            "source_url": item["source_url"],
            "chunk_id": item["chunk_id"],
            "chunk_index": item["chunk_index"],
            "excerpt": item["content"][:300],
        } for index, item in enumerate(contexts, start=1)]
        if contexts or images:
            try:
                logger.info("[knowledge] llm_answer_start request_id=%s citations=%s", submission_id, len(citations))
                raw_answer = await asyncio.wait_for(
                    ai_service.knowledge_answer(
                        data.question, contexts, history_payload, tool_call=tool_call, images=images or None,
                    ),
                    timeout=settings.KNOWLEDGE_LLM_TIMEOUT_SECONDS,
                )
                normalized = _normalize_answer(raw_answer, citations, data.question, contexts)
                logger.info("[knowledge] llm_answer_done request_id=%s citations=%s", submission_id, len(normalized["citations"]))
            except TimeoutError as exc:
                logger.warning("[knowledge] llm_answer_timeout request_id=%s", submission_id)
                user_message = db.get(KnowledgeMessage, user_message.id)
                user_message.status, user_message.error = "failed", "AI 回答超时，资料依据已检索完成"
                db.commit()
                raise HTTPException(status_code=503, detail="AI 回答超时，请稍后重试；资料依据已检索完成但未生成回答") from exc
            except Exception as exc:
                user_message = db.get(KnowledgeMessage, user_message.id)
                user_message.status, user_message.error = "failed", "AI 服务暂不可用，请稍后重试"
                db.commit()
                raise HTTPException(status_code=503, detail="AI 服务暂不可用，请稍后重试") from exc
            response_kind = "rag" if normalized["citations"] else "no_evidence"
            if not normalized["citations"] and images:
                uncited = _uncited_answer(raw_answer)
                if uncited is not None:
                    # 只有图片、没有命中资料：输出图片解读，不附引用编号
                    normalized = uncited
                    response_kind = "multimodal"
        else:
            normalized = {
                "answer": "当前知识库没有足够依据。你可以换一种更具体的问法，或先在资料库中搜索相关文件。",
                "answer_blocks": [], "citations": [], "used_citation_indexes": [], "follow_up_suggestions": [],
            }
            response_kind = "no_evidence"

    return _finish_answer(
        db=db, session=session, user_message=user_message, submission_id=submission_id,
        normalized=normalized, degraded=degraded, selected_tool=selected_tool, started_at=started_at,
        response_kind=response_kind,
    )


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
def get_sessions(
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = [
        KnowledgeSession.user_id == user.id,
        select(KnowledgeMessage.id).where(KnowledgeMessage.session_id == KnowledgeSession.id).exists(),
    ]
    if q:
        filters.append(KnowledgeSession.title.ilike(f"%{q.strip()}%"))
    total = db.scalar(select(func.count()).select_from(KnowledgeSession).where(*filters)) or 0
    rows = db.scalars(select(KnowledgeSession).where(*filters).order_by(
        KnowledgeSession.updated_at.desc()
    ).offset((page - 1) * page_size).limit(page_size)).all()
    return {"code": 0, "data": [{
        "id": row.id, "title": row.title, "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    } for row in rows], "pagination": {"page": page, "page_size": page_size, "total": total}}


@router.get("/sessions/{session_id}")
def get_session(session_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(KnowledgeSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = db.scalars(select(KnowledgeMessage).where(KnowledgeMessage.session_id == session.id).order_by(KnowledgeMessage.created_at.asc())).all()
    return {"code": 0, "data": {"id": session.id, "title": session.title, "messages": [_message_payload(item) for item in messages]}}


@router.patch("/sessions/{session_id}")
def update_session(session_id: str, data: SessionUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = db.get(KnowledgeSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="会话标题不能为空")
    session.title = title
    session.updated_at = datetime.utcnow()
    return {"code": 0, "data": {"id": session.id, "title": session.title, "updated_at": session.updated_at.isoformat()}}


@router.post("/messages/{message_id}/feedback")
def save_message_feedback(message_id: str, data: MessageFeedbackRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    message = db.get(KnowledgeMessage, message_id)
    session = db.get(KnowledgeSession, message.session_id) if message else None
    if not message or message.role != "assistant" or not session or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="回答不存在")
    message.feedback = "helpful" if data.helpful else "unhelpful"
    message.feedback_reason = data.reason.strip() or None
    return {"code": 0, "data": {"id": message.id, "feedback": message.feedback}}


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
