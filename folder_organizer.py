"""
Folder Organizer Module
Handles intelligent folder organization for JSON output files
"""

import re
from pathlib import Path
from typing import Optional

# Main organized output directory
ORGANIZED_BASE_DIR = r"C:\Users\KLH\Documents\vu-all-JSON"

# Predefined subject codes
PREDEFINED_SUBJECTS = [
    'ACC', 'BIF', 'BIO', 'BIT', 'BNK', 'BT', 'CHE', 'CS', 'ECO', 'EDU',
    'ENG', 'ETH', 'FIN', 'GSC', 'HRM', 'ISL', 'IT', 'MCD', 'MCM', 'MGMT',
    'MGT', 'MKT', 'MTH', 'PAD', 'PAK', 'PHY', 'PSC', 'SOC', 'STA', 'URD', 'ZOO'
]


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
    # This handles cases like CS101, MGT101, MGMT301, etc.
    match = re.match(r'^([A-Z]+)\d+', pdf_name.upper())
    
    if match:
        subject_code = match.group(1)
        # Check if it's in our predefined list
        if subject_code in PREDEFINED_SUBJECTS:
            return subject_code
    
    return None


def get_organized_path(pdf_name: str, pdf_source_path: str) -> Path:
    """
    Get the organized output path for JSON files.
    
    Logic:
    1. Extract subject code from PDF name
    2. If subject code matches predefined list:
       Return organized path under vu-all-JSON folder
    3. If subject code doesn't match:
       Return path in same directory as source PDF
    
    Args:
        pdf_name: Name of the PDF (without extension)
        pdf_source_path: Full path to the source PDF file
    
    Returns:
        Path object for the organized output directory
    """
    subject_code = extract_subject_code(pdf_name)
    
    if subject_code:
        # Organized path: ORGANIZED_BASE_DIR/SUBJECT/PDF_NAME/
        organized_path = Path(ORGANIZED_BASE_DIR) / subject_code / pdf_name
        print(f"📂 Using organized path: {organized_path}")
        print(f"   Subject: {subject_code}")
        return organized_path
    else:
        # Fallback: same directory as source PDF
        source_dir = Path(pdf_source_path).parent
        fallback_path = source_dir / f"{pdf_name}_JSON"
        print(f"📂 Subject not recognized, using fallback path: {fallback_path}")
        return fallback_path


if __name__ == '__main__':
    # Test the module
    print("Testing folder_organizer module\n")
    
    # Test cases
    test_cases = [
        ("CS101", r"D:\Downloads\CS101.pdf"),
        ("MGT101", r"D:\Downloads\MGT101.pdf"),
        ("MGMT301", r"D:\Downloads\MGMT301.pdf"),
        ("BIO202", r"D:\Downloads\BIO202.pdf"),
        ("XYZ999", r"D:\Downloads\XYZ999.pdf"),  # Unrecognized
        ("random_file", r"D:\Downloads\random_file.pdf"),  # Unrecognized
    ]
    
    for pdf_name, pdf_path in test_cases:
        print(f"\nTest: {pdf_name}")
        print(f"Source: {pdf_path}")
        subject = extract_subject_code(pdf_name)
        print(f"Extracted subject: {subject}")
        path = get_organized_path(pdf_name, pdf_path)
        print(f"Output path: {path}")
        print("-" * 60)
