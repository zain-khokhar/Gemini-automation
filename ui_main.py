"""
PDF MCQ Extraction Tool — Redesigned UI
Modern, minimal, premium-feeling interface with tabbed navigation.
"""

import sys
import os
import json
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
    QProgressBar, QFrame, QRadioButton, QButtonGroup,
    QSpinBox, QScrollArea, QSizePolicy, QComboBox, QListWidget,
    QListWidgetItem, QCheckBox, QTabWidget, QMessageBox,
    QAbstractItemView, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QToolButton, QGroupBox, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QTextCursor, QColor, QIcon, QPalette

from processing_thread import ProcessingThread, BatchProcessingThread
from state_manager import StateManager
from folder_organizer import scan_root_folder


# ─────────────────────────────────────────────────────────────
#  Colour palette & global stylesheet
# ─────────────────────────────────────────────────────────────
PALETTE = {
    "bg":          "#f7f8fa",
    "surface":     "#ffffff",
    "border":      "#e4e7ed",
    "border_focus":"#4361ee",
    "navy":        "#1a1a2e",
    "navy_mid":    "#16213e",
    "accent":      "#4361ee",
    "accent_hover":"#3451d1",
    "text_primary":"#1a1a2e",
    "text_secondary":"#5a6478",
    "text_muted":  "#9aa3b2",
    "success":     "#22c55e",
    "warning":     "#f59e0b",
    "error":       "#ef4444",
    "info":        "#4361ee",
    "tab_active":  "#1a1a2e",
    "tab_inactive":"#9aa3b2",
    "btn_primary_bg":    "#4361ee",
    "btn_primary_text":  "#ffffff",
    "btn_danger_bg":     "#ef4444",
    "btn_warning_bg":    "#f59e0b",
    "btn_success_bg":    "#22c55e",
    "btn_neutral_bg":    "#e4e7ed",
    "btn_neutral_text":  "#1a1a2e",
    "row_hover":   "#f0f4ff",
    "row_alt":     "#f9fafc",
}


APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {PALETTE['bg']};
    color: {PALETTE['text_primary']};
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 10pt;
}}

/* ── Tab bar ── */
QTabWidget::pane {{
    border: none;
    background: {PALETTE['bg']};
}}
QTabBar {{
    background: {PALETTE['navy']};
    border: none;
}}
QTabBar::tab {{
    background: {PALETTE['navy']};
    color: {PALETTE['tab_inactive']};
    padding: 10px 28px;
    font-size: 10pt;
    font-weight: 500;
    border: none;
    min-width: 130px;
}}
QTabBar::tab:selected {{
    color: #ffffff;
    border-bottom: 3px solid {PALETTE['accent']};
    background: {PALETTE['navy_mid']};
}}
QTabBar::tab:hover:!selected {{
    color: #ccccdd;
    background: {PALETTE['navy_mid']};
}}

/* ── Cards / surfaces ── */
QFrame#card {{
    background: {PALETTE['surface']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
}}

/* ── Inputs ── */
QLineEdit, QTextEdit, QSpinBox {{
    background: {PALETTE['surface']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 7px;
    padding: 6px 10px;
    color: {PALETTE['text_primary']};
    selection-background-color: {PALETTE['accent']};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
    border: 1.5px solid {PALETTE['border_focus']};
    outline: none;
}}
QLineEdit::placeholder {{
    color: {PALETTE['text_muted']};
}}

/* ── ComboBox (dropdown button) ── */
QComboBox {{
    background: {PALETTE['surface']};
    border: 2px solid {PALETTE['border']};
    border-radius: 7px;
    padding: 6px 12px;
    color: {PALETTE['text_primary']};
    font-weight: 500;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {PALETTE['accent']};
    background: {PALETTE['row_hover']};
}}
QComboBox:focus {{
    border: 2px solid {PALETTE['border_focus']};
    outline: none;
}}
QComboBox::drop-down {{
    border: none;
    border-left: 1.5px solid {PALETTE['border']};
    width: 28px;
    background: {PALETTE['bg']};
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}
QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}
QComboBox QAbstractItemView {{
    background: {PALETTE['surface']};
    border: 2px solid {PALETTE['border']};
    border-radius: 7px;
    selection-background-color: {PALETTE['row_hover']};
    selection-color: {PALETTE['text_primary']};
    padding: 4px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {PALETTE['btn_neutral_bg']};
    color: {PALETTE['btn_neutral_text']};
    border: none;
    border-radius: 7px;
    padding: 7px 18px;
    font-size: 10pt;
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: #d8dce6;
}}
QPushButton:disabled {{
    background-color: {PALETTE['border']};
    color: {PALETTE['text_muted']};
}}

/* Primary action */
QPushButton#primary {{
    background-color: {PALETTE['btn_primary_bg']};
    color: {PALETTE['btn_primary_text']};
}}
QPushButton#primary:hover {{
    background-color: {PALETTE['accent_hover']};
}}
QPushButton#primary:disabled {{
    background-color: #a5b4fc;
}}

/* Danger */
QPushButton#danger {{
    background-color: {PALETTE['btn_danger_bg']};
    color: white;
}}
QPushButton#danger:hover {{
    background-color: #dc2626;
}}

/* Warning */
QPushButton#warning {{
    background-color: {PALETTE['btn_warning_bg']};
    color: white;
}}
QPushButton#warning:hover {{
    background-color: #d97706;
}}

/* Success */
QPushButton#success {{
    background-color: {PALETTE['btn_success_bg']};
    color: white;
}}
QPushButton#success:hover {{
    background-color: #16a34a;
}}

/* ── List widget ── */
QListWidget {{
    background: {PALETTE['surface']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 7px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {PALETTE['bg']};
    color: {PALETTE['text_primary']};
}}
QListWidget::item:alternate {{
    background: {PALETTE['row_alt']};
}}
QListWidget::item:selected {{
    background: {PALETTE['row_hover']};
    color: {PALETTE['accent']};
}}
QListWidget::item:hover {{
    background: {PALETTE['row_hover']};
}}

/* ── Table widget ── */
QTableWidget {{
    background: {PALETTE['surface']};
    border: 1.5px solid {PALETTE['border']};
    border-radius: 7px;
    gridline-color: {PALETTE['border']};
    outline: none;
}}
QTableWidget::item {{
    padding: 5px 8px;
    color: {PALETTE['text_primary']};
}}
QTableWidget::item:selected {{
    background: {PALETTE['row_hover']};
    color: {PALETTE['accent']};
}}
QHeaderView::section {{
    background: {PALETTE['bg']};
    color: {PALETTE['text_secondary']};
    border: none;
    border-bottom: 1.5px solid {PALETTE['border']};
    padding: 6px 8px;
    font-size: 9pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* ── Progress bar ── */
QProgressBar {{
    background: {PALETTE['border']};
    border: none;
    border-radius: 5px;
    height: 6px;
    text-align: center;
    font-size: 8pt;
    color: {PALETTE['text_secondary']};
}}
QProgressBar::chunk {{
    background: {PALETTE['accent']};
    border-radius: 5px;
}}

/* ── Scrollbar ── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {PALETTE['border']};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {PALETTE['text_muted']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}
QScrollBar::handle:horizontal {{
    background: {PALETTE['border']};
    border-radius: 4px;
}}

/* ── Radio / Checkbox ── */
QRadioButton, QCheckBox {{
    color: {PALETTE['text_primary']};
    spacing: 6px;
}}
QRadioButton::indicator, QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1.5px solid {PALETTE['border']};
    border-radius: 8px;
    background: {PALETTE['surface']};
}}
QRadioButton::indicator:checked {{
    background: {PALETTE['accent']};
    border-color: {PALETTE['accent']};
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QCheckBox::indicator:checked {{
    background: {PALETTE['accent']};
    border-color: {PALETTE['accent']};
}}

/* ── Tooltip ── */
QToolTip {{
    background: {PALETTE['navy']};
    color: white;
    border: none;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 9pt;
}}
"""


def make_card(layout_type='v', margins=(16, 14, 16, 14), spacing=10):
    """Create a white card frame with a layout"""
    frame = QFrame()
    frame.setObjectName("card")
    if layout_type == 'v':
        layout = QVBoxLayout(frame)
    else:
        layout = QHBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


def label_secondary(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 9pt; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase;")
    return lbl


def label_muted(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 9pt;")
    return lbl


def divider():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f"color: {PALETTE['border']}; background: {PALETTE['border']}; border: none; max-height: 1px;")
    return line


# ─────────────────────────────────────────────────────────────
#  PDF Generator Worker Thread
# ─────────────────────────────────────────────────────────────
class PDFGenThread(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, json_paths, output_dir=None):
        super().__init__()
        self.json_paths = json_paths
        self.output_dir = output_dir

    def run(self):
        try:
            from pdf_generator import generate_pdf_from_json
            total = len(self.json_paths)
            for i, json_path in enumerate(self.json_paths, 1):
                self.log_signal.emit(f"Generating PDF {i}/{total}: {Path(json_path).name}", "info")
                try:
                    out_path = None
                    if self.output_dir:
                        out_name = Path(json_path).stem + ".pdf"
                        out_path = str(Path(self.output_dir) / out_name)
                    generated = generate_pdf_from_json(json_path, out_path)
                    self.log_signal.emit(f"  Saved: {generated}", "success")
                except Exception as e:
                    self.log_signal.emit(f"  Failed: {str(e)}", "error")
            self.finished_signal.emit(True, f"Generated {total} PDF(s)")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


# ─────────────────────────────────────────────────────────────
#  PROCESSING TAB
# ─────────────────────────────────────────────────────────────
class ProcessingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.processing_thread = None
        self.state_manager = StateManager()
        self.all_pdfs = []           # flat list of all PDF paths
        self.filtered_pdfs = []      # currently shown in list
        self.categories = {}         # {category_name: [pdf_paths]}
        self._build_ui()
        self._load_root_folder_from_config()
        self._load_last_state()

    # ── Config helpers ────────────────────────────────────────

    def _read_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_config_key(self, key, value):
        try:
            config = self._read_config()
            config[key] = value
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Config write failed: {e}")

    # ── Build UI ──────────────────────────────────────────────

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        # ── Root folder card ──────────────────────────────────
        folder_card, folder_layout = make_card('h', (14, 12, 14, 12), 10)
        folder_layout.addWidget(label_secondary("Root Folder"))

        self.root_path_label = QLabel("No folder selected")
        self.root_path_label.setStyleSheet(
            f"color: {PALETTE['text_primary']}; font-size: 9.5pt; "
            f"background: {PALETTE['bg']}; border-radius: 6px; padding: 5px 10px;"
        )
        self.root_path_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.root_path_label.setWordWrap(False)
        self.root_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        folder_layout.addWidget(self.root_path_label, 1)

        self.change_root_btn = QPushButton("  Change  ")
        self.change_root_btn.setMinimumWidth(95)
        self.change_root_btn.setFixedHeight(32)
        self.change_root_btn.clicked.connect(self._browse_root_folder)
        folder_layout.addWidget(self.change_root_btn)

        self.refresh_btn = QPushButton("  Refresh  ")
        self.refresh_btn.setMinimumWidth(95)
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.clicked.connect(self._refresh_pdf_list)
        folder_layout.addWidget(self.refresh_btn)
        root_layout.addWidget(folder_card)

        # ── Search + filter bar ───────────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search PDFs by name...")
        self.search_input.setMinimumHeight(34)
        self.search_input.textChanged.connect(self._filter_list)
        search_row.addWidget(self.search_input, 3)

        self.category_combo = QComboBox()
        self.category_combo.setMinimumHeight(34)
        self.category_combo.setMinimumWidth(160)
        self.category_combo.addItem("All Categories")
        self.category_combo.currentIndexChanged.connect(self._filter_list)
        search_row.addWidget(self.category_combo, 1)

        pdf_count_card, pdf_count_layout = make_card('h', (0, 0, 0, 0), 0)
        pdf_count_card.setStyleSheet("border: none; background: transparent;")
        self.pdf_count_label = label_muted("0 PDFs")
        self.pdf_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        pdf_count_layout.addWidget(self.pdf_count_label)
        search_row.addWidget(pdf_count_card)

        root_layout.addLayout(search_row)

        # ── PDF list ──────────────────────────────────────────
        self.pdf_table = QTableWidget(0, 3)
        self.pdf_table.setHorizontalHeaderLabels(["#", "PDF Name", "Category"])
        self.pdf_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.pdf_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pdf_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.pdf_table.setColumnWidth(0, 44)
        self.pdf_table.setColumnWidth(2, 120)
        self.pdf_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pdf_table.setAlternatingRowColors(True)
        self.pdf_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pdf_table.verticalHeader().setVisible(False)
        self.pdf_table.setMinimumHeight(200)
        self.pdf_table.setMaximumHeight(280)
        self.pdf_table.setShowGrid(False)
        self.pdf_table.setAlternatingRowColors(True)
        self.pdf_table.setStyleSheet(f"""
            QTableWidget {{
                alternate-background-color: {PALETTE['row_alt']};
            }}
        """)
        root_layout.addWidget(self.pdf_table)

        # ── Selection & settings row ──────────────────────────
        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)

        # Index selection card
        sel_card, sel_layout = make_card('v', (14, 12, 14, 12), 6)
        sel_layout.addWidget(label_secondary("Process (by index)"))

        sel_input_row = QHBoxLayout()
        self.selection_input = QLineEdit()
        self.selection_input.setPlaceholderText("e.g. 1,3,5 or 1-5 or empty for all")
        self.selection_input.setMinimumHeight(32)
        sel_input_row.addWidget(self.selection_input)
        sel_layout.addLayout(sel_input_row)

        hint = label_muted("Leave empty to process all visible PDFs")
        sel_layout.addWidget(hint)
        settings_row.addWidget(sel_card, 2)

        # Section card
        section_card, section_layout = make_card('v', (14, 12, 14, 12), 8)
        section_layout.addWidget(label_secondary("Section"))
        self.section_bg = QButtonGroup()
        self.mids_radio = QRadioButton("Mids Only")
        self.finals_radio = QRadioButton("Finals Only")
        self.both_radio = QRadioButton("Both")
        self.both_radio.setChecked(True)
        for r in [self.mids_radio, self.finals_radio, self.both_radio]:
            section_layout.addWidget(r)
            self.section_bg.addButton(r)
        settings_row.addWidget(section_card, 1)

        # Content type card
        content_card, content_layout = make_card('v', (14, 12, 14, 12), 8)
        content_layout.addWidget(label_secondary("Content Type"))
        self.mcq_check = QCheckBox("MCQs")
        self.mcq_check.setChecked(True)
        self.notes_check = QCheckBox("Short Notes")
        content_layout.addWidget(self.mcq_check)
        content_layout.addWidget(self.notes_check)
        settings_row.addWidget(content_card, 1)

        root_layout.addLayout(settings_row)

        # ── Advanced Settings (collapsible) ────────────────────
        self.adv_settings_btn = QPushButton("⚙  Advanced Settings  ▼")
        self.adv_settings_btn.setFixedHeight(32)
        self.adv_settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['surface']};
                border: 1.5px solid {PALETTE['border']};
                border-radius: 7px;
                color: {PALETTE['text_secondary']};
                font-size: 9.5pt;
                font-weight: 500;
                padding: 4px 16px;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {PALETTE['accent']};
                color: {PALETTE['accent']};
                background: {PALETTE['row_hover']};
            }}
        """)
        self.adv_settings_btn.clicked.connect(self._toggle_advanced_settings)
        root_layout.addWidget(self.adv_settings_btn)

        self.adv_settings_card, adv_layout = make_card('h', (14, 12, 14, 12), 20)

        def spin_row(label_text, minimum, maximum, default, tooltip=""):
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 9pt;")
            lbl.setMinimumWidth(80)
            sp = QSpinBox()
            sp.setMinimum(minimum)
            sp.setMaximum(maximum)
            sp.setValue(default)
            sp.setFixedWidth(70)
            sp.setFixedHeight(28)
            if tooltip:
                sp.setToolTip(tooltip)
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(sp)
            return row, sp

        delay_col = QVBoxLayout()
        delay_col.addWidget(label_secondary("Delay (sec)"))
        delay_row, self.delay_spin = spin_row("Seconds", 1, 15, 1)
        delay_col.addLayout(delay_row)
        adv_layout.addLayout(delay_col)

        pages_col = QVBoxLayout()
        pages_col.addWidget(label_secondary("Pages / Batch"))
        pages_row, self.pages_spin = spin_row("Pages", 1, 20, 10)
        pages_col.addLayout(pages_row)
        adv_layout.addLayout(pages_col)

        reset_col = QVBoxLayout()
        reset_col.addWidget(label_secondary("Chat Reset After"))
        reset_row, self.reset_spin = spin_row("Requests", 1, 50, 5, "Reset Gemini chat after N requests")
        reset_col.addLayout(reset_row)
        adv_layout.addLayout(reset_col)

        self.adv_settings_card.setVisible(False)
        root_layout.addWidget(self.adv_settings_card)

        # ── Control buttons ───────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.start_btn = QPushButton("Start Processing")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(38)
        self.start_btn.setMinimumWidth(160)
        self.start_btn.clicked.connect(self.start_processing)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setObjectName("warning")
        self.pause_btn.setMinimumHeight(38)
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.is_paused = False

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setMinimumHeight(38)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)

        self.reset_ui_btn = QPushButton("Reset UI")
        self.reset_ui_btn.setMinimumHeight(38)
        self.reset_ui_btn.clicked.connect(self.reset_ui)

        btn_row.addWidget(self.start_btn, 2)
        btn_row.addWidget(self.pause_btn, 1)
        btn_row.addWidget(self.stop_btn, 1)
        btn_row.addStretch()
        btn_row.addWidget(self.reset_ui_btn, 1)
        root_layout.addLayout(btn_row)

        # ── Status row ────────────────────────────────────────
        status_card, status_layout = make_card('h', (14, 10, 14, 10), 20)

        def status_pair(label):
            col = QVBoxLayout()
            col.setSpacing(2)
            lbl = label_secondary(label)
            val = QLabel("—")
            val.setStyleSheet(f"color: {PALETTE['text_primary']}; font-size: 10pt; font-weight: 600;")
            col.addWidget(lbl)
            col.addWidget(val)
            return col, val

        s1, self.status_section_val = status_pair("Section")
        s2, self.status_batch_val = status_pair("Batch")
        s3, self.status_status_val = status_pair("Status")
        self.status_status_val.setText("Ready")
        self.status_status_val.setStyleSheet(f"color: {PALETTE['success']}; font-size: 10pt; font-weight: 600;")

        status_layout.addLayout(s1)
        status_layout.addWidget(self._v_divider())
        status_layout.addLayout(s2)
        status_layout.addWidget(self._v_divider())
        status_layout.addLayout(s3)
        status_layout.addStretch()

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setAlignment(Qt.AlignVCenter)
        status_layout.addWidget(self.progress_bar)

        root_layout.addWidget(status_card)

        # ── Manual JSON input card ────────────────────────────
        manual_card, manual_layout = make_card('v', (14, 12, 14, 12), 8)

        manual_header = QHBoxLayout()
        manual_header.addWidget(label_secondary("Manual Response"))
        manual_header.addStretch()

        self.batch_info_label = QLabel("No active batch — start processing first")
        self.batch_info_label.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 9pt; font-style: italic;")
        manual_header.addWidget(self.batch_info_label)
        manual_layout.addLayout(manual_header)

        extract_row = QHBoxLayout()
        extract_row.setSpacing(8)

        self.extract_btn = QPushButton("Extract from Chat")
        self.extract_btn.setMinimumHeight(32)
        self.extract_btn.setEnabled(False)
        self.extract_btn.clicked.connect(self._on_extract)

        self.skip_btn = QPushButton("Skip Batch")
        self.skip_btn.setObjectName("warning")
        self.skip_btn.setMinimumHeight(32)
        self.skip_btn.setEnabled(False)
        self.skip_btn.clicked.connect(self._on_skip)

        extract_row.addWidget(self.extract_btn)
        extract_row.addWidget(self.skip_btn)
        extract_row.addStretch()
        manual_layout.addLayout(extract_row)

        sep_lbl = label_muted("— or paste JSON manually —")
        sep_lbl.setAlignment(Qt.AlignCenter)
        manual_layout.addWidget(sep_lbl)

        self.json_paste = QTextEdit()
        self.json_paste.setPlaceholderText("Paste JSON from Gemini here...")
        self.json_paste.setMaximumHeight(110)
        self.json_paste.setStyleSheet(f"""
            QTextEdit {{
                background: {PALETTE['bg']};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9.5pt;
                border: 1.5px solid {PALETTE['border']};
                border-radius: 7px;
                padding: 8px;
            }}
        """)
        manual_layout.addWidget(self.json_paste)

        self.submit_json_btn = QPushButton("Submit JSON")
        self.submit_json_btn.setObjectName("success")
        self.submit_json_btn.setMinimumHeight(32)
        self.submit_json_btn.setEnabled(False)
        self.submit_json_btn.clicked.connect(self._on_submit_json)
        manual_layout.addWidget(self.submit_json_btn)

        root_layout.addWidget(manual_card)

        # ── Log card ──────────────────────────────────────────
        log_card, log_layout = make_card('v', (14, 12, 14, 12), 8)

        log_header = QHBoxLayout()
        log_header.addWidget(label_secondary("Process Log"))
        log_header.addStretch()
        clear_log_btn = QPushButton("Clear")
        clear_log_btn.setFixedWidth(56)
        clear_log_btn.setFixedHeight(24)
        clear_log_btn.setStyleSheet(f"font-size: 8.5pt; padding: 2px 8px;")
        clear_log_btn.clicked.connect(self._clear_log)
        log_header.addWidget(clear_log_btn)
        log_layout.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(130)
        self.log_text.setMaximumHeight(240)
        self.log_text.setStyleSheet(f"""
            QTextEdit {{
                background: {PALETTE['navy']};
                color: #c9d1d9;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
                border: none;
                border-radius: 7px;
                padding: 10px;
            }}
        """)
        log_layout.addWidget(self.log_text)
        root_layout.addWidget(log_card)

    # ── Private helpers ───────────────────────────────────────

    def _v_divider(self):
        f = QFrame()
        f.setFrameShape(QFrame.VLine)
        f.setStyleSheet(f"color: {PALETTE['border']}; background: {PALETTE['border']}; border: none; max-width: 1px;")
        return f

    def _toggle_advanced_settings(self):
        visible = not self.adv_settings_card.isVisible()
        self.adv_settings_card.setVisible(visible)
        if visible:
            self.adv_settings_btn.setText("⚙  Advanced Settings  ▲")
        else:
            self.adv_settings_btn.setText("⚙  Advanced Settings  ▼")

    def _load_root_folder_from_config(self):
        cfg = self._read_config()
        root = cfg.get('root_folder_path', '').strip()
        if root and Path(root).exists():
            self.root_path_label.setText(root)
            self._load_pdfs_from_root(root)
        else:
            self.add_log("Select a root folder to begin scanning PDFs.", "info")

    def _browse_root_folder(self):
        cfg = self._read_config()
        start = cfg.get('root_folder_path', '') or os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, "Select Root Folder Containing Subfolders/PDFs", start,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if folder:
            self._write_config_key('root_folder_path', folder)
            self.root_path_label.setText(folder)
            self._load_pdfs_from_root(folder)

    def _load_pdfs_from_root(self, root_path):
        result = scan_root_folder(root_path)
        self.all_pdfs = result['all_pdfs']
        self.categories = result['categories']
        total = result['total']

        # Populate category combo
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("All Categories")
        for cat in sorted(self.categories.keys()):
            count = len(self.categories[cat])
            self.category_combo.addItem(f"{cat}  ({count})")
        self.category_combo.blockSignals(False)

        self._filter_list()
        self.add_log(f"Loaded {total} PDFs across {len(self.categories)} categories from {root_path}", "success")

    def _refresh_pdf_list(self):
        cfg = self._read_config()
        root = cfg.get('root_folder_path', '').strip()
        if root and Path(root).exists():
            self._load_pdfs_from_root(root)
            self.add_log("Refreshed PDF list.", "info")
        else:
            self.add_log("No root folder configured. Click 'Change' to select one.", "warning")

    def _filter_list(self):
        search = self.search_input.text().strip().lower()
        cat_idx = self.category_combo.currentIndex()
        cat_text = self.category_combo.currentText()

        # Determine which PDFs to show
        if cat_idx == 0:
            pool = list(self.all_pdfs)
        else:
            cat_name = cat_text.split("  (")[0]
            pool = self.categories.get(cat_name, [])

        if search:
            pool = [p for p in pool if search in Path(p).name.lower()]

        self.filtered_pdfs = pool

        # Populate table
        self.pdf_table.setRowCount(0)
        for i, pdf_path in enumerate(pool, 1):
            row = self.pdf_table.rowCount()
            self.pdf_table.insertRow(row)

            idx_item = QTableWidgetItem(str(i))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QColor(PALETTE['text_muted']))

            name_item = QTableWidgetItem(Path(pdf_path).name)
            name_item.setData(Qt.UserRole, pdf_path)

            # Find category for this pdf
            cat = "—"
            for c, paths in self.categories.items():
                if pdf_path in paths:
                    cat = c
                    break
            cat_item = QTableWidgetItem(cat)
            cat_item.setTextAlignment(Qt.AlignCenter)
            cat_item.setForeground(QColor(PALETTE['text_secondary']))

            self.pdf_table.setItem(row, 0, idx_item)
            self.pdf_table.setItem(row, 1, name_item)
            self.pdf_table.setItem(row, 2, cat_item)

        self.pdf_count_label.setText(f"{len(pool)} PDFs")

    def _parse_selection(self, selection_str, total):
        if not selection_str.strip():
            return list(range(1, total + 1))
        try:
            indexes = set()
            for part in selection_str.split(','):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-')
                    a, b = int(a.strip()), int(b.strip())
                    if a < 1 or b > total or a > b:
                        raise ValueError(f"Invalid range: {part}")
                    indexes.update(range(a, b + 1))
                else:
                    n = int(part)
                    if n < 1 or n > total:
                        raise ValueError(f"Index {n} out of range")
                    indexes.add(n)
            return sorted(indexes)
        except Exception as e:
            return None

    # ── Log helpers ───────────────────────────────────────────

    def add_log(self, message, level="info"):
        colors = {
            "info":    "#79c0ff",
            "success": "#56d364",
            "warning": "#e3b341",
            "error":   "#f85149",
        }
        color = colors.get(level, "#c9d1d9")
        html = f'<span style="color:{color};">{message}</span>'
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertHtml(html + "<br>")
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def _clear_log(self):
        self.log_text.clear()

    # ── Processing ────────────────────────────────────────────

    def start_processing(self):
        if not self.filtered_pdfs:
            QMessageBox.warning(self, "No PDFs", "No PDFs available. Please select a root folder.")
            return

        selection_str = self.selection_input.text().strip()
        selected_indexes = self._parse_selection(selection_str, len(self.filtered_pdfs))

        if selected_indexes is None:
            QMessageBox.warning(self, "Invalid Selection",
                f"Invalid selection: '{selection_str}'\n\nUse formats like: 1,3,5 or 1-5 or 1-3,7,9-12")
            return

        selected_pdfs = [self.filtered_pdfs[i - 1] for i in selected_indexes]

        if not self.mcq_check.isChecked() and not self.notes_check.isChecked():
            QMessageBox.warning(self, "No Content Type", "Select at least one content type.")
            return

        # Sections
        selected_sections = []
        if self.mids_radio.isChecked():
            selected_sections = ['mids']
        elif self.finals_radio.isChecked():
            selected_sections = ['finals']
        else:
            selected_sections = ['mids', 'finals']

        content_types = []
        if self.mcq_check.isChecked():
            content_types.append('mcq')
        if self.notes_check.isChecked():
            content_types.append('short_notes')

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_status_val.setText("Running")
        self.status_status_val.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 10pt; font-weight: 600;")

        self.add_log(f"Starting: {len(selected_pdfs)} PDFs | Sections: {', '.join(selected_sections)} | Types: {', '.join(content_types)}", "info")

        self.processing_thread = BatchProcessingThread(
            selected_pdfs,
            selected_sections,
            start_pdf_index=1,
            delay_seconds=self.delay_spin.value(),
            pages_per_request=self.pages_spin.value(),
            content_types=content_types,
            chat_reset_threshold=self.reset_spin.value()
        )

        self.processing_thread.log_signal.connect(self.add_log)
        self.processing_thread.status_signal.connect(self._update_status)
        self.processing_thread.current_pdf_signal.connect(self._update_pdf_progress)
        self.processing_thread.finished_signal.connect(self._processing_done)
        self.processing_thread.awaiting_input_signal.connect(self._on_awaiting_input)
        self.processing_thread.json_invalid_signal.connect(self._on_json_invalid)
        self.processing_thread.start()

    def stop_processing(self):
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.stop_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            self.add_log("Stopping...", "warning")

    def toggle_pause(self):
        if not self.processing_thread or not self.processing_thread.isRunning():
            return
        if self.is_paused:
            self.processing_thread.resume()
            self.is_paused = False
            self.pause_btn.setText("Pause")
            self.pause_btn.setObjectName("warning")
            self.pause_btn.setStyle(self.pause_btn.style())
            self.add_log("Resumed.", "info")
        else:
            self.processing_thread.pause()
            self.is_paused = True
            self.pause_btn.setText("Resume")
            self.pause_btn.setObjectName("success")
            self.pause_btn.setStyle(self.pause_btn.style())
            self.add_log("Paused.", "warning")

    def reset_ui(self):
        self.status_section_val.setText("—")
        self.status_batch_val.setText("—")
        self.status_status_val.setText("Ready")
        self.status_status_val.setStyleSheet(f"color: {PALETTE['success']}; font-size: 10pt; font-weight: 600;")
        self.progress_bar.setValue(0)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.is_paused = False
        self.extract_btn.setEnabled(False)
        self.submit_json_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.batch_info_label.setText("No active batch — start processing first")
        self.batch_info_label.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 9pt; font-style: italic;")
        self.add_log("UI reset.", "info")

    # ── Signal handlers ───────────────────────────────────────

    def _update_status(self, status):
        self.status_status_val.setText(status[:40])

    def _update_pdf_progress(self, pdf_name, current, total):
        self.status_section_val.setText(f"PDF {current}/{total}")
        self.status_batch_val.setText(pdf_name[:30])
        if total > 0:
            self.progress_bar.setValue(int(current / total * 100))

    def _processing_done(self, success, message):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.is_paused = False
        self.extract_btn.setEnabled(False)
        self.submit_json_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.batch_info_label.setText("No active batch")
        self.batch_info_label.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 9pt; font-style: italic;")

        if success:
            self.progress_bar.setValue(100)
            self.status_status_val.setText("Complete")
            self.status_status_val.setStyleSheet(f"color: {PALETTE['success']}; font-size: 10pt; font-weight: 600;")
            self.add_log(f"Done: {message}", "success")
            QMessageBox.information(self, "Complete", message)
        else:
            self.status_status_val.setText("Error")
            self.status_status_val.setStyleSheet(f"color: {PALETTE['error']}; font-size: 10pt; font-weight: 600;")
            self.add_log(f"Error: {message}", "error")
            QMessageBox.critical(self, "Error", message)

    def _on_awaiting_input(self, pdf_name, section, batch_idx, total_batches, content_label):
        msg = f"Waiting — {pdf_name} | {section.upper()} | Batch {batch_idx}/{total_batches} ({content_label})"
        self.batch_info_label.setText(msg)
        self.batch_info_label.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 9pt; font-weight: 600;")
        self.extract_btn.setEnabled(True)
        self.submit_json_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)

    def _on_json_invalid(self, invalid_json):
        self.batch_info_label.setText("Invalid JSON — paste corrected response below")
        self.batch_info_label.setStyleSheet(f"color: {PALETTE['error']}; font-size: 9pt; font-weight: 600;")
        self.json_paste.setPlainText(invalid_json)
        self.extract_btn.setEnabled(True)
        self.submit_json_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)

    def _on_extract(self):
        if not self.processing_thread or not self.processing_thread.isRunning():
            return
        try:
            from gemini_client import GeminiClient
            client = GeminiClient()
            raw = client.extract_response()
            if raw:
                self.add_log(f"Extracted {len(raw)} chars from Gemini", "success")
                self.processing_thread.submit_json(raw, source='extract')
                self._disable_manual_btns()
            else:
                self.add_log("No response extracted", "warning")
        except Exception as e:
            self.add_log(f"Extract failed: {str(e)}", "error")

    def _on_skip(self):
        if not self.processing_thread or not self.processing_thread.isRunning():
            return
        reply = QMessageBox.question(self, "Skip Batch?",
            "Skip this batch? Current data will be discarded.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.processing_thread.skip_current_batch()
            self._disable_manual_btns()
            self.batch_info_label.setText("Skipping batch...")
            self.batch_info_label.setStyleSheet(f"color: {PALETTE['warning']}; font-size: 9pt;")

    def _on_submit_json(self):
        if not self.processing_thread or not self.processing_thread.isRunning():
            return
        text = self.json_paste.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty", "Paste JSON first.")
            return
        self.add_log(f"Manual JSON submitted ({len(text)} chars)", "info")
        self.processing_thread.submit_json(text, source='manual')
        self.json_paste.clear()
        self._disable_manual_btns()
        self.batch_info_label.setText("JSON submitted — processing...")
        self.batch_info_label.setStyleSheet(f"color: {PALETTE['success']}; font-size: 9pt; font-weight: 600;")

    def _disable_manual_btns(self):
        self.extract_btn.setEnabled(False)
        self.submit_json_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)

    def _load_last_state(self):
        state = self.state_manager.load_state()
        if state:
            summary = self.state_manager.get_state_summary()
            self.add_log(f"Last state: {summary}", "info")
        self.add_log("Application ready. Select a root folder to begin.", "success")
        self.add_log("Make sure the Gemini server is running (npm start).", "warning")


# ─────────────────────────────────────────────────────────────
#  PDF GENERATOR TAB
# ─────────────────────────────────────────────────────────────
class PDFGeneratorTab(QWidget):
    def __init__(self):
        super().__init__()
        self.json_files = []
        self.pdf_gen_thread = None
        self.show_converted = False
        self._build_ui()
        self._auto_load_json_files()

    def _read_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        # ── Header ────────────────────────────────────────────
        header_row = QHBoxLayout()
        title_lbl = QLabel("PDF Generator")
        title_lbl.setStyleSheet(f"color: {PALETTE['navy']}; font-size: 14pt; font-weight: 700;")
        desc_lbl = label_muted("Convert JSON output files into clean, formatted PDFs")
        header_row.addWidget(title_lbl)
        header_row.addWidget(desc_lbl)
        header_row.addStretch()
        root_layout.addLayout(header_row)

        root_layout.addWidget(divider())

        # ── JSON source card ──────────────────────────────────
        source_card, source_layout = make_card('v', (16, 14, 16, 14), 10)

        source_top = QHBoxLayout()
        source_top.addWidget(label_secondary("JSON Source"))
        source_top.addStretch()

        self.reload_btn = QPushButton("  Reload  ")
        self.reload_btn.setFixedHeight(32)
        self.reload_btn.setMinimumWidth(90)
        self.reload_btn.clicked.connect(self._auto_load_json_files)
        source_top.addWidget(self.reload_btn)

        self.browse_json_btn = QPushButton("  Browse Folder  ")
        self.browse_json_btn.setFixedHeight(32)
        self.browse_json_btn.setMinimumWidth(130)
        self.browse_json_btn.clicked.connect(self._browse_json_folder)
        source_top.addWidget(self.browse_json_btn)

        source_layout.addLayout(source_top)

        self.json_root_label = label_muted("Source: (auto-detected from config)")
        source_layout.addWidget(self.json_root_label)

        # Search + filter for JSON files
        json_search_row = QHBoxLayout()
        json_search_row.setSpacing(8)
        self.json_search = QLineEdit()
        self.json_search.setPlaceholderText("Filter by filename...")
        self.json_search.setMinimumHeight(32)
        self.json_search.textChanged.connect(self._filter_json_list)
        json_search_row.addWidget(self.json_search, 3)

        self.json_category_combo = QComboBox()
        self.json_category_combo.setMinimumHeight(32)
        self.json_category_combo.setMinimumWidth(140)
        self.json_category_combo.addItem("All Categories")
        self.json_category_combo.currentIndexChanged.connect(self._filter_json_list)
        json_search_row.addWidget(self.json_category_combo, 1)

        self.json_type_combo = QComboBox()
        self.json_type_combo.setMinimumHeight(32)
        self.json_type_combo.setMinimumWidth(120)
        self.json_type_combo.addItems(["All Types", "MCQs", "Short Notes"])
        self.json_type_combo.currentIndexChanged.connect(self._filter_json_list)
        json_search_row.addWidget(self.json_type_combo, 1)

        source_layout.addLayout(json_search_row)

        # Toggle: show/hide converted files
        toggle_row = QHBoxLayout()
        self.converted_toggle_btn = QPushButton("Show Converted (0)")
        self.converted_toggle_btn.setFixedHeight(28)
        self.converted_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['surface']};
                border: 1.5px solid {PALETTE['border']};
                border-radius: 6px;
                color: {PALETTE['text_secondary']};
                font-size: 9pt;
                padding: 3px 14px;
            }}
            QPushButton:hover {{
                border-color: {PALETTE['accent']};
                color: {PALETTE['accent']};
            }}
        """)
        self.converted_toggle_btn.clicked.connect(self._toggle_converted)
        toggle_row.addWidget(self.converted_toggle_btn)

        self.json_count_label = label_muted("0 files")
        self.json_count_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        toggle_row.addStretch()
        toggle_row.addWidget(self.json_count_label)
        source_layout.addLayout(toggle_row)

        # JSON file table (unprocessed)
        self.json_table = QTableWidget(0, 4)
        self.json_table.setHorizontalHeaderLabels(["#", "File Name", "Category", "Type"])
        self.json_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.json_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.json_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.json_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.json_table.setColumnWidth(0, 44)
        self.json_table.setColumnWidth(2, 120)
        self.json_table.setColumnWidth(3, 90)
        self.json_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.json_table.setAlternatingRowColors(True)
        self.json_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.json_table.verticalHeader().setVisible(False)
        self.json_table.setMinimumHeight(180)
        self.json_table.setMaximumHeight(260)
        self.json_table.setShowGrid(False)
        source_layout.addWidget(self.json_table)
        root_layout.addWidget(source_card)

        # ── Generated PDFs Section (category-wise) ────────────
        self.gen_pdfs_btn = QPushButton("📄  Generated PDFs  ▼")
        self.gen_pdfs_btn.setFixedHeight(32)
        self.gen_pdfs_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['surface']};
                border: 1.5px solid {PALETTE['border']};
                border-radius: 7px;
                color: {PALETTE['text_secondary']};
                font-size: 9.5pt;
                font-weight: 500;
                padding: 4px 16px;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {PALETTE['success']};
                color: {PALETTE['success']};
                background: {PALETTE['row_hover']};
            }}
        """)
        self.gen_pdfs_btn.clicked.connect(self._toggle_generated_pdfs)
        root_layout.addWidget(self.gen_pdfs_btn)

        self.gen_pdfs_card, gen_pdfs_layout = make_card('v', (14, 12, 14, 12), 6)
        self.gen_pdfs_table = QTableWidget(0, 3)
        self.gen_pdfs_table.setHorizontalHeaderLabels(["#", "PDF File", "Category"])
        self.gen_pdfs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.gen_pdfs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.gen_pdfs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.gen_pdfs_table.setColumnWidth(0, 44)
        self.gen_pdfs_table.setColumnWidth(2, 120)
        self.gen_pdfs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.gen_pdfs_table.setAlternatingRowColors(True)
        self.gen_pdfs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.gen_pdfs_table.verticalHeader().setVisible(False)
        self.gen_pdfs_table.setMinimumHeight(120)
        self.gen_pdfs_table.setMaximumHeight(220)
        self.gen_pdfs_table.setShowGrid(False)
        gen_pdfs_layout.addWidget(self.gen_pdfs_table)
        self.gen_pdfs_card.setVisible(False)
        root_layout.addWidget(self.gen_pdfs_card)

        # ── Selection & output card ───────────────────────────
        opts_row = QHBoxLayout()
        opts_row.setSpacing(12)

        # Index selection
        idx_card, idx_layout = make_card('v', (14, 12, 14, 12), 6)
        idx_layout.addWidget(label_secondary("Select Files (by index)"))
        self.json_selection_input = QLineEdit()
        self.json_selection_input.setPlaceholderText("e.g. 1,3,5 or 1-5 or empty for all")
        self.json_selection_input.setMinimumHeight(32)
        idx_layout.addWidget(self.json_selection_input)
        idx_layout.addWidget(label_muted("Leave empty to generate all"))
        opts_row.addWidget(idx_card, 2)

        # Output dir card
        out_card, out_layout = make_card('v', (14, 12, 14, 12), 6)
        out_layout.addWidget(label_secondary("Output Directory"))

        self.pdf_out_path = QLineEdit()
        self.pdf_out_path.setPlaceholderText("Same folder as JSON file (default)")
        self.pdf_out_path.setMinimumHeight(32)
        out_layout.addWidget(self.pdf_out_path)

        browse_out_btn = QPushButton("  Browse  ")
        browse_out_btn.setFixedHeight(32)
        browse_out_btn.setMinimumWidth(90)
        browse_out_btn.clicked.connect(self._browse_output_dir)
        out_layout.addWidget(browse_out_btn)
        opts_row.addWidget(out_card, 2)

        root_layout.addLayout(opts_row)

        # ── Generate button ───────────────────────────────────
        gen_row = QHBoxLayout()
        self.generate_btn = QPushButton("Generate PDFs")
        self.generate_btn.setObjectName("primary")
        self.generate_btn.setMinimumHeight(42)
        self.generate_btn.setMinimumWidth(200)
        self.generate_btn.clicked.connect(self._start_generation)
        gen_row.addStretch()
        gen_row.addWidget(self.generate_btn)
        gen_row.addStretch()
        root_layout.addLayout(gen_row)

        # ── Progress ──────────────────────────────────────────
        self.gen_progress = QProgressBar()
        self.gen_progress.setValue(0)
        self.gen_progress.setFixedHeight(6)
        self.gen_progress.setTextVisible(False)
        root_layout.addWidget(self.gen_progress)

        # ── Log ───────────────────────────────────────────────
        log_card, log_layout = make_card('v', (14, 12, 14, 12), 8)

        log_header = QHBoxLayout()
        log_header.addWidget(label_secondary("Generation Log"))
        log_header.addStretch()
        clr = QPushButton("Clear")
        clr.setFixedWidth(56)
        clr.setFixedHeight(24)
        clr.setStyleSheet("font-size: 8.5pt; padding: 2px 8px;")
        clr.clicked.connect(lambda: self.gen_log.clear())
        log_header.addWidget(clr)
        log_layout.addLayout(log_header)

        self.gen_log = QTextEdit()
        self.gen_log.setReadOnly(True)
        self.gen_log.setMinimumHeight(120)
        self.gen_log.setMaximumHeight(200)
        self.gen_log.setStyleSheet(f"""
            QTextEdit {{
                background: {PALETTE['navy']};
                color: #c9d1d9;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
                border: none;
                border-radius: 7px;
                padding: 10px;
            }}
        """)
        log_layout.addWidget(self.gen_log)
        root_layout.addWidget(log_card)
        root_layout.addStretch()

    # ── Private helpers ───────────────────────────────────────

    def _add_gen_log(self, message, level="info"):
        colors = {
            "info":    "#79c0ff",
            "success": "#56d364",
            "warning": "#e3b341",
            "error":   "#f85149",
        }
        color = colors.get(level, "#c9d1d9")
        html = f'<span style="color:{color};">{message}</span>'
        cursor = self.gen_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.gen_log.setTextCursor(cursor)
        self.gen_log.insertHtml(html + "<br>")
        self.gen_log.verticalScrollBar().setValue(self.gen_log.verticalScrollBar().maximum())

    def _auto_load_json_files(self):
        """Load JSON files from configured json_output_root"""
        from folder_organizer import get_json_output_root
        cfg = self._read_config()

        # Try json_output_root first, then root_folder_path, then default
        root = cfg.get('json_output_root', '').strip()
        if not root or not Path(root).exists():
            root = get_json_output_root()

        if Path(root).exists():
            self.json_root_label.setText(f"Source: {root}")
            self._scan_json_from_root(root)
        else:
            self._add_gen_log(f"JSON output directory not found: {root}", "warning")
            self._add_gen_log("Try browsing manually or processing PDFs first.", "info")

    def _scan_json_from_root(self, root_path):
        from pdf_generator import scan_json_files
        self.json_files = scan_json_files(root_path)

        # Check which JSON files already have a generated PDF
        for item in self.json_files:
            json_path = Path(item['path'])
            pdf_sibling = json_path.with_suffix('.pdf')
            item['has_pdf'] = pdf_sibling.exists()

        # Populate category combo
        categories = sorted(set(f['category'] for f in self.json_files))
        self.json_category_combo.blockSignals(True)
        self.json_category_combo.clear()
        self.json_category_combo.addItem("All Categories")
        for cat in categories:
            count = len([f for f in self.json_files if f['category'] == cat])
            self.json_category_combo.addItem(f"{cat}  ({count})")
        self.json_category_combo.blockSignals(False)

        # Update toggle button count
        converted_count = len([f for f in self.json_files if f.get('has_pdf')])
        self.converted_toggle_btn.setText(f"Show Converted ({converted_count})")

        self._filter_json_list()
        self._refresh_generated_pdfs_table()
        self._add_gen_log(f"Found {len(self.json_files)} JSON files in {root_path}", "success")

    def _browse_json_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder with JSON Files",
            os.path.expanduser("~"), QFileDialog.ShowDirsOnly
        )
        if folder:
            self.json_root_label.setText(f"Source: {folder}")
            self._scan_json_from_root(folder)

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", os.path.expanduser("~"))
        if folder:
            self.pdf_out_path.setText(folder)

    def _toggle_converted(self):
        self.show_converted = not self.show_converted
        converted_count = len([f for f in self.json_files if f.get('has_pdf')])
        if self.show_converted:
            self.converted_toggle_btn.setText(f"Hide Converted ({converted_count})")
            self.converted_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['row_hover']};
                    border: 1.5px solid {PALETTE['accent']};
                    border-radius: 6px;
                    color: {PALETTE['accent']};
                    font-size: 9pt;
                    font-weight: 500;
                    padding: 3px 14px;
                }}
                QPushButton:hover {{
                    background: {PALETTE['surface']};
                }}
            """)
        else:
            self.converted_toggle_btn.setText(f"Show Converted ({converted_count})")
            self.converted_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['surface']};
                    border: 1.5px solid {PALETTE['border']};
                    border-radius: 6px;
                    color: {PALETTE['text_secondary']};
                    font-size: 9pt;
                    padding: 3px 14px;
                }}
                QPushButton:hover {{
                    border-color: {PALETTE['accent']};
                    color: {PALETTE['accent']};
                }}
            """)
        self._filter_json_list()

    def _toggle_generated_pdfs(self):
        visible = not self.gen_pdfs_card.isVisible()
        self.gen_pdfs_card.setVisible(visible)
        if visible:
            self.gen_pdfs_btn.setText("📄  Generated PDFs  ▲")
        else:
            self.gen_pdfs_btn.setText("📄  Generated PDFs  ▼")

    def _refresh_generated_pdfs_table(self):
        """Populate the generated PDFs table grouped by category"""
        converted = [f for f in self.json_files if f.get('has_pdf')]
        converted.sort(key=lambda x: (x['category'], x['name']))

        self.gen_pdfs_table.setRowCount(0)
        for i, item in enumerate(converted, 1):
            row = self.gen_pdfs_table.rowCount()
            self.gen_pdfs_table.insertRow(row)

            idx_item = QTableWidgetItem(str(i))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QColor(PALETTE['text_muted']))

            pdf_name = Path(item['path']).with_suffix('.pdf').name
            name_item = QTableWidgetItem(pdf_name)
            name_item.setForeground(QColor(PALETTE['success']))

            cat_item = QTableWidgetItem(item['category'])
            cat_item.setTextAlignment(Qt.AlignCenter)
            cat_item.setForeground(QColor(PALETTE['text_secondary']))

            self.gen_pdfs_table.setItem(row, 0, idx_item)
            self.gen_pdfs_table.setItem(row, 1, name_item)
            self.gen_pdfs_table.setItem(row, 2, cat_item)

        # Update button text with count
        self.gen_pdfs_btn.setText(f"📄  Generated PDFs ({len(converted)})  {'▲' if self.gen_pdfs_card.isVisible() else '▼'}")

    def _filter_json_list(self):
        search = self.json_search.text().strip().lower()
        type_filter = self.json_type_combo.currentText()
        cat_idx = self.json_category_combo.currentIndex()
        cat_text = self.json_category_combo.currentText()

        filtered = self.json_files

        # Hide converted unless toggled on
        if not self.show_converted:
            filtered = [f for f in filtered if not f.get('has_pdf', False)]

        if search:
            filtered = [f for f in filtered if search in f['name'].lower()]
        if type_filter != "All Types":
            filtered = [f for f in filtered if f['type'] == type_filter]
        if cat_idx > 0:
            cat_name = cat_text.split("  (")[0]
            filtered = [f for f in filtered if f['category'] == cat_name]

        self.json_count_label.setText(f"{len(filtered)} files")
        self._populate_json_table(filtered)

    def _populate_json_table(self, files):
        self.json_table.setRowCount(0)
        for i, item in enumerate(files, 1):
            row = self.json_table.rowCount()
            self.json_table.insertRow(row)

            idx_item = QTableWidgetItem(str(i))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QColor(PALETTE['text_muted']))

            name_item = QTableWidgetItem(item['name'])
            name_item.setData(Qt.UserRole, item['path'])

            cat_item = QTableWidgetItem(item['category'])
            cat_item.setTextAlignment(Qt.AlignCenter)
            cat_item.setForeground(QColor(PALETTE['text_secondary']))

            type_item = QTableWidgetItem(item['type'])
            type_item.setTextAlignment(Qt.AlignCenter)
            if item['type'] == 'MCQs':
                type_item.setForeground(QColor(PALETTE['accent']))
            elif item['type'] == 'Short Notes':
                type_item.setForeground(QColor(PALETTE['success']))
            else:
                type_item.setForeground(QColor(PALETTE['text_muted']))

            self.json_table.setItem(row, 0, idx_item)
            self.json_table.setItem(row, 1, name_item)
            self.json_table.setItem(row, 2, cat_item)
            self.json_table.setItem(row, 3, type_item)

    def _get_currently_shown_files(self):
        """Get the files currently displayed in the table"""
        files = []
        for row in range(self.json_table.rowCount()):
            item = self.json_table.item(row, 1)
            if item:
                files.append(item.data(Qt.UserRole))
        return files

    def _parse_selection(self, selection_str, total):
        if not selection_str.strip():
            return list(range(1, total + 1))
        try:
            indexes = set()
            for part in selection_str.split(','):
                part = part.strip()
                if '-' in part:
                    a, b = part.split('-')
                    a, b = int(a.strip()), int(b.strip())
                    if a < 1 or b > total or a > b:
                        raise ValueError()
                    indexes.update(range(a, b + 1))
                else:
                    n = int(part)
                    if n < 1 or n > total:
                        raise ValueError()
                    indexes.add(n)
            return sorted(indexes)
        except Exception:
            return None

    def _start_generation(self):
        shown = self._get_currently_shown_files()
        if not shown:
            QMessageBox.warning(self, "No Files", "No JSON files loaded. Please load or browse a folder.")
            return

        selection_str = self.json_selection_input.text().strip()
        selected_indexes = self._parse_selection(selection_str, len(shown))

        if selected_indexes is None:
            QMessageBox.warning(self, "Invalid Selection", "Invalid selection format.")
            return

        selected_paths = [shown[i - 1] for i in selected_indexes]
        output_dir = self.pdf_out_path.text().strip() or None

        self._add_gen_log(f"Generating {len(selected_paths)} PDF(s)...", "info")
        self.generate_btn.setEnabled(False)
        self.gen_progress.setValue(0)

        self.pdf_gen_thread = PDFGenThread(selected_paths, output_dir)
        self.pdf_gen_thread.log_signal.connect(self._add_gen_log)
        self.pdf_gen_thread.finished_signal.connect(self._generation_done)
        self.pdf_gen_thread.start()

    def _generation_done(self, success, message):
        self.generate_btn.setEnabled(True)
        if success:
            self.gen_progress.setValue(100)
            self._add_gen_log(f"Done: {message}", "success")

            # Refresh has_pdf flags so converted files move to Generated section
            for item in self.json_files:
                json_path = Path(item['path'])
                pdf_sibling = json_path.with_suffix('.pdf')
                item['has_pdf'] = pdf_sibling.exists()

            converted_count = len([f for f in self.json_files if f.get('has_pdf')])
            self.converted_toggle_btn.setText(f"{'Hide' if self.show_converted else 'Show'} Converted ({converted_count})")
            self._filter_json_list()
            self._refresh_generated_pdfs_table()

            QMessageBox.information(self, "Done", message)
        else:
            self._add_gen_log(f"Error: {message}", "error")
            QMessageBox.critical(self, "Error", message)


# ─────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gemini MCQ Extractor")
        self.setGeometry(80, 60, 1100, 820)
        self.setMinimumSize(900, 700)
        self._build_ui()

    def _build_ui(self):
        # ── Navbar / tab bar ──────────────────────────────────
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        main_vbox = QVBoxLayout(central)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        # Top navbar
        navbar = QWidget()
        navbar.setStyleSheet(f"background: {PALETTE['navy']}; border: none;")
        navbar.setFixedHeight(52)
        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(20, 0, 20, 0)
        nav_layout.setSpacing(0)

        # Brand
        brand = QLabel("MCQ Extractor")
        brand.setStyleSheet("color: white; font-size: 13pt; font-weight: 700; letter-spacing: -0.3px;")
        nav_layout.addWidget(brand)

        # Dot separator
        dot = QLabel("·")
        dot.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 18pt; padding: 0 10px;")
        nav_layout.addWidget(dot)

        nav_layout.addStretch()

        # Tab buttons
        self._nav_btns = []
        for i, text in enumerate(["Processing", "PDF Generator"]):
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(52)
            btn.setMinimumWidth(130)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {PALETTE['tab_inactive']};
                    border: none;
                    border-bottom: 3px solid transparent;
                    font-size: 10pt;
                    font-weight: 500;
                    padding: 0 20px;
                    border-radius: 0;
                }}
                QPushButton:checked {{
                    color: white;
                    border-bottom: 3px solid {PALETTE['accent']};
                }}
                QPushButton:hover:!checked {{
                    color: #ccccdd;
                    background: rgba(255,255,255,0.05);
                }}
            """)
            btn.clicked.connect(lambda checked, idx=i: self._switch_tab(idx))
            nav_layout.addWidget(btn)
            self._nav_btns.append(btn)

        main_vbox.addWidget(navbar)

        # ── Content area ──────────────────────────────────────
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("border: none;")

        # Stacked content container
        self.content_stack = QWidget()
        self.stack_layout = QVBoxLayout(self.content_stack)
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setSpacing(0)

        self.processing_tab = ProcessingTab()
        self.pdf_gen_tab = PDFGeneratorTab()

        self.stack_layout.addWidget(self.processing_tab)
        self.stack_layout.addWidget(self.pdf_gen_tab)

        self.scroll_area.setWidget(self.content_stack)
        main_vbox.addWidget(self.scroll_area)

        # Switch to first tab
        self._switch_tab(0)

    def _switch_tab(self, idx):
        self.processing_tab.setVisible(idx == 0)
        self.pdf_gen_tab.setVisible(idx == 1)

        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)


# ─────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(APP_STYLE)

    # Set a clean font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
