"""
Processing Thread Module
Background worker for PDF processing with MANUAL response extraction flow.

Flow:
1. Send prompt to Gemini (automated)
2. Wait for user to manually extract/paste JSON response
3. Process and save the JSON
4. Move to next batch
"""

from PyQt5.QtCore import QThread, pyqtSignal
from pdf_processor import PDFProcessor
from gemini_client import GeminiClient
from json_manager import JSONManager
import traceback
import threading
import time
import os

class SkipPDFException(Exception):
    pass


class ProcessingThread(QThread):
    """Single PDF processor (kept for backward compatibility)"""
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    status_signal = pyqtSignal(str)
    section_signal = pyqtSignal(str)
    batch_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, pdf_path, output_dir='.', selected_sections=['mids', 'finals']):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.selected_sections = selected_sections
        self.should_stop = False
    
    def stop(self):
        self.should_stop = True

    def run(self):
        self.finished_signal.emit(False, "Single PDF mode not supported in manual flow. Use batch processing.")


class BatchProcessingThread(QThread):
    """Process multiple PDFs with manual response extraction flow"""
    
    # Standard signals
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    status_signal = pyqtSignal(str)
    current_pdf_signal = pyqtSignal(str, int, int)
    position_signal = pyqtSignal(str, int, str, str, int)
    finished_signal = pyqtSignal(bool, str)
    
    # NEW: Signal to tell UI we're waiting for manual input
    # Args: (pdf_name, section, batch_idx, total_batches, content_type_label)
    awaiting_input_signal = pyqtSignal(str, str, int, int, str)
    
    # NEW: Signal when JSON is invalid
    json_invalid_signal = pyqtSignal(str)
    
    def __init__(self, pdf_paths, selected_sections=['mids', 'finals'],
                 start_pdf_index=1, start_mids_batch=1, start_finals_batch=1,
                 delay_seconds=1, pages_per_request=10,
                 is_premium_model=False, content_types=None, chat_reset_threshold=5,
                 **kwargs):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.selected_sections = selected_sections
        self.start_pdf_index = start_pdf_index
        self.start_mids_batch = start_mids_batch
        self.start_finals_batch = start_finals_batch
        self.delay_seconds = delay_seconds
        self.pages_per_request = pages_per_request
        self.is_premium_model = is_premium_model
        self.content_types = content_types if content_types else ['mcq']
        self.chat_reset_threshold = chat_reset_threshold
        self.delay_between_requests = float(delay_seconds)
        
        self.should_stop = False
        self.is_paused = False
        self.client = None
        self.current_json_manager = None
        self.request_count = 0
        
        # Current batch data for repeat functionality
        self._current_batch_text = None
        self._current_batch_section = None
        self._current_batch_content_type = None
        self._current_batch_review_topics = []
        
        # Reviews context flags
        self.use_reviews_for_mcq = False
        self.use_reviews_for_notes = False
        
        # Reviews category to use (matches selected section: 'mids', 'finals', or custom)
        self.review_category = 'uncategorized'
        
        # Manual input synchronization
        self._input_event = threading.Event()
        self._skip_event = threading.Event()
        self._skip_pdf_event = threading.Event()
        self._repeat_event = threading.Event()
        self._input_json = None  # Stores the JSON text submitted by user
        self._input_source = None  # 'extract' or 'manual'
    
    def skip_current_batch(self):
        """Skip the current batch when stuck on invalid JSON"""
        self._skip_event.set()
        self._input_event.set()  # Unblock wait

    def skip_current_pdf(self):
        """Skip the entire current PDF."""
        self._skip_pdf_event.set()
        self._input_event.set()

    def repeat_current_batch(self):
        """Repeat the current batch by re-sending the same prompt to Gemini"""
        self._repeat_event.set()
        self._input_event.set()  # Unblock wait
        
    def stop(self):
        """Stop processing and auto-save"""
        self.should_stop = True
        self._input_event.set()  # Unblock any waiting
        
        if self.current_json_manager:
            self.log_signal.emit("💾 Auto-saving progress...", "info")
            try:
                for section in ['mids', 'finals']:
                    mcqs = getattr(self.current_json_manager, f'{section}_mcqs', [])
                    if len(mcqs) > 0:
                        saved = self.current_json_manager.save_section(section)
                        if saved:
                            self.log_signal.emit(f"   ✓ Saved {section}: {saved}", "success")
            except Exception as e:
                self.log_signal.emit(f"   ⚠️ Auto-save failed: {str(e)}", "warning")
    
    def pause(self):
        self.is_paused = True
        if self.client:
            self.client.pause()
    
    def resume(self):
        self.is_paused = False
        if self.client:
            self.client.resume()
    
    def submit_json(self, json_text, source='manual'):
        """
        Called by UI when user submits JSON (either via extract button or manual paste).
        
        Args:
            json_text: Raw JSON text string
            source: 'extract' or 'manual'
        """
        self._input_json = json_text
        self._input_source = source
        self._input_event.set()
    
    def _wait_for_user_input(self, pdf_name, section, batch_idx, total_batches, content_type_label):
        """
        Block until user submits JSON via extract button or manual paste.
        
        Returns:
            Raw JSON text string, or None if stopped/skipped
            Special: returns '__REPEAT__' if user requested repeat
        """
        self._input_event.clear()
        self._skip_event.clear()
        self._skip_pdf_event.clear()
        self._repeat_event.clear()
        self._input_json = None
        self._input_source = None
        
        # Signal UI to show waiting state
        self.awaiting_input_signal.emit(pdf_name, section, batch_idx, total_batches, content_type_label)
        self.status_signal.emit(f"⏳ Waiting for response — PDF {pdf_name}, {section} batch {batch_idx}/{total_batches}")
        
        # Block until user submits or stop/skip is requested
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
        self.log_signal.emit(f"   📥 JSON received via {source_label} ({len(self._input_json or '')} chars)", "info")
        return self._input_json
    
    def run(self):
        """Process all PDFs with manual extraction flow"""
        total_pdfs = len(self.pdf_paths)
        successful = 0
        failed = 0
        failed_pdfs = []
        
        try:
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit(f"🚀 Batch Processing: {total_pdfs} PDF(s) [Manual Mode]", "info")
            self.log_signal.emit("=" * 60, "info")
            
            # Initialize Gemini client
            self.client = GeminiClient()
            if not self.client.check_health():
                raise Exception("Gemini server is not running or not initialized")
            
            for idx, pdf_path in enumerate(self.pdf_paths, 1):
                self._skip_pdf_event.clear()
                if self.should_stop:
                    self.log_signal.emit("⏹ Stopped by user", "error")
                    break
                
                # Skip PDFs before start index
                if idx < self.start_pdf_index:
                    self.log_signal.emit(f"⏭️ Skipping PDF {idx}/{total_pdfs}", "info")
                    continue
                
                pdf_name = os.path.basename(pdf_path)
                self.current_pdf_signal.emit(pdf_name, idx, total_pdfs)
                

                self.log_signal.emit("", "info")
                self.log_signal.emit("=" * 60, "info")
                self.log_signal.emit(f"📄 PDF {idx}/{total_pdfs}: {pdf_name}", "info")
                self.log_signal.emit("=" * 60, "info")
                
                # Reset chat for fresh start
                self.log_signal.emit("🔄 Resetting Gemini chat...", "info")
                if not self.client.reset_chat():
                    self.log_signal.emit("⚠️ Chat reset failed, continuing...", "warning")
                
                self.request_count = 0
                
                try:
                    processor = PDFProcessor(pdf_path)
                    pdf_basename = processor.get_pdf_name()
                    output_dir = os.path.dirname(pdf_path)
                    
                    for content_type in self.content_types:
                        if self.should_stop:
                            break
                        
                        content_label = "MCQs" if content_type == 'mcq' else "Short Notes"
                        self.log_signal.emit(f"📝 Processing {content_label} for {pdf_name}", "info")
                        
                        # Reset chat for new content type
                        if not self.client.reset_chat():
                            self.log_signal.emit("⚠️ Chat reset failed, continuing...", "warning")
                        self.request_count = 0
                        
                        json_manager = JSONManager(pdf_basename, output_dir, pdf_source_path=pdf_path, content_type=content_type)
                        self.current_json_manager = json_manager
                        
                        # Extract subject prefix for subject-aware prompt injection
                        from folder_organizer import extract_subject_code
                        subject_prefix = extract_subject_code(pdf_basename) or ''
                        
                        for section in self.selected_sections:
                            if self.should_stop:
                                break
                            
                            section_info = processor.get_section_info(section)
                            self.log_signal.emit(f"📚 {section.upper()} ({content_label}): Pages {section_info['page_range']}, {section_info['total_batches']} batches", "info")
                            
                            batches = processor.get_batches(section, self.pages_per_request)
                            
                            # Determine start batch
                            start_batch = 1
                            if idx == self.start_pdf_index and content_type == self.content_types[0]:
                                if section == 'mids':
                                    start_batch = self.start_mids_batch
                                elif section == 'finals':
                                    start_batch = self.start_finals_batch
                            
                            for batch_idx, batch in enumerate(batches, start=1):
                                if self.should_stop:
                                    break
                                
                                # Skip batches before start
                                if batch_idx < start_batch:
                                    self.log_signal.emit(f"⏭️ Skipping {section} batch {batch_idx}/{len(batches)}", "info")
                                    continue
                                
                                # Wait while paused
                                while self.is_paused:
                                    if self.should_stop:
                                        break
                                    self.status_signal.emit("⏸️ Paused")
                                    time.sleep(1)
                                
                                # Emit position
                                self.position_signal.emit(pdf_path, idx, pdf_name, section, batch_idx)
                                

                                
                                self.log_signal.emit("", "info")
                                self.log_signal.emit(f"📦 Batch {batch_idx}/{len(batches)} (Pages {batch['start_page']}-{batch['end_page']}, {batch['page_count']} pages)", "info")
                                
                                try:
                                    start_time = time.time()
                                    
                                    # Auto-reset chat if needed
                                    if self.request_count > 0 and self.request_count % self.chat_reset_threshold == 0:
                                        self.log_signal.emit(f"🔄 Auto-reset after {self.request_count} requests...", "info")
                                        self.client.reset_chat()
                                    
                                    # Step 1: Build prompt text with review topics sent separately
                                    # Reviews are extracted as raw topic lists and passed to the server
                                    # via the review_topics parameter. The server embeds them DIRECTLY
                                    # into the system prompt so the model MUST read and analyze them.
                                    #
                                    # Logic:
                                    #   - mids section  → mids reviews  (reviews_mids.json)
                                    #   - finals section → finals reviews (reviews_finals.json)
                                    prompt_text = batch['text']
                                    review_topics_list = []
                                    
                                    # Determine if reviews should be fetched based on UI checkbox flags
                                    should_use_reviews = (
                                        (content_type == 'mcq' and self.use_reviews_for_mcq) or
                                        (content_type == 'short_notes' and self.use_reviews_for_notes)
                                    )
                                    
                                    if should_use_reviews:
                                        try:
                                            from reviews_manager import get_raw_review_topics
                                            from folder_organizer import extract_full_subject_code
                                            subj = extract_full_subject_code(pdf_basename)
                                            if subj and subj != 'MISC':
                                                # Auto-select review category to match the section being processed
                                                review_cat = section  # 'mids' or 'finals'
                                                review_topics_list = get_raw_review_topics(subj, category=review_cat)
                                                if review_topics_list:
                                                    content_label_log = "MCQ" if content_type == 'mcq' else "notes"
                                                    self.log_signal.emit(f"   📝 [{review_cat.upper()}] {len(review_topics_list)} review topics will be embedded in system prompt for {subj} ({content_label_log})", "info")
                                                else:
                                                    self.log_signal.emit(f"   ℹ️ No {section} reviews found for {subj} — proceeding without reviews", "info")
                                        except Exception as e:
                                            self.log_signal.emit(f"   ⚠️ Reviews extraction failed: {str(e)}", "warning")

                                    self.log_signal.emit("   📤 Sending to Gemini...", "info")
                                    
                                    # Check if PDF was skipped
                                    if self._skip_pdf_event.is_set():
                                        raise SkipPDFException()

                                    # Store current batch data for repeat
                                    self._current_batch_text = prompt_text
                                    self._current_batch_section = section
                                    self._current_batch_content_type = content_type
                                    self._current_batch_review_topics = review_topics_list
                                    
                                    self.client.send_prompt(
                                        prompt_text,
                                        section=section,
                                        pages_count=batch['page_count'],
                                        content_type=content_type,
                                        review_topics=review_topics_list,
                                        subject_prefix=subject_prefix
                                    )
                                    self.log_signal.emit("   ✓ Prompt sent — waiting for your input", "success")
                                    
                                    # Step 2: Retry loop for JSON fixing
                                    import json_fixer
                                    
                                    # We loop until user provides valid JSON or skips/stops
                                    while True:
                                        raw_json = self._wait_for_user_input(
                                            pdf_name, section, batch_idx, len(batches), content_label
                                        )
                                        
                                        if raw_json is None:
                                            # User stopped or skipped
                                            if self._skip_event.is_set():
                                                self.log_signal.emit("   ⏭️ Batch skipped by user", "warning")
                                            break
                                        
                                        # Handle repeat request
                                        if raw_json == '__SKIP_PDF__':
                                            self.log_signal.emit("⚠️ Skipping entire PDF as requested.", "warning")
                                            raise SkipPDFException()

                                        if raw_json == '__REPEAT__':
                                            self.log_signal.emit("   🔄 Repeating batch — re-sending prompt...", "info")
                                            if self._current_batch_text:
                                                try:
                                                    self.client.send_prompt(
                                                        self._current_batch_text,
                                                        section=self._current_batch_section or section,
                                                        pages_count=batch['page_count'],
                                                        content_type=self._current_batch_content_type or content_type,
                                                        review_topics=self._current_batch_review_topics,
                                                        subject_prefix=subject_prefix
                                                    )
                                                    self.log_signal.emit("   ✓ Prompt re-sent — waiting for your input", "success")
                                                except Exception as e:
                                                    self.log_signal.emit(f"   ❌ Repeat failed: {str(e)}", "error")
                                            continue
                                            
                                        # Step 3: Parse and validate JSON
                                        try:
                                            mcqs = json_fixer.fix_json(raw_json, content_type)
                                            
                                            if isinstance(mcqs, list) and len(mcqs) > 0:
                                                # Step 4: Add to JSON manager
                                                json_manager.add_mcqs(mcqs, section)
                                                self.request_count += 1
                                                
                                                elapsed = time.time() - start_time
                                                item_label = "MCQs" if content_type == 'mcq' else "notes"
                                                self.log_signal.emit(f"   ✅ {len(mcqs)} {item_label} saved ({elapsed:.1f}s)", "success")
                                                break  # Success! Exit retry loop
                                        except Exception as e:
                                            self.log_signal.emit(f"   ⚠️ JSON still invalid: {str(e)}", "warning")
                                        
                                        # If we reach here, JSON was invalid or empty
                                        self.log_signal.emit("   🔄 Sending broken JSON back to Gemini for fixing...", "info")
                                        
                                        # Inform UI that JSON is invalid
                                        self.json_invalid_signal.emit(raw_json)
                                        
                                        # Ask Gemini to fix it
                                        try:
                                            self.client.send_fix_json(raw_json)
                                        except Exception as e:
                                            self.log_signal.emit(f"   ❌ Failed to send fix request: {str(e)}", "error")
                                            
                                    # If user skipped or stopped, continue to next batch / stop
                                    if self.should_stop:
                                        break
                                        
                                    # Delay between requests
                                    if batch_idx < len(batches):
                                        self.log_signal.emit(f"   ⏱️ Waiting {self.delay_between_requests:.0f}s...", "info")
                                        time.sleep(self.delay_between_requests)
                                    
                                except Exception as e:
                                    self.log_signal.emit(f"   ❌ Batch failed: {str(e)}", "error")
                                    self.log_signal.emit(f"   ⏭️ Skipping...", "warning")
                                    continue
                            
                            # Save section
                            saved_path = json_manager.save_section(section)
                            if saved_path:
                                self.log_signal.emit(f"   💾 Saved: {saved_path}", "success")
                        
                        self.log_signal.emit(f"✅ {content_label} done for {pdf_name}", "success")
                    
                    processor.close()
                    successful += 1
                    self.log_signal.emit(f"✅ PDF {idx}/{total_pdfs} complete", "success")
                    

                except SkipPDFException:
                    self.log_signal.emit(f"⚠️ PDF {idx}/{total_pdfs} skipped by user", "warning")
                    
                except Exception as e:
                    failed += 1
                    failed_pdfs.append(pdf_name)
                    self.log_signal.emit(f"❌ PDF {idx}/{total_pdfs} failed: {str(e)}", "error")
                    

            
            # Summary
            self.log_signal.emit("", "info")
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit("🎉 BATCH PROCESSING COMPLETE!", "success")
            self.log_signal.emit(f"   Total: {total_pdfs}, Success: {successful}, Failed: {failed}", "info")
            if failed_pdfs:
                for pdf in failed_pdfs:
                    self.log_signal.emit(f"   ❌ {pdf}", "error")
            self.log_signal.emit("=" * 60, "info")
            
            self.status_signal.emit("Batch completed!")
            self.finished_signal.emit(True, f"Processed {total_pdfs} PDFs: {successful} success, {failed} failed")
            
        except Exception as e:
            self.log_signal.emit(f"❌ BATCH ERROR: {str(e)}", "error")
            self.log_signal.emit(traceback.format_exc(), "error")
            self.status_signal.emit("Error occurred")
            self.finished_signal.emit(False, str(e))
