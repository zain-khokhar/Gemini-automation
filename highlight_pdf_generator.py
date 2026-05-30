"""
Highlighted PDF Generator Module
Generates professionally formatted PDFs from highlighted Markdown text.

The input Markdown contains **bold** markers on important text.
These bold markers are converted to yellow-highlighted text in the PDF.

Design:
- Uses PyMuPDF (fitz) to directly annotate the original PDF, ensuring 100% layout match.
- First page: Same promotional page as MCQ/Notes (via PromoPageManager)
- Last page: Same promotional page
"""

import re
import os
import io
from pathlib import Path
from typing import Optional, Tuple

import fitz
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4

from pdf_generator import (
    PromoPageManager, _create_page_handler, _append_last_page,
    _resolve_font, _hex_to_color, _load_editor_settings,
    PRIMARY_BLUE, _escape
)


# ─────────────────────────────────────────────────────────────
#  Default Configuration
# ─────────────────────────────────────────────────────────────
DEFAULT_HIGHLIGHT_COLOR = [1.0, 0.96, 0.61]  # Warm readable yellow #FFF59D


def _extract_bold_phrases(markdown_text: str) -> list:
    """Extract all **bold** phrases from the markdown text."""
    phrases = []
    # Match any content inside ** **
    matches = re.findall(r'\*\*(.*?)\*\*', markdown_text, re.DOTALL)
    seen = set()
    for m in matches:
        # Clean up whitespace and newlines
        clean_text = re.sub(r'\s+', ' ', m).strip()
        # Ignore extremely short strings and common words to prevent false positive highlights
        if clean_text and len(clean_text) >= 3:
            # Deduplicate: only keep first occurrence of each phrase
            lower_key = clean_text.lower()
            if lower_key not in seen:
                seen.add(lower_key)
                phrases.append(clean_text)
    return phrases


def _generate_promo_page_pdf(promo: PromoPageManager, is_first: bool) -> bytes:
    """Generate a single promotional page using ReportLab and return as PDF bytes."""
    buffer = io.BytesIO()
    c = rl_canvas.Canvas(buffer, pagesize=A4)
    if is_first:
        promo.draw_first_page(c)
    else:
        promo.draw_last_page(c)
    c.save()
    buffer.seek(0)
    return buffer.read()


# Maximum highlights per page to prevent visual overload
MAX_HIGHLIGHTS_PER_PAGE = 40


def generate_highlighted_pdf(highlighted_markdown: str, output_path: str,
                             original_pdf_path: str,
                             page_range: Optional[Tuple[int, int]] = None,
                             title: str = "Highlighted Handout",
                             doc_type: str = "highlighted") -> str:
    """
    Generate a highlighted PDF by annotating the original PDF.

    Args:
        highlighted_markdown: Markdown text with **bold** markers on important text
        output_path: Output PDF file path
        original_pdf_path: Path to the original unhighlighted PDF
        page_range: Optional tuple (start_page, end_page) to extract a subset of pages.
        title: Title for the document (used if promo pages are generated differently, but mostly ignored here)
        doc_type: Document type for settings lookup ('highlighted')

    Returns:
        Path to generated PDF
    """
    if not os.path.exists(original_pdf_path):
        raise FileNotFoundError(f"Original PDF not found: {original_pdf_path}")

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 1. Extract phrases to highlight
    bold_phrases = _extract_bold_phrases(highlighted_markdown)

    # 2. Open original PDF
    doc = fitz.open(original_pdf_path)

    # 3. Apply page range if specified
    if page_range:
        start_page, end_page = page_range
        # Ensure indices are within bounds
        start_page = max(0, start_page)
        end_page = min(len(doc) - 1, end_page)
        if start_page <= end_page:
            doc.select(range(start_page, end_page + 1))

    # 4. Apply Highlights
    # Track highlights per page to enforce cap and avoid redundancy
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_highlight_count = 0
        already_highlighted_on_page = set()
        
        # Extract page text for quick containment check
        page_text = page.get_text("text").replace('\n', ' ')
        
        for phrase in bold_phrases:
            # Enforce per-page cap
            if page_highlight_count >= MAX_HIGHLIGHTS_PER_PAGE:
                break
            
            # Skip if phrase already highlighted on this page
            phrase_lower = phrase.lower()
            if phrase_lower in already_highlighted_on_page:
                continue
            
            # Quick containment check — skip expensive search if phrase not in page text
            if phrase.lower() not in page_text.lower():
                continue
            
            # Using PyMuPDF's search_for. quads=True gives us quadrilateral coordinates
            # which works better for multi-line highlights.
            quads = page.search_for(phrase, quads=True)
            if quads:
                # Only highlight first occurrence on this page
                annot = page.add_highlight_annot(quads[0])
                annot.set_colors(stroke=DEFAULT_HIGHLIGHT_COLOR)
                annot.update()
                page_highlight_count += 1
                already_highlighted_on_page.add(phrase_lower)

    # 5. Handle Promotional Pages
    promo = PromoPageManager(doc_type)
    if not promo._first_enabled and not promo._last_enabled:
        promo = PromoPageManager("mcq")

    # We will build a new final document that includes promo pages
    final_doc = fitz.open()

    if promo._first_enabled:
        first_pdf_bytes = _generate_promo_page_pdf(promo, is_first=True)
        first_doc = fitz.open("pdf", first_pdf_bytes)
        final_doc.insert_pdf(first_doc)
        first_doc.close()

    # Insert the highlighted original document
    final_doc.insert_pdf(doc)
    doc.close()

    if promo._last_enabled:
        last_pdf_bytes = _generate_promo_page_pdf(promo, is_first=False)
        last_doc = fitz.open("pdf", last_pdf_bytes)
        final_doc.insert_pdf(last_doc)
        last_doc.close()

    # 6. Save final PDF
    final_doc.save(output_path)
    final_doc.close()

    print(f"✓ Highlighted PDF generated: {output_path}")
    return output_path
