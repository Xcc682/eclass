"""把 `if cond: stmt` 形式的单行语句展开为标准的双行写法。

只处理行首为 if/elif/else 且冒号后紧跟语句的情况，不做其他改动。
用法：python split_inline.py <file> [...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# 匹配 `(缩进)(if|elif|else)( ... )(其他内容)`，且 (其他内容) 非空
INLINE_IF = re.compile(r"^(\s*)(if|elif|else)\b(.*?):\s+(\S.*)$")


def split_line(line: str) -> list[str]:
    stripped = line.rstrip("\n")
    match = INLINE_IF.match(stripped)
    if not match:
        return [line]
    indent, keyword, condition, body = match.groups()
    # 条件里若含未闭合的括号，说明是跨行表达式，保守跳过
    if condition.count("(") != condition.count(")"):
        return [line]
    head = f"{indent}{keyword}{condition}:"
    return [head + "\n", f"{indent}    {body}\n"]


def process(path: Path) -> int:
    original = path.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    changed = 0
    for line in original:
        result = split_line(line)
        if len(result) > 1:
            changed += 1
        output.extend(result)
    if changed:
        path.write_text("".join(output), encoding="utf-8", newline="\n")
    return changed


def main() -> int:
    total = 0
    for name in sys.argv[1:]:
        path = Path(name)
        count = process(path)
        print(f"{path}: {count} 行已展开")
        total += count
    return 0 if total >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
