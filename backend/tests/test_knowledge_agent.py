"""知识库自主检索 Agent 的单测：工具循环、证据编号、步数上界与兜底。"""
import asyncio
import json
import unittest
from unittest.mock import patch

from app.services import knowledge_agent


def _hit(chunk_id="c1", title="入党动机资料"):
    return {
        "chunk_id": chunk_id,
        "chunk_index": 0,
        "content": "入党动机应当来自对党的认识与自身实践。",
        "document_id": "d1",
        "title": title,
        "source": "支部学习材料",
        "source_url": "",
        "category": "入党",
        "score": 0.5,
        "retrieval": ["keyword"],
    }


def _tool_call(name="search_knowledge", arguments="{\"query\":\"入党动机\"}", call_id="call-1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}


class FakeAI:
    """按脚本顺序返回助手消息的假模型。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def _call_tool_api(self, messages, tools, *, tool_choice="required", max_tokens=400):
        self.calls.append({"tool_choice": tool_choice, "messages": list(messages)})
        return self.script.pop(0) if self.script else {"content": "{}"}

    @staticmethod
    def _parse_json(text):
        return json.loads(text)


def _answer_json(blocks):
    return json.dumps({"blocks": blocks, "follow_up_suggestions": []}, ensure_ascii=False)


class AgentTests(unittest.TestCase):
    def _run(self, script, hits=None):
        ai = FakeAI(script)
        with patch.object(knowledge_agent, "retrieve", return_value=hits or [_hit()]):
            result = asyncio.run(knowledge_agent.run("我的入党动机是什么", [], None, None, None, service=ai))
        return result, ai

    def test_single_search_then_answer(self):
        script = [
            {"tool_calls": [_tool_call()]},
            {"content": _answer_json([{"type": "paragraph", "text": "动机来自认识与实践。", "citations": [1]}])},
        ]
        result, ai = self._run(script)
        self.assertEqual(len(result.contexts), 1)
        self.assertEqual(result.trace[0]["tool"], "search_knowledge")
        self.assertEqual(result.trace[0]["hit_count"], 1)
        self.assertEqual(result.answer["blocks"][0]["citations"], [1])
        self.assertEqual(len(ai.calls), 2)
        self.assertIn("role", ai.calls[1]["messages"][-1])

    def test_duplicate_chunk_keeps_stable_citation_id(self):
        script = [
            {"tool_calls": [_tool_call(call_id="c1"), _tool_call(call_id="c2")]},
            {"content": _answer_json([{"type": "paragraph", "text": "同上。", "citations": [1]}])},
        ]
        result, _ = self._run(script)
        self.assertEqual(len(result.contexts), 1)

    def test_step_limit_forces_final_answer(self):
        script = [{"tool_calls": [_tool_call(call_id=f"c{i}")]} for i in range(knowledge_agent.MAX_STEPS)]
        script.append({"content": _answer_json([{"type": "paragraph", "text": "资料不足。", "citations": []}])})
        result, ai = self._run(script)
        self.assertEqual(result.steps, knowledge_agent.MAX_STEPS)
        self.assertEqual(ai.calls[-1]["tool_choice"], "none")
        self.assertEqual(result.answer["blocks"][0]["text"], "资料不足。")

    def test_unknown_tool_returns_error_without_crash(self):
        script = [
            {"tool_calls": [_tool_call(name="rm_rf", arguments="{}", call_id="c9")]},
            {"content": "{}"},
        ]
        result, _ = self._run(script)
        self.assertEqual(result.trace[0]["tool"], "rm_rf")
        self.assertEqual(result.contexts, [])

    def test_no_tool_call_answers_directly(self):
        script = [{"content": _answer_json([{"type": "paragraph", "text": "直接回答。", "citations": []}])}]
        result, ai = self._run(script)
        self.assertEqual(len(ai.calls), 1)
        self.assertEqual(result.trace, [])


if __name__ == "__main__":
    unittest.main()
