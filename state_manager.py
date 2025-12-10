"""
State Manager Module
Handles persistence of last processed position across application restarts
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class StateManager:
    def __init__(self, state_file='last_processed_state.json'):
        """
        Initialize state manager
        
        Args:
            state_file: Name of the state file (stored in current directory)
        """
        self.state_file = Path(state_file)
    
    def save_state(self, pdf_path: str, pdf_index: int, pdf_name: str, 
                   section: str, batch: int) -> bool:
        """
        Save current processing state to file
        
        Args:
            pdf_path: Full path to the PDF file
            pdf_index: Index of the PDF in the list
            pdf_name: Name of the PDF file
            section: Current section (mids/finals)
            batch: Current batch number
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            state = {
                'pdf_path': str(pdf_path),
                'pdf_index': pdf_index,
                'pdf_name': pdf_name,
                'section': section,
                'batch': batch,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"⚠️  Failed to save state: {str(e)}")
            return False
    
    def load_state(self) -> Optional[Dict]:
        """
        Load last processed state from file
        
        Returns:
            Dictionary with state data, or None if file doesn't exist or is invalid
        """
        try:
            if not self.state_file.exists():
                return None
            
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Validate required fields
            required_fields = ['pdf_path', 'pdf_index', 'pdf_name', 'section', 'batch']
            if all(field in state for field in required_fields):
                return state
            else:
                print("⚠️  State file is missing required fields")
                return None
                
        except Exception as e:
            print(f"⚠️  Failed to load state: {str(e)}")
            return None
    
    def clear_state(self) -> bool:
        """
        Clear the state file
        
        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            return True
        except Exception as e:
            print(f"⚠️  Failed to clear state: {str(e)}")
            return False
    
    def get_state_summary(self) -> str:
        """
        Get a human-readable summary of the saved state
        
        Returns:
            Summary string, or empty string if no state
        """
        state = self.load_state()
        if not state:
            return ""
        
        return (f"PDF {state['pdf_index']}: {state['pdf_name']}, "
                f"Section: {state['section'].upper()}, "
                f"Batch: {state['batch']}")


if __name__ == '__main__':
    # Test the state manager
    manager = StateManager()
    
    # Save test state
    manager.save_state(
        pdf_path="C:/test/folder/sample.pdf",
        pdf_index=5,
        pdf_name="sample.pdf",
        section="mids",
        batch=3
    )
    
    # Load and display
    state = manager.load_state()
    if state:
        print("Loaded state:")
        print(json.dumps(state, indent=2))
        print(f"\nSummary: {manager.get_state_summary()}")
    
    # Clear state
    manager.clear_state()
    print("\nState cleared")
