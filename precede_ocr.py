"""
Precede OCR - Single-file PDF ID extraction pipeline.

Extracts 5-digit numeric Precede IDs from PDF pages using multi-rotation OCR.
Outputs structured CSV mapping each ID to its source filename and page number.
"""

import re
import sys
import shutil
import tempfile
from pathlib import Path
from PIL import Image
import pytesseract
import pandas as pd
from pdf2image import convert_from_path

# Configure Tesseract path (not in PATH on Windows)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Poppler is in PATH, so no explicit path needed
POPPLER_PATH = None


def normalize_digits(text: str) -> str:
    """
    Normalize common OCR digit confusion characters.

    Handles look-alike characters that Tesseract may misread:
    - O/o -> 0
    - I/l/| -> 1
    - S/s -> 5
    - B/b -> 8
    - Z -> 2

    Args:
        text: Raw OCR text output

    Returns:
        Text with confused characters normalized to digits
    """
    mapping = {
        'O': '0', 'o': '0',
        'I': '1', 'l': '1', '|': '1',
        'S': '5', 's': '5',
        'B': '8', 'b': '8',
        'Z': '2'
    }

    for char, digit in mapping.items():
        text = text.replace(char, digit)

    return text


def select_most_likely_id(matches: list[str]) -> str | None:
    """
    Select most likely Precede ID when multiple 5-digit numbers found.

    Per user decision D-03: Filter out trivial/repeating patterns like
    00000, 11111, etc. If multiple valid candidates remain, select first.

    Args:
        matches: List of 5-digit strings from regex matching

    Returns:
        Most likely ID string, or None if no valid candidates
    """
    # Filter out obvious noise patterns (repeating digits)
    trivial_patterns = {
        '00000', '11111', '22222', '33333', '44444',
        '55555', '66666', '77777', '88888', '99999'
    }

    filtered = [m for m in matches if m not in trivial_patterns]

    if filtered:
        # Return first valid candidate
        return filtered[0]
    elif matches:
        # If all matches were trivial but matches existed, return first original
        return matches[0]
    else:
        # No matches at all
        return None


def extract_id_with_rotation(image: Image.Image) -> tuple[str | None, int | None]:
    """
    Extract 5-digit ID by trying OCR at all 4 rotations with early exit.

    Per user decision D-04: Try rotations 0, 90, 180, 270 degrees sequentially.
    Exit loop on first valid 5-digit match (saves 75% compute vs. trying all).

    Uses PSM 6 (uniform text block) as middle ground for full-page scans with
    isolated IDs. OEM 3 (LSTM engine). Digit whitelist restricts output.

    Args:
        image: PIL Image at 300 DPI

    Returns:
        Tuple of (id_string, rotation_angle) or (None, None) if no match
    """
    for angle in [0, 90, 180, 270]:
        # Rotate image (expand=True prevents cropping)
        if angle == 0:
            rotated_image = image
        else:
            rotated_image = image.rotate(angle, expand=True)

        # Tesseract config: PSM 6, LSTM engine, digits only
        config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'

        # Run OCR
        text = pytesseract.image_to_string(rotated_image, config=config).strip()

        # Normalize digit confusion characters
        normalized_text = normalize_digits(text)

        # Find 5-digit numbers with word boundaries
        matches = re.findall(r'\b\d{5}\b', normalized_text)

        if matches:
            # Early exit on first valid match
            selected_id = select_most_likely_id(matches)
            if selected_id is not None:
                return selected_id, angle

    # No match found after all rotations
    return None, None


def process_single_pdf(pdf_path: str) -> list[dict]:
    """
    End-to-end pipeline for one PDF file.

    Implements PIPE-01 (single file), PIPE-02 (300 DPI), PIPE-04 (regex),
    PIPE-05 (mapping), per user decisions D-04 (rotation), D-06 (all pages).

    Steps:
    1. Convert PDF to 300 DPI images (disk-backed to prevent OOM)
    2. For each page: run multi-rotation OCR to extract ID
    3. Record result for every page (even pages with no ID found)
    4. Clean up temporary image files

    Args:
        pdf_path: Path to PDF file

    Returns:
        List of dicts with keys: filename, page, id, rotation_detected
    """
    # Create temporary directory for image files
    temp_dir = tempfile.mkdtemp(prefix='precede_ocr_')

    # Extract filename for output
    filename = Path(pdf_path).name

    try:
        # Convert PDF to images (memory-safe: disk-backed, paths only)
        image_paths = convert_from_path(
            pdf_path,
            dpi=300,                    # PIPE-02: 300+ DPI for reliable digits
            output_folder=temp_dir,     # Pitfall 1: disk-backed, not RAM
            paths_only=True,            # Pitfall 1: returns file paths, prevents OOM
            fmt='png',                  # Lossless format preserves OCR quality
            poppler_path=POPPLER_PATH   # None if in PATH, else explicit path
        )

        # Process each page
        results = []
        for page_num, image_path in enumerate(image_paths, start=1):
            # Open image with context manager for proper cleanup (Pitfall 5)
            with Image.open(image_path) as img:
                # Extract ID with multi-rotation OCR
                id_found, rotation = extract_id_with_rotation(img)

                # Record result (D-06: row for EVERY page, even no-match)
                results.append({
                    'filename': filename,
                    'page': page_num,
                    'id': id_found,           # None if no match - will be blank in CSV
                    'rotation_detected': rotation if id_found else None
                })

        return results

    finally:
        # Cleanup temp directory (ignore errors if files already removed)
        shutil.rmtree(temp_dir, ignore_errors=True)


def write_results_csv(results: list[dict], output_path: str) -> None:
    """
    Write results to CSV per OUT-01 and D-07.

    Creates CSV with explicit column order: filename, page, id, rotation_detected.
    Includes summary statistics on stdout.

    Args:
        results: List of dicts from process_single_pdf()
        output_path: Path to output CSV file
    """
    # Create output directory if needed
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Create DataFrame
    df = pd.DataFrame(results)

    # Enforce column order per D-07
    df = df[['filename', 'page', 'id', 'rotation_detected']]

    # Write CSV (index=False excludes row numbers)
    df.to_csv(output_path, index=False)

    # Print summary
    total_pages = len(df)
    ids_found = df['id'].notna().sum()
    no_id = df['id'].isna().sum()

    print(f"Results written to {output_path}")
    print(f"Total pages scanned: {total_pages}")
    print(f"IDs found: {ids_found}")
    print(f"Pages with no ID: {no_id}")


if __name__ == '__main__':
    # Parse command-line arguments
    if len(sys.argv) < 2:
        print("Usage: python precede_ocr.py <pdf_path> [output_csv_path]")
        print()
        print("Examples:")
        print("  python precede_ocr.py test.pdf")
        print('  python precede_ocr.py "C:\\path\\to\\document.pdf" "output/my_results.csv"')
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else 'output/results.csv'

    # Validate PDF file exists
    if not Path(pdf_path).is_file():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    # Run pipeline
    print(f"Processing {pdf_path}...")
    results = process_single_pdf(pdf_path)
    write_results_csv(results, output_path)
    print("Done.")
