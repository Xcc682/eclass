import tempfile
import unittest
import uuid
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from test_env import configure_test_environment

configure_test_environment()

from fastapi.testclient import TestClient
from sqlalchemy import bindparam, delete, select, text

from app.database import SessionLocal
from app.main import app
from app.models.user import User
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument, KnowledgeFavorite, KnowledgeIngestionJob, KnowledgeMessage, KnowledgeView
from app.services.knowledge_service import _vector_engine, chunk_text, parse_document


class KnowledgeUnitTests(unittest.TestCase):
    def test_chunk_overlap_and_text_parser(self):
        content = "第一段。" * 180
        chunks = chunk_text(content, size=120, overlap=20)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(set(chunks[0][-20:]).intersection(set(chunks[1][:20])))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.txt"
            path.write_text("标题\n\n正文内容", encoding="utf-8")
            self.assertEqual(parse_document(path), "标题\n\n正文内容")


class KnowledgeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = TestClient(app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)

    def tearDown(self):
        with SessionLocal() as db:
            documents = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source == "测试权威来源")).all()
            ids = [item.id for item in documents]
            paths = [Path(item.file_path) for item in documents if item.file_path]
            if ids:
                db.execute(delete(KnowledgeView).where(KnowledgeView.document_id.in_(ids)))
                db.execute(delete(KnowledgeFavorite).where(KnowledgeFavorite.document_id.in_(ids)))
                db.execute(delete(KnowledgeIngestionJob).where(KnowledgeIngestionJob.document_id.in_(ids)))
                db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id.in_(ids)))
                db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id.in_(ids)))
                try:
                    for document_id in ids:
                        db.execute(text("DELETE FROM knowledge_chunks_fts WHERE document_id = :id"), {"id": document_id})
                except Exception:
                    pass
                db.commit()
            storage = (Path(__file__).resolve().parents[1] / "storage" / "knowledge").resolve()
            for path in paths:
                resolved = path.resolve()
                if storage in resolved.parents and resolved.is_file():
                    resolved.unlink()
            vector_engine = _vector_engine()
            if vector_engine is not None and ids:
                with vector_engine.begin() as connection:
                    connection.execute(
                        text("DELETE FROM knowledge_vectors WHERE document_id IN :document_ids")
                        .bindparams(bindparam("document_ids", expanding=True)),
                        {"document_ids": ids},
                    )

    def login(self, phone: str, role: str = "student") -> dict[str, str]:
        response = self.client.post("/api/v1/auth/login", json={"phone": phone, "password": "test-password"})
        self.assertEqual(response.status_code, 200)
        user_id = response.json()["data"]["user"]["id"]
        if role != "student":
            with SessionLocal() as db:
                user = db.get(User, user_id)
                user.role = role
                db.commit()
            response = self.client.post("/api/v1/auth/login", json={"phone": phone, "password": "test-password"})
        return {"Authorization": f"Bearer {response.json()['data']['token']}"}

    def test_upload_permission_limits_and_complete_flow(self):
        random_part = uuid.uuid4().hex[:8]
        student = self.login(f"136{uuid.uuid4().int % 100_000_000:08d}")
        teacher = self.login(f"137{uuid.uuid4().int % 100_000_000:08d}", "teacher")
        fields = {"title": f"测试权威资料{random_part}", "category": "测试分类", "source": "测试权威来源", "source_url": "https://example.edu/source", "version": "1"}
        file_bytes = f"{random_part}是本资料的检索标识。\n\n这是经过审核后才能用于回答的正文内容。".encode()

        forbidden = self.client.post("/api/v1/knowledge/documents/upload", headers=student, data=fields, files={"file": ("sample.txt", file_bytes, "text/plain")})
        self.assertEqual(forbidden.status_code, 403)
        invalid = self.client.post("/api/v1/knowledge/documents/upload", headers=teacher, data=fields, files={"file": ("sample.exe", b"bad", "application/octet-stream")})
        self.assertEqual(invalid.status_code, 415)

        uploaded = self.client.post("/api/v1/knowledge/documents/upload", headers=teacher, data=fields, files={"file": ("sample.txt", file_bytes, "text/plain")})
        self.assertEqual(uploaded.status_code, 202, uploaded.text)
        data = uploaded.json()["data"]
        document_id, job_id = data["document"]["id"], data["job_id"]
        job = self.client.get(f"/api/v1/knowledge/ingestion-jobs/{job_id}", headers=teacher)
        self.assertEqual(job.json()["data"]["status"], "completed")

        duplicate = self.client.post(
            "/api/v1/knowledge/documents/upload",
            headers=teacher,
            data=fields,
            files={"file": ("renamed-sample.txt", file_bytes, "text/plain")},
        )
        self.assertEqual(duplicate.status_code, 409)
        duplicate_detail = duplicate.json()["detail"]
        self.assertEqual(duplicate_detail["code"], "DUPLICATE_DOCUMENT")
        self.assertEqual(duplicate_detail["document"]["id"], document_id)

        corrected_fields = {
            "title": f"修正后的资料标题{random_part}",
            "category": "修正分类",
            "source": "修正后的权威来源",
            "source_url": "https://example.edu/corrected",
            "summary": "用于验证资料信息编辑功能。",
            "version": 2,
        }
        corrected = self.client.put(f"/api/v1/knowledge/documents/{document_id}", headers=teacher, json=corrected_fields)
        self.assertEqual(corrected.status_code, 200, corrected.text)
        self.assertEqual(corrected.json()["data"]["title"], corrected_fields["title"])
        self.assertEqual(corrected.json()["data"]["version"], 2)

        before = self.client.post("/api/v1/knowledge/search", headers=student, json={"query": random_part})
        self.assertEqual(before.json()["data"], [])
        published = self.client.post(f"/api/v1/knowledge/documents/{document_id}/publish", headers=teacher)
        self.assertEqual(published.status_code, 200)

        with SessionLocal() as db:
            active_job = KnowledgeIngestionJob(document_id=document_id, status="queued", progress=0)
            db.add(active_job)
            db.commit()
            active_job_id = active_job.id
        conflict = self.client.post(f"/api/v1/knowledge/documents/{document_id}/reindex", headers=teacher)
        self.assertEqual(conflict.status_code, 409)
        edit_conflict = self.client.put(f"/api/v1/knowledge/documents/{document_id}", headers=teacher, json=corrected_fields)
        self.assertEqual(edit_conflict.status_code, 409)
        delete_conflict = self.client.delete(f"/api/v1/knowledge/documents/{document_id}", headers=teacher)
        self.assertEqual(delete_conflict.status_code, 409)
        with SessionLocal() as db:
            db.get(KnowledgeIngestionJob, active_job_id).status = "completed"
            db.commit()

        reindexed = self.client.post(f"/api/v1/knowledge/documents/{document_id}/reindex", headers=teacher)
        self.assertEqual(reindexed.status_code, 202)
        reindex_job = self.client.get(
            f"/api/v1/knowledge/ingestion-jobs/{reindexed.json()['data']['job_id']}",
            headers=teacher,
        ).json()["data"]
        self.assertEqual(reindex_job["status"], "completed")
        self.assertEqual(reindex_job["document_status"], "published")
        with SessionLocal() as db:
            self.assertEqual(db.get(KnowledgeDocument, document_id).status, "published")

        with patch("app.services.knowledge_service.parse_document", side_effect=ValueError("reindex failed")):
            failed_reindex = self.client.post(f"/api/v1/knowledge/documents/{document_id}/reindex", headers=teacher)
        failed_job = self.client.get(
            f"/api/v1/knowledge/ingestion-jobs/{failed_reindex.json()['data']['job_id']}",
            headers=teacher,
        ).json()["data"]
        self.assertEqual(failed_job["status"], "failed")
        self.assertEqual(failed_job["document_status"], "published")

        rejected = self.client.post(
            f"/api/v1/knowledge/documents/{document_id}/reject",
            headers=teacher,
            json={"reason": "标题仍需调整"},
        )
        self.assertEqual(rejected.status_code, 200)
        corrected_fields["title"] = f"最终资料标题{random_part}"
        self.assertEqual(
            self.client.put(f"/api/v1/knowledge/documents/{document_id}", headers=teacher, json=corrected_fields).status_code,
            200,
        )
        resubmitted = self.client.post(f"/api/v1/knowledge/documents/{document_id}/resubmit", headers=teacher)
        self.assertEqual(resubmitted.status_code, 200)
        self.assertEqual(resubmitted.json()["data"]["status"], "pending_review")
        self.assertEqual(self.client.post(f"/api/v1/knowledge/documents/{document_id}/publish", headers=teacher).status_code, 200)

        after = self.client.post("/api/v1/knowledge/search", headers=student, json={"query": random_part})
        self.assertEqual(after.json()["data"][0]["id"], document_id)

        with patch("app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock(return_value="根据资料，结论有明确依据。[1]")):
            answered = self.client.post("/api/v1/knowledge/ask", headers=student, json={"question": random_part})
        self.assertEqual(answered.status_code, 200)
        answer_data = answered.json()["data"]
        self.assertEqual(answer_data["citations"][0]["document_id"], document_id)
        self.assertTrue(answer_data["session_id"])

        # Natural-language question words must not make keyword fallback miss
        # an indexed document while the embedding model is still warming up.
        with patch("app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock(return_value="自然语言检索命中资料。[1]")):
            natural_answer = self.client.post(
                "/api/v1/knowledge/ask",
                headers=student,
                json={"question": f"请问资料中的{random_part}主要说明了什么？"},
            )
        self.assertEqual(natural_answer.status_code, 200, natural_answer.text)
        self.assertEqual(natural_answer.json()["data"]["citations"][0]["document_id"], document_id)

        self.assertEqual(self.client.post(f"/api/v1/knowledge/favorites/{document_id}", headers=student).status_code, 200)
        favorites = self.client.get("/api/v1/knowledge/favorites", headers=student).json()["data"]
        self.assertIn(document_id, [item["id"] for item in favorites])
        self.assertEqual(self.client.get(f"/api/v1/knowledge/documents/{document_id}", headers=student).status_code, 200)
        recent = self.client.get("/api/v1/knowledge/recent", headers=student).json()["data"]
        self.assertIn(document_id, [item["id"] for item in recent])

        with SessionLocal() as db:
            stored_path = db.get(KnowledgeDocument, document_id).file_path
        deleted = self.client.delete(f"/api/v1/knowledge/documents/{document_id}", headers=teacher)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertTrue(deleted.json()["data"]["deleted"])
        self.assertFalse(Path(stored_path).exists())
        self.assertEqual(self.client.get(f"/api/v1/knowledge/documents/{document_id}", headers=teacher).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/knowledge/search", headers=student, json={"query": random_part}).json()["data"], [])

        uploaded_again = self.client.post(
            "/api/v1/knowledge/documents/upload",
            headers=teacher,
            data=fields,
            files={"file": ("sample-again.txt", file_bytes, "text/plain")},
        )
        self.assertEqual(uploaded_again.status_code, 202, uploaded_again.text)

    def test_no_evidence_refuses_without_calling_ai(self):
        headers = self.login(f"135{uuid.uuid4().int % 100_000_000:08d}")
        with patch("app.routers.knowledge.retrieve_async", new=AsyncMock(return_value=[])), patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock()
        ) as mocked:
            response = self.client.post("/api/v1/knowledge/ask", headers=headers, json={"question": f"不存在的证据{uuid.uuid4().hex}"})
        self.assertEqual(response.json()["data"]["answer"], "当前知识库没有足够依据。")
        session_id = response.json()["data"]["session_id"]
        other_headers = self.login(f"133{uuid.uuid4().int % 100_000_000:08d}")
        self.assertEqual(self.client.delete(f"/api/v1/knowledge/sessions/{session_id}", headers=other_headers).status_code, 404)
        deleted = self.client.delete(f"/api/v1/knowledge/sessions/{session_id}", headers=headers)
        self.assertEqual(deleted.status_code, 200)
        self.assertTrue(deleted.json()["data"]["deleted"])
        self.assertEqual(self.client.get(f"/api/v1/knowledge/sessions/{session_id}", headers=headers).status_code, 404)
        with SessionLocal() as db:
            self.assertEqual(len(db.scalars(select(KnowledgeMessage).where(KnowledgeMessage.session_id == session_id)).all()), 0)
        mocked.assert_not_awaited()

    def test_vector_timeout_falls_back_to_keyword_retrieval(self):
        headers = self.login(f"134{uuid.uuid4().int % 100_000_000:08d}")
        fallback_context = [{
            "document_id": "doc-timeout-fallback",
            "title": "测试资料",
            "source": "测试来源",
            "source_url": "",
            "chunk_id": "chunk-timeout-fallback",
            "chunk_index": 0,
            "content": "用于验证向量检索超时后仍可使用关键词检索回答。",
        }]
        retrieve_mock = AsyncMock(side_effect=[asyncio.TimeoutError(), fallback_context])
        with patch("app.routers.knowledge.retrieve_async", new=retrieve_mock), patch(
            "app.routers.knowledge.ai_service.knowledge_answer", new=AsyncMock(return_value="已使用降级检索回答。[1]")
        ) as answer_mock:
            response = self.client.post("/api/v1/knowledge/ask", headers=headers, json={"question": "验证降级检索"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"]["citations"][0]["document_id"], "doc-timeout-fallback")
        self.assertEqual(retrieve_mock.await_count, 2)
        answer_mock.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
