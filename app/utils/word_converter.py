"""
Markdown 转 PDF 工具

负责把 Markdown 文本解析成 ReportLab 文档元素，再生成 PDF
该方案不依赖 Microsoft Word、浏览器或系统级 PDF 工具，可在 macOS、Windows 和 Linux 上运行
"""

import html
import logging
import re
from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import (
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    colors = None
    A4 = None
    ParagraphStyle = None
    cm = None
    pdfmetrics = None
    UnicodeCIDFont = None
    Paragraph = None
    Preformatted = None
    SimpleDocTemplate = None
    Spacer = None
    Table = None
    TableStyle = None


def convert_md_to_pdf(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """
    将 Markdown 文件转换为 PDF

    :param md_abs_path: Markdown 文件绝对路径
    :param pdf_abs_path: 输出 PDF 文件绝对路径
    :return: 转换结果说明
    """
    if SimpleDocTemplate is None:
        return "缺少依赖库，请安装 reportlab"

    try:
        with open(md_abs_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        pdf_abs_path.parent.mkdir(parents=True, exist_ok=True)
        _register_fonts()

        doc = SimpleDocTemplate(
            str(pdf_abs_path),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=md_abs_path.stem,
        )
        styles = _build_styles()
        story = _markdown_to_story(md_content, styles)
        doc.build(story)

        if pdf_abs_path.exists():
            return f"成功转换: {pdf_abs_path}"
        return f"转换完成但未生成文件: {pdf_abs_path}"

    except Exception as e:
        logging.error(f"Markdown 转 PDF 失败: {e}", exc_info=True)
        return f"转换失败: {str(e)}"


def _register_fonts() -> None:
    """
    注册内置中文 CID 字体，保证中文内容在 PDF 中可见
    """
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    except Exception:
        pass


def _build_styles() -> dict[str, ParagraphStyle]:
    """
    构建 PDF 文档样式
    """
    base_font = "STSong-Light"
    code_font = "Courier"

    return {
        "body": ParagraphStyle(
            "Body",
            fontName=base_font,
            fontSize=11,
            leading=17,
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            fontName=base_font,
            fontSize=22,
            leading=28,
            spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            fontName=base_font,
            fontSize=17,
            leading=23,
            spaceBefore=8,
            spaceAfter=10,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            fontName=base_font,
            fontSize=14,
            leading=20,
            spaceBefore=6,
            spaceAfter=8,
        ),
        "code": ParagraphStyle(
            "Code",
            fontName=code_font,
            fontSize=9,
            leading=12,
            leftIndent=8,
            rightIndent=8,
            spaceBefore=6,
            spaceAfter=8,
        ),
    }


def _markdown_to_story(
    md_content: str,
    styles: dict[str, ParagraphStyle],
) -> list:
    """
    将常见 Markdown 结构转换为 ReportLab story
    """
    story = []
    lines = md_content.splitlines()
    index = 0
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            text = " ".join(line.strip() for line in paragraph_lines)
            story.append(Paragraph(_format_inline(text), styles["body"]))
            paragraph_lines.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            story.append(Spacer(1, 6))
            index += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            story.append(Preformatted("\n".join(code_lines), styles["code"]))
            index += 1
            continue

        if _is_table_start(lines, index):
            flush_paragraph()
            table_rows, index = _collect_table(lines, index)
            story.append(_build_table(table_rows, styles))
            story.append(Spacer(1, 8))
            continue

        heading = _parse_heading(stripped)
        if heading:
            flush_paragraph()
            level, text = heading
            style_name = "h1" if level == 1 else "h2" if level == 2 else "h3"
            story.append(Paragraph(_format_inline(text), styles[style_name]))
            index += 1
            continue

        bullet = _parse_bullet(stripped)
        if bullet:
            flush_paragraph()
            story.append(Paragraph(f"• {_format_inline(bullet)}", styles["body"]))
            index += 1
            continue

        paragraph_lines.append(line)
        index += 1

    flush_paragraph()
    return story


def _parse_heading(line: str) -> tuple[int, str] | None:
    """
    解析 Markdown 标题
    """
    match = re.match(r"^(#{1,6})\s+(.+)$", line)
    if not match:
        return None
    return len(match.group(1)), match.group(2)


def _parse_bullet(line: str) -> str | None:
    """
    解析无序列表项
    """
    match = re.match(r"^[-*]\s+(.+)$", line)
    if not match:
        return None
    return match.group(1)


def _is_table_start(lines: list[str], index: int) -> bool:
    """
    判断当前位置是否是 Markdown 表格起点
    """
    if index + 1 >= len(lines):
        return False
    current = lines[index].strip()
    separator = lines[index + 1].strip()
    return "|" in current and bool(
        re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$", separator)
    )


def _collect_table(lines: list[str], index: int) -> tuple[list[list[str]], int]:
    """
    收集连续 Markdown 表格行
    """
    rows = [_split_table_row(lines[index])]
    index += 2
    while index < len(lines) and "|" in lines[index]:
        rows.append(_split_table_row(lines[index]))
        index += 1
    return rows, index


def _split_table_row(line: str) -> list[str]:
    """
    拆分 Markdown 表格行
    """
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _build_table(rows: list[list[str]], styles: dict[str, ParagraphStyle]):
    """
    构建 PDF 表格
    """
    column_count = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (column_count - len(row)) for row in rows]
    data = [
        [Paragraph(_format_inline(cell), styles["body"]) for cell in row]
        for row in normalized_rows
    ]
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _format_inline(text: str) -> str:
    """
    处理基础行内 Markdown 标记
    """
    escaped = html.escape(text)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"`(.+?)`", r'<font name="Courier">\1</font>', escaped)
    return escaped
