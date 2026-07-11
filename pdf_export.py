"""
Turns the translated explanation into a downloadable PDF. reportlab's
built-in fonts don't have Indic glyphs, so each language gets its own
Noto font registered from the fonts/ folder - without this, Hindi/Tamil/
etc. text would render as blank boxes.

The LLM's explanation comes back with markdown (**bold**, * bullets) in
it, but reportlab's Paragraph doesn't understand markdown - it uses its
own limited HTML-like tags (<b>, <br/>, etc.). Without converting one to
the other, the PDF would show literal asterisks instead of bold text.
"""
import re
from xml.sax.saxutils import escape

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


def _markdown_to_reportlab(text: str) -> str:
    """Converts the LLM's markdown into reportlab's mini-markup, and
    escapes anything that would otherwise break its XML-ish parser.
    Order matters: escape first (so a literal '<' in the text can't be
    mistaken for a tag), THEN add our own <b> and <br/> tags."""
    text = escape(text)  # protects &, <, > before we add real tags
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)  # **bold** -> <b>bold</b>
    lines = [re.sub(r"^\*\s+", "\u2022 ", line) for line in text.split("\n")]  # "* " -> "• "
    return "<br/>".join(lines)


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
        story.append(Paragraph(escape(line), body_style))
    story.append(Spacer(1, 16))

    story.append(Paragraph("Explanation", heading_style))
    for paragraph in explanation.split("\n\n"):
        if paragraph.strip():
            story.append(Paragraph(_markdown_to_reportlab(paragraph), body_style))
            story.append(Spacer(1, 8))

    story.append(Spacer(1, 16))
    story.append(Paragraph(escape(config.DISCLAIMER), ParagraphStyle("Small", parent=body_style, fontSize=9)))

    doc.build(story)
    return output_path
