"""Knowledge document parsing, chunking and hybrid retrieval."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from sqlalchemy import create_engine, delete, or_, select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, engine
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeIngestionJob

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/octet-stream",
}
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80
logger = logging.getLogger("app.knowledge")


def normalize_text(value: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    paragraphs = [re.sub(r"[ \t]+", " ", part).strip() for part in re.split(r"\n{2,}", value)]
    return "\n\n".join(part for part in paragraphs if part)


def parse_document(path: str | Path) -> str:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        content = "\n\n".join(page.extract_text() or "" for page in PdfReader(str(file_path)).pages)
    elif suffix == ".docx":
        from docx import Document

        content = "\n\n".join(paragraph.text for paragraph in Document(str(file_path)).paragraphs)
    elif suffix in {".txt", ".md"}:
        raw = file_path.read_bytes()
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                content = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("文本文件编码无法识别，请使用 UTF-8 编码")
    else:
        raise ValueError("不支持的文件格式")
    content = normalize_text(content)
    if not content:
        raise ValueError("未解析到文本内容；扫描版 PDF 暂不支持，请上传文字版文件")
    return content


def chunk_text(content: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("分段参数不合法")
    text_value = normalize_text(content)
    if not text_value:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text_value):
        end = min(start + size, len(text_value))
        if end < len(text_value):
            candidates = [text_value.rfind(mark, start + size // 2, end) for mark in ("\n\n", "。", "！", "？", "；")]
            boundary = max(candidates)
            if boundary > start:
                end = boundary + (2 if text_value[boundary:boundary + 2] == "\n\n" else 1)
        chunk = text_value[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text_value):
            break
        start = max(start + 1, end - overlap)
    return chunks


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ensure_fts() -> bool:
    if engine.dialect.name != "sqlite":
        return False
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, content, tokenize='trigram')"))
        return True
    except Exception:
        try:
            with engine.begin() as connection:
                connection.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_chunks_fts USING fts5(chunk_id UNINDEXED, document_id UNINDEXED, content, tokenize='unicode61')"))
            return True
        except Exception:
            return False


def sync_fts(document_id: str, chunks: list[KnowledgeChunk]) -> None:
    if not _ensure_fts():
        return
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM knowledge_chunks_fts WHERE document_id = :document_id"), {"document_id": document_id})
        for chunk in chunks:
            connection.execute(
                text("INSERT INTO knowledge_chunks_fts(chunk_id, document_id, content) VALUES (:chunk_id, :document_id, :content)"),
                {"chunk_id": chunk.id, "document_id": document_id, "content": chunk.content},
            )


_model: Any = None
_model_lock = Lock()
_warmup_lock = Lock()
_warmup_started = False


def _embedding_model() -> Any:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


_vector_engine_instance: Any = None
_vector_engine_url: str | None = None
_vector_engine_lock = Lock()


def _vector_engine():
    if not settings.VECTOR_DATABASE_URL:
        return None
    global _vector_engine_instance, _vector_engine_url
    with _vector_engine_lock:
        if _vector_engine_instance is None or _vector_engine_url != settings.VECTOR_DATABASE_URL:
            _vector_engine_instance = create_engine(settings.VECTOR_DATABASE_URL, pool_pre_ping=True)
            _vector_engine_url = settings.VECTOR_DATABASE_URL
    return _vector_engine_instance


def _log_retrieval_stage(stage: str, **extra: Any) -> None:
    details = " ".join(f"{key}={value}" for key, value in extra.items())
    logger.info("[knowledge] %s %s", stage, details)


def _warm_embedding_worker() -> None:
    try:
        _log_retrieval_stage("embedding_warmup_start", model=settings.EMBEDDING_MODEL)
        _embedding_model()
        _log_retrieval_stage("embedding_warmup_done", model=settings.EMBEDDING_MODEL)
    except Exception as exc:
        logger.warning("[knowledge] embedding_warmup_failed error=%s: %s", exc.__class__.__name__, exc)


def start_embedding_warmup() -> bool:
    """Start a non-blocking embedding model warmup after app startup."""
    global _warmup_started
    if not settings.VECTOR_DATABASE_URL or _model is not None:
        return False
    with _warmup_lock:
        if _warmup_started:
            return False
        _warmup_started = True
    Thread(target=_warm_embedding_worker, name="knowledge-embedding-warmup", daemon=True).start()
    return True


def _ensure_vector_schema(vector_engine) -> None:
    with vector_engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        connection.execute(text(f"""CREATE TABLE IF NOT EXISTS knowledge_vectors (
            chunk_id VARCHAR PRIMARY KEY,
            document_id VARCHAR NOT NULL,
            content TEXT NOT NULL,
            embedding vector({settings.EMBEDDING_DIMENSION}) NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )"""))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_vectors_document ON knowledge_vectors(document_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_vectors_hnsw ON knowledge_vectors USING hnsw (embedding vector_cosine_ops)"))


def sync_vectors(document_id: str, chunks: list[KnowledgeChunk]) -> bool:
    vector_engine = _vector_engine()
    if vector_engine is None:
        return False
    try:
        _ensure_vector_schema(vector_engine)
        vectors = _embedding_model().encode([chunk.content for chunk in chunks], normalize_embeddings=True)
        with vector_engine.begin() as connection:
            connection.execute(text("DELETE FROM knowledge_vectors WHERE document_id = :document_id"), {"document_id": document_id})
            for chunk, vector in zip(chunks, vectors):
                connection.execute(text("""INSERT INTO knowledge_vectors(chunk_id, document_id, content, embedding)
                    VALUES (:chunk_id, :document_id, :content, CAST(:embedding AS vector))
                    ON CONFLICT (chunk_id) DO UPDATE SET content=EXCLUDED.content, embedding=EXCLUDED.embedding, updated_at=now()"""), {
                    "chunk_id": chunk.id,
                    "document_id": document_id,
                    "content": chunk.content,
                    "embedding": "[" + ",".join(str(float(item)) for item in vector) + "]",
                })
        return True
    except Exception as exc:
        print(f"[knowledge] vector indexing unavailable: {exc.__class__.__name__}: {exc}", flush=True)
        return False


def purge_document_indexes(document_id: str) -> list[str]:
    """Remove a document from every retrieval index and return non-fatal warnings."""
    warnings: list[str] = []
    if _ensure_fts():
        try:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM knowledge_chunks_fts WHERE document_id = :document_id"),
                    {"document_id": document_id},
                )
        except Exception as exc:
            warnings.append(f"全文索引清理失败：{exc.__class__.__name__}")

    vector_engine = _vector_engine()
    if vector_engine is not None:
        try:
            _ensure_vector_schema(vector_engine)
            with vector_engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM knowledge_vectors WHERE document_id = :document_id"),
                    {"document_id": document_id},
                )
        except Exception as exc:
            warnings.append(f"向量索引清理失败：{exc.__class__.__name__}")
    return warnings


def process_document(
    document_id: str,
    job_id: str,
    final_status: str = "pending_review",
    failure_status: str = "failed",
    mark_processing: bool = True,
) -> None:
    db = SessionLocal()
    try:
        document = db.get(KnowledgeDocument, document_id)
        job = db.get(KnowledgeIngestionJob, job_id)
        if not document or not job or not document.file_path:
            return
        if mark_processing:
            document.status = "processing"
        document.processing_error = None
        job.status = "processing"
        job.progress = 10
        db.commit()

        content = parse_document(document.file_path)
        parts = chunk_text(content)
        if not parts:
            raise ValueError("文档没有可索引内容")
        job.progress = 35
        db.commit()

        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
        chunks = [KnowledgeChunk(
            document_id=document_id,
            chunk_index=index,
            content=part,
            char_count=len(part),
            content_hash=hashlib.sha256(part.encode("utf-8")).hexdigest(),
        ) for index, part in enumerate(parts)]
        db.add_all(chunks)
        document.content = content
        document.summary = document.summary or content[:200]
        document.chunk_count = len(chunks)
        db.flush()
        db.commit()

        sync_fts(document_id, chunks)
        job.progress = 70
        db.commit()

        vector_ok = sync_vectors(document_id, chunks)
        job.progress = 90
        if settings.VECTOR_DATABASE_URL and not vector_ok:
            job.error = "向量索引暂不可用，全文索引已完成，可稍后再次重建"
        document.status = final_status
        job.status = "completed"
        job.progress = 100
        db.commit()
    except Exception as exc:
        db.rollback()
        document = db.get(KnowledgeDocument, document_id)
        job = db.get(KnowledgeIngestionJob, job_id)
        message = str(exc)[:2000]
        if document:
            document.status = failure_status
            document.processing_error = message
        if job:
            job.status = "failed"
            job.error = message
        db.commit()
    finally:
        db.close()


_QUESTION_FILLERS = (
    "请问", "请介绍", "介绍一下", "简要介绍", "主要内容", "核心内涵", "核心要求",
    "有什么", "是什么", "有哪些", "为什么", "怎么样", "怎么做", "如何", "是否",
    "相关资料", "这份资料", "一下", "吗", "呢", "？", "?", "的",
)


def _keyword_terms(query: str, max_terms: int = 18) -> list[str]:
    """Build tolerant Chinese search terms from a natural-language question.

    FTS5 treats a full question as an AND expression. During embedding model
    warmup that made keyword fallback reject relevant documents merely because
    generic words such as “是什么” were absent. Domain phrases and overlapping
    n-grams provide deterministic retrieval without depending on page visits.
    """
    parts = re.findall(r"[A-Za-z0-9_]+|[\u3400-\u9fff]+", query.lower())
    terms: list[str] = []

    def add(value: str) -> None:
        value = value.strip()
        if len(value) >= 2 and value not in terms:
            terms.append(value)

    for part in parts:
        if re.fullmatch(r"[a-z0-9_]+", part):
            add(part)
            continue
        cleaned = part
        for filler in _QUESTION_FILLERS:
            cleaned = cleaned.replace(filler, " ")
        for phrase in re.findall(r"[\u3400-\u9fff]+", cleaned):
            if len(phrase) <= 20:
                add(phrase)
            for width in (6, 4, 3):
                if len(phrase) < width:
                    continue
                for index in range(len(phrase) - width + 1):
                    add(phrase[index:index + width])
                    if len(terms) >= max_terms:
                        return terms
        if len(terms) >= max_terms:
            break
    return terms[:max_terms]


def _keyword_hits(db: Session, query: str, category: str | None, limit: int = 20) -> list[dict]:
    terms = _keyword_terms(query)
    if engine.dialect.name == "sqlite" and _ensure_fts():
        try:
            sql = """SELECT c.id AS chunk_id, c.document_id, c.chunk_index, c.content, bm25(knowledge_chunks_fts) AS score
                     FROM knowledge_chunks_fts
                     JOIN knowledge_chunks c ON c.id = knowledge_chunks_fts.chunk_id
                     JOIN knowledge_documents d ON d.id = c.document_id
                     WHERE knowledge_chunks_fts MATCH :query AND d.status = 'published'"""
            fts_terms = [term for term in terms if len(term) >= 3]
            fts_query = " OR ".join(f'"{term}"' for term in fts_terms) or query
            params: dict[str, Any] = {
                "query": fts_query,
                "title_pattern": f"%{terms[0] if terms else query}%",
                "limit": limit,
            }
            if category:
                sql += " AND d.category = :category"
                params["category"] = category
            sql += " ORDER BY CASE WHEN d.title LIKE :title_pattern THEN 0 ELSE 1 END, score LIMIT :limit"
            rows = [dict(row._mapping) for row in db.execute(text(sql), params)]
            if rows:
                return rows
        except Exception as exc:
            logger.warning("SQLite FTS retrieval failed; falling back to LIKE search: %s", exc)
    patterns = terms or [query]
    content_filters = [KnowledgeChunk.content.ilike(f"%{term}%") for term in patterns[:12]]
    statement = (select(KnowledgeChunk)
                 .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
                 .where(KnowledgeDocument.status == "published", or_(*content_filters)))
    if category:
        statement = statement.where(KnowledgeDocument.category == category)
    chunks = db.scalars(statement.limit(limit)).all()
    return [{"chunk_id": chunk.id, "document_id": chunk.document_id, "chunk_index": chunk.chunk_index, "content": chunk.content, "score": index} for index, chunk in enumerate(chunks)]


def _vector_hits(query: str, limit: int = 20) -> list[dict]:
    vector_engine = _vector_engine()
    if vector_engine is None:
        return []
    try:
        _log_retrieval_stage("vector_retrieval_start", limit=limit)
        _ensure_vector_schema(vector_engine)
        vector = _embedding_model().encode([query], normalize_embeddings=True)[0]
        value = "[" + ",".join(str(float(item)) for item in vector) + "]"
        with vector_engine.connect() as connection:
            rows = connection.execute(text("""SELECT chunk_id, document_id, content,
                embedding <=> CAST(:embedding AS vector) AS score
                FROM knowledge_vectors
                WHERE embedding <=> CAST(:embedding AS vector) <= :max_distance
                ORDER BY score LIMIT :limit"""), {
                    "embedding": value,
                    "max_distance": settings.VECTOR_MAX_COSINE_DISTANCE,
                    "limit": limit,
                })
            result = [dict(row._mapping) for row in rows]
            _log_retrieval_stage("vector_retrieval_done", hits=len(result))
            return result
    except Exception as exc:
        logger.warning("[knowledge] vector_retrieval_unavailable error=%s: %s", exc.__class__.__name__, exc)
        return []


def retrieve(db: Session, query: str, category: str | None = None, limit: int = 6, use_vector: bool = True) -> list[dict]:
    _log_retrieval_stage("keyword_retrieval_start", category=category or "all")
    keyword = _keyword_hits(db, query, category)
    _log_retrieval_stage("keyword_retrieval_done", hits=len(keyword))
    vector = _vector_hits(query) if use_vector else []
    fused: dict[str, dict] = {}
    for source, rows in (("keyword", keyword), ("vector", vector)):
        for rank, row in enumerate(rows, start=1):
            chunk_id = row["chunk_id"]
            entry = fused.setdefault(chunk_id, {**row, "rrf_score": 0.0, "retrieval": []})
            entry["rrf_score"] += 1.0 / (60 + rank)
            entry["retrieval"].append(source)
    ordered = sorted(fused.values(), key=lambda item: item["rrf_score"], reverse=True)
    results: list[dict] = []
    for item in ordered:
        chunk = db.get(KnowledgeChunk, item["chunk_id"])
        document = db.get(KnowledgeDocument, item["document_id"])
        if not chunk or not document or document.status != "published" or (category and document.category != category):
            continue
        results.append({
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "document_id": document.id,
            "title": document.title,
            "source": document.source,
            "source_url": document.source_url,
            "category": document.category,
            "score": item["rrf_score"],
            "retrieval": item["retrieval"],
        })
        if len(results) >= limit:
            break
    if not results:
        terms = _keyword_terms(query) or [query]
        document_filters = []
        for term in terms[:12]:
            pattern = f"%{term}%"
            document_filters.extend((
                KnowledgeDocument.title.ilike(pattern),
                KnowledgeDocument.content.ilike(pattern),
                KnowledgeDocument.summary.ilike(pattern),
            ))
        statement = select(KnowledgeDocument).where(
            KnowledgeDocument.status == "published",
            or_(*document_filters),
        )
        if category:
            statement = statement.where(KnowledgeDocument.category == category)
        for document in db.scalars(statement.limit(limit)).all():
            results.append({
                "chunk_id": f"legacy:{document.id}",
                "chunk_index": 0,
                "content": document.content[:CHUNK_SIZE],
                "document_id": document.id,
                "title": document.title,
                "source": document.source,
                "source_url": document.source_url,
                "category": document.category,
                "score": 0.01,
                "retrieval": ["legacy_keyword"],
            })
    return results


def retrieve_with_fresh_session(query: str, category: str | None = None, limit: int = 6, use_vector: bool = True) -> list[dict]:
    """Run retrieval in an isolated DB session so callers may safely offload it."""
    db = SessionLocal()
    try:
        return retrieve(db, query, category, limit=limit, use_vector=use_vector)
    finally:
        db.close()


async def retrieve_async(query: str, category: str | None = None, limit: int = 6, use_vector: bool = True) -> list[dict]:
    return await asyncio.to_thread(retrieve_with_fresh_session, query, category, limit, use_vector)


def retrieval_status() -> dict:
    return {
        "mode": "hybrid" if settings.VECTOR_DATABASE_URL else "sqlite_fts5",
        "vector_configured": bool(settings.VECTOR_DATABASE_URL),
        "embedding_model": settings.EMBEDDING_MODEL,
        "embedding_loaded": _model is not None,
        "embedding_warmup_started": _warmup_started,
    }
