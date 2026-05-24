"""
Folder Organizer Module
Handles intelligent folder organization for JSON output files.

DIRECTORY STRUCTURE (inside ~/Documents/):
══════════════════════════════════════════════════════════════════
  vu-all-JSON/              → MCQ & Short Notes JSON files + Reviews
  │                           Organized by subject: {subject_code}/{pdf_name}/mids/
  │                           Reviews stored as: {subject_code}/reviews_mids.json
  │
  vu-generated-PDFs/        → Generated PDF files from JSON
  │                           Flat structure: {pdf_name}.pdf
  │
══════════════════════════════════════════════════════════════════

IMPORTANT FOR FUTURE AI AGENTS:
  - json_output_root  → ONLY for MCQ/Short Notes JSON + reviews
  - pdf_output_root   → ONLY for generated PDFs
  - NEVER mix these paths
  - Reviews are stored INSIDE json_output_root but are excluded
    from PDF generation scans via filename pattern (reviews_*.json)
  - Use get_json_output_root() for MCQ/review storage
  - Use get_pdf_output_root() for generated PDF storage
"""

import re
import json
from pathlib import Path
from typing import Optional

# Default organized output directories (inside ~/Documents/)
DEFAULT_ORGANIZED_BASE_DIR = str(Path.home() / "Documents" / "vu-all-JSON")
DEFAULT_PDF_OUTPUT_DIR = str(Path.home() / "Documents" / "vu-generated-PDFs")

# Predefined subject codes
PREDEFINED_SUBJECTS = [
    'ACC', 'BIF', 'BIO', 'BIT', 'BNK', 'BT', 'CHE', 'CS', 'ECO', 'EDU',
    'ENG', 'ETH', 'FIN', 'GSC', 'HRM', 'ISL', 'IT', 'MCD', 'MCM', 'MGMT',
    'MGT', 'MKT', 'MTH', 'PAD', 'PAK', 'PHY', 'PSC', 'SOC', 'STA', 'URD', 'ZOO'
]


def get_json_output_root() -> str:
    """
    Get the JSON output root directory from config.
    Falls back to default if not configured.
    
    Returns:
        Path string to the output root directory
    """
    try:
        config_path = Path(__file__).parent / 'config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            custom_root = config.get('json_output_root', '').strip()
            if custom_root and Path(custom_root).exists():
                return custom_root
    except Exception:
        pass
    
    return DEFAULT_ORGANIZED_BASE_DIR


def get_pdf_output_root() -> str:
    """
    Get the PDF output root directory from config.
    Falls back to ~/Documents/vu-generated-PDFs if not configured.
    
    This is the DEDICATED folder for generated PDFs only.
    It is SEPARATE from the JSON output root.
    
    Returns:
        Path string to the PDF output root directory
    """
    try:
        config_path = Path(__file__).parent / 'config.json'
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
            custom_root = config.get('pdf_output_root', '').strip()
            if custom_root and Path(custom_root).exists():
                return custom_root
    except Exception:
        pass
    
    # Create default directory if it doesn't exist
    default_path = Path(DEFAULT_PDF_OUTPUT_DIR)
    default_path.mkdir(parents=True, exist_ok=True)
    return str(default_path)


def extract_subject_code(pdf_name: str) -> Optional[str]:
    """
    Extract subject code from PDF name.
    
    Examples:
        CS101 -> CS
        MGT101 -> MGT
        BIO202 -> BIO
        MGMT301 -> MGMT
        random_file -> None
    
    Args:
        pdf_name: Name of the PDF (without extension)
    
    Returns:
        Subject code if found, None otherwise
    """
    # Try to match pattern: letters followed by numbers
    match = re.match(r'^([A-Z]+)\d+', pdf_name.upper())
    
    if match:
        subject_code = match.group(1)
        if subject_code in PREDEFINED_SUBJECTS:
            return subject_code
    
    return None


def get_organized_path(pdf_name: str, pdf_source_path: str) -> Path:
    """
    Get the organized output path for JSON files.
    
    Logic:
    1. Extract subject code from PDF name
    2. If subject code matches predefined list:
       Return organized path under configured JSON output root
    3. If subject code doesn't match:
       Return path in same directory as source PDF
    
    Args:
        pdf_name: Name of the PDF (without extension)
        pdf_source_path: Full path to the source PDF file
    
    Returns:
        Path object for the organized output directory
    """
    subject_code = extract_subject_code(pdf_name)
    base_dir = get_json_output_root()
    
    if subject_code:
        organized_path = Path(base_dir) / subject_code / pdf_name
        print(f"📂 Using organized path: {organized_path}")
        print(f"   Subject: {subject_code}")
        return organized_path
    else:
        # Fallback: same directory as source PDF
        source_dir = Path(pdf_source_path).parent
        fallback_path = source_dir / f"{pdf_name}_JSON"
        print(f"📂 Subject not recognized, using fallback path: {fallback_path}")
        return fallback_path


def scan_root_folder(root_path: str) -> dict:
    """
    Scan a root folder for subfolders containing PDFs.
    
    Args:
        root_path: Path to the root folder
    
    Returns:
        Dictionary with:
        - 'categories': {subfolder_name: [list of pdf paths]}
        - 'all_pdfs': [flat list of all pdf paths]
        - 'total': total PDF count
    """
    root = Path(root_path)
    if not root.exists():
        return {'categories': {}, 'all_pdfs': [], 'total': 0}
    
    categories = {}
    all_pdfs = []
    
    # Check root level PDFs
    root_pdfs = sorted([str(f) for f in root.glob('*.pdf')])
    if root_pdfs:
        categories['Root'] = root_pdfs
        all_pdfs.extend(root_pdfs)
    
    # Check subfolders
    for subfolder in sorted(root.iterdir()):
        if subfolder.is_dir():
            pdfs = sorted([str(f) for f in subfolder.glob('*.pdf')])
            if pdfs:
                categories[subfolder.name] = pdfs
                all_pdfs.extend(pdfs)
    
    return {
        'categories': categories,
        'all_pdfs': all_pdfs,
        'total': len(all_pdfs)
    }


def extract_full_subject_code(pdf_name: str) -> str:
    """
    Extract full subject code with number from PDF name.
    
    Examples:
        CS101_handouts.pdf -> CS101
        MGT501 Final.pdf -> MGT501
        random_file.pdf -> MISC
    
    Args:
        pdf_name: Name of the PDF (with or without extension)
    
    Returns:
        Full subject code (e.g., 'CS101', 'MGT501') or 'MISC'
    """
    # Remove extension if present
    name = Path(pdf_name).stem.upper()
    
    # Try to match pattern: letters followed by numbers
    match = re.match(r'^([A-Z]+\d+)', name)
    if match:
        return match.group(1)
    
    return 'MISC'


def build_index_map(pdf_paths: list) -> dict:
    """
    Build a stable unique index map for a list of PDF paths.
    
    Each PDF gets a permanent ID based on its subject prefix + sequential number.
    Examples: CS01, CS02, MCM01, MGT01, MGT02, MISC01
    
    The IDs are stable because they are based on the subject prefix grouping
    and alphabetical ordering within each group.
    
    Args:
        pdf_paths: List of PDF file paths
    
    Returns:
        Dictionary of {pdf_path: stable_id}
    """
    # Group PDFs by subject prefix
    prefix_groups = {}
    for pdf_path in pdf_paths:
        pdf_name = Path(pdf_path).stem
        full_code = extract_full_subject_code(pdf_name)
        
        # Get just the letter prefix (CS, MGT, MCM, etc.)
        prefix_match = re.match(r'^([A-Z]+)', full_code)
        prefix = prefix_match.group(1) if prefix_match else 'MISC'
        
        if prefix not in prefix_groups:
            prefix_groups[prefix] = []
        prefix_groups[prefix].append(pdf_path)
    
    # Sort within each group for stability
    for prefix in prefix_groups:
        prefix_groups[prefix].sort(key=lambda p: Path(p).name.upper())
    
    # Assign stable IDs
    index_map = {}
    for prefix in sorted(prefix_groups.keys()):
        for i, pdf_path in enumerate(prefix_groups[prefix], 1):
            stable_id = f"{prefix}{i:02d}"
            index_map[pdf_path] = stable_id
    
    return index_map


def get_processed_pdf_status(pdf_name: str) -> dict:
    """
    Check the processing status of a PDF by looking for existing output JSON files.
    
    Checks the organized JSON output folder for:
    - Mids MCQs file
    - Finals MCQs file
    - Mids Short Notes file
    - Finals Short Notes file
    
    Args:
        pdf_name: PDF name without extension (e.g., 'CS101 handouts_1')
    
    Returns:
        Dictionary with:
        {
            'mids_mcqs': int (count or 0),
            'finals_mcqs': int (count or 0),
            'mids_notes': int (count or 0),
            'finals_notes': int (count or 0),
            'mids_processed': bool,
            'finals_processed': bool,
        }
    """
    import json as _json
    
    result = {
        'mids_mcqs': 0,
        'finals_mcqs': 0,
        'mids_notes': 0,
        'finals_notes': 0,
        'mids_processed': False,
        'finals_processed': False,
    }
    
    subject_code = extract_subject_code(pdf_name)
    base_dir = Path(get_json_output_root())
    
    if subject_code:
        pdf_folder = base_dir / subject_code / pdf_name
    else:
        # Fallback — can't determine path without full source path
        return result
    
    if not pdf_folder.exists():
        return result
    
    # Check mids
    mids_folder = pdf_folder / "mids"
    if mids_folder.exists():
        # MCQs
        mcq_file = mids_folder / f"{pdf_name}_mids_mcqs.json"
        if mcq_file.exists():
            try:
                with open(mcq_file, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                if isinstance(data, list):
                    result['mids_mcqs'] = len(data)
                    result['mids_processed'] = True
            except Exception:
                pass
        
        # Short Notes
        notes_file = mids_folder / f"short note {pdf_name}_mids.json"
        if notes_file.exists():
            try:
                with open(notes_file, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                if isinstance(data, list):
                    result['mids_notes'] = len(data)
                    result['mids_processed'] = True
            except Exception:
                pass
    
    # Check finals
    finals_folder = pdf_folder / "finals"
    if finals_folder.exists():
        # MCQs
        mcq_file = finals_folder / f"{pdf_name}_finals_mcqs.json"
        if mcq_file.exists():
            try:
                with open(mcq_file, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                if isinstance(data, list):
                    result['finals_mcqs'] = len(data)
                    result['finals_processed'] = True
            except Exception:
                pass
        
        # Short Notes
        notes_file = finals_folder / f"short note {pdf_name}_finals.json"
        if notes_file.exists():
            try:
                with open(notes_file, 'r', encoding='utf-8') as f:
                    data = _json.load(f)
                if isinstance(data, list):
                    result['finals_notes'] = len(data)
                    result['finals_processed'] = True
            except Exception:
                pass
    
    return result


def scan_all_processed_pdfs() -> list:
    """
    Scan the JSON output root for all processed PDFs.
    
    Returns:
        List of dicts:
        [
            {
                'pdf_name': str,
                'subject_code': str,
                'index_code': str (e.g., 'CS01' — placeholder, assigned later),
                'mids_mcqs': int,
                'finals_mcqs': int,
                'mids_notes': int,
                'finals_notes': int,
                'mids_processed': bool,
                'finals_processed': bool,
            }
        ]
    """
    import json as _json
    
    base_dir = Path(get_json_output_root())
    results = []
    
    if not base_dir.exists():
        return results
    
    for subject_dir in sorted(base_dir.iterdir()):
        if not subject_dir.is_dir():
            continue
        
        subject_code = subject_dir.name
        
        # Skip reviews-only folders and non-subject folders
        if subject_code.startswith('.') or subject_code.startswith('_'):
            continue
        
        for pdf_folder in sorted(subject_dir.iterdir()):
            if not pdf_folder.is_dir():
                continue
            
            pdf_name = pdf_folder.name
            
            # Skip if it's a reviews file
            if pdf_name.startswith('reviews'):
                continue
            
            status = get_processed_pdf_status(pdf_name)
            
            # Only include if actually processed
            if status['mids_processed'] or status['finals_processed']:
                results.append({
                    'pdf_name': pdf_name,
                    'subject_code': subject_code,
                    'index_code': '',  # Will be assigned by caller if needed
                    **status
                })
    
    return results
