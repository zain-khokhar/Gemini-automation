"""
PDF Editor Module — Advanced Visual PDF Template Editor
Provides a professional drag-and-drop page editor with live A4 preview,
element positioning, full text/font/color customization, and per-type settings.
"""

import json
import os
import uuid
import copy
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QScrollArea, QFrame, QSplitter, QFileDialog, QMessageBox, QMenu, QAction,
    QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsTextItem,
    QGraphicsPixmapItem, QGraphicsItem, QColorDialog, QGroupBox,
    QTabWidget, QSizePolicy, QGraphicsLineItem, QSlider,
    QFontComboBox, QToolButton, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import (
    Qt, QRectF, QPointF, pyqtSignal, QSizeF, QTimer
)
from PyQt5.QtGui import (
    QFont, QColor, QPen, QBrush, QPixmap, QPainter, QFontMetrics,
    QLinearGradient, QPainterPath, QTransform, QCursor, QIcon, QFontDatabase
)


# ─────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────
EDITOR_SETTINGS_FILE = "pdf_editor_settings.json"

# A4 dimensions in points (1 point = 1/72 inch)
A4_WIDTH_PT = 595.0
A4_HEIGHT_PT = 842.0

# Preview scale (canvas shows A4 at this scale)
PREVIEW_SCALE = 0.72

PALETTE = {
    "bg": "#f7f8fa",
    "surface": "#ffffff",
    "border": "#e4e7ed",
    "accent": "#4361ee",
    "accent_hover": "#3451d1",
    "navy": "#1a1a2e",
    "text_primary": "#1a1a2e",
    "text_secondary": "#5a6478",
    "text_muted": "#9aa3b2",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "canvas_bg": "#e8eaed",
}

BASE_FONT_FAMILIES = [
    "Outfit", "Outfit-Bold", "Outfit-Light",
    "Inter", "Inter-Bold", "Inter-Medium",
    "Poppins", "Poppins-Bold", "Poppins-Light",
    "Montserrat", "Montserrat-Bold", "Montserrat-Light",
    "Plus Jakarta Sans", "Plus Jakarta Sans-Bold",
    "Google Sans Flex", "Google Sans Flex-Medium", "Google Sans Flex-Bold"
]

CUSTOM_FONT_PATHS = [
    os.path.join(os.path.dirname(__file__), "assets", "fonts"),
    r"C:\Users\zaink\Downloads\nebula"
]
SUPPORTED_FONT_EXTS = (".ttf", ".otf")


def _register_editor_fonts():
    """Register local fonts for the PDF editor preview."""
    loaded_families = []
    for font_dir in CUSTOM_FONT_PATHS:
        try:
            if not os.path.isdir(font_dir):
                continue
            for font_file in sorted(os.listdir(font_dir)):
                if not font_file.lower().endswith(SUPPORTED_FONT_EXTS):
                    continue
                font_path = os.path.join(font_dir, font_file)
                if not os.path.isfile(font_path):
                    continue
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id == -1:
                    continue
                loaded_families.extend(QFontDatabase.applicationFontFamilies(font_id))
        except Exception as e:
            print(f"[PDFEditor] Could not register fonts from {font_dir}: {e}")
    return loaded_families


def _resolve_editor_font_family(font_family):
    """Resolve editor font family names for on-screen preview."""
    family = font_family.replace('-Bold', '').replace('-Oblique', '').replace('-Italic', '')
    if family == 'Helvetica':
        return 'Arial'
    if family == 'Times-Roman' or family == 'Times':
        return 'Times New Roman'
    return family


def _get_font_family_list():
    return BASE_FONT_FAMILIES.copy()


def _load_editor_fonts():
    """Register local fonts after QApplication exists and return added family names."""
    loaded_families = []
    for font_dir in CUSTOM_FONT_PATHS:
        try:
            if not os.path.isdir(font_dir):
                continue
            for font_file in sorted(os.listdir(font_dir)):
                if not font_file.lower().endswith(SUPPORTED_FONT_EXTS):
                    continue
                font_path = os.path.join(font_dir, font_file)
                if not os.path.isfile(font_path):
                    continue
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id == -1:
                    continue
                for fam in QFontDatabase.applicationFontFamilies(font_id):
                    if fam not in loaded_families:
                        loaded_families.append(fam)
        except Exception as e:
            print(f"[PDFEditor] Could not register fonts from {font_dir}: {e}")
    return loaded_families

FONT_FAMILIES = _get_font_family_list()


# ─────────────────────────────────────────────────────────────
#  Settings Manager for Editor
# ─────────────────────────────────────────────────────────────
class PDFEditorSettingsManager:
    """Manages the enhanced PDF editor settings (per-type, per-section)."""

    def __init__(self, config_path=EDITOR_SETTINGS_FILE):
        self.config_path = config_path
        self.settings = self._load()

    def _load(self):
        if not os.path.exists(self.config_path):
            return self._default_settings()
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('version', 1) >= 2:
                return data
            return self._default_settings()
        except Exception as e:
            print(f"[PDFEditor] Error loading settings: {e}")
            return self._default_settings()

    def _default_settings(self):
        """Return a minimal default structure."""
        default_element = lambda eid, content, y, size=14, bold=True: {
            "id": eid,
            "type": "text",
            "content": content,
            "x": 297, "y": y,
            "width": 440, "height": max(30, size + 16),
            "font_family": "Outfit-Bold" if bold else "Outfit",
            "font_size": size,
            "color": "#1642a8",
            "alignment": "center",
            "bold": bold, "italic": False, "underline": False,
            "letter_spacing": 0, "line_height": 1.2,
            "hyperlink": "", "opacity": 1.0
        }

        page_section = lambda elems: {
            "enabled": True,
            "background_image": "",
            "background_color": "#ffffff",
            "elements": elems
        }

        body_section = {
            "header": {
                "enabled": True, "text": "", "url": "",
                "color": "#1642a8", "font_family": "Outfit-Bold",
                "font_size": 8, "font_weight": "bold",
                "letter_spacing": 0.3, "alignment": "right",
                "show_line": True, "line_color": "#e5e7eb",
                "line_thickness": 0.5, "padding_top": 8, "padding_bottom": 4
            },
            "footer": {
                "enabled": True, "text": "— {page_num} —", "url": "",
                "color": "#6b7280", "font_family": "Outfit",
                "font_size": 8, "font_weight": "normal",
                "letter_spacing": 0, "alignment": "center",
                "show_line": True, "line_color": "#e5e7eb",
                "line_thickness": 0.5, "padding_top": 4, "padding_bottom": 8
            },
            "layout": {
                "margin_top": 20, "margin_bottom": 25,
                "margin_left": 20, "margin_right": 20,
                "font_family": "Outfit", "title_size": 18,
                "title_color": "#1642a8", "question_size": 10,
                "question_color": "#1642a8", "option_size": 9.5,
                "option_color": "#374151", "correct_highlight_color": "#fef08a",
                "explanation_size": 9, "explanation_bg_color": "#eff6ff",
                "explanation_text_color": "#1e293b",
                "explanation_border_color": "#bfdbfe",
                "explanation_padding": 6, "explanation_width_percent": 35,
                "question_spacing": 6, "option_indent": 8,
                "show_difficulty": False, "show_importance": False
            }
        }

        return {
            "version": 2,
            "mcq": {
                "first_page": page_section([
                    default_element("fp_title", "VUEDU Premium MCQs", 360, 32),
                    default_element("fp_subtitle", "FREE ALL SUBJECTS HANDOUTS & QUIZ", 420, 12, False),
                ]),
                "body": copy.deepcopy(body_section),
                "last_page": page_section([
                    default_element("lp_thanks", "Thank You for Studying!", 360, 26),
                ])
            },
            "notes": {
                "first_page": page_section([
                    default_element("fp_title", "VUEDU Short Notes", 360, 32),
                ]),
                "body": copy.deepcopy(body_section),
                "last_page": page_section([
                    default_element("lp_thanks", "Thank You!", 360, 26),
                ])
            }
        }

    def save(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[PDFEditor] Save error: {e}")
            return False

    def get_doc_type_settings(self, doc_type):
        return self.settings.get(doc_type, self.settings.get('mcq', {}))

    def get_section(self, doc_type, section):
        return self.get_doc_type_settings(doc_type).get(section, {})

    def set_section(self, doc_type, section, data):
        if doc_type not in self.settings:
            self.settings[doc_type] = {}
        self.settings[doc_type][section] = data

    def get_elements(self, doc_type, section):
        sec = self.get_section(doc_type, section)
        return sec.get('elements', [])

    def set_elements(self, doc_type, section, elements):
        if doc_type not in self.settings:
            self.settings[doc_type] = {}
        if section not in self.settings[doc_type]:
            self.settings[doc_type][section] = {"enabled": True, "background_image": "", "background_color": "#ffffff", "elements": []}
        self.settings[doc_type][section]['elements'] = elements


# ─────────────────────────────────────────────────────────────
#  Draggable Canvas Element
# ─────────────────────────────────────────────────────────────
class DraggableTextItem(QGraphicsRectItem):
    """A draggable, selectable text element on the canvas."""

    def __init__(self, element_data, scale=PREVIEW_SCALE, parent=None):
        super().__init__(parent)
        self.element_data = element_data
        self.scale = scale
        self._selected = False

        # Position and size from data
        x = element_data.get('x', 100) * scale
        y = element_data.get('y', 100) * scale
        w = element_data.get('width', 200) * scale
        h = element_data.get('height', 30) * scale

        # Calculate dynamic text height
        font_family = _resolve_editor_font_family(element_data.get('font_family', 'Helvetica'))
        font_size = max(6, int(element_data.get('font_size', 12) * scale))
        font = QFont(font_family, font_size)
        font.setBold(element_data.get('bold', False) or 'Bold' in element_data.get('font_family', ''))
        font.setItalic(element_data.get('italic', False) or 'Oblique' in element_data.get('font_family', '') or 'Italic' in element_data.get('font_family', ''))
        fm = QFontMetrics(font)
        bounds = fm.boundingRect(0, 0, int(w - 8), 9999, int(Qt.TextWordWrap), element_data.get('content', ''))
        needed_h = bounds.height() + 8
        if needed_h > h:
            h = needed_h
            element_data['height'] = h / scale

        self.setRect(0, 0, w, h)
        self.setPos(x - w / 2, y - h / 2)  # Center-based positioning

        # Make it interactive
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setCursor(QCursor(Qt.OpenHandCursor))
        self.setAcceptHoverEvents(True)

        self._update_appearance()

    def _update_appearance(self):
        """Update visual from element_data."""
        el = self.element_data
        color = QColor(el.get('color', '#1642a8'))
        opacity = el.get('opacity', 1.0)
        self.setOpacity(opacity)

        # Transparent background for text elements
        self.setBrush(QBrush(Qt.transparent))
        self.setPen(QPen(Qt.transparent))

    def paint(self, painter, option, widget=None):
        """Custom paint to render styled text inside the rect."""
        el = self.element_data
        rect = self.rect()

        # Selection indicator
        if self.isSelected():
            painter.setPen(QPen(QColor(PALETTE['accent']), 2, Qt.DashLine))
            painter.setBrush(QBrush(QColor(67, 97, 238, 20)))
            painter.drawRect(rect)
        else:
            # Subtle border on hover
            painter.setPen(QPen(QColor(200, 200, 200, 80), 0.5, Qt.DotLine))
            painter.drawRect(rect)

        # Build font
        font_family = _resolve_editor_font_family(el.get('font_family', 'Helvetica'))
        font_size = max(6, int(el.get('font_size', 12) * self.scale))
        font = QFont(font_family, font_size)
        font.setBold(el.get('bold', False) or 'Bold' in el.get('font_family', ''))
        font.setItalic(el.get('italic', False) or 'Oblique' in el.get('font_family', '') or 'Italic' in el.get('font_family', ''))
        font.setUnderline(el.get('underline', False))

        ls = el.get('letter_spacing', 0)
        if ls:
            font.setLetterSpacing(QFont.AbsoluteSpacing, ls * self.scale)

        painter.setFont(font)
        painter.setPen(QPen(QColor(el.get('color', '#1642a8'))))

        alignment = el.get('alignment', 'center')
        flags = int(Qt.AlignVCenter)
        if alignment == 'left':
            flags |= int(Qt.AlignLeft)
        elif alignment == 'right':
            flags |= int(Qt.AlignRight)
        else:
            flags |= int(Qt.AlignHCenter)

        content = el.get('content', '')
        
        text_rect = rect.adjusted(4, 2, -4, -2)
        fm = QFontMetrics(font)
        
        # Word wrap manually
        lines = []
        for block in content.split('\n'):
            current_line = []
            for word in block.split(' '):
                test_line = ' '.join(current_line + [word])
                if fm.horizontalAdvance(test_line) > text_rect.width() and current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    current_line.append(word)
            if current_line:
                lines.append(' '.join(current_line))

        line_height_multiplier = el.get('line_height', 1.2)
        line_h_px = font_size * line_height_multiplier
        
        total_h = len(lines) * line_h_px
        start_y = text_rect.center().y() - total_h / 2.0

        for i, line in enumerate(lines):
            line_rect = QRectF(text_rect.left(), start_y + i * line_h_px, text_rect.width(), line_h_px)
            painter.drawText(line_rect, flags, line)

        # Hyperlink underline indicator
        if el.get('hyperlink'):
            painter.setPen(QPen(QColor(el.get('color', '#1642a8')), 1))
            fm = QFontMetrics(font)
            tw = min(fm.horizontalAdvance(content), rect.width() - 8)
            cx = rect.center().x()
            by = rect.bottom() - 4
            painter.drawLine(int(cx - tw / 2), int(by), int(cx + tw / 2), int(by))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            # Update element_data position when dragged
            rect = self.rect()
            center_x = (self.pos().x() + rect.width() / 2) / self.scale
            center_y = (self.pos().y() + rect.height() / 2) / self.scale
            self.element_data['x'] = round(center_x, 1)
            self.element_data['y'] = round(center_y, 1)
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self.setCursor(QCursor(Qt.SizeAllCursor))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(QCursor(Qt.OpenHandCursor))
        super().hoverLeaveEvent(event)


class DraggableImageItem(QGraphicsRectItem):
    """A draggable image element on the canvas."""

    def __init__(self, element_data, scale=PREVIEW_SCALE, parent=None):
        super().__init__(parent)
        self.element_data = element_data
        self.scale = scale
        self._pixmap = None

        x = element_data.get('x', 100) * scale
        y = element_data.get('y', 100) * scale
        w = element_data.get('width', 150) * scale
        h = element_data.get('height', 150) * scale

        self.setRect(0, 0, w, h)
        self.setPos(x - w / 2, y - h / 2)

        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setCursor(QCursor(Qt.OpenHandCursor))
        self.setAcceptHoverEvents(True)
        self.setOpacity(element_data.get('opacity', 1.0))

        self._load_image()

    def _load_image(self):
        path = self.element_data.get('path', '')
        if path and os.path.exists(path):
            self._pixmap = QPixmap(path)
        else:
            self._pixmap = None

    def paint(self, painter, option, widget=None):
        rect = self.rect()

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                int(rect.width()), int(rect.height()),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            dx = (rect.width() - scaled.width()) / 2
            dy = (rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(rect.x() + dx), int(rect.y() + dy), scaled)
        else:
            # Placeholder
            painter.setBrush(QBrush(QColor("#f0f0f0")))
            painter.setPen(QPen(QColor("#ccc"), 1, Qt.DashLine))
            painter.drawRect(rect)
            painter.setPen(QPen(QColor("#999")))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(rect, Qt.AlignCenter, "🖼 Image\n(not found)")

        if self.isSelected():
            painter.setPen(QPen(QColor(PALETTE['accent']), 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            rect = self.rect()
            center_x = (self.pos().x() + rect.width() / 2) / self.scale
            center_y = (self.pos().y() + rect.height() / 2) / self.scale
            self.element_data['x'] = round(center_x, 1)
            self.element_data['y'] = round(center_y, 1)
        return super().itemChange(change, value)


# ─────────────────────────────────────────────────────────────
#  PDF Canvas Preview Widget
# ─────────────────────────────────────────────────────────────
class PDFCanvasWidget(QGraphicsView):
    """Live A4 page preview with draggable elements."""
    element_selected = pyqtSignal(dict)  # emits element_data when selected
    element_deselected = pyqtSignal()
    elements_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)

        self.scale_factor = PREVIEW_SCALE
        self.page_width = A4_WIDTH_PT * self.scale_factor
        self.page_height = A4_HEIGHT_PT * self.scale_factor

        # Visual setup
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setStyleSheet(f"background: {PALETTE['canvas_bg']}; border: none; border-radius: 8px;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setMinimumWidth(460)
        self.setMinimumHeight(580)

        self._current_elements = []
        self._bg_image_path = ""
        self._bg_color = "#ffffff"
        self._graphics_items = []

        # Selection tracking
        self.scene.selectionChanged.connect(self._on_selection_changed)

    def render_page(self, section_data, section_type="first_page"):
        """Render a page section (first_page/last_page) on the canvas."""
        selected_id = None
        selected = self.scene.selectedItems()
        if selected and hasattr(selected[0], 'element_data'):
            selected_id = selected[0].element_data.get('id')

        self.scene.blockSignals(True)
        self.scene.clear()
        self._graphics_items = []

        # Page background (white paper)
        page_rect = self.scene.addRect(
            0, 0, self.page_width, self.page_height,
            QPen(QColor("#d0d0d0"), 1),
            QBrush(QColor(section_data.get('background_color', '#ffffff')))
        )
        page_rect.setZValue(-2)

        # Drop shadow for page
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(3, 3)
        shadow.setColor(QColor(0, 0, 0, 40))
        page_rect.setGraphicsEffect(shadow)

        # Background image
        bg_path = section_data.get('background_image', '')
        if bg_path and os.path.exists(bg_path):
            pixmap = QPixmap(bg_path).scaled(
                int(self.page_width), int(self.page_height),
                Qt.IgnoreAspectRatio, Qt.SmoothTransformation
            )
            bg_item = self.scene.addPixmap(pixmap)
            bg_item.setPos(0, 0)
            bg_item.setZValue(-1)
            bg_item.setOpacity(section_data.get('bg_opacity', 1.0))

        # Page Border
        border_thickness = section_data.get('border_thickness', 0.0)
        if border_thickness > 0:
            border_color = QColor(section_data.get('border_color', '#000000'))
            border_rect = self.scene.addRect(
                border_thickness / 2, border_thickness / 2, 
                self.page_width - border_thickness, 
                self.page_height - border_thickness,
                QPen(border_color, border_thickness),
                QBrush(Qt.NoBrush)
            )
            border_rect.setZValue(100)

        # Render elements
        elements = section_data.get('elements', [])
        self._current_elements = elements

        for el in elements:
            el_type = el.get('type', 'text')
            if el_type == 'text':
                item = DraggableTextItem(el, self.scale_factor)
            elif el_type == 'image':
                item = DraggableImageItem(el, self.scale_factor)
            else:
                continue

            self.scene.addItem(item)
            self._graphics_items.append(item)

            if selected_id and el.get('id') == selected_id:
                item.setSelected(True)

        self.scene.blockSignals(False)

        # Fit view
        self.setSceneRect(-20, -20, self.page_width + 40, self.page_height + 40)
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def render_body_page(self, body_data, doc_type="mcq"):
        """Render a mock preview of the body page margins and settings based on doc_type."""
        self.scene.clear()
        self._graphics_items = []
        self._current_elements = []

        header = body_data.get('header', {})
        footer = body_data.get('footer', {})
        layout = body_data.get('layout', {})

        # Page background
        page_rect = self.scene.addRect(
            0, 0, self.page_width, self.page_height,
            QPen(QColor("#d0d0d0"), 1),
            QBrush(QColor("#ffffff"))
        )
        page_rect.setZValue(-2)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(3, 3)
        shadow.setColor(QColor(0, 0, 0, 40))
        page_rect.setGraphicsEffect(shadow)

        s = self.scale_factor

        # Margins visualization
        mt = layout.get('margin_top', 20) * s * 2.83  # mm to pt approx
        mb = layout.get('margin_bottom', 25) * s * 2.83
        ml = layout.get('margin_left', 20) * s * 2.83
        mr = layout.get('margin_right', 20) * s * 2.83

        # Margin guides (light dashed lines)
        pen_guide = QPen(QColor("#e0e0e0"), 0.5, Qt.DashLine)
        self.scene.addLine(ml, 0, ml, self.page_height, pen_guide)
        self.scene.addLine(self.page_width - mr, 0, self.page_width - mr, self.page_height, pen_guide)
        self.scene.addLine(0, mt, self.page_width, mt, pen_guide)
        self.scene.addLine(0, self.page_height - mb, self.page_width, self.page_height - mb, pen_guide)

        # Header area
        if header.get('enabled', True):
            h_text = header.get('text', '')
            if h_text:
                h_font = QFont("Arial", max(6, int(header.get('font_size', 8) * s)))
                h_font.setBold(header.get('font_weight', '') == 'bold')
                h_item = self.scene.addText(h_text, h_font)
                h_item.setDefaultTextColor(QColor(header.get('color', '#1642a8')))

                align = header.get('alignment', 'right')
                h_y = header.get('padding_top', 8) * s
                if align == 'right':
                    h_item.setPos(self.page_width - mr - h_item.boundingRect().width(), h_y)
                elif align == 'left':
                    h_item.setPos(ml, h_y)
                else:
                    h_item.setPos((self.page_width - h_item.boundingRect().width()) / 2, h_y)

            # Header line
            if header.get('show_line', True):
                line_y = mt - 4 * s
                line_pen = QPen(QColor(header.get('line_color', '#e5e7eb')), header.get('line_thickness', 0.5) * s * 2)
                self.scene.addLine(ml, line_y, self.page_width - mr, line_y, line_pen)

        # Footer area
        if footer.get('enabled', True):
            f_text = footer.get('text', '— 1 —').replace('{page_num}', '1')
            if f_text:
                f_font = QFont("Arial", max(6, int(footer.get('font_size', 8) * s)))
                f_item = self.scene.addText(f_text, f_font)
                f_item.setDefaultTextColor(QColor(footer.get('color', '#6b7280')))

                f_y = self.page_height - footer.get('padding_bottom', 8) * s - f_item.boundingRect().height()
                align = footer.get('alignment', 'center')
                if align == 'center':
                    f_item.setPos((self.page_width - f_item.boundingRect().width()) / 2, f_y)
                elif align == 'left':
                    f_item.setPos(ml, f_y)
                else:
                    f_item.setPos(self.page_width - mr - f_item.boundingRect().width(), f_y)

            if footer.get('show_line', True):
                line_y = self.page_height - mb + 4 * s
                line_pen = QPen(QColor(footer.get('line_color', '#e5e7eb')), footer.get('line_thickness', 0.5) * s * 2)
                self.scene.addLine(ml, line_y, self.page_width - mr, line_y, line_pen)

        # Sample content area (shows mock MCQ/Note)
        content_y = mt + 10 * s
        content_x = ml + 5 * s
        avail_w = self.page_width - ml - mr - 10 * s

        # Title placeholder
        title_font = QFont("Arial", max(8, int(layout.get('title_size', 18) * s)))
        title_font.setBold(True)
        title_item = self.scene.addText("Subject Title — MCQs / Notes", title_font)
        title_item.setDefaultTextColor(QColor(layout.get('title_color', '#1642a8')))
        title_item.setPos((self.page_width - title_item.boundingRect().width()) / 2, content_y)
        content_y += title_item.boundingRect().height() + 12 * s

        # Sample question
        q_font = QFont("Arial", max(6, int(layout.get('question_size', 10) * s)))
        q_font.setBold(True)
        q_item = self.scene.addText("Q1. What is the primary function of an operating system?", q_font)
        q_item.setDefaultTextColor(QColor(layout.get('question_color', '#1642a8')))
        q_item.setTextWidth(avail_w * 0.9)
        q_item.setPos(content_x, content_y)
        content_y += q_item.boundingRect().height() + 8 * s

        if doc_type == "mcq":
            opt_font = QFont("Arial", max(6, int(layout.get('option_size', 9.5) * s)))
            options = ["A. Resource management", "B. Game development", "C. Web browsing", "D. File compression"]
            indent = layout.get('option_indent', 8) * s
            for i, opt_text in enumerate(options):
                opt_item = self.scene.addText(opt_text, opt_font)
                opt_item.setDefaultTextColor(QColor(layout.get('option_color', '#374151')))
                opt_item.setPos(content_x + indent, content_y)

                # Highlight correct answer
                if i == 0:
                    highlight_color = QColor(layout.get('correct_highlight_color', '#fef08a'))
                    hr = self.scene.addRect(
                        content_x + indent - 2, content_y,
                        opt_item.boundingRect().width() + 4,
                        opt_item.boundingRect().height(),
                        QPen(Qt.NoPen), QBrush(highlight_color)
                    )
                    hr.setZValue(-0.5)

                content_y += opt_item.boundingRect().height() + 1 * s

            # Explanation box
            content_y += 4 * s
            exp_w = avail_w * layout.get('explanation_width_percent', 35) / 100
            exp_h = 40 * s
            exp_x = self.page_width - mr - exp_w - 5 * s
            exp_bg = QColor(layout.get('explanation_bg_color', '#eff6ff'))
            exp_border = QColor(layout.get('explanation_border_color', '#bfdbfe'))

            exp_rect = self.scene.addRect(
                exp_x, content_y - 40 * s, exp_w, exp_h,
                QPen(exp_border, 1), QBrush(exp_bg)
            )

            exp_font = QFont("Arial", max(5, int(layout.get('explanation_size', 9) * s)))
            exp_text = self.scene.addText("Explanation: OS manages hardware resources...", exp_font)
            exp_text.setDefaultTextColor(QColor(layout.get('explanation_text_color', '#1e293b')))
            exp_text.setTextWidth(exp_w - 8 * s)
            exp_text.setPos(exp_x + 4 * s, content_y - 38 * s)
        else:
            # Short Notes preview
            ans_font = QFont("Arial", max(6, int(layout.get('option_size', 9.5) * s)))
            ans_text = self.scene.addText("Answer: The primary function of an OS is resource management.", ans_font)
            ans_text.setDefaultTextColor(QColor(layout.get('option_color', '#374151')))
            ans_text.setTextWidth(avail_w * 0.9)
            ans_text.setPos(content_x, content_y)
            content_y += ans_text.boundingRect().height() + 1 * s

        # Fit view
        self.setSceneRect(-20, -20, self.page_width + 40, self.page_height + 40)
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def _on_selection_changed(self):
        selected = self.scene.selectedItems()
        if selected:
            item = selected[0]
            if hasattr(item, 'element_data'):
                self.element_selected.emit(item.element_data)
        else:
            self.element_deselected.emit()

    def add_element(self, element_data):
        """Add a new element to the canvas."""
        self._current_elements.append(element_data)
        el_type = element_data.get('type', 'text')
        if el_type == 'text':
            item = DraggableTextItem(element_data, self.scale_factor)
        elif el_type == 'image':
            item = DraggableImageItem(element_data, self.scale_factor)
        else:
            return
        self.scene.addItem(item)
        self._graphics_items.append(item)
        self.elements_changed.emit()

    def delete_selected(self):
        """Delete the currently selected element."""
        selected = self.scene.selectedItems()
        for item in selected:
            if hasattr(item, 'element_data'):
                if item.element_data in self._current_elements:
                    self._current_elements.remove(item.element_data)
                self.scene.removeItem(item)
                if item in self._graphics_items:
                    self._graphics_items.remove(item)
        self.elements_changed.emit()
        self.element_deselected.emit()

    def get_elements(self):
        return self._current_elements

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.scene.items():
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)


# ─────────────────────────────────────────────────────────────
#  Properties Panel
# ─────────────────────────────────────────────────────────────
class PropertiesPanel(QWidget):
    property_changed = pyqtSignal()
    page_property_changed = pyqtSignal()

    def __init__(self, available_fonts=None, parent=None):
        super().__init__(parent)
        self._available_fonts = available_fonts or []
        self._current_element = None
        self._block_signals = False
        self.setMinimumWidth(300)
        self.setMaximumWidth(380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(10)

        # Title
        self._title_label = QLabel("Properties")
        self._title_label.setStyleSheet(f"color: {PALETTE['text_primary']}; font-size: 12pt; font-weight: 700;")
        self._content_layout.addWidget(self._title_label)

        # ── Page Properties (Shown when nothing selected) ──
        self._page_group, page_lay = self._make_group("Page Properties")
        
        bg_op_row = QHBoxLayout()
        bg_op_row.addWidget(QLabel("Bg Opacity:"))
        self._bg_opacity_slider = QSlider(Qt.Horizontal)
        self._bg_opacity_slider.setRange(10, 100)
        self._bg_opacity_slider.setValue(100)
        self._bg_opacity_slider.valueChanged.connect(self._on_page_prop_changed)
        bg_op_row.addWidget(self._bg_opacity_slider)
        self._bg_op_val_label = QLabel("100%")
        self._bg_op_val_label.setMinimumWidth(40)
        bg_op_row.addWidget(self._bg_op_val_label)
        page_lay.addLayout(bg_op_row)
        
        self._clear_bg_btn = QPushButton("Remove Background")
        self._clear_bg_btn.clicked.connect(self._clear_background)
        page_lay.addWidget(self._clear_bg_btn)

        border_row = QHBoxLayout()
        border_row.addWidget(QLabel("Border (pt):"))
        self._border_spin = QDoubleSpinBox()
        self._border_spin.setRange(0, 50)
        self._border_spin.setMinimumHeight(28)
        self._border_spin.valueChanged.connect(self._on_page_prop_changed)
        border_row.addWidget(self._border_spin)

        self._border_color_btn = QPushButton("Color")
        self._border_color_btn.setMinimumHeight(28)
        self._border_color_btn.clicked.connect(self._pick_border_color)
        border_row.addWidget(self._border_color_btn)
        page_lay.addLayout(border_row)

        self._page_section_data = None

        # ── Text Content ──
        self._text_group, text_lay = self._make_group("Text Content")
        self._content_input = QPlainTextEdit()
        self._content_input.setPlaceholderText("Element text content... (Shift+Enter for new line)")
        self._content_input.setMinimumHeight(64)
        self._content_input.setMaximumHeight(100)
        self._content_input.textChanged.connect(self._on_content_changed)
        text_lay.addWidget(self._content_input)

        # ── Font Controls ──
        self._font_group, font_lay = self._make_group("Typography")

        font_row = QHBoxLayout()
        self._font_family_combo = QComboBox()
        self._font_family_combo.addItems(self._available_fonts)
        self._font_family_combo.setMinimumHeight(30)
        self._font_family_combo.currentTextChanged.connect(self._on_font_changed)
        font_row.addWidget(self._font_family_combo, 2)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(4, 120)
        self._font_size_spin.setValue(14)
        self._font_size_spin.setMinimumHeight(30)
        self._font_size_spin.setSuffix(" pt")
        self._font_size_spin.valueChanged.connect(self._on_font_changed)
        font_row.addWidget(self._font_size_spin, 1)
        font_lay.addLayout(font_row)

        # Style buttons row
        style_row = QHBoxLayout()
        self._bold_btn = self._make_toggle_btn("B", "Bold")
        self._bold_btn.setStyleSheet("font-weight: bold; font-size: 11pt; min-width: 32px; min-height: 28px;")
        self._bold_btn.clicked.connect(self._on_style_changed)
        style_row.addWidget(self._bold_btn)

        self._italic_btn = self._make_toggle_btn("I", "Italic")
        self._italic_btn.setStyleSheet("font-style: italic; font-size: 11pt; min-width: 32px; min-height: 28px;")
        self._italic_btn.clicked.connect(self._on_style_changed)
        style_row.addWidget(self._italic_btn)

        self._underline_btn = self._make_toggle_btn("U", "Underline")
        self._underline_btn.setStyleSheet("text-decoration: underline; font-size: 11pt; min-width: 32px; min-height: 28px;")
        self._underline_btn.clicked.connect(self._on_style_changed)
        style_row.addWidget(self._underline_btn)

        style_row.addStretch()

        # Color button
        self._color_btn = QPushButton("  Color  ")
        self._color_btn.setMinimumHeight(28)
        self._color_btn.setMinimumWidth(70)
        self._color_btn.clicked.connect(self._pick_color)
        style_row.addWidget(self._color_btn)

        font_lay.addLayout(style_row)

        # Alignment
        align_row = QHBoxLayout()
        align_label = QLabel("Align:")
        align_label.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 9pt;")
        align_row.addWidget(align_label)

        self._align_combo = QComboBox()
        self._align_combo.addItems(["left", "center", "right"])
        self._align_combo.setMinimumHeight(28)
        self._align_combo.currentTextChanged.connect(self._on_alignment_changed)
        align_row.addWidget(self._align_combo)
        align_row.addStretch()

        font_lay.addLayout(align_row)

        # Letter spacing + Line height
        spacing_row = QHBoxLayout()
        spacing_row.addWidget(QLabel("Spacing:"))
        self._letter_spacing_spin = QDoubleSpinBox()
        self._letter_spacing_spin.setRange(-5, 20)
        self._letter_spacing_spin.setSingleStep(0.1)
        self._letter_spacing_spin.setMinimumHeight(28)
        self._letter_spacing_spin.valueChanged.connect(self._on_spacing_changed)
        spacing_row.addWidget(self._letter_spacing_spin)

        spacing_row.addWidget(QLabel("Line H:"))
        self._line_height_spin = QDoubleSpinBox()
        self._line_height_spin.setRange(0.5, 5.0)
        self._line_height_spin.setSingleStep(0.1)
        self._line_height_spin.setMinimumHeight(28)
        self._line_height_spin.valueChanged.connect(self._on_spacing_changed)
        spacing_row.addWidget(self._line_height_spin)

        font_lay.addLayout(spacing_row)

        # ── Position & Size ──
        self._pos_group, pos_lay = self._make_group("Position & Size")

        pos_row = QHBoxLayout()
        pos_row.addWidget(QLabel("X:"))
        self._x_spin = QDoubleSpinBox()
        self._x_spin.setRange(0, 700)
        self._x_spin.setMinimumHeight(28)
        self._x_spin.valueChanged.connect(self._on_pos_changed)
        pos_row.addWidget(self._x_spin)

        pos_row.addWidget(QLabel("Y:"))
        self._y_spin = QDoubleSpinBox()
        self._y_spin.setRange(0, 900)
        self._y_spin.setMinimumHeight(28)
        self._y_spin.valueChanged.connect(self._on_pos_changed)
        pos_row.addWidget(self._y_spin)
        pos_lay.addLayout(pos_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("W:"))
        self._w_spin = QDoubleSpinBox()
        self._w_spin.setRange(20, 600)
        self._w_spin.setMinimumHeight(28)
        self._w_spin.valueChanged.connect(self._on_size_changed)
        size_row.addWidget(self._w_spin)

        size_row.addWidget(QLabel("H:"))
        self._h_spin = QDoubleSpinBox()
        self._h_spin.setRange(10, 900)
        self._h_spin.setMinimumHeight(28)
        self._h_spin.valueChanged.connect(self._on_size_changed)
        size_row.addWidget(self._h_spin)
        pos_lay.addLayout(size_row)

        # Opacity
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("Opacity:"))
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(10, 100)
        self._opacity_slider.setValue(100)
        self._opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_row.addWidget(self._opacity_slider)
        self._opacity_val_label = QLabel("100%")
        self._opacity_val_label.setMinimumWidth(40)
        opacity_row.addWidget(self._opacity_val_label)
        pos_lay.addLayout(opacity_row)

        # ── Hyperlink ──
        self._link_group, link_lay = self._make_group("Hyperlink")
        self._hyperlink_input = QLineEdit()
        self._hyperlink_input.setPlaceholderText("https://example.com")
        self._hyperlink_input.setMinimumHeight(30)
        self._hyperlink_input.textChanged.connect(self._on_hyperlink_changed)
        link_lay.addWidget(self._hyperlink_input)

        link_hint = QLabel("Text with hyperlinks will be clickable in the PDF")
        link_hint.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 8.5pt;")
        link_lay.addWidget(link_hint)

        # Spacer
        self._content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Initially hide property groups
        self._set_groups_visible(False)

    def _make_group(self, title):
        """Create a styled group box and return (group, layout) tuple."""
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: 600;
                font-size: 9.5pt;
                color: {PALETTE['text_secondary']};
                border: 1.5px solid {PALETTE['border']};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                background: {PALETTE['surface']};
            }}
        """)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(10, 8, 10, 8)
        group_layout.setSpacing(6)
        self._content_layout.addWidget(group)
        return group, group_layout

    def _make_toggle_btn(self, text, tooltip):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setToolTip(tooltip)
        btn.setFixedSize(32, 28)
        return btn

    def _set_groups_visible(self, visible):
        self._text_group.setVisible(visible)
        self._font_group.setVisible(visible)
        self._pos_group.setVisible(visible)
        self._link_group.setVisible(visible)
        self._page_group.setVisible(not visible)

    def load_element(self, element_data):
        """Load an element's data into the properties panel."""
        self._block_signals = True
        self._current_element = element_data
        self._set_groups_visible(True)
        self._title_label.setText(f"Properties — {element_data.get('type', 'text').title()}")

        # Text content
        self._content_input.setPlainText(element_data.get('content', ''))

        # Font
        font_fam = element_data.get('font_family', 'Helvetica')
        idx = self._font_family_combo.findText(font_fam)
        if idx >= 0:
            self._font_family_combo.setCurrentIndex(idx)
        self._font_size_spin.setValue(int(element_data.get('font_size', 14)))

        # Style toggles
        self._bold_btn.setChecked(element_data.get('bold', False))
        self._italic_btn.setChecked(element_data.get('italic', False))
        self._underline_btn.setChecked(element_data.get('underline', False))

        # Color
        color = element_data.get('color', '#1642a8')
        self._color_btn.setStyleSheet(f"background-color: {color}; color: white; border-radius: 4px; font-weight: 600;")

        # Alignment
        align = element_data.get('alignment', 'center')
        idx = self._align_combo.findText(align)
        if idx >= 0:
            self._align_combo.setCurrentIndex(idx)

        # Spacing
        self._letter_spacing_spin.setValue(element_data.get('letter_spacing', 0))
        self._line_height_spin.setValue(element_data.get('line_height', 1.2))

        # Position
        self._x_spin.setValue(element_data.get('x', 0))
        self._y_spin.setValue(element_data.get('y', 0))
        self._w_spin.setValue(element_data.get('width', 200))
        self._h_spin.setValue(element_data.get('height', 30))

        # Opacity
        opacity_pct = int(element_data.get('opacity', 1.0) * 100)
        self._opacity_slider.setValue(opacity_pct)
        self._opacity_val_label.setText(f"{opacity_pct}%")

        # Hyperlink
        self._hyperlink_input.setText(element_data.get('hyperlink', ''))

        self._block_signals = False

    def clear_selection(self, section_data=None):
        self._current_element = None
        self._set_groups_visible(False)
        self._title_label.setText("Page Properties")
        
        if section_data:
            self.load_page_properties(section_data)

    def load_page_properties(self, section_data):
        self._block_signals = True
        self._page_section_data = section_data
        
        opacity_pct = int(section_data.get('bg_opacity', 1.0) * 100)
        self._bg_opacity_slider.setValue(opacity_pct)
        self._bg_op_val_label.setText(f"{opacity_pct}%")
        
        self._border_spin.setValue(section_data.get('border_thickness', 0.0))
        color = section_data.get('border_color', '#000000')
        self._border_color_btn.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold;")
        
        self._block_signals = False

    def _on_page_prop_changed(self):
        if self._block_signals or not self._page_section_data:
            return
            
        opacity = self._bg_opacity_slider.value() / 100.0
        self._bg_op_val_label.setText(f"{int(opacity * 100)}%")
        self._page_section_data['bg_opacity'] = opacity
        self._page_section_data['border_thickness'] = self._border_spin.value()
        self.page_property_changed.emit()

    def _pick_border_color(self):
        if not self._page_section_data:
            return
        current = QColor(self._page_section_data.get('border_color', '#000000'))
        color = QColorDialog.getColor(current, self, "Select Border Color")
        if color.isValid():
            self._page_section_data['border_color'] = color.name()
            self._border_color_btn.setStyleSheet(f"background-color: {color.name()}; color: white; font-weight: bold;")
            self.page_property_changed.emit()

    def _clear_background(self):
        if not self._page_section_data:
            return
        self._page_section_data['background_image'] = ''
        self.page_property_changed.emit()

    # ── Signal handlers ──

    def _on_content_changed(self):
        if self._block_signals or not self._current_element:
            return
        text = self._content_input.toPlainText()
        self._current_element['content'] = text
        self.property_changed.emit()

    def _on_font_changed(self):
        if self._block_signals or not self._current_element:
            return
        self._current_element['font_family'] = self._font_family_combo.currentText()
        self._current_element['font_size'] = self._font_size_spin.value()
        self.property_changed.emit()

    def _on_style_changed(self):
        if self._block_signals or not self._current_element:
            return
        self._current_element['bold'] = self._bold_btn.isChecked()
        self._current_element['italic'] = self._italic_btn.isChecked()
        self._current_element['underline'] = self._underline_btn.isChecked()
        self.property_changed.emit()

    def _pick_color(self):
        if not self._current_element:
            return
        current = QColor(self._current_element.get('color', '#1642a8'))
        color = QColorDialog.getColor(current, self, "Select Text Color")
        if color.isValid():
            self._current_element['color'] = color.name()
            self._color_btn.setStyleSheet(f"background-color: {color.name()}; color: white; border-radius: 4px; font-weight: 600;")
            self.property_changed.emit()

    def _on_alignment_changed(self, text):
        if self._block_signals or not self._current_element:
            return
        self._current_element['alignment'] = text
        self.property_changed.emit()

    def _on_spacing_changed(self):
        if self._block_signals or not self._current_element:
            return
        self._current_element['letter_spacing'] = self._letter_spacing_spin.value()
        self._current_element['line_height'] = self._line_height_spin.value()
        self.property_changed.emit()

    def _on_pos_changed(self):
        if self._block_signals or not self._current_element:
            return
        self._current_element['x'] = self._x_spin.value()
        self._current_element['y'] = self._y_spin.value()
        self.property_changed.emit()

    def _on_size_changed(self):
        if self._block_signals or not self._current_element:
            return
        self._current_element['width'] = self._w_spin.value()
        self._current_element['height'] = self._h_spin.value()
        self.property_changed.emit()

    def _on_opacity_changed(self, val):
        if self._block_signals or not self._current_element:
            return
        self._opacity_val_label.setText(f"{val}%")
        self._current_element['opacity'] = val / 100.0
        self.property_changed.emit()

    def _on_hyperlink_changed(self, text):
        if self._block_signals or not self._current_element:
            return
        self._current_element['hyperlink'] = text
        self.property_changed.emit()


# ─────────────────────────────────────────────────────────────
#  Body Page Properties Panel (Header/Footer/Layout editor)
# ─────────────────────────────────────────────────────────────
class BodyPropertiesPanel(QWidget):
    """Properties panel specifically for body page (header/footer/layout)."""
    property_changed = pyqtSignal()

    def __init__(self, available_fonts=None, parent=None):
        super().__init__(parent)
        self._available_fonts = available_fonts or []
        self._body_data = {}
        self._block_signals = False
        self.setMinimumWidth(300)
        self.setMaximumWidth(380)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(12)

        title = QLabel("Body Page Settings")
        title.setStyleSheet(f"color: {PALETTE['text_primary']}; font-size: 12pt; font-weight: 700;")
        cl.addWidget(title)

        # ── HEADER GROUP ──
        h_group = QGroupBox("Header")
        h_group.setStyleSheet(self._group_style())
        h_lay = QVBoxLayout(h_group)
        h_lay.setSpacing(6)

        self._h_enabled = QCheckBox("Enable Header")
        self._h_enabled.stateChanged.connect(self._emit_change)
        h_lay.addWidget(self._h_enabled)

        h_row1 = QHBoxLayout()
        h_row1.addWidget(QLabel("Text:"))
        self._h_text = QLineEdit()
        self._h_text.setMinimumHeight(28)
        self._h_text.textChanged.connect(self._emit_change)
        h_row1.addWidget(self._h_text)
        h_lay.addLayout(h_row1)

        h_row2 = QHBoxLayout()
        h_row2.addWidget(QLabel("URL:"))
        self._h_url = QLineEdit()
        self._h_url.setPlaceholderText("https://...")
        self._h_url.setMinimumHeight(28)
        self._h_url.textChanged.connect(self._emit_change)
        h_row2.addWidget(self._h_url)
        h_lay.addLayout(h_row2)

        h_row3 = QHBoxLayout()
        h_row3.addWidget(QLabel("Font:"))
        self._h_font = QComboBox()
        self._h_font.addItems(self._available_fonts)
        self._h_font.setMinimumHeight(28)
        self._h_font.currentTextChanged.connect(self._emit_change)
        h_row3.addWidget(self._h_font)
        h_row3.addWidget(QLabel("Size:"))
        self._h_size = QSpinBox()
        self._h_size.setRange(4, 24)
        self._h_size.setMinimumHeight(28)
        self._h_size.valueChanged.connect(self._emit_change)
        h_row3.addWidget(self._h_size)
        h_lay.addLayout(h_row3)

        h_row4 = QHBoxLayout()
        self._h_color_btn = QPushButton("Color")
        self._h_color_btn.setMinimumHeight(28)
        self._h_color_btn.clicked.connect(lambda: self._pick_color('header'))
        h_row4.addWidget(self._h_color_btn)
        h_row4.addWidget(QLabel("Align:"))
        self._h_align = QComboBox()
        self._h_align.addItems(["left", "center", "right"])
        self._h_align.setMinimumHeight(28)
        self._h_align.currentTextChanged.connect(self._emit_change)
        h_row4.addWidget(self._h_align)
        self._h_line_cb = QCheckBox("Show Line")
        self._h_line_cb.stateChanged.connect(self._emit_change)
        h_row4.addWidget(self._h_line_cb)
        h_lay.addLayout(h_row4)

        h_row5 = QHBoxLayout()
        h_row5.addWidget(QLabel("Weight:"))
        self._h_weight = QComboBox()
        self._h_weight.addItems(["normal", "bold"])
        self._h_weight.setMinimumHeight(28)
        self._h_weight.currentTextChanged.connect(self._emit_change)
        h_row5.addWidget(self._h_weight)
        h_row5.addWidget(QLabel("Spacing:"))
        self._h_spacing = QDoubleSpinBox()
        self._h_spacing.setRange(-2, 10)
        self._h_spacing.setSingleStep(0.1)
        self._h_spacing.setMinimumHeight(28)
        self._h_spacing.valueChanged.connect(self._emit_change)
        h_row5.addWidget(self._h_spacing)
        h_lay.addLayout(h_row5)

        cl.addWidget(h_group)

        # ── FOOTER GROUP ──
        f_group = QGroupBox("Footer")
        f_group.setStyleSheet(self._group_style())
        f_lay = QVBoxLayout(f_group)
        f_lay.setSpacing(6)

        self._f_enabled = QCheckBox("Enable Footer")
        self._f_enabled.stateChanged.connect(self._emit_change)
        f_lay.addWidget(self._f_enabled)

        f_row1 = QHBoxLayout()
        f_row1.addWidget(QLabel("Text:"))
        self._f_text = QLineEdit()
        self._f_text.setPlaceholderText("Use {page_num} for page number")
        self._f_text.setMinimumHeight(28)
        self._f_text.textChanged.connect(self._emit_change)
        f_row1.addWidget(self._f_text)
        f_lay.addLayout(f_row1)

        f_row2 = QHBoxLayout()
        f_row2.addWidget(QLabel("URL:"))
        self._f_url = QLineEdit()
        self._f_url.setPlaceholderText("https://...")
        self._f_url.setMinimumHeight(28)
        self._f_url.textChanged.connect(self._emit_change)
        f_row2.addWidget(self._f_url)
        f_lay.addLayout(f_row2)

        f_row3 = QHBoxLayout()
        f_row3.addWidget(QLabel("Font:"))
        self._f_font = QComboBox()
        self._f_font.addItems(self._available_fonts)
        self._f_font.setMinimumHeight(28)
        self._f_font.currentTextChanged.connect(self._emit_change)
        f_row3.addWidget(self._f_font)
        f_row3.addWidget(QLabel("Size:"))
        self._f_size = QSpinBox()
        self._f_size.setRange(4, 24)
        self._f_size.setMinimumHeight(28)
        self._f_size.valueChanged.connect(self._emit_change)
        f_row3.addWidget(self._f_size)
        f_lay.addLayout(f_row3)

        f_row4 = QHBoxLayout()
        self._f_color_btn = QPushButton("Color")
        self._f_color_btn.setMinimumHeight(28)
        self._f_color_btn.clicked.connect(lambda: self._pick_color('footer'))
        f_row4.addWidget(self._f_color_btn)
        f_row4.addWidget(QLabel("Align:"))
        self._f_align = QComboBox()
        self._f_align.addItems(["left", "center", "right"])
        self._f_align.setMinimumHeight(28)
        self._f_align.currentTextChanged.connect(self._emit_change)
        f_row4.addWidget(self._f_align)
        self._f_line_cb = QCheckBox("Show Line")
        self._f_line_cb.stateChanged.connect(self._emit_change)
        f_row4.addWidget(self._f_line_cb)
        f_lay.addLayout(f_row4)

        cl.addWidget(f_group)

        # ── LAYOUT GROUP ──
        l_group = QGroupBox("Layout & Content Styling")
        l_group.setStyleSheet(self._group_style())
        l_lay = QVBoxLayout(l_group)
        l_lay.setSpacing(6)

        # Margins
        m_row = QHBoxLayout()
        for lbl, attr in [("Top:", "_l_mt"), ("Bot:", "_l_mb"), ("Left:", "_l_ml"), ("Right:", "_l_mr")]:
            m_row.addWidget(QLabel(lbl))
            sp = QSpinBox()
            sp.setRange(0, 80)
            sp.setMinimumHeight(28)
            sp.valueChanged.connect(self._emit_change)
            setattr(self, attr, sp)
            m_row.addWidget(sp)
        l_lay.addLayout(m_row)

        # Font sizes
        fs_row = QHBoxLayout()
        for lbl, attr in [("Title:", "_l_title_sz"), ("Q:", "_l_q_sz"), ("Opt:", "_l_opt_sz"), ("Exp:", "_l_exp_sz")]:
            fs_row.addWidget(QLabel(lbl))
            sp = QSpinBox()
            sp.setRange(4, 40)
            sp.setMinimumHeight(28)
            sp.valueChanged.connect(self._emit_change)
            setattr(self, attr, sp)
            fs_row.addWidget(sp)
        l_lay.addLayout(fs_row)

        # Explanation box
        exp_row = QHBoxLayout()
        exp_row.addWidget(QLabel("Exp Width%:"))
        self._l_exp_width = QSpinBox()
        self._l_exp_width.setRange(10, 60)
        self._l_exp_width.setMinimumHeight(28)
        self._l_exp_width.valueChanged.connect(self._emit_change)
        exp_row.addWidget(self._l_exp_width)

        exp_row.addWidget(QLabel("Padding:"))
        self._l_exp_pad = QSpinBox()
        self._l_exp_pad.setRange(0, 30)
        self._l_exp_pad.setMinimumHeight(28)
        self._l_exp_pad.valueChanged.connect(self._emit_change)
        exp_row.addWidget(self._l_exp_pad)
        l_lay.addLayout(exp_row)

        # Text Colors
        color_row1 = QHBoxLayout()
        self._l_title_color_btn = QPushButton("Title Color")
        self._l_title_color_btn.setMinimumHeight(28)
        self._l_title_color_btn.clicked.connect(lambda: self._pick_color('title_color'))
        color_row1.addWidget(self._l_title_color_btn)

        self._l_q_color_btn = QPushButton("Q Color")
        self._l_q_color_btn.setMinimumHeight(28)
        self._l_q_color_btn.clicked.connect(lambda: self._pick_color('q_color'))
        color_row1.addWidget(self._l_q_color_btn)

        self._l_opt_color_btn = QPushButton("Opt Color")
        self._l_opt_color_btn.setMinimumHeight(28)
        self._l_opt_color_btn.clicked.connect(lambda: self._pick_color('opt_color'))
        color_row1.addWidget(self._l_opt_color_btn)
        l_lay.addLayout(color_row1)

        # Highlight & Bg Colors
        color_row2 = QHBoxLayout()
        self._l_exp_bg_btn = QPushButton("Exp BG")
        self._l_exp_bg_btn.setMinimumHeight(28)
        self._l_exp_bg_btn.clicked.connect(lambda: self._pick_color('exp_bg'))
        color_row2.addWidget(self._l_exp_bg_btn)

        self._l_exp_text_btn = QPushButton("Exp Text")
        self._l_exp_text_btn.setMinimumHeight(28)
        self._l_exp_text_btn.clicked.connect(lambda: self._pick_color('exp_text'))
        color_row2.addWidget(self._l_exp_text_btn)

        self._l_highlight_btn = QPushButton("Correct HL")
        self._l_highlight_btn.setMinimumHeight(28)
        self._l_highlight_btn.clicked.connect(lambda: self._pick_color('highlight'))
        color_row2.addWidget(self._l_highlight_btn)
        l_lay.addLayout(color_row2)

        # Q spacing
        qs_row = QHBoxLayout()
        qs_row.addWidget(QLabel("Q Spacing:"))
        self._l_q_spacing = QSpinBox()
        self._l_q_spacing.setRange(1, 30)
        self._l_q_spacing.setMinimumHeight(28)
        self._l_q_spacing.valueChanged.connect(self._emit_change)
        qs_row.addWidget(self._l_q_spacing)
        qs_row.addWidget(QLabel("Opt Indent:"))
        self._l_opt_indent = QSpinBox()
        self._l_opt_indent.setRange(0, 30)
        self._l_opt_indent.setMinimumHeight(28)
        self._l_opt_indent.valueChanged.connect(self._emit_change)
        qs_row.addWidget(self._l_opt_indent)
        l_lay.addLayout(qs_row)

        cl.addWidget(l_group)
        cl.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _group_style(self):
        return f"""
            QGroupBox {{
                font-weight: 600; font-size: 9.5pt;
                color: {PALETTE['text_secondary']};
                border: 1.5px solid {PALETTE['border']};
                border-radius: 8px; margin-top: 8px; padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 12px;
                padding: 0 6px; background: {PALETTE['surface']};
            }}
        """

    def load_body(self, body_data):
        """Load body settings into the panel."""
        self._block_signals = True
        self._body_data = body_data

        h = body_data.get('header', {})
        self._h_enabled.setChecked(h.get('enabled', True))
        self._h_text.setText(h.get('text', ''))
        self._h_url.setText(h.get('url', ''))
        idx = self._h_font.findText(h.get('font_family', 'Helvetica-Bold'))
        if idx >= 0: self._h_font.setCurrentIndex(idx)
        self._h_size.setValue(int(h.get('font_size', 8)))
        self._h_color_btn.setStyleSheet(f"background-color: {h.get('color', '#1642a8')}; color: white; border-radius: 4px;")
        idx = self._h_align.findText(h.get('alignment', 'right'))
        if idx >= 0: self._h_align.setCurrentIndex(idx)
        self._h_line_cb.setChecked(h.get('show_line', True))
        idx = self._h_weight.findText(h.get('font_weight', 'bold'))
        if idx >= 0: self._h_weight.setCurrentIndex(idx)
        self._h_spacing.setValue(h.get('letter_spacing', 0.3))

        f = body_data.get('footer', {})
        self._f_enabled.setChecked(f.get('enabled', True))
        self._f_text.setText(f.get('text', ''))
        self._f_url.setText(f.get('url', ''))
        idx = self._f_font.findText(f.get('font_family', 'Helvetica'))
        if idx >= 0: self._f_font.setCurrentIndex(idx)
        self._f_size.setValue(int(f.get('font_size', 8)))
        self._f_color_btn.setStyleSheet(f"background-color: {f.get('color', '#6b7280')}; color: white; border-radius: 4px;")
        idx = self._f_align.findText(f.get('alignment', 'center'))
        if idx >= 0: self._f_align.setCurrentIndex(idx)
        self._f_line_cb.setChecked(f.get('show_line', True))

        lay = body_data.get('layout', {})
        self._l_mt.setValue(int(lay.get('margin_top', 20)))
        self._l_mb.setValue(int(lay.get('margin_bottom', 25)))
        self._l_ml.setValue(int(lay.get('margin_left', 20)))
        self._l_mr.setValue(int(lay.get('margin_right', 20)))
        self._l_title_sz.setValue(int(lay.get('title_size', 18)))
        self._l_q_sz.setValue(int(lay.get('question_size', 10)))
        self._l_opt_sz.setValue(int(lay.get('option_size', 9.5)))
        self._l_exp_sz.setValue(int(lay.get('explanation_size', 9)))
        self._l_exp_width.setValue(int(lay.get('explanation_width_percent', 35)))
        self._l_exp_pad.setValue(int(lay.get('explanation_padding', 6)))
        self._l_q_spacing.setValue(int(lay.get('question_spacing', 6)))
        self._l_opt_indent.setValue(int(lay.get('option_indent', 8)))

        self._l_title_color_btn.setStyleSheet(f"background-color: {lay.get('title_color', '#1642a8')}; color: white; border-radius: 4px;")
        self._l_q_color_btn.setStyleSheet(f"background-color: {lay.get('question_color', '#1642a8')}; color: white; border-radius: 4px;")
        self._l_opt_color_btn.setStyleSheet(f"background-color: {lay.get('option_color', '#374151')}; color: white; border-radius: 4px;")
        self._l_exp_bg_btn.setStyleSheet(f"background-color: {lay.get('explanation_bg_color', '#eff6ff')}; border-radius: 4px;")
        self._l_exp_text_btn.setStyleSheet(f"background-color: {lay.get('explanation_text_color', '#1e293b')}; color: white; border-radius: 4px;")
        self._l_highlight_btn.setStyleSheet(f"background-color: {lay.get('correct_highlight_color', '#fef08a')}; border-radius: 4px;")

        self._block_signals = False

    def get_body_data(self):
        """Extract current body data from the panel widgets."""
        if not self._body_data:
            return {}

        h = self._body_data.get('header', {})
        h['enabled'] = self._h_enabled.isChecked()
        h['text'] = self._h_text.text()
        h['url'] = self._h_url.text()
        h['font_family'] = self._h_font.currentText()
        h['font_size'] = self._h_size.value()
        h['alignment'] = self._h_align.currentText()
        h['show_line'] = self._h_line_cb.isChecked()
        h['font_weight'] = self._h_weight.currentText()
        h['letter_spacing'] = self._h_spacing.value()

        f = self._body_data.get('footer', {})
        f['enabled'] = self._f_enabled.isChecked()
        f['text'] = self._f_text.text()
        f['url'] = self._f_url.text()
        f['font_family'] = self._f_font.currentText()
        f['font_size'] = self._f_size.value()
        f['alignment'] = self._f_align.currentText()
        f['show_line'] = self._f_line_cb.isChecked()

        lay = self._body_data.get('layout', {})
        lay['margin_top'] = self._l_mt.value()
        lay['margin_bottom'] = self._l_mb.value()
        lay['margin_left'] = self._l_ml.value()
        lay['margin_right'] = self._l_mr.value()
        lay['title_size'] = self._l_title_sz.value()
        lay['question_size'] = self._l_q_sz.value()
        lay['option_size'] = self._l_opt_sz.value()
        lay['explanation_size'] = self._l_exp_sz.value()
        lay['explanation_width_percent'] = self._l_exp_width.value()
        lay['explanation_padding'] = self._l_exp_pad.value()
        lay['question_spacing'] = self._l_q_spacing.value()
        lay['option_indent'] = self._l_opt_indent.value()

        self._body_data['header'] = h
        self._body_data['footer'] = f
        self._body_data['layout'] = lay
        return self._body_data

    def _pick_color(self, target):
        color = QColorDialog.getColor(Qt.white, self, f"Select {target} Color")
        if not color.isValid():
            return

        hex_c = color.name()
        lay = self._body_data.get('layout', {})
        h = self._body_data.get('header', {})
        f = self._body_data.get('footer', {})

        if target == 'header':
            h['color'] = hex_c
            self._h_color_btn.setStyleSheet(f"background-color: {hex_c}; color: white; border-radius: 4px;")
        elif target == 'footer':
            f['color'] = hex_c
            self._f_color_btn.setStyleSheet(f"background-color: {hex_c}; color: white; border-radius: 4px;")
        elif target == 'exp_bg':
            lay['explanation_bg_color'] = hex_c
            self._l_exp_bg_btn.setStyleSheet(f"background-color: {hex_c}; border-radius: 4px;")
        elif target == 'exp_text':
            lay['explanation_text_color'] = hex_c
            self._l_exp_text_btn.setStyleSheet(f"background-color: {hex_c}; color: white; border-radius: 4px;")
        elif target == 'highlight':
            lay['correct_highlight_color'] = hex_c
            self._l_highlight_btn.setStyleSheet(f"background-color: {hex_c}; border-radius: 4px;")
        elif target == 'title_color':
            lay['title_color'] = hex_c
            self._l_title_color_btn.setStyleSheet(f"background-color: {hex_c}; color: white; border-radius: 4px;")
        elif target == 'q_color':
            lay['question_color'] = hex_c
            self._l_q_color_btn.setStyleSheet(f"background-color: {hex_c}; color: white; border-radius: 4px;")
        elif target == 'opt_color':
            lay['option_color'] = hex_c
            self._l_opt_color_btn.setStyleSheet(f"background-color: {hex_c}; color: white; border-radius: 4px;")

        self._body_data['header'] = h
        self._body_data['footer'] = f
        self._body_data['layout'] = lay
        self._emit_change()

    def _emit_change(self, *args):
        if not self._block_signals:
            self.property_changed.emit()


# ─────────────────────────────────────────────────────────────
#  Main Edit PDF Tab (Complete Replacement)
# ─────────────────────────────────────────────────────────────
class EditPDFTab(QWidget):
    """Advanced visual PDF template editor with live preview."""

    def __init__(self):
        super().__init__()
        self.settings_mgr = PDFEditorSettingsManager()
        self._current_doc_type = "mcq"
        self._current_section = "first_page"
        self._available_fonts = FONT_FAMILIES.copy()
        self._available_fonts.extend([fam for fam in _load_editor_fonts() if fam not in self._available_fonts])
        self._build_ui()
        self._load_current_view()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Toolbar ──
        toolbar = QWidget()
        toolbar.setStyleSheet(f"""
            QWidget {{
                background: {PALETTE['surface']};
                border-bottom: 1.5px solid {PALETTE['border']};
            }}
        """)
        toolbar.setFixedHeight(56)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 8, 16, 8)
        tb_layout.setSpacing(12)

        # Doc type selector
        type_label = QLabel("Document:")
        type_label.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 9.5pt; font-weight: 600; border: none;")
        tb_layout.addWidget(type_label)

        self._doc_type_combo = QComboBox()
        self._doc_type_combo.addItems(["MCQs", "Short Notes"])
        self._doc_type_combo.setMinimumHeight(34)
        self._doc_type_combo.setMinimumWidth(140)
        self._doc_type_combo.setStyleSheet(f"""
            QComboBox {{
                background: {PALETTE['bg']};
                border: 1.5px solid {PALETTE['border']};
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 600;
                font-size: 10pt;
            }}
            QComboBox:hover {{ border-color: {PALETTE['accent']}; }}
        """)
        self._doc_type_combo.currentIndexChanged.connect(self._on_doc_type_changed)
        tb_layout.addWidget(self._doc_type_combo)

        tb_layout.addSpacing(20)

        # Section tabs
        self._section_btns = []
        for section_id, label in [("first_page", "📄 First Page"), ("body", "📝 Body Pages"), ("last_page", "📄 Last Page")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            btn.setMinimumWidth(120)
            btn.setProperty("section_id", section_id)
            btn.clicked.connect(lambda checked, sid=section_id: self._on_section_changed(sid))
            self._section_btns.append(btn)
            tb_layout.addWidget(btn)

        tb_layout.addStretch()

        # Element toolbar buttons
        self._add_text_btn = QPushButton("+ Text")
        self._add_text_btn.setMinimumHeight(30)
        self._add_text_btn.setStyleSheet(self._action_btn_style())
        self._add_text_btn.clicked.connect(self._add_text_element)
        tb_layout.addWidget(self._add_text_btn)

        self._add_img_btn = QPushButton("+ Image")
        self._add_img_btn.setMinimumHeight(30)
        self._add_img_btn.setStyleSheet(self._action_btn_style())
        self._add_img_btn.clicked.connect(self._add_image_element)
        tb_layout.addWidget(self._add_img_btn)

        self._del_btn = QPushButton("🗑 Delete")
        self._del_btn.setMinimumHeight(30)
        self._del_btn.setStyleSheet(f"""
            QPushButton {{
                background: #fff0f0; color: {PALETTE['error']};
                border: 1.5px solid {PALETTE['error']}; border-radius: 6px;
                padding: 4px 12px; font-size: 9pt; font-weight: 500;
            }}
            QPushButton:hover {{ background: {PALETTE['error']}; color: white; }}
        """)
        self._del_btn.clicked.connect(self._delete_element)
        tb_layout.addWidget(self._del_btn)

        # Background image btn
        self._bg_btn = QPushButton("🖼 Background")
        self._bg_btn.setMinimumHeight(30)
        self._bg_btn.setStyleSheet(self._action_btn_style())
        self._bg_btn.clicked.connect(self._set_background)
        tb_layout.addWidget(self._bg_btn)

        # Copy Design Btn
        self._copy_btn = QPushButton("📄 Copy Design To ▼")
        self._copy_btn.setMinimumHeight(30)
        self._copy_btn.setStyleSheet(self._action_btn_style())
        self._copy_menu = QMenu(self._copy_btn)
        
        for tgt_type, tgt_name in [('mcq', 'MCQs'), ('notes', 'Short Notes')]:
            for tgt_sec, sec_name in [('first_page', 'First Page'), ('last_page', 'Last Page')]:
                action = QAction(f"{tgt_name} - {sec_name}", self)
                action.triggered.connect(lambda checked, t=tgt_type, s=tgt_sec: self._copy_layout_to(t, s))
                self._copy_menu.addAction(action)
                
        self._copy_btn.setMenu(self._copy_menu)
        tb_layout.addWidget(self._copy_btn)

        # Save button
        self._save_btn = QPushButton("💾 Save All")
        self._save_btn.setMinimumHeight(34)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['accent']}; color: white;
                border: none; border-radius: 6px;
                padding: 6px 18px; font-size: 10pt; font-weight: 600;
            }}
            QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}
        """)
        self._save_btn.clicked.connect(self._save_all)
        tb_layout.addWidget(self._save_btn)

        # Test PDF button
        self._test_btn = QPushButton("🧪 Test PDF")
        self._test_btn.setMinimumHeight(34)
        self._test_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['success']}; color: white;
                border: none; border-radius: 6px;
                padding: 6px 18px; font-size: 10pt; font-weight: 600;
            }}
            QPushButton:hover {{ background: #2f9e44; }}
        """)
        self._test_btn.clicked.connect(self._test_pdf)
        tb_layout.addWidget(self._test_btn)

        root.addWidget(toolbar)

        # ── Main Content (Canvas + Properties) ──
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(12)

        # Canvas (left)
        self._canvas = PDFCanvasWidget()
        self._canvas.element_selected.connect(self._on_element_selected)
        self._canvas.element_deselected.connect(self._on_element_deselected)

        # Properties panels
        self._props_panel = PropertiesPanel(getattr(self, '_available_fonts', []))
        self._props_panel.property_changed.connect(self._on_property_changed)
        self._props_panel.page_property_changed.connect(self._on_property_changed)

        self._body_props_panel = BodyPropertiesPanel(getattr(self, '_available_fonts', []))
        self._body_props_panel.property_changed.connect(self._on_body_property_changed)

        # Right panel stack (show one at a time)
        self._right_panel = QWidget()
        self._right_layout = QVBoxLayout(self._right_panel)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.addWidget(self._props_panel)
        self._right_layout.addWidget(self._body_props_panel)

        content_layout.addWidget(self._canvas, 3)
        content_layout.addWidget(self._right_panel, 1)

        root.addWidget(content_widget, 1)

        # Initial state
        self._update_section_btn_styles("first_page")
        self._update_toolbar_visibility()

    def _action_btn_style(self):
        return f"""
            QPushButton {{
                background: {PALETTE['surface']}; color: {PALETTE['text_secondary']};
                border: 1.5px solid {PALETTE['border']}; border-radius: 6px;
                padding: 4px 12px; font-size: 9pt; font-weight: 500;
            }}
            QPushButton:hover {{
                border-color: {PALETTE['accent']}; color: {PALETTE['accent']};
                background: #f0f4ff;
            }}
        """

    def _update_section_btn_styles(self, active_section):
        for btn in self._section_btns:
            sid = btn.property("section_id")
            is_active = (sid == active_section)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {PALETTE['accent']}; color: white;
                        border: none; border-radius: 6px;
                        padding: 6px 14px; font-size: 9.5pt; font-weight: 600;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {PALETTE['surface']}; color: {PALETTE['text_secondary']};
                        border: 1.5px solid {PALETTE['border']}; border-radius: 6px;
                        padding: 6px 14px; font-size: 9.5pt; font-weight: 500;
                    }}
                    QPushButton:hover {{
                        border-color: {PALETTE['accent']}; color: {PALETTE['accent']};
                    }}
                """)

    def _update_toolbar_visibility(self):
        """Show/hide element buttons based on section type."""
        is_page = self._current_section in ("first_page", "last_page")
        self._add_text_btn.setVisible(is_page)
        self._add_img_btn.setVisible(is_page)
        self._del_btn.setVisible(is_page)
        self._bg_btn.setVisible(is_page)
        self._copy_btn.setVisible(is_page)

        # Show correct properties panel
        self._props_panel.setVisible(is_page)
        self._body_props_panel.setVisible(not is_page)

    # ── Navigation ──

    def _on_doc_type_changed(self, idx):
        types = ["mcq", "notes"]
        self._current_doc_type = types[idx] if idx < len(types) else "mcq"
        self._load_current_view()

    def _on_section_changed(self, section_id):
        self._current_section = section_id
        self._update_section_btn_styles(section_id)
        self._update_toolbar_visibility()
        self._load_current_view()

    # ── Loading ──

    def _load_current_view(self):
        """Load the appropriate view for current doc_type + section."""
        section = self._current_section
        doc_type = self._current_doc_type
        section_data = self.settings_mgr.get_section(doc_type, section)

        if section in ("first_page", "last_page"):
            self._canvas.render_page(section_data, section)
            self._props_panel.clear_selection(section_data)
        else:
            self._canvas.render_body_page(section_data, self._current_doc_type)
            self._body_props_panel.load_body(section_data)

    # ── Element Actions ──

    def _add_text_element(self):
        if self._current_section not in ("first_page", "last_page"):
            return
        new_el = {
            "id": f"el_{uuid.uuid4().hex[:8]}",
            "type": "text",
            "content": "New Text Element",
            "x": 297, "y": 420,
            "width": 300, "height": 35,
            "font_family": "Helvetica",
            "font_size": 14,
            "color": "#1a1a2e",
            "alignment": "center",
            "bold": False, "italic": False, "underline": False,
            "letter_spacing": 0, "line_height": 1.2,
            "hyperlink": "", "opacity": 1.0
        }
        self._canvas.add_element(new_el)
        # Update settings
        elements = self._canvas.get_elements()
        self.settings_mgr.set_elements(self._current_doc_type, self._current_section, elements)

    def _add_image_element(self):
        if self._current_section not in ("first_page", "last_page"):
            return
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.svg)")
        if not path:
            return
        new_el = {
            "id": f"img_{uuid.uuid4().hex[:8]}",
            "type": "image",
            "path": path,
            "x": 297, "y": 200,
            "width": 150, "height": 150,
            "opacity": 1.0
        }
        self._canvas.add_element(new_el)
        elements = self._canvas.get_elements()
        self.settings_mgr.set_elements(self._current_doc_type, self._current_section, elements)

    def _delete_element(self):
        self._canvas.delete_selected()
        elements = self._canvas.get_elements()
        self.settings_mgr.set_elements(self._current_doc_type, self._current_section, elements)

    def _set_background(self):
        if self._current_section not in ("first_page", "last_page"):
            return
            
        reply = QMessageBox.question(self, "Background Image", 
                                     "Do you want to set a new background image?\nSelect 'Yes' to choose an image.\nSelect 'No' to remove the current background.",
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Yes:
            path, _ = QFileDialog.getOpenFileName(self, "Select Background Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if path:
                section_data = self.settings_mgr.get_section(self._current_doc_type, self._current_section)
                section_data['background_image'] = path
                self.settings_mgr.set_section(self._current_doc_type, self._current_section, section_data)
                self._load_current_view()
        elif reply == QMessageBox.No:
            section_data = self.settings_mgr.get_section(self._current_doc_type, self._current_section)
            section_data['background_image'] = ''
            self.settings_mgr.set_section(self._current_doc_type, self._current_section, section_data)
            self._load_current_view()

    def _copy_layout_to(self, target_type, target_section):
        if self._current_section not in ("first_page", "last_page"):
            QMessageBox.warning(self, "Invalid Source", "You can only copy templates from First Page or Last Page.")
            return

        if target_type == self._current_doc_type and target_section == self._current_section:
            return  # Can't copy to itself

        reply = QMessageBox.question(
            self, "Confirm Copy",
            f"This will completely overwrite the design of the {target_type.upper()} {target_section.replace('_', ' ').title()}.\n\nAre you sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            import copy
            import uuid
            
            # Fetch current elements (make sure they are saved to settings_mgr first)
            current_elements = self._canvas.get_elements()
            self.settings_mgr.set_elements(self._current_doc_type, self._current_section, current_elements)
            
            # Get deep copy of current section
            current_data = copy.deepcopy(self.settings_mgr.get_section(self._current_doc_type, self._current_section))
            
            # Assign new UUIDs
            for el in current_data.get('elements', []):
                el['id'] = f"{el.get('type', 'el')}_{uuid.uuid4().hex[:8]}"
            
            # Set to target and save
            self.settings_mgr.set_section(target_type, target_section, current_data)
            self.settings_mgr.save()
            QMessageBox.information(self, "Success", f"Design copied successfully to {target_type.upper()} {target_section.replace('_', ' ').title()}!")

    # ── Property Panel Signals ──

    def _on_element_selected(self, element_data):
        self._props_panel.load_element(element_data)

    def _on_element_deselected(self):
        section_data = self.settings_mgr.get_section(self._current_doc_type, self._current_section)
        self._props_panel.clear_selection(section_data)

    def _on_property_changed(self):
        """When a property changes, refresh the canvas."""
        # Save current elements
        elements = self._canvas.get_elements()
        self.settings_mgr.set_elements(self._current_doc_type, self._current_section, elements)
        # Refresh canvas
        section_data = self.settings_mgr.get_section(self._current_doc_type, self._current_section)
        self._canvas.render_page(section_data, self._current_section)

    def _on_body_property_changed(self):
        """When body properties change, update settings and refresh preview."""
        body_data = self._body_props_panel.get_body_data()
        self.settings_mgr.set_section(self._current_doc_type, "body", body_data)
        self._canvas.render_body_page(body_data, self._current_doc_type)

    # ── Test PDF ──
    def _test_pdf(self):
        """Generate a test PDF using dummy JSON data."""
        # Commit current UI state to in-memory settings_mgr WITHOUT saving to file
        if self._current_section in ("first_page", "last_page"):
            self.settings_mgr.set_elements(self._current_doc_type, self._current_section, self._canvas.get_elements())
        else:
            self.settings_mgr.set_section(self._current_doc_type, "body", self._body_props_panel.get_body_data())

        import pdf_generator
        pdf_generator._EDITOR_SETTINGS_OVERRIDE = self.settings_mgr.settings

        json_path = r"e:\desktop\gemini-json\CS302_handouts_mids_mcqs.json" if self._current_doc_type == "mcq" else r"e:\desktop\gemini-json\CS302_handouts_mids_notes.json"
        out_path = r"C:\Users\zaink\Desktop\Testing_PDF.pdf"
        
        if not os.path.exists(json_path):
            QMessageBox.warning(self, "Error", f"Test JSON not found: {json_path}")
            pdf_generator._EDITOR_SETTINGS_OVERRIDE = None
            return
            
        try:
            if self._current_doc_type == "mcq":
                pdf_generator.generate_mcq_pdf(json_path, out_path, "Testing MCQs")
            else:
                pdf_generator.generate_short_notes_pdf(json_path, out_path, "Testing Notes")
            QMessageBox.information(self, "Success", f"Test PDF generated successfully at:\n{out_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to generate Test PDF:\n{str(e)}")
        finally:
            pdf_generator._EDITOR_SETTINGS_OVERRIDE = None
    # ── Save ──

    def _save_all(self):
        """Save all editor settings to file."""
        # Ensure current elements are saved
        if self._current_section in ("first_page", "last_page"):
            elements = self._canvas.get_elements()
            self.settings_mgr.set_elements(self._current_doc_type, self._current_section, elements)
        else:
            body_data = self._body_props_panel.get_body_data()
            self.settings_mgr.set_section(self._current_doc_type, "body", body_data)

        # Also update legacy pdf_settings.json for backward compat
        self._sync_to_legacy_settings()

        if self.settings_mgr.save():
            QMessageBox.information(self, "Saved", "PDF Editor settings saved successfully!\n\nAll changes will be applied to future PDF generations.")
        else:
            QMessageBox.warning(self, "Error", "Failed to save settings.")

    def _sync_to_legacy_settings(self):
        """Sync editor settings to the legacy pdf_settings.json for backward compatibility."""
        try:
            from pdf_settings import PDFSettingsManager
            legacy = PDFSettingsManager()

            # Get MCQ body settings as the "default" for legacy
            mcq_body = self.settings_mgr.get_section('mcq', 'body')
            mcq_layout = mcq_body.get('layout', {})
            mcq_header = mcq_body.get('header', {})
            mcq_footer = mcq_body.get('footer', {})

            mcq_first = self.settings_mgr.get_section('mcq', 'first_page')
            mcq_last = self.settings_mgr.get_section('mcq', 'last_page')

            legacy_settings = {
                "templates": {
                    "mcq_bg": "",
                    "notes_bg": "",
                    "use_templates": True
                },
                "layout": {
                    "margin_top": mcq_layout.get('margin_top', 20),
                    "margin_bottom": mcq_layout.get('margin_bottom', 25),
                    "margin_left": mcq_layout.get('margin_left', 20),
                    "margin_right": mcq_layout.get('margin_right', 20),
                    "font_family": mcq_layout.get('font_family', 'Helvetica'),
                    "title_size": mcq_layout.get('title_size', 18),
                    "question_size": mcq_layout.get('question_size', 10),
                    "option_size": mcq_layout.get('option_size', 9.5),
                    "explanation_size": mcq_layout.get('explanation_size', 9),
                    "explanation_bg_color": mcq_layout.get('explanation_bg_color', '#eff6ff'),
                    "explanation_text_color": mcq_layout.get('explanation_text_color', '#1e293b'),
                    "explanation_padding": mcq_layout.get('explanation_padding', 6)
                },
                "header": {
                    "enabled": mcq_header.get('enabled', True),
                    "text": mcq_header.get('text', ''),
                    "url": mcq_header.get('url', ''),
                    "color": mcq_header.get('color', '#1642a8'),
                    "font_size": mcq_header.get('font_size', 8),
                    "show_line": mcq_header.get('show_line', True)
                },
                "footer": {
                    "enabled": mcq_footer.get('enabled', True),
                    "text": mcq_footer.get('text', '— {page_num} —'),
                    "url": mcq_footer.get('url', ''),
                    "color": mcq_footer.get('color', '#6b7280'),
                    "font_size": mcq_footer.get('font_size', 8),
                    "show_line": mcq_footer.get('show_line', True)
                },
                "first_page": {
                    "enabled": mcq_first.get('enabled', True),
                    "content_text": mcq_first.get('elements', [{}])[0].get('content', '') if mcq_first.get('elements') else '',
                    "bg_image": mcq_first.get('background_image', '')
                },
                "last_page": {
                    "enabled": mcq_last.get('enabled', True),
                    "content_text": mcq_last.get('elements', [{}])[0].get('content', '') if mcq_last.get('elements') else '',
                    "bg_image": mcq_last.get('background_image', '')
                }
            }
            legacy.save_settings(legacy_settings)
        except Exception as e:
            print(f"[PDFEditor] Legacy sync error: {e}")
