"""真实链路冒烟：登录 → 知识库问答（同一问题两次，验证语义缓存）→ 可观测接口。

用法：先启动后端服务，再运行本脚本。
    python scripts/smoke_flow.py [base_url]
"""
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"

# 依序尝试，取第一条能召回到资料的问题做两轮对比（第二轮的语义缓存需要带引用答案）
QUESTIONS = [
    "党员的权利有哪些？",
    "入党誓词的内容是什么？",
    "党支部的主要职责是什么？",
    "党的群众路线是什么？",
    "入党需要经过哪些程序？",
]


def call(method: str, path: str, payload: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(BASE + path, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.status, json.loads(response.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def ask(token: str, question: str) -> tuple[int, dict, float]:
    started = time.perf_counter()
    code, data = call("POST", "/api/v1/knowledge/ask",
                      {"question": question, "submission_id": uuid.uuid4().hex}, token)
    return code, data, time.perf_counter() - started


def main() -> int:
    phone = "139" + str(int(time.time()))[-8:]
    code, data = call("POST", "/api/v1/auth/register", {"phone": phone, "password": "Smoke#2026"})
    if code not in (200, 201):
        code, data = call("POST", "/api/v1/auth/login", {"phone": phone, "password": "Smoke#2026"})
    print("register/login", code)
    payload = data.get("data") or {}
    token, user_id = payload.get("token"), (payload.get("user") or {}).get("id")
    if not token:
        print("no token", data)
        return 1

    question = None
    for candidate in QUESTIONS:
        code, data, elapsed = ask(token, candidate)
        body = data.get("data") or {}
        citations = body.get("citations") or []
        print(f"probe {candidate} status={code} {elapsed:.1f}s citations={len(citations)} "
              f"retrieval={body.get('retrieval')}")
        if code == 200 and citations:
            question = candidate
            print("   answer:", (body.get("answer") or "")[:100].replace("\n", " "),
                  "| grounding:", (body.get("grounding") or {}).get("status"))
            break
    if question is None:
        print("所有候选问题都没有召回资料，请检查知识库数据")
        return 1

    code, data, elapsed = ask(token, question)
    body = data.get("data") or {}
    print(f"repeat status={code} {elapsed:.2f}s cached={body.get('cached')} "
          f"citations={len(body.get('citations') or [])}")

    code, data = call("GET", "/api/v1/ai/observability", None, token)
    snapshot = data.get("data") or {}
    print("observability", code, json.dumps({
        "llm": snapshot.get("llm", {}).get("totals"),
        "quota": snapshot.get("quota"),
        "cache": snapshot.get("semantic_cache"),
        "breaker": (snapshot.get("circuit_breaker") or {}).get("state"),
        "user": user_id,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
