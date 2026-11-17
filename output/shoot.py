"""对本地运行中的前端逐页截图，供作品介绍文档配图使用。

用法：python -I shoot.py <token> <practiceId> <debateSessionId>

前置：后端 8000、前端 5667 已启动，且已用 seed_demo.py 灌入演示对话。
产物：output/screenshots/*.png

绝大多数页面按手机端视角（390×844）拍摄，与产品实际使用形态一致；
党史书卷与研学导游是桌面端沉浸式阅读场景，改用 1440×900 拍摄。
登录页用独立的无 token 上下文拍摄（存在 token 时 login 路由会重定向到首页）。
带对话内容的页面直接进子路由，避免只拍到入口列表。
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5667"
OUT = Path(__file__).resolve().parent / "screenshots"

# (文件名, 路由, 等待毫秒, 是否桌面端)
MOBILE_PAGES = [
    ("02_首页", "/pages/index/index", 3500),
    ("03_入党谈话", None, 4500),          # 路由在 main 里按 practiceId 拼
    ("04_谈话报告", None, 5000),
    ("07_辩论赛", None, 4500),
    ("08_知识库", "/pages/knowledge/knowledge", 3500),
    ("09_AI问答", "/pages/knowledge/ask", 3500),
    ("10_成长社区", "/pages/community/community", 3500),
    ("11_成长档案", "/pages/community/growth", 3500),
    ("12_个人中心", "/pages/community/profile", 3000),
]

# 沉浸式阅读场景，保留桌面端视角
DESKTOP_PAGES = [
    ("05_党史书卷", "/pages/history/history", 3500),
    ("06_研学导游", "/pages/tour/tour", 3500),
]


def mobile_pages(practice_id: str, debate_id: str) -> list[tuple[str, str, int]]:
    resolved = []
    for name, route, wait in MOBILE_PAGES:
        if route is None:
            if name == "03_入党谈话":
                route = f"/pages/interview/practice?practiceId={practice_id}"
            elif name == "04_谈话报告":
                route = f"/pages/interview/report?practiceId={practice_id}"
            elif name == "07_辩论赛":
                route = f"/pages/debate/arena?sessionId={debate_id}"
        resolved.append((name, route, wait))
    return resolved


def new_context(browser, mobile: bool):
    if mobile:
        return browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="zh-CN",
        )
    return browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=2,
        locale="zh-CN",
    )


def capture(page, name: str, route: str, wait: int) -> None:
    page.goto(BASE + "/#" + route, wait_until="domcontentloaded")
    page.wait_for_timeout(wait)
    if name == "09_AI问答":
        # 问答页默认是空会话，点开最近一次历史会话才有真实回答
        page.wait_for_function(
            "() => document.querySelectorAll('.session-item').length > 0", timeout=20000
        )
        page.evaluate(
            """() => {
                const el = document.querySelector('.session-item');
                if (el) el.dispatchEvent(new MouseEvent('click', {bubbles: true}));
            }"""
        )
        page.wait_for_timeout(6000)
    if name == "03_入党谈话":
        # 默认停在对话末尾，滚到开头才能同时看到 AI 提问与学生的回答
        page.evaluate(
            """() => {
                const box = document.querySelector('.practice__messages');
                if (box) box.scrollTop = 300;
            }"""
        )
        page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
    print(f"OK   {name}", flush=True)


def main() -> int:
    token = sys.argv[1] if len(sys.argv) > 1 else ""
    practice_id = sys.argv[2] if len(sys.argv) > 2 else ""
    debate_id = sys.argv[3] if len(sys.argv) > 3 else ""
    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")

        # 1) 登录页：无 token 的干净上下文，手机端视角
        anon = new_context(browser, mobile=True)
        login = anon.new_page()
        login.goto(BASE + "/#/pages/login/login", wait_until="domcontentloaded")
        login.wait_for_timeout(2500)
        login.screenshot(path=str(OUT / "01_登录页.png"), full_page=False)
        print("OK   01_登录页", flush=True)
        anon.close()

        # 2) 手机端页面
        ctx = new_context(browser, mobile=True)
        page = ctx.new_page()
        page.set_default_timeout(25000)
        page.goto(BASE + "/#/pages/index/index", wait_until="domcontentloaded")
        if token:
            page.evaluate("t => localStorage.setItem('token', t)", token)
        for name, route, wait in mobile_pages(practice_id, debate_id):
            try:
                capture(page, name, route, wait)
            except Exception as exc:
                print(f"FAIL {name}  {exc.__class__.__name__}: {exc}", flush=True)
        ctx.close()

        # 3) 沉浸式页面：桌面端视角
        dctx = new_context(browser, mobile=False)
        dpage = dctx.new_page()
        dpage.set_default_timeout(25000)
        dpage.goto(BASE + "/#/pages/index/index", wait_until="domcontentloaded")
        if token:
            dpage.evaluate("t => localStorage.setItem('token', t)", token)
        for name, route, wait in DESKTOP_PAGES:
            try:
                capture(dpage, name, route, wait)
            except Exception as exc:
                print(f"FAIL {name}  {exc.__class__.__name__}: {exc}", flush=True)
        dctx.close()

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
