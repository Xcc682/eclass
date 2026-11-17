"""思政情景工坊知识库 MCP 服务器。

通过 stdio 传输把知识库的检索能力暴露给任意 MCP 客户端（Claude Desktop、
Claude Code、自研 Agent 等），共提供三个工具：

- ``search_knowledge``：在已发布资料中做混合检索，返回资料片段；
- ``list_documents``：列出已发布资料目录，最多 50 条；
- ``get_document_outline``：查看某份资料的标题、来源、分块数与各分块首句。

直接启动（stdio 进程，通常由 MCP 客户端拉起）：

    cd backend
    python mcp_server.py

Claude Desktop 的 ``claude_desktop_config.json`` 示例：

    {
      "mcpServers": {
        "eclass-knowledge": {
          "command": "python",
          "args": ["F:/eclass/backend/mcp_server.py"]
        }
      }
    }

任意其他 MCP 客户端的 stdio 配置等价于：``command="python"``，
``args=["/absolute/path/to/eclass/backend/mcp_server.py"]``。服务器启动时会自动
切换到 ``backend`` 目录，因此无需配置 cwd；若客户端支持 cwd，也可以显式指定。

工具实现与 FastMCP 注册分离：``_*_impl`` 函数可以独立调用和测试，出错时返回
``{"error": ..., "code": ...}`` 形式的 JSON 字符串，不向客户端抛出异常栈。
"""

import json
import logging
import os
import re
from pathlib import Path

from sqlalchemy import select

try:  # mcp 1.x：官方 FastMCP
    from mcp.server.fastmcp import FastMCP
except ImportError:  # mcp 2.x：FastMCP 更名为 MCPServer，基础用法保持一致
    from mcp.server.mcpserver import MCPServer as FastMCP

# MCP 客户端拉起的 stdio 进程工作目录不可控。先切到 backend 目录，再导入
# app.*，确保 pydantic-settings 能读到 backend/.env，相对 SQLite 路径也正确。
os.chdir(Path(__file__).resolve().parent)

from app.database import SessionLocal  # noqa: E402
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument  # noqa: E402
from app.services.knowledge_service import retrieve  # noqa: E402

logger = logging.getLogger("app.mcp")

SEARCH_CONTENT_LIMIT = 800
MAX_DOCUMENTS = 50
MAX_SEARCH_LIMIT = 10
MAX_QUERY_CHARS = 300
MAX_SENTENCE_CHARS = 160
_SENTENCE_END = re.compile(r"[。！？!?；;\n]")


def _dump(payload: object) -> str:
    """把返回值序列化为 MCP 文本内容，保留中文可读性。"""
    return json.dumps(payload, ensure_ascii=False)


def _error(code: str, message: str) -> str:
    """构造结构化错误字符串，避免把异常栈暴露给外部 Agent。"""
    return _dump({"error": message, "code": code})


def _bounded_limit(limit: int) -> int:
    """把工具入参限制在 1-10 之间，非法值回退为默认的 4。"""
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return 4
    return max(1, min(MAX_SEARCH_LIMIT, value))


def _first_sentence(content: str) -> str:
    """截取片段首句（保留句末标点），便于外部 Agent 判断是否细读。"""
    text = (content or "").strip()
    if not text:
        return ""
    match = _SENTENCE_END.search(text)
    sentence = text[: match.end()] if match else text
    return sentence.strip()[:MAX_SENTENCE_CHARS]


def _search_knowledge_impl(query: str, category: str | None = None, limit: int = 4) -> str:
    """检索已发布资料片段，返回 JSON 数组字符串。

    每条结果包含 id（片段 id）、document_id、title、source、chunk_index 和
    content（最多 800 字）。参数有误或检索失败时返回结构化错误字符串。
    """
    text = (query or "").strip()
    if not text:
        return _error("EMPTY_QUERY", "query 不能为空")
    try:
        with SessionLocal() as db:
            hits = retrieve(
                db,
                text[:MAX_QUERY_CHARS],
                category or None,
                limit=_bounded_limit(limit),
                use_vector=True,
            )
        results = [
            {
                "id": hit.get("chunk_id") or "",
                "document_id": hit.get("document_id") or "",
                "title": hit.get("title") or "",
                "source": hit.get("source") or "",
                "chunk_index": hit.get("chunk_index", 0),
                "content": (hit.get("content") or "")[:SEARCH_CONTENT_LIMIT],
            }
            for hit in hits
        ]
        return _dump(results)
    except Exception as exc:
        logger.warning(
            "[mcp] search_knowledge_failed query=%s error=%s: %s",
            text[:80],
            exc.__class__.__name__,
            exc,
        )
        return _error("SEARCH_FAILED", f"知识库检索失败：{exc.__class__.__name__}")


def _list_documents_impl(category: str | None = None) -> str:
    """列出已发布资料，返回 JSON 数组字符串（最多 50 条）。"""
    try:
        with SessionLocal() as db:
            statement = select(
                KnowledgeDocument.id,
                KnowledgeDocument.title,
                KnowledgeDocument.category,
            ).where(KnowledgeDocument.status == "published")
            wanted = (category or "").strip()
            if wanted:
                statement = statement.where(KnowledgeDocument.category == wanted)
            statement = statement.order_by(KnowledgeDocument.created_at.desc()).limit(MAX_DOCUMENTS)
            rows = db.execute(statement).all()
        return _dump([{"id": row.id, "title": row.title, "category": row.category or ""} for row in rows])
    except Exception as exc:
        logger.warning(
            "[mcp] list_documents_failed category=%s error=%s: %s",
            category or "",
            exc.__class__.__name__,
            exc,
        )
        return _error("LIST_FAILED", f"资料目录读取失败：{exc.__class__.__name__}")


def _get_document_outline_impl(document_id: str) -> str:
    """返回资料的标题、来源、分块数与各分块首句（JSON 字符串）。"""
    key = (document_id or "").strip()
    if not key:
        return _error("EMPTY_DOCUMENT_ID", "document_id 不能为空")
    try:
        with SessionLocal() as db:
            document = db.get(KnowledgeDocument, key)
            if not document or document.status != "published":
                return _error("DOCUMENT_NOT_FOUND", "资料不存在或尚未发布")
            chunks = db.scalars(
                select(KnowledgeChunk)
                .where(KnowledgeChunk.document_id == document.id)
                .order_by(KnowledgeChunk.chunk_index.asc())
            ).all()
            payload = {
                "id": document.id,
                "title": document.title,
                "source": document.source or "",
                "chunk_count": len(chunks),
                "chunks": [
                    {
                        "chunk_index": chunk.chunk_index,
                        "first_sentence": _first_sentence(chunk.content),
                    }
                    for chunk in chunks
                ],
            }
        return _dump(payload)
    except Exception as exc:
        logger.warning(
            "[mcp] get_document_outline_failed document_id=%s error=%s: %s",
            key[:80],
            exc.__class__.__name__,
            exc,
        )
        return _error("OUTLINE_FAILED", f"资料大纲读取失败：{exc.__class__.__name__}")


mcp = FastMCP(
    "eclass-knowledge",
    instructions="思政情景工坊知识库：检索已发布资料片段、浏览资料目录、查看资料分块大纲。",
)


@mcp.tool()
def search_knowledge(query: str, category: str | None = None, limit: int = 4) -> str:
    """在已发布知识库资料中做混合检索。

    参数：
        query: 检索词或自然语言问题。
        category: 可选，限定资料分类。
        limit: 返回片段数，1-10，默认 4。

    返回 JSON 数组字符串，每项包含 id、document_id、title、source、
    chunk_index 和 content（最多 800 字）。
    """
    return _search_knowledge_impl(query, category, limit)


@mcp.tool()
def list_documents(category: str | None = None) -> str:
    """列出已发布知识库资料，最多 50 条。

    参数：
        category: 可选，按资料分类过滤。

    返回 JSON 数组字符串，每项包含 id、title、category。
    """
    return _list_documents_impl(category)


@mcp.tool()
def get_document_outline(document_id: str) -> str:
    """查看一份资料的标题、来源、分块数与各分块首句。

    参数：
        document_id: 资料 id，可从 list_documents 或检索结果中获得。

    返回 JSON 对象字符串。资料不存在或尚未发布时返回结构化错误。
    """
    return _get_document_outline_impl(document_id)


def main() -> None:
    """以 stdio 传输启动 MCP 服务器，供 MCP 客户端拉起。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
