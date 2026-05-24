"""
PDF MCQ Extraction Tool — Redesigned UI
Modern, minimal, premium-feeling interface with tabbed navigation.
"""

import sys
import os
import json
from pathlib import Path
from PyQt5.QtWidgets import QColorDialog
from pdf_settings import PDFSettingsManager
from pdf_editor import EditPDFTab

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
    QProgressBar, QFrame, QRadioButton, QButtonGroup,
    QSpinBox, QScrollArea, QSizePolicy, QComboBox, QListWidget,
    QListWidgetItem, QCheckBox, QTabWidget, QMessageBox,
    QAbstractItemView, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QToolButton, QGroupBox, QDialog, QPlainTextEdit,
    QToolTip
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QEvent, QElapsedTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor, QIcon, QPalette, QKeySequence

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
    font-family: 'Google Sans Flex', 'Outfit', 'Montserrat', 'Poppins', 'Inter', sans-serif;
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
            from pdf_generator import generate_pdf_from_json, get_standardized_pdf_name
            total = len(self.json_paths)
            for i, json_path in enumerate(self.json_paths, 1):
                self.log_signal.emit(f"Generating PDF {i}/{total}: {Path(json_path).name}", "info")
                try:
                    out_name = get_standardized_pdf_name(json_path)
                    out_path = None
                    if self.output_dir:
                        out_path = str(Path(self.output_dir) / out_name)
                    else:
                        out_path = str(Path(json_path).parent / out_name)
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
        self.index_map = {}          # {pdf_path: stable_id} e.g., CS01, MCM02
        # Feature 1/2: init auto-parse state before _build_ui (used in eventFilter)
        self._auto_parse_enabled = True
        self._last_paste_ms = 0
        self._paste_block_ms = 600
        self._build_ui()
        self._setup_processed_search()
        # Feature 7: Load persisted settings (after widgets exist)
        self._load_settings_from_config()
        # Feature 7: Connect settings auto-save
        self._connect_settings_persistence()
        # Feature 1+2: Setup auto-parse & paste protection
        self._setup_auto_parse()
        # Feature 5: Connect double-click
        self.pdf_table.cellDoubleClicked.connect(self._on_pdf_table_double_click)
        # Feature 4: Connect selection input changes
        self.selection_input.textChanged.connect(self._update_selection_warning)
        self.mids_radio.toggled.connect(lambda _: self._update_selection_warning())
        self.finals_radio.toggled.connect(lambda _: self._update_selection_warning())
        self.both_radio.toggled.connect(lambda _: self._update_selection_warning())
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
        self.pdf_table.setHorizontalHeaderLabels(["#", "PDF NAME", "CATEGORY"])
        self.pdf_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.pdf_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pdf_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.pdf_table.setColumnWidth(0, 80)
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
        sel_layout.addWidget(label_secondary("Process (by ID or index)"))

        sel_input_row = QHBoxLayout()
        self.selection_input = QLineEdit()
        self.selection_input.setPlaceholderText("e.g. CS01,CS03 or 1-5 or empty for all")
        self.selection_input.setMinimumHeight(32)
        sel_input_row.addWidget(self.selection_input)
        sel_layout.addLayout(sel_input_row)

        hint = label_muted("Use stable IDs (CS01, MCM02) or numeric indexes. Leave empty for all.  |  Double-click a PDF row to add its ID.")
        sel_layout.addWidget(hint)

        # Feature 4: Warning label for already-processed PDFs
        self.selection_warning_label = QLabel("")
        self.selection_warning_label.setStyleSheet(f"""
            color: {PALETTE['error']};
            font-size: 9pt;
            font-weight: 600;
            background: #fff0f0;
            border: 1px solid {PALETTE['error']};
            border-radius: 5px;
            padding: 3px 8px;
        """)
        self.selection_warning_label.setWordWrap(True)
        self.selection_warning_label.setVisible(False)
        sel_layout.addWidget(self.selection_warning_label)
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
        content_layout.addWidget(divider())
        content_layout.addWidget(label_secondary("Reviews Context"))
        self.mcq_reviews_check = QCheckBox("Use reviews for MCQs")
        self.notes_reviews_check = QCheckBox("Use reviews for Notes")
        # Feature 3: Default both review checkboxes to enabled
        self.mcq_reviews_check.setChecked(True)
        self.notes_reviews_check.setChecked(True)
        self.mcq_reviews_check.setToolTip("Include student reviews in MCQ generation prompts for better relevance")
        self.notes_reviews_check.setToolTip("Include student reviews in Short Notes generation prompts for better relevance")
        content_layout.addWidget(self.mcq_reviews_check)
        content_layout.addWidget(self.notes_reviews_check)
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

        self.repeat_btn = QPushButton("Repeat Batch")
        self.repeat_btn.setMinimumHeight(32)
        self.repeat_btn.setEnabled(False)
        self.repeat_btn.setToolTip("Re-send the same prompt for the current batch to Gemini")
        self.repeat_btn.clicked.connect(self._on_repeat)

        self.skip_btn = QPushButton("Skip Batch")
        self.skip_btn.setObjectName("warning")
        self.skip_btn.setMinimumHeight(32)
        self.skip_btn.setEnabled(False)
        self.skip_btn.clicked.connect(self._on_skip)

        # Reviews info badge
        self.reviews_badge = QPushButton("📝 Reviews: —")
        self.reviews_badge.setMinimumHeight(32)
        self.reviews_badge.setEnabled(False)
        self.reviews_badge.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['surface']};
                border: 1.5px solid {PALETTE['border']};
                border-radius: 7px;
                color: {PALETTE['text_muted']};
                font-size: 9pt;
                padding: 4px 12px;
            }}
        """)
        self.reviews_badge.setToolTip("Shows review availability for current subject")

        extract_row.addWidget(self.repeat_btn)
        extract_row.addWidget(self.skip_btn)
        extract_row.addWidget(self.reviews_badge)
        extract_row.addStretch()
        manual_layout.addLayout(extract_row)

        sep_lbl = label_muted("— or paste JSON manually —")
        sep_lbl.setAlignment(Qt.AlignCenter)
        manual_layout.addWidget(sep_lbl)

        self.json_paste = QPlainTextEdit()
        self.json_paste.setPlaceholderText("Paste JSON from Gemini here...")
        self.json_paste.setMaximumHeight(110)
        self.json_paste.setStyleSheet(f"""
            QPlainTextEdit {{
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

        # ── Feature 6: Processed PDFs search card (collapsible) ──
        self.processed_search_btn = QPushButton("🔍  Processed PDFs  ▼")
        self.processed_search_btn.setFixedHeight(32)
        self.processed_search_btn.setStyleSheet(f"""
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
        self.processed_search_btn.clicked.connect(self._toggle_processed_search_card)
        root_layout.addWidget(self.processed_search_btn)

        self.processed_search_card, proc_layout = make_card('v', (14, 12, 14, 12), 8)

        proc_header = QHBoxLayout()
        proc_header.addWidget(label_secondary("Search Processed PDFs"))
        proc_header.addStretch()

        self.processed_count_label = label_muted("0 results")
        proc_header.addWidget(self.processed_count_label)

        refresh_proc_btn = QPushButton("Scan")
        refresh_proc_btn.setFixedHeight(26)
        refresh_proc_btn.setFixedWidth(60)
        refresh_proc_btn.setStyleSheet(f"font-size: 8.5pt; padding: 2px 8px;")
        refresh_proc_btn.clicked.connect(self._load_processed_pdfs)
        proc_header.addWidget(refresh_proc_btn)
        proc_layout.addLayout(proc_header)

        self.processed_search_input = QLineEdit()
        self.processed_search_input.setPlaceholderText("Search by PDF name or subject code (e.g. CS101)...")
        self.processed_search_input.setMinimumHeight(32)
        self.processed_search_input.textChanged.connect(self._filter_processed_pdfs)
        proc_layout.addWidget(self.processed_search_input)

        self.processed_table = QTableWidget(0, 3)
        self.processed_table.setHorizontalHeaderLabels(["Subject", "PDF Name", "Status"])
        self.processed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.processed_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.processed_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.processed_table.setColumnWidth(0, 80)
        self.processed_table.setColumnWidth(2, 220)
        self.processed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.processed_table.setAlternatingRowColors(True)
        self.processed_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.processed_table.verticalHeader().setVisible(False)
        self.processed_table.setMinimumHeight(120)
        self.processed_table.setMaximumHeight(200)
        self.processed_table.setShowGrid(False)
        self.processed_table.setStyleSheet(f"""
            QTableWidget {{
                alternate-background-color: {PALETTE['row_alt']};
            }}
        """)
        proc_layout.addWidget(self.processed_table)

        proc_hint = label_muted("This shows only PDFs that have already been processed. Click 'Scan' to refresh.")
        proc_layout.addWidget(proc_hint)

        self.processed_search_card.setVisible(False)
        root_layout.addWidget(self.processed_search_card)

    def _toggle_processed_search_card(self):
        """Toggle the processed PDFs search card visibility."""
        visible = not self.processed_search_card.isVisible()
        self.processed_search_card.setVisible(visible)
        if visible:
            self.processed_search_btn.setText("🔍  Processed PDFs  ▲")
            # Auto-scan on first open
            if not self._processed_pdfs_data:
                self._load_processed_pdfs()
        else:
            self.processed_search_btn.setText("🔍  Processed PDFs  ▼")

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
        from folder_organizer import build_index_map
        result = scan_root_folder(root_path)
        self.all_pdfs = result['all_pdfs']
        self.categories = result['categories']
        total = result['total']

        # Build stable index map for permanent IDs (CS01, MCM02, etc.)
        self.index_map = build_index_map(self.all_pdfs)

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

        # Populate table with stable IDs
        self.pdf_table.setRowCount(0)
        for i, pdf_path in enumerate(pool, 1):
            row = self.pdf_table.rowCount()
            self.pdf_table.insertRow(row)

            # Use stable ID from index_map (e.g., CS01, MCM02)
            stable_id = self.index_map.get(pdf_path, str(i))
            idx_item = QTableWidgetItem(stable_id)
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QColor(PALETTE['accent']))
            idx_item.setData(Qt.UserRole, stable_id)  # Store stable ID for parsing

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
        """
        Parse selection string supporting both stable IDs (CS01, MCM02) and numeric indexes.
        
        IMPORTANT: Stable IDs are looked up against the FULL index_map (all PDFs),
        not just the currently filtered/visible PDFs. This allows users to type
        IDs like CS02,ENG01 even when the list is filtered to show only one category.
        The selected PDFs are then processed from the global all_pdfs list.
        
        Numeric indexes (1, 2, 3...) refer to the position in the currently filtered list.
        """
        if not selection_str.strip():
            return list(range(1, total + 1))

        # Build TWO reverse maps:
        # 1. From FILTERED list (for numeric index resolution)
        filtered_pos_map = {}
        for i, pdf_path in enumerate(self.filtered_pdfs, 1):
            stable_id = self.index_map.get(pdf_path, str(i))
            filtered_pos_map[stable_id.upper()] = i

        # 2. From ALL PDFs (for stable ID resolution regardless of current filter)
        # Maps stable_id -> pdf_path for global lookup
        global_id_to_path = {}
        for pdf_path, stable_id in self.index_map.items():
            global_id_to_path[stable_id.upper()] = pdf_path

        # Build a path-to-filtered-position map for cross-referencing
        path_to_filtered_pos = {pdf_path: i for i, pdf_path in enumerate(self.filtered_pdfs, 1)}

        try:
            indexes = set()
            for part in selection_str.split(','):
                part = part.strip()
                if not part:
                    continue

                upper_part = part.upper()

                # Check if it's a stable ID (e.g., CS01, MCM02)
                if upper_part in global_id_to_path:
                    pdf_path = global_id_to_path[upper_part]
                    # If this PDF is in the current filtered view, use its filtered position
                    if pdf_path in path_to_filtered_pos:
                        indexes.add(path_to_filtered_pos[pdf_path])
                    else:
                        # PDF exists globally but not in current filter —
                        # add it directly to processing by appending to filtered_pdfs temporarily
                        # We do this by adding it as a special "extra" index beyond the filtered list
                        # Actually: just add the path directly via a different mechanism.
                        # Simplest fix: add it to the filtered_pdfs temporarily for this parse session
                        self.filtered_pdfs.append(pdf_path)
                        indexes.add(len(self.filtered_pdfs))
                        path_to_filtered_pos[pdf_path] = len(self.filtered_pdfs)
                    continue

                # Check for ID range (e.g., CS01-CS05)
                if '-' in part:
                    a_str, b_str = part.split('-', 1)
                    a_str, b_str = a_str.strip(), b_str.strip()

                    # Try as stable ID range
                    a_upper, b_upper = a_str.upper(), b_str.upper()
                    if a_upper in filtered_pos_map and b_upper in filtered_pos_map:
                        a_pos, b_pos = filtered_pos_map[a_upper], filtered_pos_map[b_upper]
                        if a_pos <= b_pos:
                            indexes.update(range(a_pos, b_pos + 1))
                            continue

                    # Try as numeric range
                    try:
                        a, b = int(a_str), int(b_str)
                        if a < 1 or b > total or a > b:
                            raise ValueError(f"Invalid range: {part}")
                        indexes.update(range(a, b + 1))
                        continue
                    except ValueError:
                        pass

                    raise ValueError(f"Invalid range: {part}")
                else:
                    # Try as numeric index (position in filtered list)
                    try:
                        n = int(part)
                        if n < 1 or n > len(self.filtered_pdfs):
                            raise ValueError(f"Index {n} out of range")
                        indexes.add(n)
                    except ValueError:
                        raise ValueError(f"Unknown selection: '{part}'. Use IDs like CS01 or numeric indexes.")

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
        
        # Set reviews context flags and category
        self.processing_thread.use_reviews_for_mcq = self.mcq_reviews_check.isChecked()
        self.processing_thread.use_reviews_for_notes = self.notes_reviews_check.isChecked()

        # Auto-match review category to selected section
        if self.mids_radio.isChecked():
            self.processing_thread.review_category = 'mids'
        elif self.finals_radio.isChecked():
            self.processing_thread.review_category = 'finals'
        else:
            # When "Both" is selected, use 'mids' for mids batches and 'finals' for finals
            # The thread will handle this per-section
            self.processing_thread.review_category = 'mids'  # Default, overridden per section

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
        self.repeat_btn.setEnabled(False)
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
        self.repeat_btn.setEnabled(False)
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
        self.repeat_btn.setEnabled(True)
        self.submit_json_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        
        # Update reviews badge for current subject
        try:
            from folder_organizer import extract_subject_code
            from reviews_manager import get_review_count
            subj = extract_subject_code(pdf_name.replace('.pdf', ''))
            if subj:
                count = get_review_count(subj)
                if count > 0:
                    self.reviews_badge.setText(f"📝 Reviews: {count}")
                    self.reviews_badge.setStyleSheet(f"""
                        QPushButton {{
                            background: {PALETTE['surface']};
                            border: 1.5px solid {PALETTE['success']};
                            border-radius: 7px;
                            color: {PALETTE['success']};
                            font-size: 9pt;
                            font-weight: 600;
                            padding: 4px 12px;
                        }}
                    """)
                else:
                    self.reviews_badge.setText("📝 Reviews: 0")
                    self.reviews_badge.setStyleSheet(f"""
                        QPushButton {{
                            background: {PALETTE['surface']};
                            border: 1.5px solid {PALETTE['border']};
                            border-radius: 7px;
                            color: {PALETTE['text_muted']};
                            font-size: 9pt;
                            padding: 4px 12px;
                        }}
                    """)
            else:
                self.reviews_badge.setText("📝 Reviews: —")
        except Exception:
            pass

    def _on_json_invalid(self, invalid_json):
        self.batch_info_label.setText("Invalid JSON — paste corrected response below")
        self.batch_info_label.setStyleSheet(f"color: {PALETTE['error']}; font-size: 9pt; font-weight: 600;")
        self.json_paste.setPlainText(invalid_json)
        self.repeat_btn.setEnabled(True)
        self.submit_json_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)

    def _on_repeat(self):
        """Repeat the current batch by re-sending the same prompt"""
        if not self.processing_thread or not self.processing_thread.isRunning():
            return
        reply = QMessageBox.question(self, "Repeat Batch?",
            "Re-send the same prompt for this batch to Gemini?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self.processing_thread.repeat_current_batch()
            self._disable_manual_btns()
            self.batch_info_label.setText("Repeating batch...")
            self.batch_info_label.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 9pt; font-weight: 600;")
            self.add_log("🔄 Repeat batch requested", "info")

    def _on_extract(self):
        pass  # Removed — Extract From Chat is no longer available

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
        self.repeat_btn.setEnabled(False)
        self.submit_json_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)

    def _load_last_state(self):
        state = self.state_manager.load_state()
        if state:
            summary = self.state_manager.get_state_summary()
            self.add_log(f"Last state: {summary}", "info")
        self.add_log("Application ready. Select a root folder to begin.", "success")
        self.add_log("Make sure the Gemini server is running (npm start).", "warning")

    # ── Feature 7: Settings persistence ──────────────────────

    def _load_settings_from_config(self):
        """Load all persisted settings from config.json and apply to widgets."""
        cfg = self._read_config()

        # Advanced settings spinboxes
        delay = cfg.get('delay_seconds', 1)
        pages = cfg.get('pages_per_batch', 10)
        reset = cfg.get('chat_reset_threshold', 5)
        self.delay_spin.setValue(int(delay))
        self.pages_spin.setValue(int(pages))
        self.reset_spin.setValue(int(reset))

        # Reviews checkboxes (defaults to True per Feature 3)
        self.mcq_reviews_check.setChecked(cfg.get('reviews_for_mcqs', True))
        self.notes_reviews_check.setChecked(cfg.get('reviews_for_notes', True))

        # Content checkboxes
        self.mcq_check.setChecked(cfg.get('content_mcq', True))
        self.notes_check.setChecked(cfg.get('content_notes', False))

        # Section radio buttons
        section = cfg.get('selected_section', 'both')
        if section == 'mids':
            self.mids_radio.setChecked(True)
        elif section == 'finals':
            self.finals_radio.setChecked(True)
        else:
            self.both_radio.setChecked(True)

        # Auto-parse toggle (Feature 1)
        auto_parse = cfg.get('auto_parse_enabled', True)
        self._auto_parse_enabled = auto_parse

    def _connect_settings_persistence(self):
        """Connect all settings widgets to auto-save on change."""
        self.delay_spin.valueChanged.connect(lambda v: self._write_config_key('delay_seconds', v))
        self.pages_spin.valueChanged.connect(lambda v: self._write_config_key('pages_per_batch', v))
        self.reset_spin.valueChanged.connect(lambda v: self._write_config_key('chat_reset_threshold', v))
        self.mcq_reviews_check.stateChanged.connect(
            lambda s: self._write_config_key('reviews_for_mcqs', bool(s)))
        self.notes_reviews_check.stateChanged.connect(
            lambda s: self._write_config_key('reviews_for_notes', bool(s)))
        self.mcq_check.stateChanged.connect(
            lambda s: self._write_config_key('content_mcq', bool(s)))
        self.notes_check.stateChanged.connect(
            lambda s: self._write_config_key('content_notes', bool(s)))
        self.mids_radio.toggled.connect(
            lambda checked: self._write_config_key('selected_section', 'mids') if checked else None)
        self.finals_radio.toggled.connect(
            lambda checked: self._write_config_key('selected_section', 'finals') if checked else None)
        self.both_radio.toggled.connect(
            lambda checked: self._write_config_key('selected_section', 'both') if checked else None)

    # ── Feature 1 + 2: Auto-parse + Ctrl+V protection ─────────

    def _setup_auto_parse(self):
        """
        Feature 1: Auto-parse JSON on paste (with debounce).
        Feature 2: Block double Ctrl+V within 500ms.
        """
        self._auto_parse_timer = QTimer()
        self._auto_parse_timer.setSingleShot(True)
        self._auto_parse_timer.setInterval(350)  # 350ms debounce
        self._auto_parse_timer.timeout.connect(self._auto_submit_if_active)

        self._last_paste_ms = 0  # timestamp of last paste (ms)
        self._paste_block_ms = 600  # block second paste within 600ms

        # Install event filter on json_paste for Ctrl+V detection
        self.json_paste.installEventFilter(self)

        # Also watch text changes to detect paste content landing
        self.json_paste.textChanged.connect(self._on_json_paste_text_changed)

    def eventFilter(self, obj, event):
        """Intercept Ctrl+V on json_paste for double-paste protection."""
        if obj is self.json_paste and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
                import time
                now_ms = int(time.time() * 1000)
                delta = now_ms - self._last_paste_ms
                if delta < self._paste_block_ms and self._last_paste_ms > 0:
                    # Block the second paste
                    self.add_log("⚠️ Duplicate paste blocked (too fast)", "warning")
                    # Flash border orange briefly
                    self.json_paste.setStyleSheet(f"""
                        QPlainTextEdit {{
                            background: {PALETTE['bg']};
                            font-family: 'Consolas', 'Courier New', monospace;
                            font-size: 9.5pt;
                            border: 2px solid {PALETTE['warning']};
                            border-radius: 7px;
                            padding: 8px;
                        }}
                    """)
                    QTimer.singleShot(800, self._reset_paste_border)
                    return True  # Block the event
                self._last_paste_ms = now_ms
        return super().eventFilter(obj, event)

    def _reset_paste_border(self):
        """Reset json_paste border to normal."""
        self.json_paste.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {PALETTE['bg']};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9.5pt;
                border: 1.5px solid {PALETTE['border']};
                border-radius: 7px;
                padding: 8px;
            }}
        """)

    def _on_json_paste_text_changed(self):
        """When text is pasted, start debounce timer for auto-parse."""
        if self._auto_parse_enabled and self.submit_json_btn.isEnabled():
            # Only auto-parse if there's actual content
            if self.json_paste.toPlainText().strip():
                self._auto_parse_timer.start()

    def _auto_submit_if_active(self):
        """Called after debounce — auto-submit if conditions are met."""
        if not self._auto_parse_enabled:
            return
        if not self.submit_json_btn.isEnabled():
            return
        text = self.json_paste.toPlainText().strip()
        if not text:
            return
        # Only auto-submit if it looks like JSON (starts with [ or {)
        if not (text.startswith('[') or text.startswith('{') or '```json' in text or '```' in text):
            return
        self.add_log("⚡ Auto-parsing pasted JSON...", "info")
        self._on_submit_json()

    def set_auto_parse(self, enabled: bool):
        """Toggle auto-parse feature and persist to config."""
        self._auto_parse_enabled = enabled
        self._write_config_key('auto_parse_enabled', enabled)

    # ── Feature 4: Already-processed detection ─────────────

    def _get_current_section_mode(self) -> str:
        """Return 'mids', 'finals', or 'both' based on selected radio."""
        if self.mids_radio.isChecked():
            return 'mids'
        elif self.finals_radio.isChecked():
            return 'finals'
        return 'both'

    def _check_processed_status(self, stable_id: str) -> dict:
        """
        Given a stable ID (e.g., CS01), find the PDF path and check if it's been processed.
        Returns processing status dict or None if not found.
        """
        from folder_organizer import get_processed_pdf_status
        # Reverse lookup: stable_id -> pdf_path
        for pdf_path, sid in self.index_map.items():
            if sid.upper() == stable_id.upper():
                pdf_name = Path(pdf_path).stem
                return get_processed_pdf_status(pdf_name)
        return None

    def _update_selection_warning(self):
        """
        Feature 4: Check each entered ID in selection_input.
        Show a warning label if any are already processed (based on section mode).
        """
        text = self.selection_input.text().strip()
        if not text or not self.index_map:
            self.selection_warning_label.setVisible(False)
            return

        section_mode = self._get_current_section_mode()
        tokens = [t.strip().upper() for t in text.replace(',', ' ').split() if t.strip()]

        # Also handle ranges like CS01-CS05 — extract just the IDs
        ids_to_check = []
        for token in tokens:
            if '-' in token and not token.lstrip('-').isdigit():
                # Could be a range like CS01-CS05 or just CS01
                parts = token.split('-', 1)
                for p in parts:
                    if p and not p.isdigit():
                        ids_to_check.append(p)
            elif not token.isdigit():
                ids_to_check.append(token)

        if not ids_to_check:
            self.selection_warning_label.setVisible(False)
            return

        # Build reverse map: stable_id_upper -> pdf_path
        id_to_path = {sid.upper(): p for p, sid in self.index_map.items()}

        flagged = []
        for sid in ids_to_check:
            if sid not in id_to_path:
                continue
            pdf_path = id_to_path[sid]
            pdf_name = Path(pdf_path).stem
            try:
                from folder_organizer import get_processed_pdf_status
                status = get_processed_pdf_status(pdf_name)
            except Exception:
                continue

            should_flag = False
            if section_mode == 'mids' and status['mids_processed']:
                should_flag = True
            elif section_mode == 'finals' and status['finals_processed']:
                should_flag = True
            elif section_mode == 'both' and (status['mids_processed'] or status['finals_processed']):
                should_flag = True

            if should_flag:
                flagged.append((sid, status))

        if flagged:
            # Build tooltip HTML for hover details
            tooltip_parts = []
            warn_ids = []
            for sid, st in flagged:
                mids_info = f"✓ {st['mids_mcqs']} MCQs, {st['mids_notes']} Notes" if st['mids_processed'] else "✗ Not processed"
                finals_info = f"✓ {st['finals_mcqs']} MCQs, {st['finals_notes']} Notes" if st['finals_processed'] else "✗ Not processed"
                tooltip_parts.append(
                    f"{sid}\n  Mids:   {mids_info}\n  Finals: {finals_info}"
                )
                warn_ids.append(sid)

            tooltip_text = "\n\n".join(tooltip_parts)
            warn_text = ", ".join(warn_ids)

            self.selection_warning_label.setText(
                f"⚠ Already processed: {warn_text}  (hover for details)"
            )
            self.selection_warning_label.setToolTip(tooltip_text)
            self.selection_warning_label.setVisible(True)
        else:
            self.selection_warning_label.setVisible(False)

    # ── Feature 5: Double-click to add index code ─────────────

    def _on_pdf_table_double_click(self, row, col):
        """Feature 5: Double-click a row to add its index code to selection_input."""
        idx_item = self.pdf_table.item(row, 0)
        if not idx_item:
            return
        stable_id = idx_item.data(Qt.UserRole)
        if not stable_id:
            stable_id = idx_item.text()
        if not stable_id:
            return

        current = self.selection_input.text().strip()
        # Avoid duplicates
        existing_ids = [x.strip().upper() for x in current.split(',') if x.strip()]
        if stable_id.upper() not in existing_ids:
            if current:
                self.selection_input.setText(current + ',' + stable_id)
            else:
                self.selection_input.setText(stable_id)

    # ── Feature 6: Processed PDFs search ─────────────────────

    def _setup_processed_search(self):
        """Set up the processed PDFs search data."""
        self._processed_pdfs_data = []  # Will be populated on demand

    def _load_processed_pdfs(self):
        """Scan and load all processed PDFs from JSON output folder."""
        try:
            from folder_organizer import scan_all_processed_pdfs
            self._processed_pdfs_data = scan_all_processed_pdfs()
            self._filter_processed_pdfs()
            count = len(self._processed_pdfs_data)
            self.processed_count_label.setText(f"{count} processed PDFs found")
        except Exception as e:
            self.processed_count_label.setText(f"Scan failed: {str(e)[:50]}")

    def _filter_processed_pdfs(self):
        """Filter processed PDFs based on search text."""
        search = self.processed_search_input.text().strip().lower()
        data = self._processed_pdfs_data

        if search:
            data = [d for d in data
                    if search in d['pdf_name'].lower()
                    or search in d['subject_code'].lower()]

        self.processed_table.setRowCount(0)
        for item in data:
            row = self.processed_table.rowCount()
            self.processed_table.insertRow(row)

            code_item = QTableWidgetItem(item['subject_code'])
            code_item.setTextAlignment(Qt.AlignCenter)
            code_item.setForeground(QColor(PALETTE['accent']))

            name_item = QTableWidgetItem(item['pdf_name'])
            name_item.setForeground(QColor(PALETTE['text_primary']))

            # Status column
            parts = []
            if item['mids_processed']:
                parts.append(f"Mids:{item['mids_mcqs']}MCQs/{item['mids_notes']}Notes")
            if item['finals_processed']:
                parts.append(f"Finals:{item['finals_mcqs']}MCQs/{item['finals_notes']}Notes")
            status_text = "  |  ".join(parts) if parts else "—"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(QColor(PALETTE['success']))
            status_item.setTextAlignment(Qt.AlignCenter)

            self.processed_table.setItem(row, 0, code_item)
            self.processed_table.setItem(row, 1, name_item)
            self.processed_table.setItem(row, 2, status_item)

        self.processed_count_label.setText(f"{len(data)} results")


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
        from folder_organizer import get_json_output_root, get_pdf_output_root
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

        # Auto-fill PDF output directory with dedicated folder
        if not self.pdf_out_path.text().strip():
            pdf_root = get_pdf_output_root()
            self.pdf_out_path.setText(pdf_root)

    def _scan_json_from_root(self, root_path):
        from pdf_generator import scan_json_files
        self.json_files = scan_json_files(root_path)

        # Check which JSON files already have a generated PDF
        from folder_organizer import get_pdf_output_root
        from pdf_generator import get_standardized_pdf_name
        pdf_root = Path(get_pdf_output_root())
        for item in self.json_files:
            json_path = Path(item['path'])
            std_name = get_standardized_pdf_name(str(json_path))
            pdf_sibling = json_path.parent / std_name
            pdf_in_root = pdf_root / std_name
            item['has_pdf'] = pdf_sibling.exists() or pdf_in_root.exists()

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

            from pdf_generator import get_standardized_pdf_name
            pdf_name = get_standardized_pdf_name(item['path'])
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
            from folder_organizer import get_pdf_output_root
            from pdf_generator import get_standardized_pdf_name
            pdf_root = Path(get_pdf_output_root())
            for item in self.json_files:
                json_path = Path(item['path'])
                std_name = get_standardized_pdf_name(str(json_path))
                pdf_sibling = json_path.parent / std_name
                pdf_in_root = pdf_root / std_name
                item['has_pdf'] = pdf_sibling.exists() or pdf_in_root.exists()

            converted_count = len([f for f in self.json_files if f.get('has_pdf')])
            self.converted_toggle_btn.setText(f"{'Hide' if self.show_converted else 'Show'} Converted ({converted_count})")
            self._filter_json_list()
            self._refresh_generated_pdfs_table()

            QMessageBox.information(self, "Done", message)
        else:
            self._add_gen_log(f"Error: {message}", "error")
            QMessageBox.critical(self, "Error", message)


# ─────────────────────────────────────────────────────────────
#  REVIEW WORKER THREADS (prevent UI freezing on large data)
# ─────────────────────────────────────────────────────────────
class GeminiSendThread(QThread):
    """Background thread for sending reviews to Gemini (health check + reset + send)"""
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, raw_text):
        super().__init__()
        self.raw_text = raw_text

    def run(self):
        try:
            from gemini_client import GeminiClient
            client = GeminiClient()

            self.log_signal.emit("Checking server health...", "info")
            if not client.check_health():
                raise Exception("Gemini server is not running or not initialized")

            self.log_signal.emit("Resetting chat for clean context...", "info")
            client.reset_chat()

            self.log_signal.emit(f"Sending {len(self.raw_text)} chars to Gemini...", "info")
            client.send_prompt(
                self.raw_text,
                section='reviews',
                pages_count=1,
                content_type='reviews'
            )

            self.finished_signal.emit(True, "Reviews sent to Gemini successfully")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class ReviewsImportThread(QThread):
    """Background thread for parsing and importing large JSON review data"""
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(str)              # emits status text for each subject
    finished_signal = pyqtSignal(bool, str, dict)  # success, message, results_dict

    def __init__(self, json_text, category='uncategorized'):
        super().__init__()
        self.json_text = json_text
        self.category = category

    def run(self):
        try:
            import json_fixer
            from reviews_manager import add_reviews

            self.log_signal.emit("Parsing JSON...", "info")
            reviews = json_fixer.fix_json(self.json_text, 'reviews')

            if not reviews or len(reviews) == 0:
                raise Exception("No valid reviews found in JSON")

            self.log_signal.emit(f"✓ Parsed {len(reviews)} valid reviews — starting import ({self.category})...", "success")

            # Group by subject code so we can show per-subject progress
            grouped = {}
            for review in reviews:
                code = review.get('subject_code', 'UNKNOWN').upper().strip()
                grouped.setdefault(code, []).append(review)

            total_subjects = len(grouped)
            all_results = {}

            for i, (subject_code, subject_reviews) in enumerate(sorted(grouped.items()), 1):
                # Update status label with current subject
                self.progress_signal.emit(
                    f"⏳ Importing {subject_code}... ({i}/{total_subjects})"
                )
                self.log_signal.emit(
                    f"  → {subject_code}: processing {len(subject_reviews)} review(s)", "info"
                )

                # Import only this subject's reviews with category
                result = add_reviews(subject_reviews, category=self.category)
                added = result.get(subject_code, 0)
                all_results[subject_code] = added

                self.log_signal.emit(
                    f"  ✓ {subject_code}: {added} new review(s) saved [{self.category}]", "success"
                )

            total_added = sum(all_results.values())
            self.finished_signal.emit(True, f"Imported {total_added} reviews [{self.category}]", all_results)

        except Exception as e:
            self.finished_signal.emit(False, str(e), {})




# ─────────────────────────────────────────────────────────────
#  REVIEWS TAB
# ─────────────────────────────────────────────────────────────
class ReviewsTab(QWidget):
    """Tab for structuring, importing, and managing student reviews"""
    def __init__(self):
        super().__init__()
        self._send_thread = None
        self._import_thread = None
        self._build_ui()
        self._refresh_dashboard()

    def _read_config(self):
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    # ── Category selector helper (reused in sections A and B) ─────

    def _build_category_selector(self, parent_layout, prefix):
        """Build a category radio button group with optional custom input.
        Returns (button_group, custom_input) tuple.
        prefix is used to differentiate widget names."""
        cat_card, cat_layout = make_card('v', (12, 10, 12, 10), 6)
        cat_layout.addWidget(label_secondary("Review Category"))

        btn_group = QButtonGroup()
        mids_rb = QRadioButton("Mids")
        finals_rb = QRadioButton("Finals")
        custom_rb = QRadioButton("Custom Category")
        mids_rb.setChecked(True)

        for rb in [mids_rb, finals_rb, custom_rb]:
            cat_layout.addWidget(rb)
            btn_group.addButton(rb)

        # Custom category input (hidden by default)
        custom_row = QHBoxLayout()
        custom_input = QComboBox()
        custom_input.setEditable(True)
        custom_input.setMinimumHeight(30)
        custom_input.setMinimumWidth(180)
        custom_input.addItems(["9th Class", "10th Class", "Entry Test", "Custom Syllabus"])
        custom_input.setCurrentText("")
        custom_input.lineEdit().setPlaceholderText("Type or select category...")
        custom_input.setVisible(False)
        custom_row.addWidget(custom_input)
        custom_row.addStretch()
        cat_layout.addLayout(custom_row)

        # Toggle custom input visibility
        def on_toggle():
            custom_input.setVisible(custom_rb.isChecked())
        mids_rb.toggled.connect(on_toggle)
        finals_rb.toggled.connect(on_toggle)
        custom_rb.toggled.connect(on_toggle)

        parent_layout.addWidget(cat_card)

        # Store references
        setattr(self, f'{prefix}_mids_rb', mids_rb)
        setattr(self, f'{prefix}_finals_rb', finals_rb)
        setattr(self, f'{prefix}_custom_rb', custom_rb)
        setattr(self, f'{prefix}_custom_input', custom_input)
        setattr(self, f'{prefix}_btn_group', btn_group)

        return btn_group, custom_input

    def _get_selected_category(self, prefix):
        """Get the selected category name from a category selector."""
        mids_rb = getattr(self, f'{prefix}_mids_rb')
        finals_rb = getattr(self, f'{prefix}_finals_rb')
        custom_rb = getattr(self, f'{prefix}_custom_rb')
        custom_input = getattr(self, f'{prefix}_custom_input')

        if mids_rb.isChecked():
            return 'mids'
        elif finals_rb.isChecked():
            return 'finals'
        elif custom_rb.isChecked():
            text = custom_input.currentText().strip()
            if text:
                return text.lower().replace(' ', '_')
            return 'custom'
        return 'uncategorized'

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(12)

        # Prevent horizontal overflow
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        # ── Header ────────────────────────────────────────────
        header_row = QHBoxLayout()
        title_lbl = QLabel("Reviews Manager")
        title_lbl.setStyleSheet(f"color: {PALETTE['navy']}; font-size: 14pt; font-weight: 700;")
        desc_lbl = label_muted("Structure, import, and manage student course reviews")
        header_row.addWidget(title_lbl)
        header_row.addWidget(desc_lbl)
        header_row.addStretch()
        root_layout.addLayout(header_row)

        root_layout.addWidget(divider())

        # ══════════════════════════════════════════════════════
        # SECTION A: Generate Structured Reviews via Gemini
        # ══════════════════════════════════════════════════════
        gen_card, gen_layout = make_card('v', (16, 14, 16, 14), 10)

        gen_header = QHBoxLayout()
        gen_title = QLabel("① Generate Structured Reviews")
        gen_title.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 11pt; font-weight: 700;")
        gen_header.addWidget(gen_title)
        gen_header.addStretch()

        gen_hint = label_muted("Paste raw reviews or upload file → Send to Gemini → Get structured JSON")
        gen_header.addWidget(gen_hint)
        gen_layout.addLayout(gen_header)

        # Category selector for generation
        self._build_category_selector(gen_layout, 'gen')

        gen_layout.addWidget(label_secondary("Raw Reviews Text"))

        # File upload row
        upload_row = QHBoxLayout()
        upload_row.setSpacing(8)

        self.upload_file_btn = QPushButton("📁 Upload File (PDF/DOCX/TXT)")
        self.upload_file_btn.setMinimumHeight(32)
        self.upload_file_btn.setMinimumWidth(250)
        self.upload_file_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['surface']};
                border: 1.5px dashed {PALETTE['border']};
                border-radius: 7px;
                color: {PALETTE['text_secondary']};
                font-size: 9.5pt;
                padding: 5px 16px;
            }}
            QPushButton:hover {{
                border-color: {PALETTE['accent']};
                color: {PALETTE['accent']};
                background: {PALETTE['row_hover']};
            }}
        """)
        self.upload_file_btn.clicked.connect(self._upload_file_for_text)
        upload_row.addWidget(self.upload_file_btn)

        self.upload_status = label_muted("")
        upload_row.addWidget(self.upload_status, 1)
        upload_row.addStretch()
        gen_layout.addLayout(upload_row)

        self.raw_reviews_input = QPlainTextEdit()
        self.raw_reviews_input.setPlaceholderText(
            "Paste bulk unstructured reviews here...\n\n"
            "They can be in any language (Urdu, Roman Urdu, English, etc.)\n"
            "Unrelated text will be filtered out by Gemini.\n\n"
            "Or use the 'Upload File' button above to extract text from PDF/Word/TXT files.\n\n"
            "Example:\n"
            "MGT501 ka paper easy tha, bas lectures ache se parho\n"
            "CS101 mein loops se bohat questions aaye 15/03/2024"
        )
        self.raw_reviews_input.setMinimumHeight(120)
        self.raw_reviews_input.setMaximumHeight(180)
        self.raw_reviews_input.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {PALETTE['bg']};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9.5pt;
                border: 1.5px solid {PALETTE['border']};
                border-radius: 7px;
                padding: 8px;
            }}
        """)
        gen_layout.addWidget(self.raw_reviews_input)

        send_row = QHBoxLayout()
        self.send_to_gemini_btn = QPushButton("Send to Gemini for Structuring")
        self.send_to_gemini_btn.setObjectName("primary")
        self.send_to_gemini_btn.setMinimumHeight(36)
        self.send_to_gemini_btn.setMinimumWidth(280)
        self.send_to_gemini_btn.clicked.connect(self._send_reviews_to_gemini)
        send_row.addStretch()
        send_row.addWidget(self.send_to_gemini_btn)
        send_row.addStretch()
        gen_layout.addLayout(send_row)

        # Status label
        self.gemini_status_label = label_muted("Ready to send")
        self.gemini_status_label.setAlignment(Qt.AlignCenter)
        gen_layout.addWidget(self.gemini_status_label)

        root_layout.addWidget(gen_card)

        # ══════════════════════════════════════════════════════
        # SECTION B: Import Structured JSON Reviews
        # ══════════════════════════════════════════════════════
        import_card, import_layout = make_card('v', (16, 14, 16, 14), 10)

        import_header = QHBoxLayout()
        import_title = QLabel("② Import Structured JSON")
        import_title.setStyleSheet(f"color: {PALETTE['success']}; font-size: 11pt; font-weight: 700;")
        import_header.addWidget(import_title)
        import_header.addStretch()

        import_hint = label_muted("Paste generated JSON or import file → Reviews get added category-wise")
        import_header.addWidget(import_hint)
        import_layout.addLayout(import_header)

        # Category selector for import
        self._build_category_selector(import_layout, 'imp')

        import_layout.addWidget(label_secondary("Structured JSON"))

        # JSON file import row
        json_import_row = QHBoxLayout()
        json_import_row.setSpacing(8)

        self.import_json_file_btn = QPushButton("📄 Import JSON File")
        self.import_json_file_btn.setMinimumHeight(32)
        self.import_json_file_btn.setMinimumWidth(180)
        self.import_json_file_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['surface']};
                border: 1.5px dashed {PALETTE['border']};
                border-radius: 7px;
                color: {PALETTE['text_secondary']};
                font-size: 9.5pt;
                padding: 5px 16px;
            }}
            QPushButton:hover {{
                border-color: {PALETTE['success']};
                color: {PALETTE['success']};
                background: {PALETTE['row_hover']};
            }}
        """)
        self.import_json_file_btn.clicked.connect(self._import_json_file)
        json_import_row.addWidget(self.import_json_file_btn)

        self.json_file_status = label_muted("")
        json_import_row.addWidget(self.json_file_status, 1)
        json_import_row.addStretch()
        import_layout.addLayout(json_import_row)

        self.json_import_input = QPlainTextEdit()
        self.json_import_input.setPlaceholderText(
            'Paste the structured JSON from Gemini here, or use "Import JSON File" above...\n\n'
            'Expected format:\n'
            '[\n'
            '  {"subject_code": "MGT501", "review": "...", "review_date": "2024-03-15"},\n'
            '  {"subject_code": "CS101", "review": "...", "review_date": null}\n'
            ']'
        )
        self.json_import_input.setMinimumHeight(100)
        self.json_import_input.setMaximumHeight(160)
        self.json_import_input.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {PALETTE['bg']};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9.5pt;
                border: 1.5px solid {PALETTE['border']};
                border-radius: 7px;
                padding: 8px;
            }}
        """)
        import_layout.addWidget(self.json_import_input)

        import_btn_row = QHBoxLayout()
        self.import_btn = QPushButton("Import Reviews")
        self.import_btn.setObjectName("success")
        self.import_btn.setMinimumHeight(36)
        self.import_btn.setMinimumWidth(200)
        self.import_btn.clicked.connect(self._import_reviews)
        import_btn_row.addStretch()
        import_btn_row.addWidget(self.import_btn)
        import_btn_row.addStretch()
        import_layout.addLayout(import_btn_row)

        # Import status — with word wrap to prevent overflow
        self.import_status_label = label_muted("")
        self.import_status_label.setAlignment(Qt.AlignCenter)
        self.import_status_label.setWordWrap(True)
        self.import_status_label.setMaximumWidth(800)
        import_layout.addWidget(self.import_status_label)

        root_layout.addWidget(import_card)

        # ══════════════════════════════════════════════════════
        # SECTION C: Reviews Dashboard
        # ══════════════════════════════════════════════════════
        dash_card, dash_layout = make_card('v', (16, 14, 16, 14), 10)

        dash_header = QHBoxLayout()
        dash_title = QLabel("③ Reviews Dashboard")
        dash_title.setStyleSheet(f"color: {PALETTE['navy']}; font-size: 11pt; font-weight: 700;")
        dash_header.addWidget(dash_title)
        dash_header.addStretch()

        self.refresh_dash_btn = QPushButton("  Refresh  ")
        self.refresh_dash_btn.setFixedHeight(32)
        self.refresh_dash_btn.setMinimumWidth(90)
        self.refresh_dash_btn.clicked.connect(self._refresh_dashboard)
        dash_header.addWidget(self.refresh_dash_btn)
        dash_layout.addLayout(dash_header)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)

        def _stat_card(title_text):
            sc, sl = make_card('v', (12, 10, 12, 10), 4)
            sc.setStyleSheet(f"""
                QFrame#card {{
                    background: {PALETTE['bg']};
                    border: 1.5px solid {PALETTE['border']};
                    border-radius: 8px;
                }}
            """)
            sl.addWidget(label_secondary(title_text))
            return sc, sl

        stat1_card, stat1_layout = _stat_card("Total Reviews")
        self.total_reviews_val = QLabel("0")
        self.total_reviews_val.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 18pt; font-weight: 700;")
        stat1_layout.addWidget(self.total_reviews_val)
        stats_row.addWidget(stat1_card)

        stat2_card, stat2_layout = _stat_card("Subjects Covered")
        self.total_subjects_val = QLabel("0")
        self.total_subjects_val.setStyleSheet(f"color: {PALETTE['success']}; font-size: 18pt; font-weight: 700;")
        stat2_layout.addWidget(self.total_subjects_val)
        stats_row.addWidget(stat2_card)

        stat3_card, stat3_layout = _stat_card("Categories")
        self.categories_val = QLabel("—")
        self.categories_val.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 9pt; font-weight: 500;")
        self.categories_val.setWordWrap(True)
        stat3_layout.addWidget(self.categories_val)
        stats_row.addWidget(stat3_card)

        stat4_card, stat4_layout = _stat_card("Storage")
        self.storage_val = QLabel("—")
        self.storage_val.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 9pt; font-weight: 500;")
        self.storage_val.setWordWrap(True)
        stat4_layout.addWidget(self.storage_val)
        stats_row.addWidget(stat4_card)

        dash_layout.addLayout(stats_row)

        # ── Category filter buttons row ───────────────────────
        dash_layout.addWidget(label_secondary("Filter by Category"))

        cat_filter_container = QHBoxLayout()
        cat_filter_container.setSpacing(6)

        self.cat_all_btn = QPushButton("All")
        self.cat_all_btn.setFixedHeight(28)
        self.cat_all_btn.setMinimumWidth(60)
        self.cat_all_btn.setCheckable(True)
        self.cat_all_btn.setChecked(True)
        self.cat_all_btn.clicked.connect(lambda: self._set_dash_category_filter('all'))
        self._cat_filter_btns = {'all': self.cat_all_btn}
        self._active_cat_filter = 'all'
        self._style_cat_filter_btn(self.cat_all_btn, True)
        cat_filter_container.addWidget(self.cat_all_btn)
        cat_filter_container.addStretch()

        self.cat_filter_row = cat_filter_container
        cat_filter_widget = QWidget()
        cat_filter_widget.setLayout(cat_filter_container)
        cat_filter_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        dash_layout.addWidget(cat_filter_widget)

        # ── Search bar ────────────────────────────────────────
        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.dash_search_input = QLineEdit()
        self.dash_search_input.setPlaceholderText("🔍 Search subjects (e.g., CS101, MGT)...")
        self.dash_search_input.setMinimumHeight(32)
        self.dash_search_input.textChanged.connect(self._filter_dashboard)
        search_row.addWidget(self.dash_search_input, 3)

        self.dash_result_count = label_muted("0 subjects")
        self.dash_result_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        search_row.addWidget(self.dash_result_count)
        dash_layout.addLayout(search_row)

        # Reviews table (5 columns: #, Subject, Category, Count, Date)
        self.reviews_table = QTableWidget(0, 5)
        self.reviews_table.setHorizontalHeaderLabels(["#", "Subject Code", "Category", "Reviews Count", "Latest Date"])
        self.reviews_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.reviews_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.reviews_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.reviews_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.reviews_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        self.reviews_table.setColumnWidth(0, 44)
        self.reviews_table.setColumnWidth(2, 100)
        self.reviews_table.setColumnWidth(3, 110)
        self.reviews_table.setColumnWidth(4, 110)
        self.reviews_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.reviews_table.setAlternatingRowColors(True)
        self.reviews_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.reviews_table.verticalHeader().setVisible(False)
        self.reviews_table.setMinimumHeight(140)
        self.reviews_table.setMaximumHeight(300)
        self.reviews_table.setShowGrid(False)
        self.reviews_table.setStyleSheet(f"""
            QTableWidget {{
                alternate-background-color: {PALETTE['row_alt']};
            }}
        """)
        dash_layout.addWidget(self.reviews_table)

        # Delete button
        del_row = QHBoxLayout()
        del_row.addStretch()
        self.delete_reviews_btn = QPushButton("Delete Selected Subject Reviews")
        self.delete_reviews_btn.setObjectName("danger")
        self.delete_reviews_btn.setMinimumHeight(32)
        self.delete_reviews_btn.clicked.connect(self._delete_selected_reviews)
        del_row.addWidget(self.delete_reviews_btn)
        dash_layout.addLayout(del_row)

        root_layout.addWidget(dash_card)

        # ── Log card ──────────────────────────────────────────
        log_card, log_layout = make_card('v', (14, 12, 14, 12), 8)

        log_header = QHBoxLayout()
        log_header.addWidget(label_secondary("Reviews Log"))
        log_header.addStretch()
        clr = QPushButton("Clear")
        clr.setFixedWidth(56)
        clr.setFixedHeight(24)
        clr.setStyleSheet("font-size: 8.5pt; padding: 2px 8px;")
        clr.clicked.connect(lambda: self.reviews_log.clear())
        log_header.addWidget(clr)
        log_layout.addLayout(log_header)

        self.reviews_log = QTextEdit()
        self.reviews_log.setReadOnly(True)
        self.reviews_log.setMinimumHeight(100)
        self.reviews_log.setMaximumHeight(180)
        self.reviews_log.setStyleSheet(f"""
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
        log_layout.addWidget(self.reviews_log)
        root_layout.addWidget(log_card)
        root_layout.addStretch()

        # ── Internal state ────────────────────────────────────
        self._dash_data = []        # Flat list of {subject_code, category, count, last_date}

    # ── Style helpers ─────────────────────────────────────────

    def _style_cat_filter_btn(self, btn, active=False):
        if active:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['accent']};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 9pt;
                    font-weight: 600;
                    padding: 4px 14px;
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['surface']};
                    border: 1.5px solid {PALETTE['border']};
                    border-radius: 6px;
                    color: {PALETTE['text_secondary']};
                    font-size: 9pt;
                    padding: 4px 14px;
                }}
                QPushButton:hover {{
                    border-color: {PALETTE['accent']};
                    color: {PALETTE['accent']};
                }}
            """)

    # ── Log helper ────────────────────────────────────────────

    def _add_log(self, message, level="info"):
        colors = {
            "info":    "#79c0ff",
            "success": "#56d364",
            "warning": "#e3b341",
            "error":   "#f85149",
        }
        color = colors.get(level, "#c9d1d9")
        html = f'<span style="color:{color};">{message}</span>'
        cursor = self.reviews_log.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.reviews_log.setTextCursor(cursor)
        self.reviews_log.insertHtml(html + "<br>")
        self.reviews_log.verticalScrollBar().setValue(self.reviews_log.verticalScrollBar().maximum())

    # ── File Upload (Section A) ───────────────────────────────

    def _upload_file_for_text(self):
        """Upload a PDF/DOCX/TXT file and extract text into the raw reviews input"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select File for Text Extraction", os.path.expanduser("~"),
            "Supported Files (*.pdf *.docx *.doc *.txt *.rtf);;PDF Files (*.pdf);;Word Files (*.docx *.doc);;Text Files (*.txt *.rtf);;All Files (*)"
        )
        if not file_path:
            return

        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix.lower()
        self.upload_status.setText(f"⏳ Extracting text from {file_name}...")
        self.upload_status.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 9pt; font-weight: 500;")

        try:
            extracted_text = ""

            if file_ext == '.pdf':
                import fitz  # PyMuPDF — already a dependency
                doc = fitz.open(file_path)
                pages_text = []
                for page in doc:
                    pages_text.append(page.get_text())
                doc.close()
                extracted_text = "\n\n".join(pages_text)

            elif file_ext in ['.docx', '.doc']:
                try:
                    from docx import Document
                    doc = Document(file_path)
                    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                    extracted_text = "\n".join(paragraphs)
                except ImportError:
                    QMessageBox.warning(self, "Missing Dependency",
                        "python-docx is required for Word files.\n\nInstall it with: pip install python-docx")
                    return

            elif file_ext in ['.txt', '.rtf']:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    extracted_text = f.read()

            else:
                QMessageBox.warning(self, "Unsupported", f"File type '{file_ext}' is not supported.")
                return

            if not extracted_text.strip():
                self.upload_status.setText(f"⚠️ No text found in {file_name}")
                self.upload_status.setStyleSheet(f"color: {PALETTE['warning']}; font-size: 9pt;")
                self._add_log(f"⚠️ No text extracted from {file_name}", "warning")
                return

            self.raw_reviews_input.setPlainText(extracted_text)
            char_count = len(extracted_text)
            self.upload_status.setText(f"✓ {file_name} — {char_count:,} chars extracted")
            self.upload_status.setStyleSheet(f"color: {PALETTE['success']}; font-size: 9pt; font-weight: 500;")
            self._add_log(f"✓ Extracted {char_count:,} chars from {file_name}", "success")

        except Exception as e:
            self.upload_status.setText(f"❌ Failed: {str(e)[:60]}")
            self.upload_status.setStyleSheet(f"color: {PALETTE['error']}; font-size: 9pt;")
            self._add_log(f"❌ File extraction failed: {str(e)}", "error")

    # ── JSON File Import (Section B) ──────────────────────────

    def _import_json_file(self):
        """Import a JSON file, validate it, and populate the import field"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import JSON Reviews File", os.path.expanduser("~"),
            "JSON Files (*.json);;All Files (*)"
        )
        if not file_path:
            return

        file_name = Path(file_path).name

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            if not raw_content.strip():
                QMessageBox.warning(self, "Empty File", f"{file_name} is empty.")
                return

            try:
                import json_fixer
                reviews = json_fixer.fix_json(raw_content, 'reviews')

                if reviews and len(reviews) > 0:
                    self.json_file_status.setText(f"✓ {file_name} — {len(reviews)} valid reviews")
                    self.json_file_status.setStyleSheet(f"color: {PALETTE['success']}; font-size: 9pt; font-weight: 500;")
                    self.json_import_input.setPlainText(raw_content)
                    self._add_log(f"✓ Loaded {file_name}: {len(reviews)} valid reviews found", "success")
                else:
                    self.json_file_status.setText(f"⚠️ {file_name} — no valid reviews found")
                    self.json_file_status.setStyleSheet(f"color: {PALETTE['warning']}; font-size: 9pt;")
                    self.json_import_input.setPlainText(raw_content)
                    self._add_log(f"⚠️ {file_name}: JSON loaded but no valid reviews detected", "warning")

            except Exception as e:
                self.json_file_status.setText(f"⚠️ {file_name} — needs fixing: {str(e)[:40]}")
                self.json_file_status.setStyleSheet(f"color: {PALETTE['warning']}; font-size: 9pt;")
                self.json_import_input.setPlainText(raw_content)
                self._add_log(f"⚠️ {file_name}: JSON validation issue — {str(e)}", "warning")
                self._add_log("Content loaded into editor for manual correction", "info")

        except Exception as e:
            self.json_file_status.setText(f"❌ Failed: {str(e)[:50]}")
            self.json_file_status.setStyleSheet(f"color: {PALETTE['error']}; font-size: 9pt;")
            self._add_log(f"❌ Failed to read {file_name}: {str(e)}", "error")

    # ── Section A: Send to Gemini (background thread) ─────────

    def _send_reviews_to_gemini(self):
        """Send raw reviews text to Gemini for structuring — runs in background thread"""
        raw_text = self.raw_reviews_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.warning(self, "Empty", "Paste raw reviews text first or upload a file.")
            return

        if len(raw_text) < 20:
            QMessageBox.warning(self, "Too Short", "The text seems too short. Paste more reviews.")
            return

        category = self._get_selected_category('gen')
        self.gemini_status_label.setText(f"⏳ Sending to Gemini [{category}]...")
        self.gemini_status_label.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 9pt; font-weight: 600;")
        self.send_to_gemini_btn.setEnabled(False)
        self._add_log(f"Sending {len(raw_text)} chars of raw reviews to Gemini [{category}]...", "info")

        self._send_thread = GeminiSendThread(raw_text)
        self._send_thread.log_signal.connect(self._add_log)
        self._send_thread.finished_signal.connect(self._on_gemini_send_done)
        self._send_thread.start()

    def _on_gemini_send_done(self, success, message):
        """Callback when Gemini send thread completes"""
        self.send_to_gemini_btn.setEnabled(True)
        if success:
            category = self._get_selected_category('gen')
            self.gemini_status_label.setText(f"✓ Sent! Copy the JSON response from Gemini and paste it below ↓ [Category: {category}]")
            self.gemini_status_label.setStyleSheet(f"color: {PALETTE['success']}; font-size: 9pt; font-weight: 600;")
            self._add_log("✓ Reviews sent to Gemini successfully. Copy the JSON response and paste it in the Import section.", "success")
            self._sync_category_to_import()
        else:
            self.gemini_status_label.setText(f"❌ Failed: {message}")
            self.gemini_status_label.setStyleSheet(f"color: {PALETTE['error']}; font-size: 9pt;")
            self._add_log(f"❌ Send failed: {message}", "error")

    def _sync_category_to_import(self):
        """Sync the generation category selection to the import section"""
        gen_category = self._get_selected_category('gen')
        if gen_category == 'mids':
            self.imp_mids_rb.setChecked(True)
        elif gen_category == 'finals':
            self.imp_finals_rb.setChecked(True)
        else:
            self.imp_custom_rb.setChecked(True)
            self.imp_custom_input.setCurrentText(gen_category.replace('_', ' ').title())

    # ── Section B: Import JSON Reviews (background thread) ────

    def _import_reviews(self):
        """Parse and import structured JSON reviews — runs in background thread"""
        json_text = self.json_import_input.toPlainText().strip()
        if not json_text:
            QMessageBox.warning(self, "Empty", "Paste the structured JSON first or import a JSON file.")
            return

        category = self._get_selected_category('imp')

        self.import_btn.setEnabled(False)
        self.import_status_label.setText(f"⏳ Processing [{category}]...")
        self.import_status_label.setStyleSheet(f"color: {PALETTE['accent']}; font-size: 9pt; font-weight: 600;")
        self._add_log(f"Starting import in background [{category}]...", "info")

        self._import_thread = ReviewsImportThread(json_text, category=category)
        self._import_thread.log_signal.connect(self._add_log)
        self._import_thread.progress_signal.connect(self._on_import_progress)
        self._import_thread.finished_signal.connect(self._on_import_done)
        self._import_thread.start()

    def _on_import_progress(self, status_text):
        """Update the status label in real-time as each subject is imported"""
        self.import_status_label.setText(status_text)
        self.import_status_label.setStyleSheet(
            f"color: {PALETTE['accent']}; font-size: 9pt; font-weight: 600;"
        )

    def _on_import_done(self, success, message, results):
        """Callback when import thread completes"""
        self.import_btn.setEnabled(True)
        if success:
            subject_count = len(results)
            if subject_count <= 8:
                msg_parts = [f"{code}: +{count}" for code, count in sorted(results.items())]
                summary_text = f"✓ {message}: {', '.join(msg_parts)}"
            else:
                first_5 = list(sorted(results.items()))[:5]
                msg_parts = [f"{code}: +{count}" for code, count in first_5]
                summary_text = f"✓ {message} ({subject_count} subjects): {', '.join(msg_parts)} ... +{subject_count - 5} more"

            detailed_logs = [f"  {code}: {count} reviews added" for code, count in sorted(results.items())]
            if detailed_logs:
                self._add_log("<br>".join(detailed_logs), "success")

            self.import_status_label.setText(summary_text)
            self.import_status_label.setStyleSheet(f"color: {PALETTE['success']}; font-size: 9pt; font-weight: 600;")
            self._add_log(f"✅ {message}!", "success")
            self.json_import_input.clear()
            self._refresh_dashboard()
        else:
            self.import_status_label.setText(f"❌ Import failed: {message}")
            self.import_status_label.setStyleSheet(f"color: {PALETTE['error']}; font-size: 9pt;")
            self._add_log(f"❌ Import failed: {message}", "error")

    # ── Section C: Dashboard ──────────────────────────────────

    def _set_dash_category_filter(self, category):
        """Set the active category filter for the dashboard"""
        self._active_cat_filter = category
        for cat_name, btn in self._cat_filter_btns.items():
            self._style_cat_filter_btn(btn, active=(cat_name == category))
        self._filter_dashboard()

    def _filter_dashboard(self):
        """Filter the dashboard table based on search and category filter"""
        search = self.dash_search_input.text().strip().upper()
        cat_filter = self._active_cat_filter

        filtered = self._dash_data
        if cat_filter != 'all':
            filtered = [d for d in filtered if d['category'] == cat_filter]
        if search:
            filtered = [d for d in filtered if search in d['subject_code'].upper()]

        self._populate_dash_table(filtered)
        self.dash_result_count.setText(f"{len(filtered)} subjects")

    def _populate_dash_table(self, data):
        """Populate the reviews dashboard table"""
        self.reviews_table.setRowCount(0)
        for i, item in enumerate(data, 1):
            row = self.reviews_table.rowCount()
            self.reviews_table.insertRow(row)

            idx_item = QTableWidgetItem(str(i))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QColor(PALETTE['text_muted']))

            code_item = QTableWidgetItem(item['subject_code'])
            code_item.setForeground(QColor(PALETTE['accent']))
            code_item.setData(Qt.UserRole, item['subject_code'])
            code_item.setData(Qt.UserRole + 1, item['category'])

            cat_item = QTableWidgetItem(item['category'].replace('_', ' ').title())
            cat_item.setTextAlignment(Qt.AlignCenter)
            if item['category'] == 'mids':
                cat_item.setForeground(QColor(PALETTE['accent']))
            elif item['category'] == 'finals':
                cat_item.setForeground(QColor(PALETTE['success']))
            else:
                cat_item.setForeground(QColor(PALETTE['warning']))

            count_item = QTableWidgetItem(str(item['count']))
            count_item.setTextAlignment(Qt.AlignCenter)
            count_item.setForeground(QColor(PALETTE['success']))

            date_item = QTableWidgetItem(item.get('last_date') or '—')
            date_item.setTextAlignment(Qt.AlignCenter)
            date_item.setForeground(QColor(PALETTE['text_secondary']))

            self.reviews_table.setItem(row, 0, idx_item)
            self.reviews_table.setItem(row, 1, code_item)
            self.reviews_table.setItem(row, 2, cat_item)
            self.reviews_table.setItem(row, 3, count_item)
            self.reviews_table.setItem(row, 4, date_item)

    def _refresh_dashboard(self):
        """Refresh the reviews dashboard with current data"""
        try:
            from reviews_manager import get_all_review_stats, get_all_categories
            from folder_organizer import get_json_output_root

            stats = get_all_review_stats()
            all_categories = get_all_categories()

            self._dash_data = []
            total_reviews = 0
            cat_counts = {}

            for subject_code, info in sorted(stats.items()):
                categories = info.get('categories', {})
                for cat, cat_info in categories.items():
                    count = cat_info.get('count', 0)
                    self._dash_data.append({
                        'subject_code': subject_code,
                        'category': cat,
                        'count': count,
                        'last_date': cat_info.get('last_date')
                    })
                    total_reviews += count
                    cat_counts[cat] = cat_counts.get(cat, 0) + count

            total_subjects = len(stats)

            self.total_reviews_val.setText(str(total_reviews))
            self.total_subjects_val.setText(str(total_subjects))
            self.storage_val.setText(get_json_output_root())

            if cat_counts:
                cat_parts = [f"{cat.replace('_', ' ').title()}: {cnt}" for cat, cnt in sorted(cat_counts.items())]
                self.categories_val.setText(" | ".join(cat_parts))
            else:
                self.categories_val.setText("—")

            self._update_category_filter_buttons(all_categories, cat_counts)
            self._filter_dashboard()

            if total_reviews > 0:
                self._add_log(f"Dashboard refreshed: {total_reviews} reviews across {total_subjects} subjects", "info")
            else:
                self._add_log("No reviews stored yet. Generate or import reviews to get started.", "info")

        except Exception as e:
            self._add_log(f"Dashboard refresh failed: {str(e)}", "error")

    def _update_category_filter_buttons(self, all_categories, cat_counts):
        """Dynamically update category filter buttons"""
        for key in list(self._cat_filter_btns.keys()):
            if key != 'all':
                btn = self._cat_filter_btns.pop(key)
                self.cat_filter_row.removeWidget(btn)
                btn.deleteLater()

        total = sum(cat_counts.values())
        self.cat_all_btn.setText(f"All ({total})")
        self._style_cat_filter_btn(self.cat_all_btn, self._active_cat_filter == 'all')

        for cat in sorted(all_categories):
            count = cat_counts.get(cat, 0)
            display_name = cat.replace('_', ' ').title()
            btn = QPushButton(f"{display_name} ({count})")
            btn.setFixedHeight(28)
            btn.setMinimumWidth(60)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, c=cat: self._set_dash_category_filter(c))
            self._style_cat_filter_btn(btn, self._active_cat_filter == cat)
            self.cat_filter_row.insertWidget(self.cat_filter_row.count() - 1, btn)
            self._cat_filter_btns[cat] = btn

    def _delete_selected_reviews(self):
        """Delete reviews for the selected subject"""
        selected = self.reviews_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a subject row to delete.")
            return

        row = selected[0].row()
        code_item = self.reviews_table.item(row, 1)
        if not code_item:
            return

        subject_code = code_item.data(Qt.UserRole)
        category = code_item.data(Qt.UserRole + 1)
        count_item = self.reviews_table.item(row, 3)
        count = count_item.text() if count_item else "?"

        reply = QMessageBox.question(self, "Delete Reviews?",
            f"Delete all {count} reviews for {subject_code} [{category}]?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                from reviews_manager import ReviewsManager
                mgr = ReviewsManager()
                mgr.delete_reviews(subject_code, category=category)
                self._add_log(f"✓ Deleted reviews for {subject_code} [{category}]", "success")
                self._refresh_dashboard()
            except Exception as e:
                self._add_log(f"❌ Delete failed: {str(e)}", "error")


# ─────────────────────────────────────────────────────────────
#  EDIT PDF TAB — Now imported from pdf_editor.py
#  (EditPDFTab is imported at the top of this file)
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
        for i, text in enumerate(["Processing", "PDF Generator", "Reviews", "Edit PDF"]):
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

        # ── Feature 1: Auto-Parse toggle button in navbar ─────
        nav_sep = QLabel("|")
        nav_sep.setStyleSheet(f"color: {PALETTE['text_muted']}; padding: 0 8px; font-size: 14pt;")
        nav_layout.addWidget(nav_sep)

        self.auto_parse_btn = QPushButton("⚡ Auto-Parse")
        self.auto_parse_btn.setCheckable(True)
        self.auto_parse_btn.setFixedHeight(32)
        self.auto_parse_btn.setMinimumWidth(120)
        self.auto_parse_btn.setToolTip(
            "Auto-Parse ON: JSON pasted into the input box will be submitted automatically.\n"
            "Auto-Parse OFF: You must click 'Submit JSON' manually."
        )
        self._update_auto_parse_btn_style(True)
        self.auto_parse_btn.clicked.connect(self._toggle_auto_parse)
        nav_layout.addWidget(self.auto_parse_btn)
        nav_layout.addSpacing(12)

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
        self.reviews_tab = ReviewsTab()
        self.edit_pdf_tab = EditPDFTab()

        self.stack_layout.addWidget(self.processing_tab)
        self.stack_layout.addWidget(self.pdf_gen_tab)
        self.stack_layout.addWidget(self.reviews_tab)
        self.stack_layout.addWidget(self.edit_pdf_tab)

        self.scroll_area.setWidget(self.content_stack)
        main_vbox.addWidget(self.scroll_area)

        # Switch to first tab
        self._switch_tab(0)

    def _switch_tab(self, idx):
        self.processing_tab.setVisible(idx == 0)
        self.pdf_gen_tab.setVisible(idx == 1)
        self.reviews_tab.setVisible(idx == 2)
        self.edit_pdf_tab.setVisible(idx == 3)

        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == idx)

    def _update_auto_parse_btn_style(self, enabled: bool):
        """Update the Auto-Parse toggle button appearance based on state."""
        self.auto_parse_btn.setChecked(enabled)
        if enabled:
            self.auto_parse_btn.setText("⚡ Auto-Parse: ON")
            self.auto_parse_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['success']};
                    color: white;
                    border: none;
                    border-radius: 7px;
                    font-size: 9pt;
                    font-weight: 600;
                    padding: 4px 14px;
                }}
                QPushButton:hover {{
                    background: #16a34a;
                }}
            """)
        else:
            self.auto_parse_btn.setText("⚡ Auto-Parse: OFF")
            self.auto_parse_btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255,255,255,0.12);
                    color: {PALETTE['text_muted']};
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 7px;
                    font-size: 9pt;
                    font-weight: 500;
                    padding: 4px 14px;
                }}
                QPushButton:hover {{
                    background: rgba(255,255,255,0.2);
                    color: white;
                }}
            """)

    def _toggle_auto_parse(self):
        """Toggle the auto-parse feature and sync with ProcessingTab."""
        # Get current state from ProcessingTab
        current = self.processing_tab._auto_parse_enabled
        new_state = not current
        # Update ProcessingTab
        self.processing_tab.set_auto_parse(new_state)
        # Update navbar button appearance
        self._update_auto_parse_btn_style(new_state)
        # Log the change
        state_text = "ON" if new_state else "OFF"
        self.processing_tab.add_log(f"⚡ Auto-Parse toggled {state_text}", "info")

    def showEvent(self, event):
        """Sync the navbar Auto-Parse button state on window show."""
        super().showEvent(event)
        # Sync button with loaded config state
        enabled = self.processing_tab._auto_parse_enabled
        self._update_auto_parse_btn_style(enabled)


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
