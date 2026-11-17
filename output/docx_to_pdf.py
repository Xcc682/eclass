"""把生成好的 docx 转成 PDF，并先更新目录域，让目录带真实页码。

用法：python -I docx_to_pdf.py
"""

from __future__ import annotations

from pathlib import Path

import win32com.client as win32

ROOT = Path(__file__).resolve().parent
DOCX = ROOT / "思政情景工坊_作品介绍文档.docx"


def main() -> int:
    if not DOCX.is_file():
        print(f"找不到 {DOCX}")
        return 1

    pdf = DOCX.with_suffix(".pdf")
    word = win32.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(DOCX))
        # 目录域是空的，先更新一次才有条目和页码
        for toc in doc.TablesOfContents:
            toc.Update()
        doc.Fields.Update()
        doc.Repaginate()

        # 目录条目默认行距很松，会把目录撑到三页；逐段压紧
        for para in doc.Paragraphs:
            try:
                style_name = str(para.Style.NameLocal)
            except Exception:
                continue
            if style_name.startswith("TOC") or style_name.startswith("目录"):
                para.Format.SpaceBefore = 0
                para.Format.SpaceAfter = 0
                para.Format.LineSpacingRule = 5  # wdLineSpaceMultiple
                para.Format.LineSpacing = 1.2 * 12
        doc.Repaginate()

        doc.Save()
        doc.SaveAs(str(pdf), FileFormat=17)
        print(f"页数 {doc.ComputeStatistics(2)}")
        doc.Close(False)
    finally:
        word.Quit()

    print(f"PDF: {pdf.name}  {pdf.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
