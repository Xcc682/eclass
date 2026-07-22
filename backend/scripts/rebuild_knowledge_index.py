"""Rebuild SQLite FTS5 and pgvector indexes for published knowledge documents."""
from pathlib import Path
import hashlib
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.services.knowledge_service import chunk_text, sync_fts, sync_vectors


def rebuild() -> tuple[int, int, int]:
    indexed_documents = 0
    indexed_chunks = 0
    vector_failures = 0
    with SessionLocal() as db:
        documents = db.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.status == "published")
            .order_by(KnowledgeDocument.created_at.asc())
        ).all()
        for document in documents:
            chunks = db.scalars(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.document_id == document.id)
                .order_by(KnowledgeChunk.chunk_index.asc())
            ).all()
            if not chunks:
                parts = chunk_text(document.content or "")
                chunks = [
                    KnowledgeChunk(
                        document_id=document.id,
                        chunk_index=index,
                        content=content,
                        char_count=len(content),
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                    )
                    for index, content in enumerate(parts)
                ]
                db.add_all(chunks)
                document.chunk_count = len(chunks)
                db.commit()
            if not chunks:
                print(f"SKIP {document.id}: no content")
                continue
            sync_fts(document.id, chunks)
            vector_ok = sync_vectors(document.id, chunks)
            indexed_documents += 1
            indexed_chunks += len(chunks)
            vector_failures += int(not vector_ok)
            print(f"INDEXED {document.id}: chunks={len(chunks)} vector={vector_ok}")
    return indexed_documents, indexed_chunks, vector_failures


if __name__ == "__main__":
    document_count, chunk_count, failures = rebuild()
    print({"documents": document_count, "chunks": chunk_count, "vector_failures": failures})
    if failures:
        raise SystemExit(1)
