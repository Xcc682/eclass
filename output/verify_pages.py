"""核验截图页面的实际渲染内容：逐页打印路由与正文首段。

用法：python -I verify_pages.py <token> <practiceId> <debateSessionId>
"""

from __future__ import annotations

import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5667"


def main() -> int:
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    practice_id = sys.argv[2] if len(sys.argv) > 2 else ""
    debate_id = sys.argv[3] if len(sys.argv) > 3 else ""

    pages = [
        ("01_登录页", "/pages/login/login"),
        ("02_首页", "/pages/index/index"),
        ("03_入党谈话", f"/pages/interview/practice?practiceId={practice_id}"),
        ("04_谈话报告", f"/pages/interview/report?practiceId={practice_id}"),
        ("05_党史书卷", "/pages/history/history"),
        ("06_研学导游", "/pages/tour/tour"),
        ("07_辩论赛", f"/pages/debate/arena?sessionId={debate_id}"),
        ("08_知识库", "/pages/knowledge/knowledge"),
        ("09_AI问答", "/pages/knowledge/ask"),
        ("10_成长社区", "/pages/community/community"),
        ("11_成长档案", "/pages/community/growth"),
        ("12_个人中心", "/pages/community/profile"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = ctx.new_page()
        page.set_default_timeout(25000)
        page.goto(BASE + "/#/pages/index/index", wait_until="domcontentloaded")
        if token:
            page.evaluate("t => localStorage.setItem('token', t)", token)

        for name, route in pages:
            try:
                page.goto(BASE + "/#" + route, wait_until="domcontentloaded")
                page.wait_for_timeout(3200)
                info = page.evaluate(
                    """() => {
                        const t = (document.body.innerText || '').replace(/\\s+/g, ' ').trim();
                        return { len: t.length, head: t.slice(0, 150) };
                    }"""
                )
                print(f"[{name}] len={info['len']} :: {info['head']}", flush=True)
            except Exception as exc:
                print(f"[{name}] FAIL {exc.__class__.__name__}", flush=True)

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
