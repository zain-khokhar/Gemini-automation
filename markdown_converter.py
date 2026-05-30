"""
Markdown Converter Module
Converts PDF handouts to high-fidelity Markdown files for the Highlighted Handouts pipeline.

Uses pymupdf4llm for extremely accurate Markdown extraction that preserves:
- Headings, paragraphs, lists
- Text structure and formatting
- Table layouts (best effort)

Tracking:
- Maintains a JSON status file to avoid re-processing already converted PDFs.
- Uses partial file hashing to detect replaced/updated PDFs.

Storage:
- Markdown files are stored in the organized folder structure:
  {json_output_root}/{subject_code}/{pdf_name}/markdown/{pdf_name}.md
"""

import os
import json
import hashlib
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from folder_organizer import get_json_output_root, extract_subject_code

# Thread-safe lock for status file access
_status_lock = threading.Lock()

# Status file path (stored in JSON output root)
_STATUS_FILENAME = "markdown_conversion_status.json"


def _get_status_file_path() -> Path:
    """Get the path to the markdown conversion status tracking file."""
    return Path(get_json_output_root()) / _STATUS_FILENAME


def _compute_file_hash(file_path: str, chunk_size: int = 10240) -> str:
    """
    Compute a partial MD5 hash of a file (first 10KB).
    This is fast and sufficient to detect if a PDF was replaced.
    """
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            data = f.read(chunk_size)
            hasher.update(data)
    except Exception:
        return ""
    return hasher.hexdigest()


def _load_status() -> Dict[str, Any]:
    """Load the conversion status tracking file."""
    status_path = _get_status_file_path()
    if not status_path.exists():
        return {}
    try:
        with open(status_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}


def _save_status(status: Dict[str, Any]):
    """Save the conversion status tracking file."""
    status_path = _get_status_file_path()
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)


def _get_pdf_key(pdf_path: str) -> str:
    """Get a stable key for a PDF (its stem name)."""
    return Path(pdf_path).stem


def _get_markdown_dir(pdf_path: str) -> Path:
    """
    Get the directory where markdown files should be stored for a given PDF.
    Structure: {json_output_root}/{subject_code}/{pdf_name}/markdown/
    """
    pdf_name = Path(pdf_path).stem
    subject_code = extract_subject_code(pdf_name)
    base_dir = Path(get_json_output_root())

    if subject_code:
        md_dir = base_dir / subject_code / pdf_name / "markdown"
    else:
        md_dir = base_dir / "MISC" / pdf_name / "markdown"

    md_dir.mkdir(parents=True, exist_ok=True)
    return md_dir


def is_already_converted(pdf_path: str) -> bool:
    """
    Check if a PDF has already been converted to Markdown.

    Returns True only if:
    1. The status file has an entry for this PDF
    2. The entry status is 'done'
    3. The file hash still matches (PDF hasn't been replaced)
    4. The markdown file still exists on disk
    """
    with _status_lock:
        status = _load_status()
        key = _get_pdf_key(pdf_path)

        if key not in status:
            return False

        entry = status[key]
        if entry.get('status') != 'done':
            return False

        # Check if markdown file still exists
        md_path = entry.get('markdown_path', '')
        if not md_path or not os.path.exists(md_path):
            return False

        # Check if PDF was replaced (hash mismatch)
        current_hash = _compute_file_hash(pdf_path)
        if current_hash and entry.get('file_hash') and current_hash != entry.get('file_hash'):
            return False

        return True


def get_markdown_path(pdf_path: str) -> Optional[str]:
    """
    Get the path to the existing Markdown file for a PDF.
    Returns None if not converted yet.
    """
    if not is_already_converted(pdf_path):
        return None

    with _status_lock:
        status = _load_status()
        key = _get_pdf_key(pdf_path)
        return status.get(key, {}).get('markdown_path')


def get_conversion_status() -> Dict[str, Any]:
    """Get the full conversion status dictionary for UI display."""
    with _status_lock:
        return _load_status()


def get_conversion_summary() -> Dict[str, int]:
    """
    Get a summary of conversion status.
    Returns: {'total': N, 'done': N, 'pending': N, 'failed': N}
    """
    status = _load_status()
    summary = {'total': len(status), 'done': 0, 'pending': 0, 'failed': 0}
    for entry in status.values():
        s = entry.get('status', 'pending')
        if s in summary:
            summary[s] += 1
        else:
            summary['pending'] += 1
    return summary


def convert_single_pdf(pdf_path: str, force: bool = False,
                       log_callback=None) -> Optional[str]:
    """
    Convert a single PDF to high-fidelity Markdown.

    Args:
        pdf_path: Full path to the PDF file
        force: If True, re-convert even if already done
        log_callback: Optional callback(message, level) for progress logging

    Returns:
        Path to the generated .md file, or None on failure
    """
    def log(msg, level="info"):
        if log_callback:
            log_callback(msg, level)
        else:
            print(f"[MD Converter] {msg}")

    pdf_path_str = str(pdf_path)
    pdf_name = Path(pdf_path_str).stem

    # Check if already converted
    if not force and is_already_converted(pdf_path_str):
        existing_path = get_markdown_path(pdf_path_str)
        log(f"✓ Already converted: {pdf_name}", "info")
        return existing_path

    log(f"📄 Converting to Markdown: {pdf_name}", "info")

    # Determine output path
    md_dir = _get_markdown_dir(pdf_path_str)
    md_path = md_dir / f"{pdf_name}.md"

    # Compute file hash for tracking
    file_hash = _compute_file_hash(pdf_path_str)

    # Get total pages for tracking
    import fitz
    total_pages = 0
    try:
        doc = fitz.open(pdf_path_str)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        log(f"❌ Cannot open PDF: {e}", "error")
        return None

    # Attempt 1: Use pymupdf4llm for high-fidelity conversion
    markdown_text = None
    try:
        import pymupdf4llm
        log(f"   Using pymupdf4llm for high-fidelity conversion ({total_pages} pages)...", "info")
        markdown_text = pymupdf4llm.to_markdown(pdf_path_str)
        log(f"   ✓ pymupdf4llm conversion complete ({len(markdown_text)} chars)", "success")
    except ImportError:
        log("   ⚠️ pymupdf4llm not installed, falling back to basic extraction", "warning")
    except Exception as e:
        log(f"   ⚠️ pymupdf4llm failed: {e}, falling back to basic extraction", "warning")

    # Attempt 2: Fallback to basic fitz text extraction
    if markdown_text is None:
        try:
            log(f"   Using basic PyMuPDF extraction ({total_pages} pages)...", "info")
            doc = fitz.open(pdf_path_str)
            pages_md = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                if text.strip():
                    pages_md.append(f"<!-- Page {page_num + 1} -->\n\n{text.strip()}")
            doc.close()
            markdown_text = "\n\n---\n\n".join(pages_md)
            log(f"   ✓ Basic extraction complete ({len(markdown_text)} chars)", "success")
        except Exception as e:
            log(f"❌ PDF extraction failed: {e}", "error")
            # Update status as failed
            with _status_lock:
                status = _load_status()
                status[_get_pdf_key(pdf_path_str)] = {
                    'source_pdf': pdf_path_str,
                    'markdown_path': '',
                    'total_pages': total_pages,
                    'converted_at': datetime.now().isoformat(),
                    'file_hash': file_hash,
                    'status': 'failed',
                    'error': str(e)
                }
                _save_status(status)
            return None

    # Write markdown file
    try:
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_text)
        log(f"   💾 Saved: {md_path}", "success")
    except Exception as e:
        log(f"❌ Failed to write Markdown file: {e}", "error")
        return None

    # Update tracking status
    with _status_lock:
        status = _load_status()
        status[_get_pdf_key(pdf_path_str)] = {
            'source_pdf': pdf_path_str,
            'markdown_path': str(md_path),
            'total_pages': total_pages,
            'converted_at': datetime.now().isoformat(),
            'file_hash': file_hash,
            'status': 'done'
        }
        _save_status(status)

    log(f"✅ Conversion complete: {pdf_name} ({total_pages} pages → {len(markdown_text)} chars)", "success")
    return str(md_path)


def convert_multiple_pdfs(pdf_paths: List[str], force: bool = False,
                          log_callback=None, progress_callback=None) -> Dict[str, Optional[str]]:
    """
    Convert multiple PDFs to Markdown.

    Args:
        pdf_paths: List of PDF file paths
        force: If True, re-convert even if already done
        log_callback: Optional callback(message, level)
        progress_callback: Optional callback(current, total)

    Returns:
        Dictionary of {pdf_path: md_path_or_None}
    """
    results = {}
    total = len(pdf_paths)

    for i, pdf_path in enumerate(pdf_paths, 1):
        if progress_callback:
            progress_callback(i, total)

        md_path = convert_single_pdf(pdf_path, force=force, log_callback=log_callback)
        results[pdf_path] = md_path

    return results
