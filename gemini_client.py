"""
Gemini Client Module
Handles communication with the Node.js Gemini server
"""

import requests
import json
import time
from typing import List, Dict, Any, Optional


class GeminiClient:
    def __init__(self, config_path='config.json'):
        """Initialize Gemini client"""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.server_url = self.config['gemini_server_url']
        self.timeout = self.config['request_timeout_seconds']
        
        # Connection pooling
        self.session = requests.Session()
    
    def check_health(self) -> bool:
        """Check if the Gemini server is running and initialized"""
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
    
    def send_prompt(self, text: str, section: str = 'unknown',
                    pages_count: int = 5, content_type: str = 'mcq') -> dict:
        """
        Send prompt to Gemini via the server. Returns immediately after sending.
        Does NOT wait for Gemini to generate the response.
        
        Args:
            text: Text content to send
            section: Section name (mids/finals)
            pages_count: Number of pages in this batch
            content_type: 'mcq' or 'short_notes'
        
        Returns:
            Server response dict with success status
        
        Raises:
            Exception on failure
        """
        expected_mcqs = pages_count * 2
        content_label = "MCQs" if content_type == 'mcq' else "Short Notes"
        
        print(f"  → Sending prompt to Gemini ({pages_count} pages, {expected_mcqs} {content_label})...")
        
        try:
            response = self.session.post(
                f"{self.server_url}/api/send-prompt",
                json={
                    'text': text,
                    'section': section,
                    'expected_mcqs': expected_mcqs,
                    'content_type': content_type
                },
                timeout=30  # Short timeout — we're just sending, not waiting
            )
            
            data = response.json()
            
            if response.status_code == 503:
                code = data.get('code', 'UNKNOWN')
                if code == 'NOT_INITIALIZED':
                    raise Exception("Server not initialized. Please complete login.")
                elif code == 'PAUSED':
                    raise Exception("Processing is paused. Please resume.")
                elif code == 'PAGE_NOT_READY':
                    raise Exception("Page not ready to accept input.")
                raise Exception(f"Service unavailable: {data.get('error')}")
            
            if response.status_code != 200 or not data.get('success'):
                raise Exception(f"Send failed: {data.get('error', 'Unknown error')}")
            
            print(f"  ✓ Prompt sent successfully ({data.get('promptLength', '?')} chars)")
            return data
            
        except requests.exceptions.Timeout:
            raise Exception("Timeout while sending prompt")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Cannot connect to server: {str(e)}")

    def send_fix_json(self, broken_json: str) -> dict:
        """
        Send a request to Gemini to fix invalid JSON.
        
        Args:
            broken_json: The invalid JSON text
            
        Returns:
            Server response dict
            
        Raises:
            Exception on failure
        """
        print(f"  → Sending JSON fix request to Gemini...")
        
        try:
            response = self.session.post(
                f"{self.server_url}/api/send-fix-json",
                json={'broken_json': broken_json},
                timeout=30
            )
            
            data = response.json()
            
            if response.status_code == 503:
                code = data.get('code', 'UNKNOWN')
                if code == 'NOT_INITIALIZED':
                    raise Exception("Server not initialized. Please complete login.")
                elif code == 'PAUSED':
                    raise Exception("Processing is paused. Please resume.")
                elif code == 'PAGE_NOT_READY':
                    raise Exception("Page not ready to accept input.")
                raise Exception(f"Service unavailable: {data.get('error')}")
            
            if response.status_code != 200 or not data.get('success'):
                raise Exception(f"Send fix failed: {data.get('error', 'Unknown error')}")
            
            print(f"  ✓ JSON fix prompt sent successfully")
            return data
            
        except requests.exceptions.Timeout:
            raise Exception("Timeout while sending fix prompt")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Cannot connect to server: {str(e)}")
    
    def extract_response(self) -> str:
        """
        Extract the current response text from Gemini page.
        Grabs whatever is currently displayed — call this after Gemini has finished.
        
        Returns:
            Raw response text string
        
        Raises:
            Exception on failure
        """
        print("  → Extracting response from Gemini...")
        
        try:
            response = self.session.post(
                f"{self.server_url}/api/extract-response",
                timeout=15
            )
            
            data = response.json()
            
            if response.status_code == 404:
                raise Exception(f"No response found: {data.get('error')}")
            
            if response.status_code != 200 or not data.get('success'):
                raise Exception(f"Extract failed: {data.get('error', 'Unknown error')}")
            
            raw = data.get('raw_response', '')
            print(f"  ✓ Extracted {len(raw)} characters")
            return raw
            
        except requests.exceptions.Timeout:
            raise Exception("Timeout while extracting response")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Cannot connect to server: {str(e)}")
    
    def reset_chat(self) -> bool:
        """
        Reset Gemini chat to start fresh.
        Includes post-reset verification.
        """
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.post(
                    f"{self.server_url}/api/reset-chat",
                    timeout=60
                )
                
                if response.status_code == 200:
                    data = response.json()
                    session_id = data.get('chatSessionId', '?')
                    elapsed = data.get('elapsed_ms', '?')
                    print(f"✓ Fresh chat started (session={session_id}, {elapsed}ms)")
                    
                    time.sleep(2)
                    
                    if self.check_health():
                        return True
                    else:
                        print(f"⚠️ Health check failed after reset (attempt {attempt}/{max_retries})")
                        if attempt < max_retries:
                            time.sleep(3)
                            continue
                        return False
                else:
                    try:
                        error_data = response.json()
                        print(f"⚠️ Reset failed (attempt {attempt}): {error_data.get('error')}")
                    except:
                        print(f"⚠️ Reset failed (attempt {attempt}): HTTP {response.status_code}")
                    
                    if attempt < max_retries:
                        time.sleep(attempt * 3)
                        continue
                    return False
                    
            except requests.exceptions.Timeout:
                print(f"⚠️ Reset timed out (attempt {attempt}/{max_retries})")
                if attempt < max_retries:
                    time.sleep(5)
                    continue
                return False
            except Exception as e:
                print(f"⚠️ Reset error (attempt {attempt}): {str(e)}")
                if attempt < max_retries:
                    time.sleep(3)
                    continue
                return False
        
        return False
    
    def pause(self) -> bool:
        """Pause processing on the server"""
        try:
            response = self.session.post(f"{self.server_url}/api/pause", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def resume(self) -> bool:
        """Resume processing on the server"""
        try:
            response = self.session.post(f"{self.server_url}/api/resume", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
