"""
Folder Organizer Module
Handles intelligent folder organization for JSON output files
"""

import re
import json
from pathlib import Path
from typing import Optional

# Default organized output directory
DEFAULT_ORGANIZED_BASE_DIR = str(Path.home() / "Documents" / "vu-all-JSON")

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
