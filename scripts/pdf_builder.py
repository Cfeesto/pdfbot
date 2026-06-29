"""
pdf_builder.py — build a styled PDF from generated content dict.
Uses reportlab. Fetches a relevant header image from Unsplash (free API).
"""

import os
import io
import requests
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    HRFlowable, PageBreak, Table, TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

# Brand colours
PRIMARY   = colors.HexColor("#1a1a2e")
ACCENT    = colors.HexColor("#e94560")
LIGHT_BG  = colors.HexColor("#f8f9fa")
BODY_TEXT = colors.HexColor("#2d2d2d")

W, H = A4


def _fetch_image(query: str, width_px: int = 800) -> io.BytesIO | None:
    """Fetch a royalty-free image from Unsplash Source (no API key needed)."""
    try:
        url = f"https://source.unsplash.com/{width_px}x400/?{query.replace(' ', ',')}"
        r = requests.get(url, timeout=10, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("Content-Type", ""):
            return io.BytesIO(r.content)
    except Exception:
        pass
    return None


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"],
            fontSize=28, textColor=colors.white,
            alignment=TA_CENTER, spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontSize=14, textColor=colors.HexColor("#cccccc"),
            alignment=TA_CENTER, spaceAfter=0,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"],
            fontSize=16, textColor=PRIMARY,
            fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=6,
            borderPad=4,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=11, textColor=BODY_TEXT,
            leading=18, alignment=TA_JUSTIFY, spaceAfter=10,
        ),
        "tip": ParagraphStyle(
            "tip", parent=base["Normal"],
            fontSize=11, textColor=PRIMARY,
            leading=16, leftIndent=12, spaceAfter=6,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=9, textColor=colors.grey,
            alignment=TA_CENTER,
        ),
    }


def build_pdf(content: dict, output_path: str, btc_address: str = "") -> str:
    """
    Build a styled PDF from content dict.
    Returns output_path on success.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    s = _styles()
    story = []

    # ── Cover page ────────────────────────────────────────────────────────────
    # Dark header block with title
    header_data = [[
        Paragraph(content["title"], s["title"]),
    ]]
    header_table = Table(header_data, colWidths=[W - 4*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), PRIMARY),
        ("TOPPADDING",  (0, 0), (-1, -1), 24),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
        ("LEFTPADDING",  (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(content["subtitle"], s["subtitle"]))
    story.append(Spacer(1, 0.8*cm))

    # Header image
    img_buf = _fetch_image(content["title"])
    if img_buf:
        story.append(Image(img_buf, width=W - 4*cm, height=6*cm, kind="proportional"))
        story.append(Spacer(1, 0.5*cm))

    story.append(HRFlowable(width="100%", thickness=1, color=ACCENT))
    story.append(Spacer(1, 0.3*cm))

    # ── Introduction ──────────────────────────────────────────────────────────
    story.append(Paragraph("Introduction", s["h2"]))
    story.append(Paragraph(content["intro"], s["body"]))
    story.append(PageBreak())

    # ── Chapters ──────────────────────────────────────────────────────────────
    for i, chapter in enumerate(content["chapters"], 1):
        story.append(Paragraph(f"{i}. {chapter['heading']}", s["h2"]))
        story.append(HRFlowable(width="40%", thickness=2, color=ACCENT, spaceAfter=8))

        # Chapter image (every other chapter)
        if i % 2 == 0:
            ch_img = _fetch_image(chapter["heading"])
            if ch_img:
                story.append(Image(ch_img, width=W - 4*cm, height=4*cm, kind="proportional"))
                story.append(Spacer(1, 0.3*cm))

        story.append(Paragraph(chapter["body"], s["body"]))
        story.append(Spacer(1, 0.4*cm))

    story.append(PageBreak())

    # ── Tips ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("Quick Tips", s["h2"]))
    story.append(HRFlowable(width="40%", thickness=2, color=ACCENT, spaceAfter=8))
    for tip in content.get("tips", []):
        story.append(Paragraph(f"✓  {tip}", s["tip"]))
    story.append(Spacer(1, 0.6*cm))

    # ── Conclusion ────────────────────────────────────────────────────────────
    story.append(Paragraph("Conclusion", s["h2"]))
    story.append(Paragraph(content["conclusion"], s["body"]))

    # ── BTC payment footer ────────────────────────────────────────────────────
    if btc_address:
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            f"Enjoyed this guide? Support with Bitcoin:<br/>"
            f"<font name='Courier'>{btc_address}</font>",
            s["footer"],
        ))

    doc.build(story)
    return output_path


if __name__ == "__main__":
    # Quick test with dummy content
    dummy = {
        "title": "Complete Guide: AI Tools for Small Business",
        "subtitle": "Practical AI tools that save time and grow revenue",
        "intro": "AI is transforming small business. " * 10,
        "chapters": [
            {"heading": "Getting Started", "body": "Start with free tools. " * 40},
            {"heading": "Automation",      "body": "Automate repetitive tasks. " * 40},
            {"heading": "Marketing",       "body": "Use AI for content. " * 40},
            {"heading": "Customer Service","body": "Chatbots save time. " * 40},
            {"heading": "Finance",         "body": "AI for bookkeeping. " * 40},
        ],
        "tips": ["Start free", "Automate first", "Measure results", "Scale slowly", "Stay updated"],
        "conclusion": "AI is a tool, not a replacement. " * 8,
        "tags": ["ai", "smallbusiness", "productivity"],
    }
    build_pdf(dummy, "/tmp/test_guide.pdf", btc_address="YOUR_BTC_ADDRESS_HERE")
    print("PDF written to /tmp/test_guide.pdf")
