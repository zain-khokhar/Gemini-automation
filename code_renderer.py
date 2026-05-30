"""
Code Block Renderer Module
Renders code blocks into clean, dark-themed, monospaced blocks for PDF embedding.

This module handles code content from CS/IT/BIT subjects, parsing triple-backtick
code blocks from JSON text and rendering them as properly formatted, dark-themed
code blocks using ReportLab Table flowables.

Features:
- Dark background with monospaced font (Courier)
- Language label display
- Line numbers (optional)
- Proper line wrapping within available width
- Mixed content support (text + code + text)
"""

import re
from typing import List, Tuple, Optional

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Preformatted
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT

# Subject prefixes that need code rendering
CS_SUBJECT_PREFIXES = {'CS', 'IT', 'BIT'}

# Pre-compiled regex for code blocks: ```language\ncode\n```
CODE_BLOCK_RE = re.compile(
    r'```(\w*)\s*\n(.*?)```',
    re.DOTALL
)

# Also match inline code: `code`
INLINE_CODE_RE = re.compile(r'`([^`]+)`')

# ── Dark Theme Colors ──
CODE_BG_COLOR = HexColor('#1e1e2e')        # Dark background (Catppuccin Mocha)
CODE_BORDER_COLOR = HexColor('#313244')     # Subtle border
CODE_TEXT_COLOR = HexColor('#cdd6f4')       # Light text
CODE_LANG_BG = HexColor('#45475a')          # Language label background
CODE_LANG_TEXT = HexColor('#a6e3a1')        # Language label text (green)
CODE_LINE_NUM_COLOR = HexColor('#585b70')   # Line number color (dimmed)
CODE_COMMENT_COLOR = HexColor('#6c7086')    # Comment color


def is_cs_subject(subject_prefix: str) -> bool:
    """Check if a subject prefix indicates a CS subject."""
    if not subject_prefix:
        return False
    return subject_prefix.upper() in CS_SUBJECT_PREFIXES


def _escape_xml(text: str) -> str:
    """Escape text for ReportLab XML/Paragraph."""
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _get_code_style(font_size: float = 8) -> ParagraphStyle:
    """Get the paragraph style for code text."""
    return ParagraphStyle(
        'CodeBlock',
        fontName='Courier',
        fontSize=font_size,
        textColor=CODE_TEXT_COLOR,
        leading=font_size + 4,
        alignment=TA_LEFT,
        wordWrap='CJK',  # Allow breaking at any character for long lines
    )


def _get_lang_label_style(font_size: float = 7) -> ParagraphStyle:
    """Get the paragraph style for the language label."""
    return ParagraphStyle(
        'CodeLangLabel',
        fontName='Courier-Bold',
        fontSize=font_size,
        textColor=CODE_LANG_TEXT,
        leading=font_size + 3,
        alignment=TA_LEFT,
    )


def _get_line_num_style(font_size: float = 7) -> ParagraphStyle:
    """Get the paragraph style for line numbers."""
    return ParagraphStyle(
        'CodeLineNum',
        fontName='Courier',
        fontSize=font_size,
        textColor=CODE_LINE_NUM_COLOR,
        leading=font_size + 4,
        alignment=TA_LEFT,
    )


def render_code_block(code_str: str, language: str = '',
                      available_width: float = 450,
                      show_line_numbers: bool = True,
                      font_size: float = 8) -> Table:
    """
    Render a code block as a dark-themed ReportLab Table flowable.
    
    Args:
        code_str: The code string (may contain newlines)
        language: Programming language (e.g., 'python', 'cpp', 'java')
        available_width: Available width in points
        show_line_numbers: Whether to show line numbers
        font_size: Font size for code text
    
    Returns:
        ReportLab Table flowable styled as a dark code block
    """
    code_style = _get_code_style(font_size)
    lang_style = _get_lang_label_style(font_size - 1)
    line_num_style = _get_line_num_style(font_size - 1)
    
    # Clean up the code
    code_str = code_str.rstrip()
    lines = code_str.split('\n')
    
    # Build the table data
    table_data = []
    
    # Language label row (if language specified)
    if language:
        lang_label = Paragraph(f"  {_escape_xml(language.upper())}", lang_style)
        if show_line_numbers:
            table_data.append(['', lang_label])
        else:
            table_data.append([lang_label])
    
    # Code lines
    for i, line in enumerate(lines, 1):
        # Escape and preserve spaces
        escaped_line = _escape_xml(line) if line.strip() else '&nbsp;'
        # Replace leading spaces with non-breaking spaces for indentation
        leading_spaces = len(line) - len(line.lstrip())
        if leading_spaces > 0:
            escaped_line = '&nbsp;' * leading_spaces + _escape_xml(line.lstrip())
        
        code_para = Paragraph(escaped_line, code_style)
        
        if show_line_numbers:
            line_num = Paragraph(f"{i:3d}", line_num_style)
            table_data.append([line_num, code_para])
        else:
            table_data.append([code_para])
    
    # Calculate column widths
    if show_line_numbers:
        line_num_width = 30  # Fixed width for line numbers
        code_width = available_width - line_num_width - 16  # 16 for padding
        col_widths = [line_num_width, code_width]
    else:
        col_widths = [available_width - 16]
    
    # Create the table
    code_table = Table(table_data, colWidths=col_widths)
    
    # Style the table
    style_cmds = [
        # Background
        ('BACKGROUND', (0, 0), (-1, -1), CODE_BG_COLOR),
        # Border
        ('BOX', (0, 0), (-1, -1), 1, CODE_BORDER_COLOR),
        # Alignment
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]
    
    # Language label row styling
    if language:
        style_cmds.extend([
            ('BACKGROUND', (0, 0), (-1, 0), CODE_LANG_BG),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ])
        if show_line_numbers:
            style_cmds.append(('SPAN', (0, 0), (1, 0)))  # Span lang label across both columns
    
    # Line number column styling
    if show_line_numbers:
        start_row = 1 if language else 0
        style_cmds.extend([
            ('RIGHTPADDING', (0, start_row), (0, -1), 4),
            ('LEFTPADDING', (0, start_row), (0, -1), 6),
            # Separator line between line numbers and code
            ('LINEAFTER', (0, start_row), (0, -1), 0.5, CODE_LINE_NUM_COLOR),
        ])
    
    # Rounded corners effect (outer padding)
    style_cmds.extend([
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
    ])
    
    code_table.setStyle(TableStyle(style_cmds))
    
    return code_table


def parse_code_blocks(text: str) -> List[Tuple[str, any]]:
    """
    Parse text into segments of plain text and code blocks.
    
    Returns:
        List of tuples: [('text', str), ('code', {'lang': str, 'code': str}), ...]
    """
    segments = []
    last_end = 0
    
    for match in CODE_BLOCK_RE.finditer(text):
        # Text before code block
        before = text[last_end:match.start()].strip()
        if before:
            segments.append(('text', before))
        
        language = match.group(1).strip().lower() if match.group(1) else ''
        code_content = match.group(2)
        
        # Remove leading/trailing blank lines from code
        code_lines = code_content.split('\n')
        while code_lines and not code_lines[0].strip():
            code_lines.pop(0)
        while code_lines and not code_lines[-1].strip():
            code_lines.pop()
        
        segments.append(('code', {
            'lang': language,
            'code': '\n'.join(code_lines)
        }))
        last_end = match.end()
    
    # Remaining text
    remaining = text[last_end:].strip()
    if remaining:
        segments.append(('text', remaining))
    
    return segments


def _render_inline_code(text: str, style) -> str:
    """
    Replace inline code (`code`) with styled ReportLab markup.
    Returns the text with inline code styled using <font> tags.
    """
    def replace_inline(match):
        code = _escape_xml(match.group(1))
        return f'<font face="Courier" color="#e74c3c"><b>{code}</b></font>'
    
    return INLINE_CODE_RE.sub(replace_inline, _escape_xml(text))


def render_mixed_content_with_code(text: str, style, available_width: float = 450) -> list:
    """
    Parse text containing both plain text and code blocks, and return
    a list of ReportLab flowables.
    
    Args:
        text: Raw text potentially containing ```code``` blocks
        style: ReportLab ParagraphStyle for plain text
        available_width: Available width in points
    
    Returns:
        List of ReportLab flowables
    """
    if not text or not text.strip():
        return [Paragraph(_escape_xml(text or ''), style)]
    
    # Check if text contains any code blocks
    if '```' not in text and '`' not in text:
        return [Paragraph(_escape_xml(text), style)]
    
    # If no triple backtick blocks but has inline code, handle inline only
    if '```' not in text:
        styled_text = _render_inline_code(text, style)
        return [Paragraph(styled_text, style)]
    
    flowables = []
    segments = parse_code_blocks(text)
    
    for seg_type, seg_content in segments:
        if seg_type == 'code':
            # Add spacing before code block
            flowables.append(Spacer(1, 2 * mm))
            
            code_block = render_code_block(
                seg_content['code'],
                language=seg_content['lang'],
                available_width=available_width,
                show_line_numbers=True
            )
            flowables.append(code_block)
            
            # Add spacing after code block
            flowables.append(Spacer(1, 2 * mm))
            
        elif seg_type == 'text':
            # Handle inline code within text segments
            styled_text = _render_inline_code(seg_content, style)
            flowables.append(Paragraph(styled_text, style))
    
    if not flowables:
        flowables.append(Paragraph(_escape_xml(text), style))
    
    return flowables
