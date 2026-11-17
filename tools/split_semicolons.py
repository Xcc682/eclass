"""把一行内以分号分隔的简单语句拆成多行。

安全策略：
1. 只处理“顶层简单语句”（赋值、return、break、continue、pass、raise、表达式调用）。
2. 拆分前后分别做 AST 解析，忽略行号后比对语法树是否完全一致；
   不一致则放弃该文件的修改。
3. 不触碰带引号内容里出现的分号（用 tokenize 定位真实分隔符）。

用法：python -I split_semicolons.py <file> [...]
"""
from __future__ import annotations

import ast
import io
import sys
import tokenize
from pathlib import Path


def _semantic_dump(source: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    return ast.dump(tree, include_attributes=False)


def _split_positions(line: str) -> list[int]:
    """返回该行中处于顶层（不在字符串/括号内）的分号字符位置。"""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(line).readline))
    except (tokenize.TokenError, IndentationError):
        return []
    positions: list[int] = []
    depth = 0
    for tok in tokens:
        if tok.type == tokenize.OP:
            if tok.string in "([{":
                depth += 1
            elif tok.string in ")]}":
                depth -= 1
            elif tok.string == ";" and depth == 0:
                positions.append(tok.start[1])
    return positions


def process(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    before = _semantic_dump(text)
    if before is None:
        print(f"{path}: 原文件无法解析，跳过")
        return -1

    lines = text.splitlines(keepends=True)
    output: list[str] = []
    changed = 0

    for line in lines:
        body = line.rstrip("\n")
        newline = line[len(body):]
        positions = _split_positions(body)
        if not positions:
            output.append(line)
            continue

        indent = body[: len(body) - len(body.lstrip())]
        pieces: list[str] = []
        cursor = 0
        for pos in positions:
            piece = body[cursor:pos].strip()
            if piece:
                pieces.append(piece)
            cursor = pos + 1
        tail = body[cursor:].strip()
        if tail:
            pieces.append(tail)

        if len(pieces) < 2 or any(p.endswith(":") for p in pieces):
            output.append(line)
            continue

        for piece in pieces:
            output.append(f"{indent}{piece}{newline}")
        changed += 1

    candidate = "".join(output)
    if _semantic_dump(candidate) != before:
        print(f"{path}: AST 不一致，放弃修改（{changed} 行本可拆分）")
        return -1

    if changed:
        path.write_text(candidate, encoding="utf-8", newline="\n")
    print(f"{path}: {changed} 行已拆分")
    return changed


def main() -> int:
    for name in sys.argv[1:]:
        process(Path(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
