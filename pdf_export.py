"""
Turns the translated explanation into a downloadable PDF. reportlab's
built-in fonts don't have Indic glyphs, so each language gets its own
Noto font registered from the fonts/ folder - without this, Hindi/Tamil/
etc. text would render as blank boxes.
"""
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

import config

_registered = set()


def _font_for(language: str) -> str:
    """Registers the right font for this language (once) and returns
    its name for use in a paragraph style."""
    font_path = config.LANGUAGES.get(language, {}).get("font")
    if not font_path:
        return "Helvetica"  # English - built-in font is fine

    font_name = f"Noto-{language}"
    if font_name not in _registered:
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        _registered.add(font_name)
    return font_name


def build_pdf(output_path: str, medicines: list[dict], explanation: str, language: str):
    font_name = _font_for(language)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontName=font_name)
    body_style = ParagraphStyle("Body2", parent=styles["Normal"], fontName=font_name, leading=18)
    heading_style = ParagraphStyle("Heading2b", parent=styles["Heading2"], fontName=font_name)

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    story = [Paragraph("PresciMate - Your Prescription Explained", title_style), Spacer(1, 16)]

    story.append(Paragraph("Medicines", heading_style))
    for m in medicines:
        line = f"{m['name']} - {m.get('dosage') or ''} {m.get('frequency') or ''} {m.get('duration') or ''}"
        story.append(Paragraph(line, body_style))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Explanation", heading_style))
    for paragraph in explanation.split("\n\n"):
        if paragraph.strip():
            story.append(Paragraph(paragraph.replace("\n", "<br/>"), body_style))
            story.append(Spacer(1, 8))

    story.append(Spacer(1, 16))
    story.append(Paragraph(config.DISCLAIMER, ParagraphStyle("Small", parent=body_style, fontSize=9)))

    doc.build(story)
    return output_path
