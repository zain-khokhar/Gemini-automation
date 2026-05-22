"""
PDF Generator Module
Converts JSON (MCQs/Short Notes) into clean, professionally formatted PDFs.
Design: White background, dark navy text, minimal premium styling.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# Colors
NAVY = HexColor('#1a1a2e')
DARK_TEXT = HexColor('#16213e')
MEDIUM_TEXT = HexColor('#2d3748')
LIGHT_GRAY = HexColor('#e2e8f0')
ACCENT_BLUE = HexColor('#4361ee')
CORRECT_GREEN = HexColor('#0f5132')
CORRECT_BG = HexColor('#d1e7dd')
WHITE = HexColor('#ffffff')


def _get_styles():
    """Create custom paragraph styles for the PDF"""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='DocTitle',
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=4*mm,
        leading=22
    ))
    
    # Subtitle
    styles.add(ParagraphStyle(
        name='DocSubtitle',
        fontName='Helvetica',
        fontSize=10,
        textColor=MEDIUM_TEXT,
        alignment=TA_CENTER,
        spaceAfter=8*mm,
        leading=14
    ))
    
    # Section header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=NAVY,
        spaceBefore=6*mm,
        spaceAfter=4*mm,
        leading=16
    ))
    
    # Question number + text
    styles.add(ParagraphStyle(
        name='Question',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=DARK_TEXT,
        spaceBefore=5*mm,
        spaceAfter=2*mm,
        leading=14
    ))
    
    # Option text
    styles.add(ParagraphStyle(
        name='Option',
        fontName='Helvetica',
        fontSize=9.5,
        textColor=MEDIUM_TEXT,
        leftIndent=8*mm,
        spaceAfter=1*mm,
        leading=13
    ))
    
    # Correct answer highlight
    styles.add(ParagraphStyle(
        name='CorrectOption',
        fontName='Helvetica-Bold',
        fontSize=9.5,
        textColor=CORRECT_GREEN,
        leftIndent=8*mm,
        spaceAfter=1*mm,
        leading=13
    ))
    
    # Explanation text
    styles.add(ParagraphStyle(
        name='Explanation',
        fontName='Helvetica-Oblique',
        fontSize=9,
        textColor=MEDIUM_TEXT,
        leftIndent=8*mm,
        spaceBefore=2*mm,
        spaceAfter=3*mm,
        leading=12
    ))
    
    # Short note question
    styles.add(ParagraphStyle(
        name='NoteQuestion',
        fontName='Helvetica-Bold',
        fontSize=10.5,
        textColor=NAVY,
        spaceBefore=5*mm,
        spaceAfter=2*mm,
        leading=14
    ))
    
    # Short note answer
    styles.add(ParagraphStyle(
        name='NoteAnswer',
        fontName='Helvetica',
        fontSize=9.5,
        textColor=DARK_TEXT,
        leftIndent=4*mm,
        spaceAfter=4*mm,
        leading=13,
        alignment=TA_JUSTIFY
    ))
    
    # Footer
    styles.add(ParagraphStyle(
        name='Footer',
        fontName='Helvetica',
        fontSize=8,
        textColor=MEDIUM_TEXT,
        alignment=TA_CENTER
    ))
    
    return styles


def _add_header_footer(canvas, doc, title_text=""):
    """Add header line and footer to each page"""
    canvas.saveState()
    
    # Header line
    canvas.setStrokeColor(NAVY)
    canvas.setLineWidth(0.5)
    canvas.line(20*mm, A4[1] - 15*mm, A4[0] - 20*mm, A4[1] - 15*mm)
    
    # Footer
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(MEDIUM_TEXT)
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(A4[0] / 2, 12*mm, f"— {page_num} —")
    
    # Bottom line
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.setLineWidth(0.3)
    canvas.line(20*mm, 18*mm, A4[0] - 20*mm, 18*mm)
    
    canvas.restoreState()


def generate_mcq_pdf(json_path: str, output_path: str = None, title: str = None) -> str:
    """
    Generate a PDF from an MCQ JSON file.
    
    Args:
        json_path: Path to the JSON file containing MCQs
        output_path: Optional output PDF path. If None, saves next to JSON file.
        title: Optional title for the PDF header
    
    Returns:
        Path to the generated PDF file
    """
    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        mcqs = json.load(f)
    
    if not mcqs or not isinstance(mcqs, list):
        raise ValueError("JSON file is empty or not a valid MCQ list")
    
    # Determine output path
    json_file = Path(json_path)
    if output_path is None:
        output_path = str(json_file.with_suffix('.pdf'))
    
    # Determine title
    if title is None:
        title = json_file.stem.replace('_', ' ').title()
    
    # Create PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=25*mm,
        leftMargin=20*mm,
        rightMargin=20*mm
    )
    
    styles = _get_styles()
    story = []
    
    # Title
    story.append(Paragraph(title, styles['DocTitle']))
    story.append(Paragraph(f"{len(mcqs)} Multiple Choice Questions", styles['DocSubtitle']))
    
    # Separator
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=NAVY,
        spaceAfter=5*mm, spaceBefore=2*mm
    ))
    
    # MCQs
    option_labels = ['A', 'B', 'C', 'D']
    
    for mcq in mcqs:
        q_id = mcq.get('id', '?')
        question = mcq.get('question', 'No question text')
        options = mcq.get('options', [])
        correct = mcq.get('correct', '')
        explanation = mcq.get('explanation', '')
        
        # Question
        story.append(Paragraph(
            f"Q{q_id}. {_escape(question)}",
            styles['Question']
        ))
        
        # Options
        for i, opt in enumerate(options):
            label = option_labels[i] if i < len(option_labels) else str(i+1)
            opt_text = str(opt)
            
            if opt_text.strip() == str(correct).strip():
                story.append(Paragraph(
                    f"{label}) {_escape(opt_text)}  ✓",
                    styles['CorrectOption']
                ))
            else:
                story.append(Paragraph(
                    f"{label}) {_escape(opt_text)}",
                    styles['Option']
                ))
        
        # Explanation
        if explanation:
            story.append(Paragraph(
                f"💡 {_escape(explanation)}",
                styles['Explanation']
            ))
        
        # Light separator between questions
        story.append(HRFlowable(
            width="90%", thickness=0.2, color=LIGHT_GRAY,
            spaceAfter=2*mm, spaceBefore=2*mm
        ))
    
    # Build PDF
    doc.build(story, onFirstPage=_add_header_footer, onLaterPages=_add_header_footer)
    
    print(f"✓ PDF generated: {output_path}")
    return output_path


def generate_short_notes_pdf(json_path: str, output_path: str = None, title: str = None) -> str:
    """
    Generate a PDF from a Short Notes JSON file.
    
    Args:
        json_path: Path to the JSON file containing short notes
        output_path: Optional output PDF path
        title: Optional title for the PDF header
    
    Returns:
        Path to the generated PDF file
    """
    # Load JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        notes = json.load(f)
    
    if not notes or not isinstance(notes, list):
        raise ValueError("JSON file is empty or not a valid notes list")
    
    # Determine output path
    json_file = Path(json_path)
    if output_path is None:
        output_path = str(json_file.with_suffix('.pdf'))
    
    # Determine title
    if title is None:
        title = json_file.stem.replace('_', ' ').title()
    
    # Create PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=20*mm,
        bottomMargin=25*mm,
        leftMargin=20*mm,
        rightMargin=20*mm
    )
    
    styles = _get_styles()
    story = []
    
    # Title
    story.append(Paragraph(title, styles['DocTitle']))
    story.append(Paragraph(f"{len(notes)} Short Notes", styles['DocSubtitle']))
    
    # Separator
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=NAVY,
        spaceAfter=5*mm, spaceBefore=2*mm
    ))
    
    # Notes
    for i, note in enumerate(notes, 1):
        q_id = note.get('id', i)
        question = note.get('question', 'No question')
        answer = note.get('answer', 'No answer')
        
        # Question
        story.append(Paragraph(
            f"{q_id}. {_escape(question)}",
            styles['NoteQuestion']
        ))
        
        # Answer
        story.append(Paragraph(
            _escape(answer),
            styles['NoteAnswer']
        ))
        
        # Separator
        story.append(HRFlowable(
            width="90%", thickness=0.2, color=LIGHT_GRAY,
            spaceAfter=2*mm, spaceBefore=1*mm
        ))
    
    # Build PDF
    doc.build(story, onFirstPage=_add_header_footer, onLaterPages=_add_header_footer)
    
    print(f"✓ PDF generated: {output_path}")
    return output_path


def generate_pdf_from_json(json_path: str, output_path: str = None) -> str:
    """
    Auto-detect content type and generate appropriate PDF.
    
    Args:
        json_path: Path to the JSON file
        output_path: Optional output path
    
    Returns:
        Path to the generated PDF
    """
    # Load and inspect the JSON
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data or not isinstance(data, list):
        raise ValueError("Invalid JSON file")
    
    # Detect type: MCQs have 'options', short notes have 'answer'
    first_item = data[0]
    
    if 'options' in first_item:
        return generate_mcq_pdf(json_path, output_path)
    elif 'answer' in first_item:
        return generate_short_notes_pdf(json_path, output_path)
    else:
        raise ValueError("Cannot determine content type from JSON structure")


def _escape(text: str) -> str:
    """Escape special XML/HTML characters for ReportLab paragraphs"""
    if not text:
        return ""
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def scan_json_files(root_path: str) -> List[Dict[str, str]]:
    """
    Scan a directory recursively for MCQ/Short Notes JSON files ONLY.
    
    IMPORTANT: This function EXCLUDES review files (reviews_*.json, reviews.json)
    from the scan results. Reviews have their own dedicated storage and should
    NEVER appear in the PDF generation list.
    
    Args:
        root_path: Root directory to scan
    
    Returns:
        List of dicts with 'path', 'name', 'category', 'type' keys
    """
    results = []
    root = Path(root_path)
    
    if not root.exists():
        return results
    
    for json_file in root.rglob('*.json'):
        name = json_file.stem
        filename_lower = json_file.name.lower()
        
        # ─── EXCLUSION: Skip review files ───────────────────────
        # Review files use patterns: reviews.json, reviews_mids.json, reviews_finals.json, etc.
        # These should NEVER be included in PDF generation search results.
        if filename_lower.startswith('reviews'):
            continue
        
        # Determine type from filename
        if 'short note' in name.lower() or 'short_note' in name.lower():
            content_type = 'Short Notes'
        elif 'mcq' in name.lower():
            content_type = 'MCQs'
        else:
            # Skip unknown JSON files that are not MCQs or Short Notes
            # This prevents config files, state files, etc. from appearing
            content_type = 'Unknown'
        
        # Category from parent folders
        relative = json_file.relative_to(root)
        parts = list(relative.parts)
        category = parts[0] if len(parts) > 1 else 'Root'
        
        results.append({
            'path': str(json_file),
            'name': json_file.name,
            'category': category,
            'type': content_type,
            'size': json_file.stat().st_size
        })
    
    return sorted(results, key=lambda x: (x['category'], x['name']))
