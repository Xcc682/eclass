"""Shared, isolated environment for the unittest suite."""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def configure_test_environment() -> None:
    root = Path(__file__).resolve().parents[1]
    database = root / "test.db"
    community_storage = root / "tests" / "_community_storage"
    if os.environ.get("ECLASS_TEST_ENV_READY") != "1":
        database.unlink(missing_ok=True)
        shutil.rmtree(community_storage, ignore_errors=True)
        os.environ["ECLASS_TEST_ENV_READY"] = "1"
    os.environ["ENV"] = "test"
    os.environ["DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    os.environ["DATABASE_URL_SYNC"] = f"sqlite:///{database.as_posix()}"
    # Vector integration has its own opt-in test. Unit/API tests must never
    # depend on, or mutate, the developer's Docker database.
    os.environ["VECTOR_DATABASE_URL"] = ""
    # 自主检索 Agent 会真实调用模型；API 层测试聚焦固定检索链路，Agent 由
    # test_knowledge_agent.py 用假模型单独覆盖。
    os.environ["KNOWLEDGE_AGENT_ENABLED"] = "false"
    # 多查询改写、LLM 重排、语义缓存与引用核验都会真实调用模型；API 层测试
    # 默认关闭，相关模块由各自的单元测试用假模型覆盖。
    os.environ["RETRIEVAL_MULTI_QUERY_ENABLED"] = "false"
    os.environ["RETRIEVAL_RERANK_ENABLED"] = "false"
    os.environ["SEMANTIC_CACHE_ENABLED"] = "false"
    os.environ["GROUNDING_CHECK_ENABLED"] = "false"
    os.environ["COMMUNITY_STORAGE_DIR"] = community_storage.as_posix()
    os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-with-at-least-32-characters")
