"""
Highlight Processor Module
Background worker thread for the Highlighted Handouts pipeline.

Flow:
1. Ensure PDF is converted to Markdown (auto-convert if needed)
2. Split Markdown into mids/finals sections
3. Split each section into batches (~15 pages worth of text)
4. Send each batch to Gemini with review topics
5. Gemini returns same text with **bold** on important phrases
6. Accumulate highlighted Markdown
7. Generate highlighted PDF via highlight_pdf_generator
"""

from PyQt5.QtCore import QThread, pyqtSignal
from gemini_client import GeminiClient
import threading
import traceback
import time
import os
import json
import math
import re
from pathlib import Path

class SkipPDFException(Exception):
    pass


# ─────────────────────────────────────────────────────────────
#  Post-processing: Highlight Quality Validation
# ─────────────────────────────────────────────────────────────

# Common words that should NEVER be highlighted alone
_COMMON_WORDS = frozenset([
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
    'should', 'may', 'might', 'must', 'can', 'could', 'also', 'some',
    'any', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other',
    'such', 'no', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
    'very', 'just', 'but', 'and', 'or', 'nor', 'if', 'then', 'else',
    'when', 'where', 'why', 'how', 'what', 'which', 'who', 'whom',
    'this', 'that', 'these', 'those', 'it', 'its', 'of', 'in', 'on',
    'at', 'to', 'for', 'with', 'about', 'by', 'from', 'as', 'into',
    'through', 'during', 'before', 'after', 'above', 'below', 'between',
    'under', 'again', 'further', 'once', 'here', 'there', 'up', 'down',
    'out', 'off', 'over', 'because', 'while', 'however', 'therefore',
    'although', 'since', 'unless', 'until', 'yet', 'still', 'already',
    'according', 'example', 'following', 'etc', 'i.e', 'e.g',
    'like', 'given', 'based', 'used', 'using', 'called', 'known',
    'refer', 'refers', 'refers', 'need', 'needs', 'make', 'makes',
])


def _strip_common_word_highlights(text: str) -> str:
    """
    Remove **bold** markers from single common words.
    Keeps bold on multi-word phrases and meaningful single words.
    """
    def _check_bold(match):
        inner = match.group(1).strip()
        # Single word check
        words = inner.split()
        if len(words) == 1:
            word_lower = inner.lower().strip('.,;:!?()"\'')
            if word_lower in _COMMON_WORDS:
                return inner  # Remove bold markers
            # Also strip if it's a very short non-meaningful word (1-2 chars)
            if len(word_lower) <= 2 and not word_lower.isdigit():
                return inner
        return match.group(0)  # Keep bold

    return re.sub(r'\*\*(.*?)\*\*', _check_bold, text)


def _validate_highlight_quality(text: str, log_fn=None) -> tuple:
    """
    Validate and clean highlight quality.
    Returns (cleaned_text, density, bold_count).
    
    Density = highlights per 1000 characters.
    Acceptable: < 6.0 (roughly 10-15% of text)
    Warning: 6.0 - 10.0
    Critical: > 10.0 (strip common words aggressively)
    """
    bold_count = text.count('**') // 2
    text_len = len(re.sub(r'\*\*', '', text))  # Length without markers
    density = (bold_count / max(text_len, 1)) * 1000

    if log_fn:
        log_fn(f"   📊 Highlight density: {density:.1f}/1000chars ({bold_count} highlights in {text_len} chars)", "info")

    # Always strip common single-word highlights
    cleaned = _strip_common_word_highlights(text)

    if density > 10.0:
        if log_fn:
            log_fn(f"   ⚠️ Over-highlighted! Density {density:.1f} > 10.0 — stripping aggressively", "warning")
        # Second pass: also strip 2-word phrases that are too generic
        def _check_short_phrases(match):
            inner = match.group(1).strip()
            words = inner.split()
            if len(words) <= 2:
                # Check if ALL words are common
                if all(w.lower().strip('.,;:!?()') in _COMMON_WORDS for w in words):
                    return inner
            return match.group(0)
        cleaned = re.sub(r'\*\*(.*?)\*\*', _check_short_phrases, cleaned)
    elif density > 6.0:
        if log_fn:
            log_fn(f"   ⚠️ Highlight density slightly high ({density:.1f}/1000) — minor cleanup applied", "warning")

    # Recalculate after cleanup
    final_count = cleaned.count('**') // 2
    if final_count < bold_count and log_fn:
        log_fn(f"   🧹 Cleaned: {bold_count} → {final_count} highlights", "info")

    return cleaned, density, final_count


# ─────────────────────────────────────────────────────────────
#  Configuration Constants (adjustable without UI)
# ─────────────────────────────────────────────────────────────
DEFAULT_CHARS_PER_PAGE = 400
DEFAULT_PAGES_PER_BATCH = 15


def _load_highlight_config():
    """Load highlight-specific config from config.json."""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return {
            'chars_per_page': config.get('highlight_chars_per_page', DEFAULT_CHARS_PER_PAGE),
            'pages_per_batch': config.get('highlight_pages_per_batch', DEFAULT_PAGES_PER_BATCH),
            'batch_char_limit': config.get('highlight_batch_char_limit', 20000),
            'mids_percentage': config.get('mids_percentage', 95),
        }
    except Exception:
        return {
            'chars_per_page': DEFAULT_CHARS_PER_PAGE,
            'pages_per_batch': DEFAULT_PAGES_PER_BATCH,
            'batch_char_limit': 20000,
            'mids_percentage': 95,
        }


def _split_into_batches(text: str, batch_size: int) -> list:
    """
    Split text into batches of approximately `batch_size` characters,
    splitting on paragraph boundaries (double newline) to avoid
    cutting mid-sentence.

    Returns list of text chunks.
    """
    if len(text) <= batch_size:
        return [text]

    batches = []
    remaining = text

    while remaining:
        if len(remaining) <= batch_size:
            batches.append(remaining)
            break

        # Find the best split point near batch_size
        # Look for paragraph boundary (double newline) around the target position
        target = batch_size
        best_split = -1

        # Search backward from target for a paragraph break
        search_start = max(0, target - 1000)
        search_region = remaining[search_start:target + 500]

        # Try double newline first
        last_para = search_region.rfind('\n\n')
        if last_para != -1:
            best_split = search_start + last_para + 2
        else:
            # Try single newline
            last_nl = search_region.rfind('\n')
            if last_nl != -1:
                best_split = search_start + last_nl + 1
            else:
                # Last resort: split at target
                best_split = target

        # Ensure we make progress
        if best_split <= 0:
            best_split = target

        batches.append(remaining[:best_split])
        remaining = remaining[best_split:]

    return batches


class MarkdownConvertThread(QThread):
    """Thread for converting PDFs to Markdown (runs in background)."""

    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, pdf_paths, force=False):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.force = force
        self.should_stop = False

    def stop(self):
        self.should_stop = True

    def run(self):
        try:
            from markdown_converter import convert_single_pdf

            total = len(self.pdf_paths)
            success = 0
            failed = 0

            self.log_signal.emit(f"📄 Converting {total} PDF(s) to Markdown...", "info")

            for i, pdf_path in enumerate(self.pdf_paths, 1):
                if self.should_stop:
                    self.log_signal.emit("❌ Stopped by user", "error")
                    break

                self.progress_signal.emit(i, total)
                pdf_name = Path(pdf_path).stem

                def log_cb(msg, level):
                    self.log_signal.emit(msg, level)

                result = convert_single_pdf(pdf_path, force=self.force, log_callback=log_cb)

                if result:
                    success += 1
                else:
                    failed += 1

            self.log_signal.emit(f"✅ Markdown conversion complete: {success} success, {failed} failed", "success")
            self.finished_signal.emit(True, f"Converted {success}/{total} PDFs")

        except Exception as e:
            self.log_signal.emit(f"❌ Conversion error: {str(e)}", "error")
            self.log_signal.emit(traceback.format_exc(), "error")
            self.finished_signal.emit(False, str(e))


class HighlightProcessingThread(QThread):
    """
    Process PDFs through the Highlighted Handouts pipeline.

    For each PDF:
    1. Check/convert to Markdown
    2. Split into mids/finals
    3. Batch and send to Gemini
    4. Accumulate highlighted text
    5. Generate highlighted PDF
    """

    # Signals (same pattern as BatchProcessingThread)
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    status_signal = pyqtSignal(str)
    current_pdf_signal = pyqtSignal(str, int, int)
    position_signal = pyqtSignal(str, int, str, str, int)
    finished_signal = pyqtSignal(bool, str)

    # Manual input signals
    awaiting_input_signal = pyqtSignal(str, str, int, int, str)
    json_invalid_signal = pyqtSignal(str)

    def __init__(self, pdf_paths, selected_sections=None,
                 delay_seconds=1, chat_reset_threshold=5,
                 **kwargs):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.selected_sections = selected_sections or ['mids', 'finals']
        self.delay_seconds = float(delay_seconds)
        self.chat_reset_threshold = chat_reset_threshold

        self.should_stop = False
        self.is_paused = False
        self.client = None
        self.request_count = 0

        # Current batch data for repeat
        self._current_batch_text = None
        self._current_batch_section = None
        self._current_batch_review_topics = []

        # Reviews context
        self.use_reviews_for_highlights = True

        # Manual input synchronization
        self._input_event = threading.Event()
        self._skip_event = threading.Event()
        self._skip_pdf_event = threading.Event()
        self._repeat_event = threading.Event()
        self._input_text = None
        self._input_source = None

    def skip_current_batch(self):
        """Skip the current batch."""
        self._skip_event.set()
        self._input_event.set()

    def skip_current_pdf(self):
        """Skip the entire current PDF."""
        self._skip_pdf_event.set()
        self._input_event.set()

    def repeat_current_batch(self):
        """Repeat the current batch by re-sending the same prompt."""
        self._repeat_event.set()
        self._input_event.set()

    def stop(self):
        """Stop processing."""
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

    def submit_json(self, text, source='manual'):
        """
        Called by UI when user submits the highlighted markdown response.
        Note: We reuse 'submit_json' name for compatibility with existing UI flow.
        """
        self._input_text = text
        self._input_source = source
        self._input_event.set()

    def _wait_for_user_input(self, pdf_name, section, batch_idx, total_batches, content_type_label):
        """Block until user submits response or skips/stops."""
        self._input_event.clear()
        self._skip_event.clear()
        self._skip_pdf_event.clear()
        self._repeat_event.clear()
        self._input_text = None
        self._input_source = None

        self.awaiting_input_signal.emit(pdf_name, section, batch_idx, total_batches, content_type_label)
        self.status_signal.emit(f"⏳ Waiting for response — {pdf_name}, {section} batch {batch_idx}/{total_batches}")

        while not self._input_event.is_set():
            if self.should_stop:
                return None
            self._input_event.wait(timeout=0.5)

        if self.should_stop:
            return None
        if self._skip_pdf_event.is_set():
            return '__SKIP_PDF__'
        if self._skip_event.is_set():
            return None
        if self._repeat_event.is_set():
            return '__REPEAT__'

        source_label = "extracted" if self._input_source == 'extract' else "manual paste"
        self.log_signal.emit(f"   📥 Response received via {source_label} ({len(self._input_text or '')} chars)", "info")
        return self._input_text

    def run(self):
        """Main processing loop."""
        total_pdfs = len(self.pdf_paths)
        successful = 0
        failed = 0
        failed_pdfs = []

        try:
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit(f"🖍️ Highlighted Handouts: {total_pdfs} PDF(s)", "info")
            self.log_signal.emit("=" * 60, "info")

            # Initialize Gemini client
            self.client = GeminiClient()
            if not self.client.check_health():
                raise Exception("Gemini server is not running or not initialized")

            # Load config
            h_config = _load_highlight_config()
            batch_char_size = h_config['batch_char_limit']
            mids_pct = h_config['mids_percentage']

            for idx, pdf_path in enumerate(self.pdf_paths, 1):
                self._skip_pdf_event.clear()
                if self.should_stop:
                    self.log_signal.emit("❌ Stopped by user", "error")
                    break

                pdf_name = os.path.basename(pdf_path)
                pdf_stem = Path(pdf_path).stem
                self.current_pdf_signal.emit(pdf_name, idx, total_pdfs)

                self.log_signal.emit("", "info")
                self.log_signal.emit("=" * 60, "info")
                self.log_signal.emit(f"📄 PDF {idx}/{total_pdfs}: {pdf_name}", "info")
                self.log_signal.emit("=" * 60, "info")

                # Step 1: Ensure Markdown exists
                self.log_signal.emit("📝 Checking Markdown conversion...", "info")
                from markdown_converter import is_already_converted, get_markdown_path, convert_single_pdf

                if not is_already_converted(pdf_path):
                    self.log_signal.emit("   Converting PDF to Markdown first...", "info")
                    md_path = convert_single_pdf(pdf_path, log_callback=lambda m, l: self.log_signal.emit(m, l))
                    if not md_path:
                        self.log_signal.emit(f"❌ Markdown conversion failed for {pdf_name}", "error")
                        failed += 1
                        failed_pdfs.append(pdf_name)
                        continue
                else:
                    md_path = get_markdown_path(pdf_path)
                    self.log_signal.emit(f"   ✓ Markdown already exists", "success")

                # Step 2: Read full Markdown
                try:
                    with open(md_path, 'r', encoding='utf-8') as f:
                        full_markdown = f.read()
                    self.log_signal.emit(f"   📖 Loaded Markdown: {len(full_markdown)} chars", "info")
                except Exception as e:
                    self.log_signal.emit(f"❌ Failed to read Markdown: {e}", "error")
                    failed += 1
                    failed_pdfs.append(pdf_name)
                    continue

                # Step 3: Split into mids/finals
                total_chars = len(full_markdown)
                mids_chars = int(total_chars * (mids_pct / 100) * 0.5)
                # Adjust split to paragraph boundary
                split_point = mids_chars
                para_break = full_markdown.find('\n\n', max(0, split_point - 200), split_point + 200)
                if para_break != -1:
                    split_point = para_break + 2

                sections_data = {}
                page_ranges = {}
                
                import fitz
                try:
                    doc = fitz.open(pdf_path)
                    total_pages = len(doc)
                    doc.close()
                except Exception:
                    total_pages = 1
                
                mids_pages_count = int(total_pages * (mids_pct / 100) * 0.5)

                if 'mids' in self.selected_sections:
                    sections_data['mids'] = full_markdown[:split_point]
                    page_ranges['mids'] = (0, max(0, mids_pages_count - 1))
                if 'finals' in self.selected_sections:
                    sections_data['finals'] = full_markdown[split_point:]
                    page_ranges['finals'] = (mids_pages_count, total_pages - 1)

                self.log_signal.emit(f"   📚 Mids: {len(sections_data.get('mids', ''))} chars, Finals: {len(sections_data.get('finals', ''))} chars", "info")

                # Reset chat for fresh start
                self.log_signal.emit("🔄 Resetting Gemini chat...", "info")
                if not self.client.reset_chat():
                    self.log_signal.emit("⚠️ Chat reset failed, continuing...", "warning")
                self.request_count = 0

                # Step 4: Process each section
                all_highlighted = {}

                try:
                    for section in self.selected_sections:
                        if self.should_stop:
                            break

                        section_text = sections_data.get(section, '')
                        if not section_text.strip():
                            self.log_signal.emit(f"   ⏭️ Skipping {section} — empty", "warning")
                            continue

                        self.log_signal.emit(f"", "info")
                        self.log_signal.emit(f"📚 {section.upper()} Highlighting ({len(section_text)} chars)", "info")

                        # Split into batches
                        batches = _split_into_batches(section_text, batch_char_size)
                        self.log_signal.emit(f"   Split into {len(batches)} batches (~{h_config['pages_per_batch']} pages each)", "info")

                        # Reset chat for new section
                        if not self.client.reset_chat():
                            self.log_signal.emit("⚠️ Chat reset failed, continuing...", "warning")
                        self.request_count = 0

                        highlighted_parts = []

                        for batch_idx, batch_text in enumerate(batches, 1):
                            if self.should_stop:
                                break

                            # Wait while paused
                            while self.is_paused:
                                if self.should_stop:
                                    break
                                self.status_signal.emit("⏸️ Paused")
                                time.sleep(1)

                            self.position_signal.emit(pdf_path, idx, pdf_name, section, batch_idx)

                            self.log_signal.emit("", "info")
                            self.log_signal.emit(f"📦 Batch {batch_idx}/{len(batches)} ({len(batch_text)} chars)", "info")

                            try:
                                start_time = time.time()

                                # Auto-reset chat if needed
                                if self.request_count > 0 and self.request_count % self.chat_reset_threshold == 0:
                                    self.log_signal.emit(f"🔄 Auto-reset after {self.request_count} requests...", "info")
                                    self.client.reset_chat()

                                # Get review topics
                                review_topics_list = []
                                if self.use_reviews_for_highlights:
                                    try:
                                        from reviews_manager import get_raw_review_topics
                                        from folder_organizer import extract_full_subject_code
                                        subj = extract_full_subject_code(pdf_stem)
                                        if subj and subj != 'MISC':
                                            review_topics_list = get_raw_review_topics(subj, category=section)
                                            if review_topics_list:
                                                self.log_signal.emit(f"   📝 [{section.upper()}] {len(review_topics_list)} review topics for {subj}", "info")
                                    except Exception as e:
                                        self.log_signal.emit(f"   ⚠️ Reviews extraction failed: {e}", "warning")

                                # Save current state for repeat
                                self._current_batch_text = batch_text
                                self._current_batch_section = section
                                self._current_batch_review_topics = review_topics_list

                                # Check if PDF was skipped
                                if self._skip_pdf_event.is_set():
                                    raise SkipPDFException()

                                # Send to Gemini
                                self.log_signal.emit("   📤 Sending to Gemini...", "info")
                                self.client.send_prompt(
                                    batch_text,
                                    section=section,
                                    pages_count=h_config['pages_per_batch'],
                                    content_type='highlighted_handout',
                                    review_topics=review_topics_list
                                )
                                self.log_signal.emit("   ✓ Prompt sent — waiting for your input", "success")

                                # Wait for response (retry loop)
                                while True:
                                    raw_response = self._wait_for_user_input(
                                        pdf_name, section, batch_idx, len(batches), "Highlighted Handout"
                                    )

                                    if raw_response is None:
                                        if self._skip_event.is_set():
                                            self.log_signal.emit("   ⏭️ Batch skipped by user", "warning")
                                            # Use original text (unhighlighted) as fallback
                                            highlighted_parts.append(batch_text)
                                        break

                                    if raw_response == '__SKIP_PDF__':
                                        self.log_signal.emit("⚠️ Skipping entire PDF as requested.", "warning")
                                        raise SkipPDFException()

                                    # Handle repeat request
                                    if raw_response == '__REPEAT__':
                                        self.log_signal.emit("   🔄 Repeating batch — re-sending prompt...", "info")
                                        try:
                                            self.client.send_prompt(
                                                self._current_batch_text,
                                                section=self._current_batch_section or section,
                                                pages_count=h_config['pages_per_batch'],
                                                content_type='highlighted_handout',
                                                review_topics=self._current_batch_review_topics
                                            )
                                            self.log_signal.emit("   ✓ Prompt re-sent — waiting for your input", "success")
                                        except Exception as e:
                                            self.log_signal.emit(f"   ❌ Repeat failed: {e}", "error")
                                        continue
                                    # Basic validation: check that it's not empty and contains some bold markers
                                    if raw_response and len(raw_response.strip()) > 50:
                                        # Clean up markdown code blocks if Gemini wrapped it
                                        cleaned = raw_response.strip()
                                        if cleaned.startswith('```markdown'):
                                            cleaned = cleaned[len('```markdown'):].strip()
                                        elif cleaned.startswith('```md'):
                                            cleaned = cleaned[len('```md'):].strip()
                                        elif cleaned.startswith('```'):
                                            cleaned = cleaned[3:].strip()
                                        if cleaned.endswith('```'):
                                            cleaned = cleaned[:-3].strip()

                                        # Post-process: validate and clean highlight quality
                                        cleaned, density, final_count = _validate_highlight_quality(
                                            cleaned,
                                            log_fn=lambda msg, lvl: self.log_signal.emit(msg, lvl)
                                        )

                                        self.request_count += 1
                                        elapsed = time.time() - start_time

                                        highlighted_parts.append(cleaned)
                                        self.log_signal.emit(
                                            f"   ✅ Highlighted text saved ({len(cleaned)} chars, "
                                            f"{final_count} highlights, density={density:.1f}, {elapsed:.1f}s)",
                                            "success"
                                        )
                                        break
                                    else:
                                        self.log_signal.emit("   ⚠️ Response too short or empty, try again", "warning")
                                        continue

                                if self.should_stop:
                                    break

                                # Delay between requests
                                if batch_idx < len(batches):
                                    self.log_signal.emit(f"   ⏱️ Waiting {self.delay_seconds:.0f}s...", "info")
                                    time.sleep(self.delay_seconds)

                            except Exception as e:
                                self.log_signal.emit(f"   ❌ Batch failed: {e}", "error")
                                highlighted_parts.append(batch_text)  # Fallback to original
                                continue

                    # Combine all highlighted parts for this section
                    all_highlighted[section] = "\n\n".join(highlighted_parts)
                    self.log_signal.emit(f"   ✅ {section.upper()} highlighting complete: {len(all_highlighted[section])} chars", "success")

                except SkipPDFException:
                    self.log_signal.emit(f"⚠️ PDF {idx}/{total_pdfs} skipped by user", "warning")
                    continue

                # Step 5: Generate highlighted PDFs
                self.log_signal.emit("", "info")
                self.log_signal.emit("📄 Generating highlighted PDFs...", "info")

                try:
                    from highlight_pdf_generator import generate_highlighted_pdf
                    from folder_organizer import get_pdf_output_root, extract_full_subject_code

                    subject = extract_full_subject_code(pdf_stem)
                    pdf_output_root = get_pdf_output_root()

                    for section, highlighted_md in all_highlighted.items():
                        if not highlighted_md.strip():
                            continue

                        term = "Mids" if section == "mids" else "Finals"
                        out_name = f"{subject}_{term}_Highlighted-Handout_BY_VUEDU.pdf"
                        out_path = os.path.join(pdf_output_root, out_name)

                        self.log_signal.emit(f"   📝 Generating {term} PDF...", "info")
                        generated = generate_highlighted_pdf(
                            highlighted_markdown=highlighted_md,
                            output_path=out_path,
                            original_pdf_path=pdf_path,
                            page_range=page_ranges.get(section),
                            title=f"{subject} — {term} Highlighted Handout"
                        )
                        self.log_signal.emit(f"   ✅ Saved: {generated}", "success")

                    if not self.should_stop:
                        successful += 1
                        self.log_signal.emit(f"✅ PDF {idx}/{total_pdfs} complete", "success")
                    else:
                        self.log_signal.emit(f"⚠️ PDF {idx}/{total_pdfs} partially complete (Stopped)", "warning")

                except Exception as e:
                    self.log_signal.emit(f"❌ PDF generation failed: {e}", "error")
                    self.log_signal.emit(traceback.format_exc(), "error")
                    failed += 1
                    failed_pdfs.append(pdf_name)

                    if self.should_stop:
                        failed += 1
                        failed_pdfs.append(pdf_name)
                        break

                except Exception as e:
                    self.log_signal.emit(f"❌ Processing failed for {pdf_name}: {e}", "error")
                    self.log_signal.emit(traceback.format_exc(), "error")
                    failed += 1
                    failed_pdfs.append(pdf_name)
            self.log_signal.emit("", "info")
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit("🎉 HIGHLIGHTED HANDOUTS PROCESSING COMPLETE!", "success")
            self.log_signal.emit(f"   Total: {total_pdfs}, Success: {successful}, Failed: {failed}", "info")
            if failed_pdfs:
                for pdf in failed_pdfs:
                    self.log_signal.emit(f"   ❌ {pdf}", "error")
            self.log_signal.emit("=" * 60, "info")

            self.status_signal.emit("Highlighted handouts complete!")
            self.finished_signal.emit(True, f"Processed {total_pdfs} PDFs: {successful} success, {failed} failed")

        except Exception as e:
            self.log_signal.emit(f"❌ HIGHLIGHT ERROR: {str(e)}", "error")
            self.log_signal.emit(traceback.format_exc(), "error")
            self.status_signal.emit("Error occurred")
            self.finished_signal.emit(False, str(e))
