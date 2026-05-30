"""
Transcript Engine Module
Handles YouTube playlist resolution, audio extraction, and Whisper transcription.

Pipeline:
1. Resolve YouTube playlist/video URLs → list of videos
2. Extract audio from each video (yt-dlp → WAV 16kHz mono)
3. Transcribe audio using faster-whisper (GPU accelerated)
4. Save transcripts as JSON (lecture-by-lecture)

Dependencies: faster-whisper, yt-dlp
"""

import os
import re
import json
import tempfile
import subprocess
import time
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Callable

# CRITICAL FIX for Windows UI crash: 
# faster_whisper (CTranslate2) MUST be imported in the main thread first.
# Importing it for the first time inside a QThread causes a hard C++ abort.
try:
    import faster_whisper
except ImportError:
    pass


def _load_ffmpeg_path_from_config() -> str:
    """Load optional ffmpeg_path from config.json (if present)."""
    config_path = Path(__file__).resolve().with_name("config.json")
    if not config_path.exists():
        return ""
    try:
        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)
        return str(config.get("ffmpeg_path", "")).strip()
    except Exception:
        return ""


def _normalize_ffmpeg_dir(path_str: str) -> Optional[Path]:
    if not path_str:
        return None
    cleaned = path_str.strip().strip('"').strip("'")
    if not cleaned:
        return None
    path = Path(cleaned).expanduser()
    if path.is_file():
        return path.parent
    if path.is_dir():
        return path
    return None


def _has_ffmpeg_binaries(dir_path: Path) -> bool:
    ffmpeg_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    return (dir_path / ffmpeg_name).is_file() and (dir_path / ffprobe_name).is_file()


def resolve_ffmpeg_location(log_callback: Callable = None) -> Dict[str, Optional[str]]:
    """
    Resolve ffmpeg/ffprobe availability and optional location.

    Returns dict: {available: bool, location: Optional[str], source: str}
    - location is a directory path to pass to yt-dlp, or None when PATH is used.
    """
    def log(msg, level="info"):
        if log_callback:
            log_callback(msg, level)

    ffmpeg_on_path = shutil.which("ffmpeg")
    ffprobe_on_path = shutil.which("ffprobe")
    if ffmpeg_on_path and ffprobe_on_path:
        return {"available": True, "location": None, "source": "PATH"}

    candidates = []

    config_value = _load_ffmpeg_path_from_config()
    if config_value:
        candidates.append(("config", config_value))

    env_value = os.environ.get("FFMPEG_PATH", "").strip()
    if env_value:
        candidates.append(("env", env_value))

    base_dir = Path(__file__).resolve().parent
    common_dirs = [
        base_dir / "assets" / "ffmpeg" / "bin",
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
        Path("C:/Program Files (x86)/ffmpeg/bin"),
        Path("C:/ProgramData/chocolatey/bin"),
    ]

    userprofile = os.environ.get("USERPROFILE", "")
    if userprofile:
        user_dir = Path(userprofile)
        common_dirs.extend([
            user_dir / "scoop/apps/ffmpeg/current/bin",
            user_dir / "AppData/Local/Programs/ffmpeg/bin",
            user_dir / "AppData/Local/ffmpeg/bin",
        ])
        # Also scan Downloads for portable ffmpeg
        downloads = user_dir / "Downloads"
        if downloads.is_dir():
            for child in downloads.iterdir():
                if child.is_dir() and "ffmpeg" in child.name.lower():
                    bin_dir = child / "bin"
                    if bin_dir.is_dir():
                        common_dirs.append(bin_dir)

    for path in common_dirs:
        candidates.append(("auto", str(path)))

    for source, candidate in candidates:
        normalized = _normalize_ffmpeg_dir(candidate)
        if not normalized:
            continue
        if _has_ffmpeg_binaries(normalized):
            return {"available": True, "location": str(normalized), "source": source}

    if ffmpeg_on_path or ffprobe_on_path:
        log("⚠️ FFmpeg detected partially on PATH, but both ffmpeg and ffprobe are required", "warning")

    return {"available": False, "location": None, "source": ""}


# ─────────────────────────────────────────────────────────────
#  GPU VRAM helper – safe, non-crashing detection
# ─────────────────────────────────────────────────────────────

def _get_gpu_vram_gb() -> float:
    """
    Safely detect GPU VRAM in GB.
    Returns 0.0 if no GPU or detection fails.
    Uses nvidia-smi first (safest), then torch as fallback.
    """
    # Method 1: nvidia-smi (safest — no CUDA context created)
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            vram_mb = float(result.stdout.strip().split('\n')[0].strip())
            return round(vram_mb / 1024, 1)
    except Exception:
        pass

    # Method 2: torch (creates CUDA context – uses ~300-500MB VRAM itself)
    try:
        import torch
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            total_bytes = getattr(props, "total_memory", None)
            if total_bytes is None:
                total_bytes = getattr(props, "total_mem", 0)
            if total_bytes:
                return round(float(total_bytes) / (1024**3), 1)
    except Exception:
        pass

    return 0.0


def _choose_model_config(model_name: str, user_device: str, log_callback: Callable = None) -> Dict:
    """
    Choose the safest device/compute_type/beam_size configuration
    based on actual VRAM available.
    """
    def log(msg, level="info"):
        if log_callback:
            log_callback(msg, level)

    # If user explicitly chose CPU, respect that
    if user_device == "cpu":
        return {"device": "cpu", "compute_type": "int8", "beam_size": 5,
                "note": "CPU mode (user selected)"}

    vram_gb = _get_gpu_vram_gb()

    if vram_gb <= 0:
        log("   ⚠️ No NVIDIA GPU detected — using CPU", "warning")
        return {"device": "cpu", "compute_type": "int8", "beam_size": 5,
                "note": "No GPU detected"}

    log(f"   🔍 GPU VRAM detected: {vram_gb} GB")

    # ── Decision matrix ──────────────────────────────────────
    if model_name == "medium":
        if vram_gb >= 6.0:
            cfg = {"device": "cuda", "compute_type": "float16", "beam_size": 5,
                   "note": f"GPU float16 ({vram_gb}GB — plenty)"}
        elif vram_gb >= 4.0:
            cfg = {"device": "cuda", "compute_type": "int8", "beam_size": 5,
                   "note": f"GPU int8 ({vram_gb}GB — comfortable)"}
        elif vram_gb >= 3.0:
            cfg = {"device": "cuda", "compute_type": "int8", "beam_size": 1,
                   "note": f"GPU int8 beam=1 ({vram_gb}GB — tight for medium)"}
        else:
            log(f"   ⚠️ {vram_gb}GB VRAM is too low for medium model on GPU!", "warning")
            log(f"   🔄 Using CPU instead (still accurate, just slower)", "info")
            cfg = {"device": "cpu", "compute_type": "int8", "beam_size": 5,
                   "note": f"CPU int8 ({vram_gb}GB VRAM too low for medium on GPU)"}
    else:  # small
        if vram_gb >= 4.0:
            cfg = {"device": "cuda", "compute_type": "float16", "beam_size": 5,
                   "note": f"GPU float16 ({vram_gb}GB — plenty for small)"}
        elif vram_gb >= 2.5:
            cfg = {"device": "cuda", "compute_type": "int8", "beam_size": 5,
                   "note": f"GPU int8 ({vram_gb}GB — comfortable for small)"}
        elif vram_gb >= 1.5:
            # Small + int8 + beam=1 fits in ~1.0GB + context (perfect for MX250 2GB)
            cfg = {"device": "cuda", "compute_type": "int8", "beam_size": 1,
                   "note": f"GPU int8 beam=1 ({vram_gb}GB — tight for small, but safe)"}
        else:
            cfg = {"device": "cpu", "compute_type": "int8", "beam_size": 5,
                   "note": f"CPU int8 ({vram_gb}GB VRAM too low for small on GPU)"}

    log(f"   📊 Config: {cfg['device']} / {cfg['compute_type']} / beam={cfg['beam_size']}")
    log(f"   📝 {cfg['note']}")
    return cfg


# ─────────────────────────────────────────────────────────────
#  Playlist Resolver — fetches all video URLs from a playlist
# ─────────────────────────────────────────────────────────────

class PlaylistResolver:
    """
    Resolves YouTube URLs to a list of video metadata.

    Supports:
    - Full playlist URL (youtube.com/playlist?list=...)
    - Single video URL with playlist param (youtube.com/watch?v=...&list=...)
    - Single video URL (youtube.com/watch?v=...)

    Uses yt-dlp for reliable extraction.
    """

    @staticmethod
    def _extract_playlist_id(url: str) -> Optional[str]:
        """Extract playlist ID from URL if present."""
        match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url)
        return match.group(1) if match else None

    @staticmethod
    def resolve(url: str, log_callback: Callable = None) -> List[Dict]:
        """
        Resolve a YouTube URL to a list of video entries.

        Args:
            url: YouTube URL (playlist or single video)
            log_callback: Optional callback(msg, level) for progress logging

        Returns:
            List of dicts: [{video_id, title, url, index, duration}, ...]
        """
        def log(msg, level="info"):
            if log_callback:
                log_callback(msg, level)
            else:
                print(f"[{level}] {msg}")

        # Check if URL contains a playlist
        playlist_id = PlaylistResolver._extract_playlist_id(url)

        if playlist_id:
            resolve_url = f"https://www.youtube.com/playlist?list={playlist_id}"
            log(f"🔍 Detected playlist ID: {playlist_id}")
        else:
            resolve_url = url
            log(f"🔍 Single video URL detected")

        try:
            import yt_dlp

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'ignoreerrors': True,
            }

            videos = []
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(resolve_url, download=False)

                if info is None:
                    log("❌ Failed to extract video info", "error")
                    return []

                if 'entries' in info:
                    entries = list(info['entries'])
                    log(f"📋 Found playlist: {info.get('title', 'Unknown')} — {len(entries)} videos")

                    for i, entry in enumerate(entries, 1):
                        if entry is None:
                            continue
                        videos.append({
                            'video_id': entry.get('id', ''),
                            'title': entry.get('title', f'Video {i}'),
                            'url': entry.get('url', '') or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                            'index': i,
                            'duration': entry.get('duration', 0) or 0,
                        })
                else:
                    videos.append({
                        'video_id': info.get('id', ''),
                        'title': info.get('title', 'Unknown'),
                        'url': url,
                        'index': 1,
                        'duration': info.get('duration', 0) or 0,
                    })
                    log(f"📹 Single video: {info.get('title', 'Unknown')}")

            log(f"✅ Resolved {len(videos)} video(s)")
            return videos

        except Exception as e:
            log(f"❌ Playlist resolution failed: {str(e)}", "error")
            return []


# ─────────────────────────────────────────────────────────────
#  Audio Extractor — downloads audio from YouTube
# ─────────────────────────────────────────────────────────────

class AudioExtractor:
    """
    Extracts audio from YouTube videos using yt-dlp.
    Downloads as WAV at 16kHz mono (Whisper requirement).
    """

    @staticmethod
    def extract(video_url: str, output_dir: str, video_title: str = "audio",
                log_callback: Callable = None, ffmpeg_location: Optional[str] = None) -> Optional[str]:
        """
        Download and extract audio from a YouTube video.

        Args:
            video_url: YouTube video URL
            output_dir: Directory to save the audio file
            video_title: Title for the output file
            log_callback: Optional callback(msg, level) for logging

        Returns:
            Path to the extracted WAV file, or None on failure
        """
        def log(msg, level="info"):
            if log_callback:
                log_callback(msg, level)

        # Sanitize filename
        safe_name = re.sub(r'[^\w\s-]', '', video_title)[:80].strip()
        if not safe_name:
            safe_name = "audio"

        output_path = os.path.join(output_dir, f"{safe_name}.wav")

        try:
            import yt_dlp

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(output_dir, f"{safe_name}.%(ext)s"),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }],
                'postprocessor_args': [
                    '-ar', '16000',   # 16kHz sample rate (Whisper requirement)
                    '-ac', '1',       # Mono channel
                ],
                'quiet': True,
                'no_warnings': True,
                'overwrites': True,
            }

            if ffmpeg_location:
                ydl_opts['ffmpeg_location'] = ffmpeg_location

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            if os.path.exists(output_path):
                size_mb = os.path.getsize(output_path) / (1024 * 1024)
                log(f"   🔊 Audio extracted: {size_mb:.1f} MB")
                return output_path
            else:
                for f in os.listdir(output_dir):
                    if f.startswith(safe_name) and f.endswith('.wav'):
                        found_path = os.path.join(output_dir, f)
                        log(f"   🔊 Audio extracted: {os.path.getsize(found_path) / (1024*1024):.1f} MB")
                        return found_path

                log(f"   ❌ Audio file not found after extraction", "error")
                return None

        except Exception as e:
            log(f"   ❌ Audio extraction failed: {str(e)}", "error")
            return None


# ─────────────────────────────────────────────────────────────
#  Whisper Transcriber — GPU-accelerated transcription
# ─────────────────────────────────────────────────────────────

class WhisperTranscriber:
    """
    Transcribes audio files using faster-whisper (CTranslate2).

    Supports:
    - GPU acceleration (CUDA) with VRAM-aware configuration
    - Automatic CPU fallback for low-VRAM GPUs
    - Whisper Small (~1GB) and Medium (~1.5GB) models
    - Urdu + English bilingual transcription

    IMPORTANT (MX250 / 2GB VRAM fix):
      The medium model in float16 needs ~2.0GB + CUDA context (~0.5GB) = ~2.5GB.
      On a 2GB GPU this causes a HARD CRASH (not a catchable Python exception).
      We now detect VRAM *before* loading and route to CPU when necessary.
    """

    def __init__(self, model_name: str = "medium", device: str = "auto",
                 compute_type: str = "auto"):
        """
        Initialize the Whisper transcriber.

        Args:
            model_name: "small" or "medium" (Whisper model size)
            device: "cuda", "cpu", or "auto" (VRAM-aware auto-detect)
            compute_type: "auto" (recommended), "float16", "int8", or "float32"
        """
        self.model_name = model_name
        self.model = None
        self.device = device
        self.compute_type = compute_type
        self._config = None  # Resolved config after VRAM check

    def _ensure_model_loaded(self, log_callback: Callable = None):
        """Load the model if not already loaded. VRAM-safe."""
        if self.model is not None:
            return

        def log(msg, level="info"):
            if log_callback:
                log_callback(msg, level)

        log(f"🤖 Loading Whisper {self.model_name} model...")

        # ── Step 1: Choose safe configuration based on actual VRAM ──
        self._config = _choose_model_config(
            self.model_name, self.device, log_callback
        )
        actual_device = self._config["device"]
        actual_compute = self._config["compute_type"]

        # ── Step 2: Load model with chosen config ──
        try:
            from faster_whisper import WhisperModel

            log(f"   🔄 Loading model on {actual_device} ({actual_compute})...")
            self.model = WhisperModel(
                self.model_name,
                device=actual_device,
                compute_type=actual_compute
            )
            log(f"   ✅ Model loaded successfully on {actual_device} ({actual_compute})")

        except Exception as e:
            error_msg = str(e).lower()
            # Catch CUDA out-of-memory or any CUDA error → fall back to CPU
            if actual_device == "cuda" and ("cuda" in error_msg or "memory" in error_msg
                                            or "out of memory" in error_msg
                                            or "cudnn" in error_msg):
                log(f"   ⚠️ GPU loading failed: {e}", "warning")
                log(f"   🔄 Falling back to CPU (safe mode)...", "info")
                actual_device = "cpu"
                actual_compute = "int8"
                self._config = {"device": "cpu", "compute_type": "int8",
                                "beam_size": 5, "note": "CPU fallback after GPU error"}
                try:
                    from faster_whisper import WhisperModel
                    self.model = WhisperModel(
                        self.model_name,
                        device=actual_device,
                        compute_type=actual_compute
                    )
                    log(f"   ✅ Model loaded on CPU (int8) — fallback successful")
                except Exception as e2:
                    log(f"   ❌ CPU fallback also failed: {str(e2)}", "error")
                    raise
            else:
                log(f"   ❌ Failed to load model: {str(e)}", "error")
                raise

    def transcribe(self, audio_path: str, log_callback: Callable = None) -> str:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to WAV audio file
            log_callback: Optional callback(msg, level) for logging

        Returns:
            Full transcript text string
        """
        def log(msg, level="info"):
            if log_callback:
                log_callback(msg, level)

        self._ensure_model_loaded(log_callback)

        log(f"   🎤 Transcribing audio...")
        start_time = time.time()

        # Use the beam_size from our VRAM-safe config
        beam_size = self._config.get("beam_size", 5) if self._config else 5

        try:
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=beam_size,
                language=None,           # Auto-detect (Urdu/English/mixed)
                task="transcribe",       # Keep original language
                vad_filter=True,         # Filter out silence/noise
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
                condition_on_previous_text=True,
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.4,
            )

            transcript_parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    transcript_parts.append(text)

            full_transcript = " ".join(transcript_parts)
            elapsed = time.time() - start_time

            detected_lang = info.language if info else "unknown"
            lang_prob = f"{info.language_probability:.1%}" if info else "?"

            log(f"   ✅ Transcribed in {elapsed:.1f}s — Language: {detected_lang} ({lang_prob})")
            log(f"   📝 {len(full_transcript)} characters, {len(transcript_parts)} segments")

            return full_transcript

        except Exception as e:
            log(f"   ❌ Transcription failed: {str(e)}", "error")
            return ""

    @staticmethod
    def get_gpu_info() -> Dict:
        """Get GPU information for UI display."""
        # Use nvidia-smi (safest, doesn't create CUDA context)
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total',
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(',')
                vram_mb = float(parts[1].strip())
                vram_gb = round(vram_mb / 1024, 1)
                note = ""
                if vram_gb < 4.0:
                    note = " ⚠️ Low VRAM — will use CPU (need 4GB+ for GPU)"
                return {
                    'available': True,
                    'name': parts[0].strip(),
                    'vram_gb': vram_gb,
                    'cuda_version': 'detected',
                    'note': note,
                }
        except Exception:
            pass

        try:
            import torch
            if torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                total_bytes = getattr(props, "total_memory", None)
                if total_bytes is None:
                    total_bytes = getattr(props, "total_mem", 0)
                vram_gb = round(float(total_bytes) / (1024**3), 1) if total_bytes else 0.0
                note = ""
                if vram_gb < 4.0:
                    note = " ⚠️ Low VRAM — will use CPU (need 4GB+ for GPU)"
                return {
                    'available': True,
                    'name': torch.cuda.get_device_name(0),
                    'vram_gb': vram_gb,
                    'cuda_version': torch.version.cuda or "unknown",
                    'note': note,
                }
        except ImportError:
            pass

        return {
            'available': False,
            'name': 'No GPU detected',
            'vram_gb': 0,
            'cuda_version': 'N/A',
            'note': '',
        }


# ─────────────────────────────────────────────────────────────
#  Transcript Pipeline — orchestrates the full flow
# ─────────────────────────────────────────────────────────────

class TranscriptPipeline:
    """
    Full transcription pipeline:
    1. Resolve playlist → list of videos
    2. For each video: download audio → transcribe → append to JSON
    3. Save incremental progress

    JSON output format:
    [
        {"lecture": 1, "transcript": "Full text..."},
        {"lecture": 2, "transcript": "Full text..."},
    ]
    """

    def __init__(self, model_name: str = "medium", subject_name: str = "",
                 course_code: str = "", output_base_dir: str = ""):
        self.model_name = model_name
        self.subject_name = subject_name
        self.course_code = course_code
        self.output_base_dir = output_base_dir or r"E:\documents\vu-plan-handouts"

        self.transcriber = WhisperTranscriber(model_name=model_name)
        self.videos = []
        self.transcripts = []
        self.should_stop = False
        self.is_paused = False

    def _get_output_folder(self) -> str:
        prefix_match = re.match(r'^([A-Z]+)', self.course_code.upper())
        prefix = prefix_match.group(1) if prefix_match else self.course_code.upper()

        folder_name = f"vu-projects-{prefix}-pdfs"
        folder_path = os.path.join(self.output_base_dir, folder_name)

        os.makedirs(folder_path, exist_ok=True)
        return folder_path

    def _get_transcript_json_path(self) -> str:
        folder = self._get_output_folder()
        filename = f"{self.course_code}_transcripts.json"
        return os.path.join(folder, filename)

    def _save_progress(self):
        json_path = self._get_transcript_json_path()
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.transcripts, f, ensure_ascii=False, indent=2)
        return json_path

    def _load_existing_progress(self) -> int:
        json_path = self._get_transcript_json_path()
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.transcripts = json.load(f)
                if isinstance(self.transcripts, list):
                    return len(self.transcripts)
            except Exception:
                pass
        self.transcripts = []
        return 0

    def resolve_playlist(self, url: str, log_callback: Callable = None) -> List[Dict]:
        self.videos = PlaylistResolver.resolve(url, log_callback)
        return self.videos

    def preload_model(self, log_callback: Callable = None):
        """
        Eagerly load the Whisper model BEFORE starting video processing.
        This lets us fail fast (and fall back to CPU) before any downloads.
        """
        def log(msg, level="info"):
            if log_callback:
                log_callback(msg, level)

        log("🔧 Pre-loading Whisper model (VRAM safety check)...")
        self.transcriber._ensure_model_loaded(log_callback)
        log("✅ Whisper model ready!")

    def process_all(self, progress_callback: Callable = None,
                    log_callback: Callable = None) -> str:
        def log(msg, level="info"):
            if log_callback:
                log_callback(msg, level)

        if not self.videos:
            log("❌ No videos to process", "error")
            return ""

        total = len(self.videos)

        # Check for existing progress (resume support)
        completed = self._load_existing_progress()
        if completed > 0:
            log(f"📂 Found {completed} existing transcripts — resuming from lecture {completed + 1}")

        # Preflight: ensure ffmpeg/ffprobe are available
        ffmpeg_info = resolve_ffmpeg_location(log_callback)
        if not ffmpeg_info["available"]:
            raise RuntimeError(
                "FFmpeg not found. Install ffmpeg and ffprobe and ensure they are on PATH, "
                "or set ffmpeg_path in config.json or FFMPEG_PATH to the folder containing "
                "ffmpeg.exe and ffprobe.exe."
            )

        if ffmpeg_info["source"] == "PATH":
            log("✅ FFmpeg found on PATH")
        else:
            log(f"✅ Using FFmpeg from: {ffmpeg_info['location']}")

        # Pre-load Whisper model BEFORE starting downloads
        # This is critical: if GPU loading would crash, it crashes here
        # before we waste time downloading audio files.
        self.preload_model(log_callback)

        # Create temp directory for audio files
        temp_dir = tempfile.mkdtemp(prefix="whisper_audio_")
        log(f"📁 Temp audio dir: {temp_dir}")

        try:
            for video in self.videos:
                if self.should_stop:
                    log("⏹ Stopped by user", "warning")
                    break

                while self.is_paused:
                    if self.should_stop:
                        break
                    time.sleep(0.5)

                idx = video['index']

                if idx <= completed:
                    log(f"⏭️ Lecture {idx}/{total} already transcribed — skipping")
                    if progress_callback:
                        progress_callback(idx, total, video['title'])
                    continue

                title = video['title']
                video_url = video['url']

                if not video_url.startswith('http'):
                    video_url = f"https://www.youtube.com/watch?v={video['video_id']}"

                log("")
                log(f"{'='*60}")
                log(f"📹 Lecture {idx}/{total}: {title}")
                log(f"{'='*60}")

                if progress_callback:
                    progress_callback(idx, total, title)

                # Step 1: Extract audio
                log(f"   🔊 Extracting audio...")
                audio_path = AudioExtractor.extract(
                    video_url,
                    temp_dir,
                    f"lecture_{idx}",
                    log_callback,
                    ffmpeg_location=ffmpeg_info["location"],
                )

                if not audio_path:
                    log(f"   ⚠️ Audio extraction failed — skipping", "warning")
                    self.transcripts.append({
                        "lecture": idx,
                        "transcript": "[Audio extraction failed]"
                    })
                    self._save_progress()
                    continue

                # Step 2: Transcribe
                transcript_text = self.transcriber.transcribe(audio_path, log_callback)

                if not transcript_text:
                    log(f"   ⚠️ Transcription produced empty result", "warning")
                    transcript_text = "[Transcription failed - empty result]"

                # Step 3: Save to list
                self.transcripts.append({
                    "lecture": idx,
                    "transcript": transcript_text
                })

                saved_path = self._save_progress()
                log(f"   💾 Saved ({len(self.transcripts)}/{total} lectures)")

                # Clean up audio file to save disk space
                try:
                    os.remove(audio_path)
                except Exception:
                    pass

            # Final save
            final_path = self._save_progress()
            log("")
            log(f"{'='*60}")
            log(f"🎉 TRANSCRIPTION COMPLETE!")
            log(f"   Processed: {len(self.transcripts)}/{total} lectures")
            log(f"   Output: {final_path}")
            log(f"{'='*60}")

            return final_path

        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
