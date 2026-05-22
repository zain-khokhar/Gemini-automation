"""
Smart JSON Auto-Correction Module using json-repair library
Advanced multi-stage algorithm to fix malformed JSON from Gemini
"""

import json
import re
from typing import List, Dict, Any, Optional
from json_repair import repair_json


class JSONFixer:
    """Advanced JSON repair with context-aware fixing using json-repair"""
    
    # Pre-compiled regex patterns for performance
    MARKDOWN_JSON_BLOCK = re.compile(r'```json\s*', re.IGNORECASE)
    MARKDOWN_BLOCK = re.compile(r'```\s*')
    HTML_TAGS = re.compile(r'<[^>]+>')

    def __init__(self):
        self.stats = {
            'fast_path': 0,
            'repaired': 0,
            'failures': 0
        }
    
    def fix_and_parse(self, text: str, expected_type: str = 'mcq') -> List[Dict[str, Any]]:
        """
        Main entry point - fix malformed JSON and return valid items
        
        Args:
            text: Raw response text from Gemini
            expected_type: 'mcq' or 'short_notes'
            
        Returns:
            List of valid dictionaries
        """
        # Stage 0: Fast path - try direct parse first
        print(f"\n[JSONFixer] Processing {len(text)} chars for type: {expected_type}")
        print("[JSONFixer] Stage 0: Attempting fast native parse...")
        try:
            result = json.loads(text)
            self.stats['fast_path'] += 1
            if isinstance(result, list) and len(result) > 0:
                valid_items = self._validate_and_filter(result, expected_type)
                if valid_items:
                    print(f"✓ [JSONFixer] Success: Native parse passed ({len(valid_items)} valid items)")
                    return valid_items
        except Exception as e:
            print(f"⚠️ [JSONFixer] Stage 0 failed: {str(e)}")
        
        # Stage 1: Quick basic cleanup
        print("[JSONFixer] Stage 1: Applying quick regex fixes (markdown, trailing commas, brackets)...")
        cleaned = self._quick_fixes(text)
        
        # Stage 1.5: Fast path after cleanup
        print("[JSONFixer] Stage 1.5: Attempting native parse on cleaned text...")
        try:
            result = json.loads(cleaned)
            self.stats['fast_path'] += 1
            if isinstance(result, list) and len(result) > 0:
                valid_items = self._validate_and_filter(result, expected_type)
                if valid_items:
                    print(f"✓ [JSONFixer] Success: Native parse passed after quick fixes ({len(valid_items)} valid items)")
                    return valid_items
        except Exception as e:
            print(f"⚠️ [JSONFixer] Stage 1.5 failed: {str(e)}")
        
        # Stage 2: Use json-repair library
        # Safety limit: json-repair can take 10+ minutes and freeze the app on massive broken JSONs
        if len(cleaned) > 200000:
            print("❌ [JSONFixer] FATAL: Text is too large (200k+ chars) and severely broken.")
            print("❌ [JSONFixer] Bypassing json-repair to prevent UI freezing.")
            raise Exception("JSON payload is severely malformed and too large to auto-repair safely. Please click 'Repeat Batch'.")

        print("[JSONFixer] Stage 2: Attempting advanced json-repair (this might take some time)...")
        try:
            result = repair_json(cleaned, return_objects=True)
            if isinstance(result, list) and len(result) > 0:
                self.stats['repaired'] += 1
                valid_items = self._validate_and_filter(result, expected_type)
                if valid_items:
                    print(f"✓ [JSONFixer] Success: Repaired successfully using json-repair ({len(valid_items)} valid items)")
                    return valid_items
        except Exception as e:
            print(f"⚠️ [JSONFixer] json-repair failed: {str(e)}")
        
        # Complete failure
        self.stats['failures'] += 1
        print(f"❌ [JSONFixer] Failed: Could not extract valid items after all stages")
        raise Exception("Failed to parse or repair JSON")
    
    def _quick_fixes(self, text: str) -> str:
        """Fast common fixes before passing to json-repair"""
        # Remove markdown code blocks
        text = self.MARKDOWN_JSON_BLOCK.sub('', text)
        text = self.MARKDOWN_BLOCK.sub('', text)
        
        # Strip whitespace
        text = text.strip()
        
        # Remove HTML tags (sometimes Gemini outputs HTML instead of pure JSON)
        text = self.HTML_TAGS.sub('', text)
        
        # --- BASIC FORMAT RECOVERY ---
        
        # Fix trailing commas before closing brackets/braces (most common LLM error)
        text = re.sub(r',\s*]', ']', text)
        text = re.sub(r',\s*}', '}', text)
        
        # Ensure it starts and ends with brackets if it looks like an array
        if not text.startswith('[') and text.find('[') != -1:
            text = text[text.find('['):]
        if not text.endswith(']') and text.rfind(']') != -1:
            text = text[:text.rfind(']')+1]
            
        # Fix truncated JSON (missing final brackets)
        if text.startswith('[') and not text.endswith(']'):
            if text.endswith('}'):
                text += ']'
            elif text.endswith('"'):
                text += '}]'
        
        return text
    
    def _validate_and_filter(self, data: Any, expected_type: str) -> List[Dict[str, Any]]:
        """Validate and filter items, removing broken ones"""
        if not isinstance(data, list):
            if isinstance(data, dict):
                data = [data]
            else:
                return []
        
        valid_items = []
        for item in data:
            if not isinstance(item, dict):
                continue
                
            if expected_type == 'mcq':
                if self._is_valid_mcq(item):
                    valid_items.append(item)
            elif expected_type == 'reviews':
                if self._is_valid_review(item):
                    valid_items.append(item)
            else:
                if self._is_valid_short_note(item):
                    valid_items.append(item)
        
        if len(valid_items) < len(data):
            print(f"⚠️  Filtered out {len(data) - len(valid_items)} broken items")
            
        return valid_items
    
    def _is_valid_mcq(self, mcq: Dict) -> bool:
        """Strict validation for MCQ"""
        # Basic required fields
        if 'question' not in mcq or not mcq['question']:
            return False
        if 'options' not in mcq or not isinstance(mcq['options'], list) or len(mcq['options']) != 4:
            return False
        if 'correct' not in mcq or not mcq['correct']:
            return False
            
        # Check correct answer exists in options (normalized)
        def normalize(s):
            return str(s).strip()
            
        correct = normalize(mcq['correct'])
        options = [normalize(opt) for opt in mcq['options']]
        
        if correct not in options:
            return False
            
        return True

    def _is_valid_short_note(self, note: Dict) -> bool:
        """Strict validation for Short Note"""
        if 'question' not in note or not note['question']:
            return False
        if 'answer' not in note or not note['answer']:
            return False
        return True

    def _is_valid_review(self, review: Dict) -> bool:
        """Strict validation for Review"""
        if 'subject_code' not in review or not review['subject_code']:
            return False
        if 'review' not in review or not review['review']:
            return False
        # review_date is optional (can be null)
        return True
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics"""
        return self.stats.copy()


# Global instance
_fixer = JSONFixer()


def fix_and_parse(text: str, expected_type: str = 'mcq') -> List[Dict[str, Any]]:
    """
    Convenience function to fix and parse JSON
    
    Args:
        text: Raw JSON text from Gemini
        expected_type: 'mcq' or 'short_notes'
        
    Returns:
        List of valid dictionaries
    """
    return _fixer.fix_and_parse(text, expected_type)

def fix_json(text: str, expected_type: str = 'mcq') -> List[Dict[str, Any]]:
    """Alias for fix_and_parse"""
    return _fixer.fix_and_parse(text, expected_type)


def get_stats() -> Dict[str, int]:
    """Get global fixer statistics"""
    return _fixer.get_stats()
