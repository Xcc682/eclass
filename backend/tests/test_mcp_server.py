"""MCP 知识库服务器的单测：直接调用工具底层实现，不启动 MCP 协议。"""

import json
import unittest
import uuid

from test_env import configure_test_environment

configure_test_environment()  # noqa: E402  # 必须在导入 app.config 之前隔离测试数据库

from sqlalchemy import delete  # noqa: E402

from app.database import SessionLocal, init_db  # noqa: E402
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument  # noqa: E402
from mcp_server import (  # noqa: E402
    _first_sentence,
    _get_document_outline_impl,
    _list_documents_impl,
    _search_knowledge_impl,
)


class McpKnowledgeToolsTests(unittest.TestCase):
    """覆盖检索命中、空查询、分类过滤、资料目录与未知 document_id。"""

    @classmethod
    def setUpClass(cls):
        init_db()
        cls.token = f"mcp{uuid.uuid4().hex[:12]}"
        cls.category_a = f"MCP入党{cls.token}"
        cls.category_b = f"MCP研学{cls.token}"
        with SessionLocal() as db:
            cls.doc_a = KnowledgeDocument(
                title=f"{cls.token} 入党动机学习材料",
                category=cls.category_a,
                content=f"{cls.token} 入党动机应当来自对党的认识与自身实践。这是第二句话。",
                summary="MCP 测试资料 A",
                source="MCP 测试来源 A",
                status="published",
                chunk_count=2,
            )
            cls.doc_b = KnowledgeDocument(
                title=f"{cls.token} 红色研学路线",
                category=cls.category_b,
                content=f"{cls.token} 红色研学路线覆盖多处革命旧址。这是第二句话。",
                summary="MCP 测试资料 B",
                source="MCP 测试来源 B",
                status="published",
                chunk_count=1,
            )
            cls.doc_hidden = KnowledgeDocument(
                title=f"{cls.token} 未发布资料",
                category=cls.category_a,
                content=f"{cls.token} 这份资料尚未审核发布，不应被检索或列出。",
                summary="MCP 测试资料 C",
                source="MCP 测试来源 C",
                status="pending_review",
                chunk_count=1,
            )
            db.add_all([cls.doc_a, cls.doc_b, cls.doc_hidden])
            db.flush()
            db.add_all(
                [
                    KnowledgeChunk(
                        document_id=cls.doc_a.id,
                        chunk_index=0,
                        content=f"{cls.token} 入党动机应当来自对党的认识与自身实践。后续内容不应出现在首句。",
                        char_count=40,
                        content_hash=f"{cls.token}-a0",
                    ),
                    KnowledgeChunk(
                        document_id=cls.doc_a.id,
                        chunk_index=1,
                        content=f"{cls.token} " + "长" * 900 + "。第二段结尾。",
                        char_count=920,
                        content_hash=f"{cls.token}-a1",
                    ),
                    KnowledgeChunk(
                        document_id=cls.doc_b.id,
                        chunk_index=0,
                        content=f"{cls.token} 红色研学路线覆盖多处革命旧址。第二句。",
                        char_count=30,
                        content_hash=f"{cls.token}-b0",
                    ),
                    KnowledgeChunk(
                        document_id=cls.doc_hidden.id,
                        chunk_index=0,
                        content=f"{cls.token} 未发布资料不应出现。",
                        char_count=20,
                        content_hash=f"{cls.token}-c0",
                    ),
                ]
            )
            db.commit()
            # 会话关闭后 ORM 属性会过期，测试只保留普通字符串，避免访问脱离会话的实例。
            cls.doc_a_id = cls.doc_a.id
            cls.doc_a_title = cls.doc_a.title
            cls.doc_a_source = cls.doc_a.source
            cls.doc_b_id = cls.doc_b.id
            cls.doc_b_title = cls.doc_b.title
            cls.doc_hidden_id = cls.doc_hidden.id
            cls.doc_hidden_title = cls.doc_hidden.title

    @classmethod
    def tearDownClass(cls):
        ids = [cls.doc_a_id, cls.doc_b_id, cls.doc_hidden_id]
        with SessionLocal() as db:
            db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id.in_(ids)))
            db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id.in_(ids)))
            db.commit()

    @staticmethod
    def _payload(raw: str):
        return json.loads(raw)

    def test_search_hits_published_document_and_truncates_content(self):
        results = self._payload(_search_knowledge_impl(self.token, limit=4))
        self.assertIsInstance(results, list)
        self.assertTrue(results)
        titles = {item["title"] for item in results}
        self.assertIn(self.doc_a_title, titles)
        self.assertNotIn(self.doc_hidden_title, titles)
        for item in results:
            self.assertTrue({"id", "document_id", "title", "source", "chunk_index", "content"} <= set(item))
            self.assertTrue(item["id"])
            self.assertIn(item["document_id"], {self.doc_a_id, self.doc_b_id})
            self.assertLessEqual(len(item["content"]), 800)

    def test_empty_query_returns_structured_error(self):
        for query in ("", "   "):
            with self.subTest(query=query):
                payload = self._payload(_search_knowledge_impl(query))
                self.assertEqual(payload["code"], "EMPTY_QUERY")
                self.assertIn("error", payload)

    def test_category_filter_limits_results(self):
        all_results = self._payload(_search_knowledge_impl(self.token, limit=10))
        self.assertIn(self.doc_b_title, {item["title"] for item in all_results})

        filtered = self._payload(_search_knowledge_impl(self.token, category=self.category_a, limit=10))
        self.assertTrue(filtered)
        self.assertEqual({item["title"] for item in filtered}, {self.doc_a_title})

    def test_list_documents_excludes_unpublished_and_filters_category(self):
        listed = self._payload(_list_documents_impl())
        ids = {item["id"] for item in listed}
        self.assertIn(self.doc_a_id, ids)
        self.assertIn(self.doc_b_id, ids)
        self.assertNotIn(self.doc_hidden_id, ids)
        for item in listed:
            self.assertEqual(set(item), {"id", "title", "category"})

        filtered = self._payload(_list_documents_impl(self.category_b))
        self.assertEqual({item["id"] for item in filtered}, {self.doc_b_id})

    def test_document_outline_returns_chunk_first_sentences(self):
        payload = self._payload(_get_document_outline_impl(self.doc_a_id))
        self.assertEqual(payload["title"], self.doc_a_title)
        self.assertEqual(payload["source"], self.doc_a_source)
        self.assertEqual(payload["chunk_count"], 2)
        self.assertEqual(payload["chunks"][0]["chunk_index"], 0)
        self.assertEqual(
            payload["chunks"][0]["first_sentence"],
            f"{self.token} 入党动机应当来自对党的认识与自身实践。",
        )

    def test_unknown_document_id_returns_structured_error(self):
        payload = self._payload(_get_document_outline_impl("missing-document-id"))
        self.assertEqual(payload["code"], "DOCUMENT_NOT_FOUND")
        self.assertIn("error", payload)

        hidden = self._payload(_get_document_outline_impl(self.doc_hidden_id))
        self.assertEqual(hidden["code"], "DOCUMENT_NOT_FOUND")

    def test_first_sentence_handles_punctuation_and_empty_content(self):
        self.assertEqual(_first_sentence("第一句。第二句。"), "第一句。")
        self.assertEqual(_first_sentence("没有句号"), "没有句号")
        self.assertEqual(_first_sentence(""), "")


if __name__ == "__main__":
    unittest.main()
