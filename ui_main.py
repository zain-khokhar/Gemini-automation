"""
PDF MCQ Extraction Tool - Main UI
Professional PyQt5 interface for automated MCQ generation from PDFs
"""

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
    QProgressBar, QGroupBox, QMessageBox, QFrame, QRadioButton, QButtonGroup,
    QSpinBox, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor
from processing_thread import ProcessingThread, BatchProcessingThread
from state_manager import StateManager


class MCQExtractorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processing_thread = None
        self.state_manager = StateManager()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("PDF MCQ Extraction Tool")
        self.setGeometry(100, 100, 900, 600)
        self.setMinimumSize(900, 600)  # Reduced minimum size for better compatibility
        
        # Create scroll area for main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setCentralWidget(scroll_area)
        
        # Central widget inside scroll area
        central_widget = QWidget()
        scroll_area.setWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)  # Reduced spacing
        main_layout.setContentsMargins(15, 15, 15, 15)  # Reduced margins
        
        # Title
        title = QLabel("📚 PDF MCQ Extraction Tool")
        title_font = QFont()
        title_font.setPointSize(16)  # Reduced from 18
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Automatically generate MCQs from PDF textbooks using Gemini AI")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #666; font-size: 10pt;")  # Reduced from 11pt
        main_layout.addWidget(subtitle)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)
        
        # PDF Selection Group
        pdf_group = QGroupBox("📄 PDF Selection")
        pdf_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10pt; }")
        pdf_layout = QHBoxLayout()
        
        self.pdf_path_input = QLineEdit()
        self.pdf_path_input.setPlaceholderText("Select a folder containing PDF files...")
        self.pdf_path_input.setReadOnly(True)
        self.pdf_path_input.setMinimumHeight(30)  # Reduced from 35
        self.pdf_path_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.browse_btn = QPushButton("📁 Browse")
        self.browse_btn.setMinimumHeight(30)  # Reduced from 35
        self.browse_btn.setMinimumWidth(90)  # Reduced from 100
        self.browse_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.browse_btn.clicked.connect(self.browse_pdf)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        pdf_layout.addWidget(self.pdf_path_input, 4)
        pdf_layout.addWidget(self.browse_btn, 1)
        pdf_group.setLayout(pdf_layout)
        main_layout.addWidget(pdf_group)
        
        # PDF Range Selection Group
        pdf_range_group = QGroupBox("🎯 PDF Selection (Optional)")
        pdf_range_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10pt; }")
        pdf_range_layout = QVBoxLayout()
        pdf_range_layout.setSpacing(5)
        
        # Input field for PDF range
        range_input_layout = QHBoxLayout()
        range_label = QLabel("Process specific PDFs:")
        range_label.setStyleSheet("font-size: 10pt;")
        range_input_layout.addWidget(range_label)
        
        self.pdf_range_input = QLineEdit()
        self.pdf_range_input.setPlaceholderText("e.g., 1,3,5 or 1-5,8-10 (leave empty for all)")
        self.pdf_range_input.setMinimumHeight(30)
        range_input_layout.addWidget(self.pdf_range_input)
        pdf_range_layout.addLayout(range_input_layout)
        
        # Helper text
        helper_label = QLabel("💡 Examples: '2' (only PDF 2), '1,3,5' (PDFs 1,3,5), '1-5' (PDFs 1 to 5), '1-3,7,9-12' (mixed)")
        helper_label.setStyleSheet("font-size: 9pt; color: #666; font-style: italic;")
        helper_label.setWordWrap(True)
        pdf_range_layout.addWidget(helper_label)
        
        pdf_range_group.setLayout(pdf_range_layout)
        main_layout.addWidget(pdf_range_group)
        
        # Section Selection Group
        section_group = QGroupBox("📑 Select Sections to Process")
        section_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10pt; }")
        section_layout = QHBoxLayout()
        section_layout.setSpacing(15)  # Add spacing between radio buttons
        
        self.section_button_group = QButtonGroup()
        
        self.mids_radio = QRadioButton("Mids Only")
        self.mids_radio.setStyleSheet("font-size: 10pt;")
        self.section_button_group.addButton(self.mids_radio, 1)
        
        self.finals_radio = QRadioButton("Finals Only")
        self.finals_radio.setStyleSheet("font-size: 10pt;")
        self.section_button_group.addButton(self.finals_radio, 2)
        
        self.both_radio = QRadioButton("Both (Mids + Finals)")
        self.both_radio.setStyleSheet("font-size: 10pt;")
        self.both_radio.setChecked(True)  # Default selection
        self.section_button_group.addButton(self.both_radio, 3)
        
        section_layout.addWidget(self.mids_radio)
        section_layout.addWidget(self.finals_radio)
        section_layout.addWidget(self.both_radio)
        section_layout.addStretch()
        section_group.setLayout(section_layout)
        main_layout.addWidget(section_group)
        
        # Resume Options Group
        resume_group = QGroupBox("📍 Resume Options")
        resume_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10pt; }")
        resume_layout = QVBoxLayout()
        resume_layout.setSpacing(8)  # Reduced spacing
        
        # Start mode selection
        mode_layout = QHBoxLayout()
        self.start_from_beginning = QRadioButton("Start from beginning")
        self.start_from_beginning.setChecked(True)
        self.start_from_beginning.setStyleSheet("font-size: 10pt;")
        
        self.resume_from_position = QRadioButton("Resume from position")
        self.resume_from_position.setStyleSheet("font-size: 10pt;")
        
        mode_layout.addWidget(self.start_from_beginning)
        mode_layout.addWidget(self.resume_from_position)
        mode_layout.addStretch()
        resume_layout.addLayout(mode_layout)
        
        # PDF index selection
        pdf_index_layout = QHBoxLayout()
        pdf_index_layout.addWidget(QLabel("Start from PDF:"))
        
        self.pdf_start_index = QSpinBox()
        self.pdf_start_index.setMinimum(1)
        self.pdf_start_index.setValue(1)
        self.pdf_start_index.setMinimumWidth(80)
        self.pdf_start_index.setEnabled(False)
        pdf_index_layout.addWidget(self.pdf_start_index)
        
        self.pdf_total_label = QLabel("/ 0")
        self.pdf_total_label.setStyleSheet("color: #666;")
        pdf_index_layout.addWidget(self.pdf_total_label)
        pdf_index_layout.addStretch()
        resume_layout.addLayout(pdf_index_layout)
        
        # Batch index inputs (dynamically shown/hidden)
        # Mids batch
        mids_batch_layout = QHBoxLayout()
        mids_batch_layout.addWidget(QLabel("Start from Mids batch:"))
        self.mids_start_batch = QSpinBox()
        self.mids_start_batch.setMinimum(1)
        self.mids_start_batch.setValue(1)
        self.mids_start_batch.setMinimumWidth(80)
        self.mids_start_batch.setEnabled(False)
        mids_batch_layout.addWidget(self.mids_start_batch)
        mids_batch_layout.addStretch()
        self.mids_batch_widget = QWidget()
        self.mids_batch_widget.setLayout(mids_batch_layout)
        resume_layout.addWidget(self.mids_batch_widget)
        
        # Finals batch
        finals_batch_layout = QHBoxLayout()
        finals_batch_layout.addWidget(QLabel("Start from Finals batch:"))
        self.finals_start_batch = QSpinBox()
        self.finals_start_batch.setMinimum(1)
        self.finals_start_batch.setValue(1)
        self.finals_start_batch.setMinimumWidth(80)
        self.finals_start_batch.setEnabled(False)
        finals_batch_layout.addWidget(self.finals_start_batch)
        finals_batch_layout.addStretch()
        self.finals_batch_widget = QWidget()
        self.finals_batch_widget.setLayout(finals_batch_layout)
        resume_layout.addWidget(self.finals_batch_widget)
        
        resume_group.setLayout(resume_layout)
        main_layout.addWidget(resume_group)
        
        # Connect signals for resume controls
        self.resume_from_position.toggled.connect(self.toggle_resume_controls)
        self.section_button_group.buttonClicked.connect(self.update_batch_inputs)
        
        # Initialize batch input visibility
        self.update_batch_inputs()
        
        # Processing Settings Group
        settings_group = QGroupBox("⚙️ Processing Settings")
        settings_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10pt; }")
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(15)  # Add spacing between controls
        
        # Delay Control (in seconds)
        delay_layout = QVBoxLayout()
        delay_label = QLabel("Delay Between Requests (seconds):")
        delay_label.setStyleSheet("font-size: 10pt;")
        self.delay_seconds_spinbox = QSpinBox()
        self.delay_seconds_spinbox.setMinimum(1)
        self.delay_seconds_spinbox.setMaximum(15)
        self.delay_seconds_spinbox.setValue(1)
        self.delay_seconds_spinbox.setMinimumWidth(80)
        self.delay_seconds_spinbox.setMaximumWidth(120)
        self.delay_seconds_spinbox.setStyleSheet("font-size: 10pt;")
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(self.delay_seconds_spinbox)
        
        settings_layout.addLayout(delay_layout)
        
        # DOM Stabilization Delay Control
        dom_delay_layout = QVBoxLayout()
        dom_delay_label = QLabel("DOM Stabilization Delay (seconds):")
        dom_delay_label.setStyleSheet("font-size: 10pt;")
        self.dom_delay_spinbox = QSpinBox()
        self.dom_delay_spinbox.setMinimum(1)
        self.dom_delay_spinbox.setMaximum(15)
        self.dom_delay_spinbox.setValue(1)
        self.dom_delay_spinbox.setMinimumWidth(80)
        self.dom_delay_spinbox.setMaximumWidth(120)
        self.dom_delay_spinbox.setStyleSheet("font-size: 10pt;")
        dom_delay_layout.addWidget(dom_delay_label)
        dom_delay_layout.addWidget(self.dom_delay_spinbox)
        settings_layout.addLayout(dom_delay_layout)
        
        # Pages per Request Control
        pages_layout = QVBoxLayout()
        pages_label = QLabel("Pages per Request:")
        pages_label.setStyleSheet("font-size: 10pt;")
        self.pages_per_request_spinbox = QSpinBox()
        self.pages_per_request_spinbox.setMinimum(1)
        self.pages_per_request_spinbox.setMaximum(20)
        self.pages_per_request_spinbox.setValue(10)
        self.pages_per_request_spinbox.setMinimumWidth(80)
        self.pages_per_request_spinbox.setMaximumWidth(120)
        self.pages_per_request_spinbox.setStyleSheet("font-size: 10pt;")
        pages_layout.addWidget(pages_label)
        pages_layout.addWidget(self.pages_per_request_spinbox)
        settings_layout.addLayout(pages_layout)
        
        # Content Type Selection (MCQs/Short Notes) - Checkboxes for multiple selection
        content_type_layout = QVBoxLayout()
        content_type_label = QLabel("Content Type:")
        content_type_label.setStyleSheet("font-size: 10pt;")
        content_type_layout.addWidget(content_type_label)
        
        # Use QCheckBox instead of QRadioButton for multiple selection
        from PyQt5.QtWidgets import QCheckBox
        
        self.mcq_checkbox = QCheckBox("MCQs")
        self.mcq_checkbox.setChecked(True)
        self.mcq_checkbox.setStyleSheet("font-size: 10pt;")
        
        self.short_notes_checkbox = QCheckBox("Short Notes")
        self.short_notes_checkbox.setStyleSheet("font-size: 10pt;")
        
        content_type_layout.addWidget(self.mcq_checkbox)
        content_type_layout.addWidget(self.short_notes_checkbox)
        settings_layout.addLayout(content_type_layout)
        
        # Model Selection (Premium/Fast)
        model_layout = QVBoxLayout()
        model_label = QLabel("Model:")
        model_label.setStyleSheet("font-size: 10pt;")
        model_layout.addWidget(model_label)
        
        # Create button group for model selection
        self.model_button_group = QButtonGroup()
        
        self.fast_model_radio = QRadioButton("Fast Model")
        self.fast_model_radio.setChecked(True)
        self.fast_model_radio.setStyleSheet("font-size: 10pt;")
        self.fast_model_radio.toggled.connect(self.on_model_changed)
        self.model_button_group.addButton(self.fast_model_radio, 1)
        
        self.premium_model_radio = QRadioButton("Premium Model")
        self.premium_model_radio.setStyleSheet("font-size: 10pt;")
        self.model_button_group.addButton(self.premium_model_radio, 2)
        
        model_layout.addWidget(self.fast_model_radio)
        model_layout.addWidget(self.premium_model_radio)
        settings_layout.addLayout(model_layout)
        
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)
        
        # Last Position Display Group
        position_group = QGroupBox("📍 Last Processed Position")
        position_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10pt; }")
        position_layout = QVBoxLayout()
        position_layout.setSpacing(5)  # Reduced spacing
        
        # PDF Path (full path)
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("PDF Path:"))
        self.last_pdf_path_label = QLabel("N/A")
        self.last_pdf_path_label.setStyleSheet("font-weight: bold; color: #2196F3; font-size: 10pt;")
        self.last_pdf_path_label.setWordWrap(True)
        path_layout.addWidget(self.last_pdf_path_label, 1)
        position_layout.addLayout(path_layout)
        
        # PDF Index and Name, Section, Batch in one row
        details_layout = QHBoxLayout()
        details_layout.addWidget(QLabel("PDF:"))
        self.last_pdf_index_label = QLabel("N/A")
        self.last_pdf_index_label.setStyleSheet("font-weight: bold; color: #FF9800; font-size: 10pt;")
        details_layout.addWidget(self.last_pdf_index_label)
        
        details_layout.addWidget(QLabel("  Section:"))
        self.last_section_label = QLabel("N/A")
        self.last_section_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 10pt;")
        details_layout.addWidget(self.last_section_label)
        
        details_layout.addWidget(QLabel("  Batch:"))
        self.last_batch_label = QLabel("N/A")
        self.last_batch_label.setStyleSheet("font-weight: bold; color: #9C27B0; font-size: 10pt;")
        details_layout.addWidget(self.last_batch_label)
        details_layout.addStretch()
        position_layout.addLayout(details_layout)
        
        position_group.setLayout(position_layout)
        main_layout.addWidget(position_group)

        
        
        # Status Group
        status_group = QGroupBox("📊 Processing Status")
        status_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10pt; }")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(5)  # Reduced spacing
        
        # Current section
        section_layout = QHBoxLayout()
        section_layout.addWidget(QLabel("Current Section:"))
        self.section_label = QLabel("N/A")
        self.section_label.setStyleSheet("font-weight: bold; color: #2196F3; font-size: 11pt;")
        section_layout.addWidget(self.section_label)
        section_layout.addStretch()
        status_layout.addLayout(section_layout)
        
        # Current batch
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Current Batch:"))
        self.batch_label = QLabel("N/A")
        self.batch_label.setStyleSheet("font-weight: bold; color: #FF9800; font-size: 11pt;")
        batch_layout.addWidget(self.batch_label)
        batch_layout.addStretch()
        status_layout.addLayout(batch_layout)
        
        # Current operation
        operation_layout = QHBoxLayout()
        operation_layout.addWidget(QLabel("Status:"))
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 11pt;")
        operation_layout.addWidget(self.status_label)
        operation_layout.addStretch()
        status_layout.addLayout(operation_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(20)  # Reduced from 25
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)
        
        # Control Buttons
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)  # Add spacing between buttons
        
        self.start_btn = QPushButton("▶️ Start Processing")
        self.start_btn.setMinimumHeight(35)  # Reduced from 40
        self.start_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        
        self.stop_btn = QPushButton("⏸️ Stop")
        self.stop_btn.setMinimumHeight(35)  # Reduced from 40
        self.stop_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        
        self.pause_btn = QPushButton("⏸️ Pause")
        self.pause_btn.setMinimumHeight(35)  # Reduced from 40
        self.pause_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #ccc;
            }
        """)
        self.is_paused = False
        
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.setMinimumHeight(35)  # Reduced from 40
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.setMinimumHeight(35)  # Reduced from 40
        self.reset_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.reset_btn.clicked.connect(self.reset_ui)
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        
        control_layout.addWidget(self.start_btn, 2)
        control_layout.addWidget(self.pause_btn, 1)
        control_layout.addWidget(self.stop_btn, 1)
        control_layout.addWidget(self.reset_btn, 1)
        main_layout.addLayout(control_layout)
        
        # Logs Group
        logs_group = QGroupBox("📝 Process Logs")
        logs_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10pt; }")
        logs_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(150)
        self.log_text.setMaximumHeight(300)
        self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: 2px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        logs_layout.addWidget(self.log_text)
        logs_group.setLayout(logs_layout)
        main_layout.addWidget(logs_group)
        
        # Set main layout
        central_widget.setLayout(main_layout)
        
        # Load last processed state
        self.load_last_state()
        
        # Initial log message
        self.add_log("✓ Application started successfully", "success")
        self.add_log("ℹ️  Please select a PDF file to begin", "info")
        self.add_log("⚠️  Make sure the Gemini server is running (npm start)", "warning")
    
    def browse_pdf(self):
        """Open dialog to select folder containing PDFs"""
        # Use preferred folder if it exists, else use user's Documents
        preferred_folder = r"C:\Users\KLH\Documents\vu-plan-handouts"
        if os.path.exists(preferred_folder):
            start_folder = preferred_folder
        else:
            start_folder = os.path.join(os.path.expanduser("~"), "Documents")
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder Containing PDFs",
            start_folder,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            # Find all PDF files in the folder
            pdf_files = []
            for file in os.listdir(folder_path):
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(folder_path, file))
            
            if not pdf_files:
                QMessageBox.warning(self, "No PDFs Found", 
                                  "No PDF files found in the selected folder.")
                return
            
            # Store the list of PDFs
            self.pdf_files = pdf_files
            self.pdf_path_input.setText(f"{len(pdf_files)} PDF(s) selected from: {folder_path}")
            
            # Update PDF total label for resume controls
            self.pdf_total_label.setText(f"/ {len(pdf_files)}")
            self.pdf_start_index.setMaximum(len(pdf_files))
            
            # Show list of PDFs in log with index and name
            self.add_log(f"📁 Found {len(pdf_files)} PDF file(s):", "info")
            for idx, pdf in enumerate(pdf_files, 1):
                self.add_log(f"  {idx}. {os.path.basename(pdf)}", "info")
    
    def parse_pdf_selection(self, selection_str, total_pdfs):
        """Parse PDF selection string and return list of indexes to process
        
        Args:
            selection_str: String like '1,3,5' or '1-5,8-10' or empty
            total_pdfs: Total number of PDFs available
            
        Returns:
            List of PDF indexes (1-based) to process, or None if invalid
        """
        # If empty, return all indexes
        if not selection_str or selection_str.strip() == '':
            return list(range(1, total_pdfs + 1))
        
        try:
            indexes = set()
            parts = selection_str.split(',')
            
            for part in parts:
                part = part.strip()
                
                if '-' in part:
                    # Range like '1-5'
                    start, end = part.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    
                    if start < 1 or end > total_pdfs or start > end:
                        raise ValueError(f"Invalid range: {part}")
                    
                    indexes.update(range(start, end + 1))
                else:
                    # Single number like '3'
                    num = int(part)
                    
                    if num < 1 or num > total_pdfs:
                        raise ValueError(f"Invalid PDF index: {num}")
                    
                    indexes.add(num)
            
            # Return sorted list
            return sorted(list(indexes))
            
        except Exception as e:
            return None
    

    
    def on_model_changed(self):
        """Handle model selection change"""
        if self.premium_model_radio.isChecked():
            self.add_log("🔒 Premium Model selected - Delay range: 1-15 seconds", "info")
        else:
            self.add_log("⚡ Fast Model selected - Delay range: 1-15 seconds", "info")
    
    def load_last_state(self):
        """Load last processed state from file and update UI"""
        state = self.state_manager.load_state()
        if state:
            self.last_pdf_path_label.setText(state['pdf_path'])
            self.last_pdf_index_label.setText(f"{state['pdf_index']}: {state['pdf_name']}")
            self.last_section_label.setText(state['section'].upper())
            self.last_batch_label.setText(str(state['batch']))
            
            summary = self.state_manager.get_state_summary()
            self.add_log(f"📂 Loaded last processed state: {summary}", "success")
        else:
            self.add_log("ℹ️  No previous state found", "info")
    
    def toggle_resume_controls(self, enabled):
        """Enable/disable resume controls based on radio button"""
        self.pdf_start_index.setEnabled(enabled)
        self.mids_start_batch.setEnabled(enabled)
        self.finals_start_batch.setEnabled(enabled)
    
    def update_batch_inputs(self):
        """Show/hide batch inputs based on section selection"""
        if self.mids_radio.isChecked():
            # Show only mids batch input
            self.mids_batch_widget.setVisible(True)
            self.finals_batch_widget.setVisible(False)
        elif self.finals_radio.isChecked():
            # Show only finals batch input
            self.mids_batch_widget.setVisible(False)
            self.finals_batch_widget.setVisible(True)
        else:  # both_radio is checked
            # Show both batch inputs
            self.mids_batch_widget.setVisible(True)
            self.finals_batch_widget.setVisible(True)
    
    def start_processing(self):
        """Start the processing thread"""
        if not hasattr(self, 'pdf_files') or not self.pdf_files:
            QMessageBox.warning(self, "No PDFs Selected", "Please select a folder first.")
            return
        
        # Parse PDF selection
        selection_str = self.pdf_range_input.text().strip()
        selected_indexes = self.parse_pdf_selection(selection_str, len(self.pdf_files))
        
        if selected_indexes is None:
            QMessageBox.warning(self, "Invalid Selection", 
                              f"Invalid PDF selection format: '{selection_str}'\n\n"
                              "Valid formats:\n"
                              "  - Single: '3'\n"
                              "  - Multiple: '1,3,5'\n"
                              "  - Range: '1-5'\n"
                              "  - Mixed: '1-3,7,9-12'\n\n"
                              f"Valid indexes: 1 to {len(self.pdf_files)}")
            return
        
        # Filter PDFs based on selection
        selected_pdfs = [self.pdf_files[i-1] for i in selected_indexes]
        
        # Log selection
        if len(selected_pdfs) == len(self.pdf_files):
            self.add_log(f"📋 Processing all {len(self.pdf_files)} PDFs", "info")
        else:
            self.add_log(f"📋 Processing {len(selected_pdfs)} of {len(self.pdf_files)} PDFs: {selection_str}", "info")
            for idx in selected_indexes:
                self.add_log(f"  {idx}. {os.path.basename(self.pdf_files[idx-1])}", "info")
        
        # Disable controls
        self.start_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        
        # Reset progress
        self.progress_bar.setValue(0)
        
        # Get selected sections
        selected_sections = []
        if self.mids_radio.isChecked():
            selected_sections = ['mids']
        elif self.finals_radio.isChecked():
            selected_sections = ['finals']
        else:  # both_radio is checked
            selected_sections = ['mids', 'finals']
        
        # Get resume parameters
        start_pdf_index = 1
        start_mids_batch = 1
        start_finals_batch = 1
        
        if self.resume_from_position.isChecked():
            start_pdf_index = self.pdf_start_index.value()
            start_mids_batch = self.mids_start_batch.value()
            start_finals_batch = self.finals_start_batch.value()
            
            self.add_log(f"📍 Resuming from PDF {start_pdf_index}/{len(self.pdf_files)}", "info")
            if 'mids' in selected_sections:
                self.add_log(f"   Mids: Starting from batch {start_mids_batch}", "info")
            if 'finals' in selected_sections:
                self.add_log(f"   Finals: Starting from batch {start_finals_batch}", "info")
        
        # Get content type selection - now supports multiple types
        content_types = []
        if self.mcq_checkbox.isChecked():
            content_types.append('mcq')
        if self.short_notes_checkbox.isChecked():
            content_types.append('short_notes')
        
        if not content_types:
            QMessageBox.warning(self, "No Content Type Selected", 
                              "Please select at least one content type (MCQs or Short Notes).")
            self.start_btn.setEnabled(True)
            self.browse_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            return
        
        # Log selected content types
        content_type_str = " + ".join(["MCQs" if ct == 'mcq' else "Short Notes" for ct in content_types])
        self.add_log(f"📝 Content types: {content_type_str}", "info")
        if len(content_types) > 1:
            self.add_log("   (For each PDF: MCQs first, then Short Notes)", "info")
        
        # Create and start batch processing thread with resume parameters and new settings
        self.processing_thread = BatchProcessingThread(
            selected_pdfs,  # Use filtered PDF list
            selected_sections,
            start_pdf_index,
            start_mids_batch,
            start_finals_batch,
            delay_seconds=self.delay_seconds_spinbox.value(),
            dom_delay_seconds=self.dom_delay_spinbox.value(),
            pages_per_request=self.pages_per_request_spinbox.value(),
            is_premium_model=self.premium_model_radio.isChecked(),
            content_types=content_types  # Pass list of content types
        )
        
        # Connect signals
        self.processing_thread.log_signal.connect(self.add_log)
        self.processing_thread.status_signal.connect(self.update_status)
        self.processing_thread.current_pdf_signal.connect(self.update_current_pdf)
        self.processing_thread.position_signal.connect(self.update_position)
        self.processing_thread.finished_signal.connect(self.processing_finished)
        
        # Start thread
        self.processing_thread.start()
        self.add_log("🚀 Batch processing started...", "info")
    
    def stop_processing(self):
        """Stop the processing thread"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.stop_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
    
    def toggle_pause(self):
        """Toggle pause/resume state"""
        if not self.processing_thread or not self.processing_thread.isRunning():
            return
        
        if self.is_paused:
            # Resume - disable settings during active processing
            self.processing_thread.resume()
            self.is_paused = False
            self.pause_btn.setText("⏸️ Pause")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 12pt;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                }
            """)
            
            # Disable settings during active processing
            self.dom_delay_spinbox.setEnabled(False)
            self.pages_per_request_spinbox.setEnabled(False)
            self.delay_seconds_spinbox.setEnabled(False)
            
            self.add_log("▶️ Processing resumed", "info")
            self.add_log("⚙️ Settings locked during processing", "info")
        else:
            # Pause - enable settings for modification
            self.processing_thread.pause()
            self.is_paused = True
            self.pause_btn.setText("▶️ Resume")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 12pt;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                }
            """)
            
            # Enable settings for modification while paused
            self.delay_seconds_spinbox.setEnabled(True)
            self.dom_delay_spinbox.setEnabled(True)
            self.pages_per_request_spinbox.setEnabled(True)
            
            self.add_log("⏸️ Processing paused", "warning")
            self.add_log("⚙️ Settings unlocked - you can modify delay, DOM time, and pages per request", "info")
    
    def reset_ui(self):
        """Reset the UI to initial state"""
        self.pdf_path_input.clear()
        self.log_text.clear()
        self.section_label.setText("N/A")
        self.batch_label.setText("N/A")
        self.status_label.setText("Ready")
        self.progress_bar.setValue(0)
        
        self.start_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Pause")
        self.is_paused = False
        
        self.add_log("✓ UI reset", "success")
        self.add_log("ℹ️  Please select a PDF file to begin", "info")
    
    def add_log(self, message, level="info"):
        """Add a log message with color coding"""
        colors = {
            "info": "#2196F3",      # Blue
            "success": "#4CAF50",   # Green
            "warning": "#FF9800",   # Orange
            "error": "#f44336"      # Red
        }
        
        color = colors.get(level, "#d4d4d4")
        
        # Format message with HTML
        html_message = f'<span style="color: {color};">{message}</span>'
        
        # Append to log
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertHtml(html_message + "<br>")
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_status(self, status):
        """Update status label"""
        self.status_label.setText(status)
    
    def update_section(self, section):
        """Update current section label"""
        self.section_label.setText(section)
    
    def update_batch(self, current, total):
        """Update batch progress"""
        self.batch_label.setText(f"{current}/{total}")
        
        # Update progress bar
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
    
    def update_current_pdf(self, pdf_name, current, total):
        """Update current PDF being processed"""
        self.section_label.setText(f"PDF {current}/{total}")
        self.batch_label.setText(pdf_name)
        
        # Update progress bar for overall batch
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
    
    def update_position(self, pdf_path, pdf_index, pdf_name, section, batch):
        """Update last processed position display and save to state"""
        self.last_pdf_path_label.setText(pdf_path)
        self.last_pdf_index_label.setText(f"{pdf_index}: {pdf_name}")
        self.last_section_label.setText(section.upper())
        self.last_batch_label.setText(str(batch))
        
        # Save state to file for persistence
        self.state_manager.save_state(pdf_path, pdf_index, pdf_name, section, batch)
    
    def processing_finished(self, success, message):
        """Handle processing completion"""
        # Re-enable controls
        self.start_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Pause")
        self.is_paused = False
        
        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", f"Processing failed:\n{message}")


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MCQExtractorUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
    def stop_processing(self):
        """Stop the processing thread"""
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.stop()
            self.stop_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
    
    def toggle_pause(self):
        """Toggle pause/resume state"""
        if not self.processing_thread or not self.processing_thread.isRunning():
            return
        
        if self.is_paused:
            # Resume
            self.processing_thread.resume()
            self.is_paused = False
            self.pause_btn.setText("⏸️ Pause")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 12pt;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                }
            """)
            self.add_log("▶️ Processing resumed", "info")
        else:
            # Pause
            self.processing_thread.pause()
            self.is_paused = True
            self.pause_btn.setText("▶️ Resume")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    font-size: 12pt;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                }
            """)
            self.add_log("⏸️ Processing paused", "warning")
    
    def reset_ui(self):
        """Reset the UI to initial state"""
        self.pdf_path_input.clear()
        self.log_text.clear()
        self.section_label.setText("N/A")
        self.batch_label.setText("N/A")
        self.status_label.setText("Ready")
        self.progress_bar.setValue(0)
        
        self.start_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Pause")
        self.is_paused = False
        
        self.add_log("✓ UI reset", "success")
        self.add_log("ℹ️  Please select a PDF file to begin", "info")
    
    def add_log(self, message, level="info"):
        """Add a log message with color coding"""
        colors = {
            "info": "#2196F3",      # Blue
            "success": "#4CAF50",   # Green
            "warning": "#FF9800",   # Orange
            "error": "#f44336"      # Red
        }
        
        color = colors.get(level, "#d4d4d4")
        
        # Format message with HTML
        html_message = f'<span style="color: {color};">{message}</span>'
        
        # Append to log
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertHtml(html_message + "<br>")
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_status(self, status):
        """Update status label"""
        self.status_label.setText(status)
    
    def update_section(self, section):
        """Update current section label"""
        self.section_label.setText(section)
    
    def update_batch(self, current, total):
        """Update batch progress"""
        self.batch_label.setText(f"{current}/{total}")
        
        # Update progress bar
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
    
    def update_current_pdf(self, pdf_name, current, total):
        """Update current PDF being processed"""
        self.section_label.setText(f"PDF {current}/{total}")
        self.batch_label.setText(pdf_name)
        
        # Update progress bar for overall batch
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
    
    def update_position(self, pdf_path, pdf_index, pdf_name, section, batch):
        """Update last processed position display and save to state"""
        self.last_pdf_path_label.setText(pdf_path)
        self.last_pdf_index_label.setText(f"{pdf_index}: {pdf_name}")
        self.last_section_label.setText(section.upper())
        self.last_batch_label.setText(str(batch))
        
        # Save state to file for persistence
        self.state_manager.save_state(pdf_path, pdf_index, pdf_name, section, batch)
    
    def processing_finished(self, success, message):
        """Handle processing completion"""
        # Re-enable controls
        self.start_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ Pause")
        self.is_paused = False
        
        if success:
            self.progress_bar.setValue(100)
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", f"Processing failed:\n{message}")


def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MCQExtractorUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
