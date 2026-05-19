# 🔍 Project Audit: PDF MCQ Extraction Tool

**Date:** May 19, 2026  
**Scope:** Full architectural audit, weak points, and improvement suggestions

---

## 📋 Table of Contents

1. [Critical Issues (Fixed)](#1-critical-issues-fixed)
2. [Architectural Problems](#2-architectural-problems)
3. [Race Conditions & State Management](#3-race-conditions--state-management)
4. [Error Handling Gaps](#4-error-handling-gaps)
5. [Performance Bottlenecks](#5-performance-bottlenecks)
6. [Code Quality Issues](#6-code-quality-issues)
7. [Security Concerns](#7-security-concerns)
8. [UI/UX Issues](#8-uiux-issues)
9. [Improvement Roadmap](#9-improvement-roadmap)

---

## 1. Critical Issues (Fixed)

### ✅ Timeout After Chat Reset (RESOLVED)

**Root Cause:** After `reset_chat()`, the server used `waitUntil: 'domcontentloaded'` which fires before Gemini's JavaScript framework fully initializes. The 2-second delay was insufficient. The next request would find the textarea in DOM but it wasn't interactive yet, causing the Enter key press to do nothing → 180s timeout.

**Fix Applied:**
- Changed to `waitUntil: 'networkidle2'` with fallback
- Added `verifyPageReady()` function that checks element interactivity (not just DOM presence)
- Added `chatSessionId` tracking to invalidate stale requests
- Added `isPageReady` flag to prevent sending to uninitialized page
- Added retry logic with exponential backoff in `gemini_client.py`
- Added post-reset health verification

---

## 2. Architectural Problems

### 🔴 HIGH: Tight Coupling Between Python and Node.js

**Problem:** The Python client (`gemini_client.py`) communicates with the Node.js server (`server.js`) over HTTP localhost. If either crashes, the other has no graceful recovery mechanism.

**Impact:** If the Node process dies mid-request, the Python UI hangs until timeout.

**Suggestion:**
- Add a heartbeat mechanism (Python polls `/api/health` every 10s)
- Add automatic Node.js restart in `launcher.py` if health check fails
- Consider using WebSocket for real-time bidirectional communication

### 🔴 HIGH: No Request Queue or Backpressure

**Problem:** The server processes one request at a time but has no explicit queue. If two requests arrive simultaneously (e.g., due to a race condition), behavior is undefined.

**Suggestion:**
- Implement a proper request queue in `server.js`
- Add a mutex/lock around `sendToGemini()` to serialize access
- Return 429 (Too Many Requests) if a request is already in-flight

### 🟡 MEDIUM: Monolithic Server File

**Problem:** `server.js` is 1200+ lines handling browser automation, API routing, response parsing, caching, rate limiting, and prompt generation all in one file.

**Suggestion:**
- Split into modules: `browser.js`, `routes.js`, `prompts.js`, `cache.js`, `rate-limiter.js`
- Use a class-based architecture for browser management

### 🟡 MEDIUM: No API Versioning

**Problem:** The API has no versioning. Any breaking change requires updating both Python and Node simultaneously.

**Suggestion:** Add `/api/v1/` prefix to all endpoints.

### 🟡 MEDIUM: Hardcoded Configuration

**Problem:** Many values are hardcoded in source code:
- `CACHE_EXPIRY_MS = 300000` in server.js
- `MAX_REQUESTS_BEFORE_COOLDOWN = 50` in server.js
- `COOLDOWN_DURATION_MS = 5 * 60 * 1000` in server.js
- `request_timeout_seconds: 200` in config.json (but some timeouts are hardcoded in code)
- Chrome paths hardcoded for Windows only

**Suggestion:** Move ALL configurable values to `config.json` and read them at startup.

---

## 3. Race Conditions & State Management

### 🔴 HIGH: Pause During In-Flight Request

**Problem:** When user clicks "Pause", the `pause()` method sends a POST to `/api/pause`. The server sets `isPaused = true`. But if there's already a request being processed by `sendToGemini()`, it continues to completion. The NEXT request will be rejected with "PAUSED" error.

**Impact:** The current in-flight request might complete and its response is processed AFTER the user expected processing to stop.

**Suggestion:**
- Track in-flight request state
- On pause, let current request complete but don't start new ones
- Signal the UI clearly: "Pausing after current request completes..."

### 🟡 MEDIUM: `activeRequest` Race Condition

**Problem:** In `sendToGemini()`, `activeRequest` and `activeRequestText` are checked and set without any mutex. In theory, two nearly-simultaneous API calls could both pass the check before either sets the flag.

**Impact:** Low (unlikely in practice since Python sends sequentially), but architecturally unsound.

**Suggestion:** Use a proper lock/semaphore pattern.

### 🟡 MEDIUM: Cache Key Collision

**Problem:** Cache key is MD5 hash of the text content. If the same text is sent with different `expected_mcqs` or `content_type`, the cached response from the wrong type could be returned.

**Suggestion:** Include `expected_mcqs`, `content_type`, and `dom_delay` in the cache key.

### 🟡 MEDIUM: `last_response` Duplicate Assignment

**Problem:** In `gemini_client.py` line 37-38:
```python
self.last_response = None
self.last_response = None  # Duplicate!
```

**Impact:** No functional impact, but indicates copy-paste carelessness.

---

## 4. Error Handling Gaps

### 🔴 HIGH: Browser Crash Not Detected

**Problem:** If Chrome crashes or the tab becomes unresponsive, `page` object methods will throw but there's no recovery mechanism to restart the browser.

**Suggestion:**
- Add `page.on('error')` and `browser.on('disconnected')` handlers
- Implement automatic browser restart on crash
- Add `/api/restart-browser` endpoint

### 🟡 MEDIUM: No Retry for Transient Network Errors

**Problem:** If `page.goto()` fails due to transient network issue, the entire reset fails. While we added retry in `gemini_client.py`, the server itself doesn't retry navigation.

**Suggestion:** Add 2-3 retries with backoff for navigation in `initializeBrowser()` and `reset-chat`.

### 🟡 MEDIUM: Silent Failures in JSON Parsing

**Problem:** In `gemini_client.py`, if `json_fixer.fix_json()` returns an empty array, processing continues silently. The batch is counted as "processed" but produced 0 MCQs.

**Impact:** You might think all pages were processed when actually many returned empty.

**Suggestion:**
- Track empty-response batches separately
- Add a warning threshold (e.g., if >50% of batches return empty)
- Add an option to retry empty batches

### 🟡 MEDIUM: `ProcessingThread` (Single PDF) Has No Chat Reset Logic

**Problem:** The `ProcessingThread` class (used for single PDF processing) never resets the chat. It only exists in `BatchProcessingThread`. If used, long conversations could exceed Gemini's context window.

---

## 5. Performance Bottlenecks

### 🟡 MEDIUM: Blocking `time.sleep()` in QThread

**Problem:** In `processing_thread.py`, `time.sleep()` is used inside a QThread. While this works, it blocks the thread from responding to stop/pause signals during the sleep.

**Suggestion:** Replace with a loop that checks `should_stop` every 100ms:
```python
def interruptible_sleep(self, seconds):
    for _ in range(int(seconds * 10)):
        if self.should_stop:
            return
        time.sleep(0.1)
```

### 🟡 MEDIUM: DOM Resource Blocking May Break Gemini

**Problem:** `server.js` blocks stylesheets and images. While this speeds up loading, future Gemini UI updates might require CSS for proper rendering of the textarea/input elements.

**Suggestion:** Only block `media` and `font` types. Keep stylesheets to ensure UI elements render correctly.

### 🟢 LOW: Response Cache Inefficiency

**Problem:** Cache uses MD5 hashing on every request. For large texts (50k+ chars), this adds latency.

**Suggestion:** Use first 100 chars + length as a fast pre-check before computing full hash.

---

## 6. Code Quality Issues

### 🟡 MEDIUM: Duplicate Code in `ui_main.py`

**Problem:** Lines 526-528:
```python
self.reset_btn = QPushButton("🔄 Reset")
self.reset_btn.setMinimumHeight(35)  # Reduced from 40
self.reset_btn = QPushButton("🔄 Reset")  # DUPLICATE!
self.reset_btn.setMinimumHeight(35)  # DUPLICATE!
```

The reset button is created twice. The first instance is immediately garbage collected.

### 🟡 MEDIUM: Inconsistent Error Messages

**Problem:** Some errors use `print()`, others use `self.log_signal.emit()`, some use both. No consistent format.

**Suggestion:** Standardize all error output to include: `[TIMESTAMP] [ERROR_CODE] [SOURCE] message`

### 🟡 MEDIUM: Magic Numbers Throughout

**Problem:** 
- `50` (characters minimum for valid response) in multiple places
- `5000` (ms delay) in multiple places
- `2000` (ms delay) scattered throughout
- `180000` (timeout) hardcoded in two places in the same function

**Suggestion:** Define constants at the top of each file.

### 🟢 LOW: Unused Imports and Dead Code

**Problem:**
- `cleanJsonResponse()` in `server.js` is defined but never called by the API endpoint
- `validateMCQs()` in `server.js` is defined but never called
- `_validate_mcqs()` in `gemini_client.py` exists but is never called in the main flow

### 🟢 LOW: System Prompt Duplication

**Problem:** In `generateSystemPrompt()`, lines 166-170 contain a duplicated "BEFORE SENDING YOUR RESPONSE" section (appears twice with overlapping content).

---

## 7. Security Concerns

### 🟡 MEDIUM: No Input Sanitization

**Problem:** PDF text content is sent directly to Gemini without sanitization. Malicious PDF content could potentially inject instructions that override the system prompt.

**Suggestion:** Strip any text that looks like meta-instructions before sending.

### 🟡 MEDIUM: CORS Wildcard

**Problem:** `res.header('Access-Control-Allow-Origin', '*')` allows any origin to call the API.

**Impact:** Low (localhost only), but bad practice.

**Suggestion:** Restrict to `http://localhost:*` or remove CORS entirely since it's same-machine.

### 🟢 LOW: Session Data in Git-Ignored Folder

**Problem:** Puppeteer session data (`./session/`) stores Chrome login cookies. If `.gitignore` is misconfigured, these could be committed.

**Current Status:** `.gitignore` appears to handle this, but worth verifying.

---

## 8. UI/UX Issues

### 🟡 MEDIUM: No Progress Per-Batch Within a PDF

**Problem:** Progress bar shows PDF-level progress (1/10 PDFs = 10%), but within a single PDF processing (e.g., 10 batches), the progress bar doesn't update incrementally.

**Suggestion:** Calculate combined progress: `(pdf_progress * batch_in_pdf_progress)`

### 🟡 MEDIUM: Settings Not Persisted

**Problem:** UI settings (delay, DOM delay, pages per request, chat reset threshold) reset to defaults on every app restart.

**Suggestion:** Save settings to a `user_settings.json` file and load on startup.

### 🟢 LOW: Log Window Size Fixed

**Problem:** Log window has `setMaximumHeight(300)` which limits visibility on large monitors.

**Suggestion:** Make it resizable or use a splitter layout.

---

## 9. Improvement Roadmap

### Priority 1 (Critical - Do Next)
| # | Item | Effort |
|---|------|--------|
| 1 | Add browser crash detection + auto-restart | 2-3 hours |
| 2 | Fix cache key to include content_type | 15 minutes |
| 3 | Add heartbeat mechanism (Python → Node) | 1 hour |
| 4 | Remove duplicate code (reset_btn, system prompt) | 15 minutes |

### Priority 2 (Important - This Week)
| # | Item | Effort |
|---|------|--------|
| 5 | Split server.js into modules | 3-4 hours |
| 6 | Add request queue/mutex in server | 1-2 hours |
| 7 | Persist UI settings to file | 30 minutes |
| 8 | Add interruptible sleep | 30 minutes |
| 9 | Track and report empty-response batches | 1 hour |

### Priority 3 (Nice to Have - This Month)
| # | Item | Effort |
|---|------|--------|
| 10 | WebSocket communication instead of HTTP polling | 4-6 hours |
| 11 | Move all hardcoded values to config.json | 1-2 hours |
| 12 | Add API versioning | 1 hour |
| 13 | Add per-batch progress tracking in UI | 2 hours |
| 14 | Add automatic retry for empty-response batches | 2 hours |

---

## Summary

The project is functional and gets the job done, but has several architectural weaknesses that manifest as occasional failures (like the timeout-after-reset bug). The biggest risks are:

1. **Single point of failure** - If Chrome/Node crashes, no recovery
2. **State synchronization** - Python and Node can get out of sync
3. **Silent failures** - Empty responses counted as "success"

The fixes applied in this session address the most critical issue (timeout after reset) and add configurable controls. The roadmap above prioritizes the remaining issues by impact and effort.
