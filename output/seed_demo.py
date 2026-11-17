"""通过真实 API 走一遍完整实训流程，为文档截图准备有内容的界面数据。

用法：python -I seed_demo.py <token>

产物：谈话 / 辩论 / 知识问答 三个模块留下可截图的真实对话记录。
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx

BASE = "http://127.0.0.1:8000/api/v1"

# 入党积极分子谈话的真实回答脚本
INTERVIEW_ANSWERS = [
    "我是一名大二学生，担任班级团支书。平时参与组织主题团日活动，也在学院党建中心做过志愿服务。",
    "我的入党动机来自家里的影响。爷爷是老党员，在村里做了三十年基层工作，我从小看着他处理邻里纠纷、带头修路，慢慢明白党员不只是荣誉，是要实实在在做事。",
    "我理解党的性质是中国工人阶级的先锋队，同时是中国人民和中华民族的先锋队，宗旨是全心全意为人民服务。",
    "如果组织上分配我去做一份没人愿意干的琐碎工作，我会先接下来。工作没有高低，我愿意把小事做好，在这个过程中证明自己的态度。",
    "我最近系统读了《党章》，也在跟支部一起学习党的二十大精神，对新时代十年的变革有了更具体的认识。",
    "我身上还有不足，主要是理论学习的系统性不够，遇到复杂问题容易着急，需要多沉淀。",
]

DEBATE_ARGS = [
    "我方认为，网络曝光的监督作用确实大于其负面影响。理由有三：第一，在传统监督渠道失灵的场景下，网络曝光是普通人唯一能启动的救济手段，它把分散的个体声音汇聚成公共压力；第二，曝光带来的即时舆论成本，显著提高了失德行为的预期代价，形成有效威慑；第三，程序瑕疵可以通过平台核验与后续追责修补，而监督缺位造成的不公却难以弥补。",
    "对方强调曝光缺乏事实核验、容易误伤，这一点我方承认存在，但这属于机制完善问题，而非否定监督价值。我方主张：应当建立曝光前的必要核验与曝光后的纠错通道，而不是因噎废食地否定曝光本身。",
    "对方提到的网络暴力确实值得警惕，但请注意，网络暴力恰恰发生在缺乏规则约束的环境中。我方主张的正是为曝光设定清晰边界：事实性内容可曝光，隐私与情绪化人身攻击应被约束。规范曝光不等于取消曝光。",
    "综上，我方坚持：网络曝光在救济渠道、威慑效果与公共监督三方面产生的正向作用，超过其可控的负面成本。真正需要解决的是如何让曝光更规范，而不是让它消失。",
]

KNOWLEDGE_QUESTIONS = [
    "入党积极分子的培养考察期一般是多长时间？",
    "党的全国代表大会每几年举行一次？",
]


def post_retry(client: httpx.Client, url: str, payload: dict, label: str, tries: int = 4):
    """AI 接口偶发返回非法 JSON，做有限次重试。"""
    for attempt in range(tries):
        resp = client.post(url, json=payload)
        if resp.status_code == 200:
            return resp.json()["data"]
        print(f"  {label} 第 {attempt + 1} 次 {resp.status_code}，重试…")
        time.sleep(3)
    print(f"  {label} 放弃")
    return None


def main() -> int:
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    if not token:
        print("需要 token")
        return 1
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=120.0, headers=headers) as client:
        # ---------- 1. 入党谈话 ----------
        scenarios = client.get(f"{BASE}/interviews/scenarios").json()["data"]
        if not scenarios:
            print("没有谈话场景")
            return 1
        target = scenarios[0]
        start = client.post(
            f"{BASE}/interviews/practice/start",
            json={"scenario_id": target["id"], "restart": True},
        ).json()
        practice_id = start["data"]["id"]
        print(f"谈话 practice={practice_id}")

        for idx, answer in enumerate(INTERVIEW_ANSWERS, 1):
            got = post_retry(
                client,
                f"{BASE}/interviews/practice/{practice_id}/respond",
                {"content": answer, "submission_id": str(uuid.uuid4())},
                f"谈话第 {idx} 轮",
            )
            if got is None:
                break
            print(f"  谈话第 {idx} 轮 OK → {got['question'][:40]}…")
            time.sleep(0.5)

        client.post(f"{BASE}/interviews/practice/{practice_id}/end")
        print("谈话报告已生成")

        # ---------- 2. 思政辩论 ----------
        topics = client.get(f"{BASE}/debates/topics").json()["data"]
        if topics:
            topic = topics[0]
            ds = client.post(
                f"{BASE}/debates/practice/start",
                json={
                    "topic_id": topic["id"],
                    "stance": "pro",
                    "mode": "quick",
                    "restart": True,
                },
            ).json()
            sid = ds["data"]["id"]
            print(f"辩论 session={sid}")
            for idx, arg in enumerate(DEBATE_ARGS, 1):
                got = post_retry(
                    client,
                    f"{BASE}/debates/practice/{sid}/argue",
                    {
                        "argument": arg,
                        "evidence_refs": [],
                        "submission_id": str(uuid.uuid4()),
                    },
                    f"辩论第 {idx} 轮",
                )
                if got is None:
                    break
                print(f"  辩论第 {idx} 轮 OK")
                time.sleep(0.5)

        # ---------- 3. 知识库问答 ----------
        for q in KNOWLEDGE_QUESTIONS:
            got = post_retry(
                client,
                f"{BASE}/knowledge/ask",
                {"question": q, "submission_id": str(uuid.uuid4())},
                f"问答「{q[:16]}」",
            )
            if got:
                print(f"  问答 OK，引用 {len(got.get('citations', []))} 条")
            time.sleep(0.5)

    print("演示数据准备完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
