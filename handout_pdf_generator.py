"""
Handout PDF Generator Module
Converts processed handout JSON data into clean, formatted PDF handouts.

Uses ReportLab to generate academic-style PDF documents with:
- Title page
- Table of contents
- Structured lecture content with headings/subheadings
- Headers and footers with page numbers
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── Color palette ──
NAVY = HexColor('#1a1a2e')
ACCENT = HexColor('#4361ee')
ACCENT_LIGHT = HexColor('#e8ecfd')
TEXT_PRIMARY = HexColor('#1a1a2e')
TEXT_SECONDARY = HexColor('#5a6478')
TEXT_MUTED = HexColor('#9aa3b2')
BORDER = HexColor('#e4e7ed')
SUCCESS = HexColor('#22c55e')


def _build_styles():
    """Create document styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        'HandoutTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=8,
    ))

    styles.add(ParagraphStyle(
        'HandoutSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        textColor=TEXT_SECONDARY,
        alignment=TA_CENTER,
        spaceAfter=30,
    ))

    styles.add(ParagraphStyle(
        'LectureHeading',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=ACCENT,
        spaceBefore=20,
        spaceAfter=10,
        borderColor=ACCENT,
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=NAVY,
        spaceBefore=14,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        'SubsectionHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        textColor=TEXT_SECONDARY,
        spaceBefore=10,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        'BodyText_Handout',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        leading=15,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        'BulletPoint',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=TEXT_PRIMARY,
        leading=14,
        leftIndent=20,
        bulletIndent=8,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        'BlockQuote',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        textColor=ACCENT,
        leftIndent=20,
        rightIndent=20,
        leading=14,
        spaceBefore=6,
        spaceAfter=6,
        backColor=ACCENT_LIGHT,
    ))

    styles.add(ParagraphStyle(
        'KeyConcept',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=NAVY,
        leading=14,
        leftIndent=15,
        spaceAfter=4,
    ))

    styles.add(ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=TEXT_MUTED,
        alignment=TA_CENTER,
    ))

    return styles


def _markdown_to_flowables(md_text: str, styles) -> list:
    """
    Convert a Markdown-formatted handout into ReportLab flowables.
    
    Handles: headings (##, ###), bold (**), bullets (-), blockquotes (>),
    numbered lists, and paragraphs.
    """
    flowables = []
    lines = md_text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            i += 1
            continue
        
        # Heading level 2: ## Main Topic
        if stripped.startswith('## '):
            heading_text = stripped[3:].strip()
            heading_text = _clean_markdown_inline(heading_text)
            flowables.append(Spacer(1, 8))
            flowables.append(HRFlowable(width="100%", thickness=1, color=BORDER))
            flowables.append(Paragraph(heading_text, styles['SectionHeading']))
            i += 1
            continue
        
        # Heading level 3: ### Subtopic
        if stripped.startswith('### '):
            heading_text = stripped[4:].strip()
            heading_text = _clean_markdown_inline(heading_text)
            flowables.append(Paragraph(heading_text, styles['SubsectionHeading']))
            i += 1
            continue
        
        # Heading level 1: # (treat same as ##)
        if stripped.startswith('# ') and not stripped.startswith('## '):
            heading_text = stripped[2:].strip()
            heading_text = _clean_markdown_inline(heading_text)
            flowables.append(Spacer(1, 10))
            flowables.append(Paragraph(heading_text, styles['SectionHeading']))
            i += 1
            continue
        
        # Blockquote: > text
        if stripped.startswith('> '):
            quote_text = stripped[2:].strip()
            quote_text = _clean_markdown_inline(quote_text)
            flowables.append(Paragraph(f"❝ {quote_text}", styles['BlockQuote']))
            i += 1
            continue
        
        # Bullet point: - text or * text
        if re.match(r'^[-*]\s+', stripped):
            bullet_text = re.sub(r'^[-*]\s+', '', stripped)
            bullet_text = _clean_markdown_inline(bullet_text)
            flowables.append(Paragraph(f"• {bullet_text}", styles['BulletPoint']))
            i += 1
            continue
        
        # Numbered list: 1. text
        if re.match(r'^\d+\.\s+', stripped):
            num_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
            if num_match:
                num = num_match.group(1)
                text = _clean_markdown_inline(num_match.group(2))
                flowables.append(Paragraph(f"{num}. {text}", styles['BulletPoint']))
            i += 1
            continue
        
        # Key Concepts heading detection
        if 'key concepts' in stripped.lower() or 'key concept' in stripped.lower():
            heading_text = _clean_markdown_inline(stripped.lstrip('#').strip())
            flowables.append(Spacer(1, 6))
            flowables.append(Paragraph(f"📌 {heading_text}", styles['KeyConcept']))
            i += 1
            continue
        
        # Regular paragraph — collect continuous lines
        para_lines = [stripped]
        i += 1
        while i < len(lines):
            next_line = lines[i].strip()
            if not next_line or next_line.startswith('#') or next_line.startswith('>') or \
               next_line.startswith('- ') or next_line.startswith('* ') or \
               re.match(r'^\d+\.\s+', next_line):
                break
            para_lines.append(next_line)
            i += 1
        
        para_text = ' '.join(para_lines)
        para_text = _clean_markdown_inline(para_text)
        if para_text.strip():
            flowables.append(Paragraph(para_text, styles['BodyText_Handout']))
    
    return flowables


def _clean_markdown_inline(text: str) -> str:
    """Convert inline markdown to ReportLab XML tags."""
    # Bold: **text** → <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Italic: *text* → <i>text</i>
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'<i>\1</i>', text)
    # Inline code: `text` → <font face="Courier">text</font>
    text = re.sub(r'`(.*?)`', r'<font face="Courier" color="#d63384">\1</font>', text)
    # Escape XML entities
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # Restore our XML tags
    text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
    text = text.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
    text = text.replace('&lt;font ', '<font ').replace('&lt;/font&gt;', '</font>')
    text = re.sub(r'&lt;font(.*?)&gt;', r'<font\1>', text)
    return text


def _add_header_footer(canvas, doc, title="Lecture Handout"):
    """Draw page header and footer."""
    canvas.saveState()
    
    # Header
    canvas.setFillColor(NAVY)
    canvas.setFont('Helvetica', 8)
    canvas.drawString(cm * 2, A4[1] - cm * 1.2, title)
    
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawRightString(A4[0] - cm * 2, A4[1] - cm * 1.2, f"Page {doc.page}")
    
    # Header line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(cm * 2, A4[1] - cm * 1.5, A4[0] - cm * 2, A4[1] - cm * 1.5)
    
    # Footer
    canvas.setFillColor(TEXT_MUTED)
    canvas.setFont('Helvetica', 7)
    canvas.drawCentredString(A4[0] / 2, cm * 1, f"Generated by VU EDU Handout System • {datetime.now().strftime('%Y-%m-%d')}")
    
    canvas.restoreState()


def generate_handout_pdf(json_path: str, output_path: str, title: str = "",
                         subject_name: str = "", course_code: str = "") -> str:
    """
    Generate a handout PDF from processed handout JSON.
    
    Args:
        json_path: Path to handout JSON (or transcript JSON)
        output_path: Output PDF file path
        title: Document title
        subject_name: Subject name for title page
        course_code: Course code for title page
        
    Returns:
        Path to generated PDF
    """
    # Load JSON data
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        raise ValueError("Invalid JSON: expected a non-empty array of lecture entries")

    # Detect format: handout_data (has 'handout' key) vs transcript (has 'transcript' key)
    is_handout = 'handout' in data[0]
    content_key = 'handout' if is_handout else 'transcript'

    styles = _build_styles()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Build document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=cm * 2,
        rightMargin=cm * 2,
        topMargin=cm * 2,
        bottomMargin=cm * 2,
    )

    doc_title = title or f"{subject_name} ({course_code})"

    elements = []

    # ── Title Page ──
    elements.append(Spacer(1, 2 * inch))
    elements.append(Paragraph(doc_title, styles['HandoutTitle']))
    elements.append(Spacer(1, 10))
    
    subtitle_parts = []
    if subject_name:
        subtitle_parts.append(subject_name)
    if course_code:
        subtitle_parts.append(course_code)
    subtitle_parts.append(f"{len(data)} Lectures")
    subtitle_parts.append(f"Generated {datetime.now().strftime('%B %d, %Y')}")
    
    elements.append(Paragraph(" • ".join(subtitle_parts), styles['HandoutSubtitle']))
    elements.append(Spacer(1, 1 * inch))
    
    # Info box
    if is_handout:
        info_text = "This document contains structured academic handouts generated from YouTube lecture transcripts using AI-powered processing."
    else:
        info_text = "This document contains raw lecture transcripts. For structured handouts, process through Gemini first."
    
    elements.append(Paragraph(info_text, styles['BodyText_Handout']))
    elements.append(PageBreak())

    # ── Table of Contents ──
    elements.append(Paragraph("Table of Contents", styles['SectionHeading']))
    elements.append(Spacer(1, 10))
    
    for entry in data:
        lecture_num = entry.get('lecture', '?')
        content = entry.get(content_key, '')
        
        # Try to extract first heading from content
        first_heading = f"Lecture {lecture_num}"
        heading_match = re.search(r'^#{1,3}\s+(.+)', content, re.MULTILINE)
        if heading_match:
            first_heading = f"Lecture {lecture_num}: {heading_match.group(1).strip()}"
        
        elements.append(Paragraph(
            f"<font color='#4361ee'><b>{first_heading}</b></font>",
            styles['BulletPoint']
        ))
    
    elements.append(PageBreak())

    # ── Lecture Content ──
    for entry in data:
        lecture_num = entry.get('lecture', '?')
        content = entry.get(content_key, '')
        
        if not content or content.startswith('[') and 'failed' in content.lower():
            continue

        # Lecture header
        elements.append(Paragraph(f"Lecture {lecture_num}", styles['LectureHeading']))
        elements.append(HRFlowable(width="100%", thickness=2, color=ACCENT))
        elements.append(Spacer(1, 8))

        # Convert content to flowables
        if is_handout:
            # Structured handout — parse markdown
            content_flowables = _markdown_to_flowables(content, styles)
            elements.extend(content_flowables)
        else:
            # Raw transcript — just wrap in paragraphs
            paragraphs = content.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    cleaned = _clean_markdown_inline(para)
                    elements.append(Paragraph(cleaned, styles['BodyText_Handout']))

        elements.append(Spacer(1, 12))
        elements.append(PageBreak())

    # Build PDF with headers/footers
    doc.build(
        elements,
        onFirstPage=lambda c, d: _add_header_footer(c, d, doc_title),
        onLaterPages=lambda c, d: _add_header_footer(c, d, doc_title),
    )

    return output_path
