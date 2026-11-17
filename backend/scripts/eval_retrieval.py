"""检索层离线评测：recall@k 与 MRR@k，基线（单查询混合检索）对比增强（多查询+RRF+重排）。

评测方法对齐 BEIR 的检索评测约定：人工构造问题，用「判定关键词组」标注哪些片段算
相关（片段同时包含某一组内的全部关键词即判相关），统计前 k 条结果中相关片段的
召回率与首个相关内容的名次倒数（MRR）。评测集里问题对应的资料不在语料库中时，
该条记为 unavailable 并跳过，不计入分母，避免用空语料拉高或拉低指标。

用法：
    python scripts/eval_retrieval.py                 # 两种模式都跑
    python scripts/eval_retrieval.py --mode enhanced --k 6 --out ../output/评测报告_检索.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import or_, select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument  # noqa: E402
from app.services import retrieval_advanced  # noqa: E402
from app.services.ai_service import ai_service  # noqa: E402
from app.services.knowledge_service import retrieve_async  # noqa: E402

DEFAULT_DATASET = Path(__file__).with_name("eval_set.json")


def is_relevant(row: dict, item: dict) -> bool:
    """片段所属文档是应依据的资料，或同时包含某一判定组内的全部关键词，即判相关。"""
    title = row.get("title") or ""
    if any(expected in title for expected in item.get("expected_titles") or []):
        return True
    text = f"{title}\n{row.get('content') or ''}"
    judge = item.get("judge") or []
    return any(all(term in text for term in group) for group in judge)


def recall_at_k(rows: list[dict], item: dict, k: int) -> float:
    """前 k 条里是否召回了应依据的资料（单目标检索，命中即 1）。"""
    return 1.0 if any(is_relevant(row, item) for row in rows[:k]) else 0.0


def reciprocal_rank(rows: list[dict], item: dict, k: int) -> float:
    for rank, row in enumerate(rows[:k], start=1):
        if is_relevant(row, item):
            return 1.0 / rank
    return 0.0


def corpus_has_answer(db, item: dict) -> bool:
    """语料库里是否存在能命中判定条件的资料，用于识别 unavailable 题目。"""
    titles = item.get("expected_titles") or []
    if titles:
        filters = [KnowledgeDocument.title.ilike(f"%{title}%") for title in titles]
        if db.scalar(select(KnowledgeChunk.id).join(
            KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id,
        ).where(or_(*filters)).limit(1)):
            return True
    for group in item.get("judge") or []:
        filters = [KnowledgeChunk.content.ilike(f"%{term}%") for term in group]
        if db.scalar(select(KnowledgeChunk.id).where(*filters).limit(1)):
            return True
    return False


def load_dataset(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise SystemExit("评测集格式错误：需要 {\"items\": [...]} 或数组")
    return items


async def run_baseline(item: dict, k: int) -> list[dict]:
    rows = await retrieve_async(item["question"], item.get("category"), limit=max(k, 6), use_vector=True)
    return rows[:k]


async def run_enhanced(item: dict, k: int) -> tuple[list[dict], dict]:
    rows, trace = await retrieval_advanced.search(
        retrieve_async, ai_service, item["question"],
        category=item.get("category"), limit=max(k, 6),
    )
    return rows[:k], trace


async def evaluate(dataset: list[dict], k: int, modes: list[str]) -> dict:
    report: dict = {"k": k, "items": [], "summary": {}}
    with SessionLocal() as db:
        available = [(item, corpus_has_answer(db, item)) for item in dataset]
    judged = [(item, ok) for item, ok in available if ok]
    report["unavailable"] = [item["id"] for item, ok in available if not ok]

    for mode in modes:
        scores = {"recall@1": [], f"recall@{k}": [], f"mrr@{k}": []}
        for item, _ in judged:
            if mode == "enhanced":
                rows, trace = await run_enhanced(item, k)
            else:
                rows, trace = await run_baseline(item, k), {}
            record = {
                "id": item["id"], "question": item["question"], "mode": mode,
                "recall@1": round(recall_at_k(rows, item, 1), 3),
                f"recall@{k}": round(recall_at_k(rows, item, k), 3),
                f"mrr@{k}": round(reciprocal_rank(rows, item, k), 3),
                "top": [row.get("title") for row in rows[:3]],
                "trace": trace,
            }
            report["items"].append(record)
            for key in scores:
                scores[key].append(record[key])
        report["summary"][mode] = {
            key: round(sum(values) / len(values), 4) if values else None
            for key, values in scores.items()
        } | {"items": len(judged)}
    return report


def to_markdown(report: dict) -> str:
    k = report["k"]
    lines = [
        "# 检索评测报告", "",
        f"- 评测题数（语料可答）：{next(iter(report['summary'].values()), {}).get('items', 0)}",
        f"- 因语料缺失跳过：{len(report.get('unavailable') or [])} 题 {report.get('unavailable') or ''}",
        f"- 指标：recall@1、recall@{k}、MRR@{k}（单目标语料下 recall@k 等价于 Hit@k）", "",
        f"| 模式 | recall@1 | recall@{k} | MRR@{k} |",
        "| --- | --- | --- | --- |",
    ]
    for mode, scores in report["summary"].items():
        lines.append(f"| {mode} | {scores['recall@1']} | {scores[f'recall@{k}']} | {scores[f'mrr@{k}']} |")
    lines += ["", "## 逐题明细", "", f"| 题目 | 模式 | recall@1 | recall@{k} | MRR@{k} | Top1 |", "| --- | --- | --- | --- | --- | --- |"]
    for row in report["items"]:
        lines.append(
            f"| {row['question'][:28]} | {row['mode']} | {row['recall@1']} | "
            f"{row[f'recall@{k}']} | {row[f'mrr@{k}']} | {(row['top'] or ['-'])[0]} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="检索层 recall@k / MRR 评测")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--k", type=int, default=6)
    parser.add_argument("--mode", choices=["baseline", "enhanced", "both"], default="both")
    parser.add_argument("--out", type=Path, default=None, help="输出 Markdown 报告路径")
    parser.add_argument("--json", type=Path, default=None, help="输出 JSON 结果路径")
    args = parser.parse_args()

    modes = ["baseline", "enhanced"] if args.mode == "both" else [args.mode]
    report = asyncio.run(evaluate(load_dataset(args.dataset), args.k, modes))
    markdown = to_markdown(report)
    print(markdown)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(markdown, encoding="utf-8")
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
