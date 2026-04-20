"""Export a diff result to a self-contained HTML document or a PDF.

HTML export embeds all CSS inline so the file is portable.
PDF export draws the diff with reportlab if installed; otherwise raises
RuntimeError with a clear message so the caller can surface it to the UI.
"""

from __future__ import annotations

import html
from datetime import datetime


def _esc(s: str) -> str:
    return html.escape(s if s is not None else "", quote=True)


def to_html(record: dict) -> str:
    rows = record["rows"]
    summary = record["summary"]
    meta = {
        "format": record.get("format", "text"),
        "created_at": record.get("created_at", datetime.utcnow().isoformat() + "Z"),
        "title": record.get("title", "API Response Comparison"),
        "ignore": ", ".join(record.get("ignore", []) or []) or "—",
    }

    def render_row(r):
        tag = r["tag"]
        l_no = r["left_no"] if r["left_no"] is not None else ""
        r_no = r["right_no"] if r["right_no"] is not None else ""
        return (
            f'<tr class="row {tag}">'
            f'<td class="ln">{l_no}</td>'
            f'<td class="code left">{_esc(r["left"]) or "&nbsp;"}</td>'
            f'<td class="ln">{r_no}</td>'
            f'<td class="code right">{_esc(r["right"]) or "&nbsp;"}</td>'
            f"</tr>"
        )

    body_rows = "\n".join(render_row(r) for r in rows)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{_esc(meta["title"])}</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: -apple-system, system-ui, "Segoe UI", sans-serif; margin: 24px; color: #111; background: #fff; }}
  header {{ border-bottom: 1px solid #ddd; padding-bottom: 12px; margin-bottom: 16px; }}
  h1 {{ margin: 0 0 6px; font-size: 20px; }}
  .meta {{ font-size: 13px; color: #555; }}
  .meta span {{ margin-right: 16px; }}
  .summary {{ display: flex; gap: 8px; margin: 12px 0 20px; flex-wrap: wrap; }}
  .pill {{ padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
  .pill.equal {{ background: #eef; color: #335; }}
  .pill.added {{ background: #e7f7ea; color: #155724; }}
  .pill.removed {{ background: #fdecea; color: #842029; }}
  .pill.changed {{ background: #fff4d6; color: #7a5a00; }}
  table.diff {{ width: 100%; border-collapse: collapse; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12.5px; }}
  table.diff td {{ padding: 2px 8px; vertical-align: top; white-space: pre-wrap; word-break: break-word; }}
  .ln {{ width: 44px; text-align: right; color: #999; user-select: none; background: #fafafa; border-right: 1px solid #eee; }}
  tr.added .right {{ background: #e7f7ea; }}
  tr.added .left  {{ background: #f7f7f7; }}
  tr.removed .left  {{ background: #fdecea; }}
  tr.removed .right {{ background: #f7f7f7; }}
  tr.changed .left  {{ background: #fff4d6; }}
  tr.changed .right {{ background: #fff4d6; }}
  tr.equal td.code {{ background: #fff; }}
  @media print {{
    body {{ margin: 12mm; }}
    tr {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<header>
  <h1>{_esc(meta["title"])}</h1>
  <div class="meta">
    <span><b>Format:</b> {_esc(meta["format"])}</span>
    <span><b>Created:</b> {_esc(meta["created_at"])}</span>
    <span><b>Ignored:</b> {_esc(meta["ignore"])}</span>
  </div>
  <div class="summary">
    <span class="pill equal">{summary.get("equal",0)} equal</span>
    <span class="pill added">{summary.get("added",0)} added</span>
    <span class="pill removed">{summary.get("removed",0)} removed</span>
    <span class="pill changed">{summary.get("changed",0)} changed</span>
  </div>
</header>
<table class="diff">
  <colgroup>
    <col><col style="width:50%"><col><col style="width:50%">
  </colgroup>
  <tbody>
{body_rows}
  </tbody>
</table>
</body>
</html>"""


def to_pdf(record: dict) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
    except ImportError as e:
        raise RuntimeError(
            "PDF export requires the 'reportlab' package. "
            "Install it with: pip install reportlab"
        ) from e

    from io import BytesIO

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(letter),
        leftMargin=0.4 * inch, rightMargin=0.4 * inch,
        topMargin=0.4 * inch, bottomMargin=0.4 * inch,
    )
    styles = getSampleStyleSheet()
    mono = ParagraphStyle(
        "mono", parent=styles["BodyText"],
        fontName="Courier", fontSize=7.5, leading=9, wordWrap="CJK",
    )
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=14, spaceAfter=4)
    meta = ParagraphStyle("meta", parent=styles["BodyText"], fontSize=9, textColor=colors.grey)

    story = []
    story.append(Paragraph(_esc(record.get("title", "API Response Comparison")), h1))
    summary = record["summary"]
    ignore = ", ".join(record.get("ignore", []) or []) or "—"
    story.append(Paragraph(
        f"Format: {_esc(record.get('format','text'))} &nbsp;&nbsp; "
        f"Created: {_esc(record.get('created_at',''))} &nbsp;&nbsp; "
        f"Ignored: {_esc(ignore)}",
        meta,
    ))
    story.append(Paragraph(
        f"equal={summary.get('equal',0)} &nbsp; added={summary.get('added',0)} "
        f"&nbsp; removed={summary.get('removed',0)} &nbsp; changed={summary.get('changed',0)}",
        meta,
    ))
    story.append(Spacer(1, 8))

    color_for = {
        "added":   colors.HexColor("#e7f7ea"),
        "removed": colors.HexColor("#fdecea"),
        "changed": colors.HexColor("#fff4d6"),
        "equal":   colors.white,
    }

    data = [["#", "Left", "#", "Right"]]
    row_styles = []
    for i, r in enumerate(record["rows"], start=1):
        left  = (r["left"]  or "").replace("\t", "    ")
        right = (r["right"] or "").replace("\t", "    ")
        data.append([
            str(r["left_no"]) if r["left_no"] is not None else "",
            Paragraph(_esc(left) or "&nbsp;", mono),
            str(r["right_no"]) if r["right_no"] is not None else "",
            Paragraph(_esc(right) or "&nbsp;", mono),
        ])
        bg = color_for.get(r["tag"], colors.white)
        row_styles.append(("BACKGROUND", (1, i), (1, i), bg if r["tag"] != "added" else colors.HexColor("#f7f7f7")))
        row_styles.append(("BACKGROUND", (3, i), (3, i), bg if r["tag"] != "removed" else colors.HexColor("#f7f7f7")))
        if r["tag"] == "added":
            row_styles.append(("BACKGROUND", (3, i), (3, i), color_for["added"]))
        if r["tag"] == "removed":
            row_styles.append(("BACKGROUND", (1, i), (1, i), color_for["removed"]))

    avail = landscape(letter)[0] - 0.8 * inch
    ln = 0.35 * inch
    code = (avail - 2 * ln) / 2
    t = Table(data, colWidths=[ln, code, ln, code], repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("GRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONT", (0, 1), (0, -1), "Helvetica", 7),
        ("FONT", (2, 1), (2, -1), "Helvetica", 7),
        ("TEXTCOLOR", (0, 1), (0, -1), colors.grey),
        ("TEXTCOLOR", (2, 1), (2, -1), colors.grey),
        *row_styles,
    ]))
    story.append(t)
    doc.build(story)
    return buf.getvalue()
