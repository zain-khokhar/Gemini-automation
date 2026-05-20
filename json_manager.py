"""
JSON Manager Module
Handles JSON file creation, validation, saving with field transformation
"""

import json
import threading
from pathlib import Path
from typing import List, Dict, Any
from folder_organizer import get_organized_path

# Global lock for thread-safe ID generation
_id_lock = threading.Lock()


class JSONManager:
    # Fields to remove from Gemini output
    FIELDS_TO_REMOVE = ['source', 'importance', 'difficulty', 'id']

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
        
        # Create separate subfolders for mids and finals
        self.mids_folder = self.output_folder / "mids"
        self.finals_folder = self.output_folder / "finals"
        
        # Create output folders
        self.output_folder.mkdir(parents=True, exist_ok=True)
        self.mids_folder.mkdir(parents=True, exist_ok=True)
        self.finals_folder.mkdir(parents=True, exist_ok=True)
        
        # File paths - different naming based on content type
        if content_type == 'short_notes':
            self.mids_file = self.mids_folder / f"short note {pdf_name}_mids.json"
            self.finals_file = self.finals_folder / f"short note {pdf_name}_finals.json"
        else:
            self.mids_file = self.mids_folder / f"{pdf_name}_mids_mcqs.json"
            self.finals_file = self.finals_folder / f"{pdf_name}_finals_mcqs.json"
        
        # MCQ storage
        self.mids_mcqs = []
        self.finals_mcqs = []
        
        print(f"📁 Output folder: {self.output_folder}")
        print(f"   ├── mids: {self.mids_folder}")
        print(f"   └── finals: {self.finals_folder}")
    
    def _transform_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a single item by removing unwanted fields.
        
        Removes: source, importance, difficulty, id
        
        Args:
            item: Raw item dictionary from Gemini
        
        Returns:
            Cleaned item dictionary
        """
        cleaned = {}
        for key, value in item.items():
            if key.lower() not in [f.lower() for f in self.FIELDS_TO_REMOVE]:
                cleaned[key] = value
        return cleaned
    
    def _transform_batch(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform a batch of items by removing unwanted fields.
        
        Args:
            items: List of raw item dictionaries
        
        Returns:
            List of cleaned item dictionaries
        """
        return [self._transform_item(item) for item in items]
    
    def add_mcqs(self, mcqs: List[Dict[str, Any]], section: str):
        """
        Add MCQs to the appropriate section after transforming (removing unwanted fields)
        
        Args:
            mcqs: List of MCQ dictionaries
            section: 'mids' or 'finals'
        """
        # Transform: remove unwanted fields before storing
        transformed = self._transform_batch(mcqs)
        
        if section == 'mids':
            self.mids_mcqs.extend(transformed)
        elif section == 'finals':
            self.finals_mcqs.extend(transformed)
        else:
            raise ValueError("Section must be 'mids' or 'finals'")
    
    def _assign_sequential_ids(self, mcqs: List[Dict[str, Any]], file_path: Path) -> List[Dict[str, Any]]:
        """
        Assign collision-free sequential IDs.
        
        Logic:
        - Load existing file to get current max ID
        - New items get IDs starting from max_existing_id + 1
        - Thread-safe via global lock
        
        Args:
            mcqs: List of MCQ dictionaries (without 'id' field)
            file_path: Path to the JSON file (to check existing IDs)
        
        Returns:
            List of MCQs with sequential IDs assigned
        """
        with _id_lock:
            # Determine starting ID
            start_id = 1
            
            # Check if file already exists with data
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                    if isinstance(existing, list) and len(existing) > 0:
                        # Find max ID in existing data
                        existing_ids = [item.get('id', 0) for item in existing if isinstance(item, dict)]
                        if existing_ids:
                            start_id = max(existing_ids) + 1
                except (json.JSONDecodeError, Exception):
                    start_id = 1
            
            # Assign sequential IDs
            for i, mcq in enumerate(mcqs):
                mcq['id'] = start_id + i
            
            return mcqs
    
    def save_section(self, section: str) -> str:
        """
        Save MCQs for a section to JSON file with sequential IDs
        
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
        
        # Assign collision-free sequential IDs
        mcqs = self._assign_sequential_ids(mcqs, file_path)
        
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
