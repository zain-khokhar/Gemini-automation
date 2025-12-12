"""
JSON Manager Module
Handles JSON file creation, validation, and saving
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from folder_organizer import get_organized_path


class JSONManager:
    def __init__(self, pdf_name: str, output_base_dir: str = '.', pdf_source_path: str = None, content_type: str = 'mcq'):
        """
        Initialize JSON manager
        
        Args:
            pdf_name: Name of the PDF (without extension)
            output_base_dir: Base directory for output (deprecated, kept for compatibility)
            pdf_source_path: Full path to the source PDF file (for organized folder structure)
            content_type: Type of content - 'mcq' or 'short_notes'
        """
        self.pdf_name = pdf_name
        self.content_type = content_type
        
        # Use organized folder structure if pdf_source_path is provided
        if pdf_source_path:
            self.output_folder = get_organized_path(pdf_name, pdf_source_path)
        else:
            # Fallback to old behavior for backward compatibility
            self.output_base_dir = Path(output_base_dir)
            self.output_folder = self.output_base_dir / f"{pdf_name}_JSON"
        
        # Create output folder
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # File paths - different naming based on content type
        if content_type == 'short_notes':
            # Short notes: "short note {pdf_name}_{section}.json"
            self.mids_file = self.output_folder / f"short note {pdf_name}_mids.json"
            self.finals_file = self.output_folder / f"short note {pdf_name}_finals.json"
        else:
            # MCQs: "{pdf_name}_{section}_mcqs.json"
            self.mids_file = self.output_folder / f"{pdf_name}_mids_mcqs.json"
            self.finals_file = self.output_folder / f"{pdf_name}_finals_mcqs.json"
        
        # MCQ storage
        self.mids_mcqs = []
        self.finals_mcqs = []
        
        print(f"📁 Output folder: {self.output_folder}")
    
    def add_mcqs(self, mcqs: List[Dict[str, Any]], section: str):
        """
        Add MCQs to the appropriate section
        
        Args:
            mcqs: List of MCQ dictionaries
            section: 'mids' or 'finals'
        """
        if section == 'mids':
            self.mids_mcqs.extend(mcqs)
        elif section == 'finals':
            self.finals_mcqs.extend(mcqs)
        else:
            raise ValueError("Section must be 'mids' or 'finals'")
    
    def _reassign_ids(self, mcqs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reassign sequential IDs to MCQs
        
        Args:
            mcqs: List of MCQ dictionaries
        
        Returns:
            List of MCQs with reassigned IDs
        """
        for i, mcq in enumerate(mcqs, start=1):
            mcq['id'] = i
        return mcqs
    
    def save_section(self, section: str) -> str:
        """
        Save MCQs for a section to JSON file
        
        Args:
            section: 'mids' or 'finals'
        
        Returns:
            Path to saved file
        """
        if section == 'mids':
            mcqs = self.mids_mcqs
            file_path = self.mids_file
        elif section == 'finals':
            mcqs = self.finals_mcqs
            file_path = self.finals_file
        else:
            raise ValueError("Section must be 'mids' or 'finals'")
        
        if not mcqs:
            print(f"⚠️  No MCQs to save for {section}")
            return None
        
        # Reassign IDs sequentially
        mcqs = self._reassign_ids(mcqs)
        
        # Save to file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(mcqs, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Saved {len(mcqs)} MCQs to {file_path.name}")
            return str(file_path)
        
        except Exception as e:
            raise Exception(f"Failed to save {section} MCQs: {str(e)}")
    
    def save_all(self) -> Dict[str, str]:
        """
        Save all MCQs to their respective files
        
        Returns:
            Dictionary with file paths: {'mids': path, 'finals': path}
        """
        result = {}
        
        if self.mids_mcqs:
            result['mids'] = self.save_section('mids')
        
        if self.finals_mcqs:
            result['finals'] = self.save_section('finals')
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about saved MCQs
        
        Returns:
            Dictionary with statistics
        """
        return {
            'pdf_name': self.pdf_name,
            'output_folder': str(self.output_folder),
            'mids_count': len(self.mids_mcqs),
            'finals_count': len(self.finals_mcqs),
            'total_count': len(self.mids_mcqs) + len(self.finals_mcqs),
            'mids_file': str(self.mids_file) if self.mids_mcqs else None,
            'finals_file': str(self.finals_file) if self.finals_mcqs else None
        }
    
    def load_existing(self, section: str) -> List[Dict[str, Any]]:
        """
        Load existing MCQs from file (for resume functionality)
        
        Args:
            section: 'mids' or 'finals'
        
        Returns:
            List of existing MCQs
        """
        file_path = self.mids_file if section == 'mids' else self.finals_file
        
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                mcqs = json.load(f)
            
            print(f"📖 Loaded {len(mcqs)} existing MCQs from {file_path.name}")
            return mcqs
        
        except Exception as e:
            print(f"⚠️  Failed to load existing MCQs: {str(e)}")
            return []

