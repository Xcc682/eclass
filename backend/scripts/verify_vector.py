"""Verify pgvector indexing and retrieval, then remove the smoke-test row."""
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app.services.knowledge_service import _vector_engine, _vector_hits, sync_vectors


DOCUMENT_ID = "configuration-smoke-document"
CHUNK_ID = "configuration-smoke-test"


def main() -> None:
    chunk = SimpleNamespace(id=CHUNK_ID, content="红船精神")
    indexed = sync_vectors(DOCUMENT_ID, [chunk])
    hits = _vector_hits("红船精神", 5)
    retrieved = any(item["chunk_id"] == CHUNK_ID for item in hits)
    print({"indexed": indexed, "retrieved": retrieved, "hit_count": len(hits)})
    if not indexed or not retrieved:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    finally:
        engine = _vector_engine()
        if engine is not None:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM knowledge_vectors WHERE document_id = :document_id"),
                    {"document_id": DOCUMENT_ID},
                )
