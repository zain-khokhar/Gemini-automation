"""
PDF Processing Module
Handles PDF text extraction and Mids/Finals splitting logic
"""

import fitz  # PyMuPDF
import json
import math
from pathlib import Path


class PDFProcessor:
    def __init__(self, pdf_path, config_path='config.json'):
        """
        Initialize PDF processor
        
        Args:
            pdf_path: Path to the PDF file
            config_path: Path to configuration file
        """
        self.pdf_path = Path(pdf_path)
        self.pdf_name = self.pdf_path.stem
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.pages_per_batch = self.config['pages_per_batch']
        self.mids_percentage = self.config['mids_percentage']
        
        # Open PDF
        try:
            self.doc = fitz.open(str(self.pdf_path))
            self.total_pages = len(self.doc)
        except Exception as e:
            raise Exception(f"Failed to open PDF: {str(e)}")
        
        # Calculate split point
        self.mids_pages = self._calculate_mids_pages()
        
        print(f"📄 PDF: {self.pdf_name}")
        print(f"   Total pages: {self.total_pages}")
        print(f"   Mids pages: 1-{self.mids_pages} ({self.mids_pages} pages)")
        print(f"   Finals pages: {self.mids_pages + 1}-{self.total_pages} ({self.total_pages - self.mids_pages} pages)")
    
    def _calculate_mids_pages(self):
        """
        Calculate number of pages for Mids section
        Formula: (total_pages / 2) × mids_percentage
        Example: 260 pages → half = 130 → 130 × 95% = 123.5 ≈ 123 pages for Mids
        
        mids_percentage in config should be 95 for "half minus 5%"
        """
        half_pages = self.total_pages / 2
        mids_pages = math.floor(half_pages * (self.mids_percentage / 100))
        return max(1, mids_pages)  # At least 1 page
    
    def get_page_count(self):
        """Get total page count"""
        return self.total_pages
    
    def get_pdf_name(self):
        """Get PDF filename without extension"""
        return self.pdf_name
    
    def extract_text_from_page(self, page_num):
        """
        Extract text from a single page
        
        Args:
            page_num: Page number (0-indexed)
        
        Returns:
            Extracted text string
        """
        try:
            page = self.doc[page_num]
            text = page.get_text()
            return self._clean_text(text)
        except Exception as e:
            print(f"⚠️  Error extracting page {page_num + 1}: {str(e)}")
            return ""
    
    def _clean_text(self, text):
        """
        Clean extracted text
        - Remove excessive whitespace
        - Remove special characters that might break JSON
        """
        # Replace multiple newlines with double newline
        text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
        
        # Remove excessive spaces
        import re
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def get_batches(self, section='mids', pages_per_batch=None):
        """
        Get page batches for a section
        
        Args:
            section: 'mids' or 'finals'
            pages_per_batch: Number of pages per batch (default: use config value)
        
        Returns:
            List of tuples: [(batch_num, start_page, end_page, text), ...]
        """
        # Use provided pages_per_batch or fall back to config
        batch_size = pages_per_batch if pages_per_batch is not None else self.pages_per_batch
        
        if section == 'mids':
            start_page = 0
            end_page = self.mids_pages - 1
        elif section == 'finals':
            start_page = self.mids_pages
            end_page = self.total_pages - 1
        else:
            raise ValueError("Section must be 'mids' or 'finals'")
        
        batches = []
        current_page = start_page
        batch_num = 1
        
        while current_page <= end_page:
            # Calculate remaining pages in section
            remaining_pages = end_page - current_page + 1
            
            # Use minimum of batch_size and remaining pages (edge case handling)
            actual_batch_size = min(batch_size, remaining_pages)
            batch_end = current_page + actual_batch_size - 1
            
            # Extract text from all pages in this batch
            batch_text = []
            for page_num in range(current_page, batch_end + 1):
                page_text = self.extract_text_from_page(page_num)
                if page_text:
                    batch_text.append(f"--- Page {page_num + 1} ---\n{page_text}")
            
            combined_text = '\n\n'.join(batch_text)
            
            batches.append({
                'batch_num': batch_num,
                'start_page': current_page + 1,  # 1-indexed for display
                'end_page': batch_end + 1,       # 1-indexed for display
                'text': combined_text,
                'page_count': batch_end - current_page + 1
            })
            
            current_page = batch_end + 1
            batch_num += 1
        
        return batches

    
    def get_section_info(self, section='mids'):
        """
        Get information about a section
        
        Returns:
            Dictionary with section details
        """
        batches = self.get_batches(section)
        
        if section == 'mids':
            page_range = f"1-{self.mids_pages}"
            total_pages = self.mids_pages
        else:
            page_range = f"{self.mids_pages + 1}-{self.total_pages}"
            total_pages = self.total_pages - self.mids_pages
        
        return {
            'section': section,
            'page_range': page_range,
            'total_pages': total_pages,
            'total_batches': len(batches),
            'pages_per_batch': self.pages_per_batch
        }
    
    def close(self):
        """Close the PDF document"""
        if self.doc:
            self.doc.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == '__main__':
    # Test the processor
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_processor.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    with PDFProcessor(pdf_path) as processor:
        print("\n=== MIDS SECTION ===")
        mids_info = processor.get_section_info('mids')
        print(f"Pages: {mids_info['page_range']}")
        print(f"Total batches: {mids_info['total_batches']}")
        
        print("\n=== FINALS SECTION ===")
        finals_info = processor.get_section_info('finals')
        print(f"Pages: {finals_info['page_range']}")
        print(f"Total batches: {finals_info['total_batches']}")
        
        print("\n=== SAMPLE BATCH (Mids, Batch 1) ===")
        batches = processor.get_batches('mids')
        if batches:
            sample = batches[0]
            print(f"Pages {sample['start_page']}-{sample['end_page']}")
            print(f"Text length: {len(sample['text'])} characters")
            print(f"Preview: {sample['text'][:200]}...")
