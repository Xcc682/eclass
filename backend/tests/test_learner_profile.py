# ruff: noqa: E402
# 说明：必须先调用 configure_test_environment()，再导入读取环境变量的 app 模块。
import asyncio
import json
import unittest
import uuid
from datetime import datetime

from test_env import configure_test_environment

configure_test_environment()

from app.database import SessionLocal, init_db
from app.models.domain import TourRecord, TourSite
from app.models.interview import InterviewMessage, InterviewPracticeRecord, InterviewScenario
from app.models.user import User
from app.services import knowledge_agent, learner_profile


class FakeAI:
    """按脚本返回助手消息的假模型，避免真实调用。"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def _call_tool_api(self, messages, tools, *, tool_choice="required", max_tokens=400):
        self.calls.append({"tool_choice": tool_choice, "messages": list(messages),
                           "tool_names": [tool["function"]["name"] for tool in tools]})
        return self.script.pop(0) if self.script else {"content": "{}"}

    @staticmethod
    def _parse_json(text):
        return json.loads(text)


def _tool_call(name, arguments):
    return {"id": f"call-{name}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments, ensure_ascii=False)}}


class LearnerProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def _user(self):
        with SessionLocal() as db:
            user = User(phone=f"138{uuid.uuid4().int % 100_000_000:08d}", hashed_password="test-only")
            db.add(user)
            db.commit()
            return user.id

    def _seed_interview(self, user_id, score=78):
        with SessionLocal() as db:
            scenario = InterviewScenario(title="预备党员接收谈话", difficulty="intermediate")
            db.add(scenario)
            db.flush()
            record = InterviewPracticeRecord(
                user_id=user_id, scenario_id=scenario.id, status="completed",
                overall_score=score, total_rounds=4, completed_at=datetime.utcnow(),
                report_json=json.dumps({
                    "overall_score": score,
                    "dimension_scores": {"思想认识": 86, "理论掌握": 62},
                    "weaknesses": ["理论联系实际不够紧密", "举例过于笼统"],
                    "suggestion": "围绕党史具体事件展开论述。",
                }, ensure_ascii=False),
            )
            db.add(record)
            db.flush()
            db.add(InterviewMessage(record_id=record.id, role="assistant",
                                    content="你的入党动机是什么？", round_number=1))
            db.add(InterviewMessage(record_id=record.id, role="user",
                                    content="我的入党动机来自对党史的学习与服务同学的实践。", round_number=1))
            db.commit()
            return record.id

    def _seed_tour(self, user_id):
        with SessionLocal() as db:
            site = TourSite(name="中共一大纪念馆", location="上海")
            db.add(site)
            db.flush()
            db.add(TourRecord(user_id=user_id, site_id=site.id, completed=True,
                              qa_json=json.dumps([{"question": "一大召开时间", "answer": "1921年7月"}],
                                                 ensure_ascii=False),
                              completed_at=datetime.utcnow()))
            db.commit()

    def test_empty_profile_for_new_user(self):
        user_id = self._user()
        with SessionLocal() as db:
            summary = learner_profile.profile_summary(db, user_id)
            self.assertEqual(summary["total_practices"], 0)
            self.assertEqual(summary["modules"]["interview"]["count"], 0)
            self.assertEqual(learner_profile.interview_context(db, user_id), "")

    def test_profile_aggregates_scores_and_weakest_dimension(self):
        user_id = self._user()
        self._seed_interview(user_id, score=78)
        self._seed_tour(user_id)
        with SessionLocal() as db:
            summary = learner_profile.profile_summary(db, user_id)
            self.assertEqual(summary["total_practices"], 2)
            self.assertEqual(summary["modules"]["interview"]["count"], 1)
            self.assertEqual(summary["modules"]["interview"]["average_score"], 78)
            self.assertEqual(summary["modules"]["tour"]["count"], 1)
            weakest = summary["weakest_dimensions"]
            self.assertEqual(weakest[0]["name"], "理论掌握")
            self.assertEqual(weakest[0]["score"], 62)
            self.assertIn("报告点评", [item["name"] for item in weakest])

    def test_list_records_filters_by_module(self):
        user_id = self._user()
        self._seed_interview(user_id)
        self._seed_tour(user_id)
        with SessionLocal() as db:
            only_tour = learner_profile.list_records(db, user_id, "tour")
            self.assertEqual(only_tour["total"], 1)
            self.assertEqual(only_tour["records"][0]["title"], "中共一大纪念馆")
            everything = learner_profile.list_records(db, user_id)
            self.assertEqual(everything["total"], 2)

    def test_record_detail_enforces_ownership(self):
        owner_id, other_id = self._user(), self._user()
        record_id = self._seed_interview(owner_id)
        with SessionLocal() as db:
            detail = learner_profile.record_detail(db, owner_id, "interview", record_id)
            self.assertEqual(detail["title"], "预备党员接收谈话")
            self.assertEqual(len(detail["turns"]), 1)
            self.assertEqual(detail["turns"][0]["question"], "你的入党动机是什么？")
            self.assertEqual(detail["weaknesses"][0], "理论联系实际不够紧密")
            denied = learner_profile.record_detail(db, other_id, "interview", record_id)
            self.assertEqual(denied["error"], "练习记录不存在")

    def test_interview_context_is_bounded_and_specific(self):
        user_id = self._user()
        self._seed_interview(user_id)
        self._seed_tour(user_id)
        with SessionLocal() as db:
            text = learner_profile.interview_context(db, user_id)
        self.assertIn("参加过 1 次入党谈话", text)
        self.assertIn("理论掌握（62）", text)
        self.assertIn("红色研学 1 次", text)
        self.assertLessEqual(len(text), 600)

    def test_agent_exposes_learning_tools_and_reads_profile(self):
        user_id = self._user()
        self._seed_interview(user_id)
        script = [
            {"tool_calls": [_tool_call("get_learning_profile", {})]},
            {"tool_calls": [_tool_call("list_my_practices", {"module": "interview", "limit": 3})]},
            {"content": json.dumps({"blocks": [{"type": "paragraph",
                                                "text": "上次谈话中理论维度偏弱，建议先从党史事件入手练习。",
                                                "citations": []}],
                                    "follow_up_suggestions": ["帮我出一道理联系实际的题"]},
                                   ensure_ascii=False)},
        ]
        ai = FakeAI(script)
        with SessionLocal() as db:
            result = asyncio.run(knowledge_agent.run(
                "根据我之前的谈话，帮我看看哪里薄弱", [], None, None, db,
                service=ai, user_id=user_id,
            ))
        self.assertEqual([item["tool"] for item in result.trace],
                         ["get_learning_profile", "list_my_practices"])
        self.assertEqual(result.trace[0]["hit_count"], 1)
        self.assertEqual(result.trace[1]["hit_count"], 1)
        self.assertEqual(result.contexts, [])  # 个人档案不参与引用编号
        tool_payload = json.loads(ai.calls[1]["messages"][-1]["content"])
        self.assertEqual(tool_payload["modules"]["interview"]["average_score"], 78)
        self.assertIn("get_practice_detail", ai.calls[0]["tool_names"])
        self.assertNotIn("citations", json.dumps(result.trace, ensure_ascii=False))

    def test_agent_reports_error_without_user(self):
        script = [
            {"tool_calls": [_tool_call("get_learning_profile", {})]},
            {"content": "{}"},
        ]
        ai = FakeAI(script)
        with SessionLocal() as db:
            result = asyncio.run(knowledge_agent.run("我练过什么", [], None, None, db, service=ai))
        self.assertEqual(result.trace[0]["tool"], "get_learning_profile")
        payload = json.loads(ai.calls[1]["messages"][-1]["content"])
        self.assertEqual(payload["error"], "当前会话无法读取学习档案")


if __name__ == "__main__":
    unittest.main()
