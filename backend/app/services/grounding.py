"""引用核验：回答里的每条引用是否真的被所引原文支撑。

模型生成答案时可能给出「看起来合理」的引用编号。这里把答案块与其引用片段
一起交给快模型做一次逐块核验，剔除不被支撑的引用编号，重新编号并重建正文。
核验超时、输出不可解析或全部不通过时失败开放：保留原答案并标记状态，
不让核验本身成为回答失败的原因。
"""
from __future__ import annotations

import asyncio
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)

CHECK_PROMPT = """你是引用核验员。给出一条问题、若干带编号的资料片段，以及答案中的若干段落（每段带引用编号）。
请逐段判断：该段表述是否能由它引用的资料片段直接支撑。只依据给出的片段判断，不引入外部知识；
只做关键词重合但事实无关的，判为不支撑。
输出 JSON 数组，每项形如 {"block": 段落编号, "supported": [被支撑的引用编号]}，必须包含所有段落。"""

MAX_BLOCK_CHARS = 400
MAX_EXCERPT_CHARS = 260


def _parse_verdicts(raw: str, block_count: int, citation_count: int) -> dict[int, list[int]]:
    text = raw.strip()
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        raise ValueError("模型未返回 JSON 数组")
    values = json.loads(text[start : end + 1])
    if not isinstance(values, list):
        raise ValueError("模型返回的不是数组")
    verdicts: dict[int, list[int]] = {}
    for item in values:
        if not isinstance(item, dict):
            continue
        try:
            block = int(item.get("block"))
        except (TypeError, ValueError):
            continue
        if not 1 <= block <= block_count:
            continue
        supported: list[int] = []
        for value in item.get("supported") or []:
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if 1 <= number <= citation_count and number not in supported:
                supported.append(number)
        verdicts[block] = supported
    if not verdicts:
        raise ValueError("模型没有给出有效核验结果")
    return verdicts


def apply_verdicts(normalized: dict, verdicts: dict[int, list[int]]) -> tuple[dict, int]:
    """按核验结果过滤引用并重建答案；返回 (新答案, 被剔除的引用数)。

    verdicts 以「送检序号」为键（只给带引用的段落编号，从 1 连续编号），
    这里按同一顺序映射回段落位置，避免 heading 等无引用块造成编号错位。
    """
    blocks = [dict(block) for block in normalized.get("answer_blocks") or []]
    citations = [dict(item) for item in normalized.get("citations") or []]
    targets = [position for position, block in enumerate(blocks, start=1) if block.get("citations")]
    if not targets or not citations:
        return normalized, 0
    support_by_position = {
        position: verdicts[ordinal]
        for ordinal, position in enumerate(targets, start=1)
        if ordinal in verdicts
    }

    kept_blocks: list[dict] = []
    used: list[int] = []
    dropped = 0
    for position, block in enumerate(blocks, start=1):
        cites = list(block.get("citations") or [])
        if cites and position in support_by_position:
            supported = set(support_by_position[position])
            removed = [index for index in cites if index not in supported]
            cites = [index for index in cites if index in supported]
            dropped += len(removed)
        if not cites and block.get("type") != "heading":
            continue
        block["citations"] = cites
        for index in cites:
            if index not in used:
                used.append(index)
        kept_blocks.append(block)

    # 正文被剔光时不留孤立标题
    if not any(block["type"] != "heading" for block in kept_blocks):
        kept_blocks = []
    if not used or not kept_blocks:
        return normalized, dropped
    remap = {old: new for new, old in enumerate(used, start=1)}
    selected = []
    for old in used:
        citation = dict(citations[old - 1])
        citation["index"] = remap[old]
        selected.append(citation)
    lines: list[str] = []
    for block in kept_blocks:
        block["citations"] = sorted({remap[index] for index in block["citations"]})
        marks = "".join(f"[{index}]" for index in block["citations"])
        prefix = "- " if block["type"] == "list_item" else ""
        suffix = marks if block["type"] != "heading" else ""
        lines.append(f"{prefix}{block['text']}{suffix}")
    updated = dict(normalized)
    updated.update({
        "answer": "\n".join(lines),
        "answer_blocks": kept_blocks,
        "citations": selected,
        "used_citation_indexes": list(range(1, len(selected) + 1)),
    })
    return updated, dropped


async def verify(service: object, normalized: dict, question: str = "") -> tuple[dict, dict]:
    """核验答案引用，返回 (答案, 核验报告)。异常一律原样返回。"""
    citations = normalized.get("citations") or []
    blocks = normalized.get("answer_blocks") or []
    if not settings.GROUNDING_CHECK_ENABLED:
        return normalized, {"status": "disabled"}
    if not citations or not blocks:
        return normalized, {"status": "skipped"}
    if not getattr(service, "api_key", None) or not callable(getattr(service, "_call_api", None)):
        return normalized, {"status": "skipped"}

    evidence = "\n".join(
        f"[{item.get('index')}] {item.get('document_title') or ''}：{str(item.get('excerpt') or '')[:MAX_EXCERPT_CHARS]}"
        for item in citations
    )
    listed = []
    checked = 0
    for block in blocks:
        if not block.get("citations"):
            continue
        checked += 1
        listed.append(f"{checked}. {str(block.get('text') or '')[:MAX_BLOCK_CHARS]}"
                      f"（引用 {','.join(str(value) for value in block['citations'])}）")
    if not checked:
        return normalized, {"status": "skipped"}
    prompt = (
        f"{CHECK_PROMPT}\n\n问题：{question[:400]}\n\n资料片段：\n{evidence}\n\n"
        f"答案段落：\n" + "\n".join(listed)
    )
    try:
        raw = await asyncio.wait_for(
            service._call_api(  # type: ignore[attr-defined]
                [{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
                model=getattr(service, "fast_model", None),
                disable_thinking=True,
            ),
            timeout=settings.GROUNDING_TIMEOUT_SECONDS,
        )
        verdicts = _parse_verdicts(raw, checked, len(citations))
    except Exception as exc:
        logger.warning("[grounding] check_failed error=%s fallback=keep_answer", exc.__class__.__name__)
        return normalized, {"status": "degraded", "checked_blocks": checked}

    answered = len([ordinal for ordinal in verdicts if 1 <= ordinal <= checked])
    updated, dropped = apply_verdicts(normalized, verdicts)
    if updated is normalized:
        # 没有任何引用通过核验：保留原答案，交由前端与日志判断，不做静默删改
        return normalized, {"status": "unverified", "checked_blocks": checked,
                            "answered_blocks": answered, "dropped": dropped}
    status = "verified" if answered >= checked else "partial"
    return updated, {"status": status, "checked_blocks": checked,
                     "answered_blocks": answered, "dropped": dropped}
