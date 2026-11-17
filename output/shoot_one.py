"""单独重拍一张手机端截图（用于修图后局部替换）。

用法：python -I shoot_one.py <token> <name> <route> [等待毫秒] [滚动像素]
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5667"
OUT = Path(__file__).resolve().parent / "screenshots"


def main() -> int:
    token = sys.argv[1]
    name = sys.argv[2]
    route = sys.argv[3]
    wait = int(sys.argv[4]) if len(sys.argv) > 4 else 4500
    scroll = int(sys.argv[5]) if len(sys.argv) > 5 else -1

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="zh-CN",
        )
        page = ctx.new_page()
        page.set_default_timeout(25000)
        page.goto(BASE + "/#/pages/index/index", wait_until="domcontentloaded")
        page.evaluate("t => localStorage.setItem('token', t)", token)
        page.goto(BASE + "/#" + route, wait_until="domcontentloaded")
        page.wait_for_timeout(wait)
        if scroll >= 0:
            page.evaluate(
                """top => {
                    const box = document.querySelector('.practice__messages, .arena__messages, .chat-scroll');
                    if (box) box.scrollTop = top;
                }""",
                scroll,
            )
            page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
        ctx.close()
        browser.close()
    print(f"OK {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
