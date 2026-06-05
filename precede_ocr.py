"""
Precede OCR - Single-file PDF ID extraction pipeline.

Extracts 5-digit numeric Precede IDs from PDF pages using multi-rotation OCR.
Outputs structured CSV and JSON mapping each ID to its source filename and page number.
"""

import re
import sys
import json
import argparse
import shutil
import tempfile
from pathlib import Path
from collections import defaultdict
from PIL import Image
import pytesseract
import pandas as pd
from pdf2image import convert_from_path

# Configure Tesseract path (auto-detect common Windows locations)
TESSERACT_SEARCH_PATHS = [
    Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe'),
    Path.home() / 'Tesseract-OCR' / 'tesseract.exe',
    Path(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'),
]

for _tess_path in TESSERACT_SEARCH_PATHS:
    if _tess_path.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(_tess_path)
        break
else:
    # Fall back to assuming it's in PATH
    pytesseract.pytesseract.tesseract_cmd = 'tesseract'

# Configure Poppler path (auto-detect common Windows locations)
# Poppler-for-Windows often installs with versioned subdirs, e.g.
# ~/poppler/poppler-24.08.0/Library/bin/pdftoppm.exe
# So we search fixed paths first, then recursively search known roots.
_POPPLER_FIXED_PATHS = [
    Path.home() / 'poppler' / 'Library' / 'bin',
    Path.home() / 'poppler' / 'bin',
    Path.home() / 'poppler',
    Path(r'C:\Program Files\poppler\Library\bin'),
    Path(r'C:\Program Files\poppler\bin'),
]

POPPLER_PATH = None
# First: check fixed paths
for _pop_path in _POPPLER_FIXED_PATHS:
    if _pop_path.is_dir() and any(_pop_path.glob('pdftoppm*')):
        POPPLER_PATH = str(_pop_path)
        break

# Second: recursive search in common root directories for versioned installs
if POPPLER_PATH is None:
    for _pop_root in [Path.home() / 'poppler', Path(r'C:\Program Files\poppler')]:
        if _pop_root.is_dir():
            for _match in _pop_root.rglob('pdftoppm*'):
                POPPLER_PATH = str(_match.parent)
                break
        if POPPLER_PATH:
            break

if POPPLER_PATH is None:
    print("WARNING: Could not auto-detect Poppler. Searched:")
    for _p in _POPPLER_FIXED_PATHS:
        print(f"  {_p} (exists={_p.is_dir()})")
    print(f"  Recursive search in: {Path.home() / 'poppler'}")
    print("Set POPPLER_PATH manually in precede_ocr.py or add Poppler to PATH.")


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

    Deprecated: Use select_all_valid_ids() for multi-ID extraction.

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


def select_all_valid_ids(matches: list[str]) -> list[str]:
    """
    Filter and return ALL valid Precede IDs from matches.

    Per D-02: Return all valid candidates from the successful rotation.
    Per D-03: Filter trivial/repeating patterns (00000, 11111, etc.).
    Unlike select_most_likely_id, does NOT fall back to trivial matches.

    Args:
        matches: List of 5-digit strings from regex matching

    Returns:
        List of valid ID strings (may be empty)
    """
    trivial_patterns = {
        '00000', '11111', '22222', '33333', '44444',
        '55555', '66666', '77777', '88888', '99999'
    }
    return [m for m in matches if m not in trivial_patterns]


def classify_failure_reason(ocr_texts: list[str]) -> str:
    """
    Classify why no valid ID was found after trying all rotations.

    Args:
        ocr_texts: Raw OCR text from each rotation attempt

    Returns:
        Concise failure reason: 'no_text_detected', 'only_noise_matches',
        or 'no_match_any_rotation'
    """
    # Check if any rotation returned text
    has_any_text = any(text.strip() for text in ocr_texts)

    if not has_any_text:
        return 'no_text_detected'

    # Check if any rotation had 5-digit numbers (even if filtered as noise)
    all_normalized = [normalize_digits(text) for text in ocr_texts]
    all_matches = []
    for text in all_normalized:
        all_matches.extend(re.findall(r'\b\d{5}\b', text))

    if all_matches:
        return 'only_noise_matches'
    else:
        return 'no_match_any_rotation'


def extract_id_with_rotation(image: Image.Image, debug: bool = False) -> tuple[list[str], int | None, str]:
    """
    Extract 5-digit IDs by trying OCR at all 4 rotations with early exit.

    Per Phase 2 decisions D-08, D-09: Try rotations [90, 270, 0, 180] sequentially.
    Exit loop on first rotation that yields valid 5-digit matches (saves compute).
    90-first order eliminates false positives from 0-degree matches (page numbers, dates).

    Per Phase 3 D-02: Returns ALL valid IDs from the successful rotation, not just first.

    Uses PSM 6 (uniform text block) as middle ground for full-page scans with
    isolated IDs. OEM 3 (LSTM engine). Digit whitelist restricts output.

    Args:
        image: PIL Image at 300 DPI
        debug: If True, print raw OCR text to stderr for each rotation

    Returns:
        Tuple of (ids_list, rotation_angle, notes) where ids_list is a list of
        valid ID strings, and notes is '' for success or failure reason for no match
    """
    ocr_texts = []  # Collect OCR text for failure classification

    for angle in [90, 270, 0, 180]:  # D-08: Rotation order optimized
        # Rotate image (expand=True prevents cropping)
        if angle == 0:
            rotated_image = image
        else:
            rotated_image = image.rotate(angle, expand=True)

        # Tesseract config: PSM 6, LSTM engine, digits only
        config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'

        # Run OCR
        text = pytesseract.image_to_string(rotated_image, config=config).strip()

        # Collect OCR text for failure classification
        ocr_texts.append(text)

        # D-11: Debug output to stderr
        if debug:
            print(f"DEBUG [Rotation {angle}]: {repr(text)}", file=sys.stderr)

        # Normalize digit confusion characters
        normalized_text = normalize_digits(text)

        # Find 5-digit numbers with word boundaries
        matches = re.findall(r'\b\d{5}\b', normalized_text)

        if matches:
            # D-02: Return ALL valid IDs from this rotation
            selected_ids = select_all_valid_ids(matches)
            if selected_ids:
                return selected_ids, angle, ''  # D-09: Early exit with empty notes

    # D-12: No match found - classify failure reason
    reason = classify_failure_reason(ocr_texts)
    return [], None, reason


def process_single_pdf(pdf_path: str, debug: bool = False) -> list[dict]:
    """
    End-to-end pipeline for one PDF file.

    Implements PIPE-01 (single file), PIPE-02 (300 DPI), PIPE-04 (regex),
    PIPE-05 (mapping), PIPE-06 (multiple IDs per page), PIPE-07 (no-ID flagging).

    Steps:
    1. Convert PDF to 300 DPI images (disk-backed to prevent OOM)
    2. For each page: run multi-rotation OCR to extract all IDs
    3. Record result for every page (even pages with no ID found)
    4. Clean up temporary image files

    Args:
        pdf_path: Path to PDF file
        debug: If True, print raw OCR text to stderr for debugging

    Returns:
        List of dicts with keys: filename, page, ids, rotation_detected, notes
        where ids is a list of valid ID strings (may be empty for no-match pages)
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
                # Extract IDs with multi-rotation OCR
                ids_found, rotation, notes = extract_id_with_rotation(img, debug=debug)

                # Record result (D-06: row for EVERY page, even no-match)
                results.append({
                    'filename': filename,
                    'page': page_num,
                    'ids': ids_found,             # List of IDs (empty if no match)
                    'rotation_detected': rotation if ids_found else None,
                    'notes': notes                # D-12: Failure reason or empty string
                })

        return results

    finally:
        # Cleanup temp directory (ignore errors if files already removed)
        shutil.rmtree(temp_dir, ignore_errors=True)


def write_results_csv(results: list[dict], output_path: str) -> None:
    """
    Write results to CSV per OUT-01, D-01, and Phase 2 D-12.

    Per D-01: One row per ID. Same page appears in multiple rows when it has
    multiple IDs. Pages with no IDs get one row with blank id column.

    Creates CSV with explicit column order: filename, page, id, rotation_detected, notes.
    Includes summary statistics on stdout.

    Args:
        results: List of dicts from process_single_pdf() with 'ids' key (list)
        output_path: Path to output CSV file
    """
    # Create output directory if needed
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Flatten multi-ID results to one row per ID (D-01)
    flattened = []
    for r in results:
        if r['ids']:
            for id_val in r['ids']:
                flattened.append({
                    'filename': r['filename'],
                    'page': r['page'],
                    'id': id_val,
                    'rotation_detected': r['rotation_detected'],
                    'notes': r['notes']
                })
        else:
            flattened.append({
                'filename': r['filename'],
                'page': r['page'],
                'id': '',
                'rotation_detected': r['rotation_detected'],
                'notes': r['notes']
            })

    # Create DataFrame
    df = pd.DataFrame(flattened)

    # Enforce column order per D-12: includes notes column
    df = df[['filename', 'page', 'id', 'rotation_detected', 'notes']]

    # Write CSV (index=False excludes row numbers)
    df.to_csv(output_path, index=False)

    # Print summary
    total_pages = len(results)
    ids_found = sum(len(r['ids']) for r in results)
    no_id = sum(1 for r in results if not r['ids'])

    print(f"Results written to {output_path}")
    print(f"Total pages scanned: {total_pages}")
    print(f"IDs found: {ids_found}")
    print(f"Pages with no ID: {no_id}")


def write_results_json(results: list[dict], output_path: str) -> None:
    """
    Write results to nested JSON per OUT-02 and D-04.

    Structure: {"file.pdf": {"1": ["12345"], "2": ["67890", "11234"], "3": []}}
    Pages with no ID show as empty array (per D-04, PIPE-07).
    Page keys are strings (JSON keys must be strings).

    Args:
        results: List of dicts from process_single_pdf() with 'ids' key (list)
        output_path: Path to output JSON file
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    nested = defaultdict(dict)
    for row in results:
        filename = row['filename']
        page = str(row['page'])
        ids = row['ids']
        nested[filename][page] = ids

    with open(output_path, 'w') as f:
        json.dump(dict(nested), f, indent=2)

    print(f"JSON output written to {output_path}")


def print_rotation_summary(results: list[dict]) -> None:
    """
    Print rotation distribution summary to console per D-13.

    Shows count and percentage of pages at each rotation angle.
    Helps validate pipeline assumptions and detect scanner orientation issues.

    Args:
        results: List of dicts from process_single_pdf()
    """
    if not results:
        print("\nNo pages processed.")
        return

    df = pd.DataFrame(results)
    rotation_counts = df['rotation_detected'].value_counts(dropna=False)
    total_pages = len(df)

    print("\nRotation distribution:")
    for angle, count in rotation_counts.items():
        percentage = count / total_pages * 100
        if pd.notna(angle):
            label = f"{int(angle)} degrees"
        else:
            label = "No match"
        print(f"  {label}: {count} pages ({percentage:.1f}%)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract Precede IDs from PDF files')
    parser.add_argument('pdf_path', help='Path to input PDF file')
    parser.add_argument('output_path', nargs='?', default='output/results.csv',
                        help='Path to output CSV (default: output/results.csv)')
    parser.add_argument('--output-json', default=None,
                        help='Path to output JSON (default: same dir as CSV with .json extension)')
    parser.add_argument('--debug', action='store_true',
                        help='Print raw OCR text for each rotation to stderr')
    args = parser.parse_args()

    if not Path(args.pdf_path).is_file():
        print(f"Error: PDF file not found: {args.pdf_path}")
        sys.exit(1)

    print(f"Processing {args.pdf_path}...")
    results = process_single_pdf(args.pdf_path, debug=args.debug)
    write_results_csv(results, args.output_path)

    # Per D-05: always generate both CSV and JSON
    json_path = args.output_json
    if json_path is None:
        json_path = str(Path(args.output_path).with_suffix('.json'))
    write_results_json(results, json_path)

    print_rotation_summary(results)
    print("Done.")
