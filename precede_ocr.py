"""
Precede OCR - Batch PDF ID extraction pipeline with parallel processing.

Extracts 5-digit numeric Precede IDs from PDF pages using multi-rotation OCR.
Supports single file or directory of PDFs with multiprocessing parallelism.
Outputs structured CSV and JSON mapping each ID to its source filename and page number.
"""

import re
import sys
import json
import argparse
import shutil
import tempfile
import os
import time as time_module
import multiprocessing as mp
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from functools import wraps
from PIL import Image
from tqdm import tqdm
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

# Module-level config for multiprocessing workers (set by main before pool spawn)
_ERROR_LOG_PATH = None
_CHECKPOINT_FREQUENCY = 50


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


def discover_pdfs(input_path: str) -> list[Path]:
    """
    Recursively discover all PDF files in directory, or return single file.

    Args:
        input_path: Path to PDF file or directory

    Returns:
        List of Path objects for PDF files, sorted alphabetically

    Raises:
        FileNotFoundError: If path does not exist
        ValueError: If single file is not a PDF
    """
    path = Path(input_path)
    if path.is_file():
        if path.suffix.lower() == '.pdf':
            return [path]
        else:
            raise ValueError(f"Not a PDF file: {input_path}")
    elif path.is_dir():
        return sorted(path.glob('**/*.pdf'))
    else:
        raise FileNotFoundError(f"Path not found: {input_path}")


def retry_once(func):
    """Retry function once on any exception per D-11."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            time_module.sleep(0.5)
            return func(*args, **kwargs)
    return wrapper


def log_error_to_file(filename: str, error: Exception, error_log_path: Path) -> None:
    """Append error entry to errors.log per D-09."""
    timestamp = datetime.now().isoformat()
    error_type = type(error).__name__
    error_msg = str(error)
    log_entry = f"[{timestamp}] {filename} | {error_type}: {error_msg}\n"
    error_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(error_log_path, 'a') as f:
        f.write(log_entry)


def save_checkpoint_atomic(results: list[dict], processed_files: set[str],
                           input_path: str, checkpoint_path: Path,
                           checkpoint_frequency: int) -> None:
    """Atomically save checkpoint JSON per D-01, D-02, D-03."""
    checkpoint_data = {
        "metadata": {
            "version": "1.0",
            "input_path": input_path,
            "processed_count": len(processed_files),
            "timestamp": datetime.now().isoformat(),
            "checkpoint_frequency": checkpoint_frequency
        },
        "results": results,
        "processed_files": list(processed_files)
    }
    checkpoint_path = Path(checkpoint_path)
    temp_dir = checkpoint_path.parent
    with tempfile.NamedTemporaryFile(
        mode='w', dir=temp_dir, delete=False, suffix='.tmp', prefix='.checkpoint_'
    ) as tmp_file:
        json.dump(checkpoint_data, tmp_file, indent=2)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
        tmp_path = tmp_file.name
    os.replace(tmp_path, str(checkpoint_path))


def load_checkpoint_if_exists(output_dir: Path, input_path: str) -> tuple[list[dict], set[str]] | None:
    """Load checkpoint if exists per D-05, D-06, D-08."""
    checkpoint_path = Path(output_dir) / '.checkpoint.json'
    if not checkpoint_path.exists():
        return None
    try:
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        results = checkpoint['results']
        processed_files = set(checkpoint['processed_files'])
        metadata = checkpoint['metadata']
        print(f"Resuming from checkpoint: {len(processed_files)} files already processed")
        if metadata.get('input_path') != input_path:
            print(f"WARNING: Checkpoint was created for '{metadata.get('input_path')}'")
            print(f"         Now processing '{input_path}'")
            print(f"         New files will be processed; removed files skipped from re-processing.")
        return results, processed_files
    except (json.JSONDecodeError, KeyError) as e:
        print(f"WARNING: Corrupt checkpoint file, starting fresh: {e}")
        checkpoint_path.unlink(missing_ok=True)
        return None


def filter_remaining_pdfs(pdf_paths: list[Path], processed_files: set[str]) -> list[Path]:
    """Remove already-processed files from work queue per D-08."""
    return [p for p in pdf_paths if p.name not in processed_files]


def calculate_batch_stats(all_results: list[dict], checkpointed_count: int,
                          newly_processed_count: int, start_time: float) -> dict:
    """Calculate batch statistics per D-13, D-14."""
    duration = time_module.time() - start_time
    total_pages = len(all_results)
    ids_found = sum(len(r['ids']) for r in all_results)
    no_id_pages = sum(1 for r in all_results if not r['ids'] and 'error:' not in r.get('notes', ''))
    error_count = sum(1 for r in all_results if r['page'] == 0 and 'error:' in r.get('notes', ''))
    all_filenames = set(r['filename'] for r in all_results)
    error_filenames = set(r['filename'] for r in all_results if 'error:' in r.get('notes', ''))
    successful_files = len(all_filenames - error_filenames)
    total_files = len(all_filenames)
    files_per_sec = newly_processed_count / duration if duration > 0 else 0
    return {
        "summary": {
            "total_files": total_files,
            "successful": successful_files,
            "failed": error_count,
            "total_pages": total_pages,
            "ids_found": ids_found,
            "no_id_pages": no_id_pages,
            "error_count": error_count
        },
        "performance": {
            "wall_clock_duration_sec": round(duration, 2),
            "files_per_second": round(files_per_sec, 2)
        },
        "resume_context": {
            "previously_checkpointed": checkpointed_count,
            "newly_processed": newly_processed_count
        },
        "timestamp": datetime.now().isoformat()
    }


def print_batch_stats(stats: dict) -> None:
    """Print summary to console per D-12."""
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)
    s = stats['summary']
    print(f"Total files:        {s['total_files']}")
    print(f"  Successful:       {s['successful']}")
    print(f"  Failed:           {s['failed']}")
    print(f"Total pages:        {s['total_pages']}")
    print(f"  IDs found:        {s['ids_found']}")
    print(f"  No-ID pages:      {s['no_id_pages']}")
    p = stats['performance']
    print(f"\nDuration:           {p['wall_clock_duration_sec']}s")
    print(f"Processing rate:    {p['files_per_second']:.2f} files/sec")
    r = stats['resume_context']
    if r['previously_checkpointed'] > 0:
        print(f"\nResumed from checkpoint:")
        print(f"  Previously done:  {r['previously_checkpointed']} files")
        print(f"  Newly processed:  {r['newly_processed']} files")
    print("=" * 60)


def _process_single_pdf_with_retry(pdf_path_str: str, debug: bool = False) -> list[dict]:
    """Core processing wrapped with retry_once decorator."""
    return process_single_pdf(pdf_path_str, debug=debug)


_process_single_pdf_with_retry = retry_once(_process_single_pdf_with_retry)


def process_single_pdf_wrapper(pdf_path: Path) -> list[dict]:
    """
    Wrapper for multiprocessing: retry once, log errors per D-09/D-10/D-11.

    Must be top-level function for Windows spawn pickling.
    Uses module-level _ERROR_LOG_PATH set by main() before pool creation.
    """
    try:
        results = _process_single_pdf_with_retry(str(pdf_path), debug=False)
        return results
    except Exception as e:
        # Log to errors.log (D-09)
        if _ERROR_LOG_PATH is not None:
            log_error_to_file(pdf_path.name, e, Path(_ERROR_LOG_PATH))

        # Return error dict for CSV notes column (D-10)
        return [{
            'filename': pdf_path.name,
            'page': 0,
            'ids': [],
            'rotation_detected': None,
            'notes': f'error: {type(e).__name__}: {str(e)}'
        }]


def process_all_pdfs(pdf_paths: list[Path], workers: int,
                     checkpointed_results: list[dict] | None = None,
                     checkpoint_path: Path | None = None,
                     input_path: str = '',
                     checkpoint_frequency: int = 50) -> list[dict]:
    """
    Process all PDFs in parallel with progress bar, running stats, and periodic checkpointing.

    Per D-03: Saves checkpoint every checkpoint_frequency files (default 50).
    Per D-04: Returns merged results (checkpointed + newly processed).
    Per D-14: Tracks resume-aware metrics (checkpointed vs newly processed counts).

    Args:
        pdf_paths: List of REMAINING PDF file paths (already filtered)
        workers: Number of worker processes
        checkpointed_results: Previously checkpointed results to merge (default: empty)
        checkpoint_path: Path to .checkpoint.json file (None = no checkpointing)
        input_path: Original input path string (stored in checkpoint metadata)
        checkpoint_frequency: Save checkpoint every N files (default 50, per D-03 Claude's discretion)

    Returns:
        Flat list of ALL result dicts (checkpointed + new)
    """
    if checkpointed_results is None:
        checkpointed_results = []

    all_results = list(checkpointed_results)  # Copy to avoid mutating input
    processed_files = {r['filename'] for r in checkpointed_results}
    files_since_checkpoint = 0
    stats = {'ids': 0, 'no_id_pages': 0, 'errors': 0}

    # Calculate total for progress bar (remaining + already done)
    total_files = len(pdf_paths) + len(checkpointed_results)

    chunksize = max(1, len(pdf_paths) // (4 * workers))

    with mp.Pool(processes=workers, maxtasksperchild=50) as pool:
        pbar = tqdm(
            total=total_files,
            initial=len(checkpointed_results),  # Resume offset
            desc="Processing PDFs",
            unit="file"
        )

        for file_results in pool.imap_unordered(
            process_single_pdf_wrapper,
            pdf_paths,
            chunksize=chunksize
        ):
            all_results.extend(file_results)

            # Track processed file
            if file_results:
                processed_files.add(file_results[0]['filename'])
            files_since_checkpoint += 1

            # Update running stats (D-09)
            for r in file_results:
                if r['page'] == 0 and 'error:' in r.get('notes', ''):
                    stats['errors'] += 1
                elif r['ids']:
                    stats['ids'] += len(r['ids'])
                else:
                    stats['no_id_pages'] += 1

            # Periodic checkpoint save (per D-03: every checkpoint_frequency files)
            if checkpoint_path and files_since_checkpoint >= checkpoint_frequency:
                save_checkpoint_atomic(
                    all_results, processed_files, input_path,
                    checkpoint_path, checkpoint_frequency
                )
                files_since_checkpoint = 0

            pbar.update(1)
            pbar.set_postfix({
                'IDs': stats['ids'],
                'No-ID': stats['no_id_pages'],
                'Errors': stats['errors']
            })

        pbar.close()

    # Final checkpoint save (ensure all results persisted)
    if checkpoint_path:
        save_checkpoint_atomic(
            all_results, processed_files, input_path,
            checkpoint_path, checkpoint_frequency
        )

    return all_results


def main(input_path: str, output_csv: str, output_json: str | None = None,
         workers: int | None = None, debug: bool = False, fresh: bool = False) -> None:
    """
    Main entry point: discover PDFs, handle checkpoint/resume, process, write outputs + stats.

    Args:
        input_path: Path to PDF file or directory of PDFs
        output_csv: Path to output CSV file
        output_json: Path to output JSON file (default: CSV path with .json extension)
        workers: Number of parallel workers (None = cpu_count()-1 for dirs, 1 for single file)
        debug: Enable debug OCR output to stderr (single file only)
        fresh: Delete existing checkpoint and start from scratch (D-07)
    """
    global _ERROR_LOG_PATH

    # Determine output directory from CSV path
    output_dir = Path(output_csv).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / '.checkpoint.json'
    error_log_path = output_dir / 'errors.log'
    stats_path = output_dir / 'batch_stats.json'

    # Set module-level error log path for workers
    _ERROR_LOG_PATH = str(error_log_path)

    # D-07: --fresh flag deletes checkpoint and error log
    if fresh:
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            print("Deleted existing checkpoint (--fresh mode)")
        if error_log_path.exists():
            error_log_path.unlink()
            print("Deleted existing error log (--fresh mode)")

    # Discover PDF files
    pdf_paths = discover_pdfs(input_path)

    if not pdf_paths:
        print(f"No PDF files found in {input_path}")
        return

    print(f"Found {len(pdf_paths)} PDF file(s)")

    # Determine JSON output path (D-05: always generate both)
    if output_json is None:
        output_json = str(Path(output_csv).with_suffix('.json'))

    # D-05: Auto-detect checkpoint for resume
    checkpointed_results = []
    processed_files = set()
    if not fresh:
        checkpoint_data = load_checkpoint_if_exists(output_dir, input_path)
        if checkpoint_data:
            checkpointed_results, processed_files = checkpoint_data
            pdf_paths = filter_remaining_pdfs(pdf_paths, processed_files)
            if not pdf_paths:
                print("All files already processed. Use --fresh to reprocess.")
                # Still write outputs from checkpoint data
                all_results = checkpointed_results
                write_results_csv(all_results, output_csv)
                write_results_json(all_results, output_json)
                print_rotation_summary(all_results)
                print("Done.")
                return

    # Start timing for batch stats
    start_time = time_module.time()

    # Single file: process directly (preserves debug mode, no checkpointing needed)
    if len(pdf_paths) == 1 and not checkpointed_results:
        print(f"Processing {pdf_paths[0].name}...")
        try:
            all_results = _process_single_pdf_with_retry(str(pdf_paths[0]), debug=debug)
        except Exception as e:
            log_error_to_file(pdf_paths[0].name, e, error_log_path)
            all_results = [{
                'filename': pdf_paths[0].name,
                'page': 0,
                'ids': [],
                'rotation_detected': None,
                'notes': f'error: {type(e).__name__}: {str(e)}'
            }]
    else:
        # Multiple files (or resuming): parallel processing with checkpointing
        if workers is None:
            workers = max(1, mp.cpu_count() - 1)
        print(f"Processing {len(pdf_paths)} remaining file(s) with {workers} workers...")
        all_results = process_all_pdfs(
            pdf_paths, workers=workers,
            checkpointed_results=checkpointed_results,
            checkpoint_path=checkpoint_path,
            input_path=input_path,
            checkpoint_frequency=_CHECKPOINT_FREQUENCY
        )

    # Write outputs (D-04: merged checkpointed + new results)
    write_results_csv(all_results, output_csv)
    write_results_json(all_results, output_json)
    print_rotation_summary(all_results)

    # D-12, D-13, D-14: Batch statistics (console + JSON file)
    # Per D-14: resume-aware stats distinguish previously-checkpointed vs newly-processed
    newly_processed_count = len(set(r['filename'] for r in all_results)) - len(
        set(r['filename'] for r in checkpointed_results)) if checkpointed_results else len(
        set(r['filename'] for r in all_results))
    stats = calculate_batch_stats(
        all_results,
        checkpointed_count=len(set(r['filename'] for r in checkpointed_results)),
        newly_processed_count=newly_processed_count,
        start_time=start_time
    )
    print_batch_stats(stats)

    # Write batch_stats.json (D-12)
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"\nBatch statistics written to {stats_path}")

    # Clean up checkpoint after successful completion
    # (keep it — user may want to inspect; next run with --fresh clears it)

    print("Done.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Extract Precede IDs from PDF files')
    parser.add_argument('input_path', help='Path to PDF file or directory of PDFs')
    parser.add_argument('--output-csv', default='output/results.csv',
                        help='Path to output CSV (default: output/results.csv)')
    parser.add_argument('--output-json', default=None,
                        help='Path to output JSON (default: same dir as CSV with .json extension)')
    parser.add_argument('--workers', type=int, default=None,
                        help='Number of parallel workers (default: cpu_count()-1)')
    parser.add_argument('--debug', action='store_true',
                        help='Print raw OCR text for each rotation to stderr (single file only)')
    parser.add_argument('--fresh', action='store_true',
                        help='Delete existing checkpoint and start from scratch')
    args = parser.parse_args()

    main(args.input_path, args.output_csv, args.output_json, args.workers, args.debug, args.fresh)
