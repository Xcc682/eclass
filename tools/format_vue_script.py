"""只格式化 .vue 文件的 <script> 块内容，模板与样式保持原样。

做法：抽出 script 内容 → 写成临时 .ts 交给 prettier → 把格式化结果写回原位置。
这样避免 prettier 重排 Vue 模板产生难以阅读的 `><` 折行。

用法：python -I format_vue_script.py <file.vue> [...]
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_BLOCK = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)", re.DOTALL)


def format_ts(source: str) -> str | None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "block.ts"
        path.write_text(source, encoding="utf-8")
        result = subprocess.run(
            ["npx", "prettier", "--parser", "typescript", "--write", str(path)],
            capture_output=True,
            text=True,
            shell=True,
        )
        if result.returncode != 0:
            print(f"  prettier 失败: {result.stderr.strip()[:200]}")
            return None
        return path.read_text(encoding="utf-8")


def process(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    matches = list(SCRIPT_BLOCK.finditer(text))
    if not matches:
        print(f"{path}: 未找到 <script> 块")
        return False

    original_longest = max((len(line) for line in text.splitlines()), default=0)
    changed = False
    output = text
    # 从后往前替换，避免位置偏移
    for match in reversed(matches):
        open_tag, body, close_tag = match.groups()
        if not body.strip():
            continue
        formatted = format_ts(body)
        if formatted is None:
            continue
        if formatted.strip() == body.strip():
            continue
        output = output[: match.start()] + open_tag + "\n" + formatted.rstrip() + "\n" + close_tag + output[match.end():]
        changed = True

    if changed:
        path.write_text(output, encoding="utf-8", newline="\n")
        new_longest = max((len(line) for line in output.splitlines()), default=0)
        print(f"{path}: 已格式化 script 块，最长行 {original_longest} -> {new_longest}")
    else:
        print(f"{path}: script 块无需改动")
    return True


def main() -> int:
    for name in sys.argv[1:]:
        process(Path(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
