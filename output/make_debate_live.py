"""新建一局未完成的辩论练习，供「辩论赛场」截图使用。

已完成的练习一进页面就弹阶段结算弹窗，遮住对话内容，不能用于文档。

用法：python -I make_debate_live.py
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
PHONE, PASSWORD = "13800001234", "demo123456"

ARGS = [
    "我方认为，网络曝光的监督作用确实大于其负面影响。理由有三：第一，在传统监督渠道失灵的场景下，"
    "网络曝光是普通人唯一能启动的救济手段，它把分散的个体声音汇聚成公共压力；第二，曝光带来的即时"
    "舆论成本，显著提高了失德行为的预期代价，形成有效威慑；第三，程序瑕疵可以通过平台核验与后续"
    "追责修补，而监督缺位造成的不公却难以弥补。",
    "对方强调曝光缺乏事实核验、容易误伤，这一点我方承认存在，但这属于机制完善问题，而非否定监督"
    "价值。我方主张：应当建立曝光前的必要核验与曝光后的纠错通道，而不是因噎废食地否定曝光本身。",
]


def main() -> int:
    with httpx.Client(timeout=120.0) as client:
        login = client.post(f"{BASE}/auth/login", json={"phone": PHONE, "password": PASSWORD})
        if login.status_code != 200:
            print("登录失败", login.status_code, login.text[:200])
            return 1
        token = login.json()["data"]["token"]
        headers = {"Authorization": f"Bearer {token}"}

        topics = client.get(f"{BASE}/debates/topics", headers=headers).json()["data"]
        topic = topics[0]
        start = client.post(
            f"{BASE}/debates/practice/start",
            headers=headers,
            json={"topic_id": topic["id"], "stance": "pro", "mode": "quick", "restart": True},
        )
        if start.status_code != 200:
            print("开局失败", start.status_code, start.text[:300])
            return 1
        sid = start.json()["data"]["id"]
        print(f"session={sid}")

        for idx, arg in enumerate(ARGS, 1):
            for attempt in range(4):
                resp = client.post(
                    f"{BASE}/debates/practice/{sid}/argue",
                    headers=headers,
                    json={
                        "argument": arg,
                        "evidence_refs": [],
                        "submission_id": str(uuid.uuid4()),
                    },
                )
                if resp.status_code == 200:
                    print(f"  第 {idx} 轮 OK")
                    break
                print(f"  第 {idx} 轮 {resp.status_code} 重试")
                time.sleep(3)
            else:
                return 1
            time.sleep(0.5)

    print("TOKEN=" + token)
    print("SESSION=" + sid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
