"""
Transcript Thread Module
QThread worker for background YouTube transcription.

Wraps TranscriptPipeline with Qt signal integration for UI updates.
"""

from PyQt5.QtCore import QThread, pyqtSignal
import traceback


class TranscriptThread(QThread):
    """
    Background worker thread for YouTube transcription pipeline.
    
    Signals:
        log_signal(str, str): (message, level) — log output
        progress_signal(int, int): (current, total) — overall progress
        video_progress_signal(str, int, int): (title, current, total) — per-video
        playlist_resolved_signal(list): videos list resolved
        finished_signal(bool, str): (success, message/path)
    """
    
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    video_progress_signal = pyqtSignal(str, int, int)
    playlist_resolved_signal = pyqtSignal(list)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url: str, subject_name: str, course_code: str,
                 model_name: str = "medium", device: str = "auto",
                 output_base_dir: str = ""):
        super().__init__()
        self.url = url
        self.subject_name = subject_name
        self.course_code = course_code
        self.model_name = model_name
        self.device = device
        self.output_base_dir = output_base_dir
        
        self.should_stop = False
        self.is_paused = False
        self._pipeline = None

    def stop(self):
        """Stop processing (saves progress)."""
        self.should_stop = True
        if self._pipeline:
            self._pipeline.should_stop = True

    def pause(self):
        """Pause processing."""
        self.is_paused = True
        if self._pipeline:
            self._pipeline.is_paused = True

    def resume(self):
        """Resume processing."""
        self.is_paused = False
        if self._pipeline:
            self._pipeline.is_paused = False

    def run(self):
        """Main transcription workflow."""
        try:
            from transcript_engine import TranscriptPipeline

            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit("🎙️ YouTube Lecture Transcription Pipeline", "info")
            self.log_signal.emit(f"   Subject: {self.subject_name}", "info")
            self.log_signal.emit(f"   Course: {self.course_code}", "info")
            self.log_signal.emit(f"   Model: Whisper {self.model_name}", "info")
            self.log_signal.emit("=" * 60, "info")

            # Create pipeline
            self._pipeline = TranscriptPipeline(
                model_name=self.model_name,
                subject_name=self.subject_name,
                course_code=self.course_code,
                output_base_dir=self.output_base_dir
            )

            # Step 1: Resolve playlist
            self.log_signal.emit("🔍 Resolving playlist/video URL...", "info")
            videos = self._pipeline.resolve_playlist(
                self.url,
                log_callback=lambda msg, lvl: self.log_signal.emit(msg, lvl)
            )

            if not videos:
                self.finished_signal.emit(False, "No videos found at the given URL")
                return

            # Emit resolved videos to UI
            self.playlist_resolved_signal.emit(videos)

            # Step 2: Process all videos
            def on_progress(current, total, title):
                self.progress_signal.emit(current, total)
                self.video_progress_signal.emit(title, current, total)

            result_path = self._pipeline.process_all(
                progress_callback=on_progress,
                log_callback=lambda msg, lvl: self.log_signal.emit(msg, lvl)
            )

            if result_path:
                self.finished_signal.emit(True, result_path)
            else:
                self.finished_signal.emit(False, "Transcription completed but no output generated")

        except Exception as e:
            self.log_signal.emit(f"❌ TRANSCRIPTION ERROR: {str(e)}", "error")
            self.log_signal.emit(traceback.format_exc(), "error")
            self.finished_signal.emit(False, str(e))


class PlaylistResolveThread(QThread):
    """
    Quick background thread just for resolving playlist URLs.
    Used for the "Detect Playlist" button in the UI.
    """
    
    log_signal = pyqtSignal(str, str)
    resolved_signal = pyqtSignal(list)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            from transcript_engine import PlaylistResolver
            
            videos = PlaylistResolver.resolve(
                self.url,
                log_callback=lambda msg, lvl: self.log_signal.emit(msg, lvl)
            )
            
            if videos:
                self.resolved_signal.emit(videos)
                self.finished_signal.emit(True, f"Found {len(videos)} videos")
            else:
                self.resolved_signal.emit([])
                self.finished_signal.emit(False, "No videos found")
                
        except Exception as e:
            self.log_signal.emit(f"❌ Resolve failed: {str(e)}", "error")
            self.resolved_signal.emit([])
            self.finished_signal.emit(False, str(e))
