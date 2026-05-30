import json
import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from PyQt5.QtGui import QColor

PALETTE = {
    'bg': '#0d1117',
    'surface': '#161b22',
    'border': '#30363d',
    'accent': '#58a6ff',
    'success': '#3fb950',
    'warning': '#d29922',
    'error': '#f85149',
    'text': '#c9d1d9',
    'text_secondary': '#8b949e',
    'text_muted': '#484f58',
    'navy': '#030d1a',
    'row_alt': 'rgba(255,255,255,0.02)'
}

class LiveSyncTab(QWidget):
    def __init__(self, sync_manager=None):
        super().__init__()
        self.sync_manager = sync_manager
        self.jobs = {} # dict of event_id -> job info
        self._build_ui()
        
        if self.sync_manager:
            self.sync_manager.event_received.connect(self.on_event_received)
            self.sync_manager.connection_status.connect(self.on_connection_status)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("🌐 Live Global Dashboard")
        title.setStyleSheet(f"color: {PALETTE['text']}; font-size: 16pt; font-weight: 700;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.status_lbl = QLabel("🔴 Offline")
        self.status_lbl.setStyleSheet(f"color: {PALETTE['error']}; font-weight: 600; padding: 5px 10px; border-radius: 5px; background: {PALETTE['navy']};")
        header.addWidget(self.status_lbl)
        
        main_layout.addLayout(header)

        # Stats Row
        stats_row = QHBoxLayout()
        
        self.lbl_pending = self._create_stat_card("Pending", "0", PALETTE['warning'])
        self.lbl_processing = self._create_stat_card("Processing", "0", PALETTE['accent'])
        self.lbl_completed = self._create_stat_card("Completed", "0", PALETTE['success'])
        
        stats_row.addWidget(self.lbl_pending[0])
        stats_row.addWidget(self.lbl_processing[0])
        stats_row.addWidget(self.lbl_completed[0])
        main_layout.addLayout(stats_row)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Job / PDF Name", "Status", "Progress", "Last Update"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet(f"background: {PALETTE['surface']}; color: {PALETTE['text']}; border: 1px solid {PALETTE['border']};")
        main_layout.addWidget(self.table)

    def _create_stat_card(self, title, val, color):
        card = QFrame()
        card.setStyleSheet(f"background: {PALETTE['surface']}; border: 1px solid {PALETTE['border']}; border-radius: 8px;")
        layout = QVBoxLayout(card)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {PALETTE['text_secondary']};")
        v_lbl = QLabel(val)
        v_lbl.setStyleSheet(f"color: {color}; font-size: 18pt; font-weight: bold;")
        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        return card, v_lbl

    @pyqtSlot(bool)
    def on_connection_status(self, connected):
        if connected:
            self.status_lbl.setText("🟢 Online & Synced")
            self.status_lbl.setStyleSheet(f"color: {PALETTE['success']}; font-weight: 600; padding: 5px 10px; border-radius: 5px; background: {PALETTE['navy']};")
        else:
            self.status_lbl.setText("🔴 Offline")
            self.status_lbl.setStyleSheet(f"color: {PALETTE['error']}; font-weight: 600; padding: 5px 10px; border-radius: 5px; background: {PALETTE['navy']};")

    @pyqtSlot(dict)
    def on_event_received(self, event):
        payload = event.get('payload', {})
        event_type = event.get('event_type')
        job_id = payload.get('job_id')
        
        if not job_id:
            return
            
        if job_id not in self.jobs:
            self.jobs[job_id] = {
                'name': payload.get('pdf_name', 'Unknown PDF'),
                'status': 'Pending',
                'progress': '0%',
                'time': event.get('timestamp')
            }
            
        job = self.jobs[job_id]
        job['time'] = event.get('timestamp')
        
        if event_type == 'job_started':
            if job['status'] != 'Completed':
                job['status'] = 'Processing'
                job['progress'] = 'Started'
        elif event_type == 'job_progress':
            if job['status'] != 'Completed':
                job['status'] = 'Processing'
                job['progress'] = f"{payload.get('batch_idx')}/{payload.get('total_batches')} Batches"
        elif event_type == 'job_completed':
            job['status'] = 'Completed'
            job['progress'] = '100%'
        elif event_type == 'job_failed':
            job['status'] = 'Failed'
            job['progress'] = payload.get('error', 'Error')
            
        self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(0)
        pending, processing, completed = 0, 0, 0
        
        for job_id, job in self.jobs.items():
            if job['status'] == 'Pending': pending += 1
            elif job['status'] == 'Processing': processing += 1
            elif job['status'] == 'Completed': completed += 1
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(job_id[-6:]))
            self.table.setItem(row, 1, QTableWidgetItem(job['name']))
            
            status_item = QTableWidgetItem(job['status'])
            if job['status'] == 'Completed': status_item.setForeground(QColor(PALETTE['success']))
            elif job['status'] == 'Processing': status_item.setForeground(QColor(PALETTE['accent']))
            elif job['status'] == 'Failed': status_item.setForeground(QColor(PALETTE['error']))
            self.table.setItem(row, 2, status_item)
            
            self.table.setItem(row, 3, QTableWidgetItem(job['progress']))
            
            time_str = datetime.datetime.fromtimestamp(job['time']).strftime('%H:%M:%S')
            self.table.setItem(row, 4, QTableWidgetItem(time_str))
            
        self.lbl_pending[1].setText(str(pending))
        self.lbl_processing[1].setText(str(processing))
        self.lbl_completed[1].setText(str(completed))
