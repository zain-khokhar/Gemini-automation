"""
Gemini Client Module
Handles communication with the Node.js Gemini server
"""

import requests
import json
import time
import re
from typing import List, Dict, Any


class GeminiClient:
    # Pre-compiled regex for performance
    WHITESPACE_PATTERN = re.compile(r'\s+')

    def __init__(self, config_path='config.json'):
        """
        Initialize Gemini client
        
        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.server_url = self.config['gemini_server_url']
        self.timeout = self.config['request_timeout_seconds']
        
        # Initialize session for connection pooling
        self.session = requests.Session()
        
        # Track requests to prevent duplicates
        self.last_request_text = None
        self.last_request_time = 0
        self.last_response = None
        self.last_response = None
    
    def check_health(self) -> bool:
        """
        Check if the Gemini server is running and initialized
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.server_url}/api/health",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('initialized', False)
            
            return False
        except Exception as e:
            print(f"❌ Server health check failed: {str(e)}")
            return False
    
    def reset_chat(self) -> bool:
        """
        Request server to start a fresh Gemini chat
        
        Returns:
            True if chat reset successfully, False otherwise
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/reset-chat",
                timeout=10
            )
            
            if response.status_code == 200:
                # Clear local cache too
                self.last_request_text = None
                self.last_response = None
                print("✓ Fresh Gemini chat started")
                return True
            else:
                print(f"⚠️ Failed to reset chat: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️ Failed to reset chat: {str(e)}")
            return False
    
    def pause(self) -> bool:
        """
        Pause processing on the server
        
        Returns:
            True if paused successfully, False otherwise
        """
        try:
            response = self.session.post(
                f"{self.server_url}/api/pause",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"⏸️  Processing paused at {data.get('pausedAt', 'now')}")
                return True
            else:
                print(f"⚠️ Failed to pause: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️ Failed to pause: {str(e)}")
            return False
    
    def resume(self) -> bool:
        """
        Resume processing on the server
        
        Returns:
            True if resumed successfully, False otherwise
        """
        try:
            response = self.session.post(
                f"{self.server_url}/api/resume",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                duration = data.get('pauseDurationSeconds', 0)
                print(f"▶️  Processing resumed (was paused for {duration}s)")
                return True
            else:
                print(f"⚠️ Failed to resume: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️ Failed to resume: {str(e)}")
            return False
    
    def is_paused(self) -> bool:
        """
        Check if processing is currently paused
        
        Returns:
            True if paused, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.server_url}/api/pause-status",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('isPaused', False)
            
            return False
        except Exception as e:
            print(f"⚠️ Failed to check pause status: {str(e)}")
            return False
    
    def generate_mcqs(self, text: str, section: str = 'unknown', 
                      pages_count: int = 5, on_attempt: callable = None, content_type: str = 'mcq', dom_delay_seconds: int = 1) -> List[Dict[str, Any]]:
        """
        Generate MCQs or Short Notes from text using Gemini - SINGLE REQUEST WITH AUTO-FIX
        
        Args:
            text: Text content to generate MCQs/notes from
            section: Section name (mids/finals) for logging
            pages_count: Number of pages in this batch (default: 5)
            on_attempt: Callback function (deprecated, kept for compatibility)
            content_type: Type of content to generate ('mcq' or 'short_notes')
            dom_delay_seconds: DOM stabilization delay in seconds (1-15)
        
        Returns:
            List of MCQ or short note dictionaries
        
        Raises:
            Exception if request fails
        """
        import json_fixer
        import time
        
        # Calculate expected MCQs: 2 MCQs per page
        expected_mcqs = pages_count * 2
        
        current_time = time.time()
        
        # Prevent duplicate requests within 5 seconds
        if (self.last_request_text == text and 
            current_time - self.last_request_time < 5.0 and 
            self.last_response is not None):
            print(f"  ⚠️  Duplicate request detected (within 5s), using cached response")
            return self.last_response
        
        # Track this request
        self.last_request_text = text
        self.last_request_time = current_time
        
        try:
            content_label = "MCQs" if content_type == 'mcq' else "Short Notes"
            print(f"  → Sending request to server ({pages_count} pages, expecting {expected_mcqs} {content_label})...")
            start_time = time.time()
            
            # Single request - no retries
            response = self.session.post(
                f"{self.server_url}/api/generate-mcqs",
                json={
                    'text': text,
                    'section': section,
                    'expected_mcqs': expected_mcqs,
                    'content_type': content_type,
                    'dom_delay_seconds': dom_delay_seconds
                },
                timeout=self.timeout
            )
            
            # Parse response data
            try:
                data = response.json()
            except json.JSONDecodeError:
                raise Exception(f"Server returned invalid JSON (status {response.status_code})")
            
            # Handle different status codes
            if response.status_code == 503:
                error_code = data.get('code', 'UNKNOWN')
                if error_code == 'NOT_INITIALIZED':
                    raise Exception("Server not initialized. Please start the server and complete login.")
                elif error_code == 'PAUSED':
                    raise Exception("Processing is paused. Please resume to continue.")
                raise Exception(f"Service unavailable: {data.get('error', 'Unknown error')}")
            
            elif response.status_code == 504:
                raise Exception(f"Server timeout: {data.get('error', 'Request took too long')}")
            
            elif response.status_code != 200:
                raise Exception(f"Server error ({response.status_code}): {data.get('error', 'Unknown error')}")
            
            # Check success flag
            if not data.get('success'):
                raise Exception(f"Generation failed: {data.get('error', 'Unknown error')}")
            
            # Get raw response text
            raw_response = data.get('raw_response', '')
            if not raw_response:
                # Fallback to mcqs if available
                mcqs = data.get('mcqs', [])
                if mcqs:
                    self.last_response = mcqs
                    elapsed_time = time.time() - start_time
                    print(f"  ✓ Received {len(mcqs)} in {elapsed_time:.1f}s")
                    return mcqs
                raise Exception("No response data from server")
            
            # Log when data received from Gemini
            receive_time = time.time() - start_time
            print(f"  📥 Data received from Gemini ({len(raw_response)} chars) in {receive_time:.1f}s")
            
            # Parse and validate JSON
            print(f"  📋 Parsing and validating JSON ({len(raw_response)} chars)...")
            parse_start = time.time()
            
            try:
                # Use json_fixer to parse, fix syntax if needed, and filter out broken items
                mcqs = json_fixer.fix_json(raw_response, content_type)
                
                parse_time = time.time() - parse_start
                print(f"  ✓ JSON parsed and filtered in {parse_time*1000:.0f}ms")
                
            except Exception as e:
                parse_time = time.time() - parse_start
                print(f"  ❌ JSON parsing failed: {str(e)}")
                print(f"     Returning empty array")
                mcqs = []
            
            # Check if it's a list
            if not isinstance(mcqs, list):
                print(f"  ⚠️  Response is not a JSON array (type: {type(mcqs).__name__})")
                print(f"     Returning empty array")
                mcqs = []
            
            # If empty, just log it
            if not mcqs:
                print(f"  ⚠️  Empty array received (0 items)")
            else:
                print(f"  ✓ Received {len(mcqs)} items")
            
            # Success! Cache the response
            self.last_response = mcqs
            
            total_time = time.time() - start_time
            cached_indicator = " (cached)" if data.get('cached') else ""
            print(f"  ✅ Successfully processed {len(mcqs)} items in {total_time:.1f}s{cached_indicator}")
            print(f"     └─ Breakdown: Receive={receive_time:.1f}s, Parse={parse_time*1000:.0f}ms")
            
            return mcqs

            
        except requests.exceptions.Timeout:
            raise Exception("Request timed out - server took too long to respond")
        
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Cannot connect to server: {str(e)}")
        
        except Exception as e:
            error_msg = str(e)
            print(f"  ❌ Request failed: {error_msg}")
            raise Exception(error_msg)


    
    def _validate_mcqs(self, mcqs: List[Dict[str, Any]]):
        """
        Validate MCQ structure
        
        Args:
            mcqs: List of MCQ dictionaries
        
        Raises:
            Exception if validation fails
        """
        if not isinstance(mcqs, list):
            raise Exception("MCQs must be a list")
        
        required_fields = ['id', 'question', 'options', 'correct', 'explanation', 'difficulty', 'importance']
        
        def normalize_string(s):
            """Normalize string by replacing all whitespace types with regular space and stripping"""
            if not isinstance(s, str):
                return s
            # Replace all Unicode spaces with regular space
            s = s.replace('\u00a0', ' ')  # Non-breaking space
            s = s.replace('\u2009', ' ')  # Thin space
            s = s.replace('\u200a', ' ')  # Hair space
            s = s.replace('\u202f', ' ')  # Narrow no-break space
            # Normalize multiple spaces to single space
            s = self.WHITESPACE_PATTERN.sub(' ', s)
            return s.strip()
        
        for i, mcq in enumerate(mcqs):
            # Check all required fields
            for field in required_fields:
                if field not in mcq:
                    raise Exception(f"MCQ {i+1} missing field: {field}")
            
            # Validate options
            if not isinstance(mcq['options'], list) or len(mcq['options']) != 4:
                raise Exception(f"MCQ {i+1} must have exactly 4 options")
            
            # Validate correct answer - NORMALIZE BEFORE COMPARING
            correct_normalized = normalize_string(mcq['correct'])
            options_normalized = [normalize_string(opt) for opt in mcq['options']]
            
            if correct_normalized not in options_normalized:
                print(f"  ⚠️  MCQ {i+1} validation details:")
                print(f"     Correct answer: '{mcq['correct']}' (normalized: '{correct_normalized}')")
                print(f"     Options: {mcq['options']}")
                print(f"     Options normalized: {options_normalized}")
                raise Exception(f"MCQ {i+1} correct answer not in options")

