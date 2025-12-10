"""
Processing Thread Module
Background worker for PDF processing without blocking UI
"""

from PyQt5.QtCore import QThread, pyqtSignal
from pdf_processor import PDFProcessor
from gemini_client import GeminiClient
from json_manager import JSONManager
import traceback


class ProcessingThread(QThread):
    # Signals for UI updates
    log_signal = pyqtSignal(str, str)  # (message, level: info/success/warning/error)
    progress_signal = pyqtSignal(int, int)  # (current, total)
    status_signal = pyqtSignal(str)  # Current status message
    section_signal = pyqtSignal(str)  # Current section (Mids/Finals)
    batch_signal = pyqtSignal(int, int)  # (current_batch, total_batches)
    finished_signal = pyqtSignal(bool, str)  # (success, message)
    
    def __init__(self, pdf_path, output_dir='.', selected_sections=['mids', 'finals']):
        super().__init__()
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.selected_sections = selected_sections
        self.should_stop = False
        self.is_paused = False
        self.client = None
    
    def stop(self):
        """Request thread to stop"""
        self.should_stop = True
        self.log_signal.emit("⏸️  Stop requested by user...", "warning")
    
    def pause(self):
        """Request thread to pause"""
        self.is_paused = True
        if self.client:
            self.client.pause()
        self.log_signal.emit("⏸️  Pause requested by user...", "warning")
    
    def resume(self):
        """Resume thread from pause"""
        self.is_paused = False
        if self.client:
            self.client.resume()
        self.log_signal.emit("▶️  Resuming processing...", "info")
    
    def run(self):
        """Main processing logic"""
        try:
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit("🚀 Starting PDF MCQ Extraction Process", "info")
            self.log_signal.emit("=" * 60, "info")
            
            # Initialize components
            self.status_signal.emit("Initializing...")
            self.log_signal.emit(f"📄 PDF: {self.pdf_path}", "info")
            
            # Check Gemini server
            self.log_signal.emit("🔍 Checking Gemini server...", "info")
            self.client = GeminiClient()
            
            if not self.client.check_health():
                raise Exception("Gemini server is not running or not initialized. Please start the server with 'npm start'")
            
            self.log_signal.emit("✓ Gemini server is ready", "success")
            
            # Open PDF
            self.status_signal.emit("Opening PDF...")
            processor = PDFProcessor(self.pdf_path)
            pdf_name = processor.get_pdf_name()
            
            # Initialize JSON manager
            json_manager = JSONManager(pdf_name, self.output_dir, pdf_source_path=self.pdf_path, content_type='mcq')
            
            # Process selected sections only
            sections = self.selected_sections
            total_sections = len(sections)
            
            self.log_signal.emit(f"📋 Sections to process: {', '.join([s.upper() for s in sections])}", "info")
            
            for section_idx, section in enumerate(sections):
                if self.should_stop:
                    self.log_signal.emit("❌ Process stopped by user", "error")
                    self.finished_signal.emit(False, "Stopped by user")
                    return
                
                # Update section
                self.section_signal.emit(section.upper())
                section_info = processor.get_section_info(section)
                
                self.log_signal.emit("", "info")
                self.log_signal.emit(f"{'=' * 60}", "info")
                self.log_signal.emit(f"📚 Processing {section.upper()} Section", "info")
                self.log_signal.emit(f"   Pages: {section_info['page_range']}", "info")
                self.log_signal.emit(f"   Total batches: {section_info['total_batches']}", "info")
                self.log_signal.emit(f"{'=' * 60}", "info")
                
                # Get batches
                batches = processor.get_batches(section)
                total_batches = len(batches)
                
                # Process each batch
                for batch_idx, batch in enumerate(batches, start=1):
                    if self.should_stop:
                        self.log_signal.emit("❌ Process stopped by user", "error")
                        self.finished_signal.emit(False, "Stopped by user")
                        return
                    
                    # Check if paused - wait until resumed
                    while self.is_paused:
                        if self.should_stop:
                            self.log_signal.emit("❌ Process stopped by user", "error")
                            self.finished_signal.emit(False, "Stopped by user")
                            return
                        self.status_signal.emit("⏸️  Paused - waiting to resume...")
                        import time
                        time.sleep(1)
                    
                    # Update progress
                    self.batch_signal.emit(batch_idx, total_batches)
                    self.status_signal.emit(f"Processing {section} batch {batch_idx}/{total_batches}")
                    
                    self.log_signal.emit("", "info")
                    self.log_signal.emit(f"📦 Batch {batch_idx}/{total_batches} (Pages {batch['start_page']}-{batch['end_page']})", "info")
                    self.log_signal.emit(f"   Text length: {len(batch['text'])} characters", "info")
                    
                    # Generate MCQs with error handling - SKIP ON FAILURE
                    try:
                        import time
                        start_time = time.time()
                        
                        mcqs = self.client.generate_mcqs(
                            batch['text'],
                            section=section
                        )
                        
                        elapsed_time = time.time() - start_time
                        
                        # Add to JSON manager
                        json_manager.add_mcqs(mcqs, section)
                        
                        self.log_signal.emit(f"   ✓ Generated {len(mcqs)} MCQs in {elapsed_time:.1f}s", "success")
                        
                    except Exception as e:
                        # Skip this batch and continue - don't crash
                        error_msg = f"Failed to generate MCQs for batch {batch_idx}: {str(e)}"
                        self.log_signal.emit(f"   ❌ {error_msg}", "error")
                        self.log_signal.emit(f"   ⏭️  Skipping this batch and continuing...", "warning")
                        # Continue to next batch
                        continue
                
                # Save section
                self.status_signal.emit(f"Saving {section} MCQs...")
                self.log_signal.emit("", "info")
                self.log_signal.emit(f"💾 Saving {section.upper()} MCQs...", "info")
                
                saved_path = json_manager.save_section(section)
                if saved_path:
                    self.log_signal.emit(f"   ✓ Saved to: {saved_path}", "success")
            
            # Final summary
            processor.close()
            stats = json_manager.get_stats()
            
            self.log_signal.emit("", "info")
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit("🎉 PROCESS COMPLETED SUCCESSFULLY!", "success")
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit(f"📊 Summary:", "info")
            self.log_signal.emit(f"   PDF: {stats['pdf_name']}", "info")
            self.log_signal.emit(f"   Output folder: {stats['output_folder']}", "info")
            
            # Show only processed sections
            if 'mids' in self.selected_sections:
                self.log_signal.emit(f"   Mids MCQs: {stats['mids_count']}", "info")
            if 'finals' in self.selected_sections:
                self.log_signal.emit(f"   Finals MCQs: {stats['finals_count']}", "info")
            
            self.log_signal.emit(f"   Total MCQs: {stats['total_count']}", "info")
            self.log_signal.emit("=" * 60, "info")
            
            self.status_signal.emit("Completed!")
            self.finished_signal.emit(True, f"Successfully generated {stats['total_count']} MCQs")
            
        except Exception as e:
            error_msg = str(e)
            self.log_signal.emit("", "info")
            self.log_signal.emit("=" * 60, "error")
            self.log_signal.emit(f"❌ ERROR: {error_msg}", "error")
            self.log_signal.emit("=" * 60, "error")
            self.log_signal.emit("", "info")
            self.log_signal.emit("Stack trace:", "error")
            self.log_signal.emit(traceback.format_exc(), "error")
            
            self.status_signal.emit("Error occurred")
            self.finished_signal.emit(False, error_msg)


class BatchProcessingThread(QThread):
    """Process multiple PDFs sequentially with fresh Gemini chat for each"""
    
    # Signals for UI updates
    log_signal = pyqtSignal(str, str)  # (message, level)
    progress_signal = pyqtSignal(int, int)  # (current, total)
    status_signal = pyqtSignal(str)
    current_pdf_signal = pyqtSignal(str, int, int)  # (pdf_name, current, total)
    position_signal = pyqtSignal(str, int, str, str, int)  # (pdf_path, pdf_index, pdf_name, section, batch)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, pdf_paths, selected_sections=['mids', 'finals'],
                 start_pdf_index=1, start_mids_batch=1, start_finals_batch=1,
                 delay_seconds=12, dom_delay_seconds=1, pages_per_request=5, is_premium_model=False, content_type='mcq'):
        super().__init__()
        self.pdf_paths = pdf_paths
        self.selected_sections = selected_sections
        self.start_pdf_index = start_pdf_index
        self.start_mids_batch = start_mids_batch
        self.start_finals_batch = start_finals_batch
        self.delay_seconds = delay_seconds
        self.dom_delay_seconds = dom_delay_seconds
        self.pages_per_request = pages_per_request
        self.is_premium_model = is_premium_model
        self.content_type = content_type  # 'mcq' or 'short_notes'
        
        # Use user-specified delay for both Premium and Fast models
        self.delay_between_requests = float(delay_seconds)
        
        self.should_stop = False
        self.is_paused = False
        self.client = None
        self.current_json_manager = None  # Track for auto-save
        self.request_count = 0  # Track total requests made for auto chat reset
    
    def stop(self):
        """Request thread to stop and auto-save current progress"""
        self.should_stop = True
        
        # Auto-save current JSON if available
        if self.current_json_manager:
            self.log_signal.emit("💾 Auto-saving progress before stopping...", "info")
            try:
                # Save both sections if they have data
                for section in ['mids', 'finals']:
                    if section == 'mids' and len(self.current_json_manager.mids_mcqs) > 0:
                        saved_path = self.current_json_manager.save_section(section)
                        if saved_path:
                            self.log_signal.emit(f"   ✓ Auto-saved {section}: {saved_path}", "success")
                    elif section == 'finals' and len(self.current_json_manager.finals_mcqs) > 0:
                        saved_path = self.current_json_manager.save_section(section)
                        if saved_path:
                            self.log_signal.emit(f"   ✓ Auto-saved {section}: {saved_path}", "success")
            except Exception as e:
                self.log_signal.emit(f"   ⚠️ Auto-save failed: {str(e)}", "warning")
    
    def pause(self):
        """Request thread to pause"""
        self.is_paused = True
        if self.client:
            self.client.pause()
        self.log_signal.emit("⏸️  Pause requested by user...", "warning")
    
    def resume(self):
        """Resume thread from pause"""
        self.is_paused = False
        if self.client:
            self.client.resume()
        self.log_signal.emit("▶️  Resuming processing...", "info")
    
    def run(self):
        """Process all PDFs sequentially"""
        import os
        
        total_pdfs = len(self.pdf_paths)
        successful = 0
        failed = 0
        failed_pdfs = []
        
        try:
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit(f"🚀 Batch Processing: {total_pdfs} PDF(s)", "info")
            self.log_signal.emit("=" * 60, "info")
            
            # Initialize Gemini client once
            self.client = GeminiClient()
            
            if not self.client.check_health():
                raise Exception("Gemini server is not running or not initialized")
            
            for idx, pdf_path in enumerate(self.pdf_paths, 1):
                if self.should_stop:
                    self.log_signal.emit("❌ Batch processing stopped by user", "error")
                    break
                
                # Skip PDFs before start index
                if idx < self.start_pdf_index:
                    self.log_signal.emit(f"⏭️  Skipping PDF {idx}/{total_pdfs} (resuming from {self.start_pdf_index})", "info")
                    continue
                
                pdf_name = os.path.basename(pdf_path)
                self.current_pdf_signal.emit(pdf_name, idx, total_pdfs)
                
                self.log_signal.emit("", "info")
                self.log_signal.emit("=" * 60, "info")
                self.log_signal.emit(f"📄 Processing PDF {idx}/{total_pdfs}: {pdf_name}", "info")
                self.log_signal.emit("=" * 60, "info")
                
                # Reset Gemini chat for fresh start
                self.log_signal.emit("🔄 Starting fresh Gemini chat...", "info")
                if not self.client.reset_chat():
                    self.log_signal.emit("⚠️  Failed to reset chat, continuing anyway...", "warning")
                
                # Reset request counter for new PDF
                self.request_count = 0
                self.log_signal.emit("🔄 Request counter reset for new PDF", "info")
                
                # Process this PDF using ProcessingThread logic
                try:
                    processor = PDFProcessor(pdf_path)
                    pdf_basename = processor.get_pdf_name()
                    
                    # Get output directory from PDF location
                    output_dir = os.path.dirname(pdf_path)
                    
                    # Initialize JSON manager with organized folder structure
                    json_manager = JSONManager(pdf_basename, output_dir, pdf_source_path=pdf_path, content_type=self.content_type)
                    self.current_json_manager = json_manager  # Track for auto-save
                    
                    # Process selected sections
                    for section in self.selected_sections:
                        if self.should_stop:
                            break
                        
                        section_info = processor.get_section_info(section)
                        self.log_signal.emit(f"📚 Processing {section.upper()} Section", "info")
                        self.log_signal.emit(f"   Pages: {section_info['page_range']}", "info")
                        self.log_signal.emit(f"   Total batches: {section_info['total_batches']}", "info")
                        
                        batches = processor.get_batches(section, self.pages_per_request)
                        
                        # Determine start batch for this section
                        start_batch = 1
                        if idx == self.start_pdf_index:
                            # Only apply batch skip on the resume PDF
                            if section == 'mids':
                                start_batch = self.start_mids_batch
                            elif section == 'finals':
                                start_batch = self.start_finals_batch
                        
                        for batch_idx, batch in enumerate(batches, start=1):
                            if self.should_stop:
                                break
                            
                            # Skip batches before start index
                            if batch_idx < start_batch:
                                self.log_signal.emit(f"⏭️  Skipping {section} batch {batch_idx}/{len(batches)}", "info")
                                continue
                            
                            # Check if paused - wait until resumed
                            while self.is_paused:
                                if self.should_stop:
                                    break
                                self.status_signal.emit("⏸️  Paused - waiting to resume...")
                                import time
                                time.sleep(1)
                            
                            # Emit position update with full PDF path and name
                            pdf_name = os.path.basename(pdf_path)
                            self.position_signal.emit(pdf_path, idx, pdf_name, section, batch_idx)
                            
                            self.status_signal.emit(f"PDF {idx}/{total_pdfs}: {section} batch {batch_idx}/{len(batches)}")
                            self.log_signal.emit(f"📦 Batch {batch_idx}/{len(batches)} (Pages {batch['start_page']}-{batch['end_page']}, {batch['page_count']} pages)", "info")
                            
                            try:
                                import time
                                start_time = time.time()
                                
                                # Auto-reset chat based on request count
                                # Premium: every 10 requests, Fast: every 20 requests
                                reset_threshold = 10 if self.is_premium_model else 20
                                
                                if self.request_count > 0 and self.request_count % reset_threshold == 0:
                                    self.log_signal.emit(f"🔄 Auto-resetting chat after {self.request_count} requests ({reset_threshold} request limit)...", "info")
                                    if not self.client.reset_chat():
                                        self.log_signal.emit("⚠️  Failed to reset chat, continuing anyway...", "warning")
                                    else:
                                        self.log_signal.emit("✓ Chat reset successful", "success")
                                
                                # Pass page count for dynamic MCQ calculation and content type
                                mcqs = self.client.generate_mcqs(
                                    batch['text'], 
                                    section=section,
                                    pages_count=batch['page_count'],
                                    content_type=self.content_type,
                                    dom_delay_seconds=self.dom_delay_seconds
                                )
                                
                                # Log when JSON is returned
                                self.log_signal.emit("   📥 JSON return triggered from Gemini script", "info")
                                
                                json_manager.add_mcqs(mcqs, section)
                                
                                # Increment request counter after successful request
                                self.request_count += 1
                                
                                elapsed_time = time.time() - start_time
                                self.log_signal.emit(f"   ✓ Generated {len(mcqs)} MCQs in {elapsed_time:.1f}s (Total requests: {self.request_count})", "success")
                                
                                # Apply delay between requests (except for last batch)
                                if batch_idx < len(batches):
                                    self.log_signal.emit(f"   ⏱️  Waiting {self.delay_between_requests:.1f}s before next request...", "info")
                                    time.sleep(self.delay_between_requests)
                                    
                            except Exception as e:
                                self.log_signal.emit(f"   ❌ Failed: {str(e)}", "error")
                                self.log_signal.emit(f"   ⏭️  Skipping batch...", "warning")
                                continue
                        
                        # Save section
                        saved_path = json_manager.save_section(section)
                        if saved_path:
                            self.log_signal.emit(f"   ✓ Saved to: {saved_path}", "success")
                    
                    processor.close()
                    successful += 1
                    self.log_signal.emit(f"✅ PDF {idx}/{total_pdfs} completed successfully", "success")
                    
                except Exception as e:
                    failed += 1
                    failed_pdfs.append(pdf_name)
                    self.log_signal.emit(f"❌ PDF {idx}/{total_pdfs} failed: {str(e)}", "error")
            
            # Final summary
            self.log_signal.emit("", "info")
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit("🎉 BATCH PROCESSING COMPLETE!", "success")
            self.log_signal.emit("=" * 60, "info")
            self.log_signal.emit(f"📊 Summary:", "info")
            self.log_signal.emit(f"   Total PDFs: {total_pdfs}", "info")
            self.log_signal.emit(f"   Successful: {successful}", "success")
            self.log_signal.emit(f"   Failed: {failed}", "error" if failed > 0 else "info")
            
            if failed_pdfs:
                self.log_signal.emit(f"   Failed PDFs:", "error")
                for pdf in failed_pdfs:
                    self.log_signal.emit(f"     • {pdf}", "error")
            
            self.log_signal.emit("=" * 60, "info")
            
            self.status_signal.emit("Batch completed!")
            self.finished_signal.emit(True, f"Processed {total_pdfs} PDFs: {successful} successful, {failed} failed")
            
        except Exception as e:
            error_msg = str(e)
            self.log_signal.emit("", "info")
            self.log_signal.emit("=" * 60, "error")
            self.log_signal.emit(f"❌ BATCH ERROR: {error_msg}", "error")
            self.log_signal.emit("=" * 60, "error")
            self.log_signal.emit(traceback.format_exc(), "error")
            
            self.status_signal.emit("Batch error occurred")
            self.finished_signal.emit(False, error_msg)
