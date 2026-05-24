"""
PDF Generator Module
Converts JSON (MCQs/Short Notes) into clean, professionally formatted PDFs.
Updated to use the advanced pdf_editor_settings.json for first/last pages,
per-type header/footer, and full layout customization.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from pdf_settings import PDFSettingsManager

# Register custom fonts
try:
    _font_dir = os.path.join(os.path.dirname(__file__), 'assets', 'fonts')
    if os.path.exists(os.path.join(_font_dir, 'GoogleSansFlex_24pt-Regular.ttf')):
        pdfmetrics.registerFont(TTFont('Google Sans Flex', os.path.join(_font_dir, 'GoogleSansFlex_24pt-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('Google Sans Flex-Bold', os.path.join(_font_dir, 'GoogleSansFlex_24pt-Bold.ttf')))
        pdfmetrics.registerFont(TTFont('Google Sans Flex-Medium', os.path.join(_font_dir, 'GoogleSansFlex_24pt-Medium.ttf')))
except Exception as e:
    print(f"[PDFGen] Could not register Google Sans Flex fonts: {e}")


def _font_name_from_path(font_path):
    stem = Path(font_path).stem
    for sep in ('-', '_'):
        if sep in stem:
            base, style = stem.rsplit(sep, 1)
            style = style.lower()
            if style in ('regular', 'roman'):
                return base
            if style == 'bold':
                return f"{base}-Bold"
            if style in ('italic', 'oblique'):
                return f"{base}-Italic"
            if style in ('bolditalic', 'bold_italic', 'bolditalic'):
                return f"{base}-BoldItalic"
    return stem


def _register_downloaded_fonts():
    download_dir = r"C:\Users\zaink\Downloads\nebula"
    if not os.path.isdir(download_dir):
        return
    for font_file in sorted(os.listdir(download_dir)):
        if not font_file.lower().endswith(('.ttf', '.otf')):
            continue
        font_path = os.path.join(download_dir, font_file)
        if not os.path.isfile(font_path):
            continue
        font_name = _font_name_from_path(font_path)
        if font_name in pdfmetrics.getRegisteredFontNames():
            continue
        try:
            pdfmetrics.registerFont(TTFont(font_name, font_path))
        except Exception as e:
            print(f"[PDFGen] Could not register downloaded font '{font_file}': {e}")


_register_downloaded_fonts()
# ─────────────────────────────────────────────────────────────
#  Color Palette (based on provided template images)
# ─────────────────────────────────────────────────────────────
PRIMARY_BLUE = HexColor('#1642a8')
TEXT_GRAY = HexColor('#374151')
HIGHLIGHT_YELLOW = HexColor('#fef08a')
EXP_BG_BLUE = HexColor('#eff6ff')
EXP_BORDER = HexColor('#bfdbfe')
LIGHT_GRAY = HexColor('#e5e7eb')

# Legacy settings manager (for backward compat)
pdf_config = PDFSettingsManager()


_EDITOR_SETTINGS_OVERRIDE = None

def _load_editor_settings():
    if _EDITOR_SETTINGS_OVERRIDE is not None:
        return _EDITOR_SETTINGS_OVERRIDE
    """Load the advanced pdf_editor_settings.json if available, else return None."""
    try:
        settings_path = "pdf_editor_settings.json"
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('version', 1) >= 2:
                return data
    except Exception as e:
        print(f"[PDFGen] Could not load editor settings: {e}")
    return None


def _draw_image_or_svg(canvas, path, x, y, width, height, preserveAspectRatio=True):
    if not path or not os.path.exists(path):
        return
    if path.lower().endswith('.svg'):
        try:
            from svglib.svglib import svg2rlg
            from reportlab.graphics import renderPDF
            drawing = svg2rlg(path)
            if drawing:
                scale_x = width / drawing.width
                scale_y = height / drawing.height
                if preserveAspectRatio:
                    scale = min(scale_x, scale_y)
                    scale_x = scale
                    scale_y = scale
                    x += (width - drawing.width * scale) / 2
                    y += (height - drawing.height * scale) / 2
                drawing.width, drawing.height = drawing.width * scale_x, drawing.height * scale_y
                drawing.scale(scale_x, scale_y)
                renderPDF.draw(drawing, canvas, x, y)
        except Exception as e:
            print(f"[PDFGen] Failed to render SVG {path}: {e}")
    else:
        canvas.drawImage(path, x, y, width=width, height=height, preserveAspectRatio=preserveAspectRatio)


def _hex_to_color(hex_str, fallback=None):
    """Safely convert hex color string to reportlab HexColor."""
    try:
        if hex_str and hex_str.startswith('#'):
            return HexColor(hex_str)
    except Exception:
        pass
    return fallback or HexColor('#000000')


def _resolve_font(font_fam, is_bold=False, is_italic=False):
    """Resolve font family to a valid ReportLab font name."""
    from reportlab.pdfbase import pdfmetrics
    
    if is_bold and is_italic:
        test_name = f"{font_fam}-BoldItalic"
    elif is_bold:
        test_name = f"{font_fam}-Bold"
    elif is_italic:
        test_name = f"{font_fam}-Italic"
    else:
        test_name = font_fam
        
    if test_name in pdfmetrics.getRegisteredFontNames():
        return test_name

    _std_fonts = ['Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique', 
                  'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique', 
                  'Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic', 
                  'Symbol', 'ZapfDingbats']
    if test_name in _std_fonts:
        return test_name

    if 'Bold' in test_name and 'Italic' in test_name: return 'Helvetica-BoldOblique'
    elif 'Bold' in test_name: return 'Helvetica-Bold'
    elif 'Italic' in test_name or 'Oblique' in test_name: return 'Helvetica-Oblique'
    return 'Helvetica'

def _get_styles(doc_type="mcq"):
    """Get paragraph styles, reading from editor settings if available."""
    editor = _load_editor_settings()

    if editor and doc_type in editor:
        lay = editor[doc_type].get('body', {}).get('layout', {})
    else:
        settings = pdf_config.load_settings()
        lay = settings.get('layout', {})

    font_fam = lay.get('font_family', 'Helvetica')
    from reportlab.pdfbase import pdfmetrics
    _std_fonts = ['Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique', 
                  'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique', 
                  'Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic', 
                  'Symbol', 'ZapfDingbats']
    if font_fam not in _std_fonts and font_fam not in pdfmetrics.getRegisteredFontNames():
        font_fam = 'Helvetica'
    title_sz = lay.get('title_size', 18)
    title_color = _hex_to_color(lay.get('title_color', '#1642a8'), PRIMARY_BLUE)
    q_sz = lay.get('question_size', 10)
    q_color = _hex_to_color(lay.get('question_color', '#1642a8'), PRIMARY_BLUE)
    opt_sz = lay.get('option_size', 9.5)
    opt_color = _hex_to_color(lay.get('option_color', '#374151'), TEXT_GRAY)
    exp_sz = lay.get('explanation_size', 9)
    exp_text_col = _hex_to_color(lay.get('explanation_text_color', '#1e293b'))

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='DocTitle',
        fontName=_resolve_font(font_fam, is_bold=True),
        fontSize=title_sz,
        textColor=title_color,
        alignment=TA_CENTER,
        spaceAfter=4*mm,
        leading=title_sz + 4
    ))

    styles.add(ParagraphStyle(
        name='DocSubtitle',
        fontName=_resolve_font(font_fam, is_bold=True),
        fontSize=10,
        textColor=PRIMARY_BLUE,
        alignment=TA_CENTER,
        spaceAfter=8*mm,
        leading=14,
        textTransform='uppercase'
    ))

    styles.add(ParagraphStyle(
        name='Question',
        fontName=_resolve_font(font_fam, is_bold=True),
        fontSize=q_sz,
        textColor=q_color,
        spaceBefore=0,
        spaceAfter=3*mm,
        leading=q_sz + 3
    ))

    styles.add(ParagraphStyle(
        name='Option',
        fontName=font_fam,
        fontSize=opt_sz,
        textColor=opt_color,
        leftIndent=lay.get('option_indent', 8)*mm,
        spaceAfter=1*mm,
        leading=opt_sz + 3.5
    ))

    styles.add(ParagraphStyle(
        name='MetaText',
        fontName=font_fam,
        fontSize=8,
        textColor=HexColor('#6b7280'),
        leftIndent=8*mm,
        spaceBefore=2*mm,
        spaceAfter=1*mm
    ))

    styles.add(ParagraphStyle(
        name='Explanation',
        fontName=font_fam,
        fontSize=exp_sz,
        textColor=exp_text_col,
        alignment=TA_CENTER,
        leading=exp_sz + 3
    ))

    styles.add(ParagraphStyle(
        name='ExplanationLabel',
        fontName=f'{font_fam}-Bold' if font_fam == 'Helvetica' else font_fam,
        fontSize=exp_sz,
        textColor=exp_text_col,
        alignment=TA_CENTER,
        spaceAfter=2,
        leading=exp_sz + 3
    ))

    styles.add(ParagraphStyle(
        name='NoteAnswer',
        fontName=font_fam,
        fontSize=opt_sz,
        textColor=opt_color,
        leftIndent=lay.get('answer_indent', 8)*mm,
        spaceAfter=4*mm,
        leading=opt_sz + 4,
        alignment=TA_JUSTIFY
    ))

    return styles


def _create_page_handler(doc_type="mcq"):
    """Create a page handler that draws header/footer and background using editor settings."""
    def _add_header_footer(canvas, doc):
        canvas.saveState()

        editor = _load_editor_settings()
        settings = pdf_config.load_settings()

        # ── Background Template ──
        tpl = settings.get('templates', {})
        if tpl.get('use_templates'):
            bg_path = tpl.get('mcq_bg') if doc_type == "mcq" else tpl.get('notes_bg')
            if bg_path and os.path.exists(bg_path):
                _draw_image_or_svg(canvas, bg_path, 0, 0, width=A4[0], height=A4[1], preserveAspectRatio=False)

        # ── Get header/footer config from editor settings (per doc_type) ──
        if editor and doc_type in editor:
            body = editor[doc_type].get('body', {})
            h_cfg = body.get('header', {})
            f_cfg = body.get('footer', {})
        else:
            h_cfg = settings.get('header', {})
            f_cfg = settings.get('footer', {})

        # ── Header ──
        if h_cfg.get('enabled', True):
            h_text = h_cfg.get('text', '')
            h_url = h_cfg.get('url', '')
            h_color = _hex_to_color(h_cfg.get('color', '#1642a8'))
            h_sz = max(6, int(h_cfg.get('font_size', 8)))
            h_font = h_cfg.get('font_family', 'Helvetica')
            is_bold = 'Bold' in h_font or h_cfg.get('font_weight', '') == 'bold'
            font_name = _resolve_font(h_font.replace('-Bold', ''), is_bold)
            h_align = h_cfg.get('alignment', 'right')
            padding_top = h_cfg.get('padding_top', 8)
            show_line = h_cfg.get('show_line', True)

            if h_text:
                canvas.setFont(font_name, h_sz)
                canvas.setFillColor(h_color)
                y_pos = A4[1] - padding_top * mm
                tw = pdfmetrics.stringWidth(h_text, font_name, h_sz)

                if h_align == 'right':
                    x_pos = A4[0] - 20*mm
                    canvas.drawRightString(x_pos, y_pos, h_text)
                    link_x = x_pos - tw
                elif h_align == 'left':
                    x_pos = 20*mm
                    canvas.drawString(x_pos, y_pos, h_text)
                    link_x = x_pos
                else:
                    x_pos = A4[0] / 2
                    canvas.drawCentredString(x_pos, y_pos, h_text)
                    link_x = x_pos - tw / 2

                if h_url:
                    canvas.linkURL(h_url, (link_x, y_pos - 2, link_x + tw, y_pos + h_sz), relative=1)

            if show_line:
                line_color = _hex_to_color(h_cfg.get('line_color', '#e5e7eb'))
                line_thickness = h_cfg.get('line_thickness', 0.5)
                canvas.setStrokeColor(line_color)
                canvas.setLineWidth(line_thickness)
                line_y = A4[1] - (padding_top + 2) * mm
                canvas.line(20*mm, line_y, A4[0] - 20*mm, line_y)

        # ── Footer ──
        if f_cfg.get('enabled', True):
            f_color = _hex_to_color(f_cfg.get('color', '#6b7280'))
            f_text = f_cfg.get('text', '— {page_num} —').replace('{page_num}', str(canvas.getPageNumber()))
            f_sz = max(6, int(f_cfg.get('font_size', 8)))
            f_font = f_cfg.get('font_family', 'Helvetica')
            is_bold = 'Bold' in f_font or f_cfg.get('font_weight', '') == 'bold'
            font_name_f = _resolve_font(f_font.replace('-Bold', ''), is_bold)
            f_align = f_cfg.get('alignment', 'center')
            padding_bottom = f_cfg.get('padding_bottom', 8)
            show_f_line = f_cfg.get('show_line', True)
            f_url = f_cfg.get('url', '')

            canvas.setFont(font_name_f, f_sz)
            canvas.setFillColor(f_color)
            y_pos = padding_bottom * mm
            tw = pdfmetrics.stringWidth(f_text, font_name_f, f_sz)

            if f_align == 'center':
                canvas.drawCentredString(A4[0] / 2, y_pos, f_text)
                link_x = A4[0] / 2 - tw / 2
            elif f_align == 'left':
                canvas.drawString(20*mm, y_pos, f_text)
                link_x = 20*mm
            else:
                canvas.drawRightString(A4[0] - 20*mm, y_pos, f_text)
                link_x = A4[0] - 20*mm - tw

            if f_url:
                canvas.linkURL(f_url, (link_x, y_pos - 2, link_x + tw, y_pos + f_sz), relative=1)

            if show_f_line:
                line_color = _hex_to_color(f_cfg.get('line_color', '#e5e7eb'))
                line_thickness = f_cfg.get('line_thickness', 0.5)
                canvas.setStrokeColor(line_color)
                canvas.setLineWidth(line_thickness)
                line_y = (padding_bottom + 4) * mm
                canvas.line(20*mm, line_y, A4[0] - 20*mm, line_y)

        canvas.restoreState()

    return _add_header_footer


def _render_promotional_page(canvas, page_config, page_type="first_page"):
    """
    Render a full promotional page (first or last) using the element-based system.
    This is called directly on the canvas for precise positioning.
    """
    if not page_config:
        return

    # Background color
    bg_color = page_config.get('background_color', '#ffffff')
    canvas.setFillColor(_hex_to_color(bg_color))
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)

    # Background image
    bg_path = page_config.get('background_image', '')
    if bg_path and os.path.exists(bg_path):
        bg_opacity = page_config.get('bg_opacity', 1.0)
        canvas.saveState()
        if bg_opacity < 1.0:
            canvas.setFillAlpha(bg_opacity)
        _draw_image_or_svg(canvas, bg_path, 0, 0, width=A4[0], height=A4[1], preserveAspectRatio=False)
        canvas.restoreState()

    # Page Border
    border_thickness = page_config.get('border_thickness', 0.0)
    if border_thickness > 0:
        border_color = page_config.get('border_color', '#000000')
        canvas.setStrokeColor(_hex_to_color(border_color))
        canvas.setLineWidth(border_thickness)
        canvas.rect(border_thickness / 2, border_thickness / 2, A4[0] - border_thickness, A4[1] - border_thickness, fill=0, stroke=1)

    # Render elements
    elements = page_config.get('elements', [])
    for el in elements:
        el_type = el.get('type', 'text')
        opacity = el.get('opacity', 1.0)
        canvas.saveState()

        if opacity < 1.0:
            canvas.setFillAlpha(opacity)
            canvas.setStrokeAlpha(opacity)

        if el_type == 'text':
            _render_text_element(canvas, el)
        elif el_type == 'image':
            _render_image_element(canvas, el)

        canvas.restoreState()


def _render_text_element(canvas, el):
    """Render a text element onto the canvas at exact PDF coordinates."""
    # A4 dimensions: 595 x 842 pts
    # Our data stores x/y in PDF points (origin at top-left)
    x = el.get('x', 297)
    y_from_top = el.get('y', 400)
    w = el.get('width', 300)
    h = el.get('height', 30)
    content = el.get('content', '')
    color_hex = el.get('color', '#1642a8')
    font_sz = max(4, int(el.get('font_size', 14)))
    alignment = el.get('alignment', 'center')
    is_bold = el.get('bold', False)
    is_italic = el.get('italic', False)
    underline = el.get('underline', False)
    hyperlink = el.get('hyperlink', '')
    letter_spacing = el.get('letter_spacing', 0)

    # Convert from top-based to bottom-based (ReportLab uses bottom-left origin)
    y_bottom = A4[1] - y_from_top

    # Build font name
    font_fam = el.get('font_family', 'Helvetica')
    actual_bold = is_bold or 'Bold' in font_fam
    actual_italic = is_italic or 'Oblique' in font_fam or 'Italic' in font_fam
    base_fam = font_fam.replace('-Bold', '').replace('-Oblique', '').replace('-Italic', '')
    font_name = _resolve_font(base_fam, actual_bold, actual_italic)

    canvas.setFont(font_name, font_sz)
    canvas.setFillColor(_hex_to_color(color_hex))

    if letter_spacing:
        canvas._code.append(f'{float(letter_spacing)} Tc')

    # Manual word wrap to match the UI preview
    def get_width(text_str):
        base_w = pdfmetrics.stringWidth(text_str, font_name, font_sz)
        if letter_spacing:
            base_w += max(0, len(text_str) - 1) * letter_spacing
        return base_w

    lines = []
    max_w = w - 8 # Account for the 4px padding on each side used in UI
    
    for block in content.split('\n'):
        current_line = []
        for word in block.split(' '):
            test_line = ' '.join(current_line + [word])
            if get_width(test_line) > max_w and current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        if current_line:
            lines.append(' '.join(current_line))

    line_h_pt = font_sz * el.get('line_height', 1.2)
    start_y = y_bottom + (len(lines) - 1) * line_h_pt / 2.0

    for i, line in enumerate(lines):
        line_y = start_y - i * line_h_pt
        text_w = get_width(line)

        if alignment == 'center':
            canvas.drawString(x - text_w / 2, line_y, line)
            link_x = x - text_w / 2
        elif alignment == 'right':
            canvas.drawString(x + w / 2 - text_w, line_y, line)
            link_x = x + w / 2 - text_w
        else:
            canvas.drawString(x - w / 2, line_y, line)
            link_x = x - w / 2

        # Underline
        if underline:
            canvas.setLineWidth(0.5)
            canvas.line(link_x, line_y - 2, link_x + text_w, line_y - 2)

        # Hyperlink annotation (only on first line if multi-line, or all lines?)
        # Better to add hyperlink to each line individually
        if hyperlink:
            canvas.linkURL(
                hyperlink,
                (link_x, line_y - 2, link_x + text_w, line_y + font_sz),
                relative=1
            )

    if letter_spacing:
        canvas._code.append('0 Tc')


def _render_image_element(canvas, el):
    """Render an image element onto the canvas."""
    path = el.get('path', '')
    if not path or not os.path.exists(path):
        return

    x = el.get('x', 297)
    y_from_top = el.get('y', 200)
    w = el.get('width', 150)
    h = el.get('height', 150)

    # Convert to bottom-left origin; x,y is center point
    draw_x = x - w / 2
    draw_y = A4[1] - y_from_top - h / 2

    _draw_image_or_svg(canvas, path, draw_x, draw_y, width=w, height=h, preserveAspectRatio=True)


class PromoPageManager:
    """Handles first and last promotional pages using editor settings."""

    def __init__(self, doc_type="mcq"):
        self.doc_type = doc_type
        self.editor = _load_editor_settings()
        self._first_page_rendered = False
        self._last_page_config = None

        if self.editor and doc_type in self.editor:
            fp = self.editor[doc_type].get('first_page', {})
            lp = self.editor[doc_type].get('last_page', {})
            self._first_enabled = fp.get('enabled', True)
            self._last_enabled = lp.get('enabled', True)
            self._first_config = fp
            self._last_page_config = lp
        else:
            # Fall back to legacy settings
            leg = pdf_config.load_settings()
            fp = leg.get('first_page', {})
            lp = leg.get('last_page', {})
            self._first_enabled = fp.get('enabled', False)
            self._last_enabled = lp.get('enabled', False)
            self._first_config = fp
            self._last_page_config = lp

    def draw_first_page(self, canvas):
        """Draw the first promotional page on the canvas."""
        if not self._first_enabled:
            return

        editor = self.editor
        if editor and self.doc_type in editor:
            _render_promotional_page(canvas, self._first_config, "first_page")
        else:
            # Legacy rendering
            cfg = self._first_config
            text = cfg.get('content_text', '')
            bg = cfg.get('bg_image', '')
            if bg and os.path.exists(bg):
                _draw_image_or_svg(canvas, bg, 0, 0, width=A4[0], height=A4[1], preserveAspectRatio=False)
            if text:
                canvas.setFont('Helvetica-Bold', 24)
                canvas.setFillColor(PRIMARY_BLUE)
                canvas.drawCentredString(A4[0] / 2, A4[1] / 2, text)

    def draw_last_page(self, canvas):
        """Draw the last promotional page on the canvas."""
        if not self._last_enabled:
            return

        editor = self.editor
        if editor and self.doc_type in editor:
            _render_promotional_page(canvas, self._last_page_config, "last_page")
        else:
            cfg = self._last_page_config
            text = cfg.get('content_text', '')
            bg = cfg.get('bg_image', '')
            if bg and os.path.exists(bg):
                _draw_image_or_svg(canvas, bg, 0, 0, width=A4[0], height=A4[1], preserveAspectRatio=False)
            if text:
                canvas.setFont('Helvetica-Bold', 24)
                canvas.setFillColor(PRIMARY_BLUE)
                canvas.drawCentredString(A4[0] / 2, A4[1] / 2, text)


def _insert_marketing_page_story(story, settings, key="first_page"):
    """
    Legacy: Insert a placeholder page break. The actual rendering is now done
    in the page handler via PromoPageManager for the first page,
    and we add a PageBreak at the end of content for the last page.
    This function just inserts a placeholder for the story approach.
    """
    cfg = settings.get(key, {})
    if not cfg.get('enabled'):
        return

    # Use a spacer + page break for legacy compatibility
    text = cfg.get('content_text', '')
    if text:
        from reportlab.lib.styles import getSampleStyleSheet
        p_style = ParagraphStyle(
            name='PromoText_' + key,
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=PRIMARY_BLUE,
            alignment=TA_CENTER,
            leading=28
        )
        story.append(Spacer(1, 100*mm))
        story.append(Paragraph(text, p_style))
    story.append(PageBreak())


def _escape(text: str) -> str:
    if not text:
        return ""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _get_layout(doc_type="mcq"):
    """Get layout settings for a doc type from editor settings or legacy."""
    editor = _load_editor_settings()
    if editor and doc_type in editor:
        return editor[doc_type].get('body', {}).get('layout', {})
    settings = pdf_config.load_settings()
    return settings.get('layout', {})


def generate_mcq_pdf(json_path: str, output_path: str = None, title: str = None) -> str:
    with open(json_path, 'r', encoding='utf-8') as f:
        mcqs = json.load(f)

    if not mcqs or not isinstance(mcqs, list):
        raise ValueError("JSON file is empty or not a valid MCQ list")

    json_file = Path(json_path)
    if output_path is None:
        output_path = str(json_file.with_suffix('.pdf'))
    if title is None:
        title = json_file.stem.replace('_', ' ').title()

    lay = _get_layout("mcq")
    editor = _load_editor_settings()
    promo = PromoPageManager("mcq")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=int(lay.get('margin_top', 20)) * mm,
        bottomMargin=int(lay.get('margin_bottom', 20)) * mm,
        leftMargin=int(lay.get('margin_left', 20)) * mm,
        rightMargin=int(lay.get('margin_right', 20)) * mm
    )

    styles = _get_styles("mcq")
    story = []

    # ── First page (element-based via promo handler) ──
    # We use an on-first-page callback approach
    first_page_rendered = [False]

    def _page_handler_with_first(canvas, doc):
        """Combined handler: draws promo on page 1, header/footer on all pages."""
        page_num = canvas.getPageNumber()
        if page_num == 1 and promo._first_enabled and not first_page_rendered[0]:
            promo.draw_first_page(canvas)
            first_page_rendered[0] = True
            return  # Skip header/footer on promo first page
        _create_page_handler("mcq")(canvas, doc)

    # If first page is enabled, add a page break before content
    if promo._first_enabled:
        story.append(PageBreak())

    # ── Content Header ──
    story.append(Paragraph("FREE ALL SUBJECTS HANDOUTS, MCQS FILES, AND QUIZ TEST POWERED BY VUEDU", styles['DocSubtitle']))
    story.append(Paragraph("VUEDU QUIZ TEST", styles['DocSubtitle']))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(title, styles['DocTitle']))
    story.append(Spacer(1, 8*mm))

    option_labels = ['A', 'B', 'C', 'D']

    correct_highlight = _hex_to_color(
        lay.get('correct_highlight_color', '#fef08a'),
        HexColor('#fef08a')
    )
    exp_bg_color = _hex_to_color(
        lay.get('explanation_bg_color', '#eff6ff'),
        EXP_BG_BLUE
    )
    exp_border_color = _hex_to_color(
        lay.get('explanation_border_color', '#bfdbfe'),
        EXP_BORDER
    )
    exp_width_pct = lay.get('explanation_width_percent', 35) / 100.0
    q_spacing = int(lay.get('question_spacing', 6))

    for mcq in mcqs:
        q_id = mcq.get('id', '?')
        question = mcq.get('question', 'No question text')
        options = mcq.get('options', [])
        correct = mcq.get('correct', '')
        explanation = mcq.get('explanation', '')
        diff = mcq.get('difficulty', '')
        imp = mcq.get('importance', '')

        block = []
        block.append(Paragraph(f"Q{q_id}. {_escape(question)}", styles['Question']))

        # Options
        correct_idx = -1
        for i, opt in enumerate(options):
            opt_str = str(opt).strip()
            corr_str = str(correct).strip()
            if opt_str == corr_str or opt_str.startswith(corr_str + ".") or opt_str.startswith(corr_str + ")") or opt_str.startswith(corr_str + " ") or opt_str.startswith(corr_str):
                correct_idx = i

        opt_data = []
        for i, opt in enumerate(options):
            label = option_labels[i] if i < len(option_labels) else str(i + 1)
            p = Paragraph(f"{label}. {_escape(str(opt))}", styles['Option'])
            opt_data.append([p])

        opt_flowables = []
        if opt_data:
            opt_table = Table(opt_data, colWidths=['100%'])
            opt_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]
            if correct_idx != -1:
                opt_styles.append(('BACKGROUND', (0, correct_idx), (0, correct_idx), correct_highlight))
            opt_table.setStyle(TableStyle(opt_styles))
            opt_flowables.append(opt_table)

        if lay.get('show_difficulty') and diff:
            opt_flowables.append(Paragraph(f"Difficulty: {diff}", styles['MetaText']))
        if lay.get('show_importance') and imp:
            opt_flowables.append(Paragraph(f"Importance: {imp}", styles['MetaText']))

        # Explanation box
        exp_flowables = []
        if explanation:
            exp_flowables.append(Paragraph("Explanation:", styles['ExplanationLabel']))
            exp_flowables.append(Paragraph(_escape(explanation), styles['Explanation']))

            exp_table = Table([[exp_flowables]], colWidths=['100%'])
            exp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), exp_bg_color),
                ('BOX', (0, 0), (-1, -1), 0.5, exp_border_color),
                ('TOPPADDING', (0, 0), (-1, -1), int(lay.get('explanation_padding', 6))),
                ('BOTTOMPADDING', (0, 0), (-1, -1), int(lay.get('explanation_padding', 6))),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
        else:
            exp_table = Spacer(1, 1)

        # Side-by-side layout
        opts_width = A4[0] * (1.0 - exp_width_pct) * 0.82
        exp_col_width = A4[0] * exp_width_pct
        row_data = [[opt_flowables, exp_table]]
        layout_table = Table(row_data, colWidths=[opts_width, exp_col_width])
        layout_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        block.append(layout_table)
        story.append(KeepTogether(block))
        story.append(Spacer(1, q_spacing * mm))

    # ── Last page (add page break then render) ──
    if promo._last_enabled:
        story.append(PageBreak())

    def _on_first_page(canvas, doc):
        if promo._first_enabled:
            promo.draw_first_page(canvas)
            # Don't draw header/footer on first promo page
        else:
            _create_page_handler("mcq")(canvas, doc)

    def _on_later_pages(canvas, doc):
        page_num = canvas.getPageNumber()
        total = doc.page

        # Detect if this is the last page (for last promo page)
        if promo._last_enabled and story:
            # We'll use a post-page approach — draw on the last page via after-page callback
            pass

        _create_page_handler("mcq")(canvas, doc)

    def _on_page_end(canvas, doc):
        """Called when each page ends — used to render last promotional page."""
        pass

    # Build PDF with proper page handlers
    def _first_pg(canvas, doc):
        if promo._first_enabled:
            promo.draw_first_page(canvas)
        else:
            _create_page_handler("mcq")(canvas, doc)

    def _later_pg(canvas, doc):
        _create_page_handler("mcq")(canvas, doc)

    def _after_draw(canvas, doc):
        """After build: if last page enabled, draw on the final page."""
        if promo._last_enabled:
            # The last page break added a new page — draw on it
            # We need to re-render the last page
            pass

    doc.build(
        story,
        onFirstPage=_first_pg,
        onLaterPages=_later_pg
    )

    # Post-process: if last page is enabled, we need to add it
    # We achieve this by rebuilding with a custom approach
    if promo._last_enabled:
        _append_last_page(output_path, promo, "mcq", lay)

    print(f"✓ MCQ PDF generated: {output_path}")
    return output_path


class _PromoLastPageFlowable(Spacer):
    """
    A custom Flowable that triggers drawing the last promotional page
    when it appears on a new page. Uses ReportLab's onDraw mechanism.
    """
    def __init__(self, promo: 'PromoPageManager'):
        super().__init__(0, 0)
        self._promo = promo

    def draw(self):
        pass  # Nothing to draw in-flow

    def beforePage(self):
        pass

    def wrap(self, availWidth, availHeight):
        return (0, 0)


def _append_last_page(pdf_path: str, promo: 'PromoPageManager', doc_type: str, lay: dict):
    """
    Append a last promotional page to an existing PDF.
    Uses pypdf for merging, falls back to raw byte append.
    """
    from reportlab.pdfgen import canvas as rl_canvas
    import io

    # Build the last page as a standalone PDF in memory
    buffer = io.BytesIO()
    c = rl_canvas.Canvas(buffer, pagesize=A4)
    promo.draw_last_page(c)
    c.save()
    buffer.seek(0)

    merged = False

    # Attempt 1: pypdf (pip install pypdf)
    try:
        from pypdf import PdfReader, PdfWriter
        existing_reader = PdfReader(pdf_path)
        last_reader = PdfReader(buffer)
        writer = PdfWriter()
        for page in existing_reader.pages:
            writer.add_page(page)
        for page in last_reader.pages:
            writer.add_page(page)
        with open(pdf_path, 'wb') as f:
            writer.write(f)
        print(f"✓ Last page appended via pypdf: {pdf_path}")
        merged = True
    except ImportError:
        pass
    except Exception as e:
        print(f"[PDFGen] pypdf merge failed: {e}")

    # Attempt 2: Raw byte append (compatible with most PDF viewers for simple pages)
    if not merged:
        try:
            buffer.seek(0)
            last_pdf_bytes = buffer.read()
            with open(pdf_path, 'ab') as f:
                f.write(last_pdf_bytes)
            print(f"[PDFGen] Last page appended via raw bytes (limited compat): {pdf_path}")
            merged = True
        except Exception as e:
            print(f"[PDFGen] Raw append failed: {e}")

    if not merged:
        print("[PDFGen] WARNING: Could not append last page. Install pypdf: pip install pypdf")



def generate_short_notes_pdf(json_path: str, output_path: str = None, title: str = None) -> str:
    with open(json_path, 'r', encoding='utf-8') as f:
        notes = json.load(f)

    if not notes or not isinstance(notes, list):
        raise ValueError("JSON file is empty or not a valid notes list")

    json_file = Path(json_path)
    if output_path is None:
        output_path = str(json_file.with_suffix('.pdf'))
    if title is None:
        title = json_file.stem.replace('_', ' ').title()

    lay = _get_layout("notes")
    promo = PromoPageManager("notes")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=int(lay.get('margin_top', 20)) * mm,
        bottomMargin=int(lay.get('margin_bottom', 25)) * mm,
        leftMargin=int(lay.get('margin_left', 20)) * mm,
        rightMargin=int(lay.get('margin_right', 20)) * mm
    )

    styles = _get_styles("notes")
    story = []

    # First page
    if promo._first_enabled:
        story.append(PageBreak())

    # Notes header
    story.append(Paragraph("VUEDU Short Notes", ParagraphStyle(
        'NotesHeader', fontName='Helvetica-Bold', fontSize=10,
        textColor=PRIMARY_BLUE, spaceAfter=2*mm
    )))
    story.append(HRFlowable(
        width="100%", thickness=0.5, color=HexColor('#cbd5e1'),
        spaceAfter=10*mm, spaceBefore=0
    ))
    story.append(Paragraph(title, styles['DocTitle']))
    story.append(Spacer(1, 6*mm))

    q_spacing = int(lay.get('question_spacing', 4))

    for i, note in enumerate(notes, 1):
        q_id = note.get('id', i)
        question = note.get('question', 'No question')
        answer = note.get('answer', 'No answer')

        block = []
        block.append(Paragraph(f"Q{q_id}. {_escape(question)}", styles['Question']))
        ans_text = f"<b>Answer:</b> {_escape(answer)}"
        block.append(Paragraph(ans_text, styles['NoteAnswer']))
        story.append(KeepTogether(block))
        story.append(Spacer(1, q_spacing * mm))

    if promo._last_enabled:
        story.append(PageBreak())

    def _first_pg(canvas, doc):
        if promo._first_enabled:
            promo.draw_first_page(canvas)
        else:
            _create_page_handler("notes")(canvas, doc)

    def _later_pg(canvas, doc):
        _create_page_handler("notes")(canvas, doc)

    doc.build(story, onFirstPage=_first_pg, onLaterPages=_later_pg)

    if promo._last_enabled:
        _append_last_page(output_path, promo, "notes", lay)

    print(f"✓ Notes PDF generated: {output_path}")
    return output_path


def generate_pdf_from_json(json_path: str, output_path: str = None) -> str:
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not data or not isinstance(data, list):
        raise ValueError("Invalid JSON file")

    if 'options' in data[0]:
        return generate_mcq_pdf(json_path, output_path)
    elif 'answer' in data[0]:
        return generate_short_notes_pdf(json_path, output_path)
    else:
        raise ValueError("Cannot determine content type from JSON structure")


def scan_json_files(root_path: str) -> List[Dict[str, str]]:
    results = []
    root = Path(root_path)
    if not root.exists():
        return results
    for json_file in root.rglob('*.json'):
        name = json_file.stem
        if json_file.name.lower().startswith('reviews'):
            continue
        if 'short note' in name.lower() or 'short_note' in name.lower():
            content_type = 'Short Notes'
        elif 'mcq' in name.lower():
            content_type = 'MCQs'
        else:
            content_type = 'Unknown'
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
