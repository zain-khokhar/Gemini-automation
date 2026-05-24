import sys

with open('pdf_generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

resolve_code = '''
def _resolve_font(font_fam, is_bold=False, is_italic=False):
    from reportlab.pdfbase import pdfmetrics
    if is_bold and is_italic: test_name = f"{font_fam}-BoldItalic"
    elif is_bold: test_name = f"{font_fam}-Bold"
    elif is_italic: test_name = f"{font_fam}-Italic"
    else: test_name = font_fam
    
    if test_name in pdfmetrics.getRegisteredFontNames(): return test_name
    
    std = ['Courier', 'Courier-Bold', 'Courier-Oblique', 'Courier-BoldOblique', 'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique', 'Helvetica-BoldOblique', 'Times-Roman', 'Times-Bold', 'Times-Italic', 'Times-BoldItalic', 'Symbol', 'ZapfDingbats']
    if test_name in std: return test_name
    
    if 'Bold' in test_name and 'Italic' in test_name: return 'Helvetica-BoldOblique'
    elif 'Bold' in test_name: return 'Helvetica-Bold'
    elif 'Italic' in test_name or 'Oblique' in test_name: return 'Helvetica-Oblique'
    return 'Helvetica'
'''

# Add function before _get_styles
content = content.replace('def _get_styles', resolve_code + '\n\ndef _get_styles')

# Replace _render_text_element font resolution
old_render = '''    # Build font name
    font_fam = el.get('font_family', 'Helvetica')
    if 'Bold' in font_fam:
        font_name = 'Helvetica-Bold'
        is_bold = True
    elif 'Oblique' in font_fam or 'Italic' in font_fam:
        font_name = 'Helvetica-Oblique'
    elif is_bold:
        font_name = 'Helvetica-Bold'
    else:
        font_name = 'Helvetica''''

new_render = '''    # Build font name
    font_fam = el.get('font_family', 'Helvetica')
    actual_bold = is_bold or 'Bold' in font_fam
    actual_italic = is_italic or 'Oblique' in font_fam or 'Italic' in font_fam
    base_fam = font_fam.replace('-Bold', '').replace('-Oblique', '').replace('-Italic', '')
    font_name = _resolve_font(base_fam, actual_bold, actual_italic)'''
content = content.replace(old_render, new_render)

# Replace Header font resolution
old_header = '''            h_font = h_cfg.get('font_family', 'Helvetica')
            if 'Bold' in h_font or h_cfg.get('font_weight', '') == 'bold':
                font_name = 'Helvetica-Bold'
            else:
                font_name = 'Helvetica''''

new_header = '''            h_font = h_cfg.get('font_family', 'Helvetica')
            is_bold = 'Bold' in h_font or h_cfg.get('font_weight', '') == 'bold'
            font_name = _resolve_font(h_font.replace('-Bold', ''), is_bold)'''
content = content.replace(old_header, new_header)

# Replace Footer font resolution
old_footer = '''            f_font = f_cfg.get('font_family', 'Helvetica')
            font_name_f = 'Helvetica-Bold' if ('Bold' in f_font or f_cfg.get('font_weight', '') == 'bold') else 'Helvetica''''

new_footer = '''            f_font = f_cfg.get('font_family', 'Helvetica')
            is_bold = 'Bold' in f_font or f_cfg.get('font_weight', '') == 'bold'
            font_name_f = _resolve_font(f_font.replace('-Bold', ''), is_bold)'''
content = content.replace(old_footer, new_footer)

with open('pdf_generator.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched successfully.')
