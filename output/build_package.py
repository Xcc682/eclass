"""生成参赛交付包：只收录源码与文档，排除密钥、数据库、依赖与构建产物。

用法：python -I build_package.py

产物：output/思政情景工坊_参赛作品.zip
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "output" / "思政情景工坊_参赛作品.zip"

# 需要收录的顶层条目
INCLUDE_DIRS = ["backend", "frontend", "docs", "scripts", ".github"]
INCLUDE_FILES = [
    "README.md",
    "DEPLOYMENT.md",
    ".editorconfig",
    ".gitignore",
    ".env.production.example",
    "docker-compose.yml",
    "docker-compose.quick.yml",
    "docker-compose.production.yml",
]

# 任何位置出现即排除
EXCLUDE_DIR_NAMES = {
    "node_modules", "dist", "__pycache__", ".git", "_backup", ".ruff_cache",
    ".mypy_cache", ".pytest_cache", "backups", ".claude", ".playwright-cli",
    ".vscode", ".venv", "venv", "build", "storage",
}
EXCLUDE_FILE_SUFFIXES = {".pyc", ".pyo", ".log", ".db", ".zip", ".pid"}
EXCLUDE_FILE_NAMES = {
    ".env",            # 真实密钥，绝不打包
    "dev.db",
    "test.db",
    "说明 .txt",        # 含真实手机号
    "eclass.zip",
}

# 前端大体积媒体资源：保留，但记录体积
MEDIA_EXTS = {".webp", ".png", ".jpg", ".jpeg"}


def should_skip(path: Path) -> bool:
    if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
        return True
    if path.name in EXCLUDE_FILE_NAMES:
        return True
    if path.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
        return True
    return False


def collect() -> list[Path]:
    files: list[Path] = []
    for entry in INCLUDE_FILES:
        candidate = ROOT / entry
        if candidate.is_file():
            files.append(candidate)
    for entry in INCLUDE_DIRS:
        base = ROOT / entry
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and not should_skip(path.relative_to(ROOT)):
                files.append(path)
    # 文档与脚本单独加入：只收最终版作品介绍文档与检索评测报告
    for pattern in (
        "思政情景工坊_作品介绍文档.docx",
        "思政情景工坊_作品介绍文档.pdf",
        "评测报告_检索.md",
        "评测报告_检索_口语化.md",
        "eval_retrieval.json",
        "eval_paraphrase.json",
    ):
        path = ROOT / "output" / pattern
        if path.is_file():
            files.append(path)
    return sorted(set(files))


def main() -> int:
    files = collect()
    total = sum(f.stat().st_size for f in files)
    media = [f for f in files if f.suffix.lower() in MEDIA_EXTS]
    media_size = sum(f.stat().st_size for f in media)

    print(f"待打包文件: {len(files)} 个")
    print(f"总体积: {total / 1024 / 1024:.1f} MB")
    print(f"其中媒体资源: {len(media)} 个，{media_size / 1024 / 1024:.1f} MB")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in files:
            arcname = Path("思政情景工坊_参赛作品") / path.relative_to(ROOT)
            zf.write(path, arcname.as_posix())

    size = OUT.stat().st_size
    print(f"\n已生成: {OUT}")
    print(f"压缩包大小: {size / 1024 / 1024:.1f} MB")

    # 安全自检：确认包内不含敏感文件
    with zipfile.ZipFile(OUT) as zf:
        names = zf.namelist()
        leaked = [
            n for n in names
            if n.endswith("/.env") or n.endswith(".db") or n.endswith(".pyc")
        ]
        if leaked:
            print("\n[警告] 包内发现敏感文件:")
            for item in leaked[:10]:
                print(f"  {item}")
            return 1
        print("安全自检通过：无 .env / .db / .pyc")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
