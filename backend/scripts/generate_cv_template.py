"""Generate the Pandoc reference DOCX used to style ATS-friendly CVs.

Pandoc only copies STYLES from the reference doc — it doesn't copy
content. So this script programmatically creates a docx with:
  - Calibri 11pt body, justified left
  - 0.6" margins (tighter than Word default; fits more content per page)
  - H1 (candidate name): 24pt bold, no underline
  - H2 (section header — Summary, Experience, ...): 13pt bold uppercase
    spacing, with bottom border
  - H3 (role/entry header): 12pt bold
  - Bullet list: small disc, tight spacing (6pt before, 0pt after)
  - No tables, no images, no graphics, no footnotes
  - Hyperlinks: blue underlined (default Word style)

These are deliberate ATS-parser-friendly choices:
  - Single-column layout — multi-column resumes routinely fail parsing
  - Calibri / Arial — fonts ATS engines whitelist
  - No graphic shapes, text boxes — parsers strip them and lose content
  - Date ranges as plain text inline, not in a side column

Usage (from repo root):

    python backend/scripts/generate_cv_template.py

Re-run after editing this file to refresh the template. Output goes to
`backend/templates/cv-ats-template.docx` — committed to the repo so the
Docker build picks it up without needing a build-time pandoc invocation.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Inches, Pt, RGBColor

OUT_PATH = Path(__file__).resolve().parents[1] / "templates" / "cv-ats-template.docx"


def _set_paragraph_border(paragraph, *, bottom: bool = False):
    """Add a hairline border below the paragraph (used on H2 section
    headers for visual separation without being heavy)."""
    if not bottom:
        return
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom_bdr = OxmlElement("w:bottom")
    bottom_bdr.set(qn("w:val"), "single")
    bottom_bdr.set(qn("w:sz"), "6")  # 0.75pt
    bottom_bdr.set(qn("w:space"), "1")
    bottom_bdr.set(qn("w:color"), "808080")
    p_bdr.append(bottom_bdr)
    p_pr.append(p_bdr)


def _configure_style(
    doc,
    name: str,
    *,
    font_name: str = "Calibri",
    font_size_pt: float | None = None,
    bold: bool = False,
    italic: bool = False,
    color: tuple[int, int, int] | None = None,
    space_before_pt: float = 0,
    space_after_pt: float = 0,
    all_caps: bool = False,
    keep_with_next: bool = False,
):
    """Update a built-in style by name. Pandoc maps:
        Heading 1 -> # in markdown
        Heading 2 -> ##
        Heading 3 -> ###
        Normal    -> body text
        List Bullet -> - / * lists
    Keeping the names matches Pandoc's expectations exactly."""
    style = doc.styles[name]
    font = style.font
    font.name = font_name
    if font_size_pt is not None:
        font.size = Pt(font_size_pt)
    font.bold = bold
    font.italic = italic
    if color is not None:
        font.color.rgb = RGBColor(*color)

    pf = style.paragraph_format
    pf.space_before = Pt(space_before_pt)
    pf.space_after = Pt(space_after_pt)
    pf.keep_with_next = keep_with_next

    # All-caps tracking for section headers (Word's "all caps" character
    # property; ATS parsers handle either case fine but it reads better).
    if all_caps:
        rpr = style.element.get_or_add_rPr()
        caps = OxmlElement("w:caps")
        caps.set(qn("w:val"), "true")
        rpr.append(caps)


def main() -> int:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    # --- Page setup ---------------------------------------------------
    # Tight 0.6" all-around margins → ~10% more content per page than
    # the Word 1.0" default without crashing into ATS parser limits.
    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.7)
        section.right_margin = Inches(0.7)
        # US Letter is the safer default for international ATS — most
        # parsers handle A4 fine but some fall over on non-letter sizes.
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)

    # --- Body / Normal -----------------------------------------------
    _configure_style(
        doc,
        "Normal",
        font_size_pt=11,
        space_after_pt=4,
    )

    # --- H1 (candidate name, top of doc) -----------------------------
    _configure_style(
        doc,
        "Heading 1",
        font_size_pt=24,
        bold=True,
        color=(20, 30, 50),  # near-black with a hint of navy
        space_before_pt=0,
        space_after_pt=2,
        keep_with_next=True,
    )

    # --- H2 (section headers — Summary / Experience / ...) ----------
    _configure_style(
        doc,
        "Heading 2",
        font_size_pt=13,
        bold=True,
        color=(20, 30, 50),
        space_before_pt=12,
        space_after_pt=4,
        all_caps=True,
        keep_with_next=True,
    )

    # --- H3 (role / project / school entry header) -------------------
    _configure_style(
        doc,
        "Heading 3",
        font_size_pt=12,
        bold=True,
        color=(0, 0, 0),
        space_before_pt=8,
        space_after_pt=2,
        keep_with_next=True,
    )

    # --- Bullet lists ------------------------------------------------
    # Pandoc emits "List Bullet" for `- item` markdown.
    _configure_style(
        doc,
        "List Bullet",
        font_size_pt=11,
        space_before_pt=0,
        space_after_pt=2,
    )

    # --- Block quotes (used for date / location meta lines) ----------
    # Pandoc maps `_text_` italics to runs — the meta line under each
    # H3 is italicized, not block-quoted, so this is mostly cosmetic
    # but worth setting correctly for any future markdown that uses >.
    if "Quote" in [s.name for s in doc.styles]:
        _configure_style(
            doc,
            "Quote",
            font_size_pt=10,
            italic=True,
            color=(80, 80, 80),
            space_before_pt=2,
            space_after_pt=4,
        )

    # --- Sample content ----------------------------------------------
    # Pandoc only copies STYLES from this template — it ignores the
    # actual content here. The sample paragraphs exist so a designer
    # opening this file in Word sees a styled preview to edit.
    name = doc.add_paragraph("Your Name", style="Heading 1")
    contact = doc.add_paragraph(
        "your.email@example.com · +00 000 000 000 · City, Country"
    )
    contact.runs[0].font.size = Pt(10)

    h2 = doc.add_paragraph("SUMMARY", style="Heading 2")
    _set_paragraph_border(h2, bottom=True)
    doc.add_paragraph(
        "Two-to-three sentence professional summary highlighting your most "
        "relevant experience and the value you bring to the role."
    )

    h2 = doc.add_paragraph("EXPERIENCE", style="Heading 2")
    _set_paragraph_border(h2, bottom=True)
    doc.add_paragraph("Job Title · Company Name", style="Heading 3")
    meta = doc.add_paragraph("Jan 2024 – Present · Location")
    meta.runs[0].italic = True
    meta.runs[0].font.size = Pt(10)
    meta.runs[0].font.color.rgb = RGBColor(80, 80, 80)
    doc.add_paragraph(
        "One or two sentences summarizing the role and your scope."
    )
    doc.add_paragraph("Quantified achievement bullet 1", style="List Bullet")
    doc.add_paragraph("Quantified achievement bullet 2", style="List Bullet")

    doc.save(OUT_PATH)
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
