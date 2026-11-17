"""把作品介绍 Markdown 转换为排版规范的 Word 文档。

用法：python -I build_doc.py [--screenshots DIR]

功能：
- 中文标题层级（一、/ 1.1 / （1））
- 表格样式统一
- 代码块等宽字体 + 浅灰底纹
- 自动插入目录域
- 若提供截图目录，按文件名排序插入到第五章
"""
from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
MD_PATH = ROOT / "思政情景工坊_作品介绍文档.md"
OUT_PATH = ROOT / "思政情景工坊_作品介绍文档.docx"

# 统一用字体的英文名，避免 Word 对中文名做字体替换（"黑体"会被换到 MS Gothic）
BODY_LATIN = "Times New Roman"
BODY_CJK = "SimSun"
HEADING_LATIN = "Arial"
HEADING_CJK = "SimHei"
CODE_LATIN = "Consolas"
CODE_CJK = "SimSun"


def apply_font(run, latin: str, cjk: str, size=None, bold=None) -> None:
    """同时设定西文与中文字体：w:ascii 管西文，w:eastAsia 管中文。

    四个槽位全部显式写入，否则 Word 会按主题字体或系统字体回退，
    同一份文档里就会出现粗细不一的字形。
    """
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rFonts.set(qn(attr), latin)
    rFonts.set(qn("w:eastAsia"), cjk)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def style_font(style, latin: str, cjk: str, size=None, bold=None) -> None:
    """把字体写到样式定义上，作用于该样式的全部段落。"""
    rPr = style._element.get_or_add_rPr()
    rFonts = rPr.get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
        rFonts.set(qn(attr), latin)
    rFonts.set(qn("w:eastAsia"), cjk)
    if size is not None:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold



def set_cell_shading(cell, hex_color: str) -> None:
    """给表格单元格加底色。"""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def add_page_number_footer(section) -> None:
    """页脚插入“第 X 页”域代码。"""
    # 取消与上一节的链接，否则会写进封面那一节的页脚
    section.footer.is_linked_to_previous = False
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("第 ")
    run.font.size = Pt(9)

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")

    run2 = paragraph.add_run()
    run2._r.append(fld_begin)
    run2._r.append(instr)
    run2._r.append(fld_end)

    run3 = paragraph.add_run(" 页")
    run3.font.size = Pt(9)


def add_toc(document) -> None:
    """插入目录域（Word 打开后按 Ctrl+A → F9 或“更新域”即可生成）。"""
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("目  录")
    apply_font(run, HEADING_LATIN, HEADING_CJK, size=16, bold=True)

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run()

    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    fld_begin.set(qn("w:dirty"), "true")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r'TOC \o "1-3" \h \z \u'

    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")

    hint = OxmlElement("w:t")
    hint.text = "（打开文档后按 Ctrl+A 再按 F9，选择“更新整个目录”即可生成）"

    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")

    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(hint)
    run._r.append(fld_end)


def add_code_block(document, code: str) -> None:
    """代码块：等宽字体 + 浅灰底纹 + 细边框。"""
    table = document.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    set_cell_shading(cell, "F5F5F5")

    cell.paragraphs[0].text = ""
    for index, line in enumerate(code.rstrip("\n").split("\n")):
        paragraph = cell.paragraphs[0] if index == 0 else cell.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        run = paragraph.add_run(line)
        apply_font(run, CODE_LATIN, CODE_CJK, size=9)


def _visual_lines(text: str) -> list[str]:
    """把段落文本切成视觉行：行尾两个空格是硬换行，其余相邻行合并。"""
    segments: list[str] = []
    buf: list[str] = []
    for raw in text.split("\n"):
        buf.append(raw.strip())
        if raw.endswith("  "):
            segments.append(" ".join(x for x in buf if x))
            buf = []
    if any(buf):
        segments.append(" ".join(x for x in buf if x))
    return segments


def add_rich_paragraph(document, text: str, style: str | None = None, indent: bool = False) -> None:
    """渲染一段文字，识别行内 **粗体**、`代码` 与 Windows 换行。

    Markdown 行尾两个空格表示硬换行（封面信息靠它逐行排布），
    没有这两个空格的相邻行属于同一段的软换行，合并为一行。
    """
    paragraph = document.add_paragraph(style=style) if style else document.add_paragraph()
    if indent:
        paragraph.paragraph_format.first_line_indent = Pt(21)

    # 按行尾双空格切分出视觉行
    segments = _visual_lines(text)

    for seg_index, segment in enumerate(segments):
        if seg_index:
            paragraph.add_run().add_break()
        # 先按 **粗体** 切分（奇数下标即粗体），再在每段内按 `代码` 切分
        for chunk_index, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", segment)):
            if not chunk:
                continue
            bold = chunk_index % 2 == 1
            for piece_index, piece in enumerate(re.split(r"`(.+?)`", chunk)):
                if not piece:
                    continue
                run = paragraph.add_run(piece)
                if piece_index % 2 == 1:
                    apply_font(run, CODE_LATIN, CODE_CJK)
                else:
                    apply_font(run, BODY_LATIN, BODY_CJK)
                if bold:
                    run.bold = True


def _aspect(image_path: Path) -> float:
    """返回高宽比；读不到时按 0（当作横图）处理。"""
    try:
        from PIL import Image

        with Image.open(image_path) as im:
            return im.height / im.width
    except Exception:
        return 0.0


def add_image_row(document, items: list[tuple[Path, str]], workdir: Path, max_height_cm: float = 8.5) -> None:
    """把若干张竖图并排放在一行（无边框表格），每张下方附图题。"""
    cols = len(items)
    table = document.add_table(rows=2, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # 图片与图注必须在同一页，禁止行内跨页拆分
    for row in table.rows:
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)

    # 单元格内边距清零，否则两行各留 0.19cm，整组图白占近 1cm 版心
    cell_mar = OxmlElement("w:tblCellMar")
    for side in ("top", "left", "bottom", "right"):
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), "0")
        node.set(qn("w:type"), "dxa")
        cell_mar.append(node)
    table._tbl.tblPr.append(cell_mar)

    for col, (image_path, caption) in enumerate(items):
        cell = table.cell(0, col)
        cell.text = ""
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.keep_with_next = True
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        try:
            embed = shrink_for_doc(image_path, workdir)
            width = min((max_height_cm / max(_aspect(image_path), 0.01)) * 1.0, 7.4)
            paragraph.add_run().add_picture(str(embed), width=Cm(width))
        except Exception as exc:
            paragraph.add_run(f"[图片插入失败: {image_path.name} - {exc}]")

        cap_cell = table.cell(1, col)
        cap_cell.text = ""
        cap_para = cap_cell.paragraphs[0]
        cap_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap_para.paragraph_format.space_before = Pt(2)
        cap_para.paragraph_format.space_after = Pt(6)
        cap_para.paragraph_format.line_spacing = 1.0
        run = cap_para.add_run(caption)
        apply_font(run, BODY_LATIN, BODY_CJK, size=9)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


def add_image(
    document,
    image_path: Path,
    caption: str,
    workdir: Path,
    max_width_cm: float = 14.0,
    max_height_cm: float = 19.0,
) -> None:
    """插入一张图并附图题。

    手机截图是竖长条（约 1:2.16），按固定宽度插入会超出版心；
    这里按高度上限反算宽度，并保证不超过版心宽度。
    """
    width_cm = max_width_cm
    try:
        from PIL import Image

        with Image.open(image_path) as im:
            ratio = im.height / im.width
        # 竖长的手机截图不必占满整页高度，留出空间给正文
        cap_height = max_height_cm if ratio <= 1.5 else min(max_height_cm, 15.5)
        if ratio * width_cm > cap_height:
            width_cm = cap_height / ratio
    except Exception:
        pass

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(3)
    try:
        embed = shrink_for_doc(image_path, workdir)
        paragraph.add_run().add_picture(str(embed), width=Cm(width_cm))
    except Exception as exc:  # 图片损坏时不要中断整篇文档
        paragraph.add_run(f"[图片插入失败: {image_path.name} - {exc}]")

    cap = document.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = cap.add_run(caption)
    apply_font(run, BODY_LATIN, BODY_CJK, size=9)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    cap.paragraph_format.space_after = Pt(12)



def add_table(document, rows: list[list[str]], borderless: bool = False) -> None:
    """渲染 Markdown 表格。borderless 用于封面信息块，不画边框、不渲染表头。"""
    if not rows:
        return
    if borderless:
        rows = rows[1:]  # Markdown 表头在封面里没有意义
    if not rows:
        return
    cols = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=cols)
    if borderless:
        table.alignment = WD_TABLE_ALIGNMENT.LEFT
        # 封面信息块整体右移，在版心里视觉居中
        tbl_pr = table._tbl.tblPr
        ind = OxmlElement("w:tblInd")
        ind.set(qn("w:type"), "dxa")
        ind.set(qn("w:w"), str(int(Cm(2.4).twips)))
        tbl_pr.append(ind)
        for row in table.rows:
            row.cells[0].width = Cm(2.6)
            if cols > 1:
                row.cells[1].width = Cm(11.6)
    else:
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for row_index, row in enumerate(rows):
        for col_index in range(cols):
            text = row[col_index] if col_index < len(row) else ""
            cell = table.cell(row_index, col_index)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_before = Pt(2 if borderless else 2)
            paragraph.paragraph_format.space_after = Pt(2 if borderless else 2)
            if borderless:
                paragraph.paragraph_format.line_spacing = 1.9
            run = paragraph.add_run()
            apply_font(run, BODY_LATIN, BODY_CJK, size=10.5 if borderless else 9.5)
            for part_index, part in enumerate(text.replace("<br>", "\n").split("\n")):
                if part_index:
                    run.add_break()
                run.add_text(part)
            if borderless:
                if col_index == 0:
                    run.bold = True
            elif row_index == 0:
                run.bold = True
                set_cell_shading(cell, "EDEDED")
    if not borderless:
        document.add_paragraph()


def is_table_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", line.strip())) and "-" in line


def parse_markdown(md: str):
    """把 Markdown 切成块：heading / paragraph / code / table / quote / list。"""
    lines = md.split("\n")
    blocks = []
    index = 0
    while index < len(lines):
        line = lines[index]

        if line.startswith("```"):
            index += 1
            buffer = []
            while index < len(lines) and not lines[index].startswith("```"):
                buffer.append(lines[index])
                index += 1
            blocks.append(("code", "\n".join(buffer)))
            index += 1
            continue

        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            blocks.append(("heading", len(heading.group(1)), heading.group(2).strip()))
            index += 1
            continue

        # 独占一行的配图：![图 3　入党谈话](03_入党谈话.png)
        figure = re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", line.strip())
        if figure:
            blocks.append(("figure", figure.group(2).strip(), figure.group(1).strip()))
            index += 1
            continue

        # 水平分隔线（--- / *** / ___）只用于分节，Word 里不需要渲染成正文
        if re.fullmatch(r"\s*([-*_])\s*(\1\s*){2,}", line):
            index += 1
            continue

        if line.strip().startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            rows = []
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(header)
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append([c.strip() for c in lines[index].strip().strip("|").split("|")])
                index += 1
            blocks.append(("table", rows))
            continue

        if line.strip().startswith(">"):
            buffer = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                buffer.append(lines[index].strip().lstrip(">").strip())
                index += 1
            blocks.append(("quote", " ".join(buffer)))
            continue

        if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            buffer = []
            while index < len(lines) and (re.match(r"^\s*[-*]\s+", lines[index]) or re.match(r"^\s*\d+\.\s+", lines[index])):
                buffer.append(re.sub(r"^\s*[-*]\s+", "", lines[index]).strip())
                index += 1
            blocks.append(("list", buffer))
            continue

        cover = re.match(r"^<!--\s*fullcover:\s*(.+?)\s*-->$", line.strip())
        if cover:
            blocks.append(("fullcover", cover.group(1)))
            index += 1
            continue

        if line.strip() in {"<!-- pagebreak -->", "<!--pagebreak-->"}:
            blocks.append(("pagebreak", ""))
            index += 1
            continue

        if not line.strip():
            index += 1
            continue

        buffer = []
        while index < len(lines) and lines[index].strip() and not lines[index].startswith(("#", "```", "|", ">")):
            if re.match(r"^\s*[-*]\s+", lines[index]) or re.match(r"^\s*\d+\.\s+", lines[index]):
                break
            if re.fullmatch(r"\s*([-*_])\s*(\1\s*){2,}", lines[index]):
                break
            if re.match(r"^!\[(.*?)\]\((.+?)\)\s*$", lines[index].strip()):
                break
            if lines[index].strip() in {"<!-- pagebreak -->", "<!--pagebreak-->"}:
                break
            buffer.append(lines[index])
            index += 1
        if buffer:
            blocks.append(("paragraph", "\n".join(buffer)))
        else:
            index += 1

    return blocks


def strip_inline(text: str) -> str:
    """去掉 Markdown 行内标记（** / ` / []()）。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", text)
    return text


def screenshot_caption(image_path: Path) -> str:
    """`03_入党谈话.png` -> `图 3 入党谈话`。"""
    stem = image_path.stem
    match = re.match(r"^(\d+)[_\- ]*(.+)$", stem)
    if match:
        return f"图 {int(match.group(1))}　{match.group(2).strip()}"
    return stem


def shrink_for_doc(image_path: Path, workdir: Path) -> Path:
    """把高清原图等比缩为 2000px 宽的 JPEG，供文档嵌入（原图仍保留在 screenshots/）。

    15.2cm 宽的版面下 2000px 约合 335 DPI，印刷与屏幕阅读都足够；
    直接把 2880px 无损 PNG 塞进 docx 会让文件膨胀到十几 MB。
    """
    try:
        from PIL import Image
    except ImportError:  # 没有 Pillow 时退回原图，保证脚本仍能跑完
        return image_path

    target = workdir / (image_path.stem + ".jpg")
    try:
        with Image.open(image_path) as im:
            if im.width > 2000:
                im = im.resize((2000, round(im.height * 2000 / im.width)), Image.LANCZOS)
            im.convert("RGB").save(target, quality=88, optimize=True)
        return target
    except Exception:
        return image_path


def group_figures(blocks, shot_dir: Path | None, per_row: int = 2):
    """把配图组织成行：竖图两两并排，横图独占一行。

    形如「图 - 说明 - 图」的相邻两张也会并成一行，说明文字移到图后，
    否则单张竖图占掉大半页，前面留下大片空白。
    """
    out = []
    run: list = []

    def aspect_of(block) -> float:
        path = (shot_dir / block[1]) if shot_dir else Path(block[1])
        return _aspect(path)

    def flush():
        while run:
            if aspect_of(run[0]) > 1.5 and len(run) >= 2:
                out.append(("figurerow", run[:2]))
                del run[:2]
            else:
                out.append(("figurerow", [run[0]]))
                del run[0]

    index = 0
    while index < len(blocks):
        block = blocks[index]
        if block[0] == "figure":
            run.append(block)
            index += 1
            continue
        # 「单图 + 一段说明 + 单图」→ 两图并排，说明文字后移
        if (
            run
            and len(run) == 1
            and block[0] == "paragraph"
            and index + 1 < len(blocks)
            and blocks[index + 1][0] == "figure"
            and aspect_of(run[0]) > 1.5
            and aspect_of(blocks[index + 1]) > 1.5
        ):
            out.append(("figurerow", [run[0], blocks[index + 1]]))
            run.clear()
            out.append(block)
            index += 2
            continue
        flush()
        out.append(block)
        index += 1
    flush()
    return out


def build(screenshot_dir: Path | None) -> None:
    md = MD_PATH.read_text(encoding="utf-8")
    document = Document()
    tmp_dir = Path(tempfile.mkdtemp(prefix="docshots_"))

    # 页面设置
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    has_cover = "<!--fullcover:" in md.replace(" ", "")
    if has_cover:
        # 首页留给满版封面图，页边距归零
        section.left_margin = Cm(0)
        section.right_margin = Cm(0)
        section.top_margin = Cm(0)
        section.bottom_margin = Cm(0)
    else:
        section.left_margin = Cm(2.8)
        section.right_margin = Cm(2.8)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        # 无封面图时，首页（标题页）不显示页码
        section.different_first_page_header_footer = True
        add_page_number_footer(section)

    # 正文默认样式
    normal = document.styles["Normal"]
    style_font(normal, BODY_LATIN, BODY_CJK, size=10.5)
    normal.paragraph_format.line_spacing = 1.5
    normal.paragraph_format.space_after = Pt(6)

    for style_name, size in (("Heading 1", 18), ("Heading 2", 15), ("Heading 3", 13), ("Heading 4", 11.5)):
        style = document.styles[style_name]
        style_font(style, HEADING_LATIN, HEADING_CJK, size=size, bold=True)
        style.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(6)

    # 列表样式必须显式指定字体，否则 Word 会用默认字体，出现中英混排不统一
    for style_name in ("List Bullet", "List Number"):
        try:
            style = document.styles[style_name]
        except KeyError:
            continue
        style_font(style, BODY_LATIN, BODY_CJK, size=10.5, bold=False)
        style.paragraph_format.line_spacing = 1.4

    # 目录域生成的三级样式：压紧行距，避免目录占满三页
    for style_name in ("TOC 1", "TOC 2", "TOC 3", "TOC1", "TOC2", "TOC3"):
        try:
            style = document.styles[style_name]
        except KeyError:
            continue
        style_font(style, BODY_LATIN, BODY_CJK, size=10.5, bold=False)
        style.paragraph_format.space_before = Pt(0)
        style.paragraph_format.space_after = Pt(0)
        style.paragraph_format.line_spacing = 1.25




    shot_dir = screenshot_dir if (screenshot_dir and screenshot_dir.is_dir()) else None
    blocks = group_figures(parse_markdown(md), shot_dir)
    toc_done = False

    for block in blocks:
        kind = block[0]

        if kind == "heading":
            level, text = block[1], strip_inline(block[2])
            if level == 1:
                # 文档主标题
                paragraph = document.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = paragraph.add_run(text)
                apply_font(run, HEADING_LATIN, HEADING_CJK, size=24, bold=True)
                paragraph.paragraph_format.space_before = Pt(60)
                paragraph.paragraph_format.space_after = Pt(24)
                continue
            if level == 2 and not toc_done and text.startswith("一、"):
                # 第一个二级标题前插入目录，目录单独占一页
                # 已有满版封面时，分节符已经换过页，不必再插分页符
                if not has_cover:
                    document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                add_toc(document)
                document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
                toc_done = True
            # 封面区域的标题用普通段落排版，不用 Heading 样式，避免被目录收录
            if not toc_done:
                cover_sizes = {2: 18, 3: 15, 4: 12}
                para = document.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_before = Pt(10)
                para.paragraph_format.space_after = Pt(10)
                run = para.add_run(text)
                apply_font(run, HEADING_LATIN, HEADING_CJK, size=cover_sizes.get(level, 12), bold=True)
                continue

            # Markdown 的 ## -> Word Heading 1，### -> Heading 2，#### -> Heading 3
            word_level = max(1, min(level - 1, 3))
            heading = document.add_heading("", level=word_level)
            run = heading.add_run(text)
            apply_font(run, HEADING_LATIN, HEADING_CJK, bold=True)
            continue

        if kind == "fullcover":
            candidate = Path(block[1])
            if not candidate.is_absolute():
                # 封面图放在 output 根目录，其余配图在 screenshots 下
                for base in (ROOT, shot_dir):
                    if base and (base / block[1]).is_file():
                        candidate = base / block[1]
                        break
            image_path = candidate
            para = document.add_paragraph()
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.space_before = Pt(0)
            para.paragraph_format.space_after = Pt(0)
            para.paragraph_format.line_spacing = 1.0
            try:
                embed = shrink_for_doc(image_path, tmp_dir)
                para.add_run().add_picture(str(embed), width=Cm(21), height=Cm(29.7))
            except Exception as exc:
                para.add_run(f"[封面图插入失败: {image_path.name} - {exc}]")

            # 封面之后另起一节，恢复正常页边距与页脚
            body_section = document.add_section(WD_SECTION.NEW_PAGE)
            body_section.page_width = Cm(21)
            body_section.page_height = Cm(29.7)
            body_section.left_margin = Cm(2.8)
            body_section.right_margin = Cm(2.8)
            body_section.top_margin = Cm(2.5)
            body_section.bottom_margin = Cm(2.5)
            add_page_number_footer(body_section)
            continue

        if kind == "pagebreak":
            document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            continue

        if kind == "figurerow":
            entries = []
            for rel_path, caption in [(b[1], strip_inline(b[2])) for b in block[1]]:
                image_path = shot_dir / rel_path if shot_dir else Path(rel_path)
                if image_path.is_file():
                    entries.append((image_path, caption))
                else:
                    note = document.add_paragraph()
                    run = note.add_run(f"[缺图：{rel_path}]")
                    apply_font(run, BODY_LATIN, BODY_CJK, size=9)
            if not entries:
                continue
            # 竖图一律按并排尺寸插入，单张时也保持与其他图同样高度；
            # 只有横图（沉浸式页面）独占一行、铺满版心。
            if len(entries) == 1 and _aspect(entries[0][0]) <= 1.5:
                add_image(document, entries[0][0], entries[0][1], tmp_dir)
            else:
                add_image_row(document, entries, tmp_dir)
            continue

        if kind == "paragraph":
            if block[1].strip() == "<br>":
                document.add_paragraph()
                continue
            if not toc_done:
                # 封面信息块：不缩进，整体右移居中，逐行排布
                para = document.add_paragraph()
                para.paragraph_format.left_indent = Cm(3.2)
                para.paragraph_format.line_spacing = 2.0
                for seg_index, segment in enumerate(_visual_lines(block[1])):
                    if seg_index:
                        para.add_run().add_break()
                    for chunk_index, chunk in enumerate(re.split(r"\*\*(.+?)\*\*", segment)):
                        if not chunk:
                            continue
                        run = para.add_run(chunk)
                        apply_font(run, BODY_LATIN, BODY_CJK, size=11)
                        if chunk_index % 2 == 1:
                            run.bold = True
                continue
            add_rich_paragraph(document, block[1], indent=True)
            continue

        if kind == "list":
            for item in block[1]:
                add_rich_paragraph(document, item, style="List Bullet")
            continue

        if kind == "quote":
            paragraph = document.add_paragraph()
            run = paragraph.add_run(strip_inline(block[1]))
            apply_font(run, BODY_LATIN, BODY_CJK, size=9.5)
            run.italic = True
            run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            paragraph.paragraph_format.left_indent = Pt(21)
            continue

        if kind == "code":
            add_code_block(document, block[1])
            document.add_paragraph()
            continue

        if kind == "table":
            add_table(document, [[strip_inline(c) for c in row] for row in block[1]], borderless=not toc_done)
            continue

    document.save(OUT_PATH)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"已生成: {OUT_PATH}  ({OUT_PATH.stat().st_size / 1024 / 1024:.1f} MB)")


def main() -> int:
    screenshot_dir = None
    if "--screenshots" in sys.argv:
        pos = sys.argv.index("--screenshots")
        if pos + 1 < len(sys.argv):
            screenshot_dir = Path(sys.argv[pos + 1])
    else:
        candidate = ROOT / "screenshots"
        if candidate.is_dir():
            screenshot_dir = candidate

    build(screenshot_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
