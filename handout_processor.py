"""
Handout Processor Module
Processes transcript JSON through Gemini to generate structured academic handouts.

Pipeline:
1. Read transcript JSON (lectures array)
2. Send each lecture's transcript to Gemini with handout prompt
3. Collect structured handout responses
4. Save as handout JSON

This uses the same Puppeteer-based Gemini interaction as the existing MCQ flow.
"""

import os
import json
import time
import threading
import traceback
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal

from gemini_client import GeminiClient


class HandoutProcessingThread(QThread):
    """
    Background thread for processing transcripts through Gemini
    to generate structured lecture handouts.
    
    Uses the same Puppeteer server (Node.js) approach as existing flows.
    """
    
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    awaiting_input_signal = pyqtSignal(str, str, int, int, str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, transcript_json_path: str, course_code: str,
                 subject_name: str, delay_seconds: float = 1.0):
        super().__init__()
        self.transcript_json_path = transcript_json_path
        self.course_code = course_code
        self.subject_name = subject_name
        self.delay_seconds = delay_seconds
        
        self.should_stop = False
        self.is_paused = False
        self.client = None
        
        # Input synchronization
        self._input_event = threading.Event()
        self._skip_event = threading.Event()
        self._input_text = None

    def stop(self):
        self.should_stop = True
        self._input_event.set()

    def pause(self):
        self.is_paused = True
        if self.client:
            self.client.pause()

    def resume(self):
        self.is_paused = False
        if self.client:
            self.client.resume()

    def submit_response(self, text):
        """Called by UI when user submits the handout response."""
        self._input_text = text
        self._input_event.set()

    def skip_current(self):
        """Skip the current lecture."""
        self._skip_event.set()
        self._input_event.set()

    def _wait_for_input(self, lecture_num, total):
        """Block until user submits response or skips."""
        self._input_event.clear()
        self._skip_event.clear()
        self._input_text = None

        self.awaiting_input_signal.emit(
            f"Lecture {lecture_num}", "handout",
            lecture_num, total, "Lecture Handout"
        )
        self.log_signal.emit(
            f"   ⏳ Waiting for Gemini response (paste or extract)...", "info"
        )

        while not self._input_event.is_set():
            if self.should_stop:
                return None
            self._input_event.wait(timeout=0.5)

        if self.should_stop:
            return None
        if self._skip_event.is_set():
            return None

        return self._input_text

    def run(self):
        """Main processing loop."""
        try:
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit("📝 Handout Processing Pipeline", "info")
            self.log_signal.emit(f"   Subject: {self.subject_name}", "info")
            self.log_signal.emit(f"   Course: {self.course_code}", "info")
            self.log_signal.emit("=" * 60, "info")

            # Load transcript JSON
            with open(self.transcript_json_path, 'r', encoding='utf-8') as f:
                transcripts = json.load(f)

            if not isinstance(transcripts, list) or not transcripts:
                self.finished_signal.emit(False, "Invalid or empty transcript JSON")
                return

            total = len(transcripts)
            self.log_signal.emit(f"📚 {total} lectures to process", "info")

            # Initialize Gemini client
            self.client = GeminiClient()
            if not self.client.check_health():
                self.finished_signal.emit(False, "Gemini server is not running")
                return

            # Determine output path
            import re
            prefix_match = re.match(r'^([A-Z]+)', self.course_code.upper())
            prefix = prefix_match.group(1) if prefix_match else self.course_code.upper()
            base_dir = r"E:\documents\vu-plan-handouts"
            folder = os.path.join(base_dir, f"vu-projects-{prefix}-pdfs")
            os.makedirs(folder, exist_ok=True)
            
            output_path = os.path.join(folder, f"{self.course_code}_handout_data.json")

            # Load existing progress
            handout_data = []
            completed_lectures = set()
            if os.path.exists(output_path):
                try:
                    with open(output_path, 'r', encoding='utf-8') as f:
                        handout_data = json.load(f)
                    if isinstance(handout_data, list):
                        completed_lectures = {h['lecture'] for h in handout_data if 'lecture' in h}
                        self.log_signal.emit(f"📂 Found {len(completed_lectures)} existing handouts — resuming", "info")
                except Exception:
                    handout_data = []

            # Process each lecture
            for entry in transcripts:
                if self.should_stop:
                    break

                # Wait while paused
                while self.is_paused:
                    if self.should_stop:
                        break
                    time.sleep(0.5)

                lecture_num = entry.get('lecture', 0)
                transcript = entry.get('transcript', '')

                # Skip already processed
                if lecture_num in completed_lectures:
                    self.log_signal.emit(f"⏭️ Lecture {lecture_num}/{total} already processed", "info")
                    self.progress_signal.emit(lecture_num, total)
                    continue

                if not transcript or transcript.startswith('[') and 'failed' in transcript.lower():
                    self.log_signal.emit(f"⏭️ Lecture {lecture_num}/{total} — no valid transcript", "warning")
                    continue

                self.log_signal.emit("", "info")
                self.log_signal.emit(f"📖 Lecture {lecture_num}/{total}", "info")
                self.log_signal.emit(f"   Transcript: {len(transcript)} characters", "info")

                self.progress_signal.emit(lecture_num, total)

                # Send to Gemini
                try:
                    # Reset chat for clean context
                    self.client.reset_chat()
                    
                    self.log_signal.emit("   📤 Sending to Gemini...", "info")
                    self.client.send_prompt(
                        transcript,
                        section=f"lecture_{lecture_num}",
                        content_type='lecture_handout'
                    )
                    self.log_signal.emit("   ✓ Prompt sent — waiting for response", "success")

                    # Wait for user to extract/paste response
                    response = self._wait_for_input(lecture_num, total)

                    if response is None:
                        if self._skip_event.is_set():
                            self.log_signal.emit(f"   ⏭️ Lecture {lecture_num} skipped", "warning")
                        continue

                    # Clean up markdown code blocks
                    cleaned = response.strip()
                    if cleaned.startswith('```markdown'):
                        cleaned = cleaned[len('```markdown'):].strip()
                    elif cleaned.startswith('```md'):
                        cleaned = cleaned[len('```md'):].strip()
                    elif cleaned.startswith('```'):
                        cleaned = cleaned[3:].strip()
                    if cleaned.endswith('```'):
                        cleaned = cleaned[:-3].strip()

                    # Save handout
                    handout_data.append({
                        'lecture': lecture_num,
                        'handout': cleaned
                    })

                    # Incremental save
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(handout_data, f, ensure_ascii=False, indent=2)

                    self.log_signal.emit(f"   ✅ Handout saved ({len(cleaned)} chars)", "success")

                    # Delay between requests
                    if lecture_num < total:
                        time.sleep(self.delay_seconds)

                except Exception as e:
                    self.log_signal.emit(f"   ❌ Failed: {str(e)}", "error")
                    continue

            # Done
            self.log_signal.emit("", "info")
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit("🎉 HANDOUT PROCESSING COMPLETE!", "success")
            self.log_signal.emit(f"   Output: {output_path}", "info")
            self.log_signal.emit("=" * 60, "info")

            self.finished_signal.emit(True, output_path)

        except Exception as e:
            self.log_signal.emit(f"❌ ERROR: {str(e)}", "error")
            self.log_signal.emit(traceback.format_exc(), "error")
            self.finished_signal.emit(False, str(e))
