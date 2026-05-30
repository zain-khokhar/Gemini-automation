"""
Transcripts Tab — YouTube Lecture Transcript System
Full UI for: URL input → Playlist detection → Whisper transcription → Gemini processing → PDF handout generation.
"""

import os
import json
import time
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTextEdit, QProgressBar, QFrame, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QAbstractItemView, QFileDialog, QPlainTextEdit, QMessageBox,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QTextCursor


# ── Colour palette (matches ui_main.py) ──
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
    "row_hover":   "#f0f4ff",
    "row_alt":     "#f9fafc",
}


def _make_card(layout_type='v', margins=(16, 14, 16, 14), spacing=10):
    frame = QFrame()
    frame.setObjectName("card")
    if layout_type == 'v':
        layout = QVBoxLayout(frame)
    else:
        layout = QHBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


def _label_secondary(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {PALETTE['text_secondary']}; font-size: 9pt; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase;")
    return lbl


def _label_muted(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 9pt;")
    return lbl


def _divider():
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet(f"color: {PALETTE['border']}; background: {PALETTE['border']}; border: none; max-height: 1px;")
    return line


class TranscriptsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.videos = []
        self.transcript_thread = None
        self.resolve_thread = None
        self.handout_thread = None
        self._transcript_json_path = None
        self._start_time = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── Header ────────────────────────────────────
        header_row = QHBoxLayout()
        title = QLabel("🎙️ YouTube Lecture Transcripts")
        title.setStyleSheet(f"color: {PALETTE['navy']}; font-size: 14pt; font-weight: 700;")
        desc = _label_muted("Extract transcripts from YouTube lectures → Generate handout PDFs")
        header_row.addWidget(title)
        header_row.addWidget(desc)
        header_row.addStretch()
        root.addLayout(header_row)
        root.addWidget(_divider())

        # ── Course Info Card ──────────────────────────
        info_card, info_layout = _make_card('h', (14, 12, 14, 12), 16)

        col1 = QVBoxLayout()
        col1.addWidget(_label_secondary("Subject Name"))
        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("e.g. Microbiology")
        self.subject_input.setMinimumHeight(34)
        col1.addWidget(self.subject_input)
        info_layout.addLayout(col1, 2)

        col2 = QVBoxLayout()
        col2.addWidget(_label_secondary("Course Code"))
        self.course_code_input = QLineEdit()
        self.course_code_input.setPlaceholderText("e.g. MIC501T")
        self.course_code_input.setMinimumHeight(34)
        col2.addWidget(self.course_code_input)
        info_layout.addLayout(col2, 1)

        root.addWidget(info_card)

        # ── YouTube Source Card ───────────────────────
        yt_card, yt_layout = _make_card('v', (14, 12, 14, 12), 8)
        yt_layout.addWidget(_label_secondary("YouTube Source"))

        url_row = QHBoxLayout()
        url_row.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube playlist URL or single video URL...")
        self.url_input.setMinimumHeight(36)
        url_row.addWidget(self.url_input, 5)

        self.detect_btn = QPushButton("🔍 Detect Playlist")
        self.detect_btn.setMinimumHeight(36)
        self.detect_btn.setMinimumWidth(140)
        self.detect_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['accent']};
                color: white;
                border: none;
                border-radius: 7px;
                font-weight: 600;
                padding: 6px 16px;
            }}
            QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}
            QPushButton:disabled {{ background: #a5b4fc; }}
        """)
        self.detect_btn.clicked.connect(self._detect_playlist)
        url_row.addWidget(self.detect_btn)
        yt_layout.addLayout(url_row)

        # Detected info label
        self.detected_label = QLabel("")
        self.detected_label.setStyleSheet(f"color: {PALETTE['success']}; font-weight: 600; font-size: 10pt;")
        self.detected_label.setVisible(False)
        yt_layout.addWidget(self.detected_label)

        # Video list table
        self.video_table = QTableWidget(0, 4)
        self.video_table.setHorizontalHeaderLabels(["#", "TITLE", "DURATION", "STATUS"])
        self.video_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.video_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.video_table.setColumnWidth(0, 50)
        self.video_table.setColumnWidth(2, 80)
        self.video_table.setColumnWidth(3, 100)
        self.video_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.video_table.setAlternatingRowColors(True)
        self.video_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.video_table.verticalHeader().setVisible(False)
        self.video_table.setMinimumHeight(160)
        self.video_table.setMaximumHeight(260)
        self.video_table.setShowGrid(False)
        self.video_table.setStyleSheet(f"""
            QTableWidget {{
                alternate-background-color: {PALETTE['row_alt']};
            }}
        """)
        yt_layout.addWidget(self.video_table)
        root.addWidget(yt_card)

        # ── Whisper Settings Card ─────────────────────
        whisper_card, whisper_layout = _make_card('h', (14, 12, 14, 12), 20)

        model_col = QVBoxLayout()
        model_col.addWidget(_label_secondary("Whisper Model"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(34)
        self.model_combo.addItems(["small — Faster (~1 GB)", "medium — Best accuracy (~1.5 GB)"])
        model_col.addWidget(self.model_combo)
        whisper_layout.addLayout(model_col, 1)

        device_col = QVBoxLayout()
        device_col.addWidget(_label_secondary("Device"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumHeight(34)
        self.device_combo.addItems(["Auto-detect (GPU preferred)", "GPU (CUDA)", "CPU"])
        device_col.addWidget(self.device_combo)
        whisper_layout.addLayout(device_col, 1)

        gpu_col = QVBoxLayout()
        gpu_col.addWidget(_label_secondary("GPU Status"))
        self.gpu_label = QLabel("🔄 Checking...")
        self.gpu_label.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 9pt; padding: 6px;")
        gpu_col.addWidget(self.gpu_label)
        whisper_layout.addLayout(gpu_col, 1)

        root.addWidget(whisper_card)

        # Auto-detect GPU after UI builds
        QTimer.singleShot(500, self._check_gpu)

        # ── Control Buttons ───────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.start_btn = QPushButton("▶  Start Transcription")
        self.start_btn.setObjectName("primary")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setMinimumWidth(180)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['accent']};
                color: white;
                border: none;
                border-radius: 7px;
                font-size: 11pt;
                font-weight: 600;
                padding: 8px 24px;
            }}
            QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}
            QPushButton:disabled {{ background: #a5b4fc; color: #e0e0e0; }}
        """)
        self.start_btn.clicked.connect(self._start_transcription)

        self.pause_btn = QPushButton("⏸  Pause")
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['warning']};
                color: white;
                border: none;
                border-radius: 7px;
                font-weight: 600;
                padding: 8px 18px;
            }}
            QPushButton:hover {{ background: #d97706; }}
            QPushButton:disabled {{ background: {PALETTE['border']}; color: {PALETTE['text_muted']}; }}
        """)
        self.pause_btn.clicked.connect(self._toggle_pause)
        self._is_paused = False

        self.stop_btn = QPushButton("⏹  Stop")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['error']};
                color: white;
                border: none;
                border-radius: 7px;
                font-weight: 600;
                padding: 8px 18px;
            }}
            QPushButton:hover {{ background: #dc2626; }}
            QPushButton:disabled {{ background: {PALETTE['border']}; color: {PALETTE['text_muted']}; }}
        """)
        self.stop_btn.clicked.connect(self._stop_transcription)

        btn_row.addWidget(self.start_btn, 2)
        btn_row.addWidget(self.pause_btn, 1)
        btn_row.addWidget(self.stop_btn, 1)
        btn_row.addStretch(2)
        root.addLayout(btn_row)

        # ── Progress Card ─────────────────────────────
        progress_card, progress_layout = _make_card('v', (14, 10, 14, 10), 6)

        prog_header = QHBoxLayout()
        self.progress_title = QLabel("Ready to start")
        self.progress_title.setStyleSheet(f"color: {PALETTE['text_primary']}; font-size: 10pt; font-weight: 600;")
        prog_header.addWidget(self.progress_title)
        prog_header.addStretch()
        self.eta_label = _label_muted("")
        prog_header.addWidget(self.eta_label)
        progress_layout.addLayout(prog_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {PALETTE['border']};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: {PALETTE['accent']};
                border-radius: 4px;
            }}
        """)
        progress_layout.addWidget(self.progress_bar)

        self.progress_detail = _label_muted("No transcription in progress")
        progress_layout.addWidget(self.progress_detail)

        root.addWidget(progress_card)

        # ── Log Card ──────────────────────────────────
        log_card, log_layout = _make_card('v', (14, 12, 14, 12), 8)

        log_header = QHBoxLayout()
        log_header.addWidget(_label_secondary("Process Log"))
        log_header.addStretch()
        clear_log_btn = QPushButton("Clear")
        clear_log_btn.setFixedWidth(56)
        clear_log_btn.setFixedHeight(24)
        clear_log_btn.setStyleSheet("font-size: 8.5pt; padding: 2px 8px;")
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        log_header.addWidget(clear_log_btn)
        log_layout.addLayout(log_header)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(130)
        self.log_text.setMaximumHeight(220)
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
        root.addWidget(log_card)

        # ── Generated Transcripts Card ────────────────
        gen_card, gen_layout = _make_card('v', (14, 12, 14, 12), 8)
        gen_layout.addWidget(_label_secondary("Generated Transcripts"))

        self.transcript_info = QLabel("No transcripts generated yet")
        self.transcript_info.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 10pt; padding: 4px 0;")
        gen_layout.addWidget(self.transcript_info)

        gen_btn_row = QHBoxLayout()
        gen_btn_row.setSpacing(8)

        self.send_gemini_btn = QPushButton("🚀  Send to Gemini for Handout")
        self.send_gemini_btn.setMinimumHeight(36)
        self.send_gemini_btn.setEnabled(False)
        self.send_gemini_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['success']};
                color: white;
                border: none;
                border-radius: 7px;
                font-weight: 600;
                padding: 6px 20px;
            }}
            QPushButton:hover {{ background: #16a34a; }}
            QPushButton:disabled {{ background: {PALETTE['border']}; color: {PALETTE['text_muted']}; }}
        """)
        self.send_gemini_btn.clicked.connect(self._send_to_gemini)
        gen_btn_row.addWidget(self.send_gemini_btn)

        self.gen_pdf_btn = QPushButton("📄  Generate Handout PDF")
        self.gen_pdf_btn.setMinimumHeight(36)
        self.gen_pdf_btn.setEnabled(False)
        self.gen_pdf_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PALETTE['accent']};
                color: white;
                border: none;
                border-radius: 7px;
                font-weight: 600;
                padding: 6px 20px;
            }}
            QPushButton:hover {{ background: {PALETTE['accent_hover']}; }}
            QPushButton:disabled {{ background: {PALETTE['border']}; color: {PALETTE['text_muted']}; }}
        """)
        self.gen_pdf_btn.clicked.connect(self._generate_pdf)
        gen_btn_row.addWidget(self.gen_pdf_btn)

        self.open_folder_btn = QPushButton("📁  Open Folder")
        self.open_folder_btn.setMinimumHeight(36)
        self.open_folder_btn.setEnabled(False)
        self.open_folder_btn.clicked.connect(self._open_output_folder)
        gen_btn_row.addWidget(self.open_folder_btn)

        gen_btn_row.addStretch()
        gen_layout.addLayout(gen_btn_row)
        root.addWidget(gen_card)

    # ── GPU Check ─────────────────────────────────────

    def _check_gpu(self):
        """Check GPU availability and update label."""
        try:
            from transcript_engine import WhisperTranscriber
            info = WhisperTranscriber.get_gpu_info()
            if info['available']:
                note = info.get('note', '')
                if note:
                    # Low VRAM warning
                    self.gpu_label.setText(f"⚠️ {info['name']} ({info['vram_gb']} GB){note}")
                    self.gpu_label.setStyleSheet(f"color: {PALETTE['warning']}; font-size: 9pt; font-weight: 600; padding: 6px;")
                else:
                    self.gpu_label.setText(f"✅ {info['name']} ({info['vram_gb']} GB)")
                    self.gpu_label.setStyleSheet(f"color: {PALETTE['success']}; font-size: 9pt; font-weight: 600; padding: 6px;")
            else:
                self.gpu_label.setText("⚠️ No GPU — CPU mode (slower)")
                self.gpu_label.setStyleSheet(f"color: {PALETTE['warning']}; font-size: 9pt; font-weight: 600; padding: 6px;")
        except Exception as e:
            self.gpu_label.setText(f"❓ Check failed: {str(e)[:40]}")
            self.gpu_label.setStyleSheet(f"color: {PALETTE['error']}; font-size: 9pt; padding: 6px;")

    # ── Detect Playlist ───────────────────────────────

    def _detect_playlist(self):
        """Resolve YouTube URL to detect playlist videos."""
        url = self.url_input.text().strip()
        if not url:
            self._add_log("⚠️ Please enter a YouTube URL first", "warning")
            return

        self.detect_btn.setEnabled(False)
        self.detect_btn.setText("🔄 Detecting...")

        from transcript_thread import PlaylistResolveThread
        self.resolve_thread = PlaylistResolveThread(url)
        self.resolve_thread.log_signal.connect(self._add_log)
        self.resolve_thread.resolved_signal.connect(self._on_playlist_resolved)
        self.resolve_thread.finished_signal.connect(self._on_playlist_detect_done)
        self.resolve_thread.start()

    def _on_playlist_resolved(self, videos):
        """Called when playlist is resolved."""
        self.videos = videos
        self._populate_video_table(videos)
        
        if videos:
            self.detected_label.setText(f"📋 {len(videos)} video(s) detected")
            self.detected_label.setVisible(True)
        else:
            self.detected_label.setText("❌ No videos found")
            self.detected_label.setStyleSheet(f"color: {PALETTE['error']}; font-weight: 600; font-size: 10pt;")
            self.detected_label.setVisible(True)

    def _on_playlist_detect_done(self, success, msg):
        """Reset detect button after completion."""
        self.detect_btn.setEnabled(True)
        self.detect_btn.setText("🔍 Detect Playlist")
        if success:
            self._add_log(f"✅ {msg}", "success")
        else:
            self._add_log(f"❌ {msg}", "error")

    def _populate_video_table(self, videos):
        """Fill the video table with detected videos."""
        self.video_table.setRowCount(0)
        for v in videos:
            row = self.video_table.rowCount()
            self.video_table.insertRow(row)

            # Index
            idx_item = QTableWidgetItem(str(v['index']))
            idx_item.setTextAlignment(Qt.AlignCenter)
            idx_item.setForeground(QColor(PALETTE['accent']))
            self.video_table.setItem(row, 0, idx_item)

            # Title
            title_item = QTableWidgetItem(v['title'])
            self.video_table.setItem(row, 1, title_item)

            # Duration
            dur = v.get('duration', 0)
            if dur:
                mins, secs = divmod(int(dur), 60)
                hrs, mins = divmod(mins, 60)
                dur_str = f"{hrs}:{mins:02d}:{secs:02d}" if hrs else f"{mins}:{secs:02d}"
            else:
                dur_str = "—"
            dur_item = QTableWidgetItem(dur_str)
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.video_table.setItem(row, 2, dur_item)

            # Status
            status_item = QTableWidgetItem("⏳ Pending")
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(QColor(PALETTE['text_muted']))
            self.video_table.setItem(row, 3, status_item)

    def _update_video_status(self, index: int, status: str, color: str):
        """Update status column for a video in the table."""
        if 0 <= index < self.video_table.rowCount():
            item = QTableWidgetItem(status)
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor(color))
            self.video_table.setItem(index, 3, item)

    # ── Transcription Controls ────────────────────────

    def _start_transcription(self):
        """Start the transcription pipeline."""
        url = self.url_input.text().strip()
        subject = self.subject_input.text().strip()
        course_code = self.course_code_input.text().strip()

        if not url:
            self._add_log("⚠️ Please enter a YouTube URL", "warning")
            return
        if not subject:
            self._add_log("⚠️ Please enter a subject name", "warning")
            return
        if not course_code:
            self._add_log("⚠️ Please enter a course code", "warning")
            return

        # Get model selection
        model_idx = self.model_combo.currentIndex()
        model_name = "small" if model_idx == 0 else "medium"

        # Get device selection
        device_idx = self.device_combo.currentIndex()
        device = ["auto", "cuda", "cpu"][device_idx]

        # Update UI state
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.detect_btn.setEnabled(False)
        self.progress_title.setText("Starting transcription...")
        self._start_time = time.time()

        # Start thread
        from transcript_thread import TranscriptThread
        self.transcript_thread = TranscriptThread(
            url=url,
            subject_name=subject,
            course_code=course_code,
            model_name=model_name,
            device=device,
        )
        self.transcript_thread.log_signal.connect(self._add_log)
        self.transcript_thread.progress_signal.connect(self._on_progress)
        self.transcript_thread.video_progress_signal.connect(self._on_video_progress)
        self.transcript_thread.playlist_resolved_signal.connect(self._on_playlist_resolved)
        self.transcript_thread.finished_signal.connect(self._on_transcription_done)
        self.transcript_thread.start()

    def _toggle_pause(self):
        """Toggle pause/resume."""
        if not self.transcript_thread:
            return
        if self._is_paused:
            self.transcript_thread.resume()
            self.pause_btn.setText("⏸  Pause")
            self._is_paused = False
            self._add_log("▶ Resumed", "info")
        else:
            self.transcript_thread.pause()
            self.pause_btn.setText("▶  Resume")
            self._is_paused = True
            self._add_log("⏸ Paused", "info")

    def _stop_transcription(self):
        """Stop transcription (saves progress)."""
        if self.transcript_thread:
            self._add_log("⏹ Stopping... (saving progress)", "warning")
            self.transcript_thread.stop()

    def _on_progress(self, current, total):
        """Update overall progress bar."""
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)

            # Calculate ETA
            if self._start_time and current > 0:
                elapsed = time.time() - self._start_time
                per_video = elapsed / current
                remaining = (total - current) * per_video
                
                if remaining > 3600:
                    eta_str = f"~{remaining/3600:.1f}h remaining"
                elif remaining > 60:
                    eta_str = f"~{remaining/60:.0f}m remaining"
                else:
                    eta_str = f"~{remaining:.0f}s remaining"
                self.eta_label.setText(eta_str)

    def _on_video_progress(self, title, current, total):
        """Update per-video progress display."""
        self.progress_title.setText(f"Video {current}/{total}: {title}")
        self.progress_detail.setText(f"Processing lecture {current} of {total}")

        # Update video table status
        if current > 0:
            # Mark previous as done
            if current > 1:
                self._update_video_status(current - 2, "✅ Done", PALETTE['success'])
            # Mark current as processing
            self._update_video_status(current - 1, "🔄 Processing", PALETTE['accent'])

    def _on_transcription_done(self, success, result):
        """Handle transcription completion."""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.detect_btn.setEnabled(True)
        self._is_paused = False

        if success:
            self._transcript_json_path = result
            self.progress_title.setText("✅ Transcription Complete!")
            self.progress_bar.setValue(100)
            self.eta_label.setText("")
            
            # Update transcript info
            try:
                with open(result, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                count = len(data) if isinstance(data, list) else 0
                size_kb = os.path.getsize(result) / 1024
                self.transcript_info.setText(
                    f"📄 {Path(result).name}  |  {count} lectures  |  {size_kb:.0f} KB"
                )
                self.transcript_info.setStyleSheet(f"color: {PALETTE['success']}; font-size: 10pt; font-weight: 600; padding: 4px 0;")
            except Exception:
                self.transcript_info.setText(f"📄 {Path(result).name}")

            self.send_gemini_btn.setEnabled(True)
            self.gen_pdf_btn.setEnabled(True)
            self.open_folder_btn.setEnabled(True)

            # Mark all videos as done
            for i in range(self.video_table.rowCount()):
                self._update_video_status(i, "✅ Done", PALETTE['success'])

            self._add_log(f"🎉 All transcripts saved to: {result}", "success")
        else:
            self.progress_title.setText("❌ Transcription Failed")
            self._add_log(f"❌ {result}", "error")

    # ── Gemini Handout Processing ─────────────────────

    def _send_to_gemini(self):
        """Send transcripts to Gemini for handout generation."""
        if not self._transcript_json_path or not os.path.exists(self._transcript_json_path):
            self._add_log("⚠️ No transcript JSON file found", "warning")
            return

        course_code = self.course_code_input.text().strip()
        subject = self.subject_input.text().strip()

        self.send_gemini_btn.setEnabled(False)
        self.send_gemini_btn.setText("🔄 Processing...")

        from handout_processor import HandoutProcessingThread
        self.handout_thread = HandoutProcessingThread(
            transcript_json_path=self._transcript_json_path,
            course_code=course_code,
            subject_name=subject,
        )
        self.handout_thread.log_signal.connect(self._add_log)
        self.handout_thread.progress_signal.connect(self._on_progress)
        self.handout_thread.finished_signal.connect(self._on_handout_done)
        self.handout_thread.start()

    def _on_handout_done(self, success, result):
        """Handle handout processing completion."""
        self.send_gemini_btn.setEnabled(True)
        self.send_gemini_btn.setText("🚀  Send to Gemini for Handout")

        if success:
            self._add_log(f"✅ Handout data saved: {result}", "success")
            self.gen_pdf_btn.setEnabled(True)
        else:
            self._add_log(f"❌ Handout processing failed: {result}", "error")

    # ── PDF Generation ────────────────────────────────

    def _generate_pdf(self):
        """Generate handout PDF from processed data."""
        course_code = self.course_code_input.text().strip()
        subject = self.subject_input.text().strip()

        if not course_code:
            self._add_log("⚠️ Course code is required for PDF generation", "warning")
            return

        # Determine handout JSON path
        import re
        prefix_match = re.match(r'^([A-Z]+)', course_code.upper())
        prefix = prefix_match.group(1) if prefix_match else course_code.upper()
        base_dir = r"E:\documents\vu-plan-handouts"
        folder = os.path.join(base_dir, f"vu-projects-{prefix}-pdfs")
        
        # Try handout data first, then raw transcripts
        handout_json = os.path.join(folder, f"{course_code}_handout_data.json")
        transcript_json = os.path.join(folder, f"{course_code}_transcripts.json")
        
        source_json = handout_json if os.path.exists(handout_json) else transcript_json
        
        if not os.path.exists(source_json):
            self._add_log(f"⚠️ No JSON file found at: {source_json}", "warning")
            return

        self.gen_pdf_btn.setEnabled(False)
        self.gen_pdf_btn.setText("🔄 Generating...")
        self._add_log(f"📄 Generating PDF from: {Path(source_json).name}", "info")

        try:
            from handout_pdf_generator import generate_handout_pdf

            # Build PDF name: "[User Entered Name] Handout.pdf"
            pdf_name = f"{course_code} Handout.pdf"
            output_path = os.path.join(folder, pdf_name)

            result = generate_handout_pdf(
                json_path=source_json,
                output_path=output_path,
                title=f"{subject} ({course_code})",
                subject_name=subject,
                course_code=course_code,
            )
            
            self._add_log(f"✅ PDF saved: {result}", "success")
            self.transcript_info.setText(f"📄 {pdf_name} — saved to {folder}")

        except Exception as e:
            self._add_log(f"❌ PDF generation failed: {str(e)}", "error")
        finally:
            self.gen_pdf_btn.setEnabled(True)
            self.gen_pdf_btn.setText("📄  Generate Handout PDF")

    # ── Open Folder ───────────────────────────────────

    def _open_output_folder(self):
        """Open the output folder in file explorer."""
        course_code = self.course_code_input.text().strip()
        if not course_code:
            return

        import re, subprocess
        prefix_match = re.match(r'^([A-Z]+)', course_code.upper())
        prefix = prefix_match.group(1) if prefix_match else course_code.upper()
        folder = os.path.join(r"E:\documents\vu-plan-handouts", f"vu-projects-{prefix}-pdfs")

        if os.path.exists(folder):
            subprocess.Popen(f'explorer "{folder}"')
        else:
            self._add_log(f"⚠️ Folder not found: {folder}", "warning")

    # ── Logging ───────────────────────────────────────

    def _add_log(self, message, level="info"):
        """Add a log entry with color coding."""
        colors = {
            "info": "#c9d1d9",
            "success": "#3fb950",
            "warning": "#d29922",
            "error": "#f85149",
        }
        color = colors.get(level, "#c9d1d9")

        if message.strip() == "=" * 60:
            self.log_text.append(f'<span style="color: {PALETTE["text_muted"]};">{"─" * 50}</span>')
        else:
            escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            self.log_text.append(f'<span style="color: {color};">{escaped}</span>')

        # Auto-scroll
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
