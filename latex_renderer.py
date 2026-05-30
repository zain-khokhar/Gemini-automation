"""
LaTeX Renderer Module
Converts LaTeX expressions to images for PDF embedding using matplotlib.

This module handles math content from MTH/STA/PHY subjects, rendering
LaTeX expressions ($...$, $$...$$) into clean PNG images that can be
embedded into ReportLab PDFs as Image flowables.

No external TeX installation is required — uses matplotlib's built-in mathtext.
"""

import os
import re
import tempfile
import hashlib
from typing import List, Tuple, Optional

from reportlab.platypus import Paragraph, Image, Spacer, Table, TableStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# Subject prefixes that require LaTeX rendering
MATH_SUBJECT_PREFIXES = {'MTH', 'STA', 'PHY'}

# Pre-compiled regex patterns
# Match $$...$$ (block/display math) FIRST, then $...$ (inline math)
# Use negative lookbehind (?<!\\) to ignore escaped dollar signs like \$
BLOCK_LATEX_RE = re.compile(r'(?<!\\)\$\$(.+?)(?<!\\)\$\$', re.DOTALL)
INLINE_LATEX_RE = re.compile(r'(?<!\\)\$(.+?)(?<!\\)\$', re.DOTALL)
# Combined pattern that matches both (block first to avoid partial matches)
ALL_LATEX_RE = re.compile(r'((?<!\\)\$\$(.+?)(?<!\\)\$\$|(?<!\\)\$(.+?)(?<!\\)\$)', re.DOTALL)

# Temp directory for rendered images
_TEMP_DIR = None
_RENDERED_CACHE = {}


def _get_temp_dir():
    """Get or create the temp directory for LaTeX images."""
    global _TEMP_DIR
    if _TEMP_DIR is None or not os.path.exists(_TEMP_DIR):
        _TEMP_DIR = tempfile.mkdtemp(prefix='vuedu_latex_')
    return _TEMP_DIR


def is_math_subject(subject_prefix: str) -> bool:
    """Check if a subject prefix indicates a math/science subject."""
    if not subject_prefix:
        return False
    return subject_prefix.upper() in MATH_SUBJECT_PREFIXES


def render_latex_to_image(latex_str: str, font_size: int = 14, dpi: int = 200,
                          is_block: bool = False) -> Optional[str]:
    """
    Render a LaTeX expression to a PNG image using matplotlib.
    
    Args:
        latex_str: Raw LaTeX string (without $ delimiters)
        font_size: Font size for rendering
        dpi: Resolution of the output image
        is_block: If True, render as display/block math (larger, centered)
    
    Returns:
        Path to the rendered PNG file, or None on failure
    """
    # Check cache first
    cache_key = hashlib.md5(f"{latex_str}_{font_size}_{dpi}_{is_block}".encode()).hexdigest()
    if cache_key in _RENDERED_CACHE and os.path.exists(_RENDERED_CACHE[cache_key]):
        return _RENDERED_CACHE[cache_key]
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt
        
        # Clean the LaTeX string
        cleaned = latex_str.strip()
        if not cleaned:
            return None
        
        # Ensure it's wrapped in $ for matplotlib
        if not cleaned.startswith('$'):
            cleaned = f'${cleaned}$'
        
        # Create figure with transparent background
        actual_font_size = font_size * 1.3 if is_block else font_size
        
        fig = plt.figure(figsize=(0.01, 0.01))
        fig.patch.set_alpha(0.0)
        
        # Render the text
        text_obj = fig.text(0, 0, cleaned,
                           fontsize=actual_font_size,
                           color='#1e293b',  # Dark text color matching PDF theme
                           ha='left', va='baseline',
                           usetex=False)  # Use mathtext, not full TeX
        
        # Get the rendered size
        renderer = fig.canvas.get_renderer()
        bbox = text_obj.get_window_extent(renderer)
        
        # Add padding
        pad_x = 6
        pad_y = 4
        fig.set_size_inches(
            (bbox.width + 2 * pad_x) / dpi,
            (bbox.height + 2 * pad_y) / dpi
        )
        text_obj.set_position((pad_x / (bbox.width + 2 * pad_x),
                               pad_y / (bbox.height + 2 * pad_y)))
        
        # Save to temp file
        output_path = os.path.join(_get_temp_dir(), f"latex_{cache_key}.png")
        fig.savefig(output_path, dpi=dpi, transparent=True,
                    bbox_inches='tight', pad_inches=0.02)
        plt.close(fig)
        
        _RENDERED_CACHE[cache_key] = output_path
        return output_path
        
    except Exception as e:
        print(f"[LaTeXRenderer] Failed to render: {e}")
        try:
            plt.close('all')
        except:
            pass
        return None


def _escape_xml(text: str) -> str:
    """Escape text for ReportLab XML/Paragraph."""
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _preprocess_latex(latex_str: str) -> str:
    """Preprocess LaTeX to fix commands unsupported by matplotlib mathtext."""
    # Common replacements using regex for word boundaries and flexible spacing
    latex_str = re.sub(r'\\ge\b', r'\\geq', latex_str)
    latex_str = re.sub(r'\\le\b', r'\\leq', latex_str)
    latex_str = re.sub(r'\\text\s*\{', r'\\mathrm{', latex_str)
    
    # Attempt to flatten \begin{cases} ... \end{cases} into a readable set notation \{ ... \}
    def replace_cases(match):
        content = match.group(1)
        # Clean up alignment ampersands and replace line breaks with commas
        content = content.replace('&', ' ')
        content = content.replace('\\\\', ', ')
        # mathtext requires spaces around commas and braces sometimes
        return r'\{ ' + content.strip() + r' \}'
    
    latex_str = re.sub(r'\\begin\s*\{\s*cases\s*\}(.*?)\\end\s*\{\s*cases\s*\}', replace_cases, latex_str, flags=re.DOTALL)
    return latex_str

def parse_and_render_mixed_content(text: str, style, font_size: int = 10,
                                    available_width: float = 450, prefix_text: str = '') -> list:
    """
    Parse text containing mixed LaTeX and plain text, and return a list
    of ReportLab flowables.
    
    Block math ($$...$$) is rendered as a centered Table with an Image.
    Inline math ($...$) is rendered to images and embedded directly inside 
    a single Paragraph using the HTML <img> tag for perfect alignment.
    """
    if not text or not text.strip():
        full_text = f"{_escape_xml(prefix_text)}{_escape_xml(text or '')}"
        return [Paragraph(full_text, style)]
    
    if '$' not in text:
        full_text = f"{_escape_xml(prefix_text)}{_escape_xml(text)}"
        return [Paragraph(full_text, style)]
    
    flowables = []
    
    # Split by block math first ($$...$$)
    segments = _split_into_segments(text)
    
    is_first_segment = True
    
    for seg_type, seg_content in segments:
        if seg_type == 'block_math':
            # Preprocess and render block math
            clean_math = _preprocess_latex(seg_content)
            img_path = render_latex_to_image(clean_math, font_size=font_size + 4,
                                             dpi=200, is_block=True)
            
            if is_first_segment and prefix_text:
                flowables.append(Paragraph(_escape_xml(prefix_text), style))
                is_first_segment = False

            if img_path and os.path.exists(img_path):
                img = Image(img_path)
                # Scale to fit within available width
                iw, ih = img.imageWidth, img.imageHeight
                if iw > available_width * 0.85:
                    scale = (available_width * 0.85) / iw
                    img.drawWidth = iw * scale
                    img.drawHeight = ih * scale
                else:
                    img.drawWidth = iw * 0.5  # Scale down for better PDF size
                    img.drawHeight = ih * 0.5
                
                # Center the block math in a table
                centered = Table([[img]], colWidths=[available_width])
                centered.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ]))
                flowables.append(centered)
            else:
                # Fallback: render as escaped text
                flowables.append(Paragraph(_escape_xml(f"$${seg_content}$$"), style))
                
        elif seg_type == 'text':
            # Process inline math within text segments using HTML <img> tags
            html_text = _render_inline_math_html(seg_content, font_size, available_width)
            
            if is_first_segment and prefix_text:
                html_text = _escape_xml(prefix_text) + html_text
                is_first_segment = False
                
            if html_text.strip():
                flowables.append(Paragraph(html_text, style))
    
    return flowables

def _split_into_segments(text: str) -> List[Tuple[str, str]]:
    segments = []
    last_end = 0
    for match in BLOCK_LATEX_RE.finditer(text):
        before = text[last_end:match.start()].strip()
        if before:
            segments.append(('text', before))
        segments.append(('block_math', match.group(1).strip()))
        last_end = match.end()
    
    remaining = text[last_end:].strip()
    if remaining:
        segments.append(('text', remaining))
    return segments

def _render_inline_math_html(text: str, font_size: int, available_width: float) -> str:
    """
    Parses inline math and returns an HTML-like string valid for ReportLab Paragraphs,
    with <img> tags embedding the rendered math images inline.
    """
    if '$' not in text:
        return _escape_xml(text)
    
    result_html = ""
    last_end = 0
    
    for match in INLINE_LATEX_RE.finditer(text):
        # Escaped plain text before the math
        before = text[last_end:match.start()]
        if before:
            result_html += _escape_xml(before)
        
        latex_content = match.group(1).strip()
        clean_math = _preprocess_latex(latex_content)
        img_path = render_latex_to_image(clean_math, font_size=font_size, dpi=200, is_block=False)
        
        if img_path and os.path.exists(img_path):
            from reportlab.platypus import Image
            img = Image(img_path)
            iw, ih = img.imageWidth, img.imageHeight
            
            # Scale inline images to match their true rendered point size
            # Since matplotlib renders at 200 DPI, we convert pixels back to points (72 DPI)
            scale = 72.0 / 200.0
            
            max_width = available_width * 0.85
            if iw * scale > max_width:
                scale = max_width / iw
                
            final_w = iw * scale
            final_h = ih * scale
            
            # Use negative valign to align the image baseline with text
            # Matplotlib adds some padding, so we adjust baseline accordingly
            valign = -(final_h * 0.3)
            
            # Make sure to use forward slashes for the path in ReportLab XML
            safe_path = img_path.replace('\\', '/')
            result_html += f'<img src="{safe_path}" width="{final_w}" height="{final_h}" valign="{valign}"/>'
        else:
            # Fallback: just show the math as text
            result_html += f" <i>[{_escape_xml(latex_content)}]</i> "
        
        last_end = match.end()
    
    remaining = text[last_end:]
    if remaining:
        result_html += _escape_xml(remaining)
    
    return result_html


def cleanup_temp_files():
    """Clean up all temporary LaTeX image files."""
    global _RENDERED_CACHE, _TEMP_DIR
    import shutil
    
    _RENDERED_CACHE.clear()
    
    if _TEMP_DIR and os.path.exists(_TEMP_DIR):
        try:
            shutil.rmtree(_TEMP_DIR)
            print(f"[LaTeXRenderer] Cleaned up temp dir: {_TEMP_DIR}")
        except Exception as e:
            print(f"[LaTeXRenderer] Cleanup failed: {e}")
        _TEMP_DIR = None
