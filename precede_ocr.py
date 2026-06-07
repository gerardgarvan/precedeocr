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
import signal
import tempfile
import os
import time as time_module
import multiprocessing as mp
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from functools import wraps
from dataclasses import dataclass, field, asdict
from typing import Optional
from PIL import Image
from tqdm import tqdm
import cv2
import numpy as np
import pytesseract
import pandas as pd
from pdf2image import convert_from_path
from scipy.stats import theilslopes

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
_INPUT_PATH_ROOT = None  # Set by main() before pool spawn, used by wrapper for folder_path

# Graceful shutdown infrastructure (Phase 7)
_SHUTDOWN_EVENT = None   # multiprocessing.Event, set by process_all_pdfs before pool spawn (D-01)
_INTERRUPT_COUNT = 0     # Tracks Ctrl+C presses for double-interrupt force-quit (D-03)


def _init_worker():
    """Pool initializer: make workers ignore SIGINT so only main process handles Ctrl+C.

    Per SHUT-02: prevents KeyboardInterrupt injection into workers during OCR processing.
    Workers check _SHUTDOWN_EVENT instead for cooperative shutdown (D-01).
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _handle_sigint(signum, frame):
    """Handle Ctrl+C: first press sets shutdown flag, second force-quits.

    Per D-03: Second Ctrl+C force-terminates immediately.
    Per D-04: Force-quit prints warning about in-flight files.
    Per D-06: First Ctrl+C prints status with in-flight count and force-quit hint.
    """
    global _INTERRUPT_COUNT
    _INTERRUPT_COUNT += 1

    if _INTERRUPT_COUNT == 1:
        # Per D-06: Tell user what's happening
        print("\n\nCtrl+C received. Finishing in-flight files... (press Ctrl+C again to force-quit)")
        if _SHUTDOWN_EVENT is not None:
            _SHUTDOWN_EVENT.set()
    else:
        # Per D-04: Force-quit warning
        print("\n\nForce-quit! In-flight files may not be saved. Checkpoint has all completed files.")
        sys.exit(1)


@dataclass
class CampaignState:
    """Campaign orchestration metadata (separate from checkpoint results)."""
    version: str = "1.1"
    campaign_id: str = ""
    input_path: str = ""
    status: str = "running"  # running | interrupted | completed | failed
    started_at: str = ""
    last_updated: str = ""
    completed_at: Optional[str] = None
    total_files_discovered: int = 0
    files_processed: int = 0
    files_failed: int = 0
    folder_stats: dict = field(default_factory=dict)
    interruptions: list = field(default_factory=list)
    options: dict = field(default_factory=dict)

    @classmethod
    def generate_campaign_id(cls) -> str:
        """Generate campaign ID per D-01: campaign_YYYYMMDD_HHMMSS."""
        now = datetime.now()
        return f"campaign_{now.strftime('%Y%m%d_%H%M%S')}"


def save_campaign_state_atomic(state: CampaignState, output_dir: Path) -> None:
    """Atomically save campaign state JSON. Same pattern as save_checkpoint_atomic."""
    state_path = Path(output_dir) / 'campaign_state.json'
    temp_dir = state_path.parent
    state.last_updated = datetime.now().isoformat()
    state_dict = asdict(state)
    with tempfile.NamedTemporaryFile(
        mode='w', dir=temp_dir, delete=False, suffix='.tmp', prefix='.campaign_state_'
    ) as tmp_file:
        json.dump(state_dict, tmp_file, indent=2)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())
        tmp_path = tmp_file.name
    os.replace(tmp_path, str(state_path))


def load_or_create_campaign_state(
    output_dir: Path, input_path: str, cli_options: dict
) -> CampaignState:
    """Load existing campaign state, upgrade from v1.0 checkpoint, or create fresh."""
    state_path = Path(output_dir) / 'campaign_state.json'
    checkpoint_path = Path(output_dir) / '.checkpoint.json'

    # Case 1: Campaign state exists — load it
    if state_path.exists():
        try:
            with open(state_path) as f:
                state_dict = json.load(f)
            state = CampaignState(**{
                k: v for k, v in state_dict.items()
                if k in CampaignState.__dataclass_fields__
            })
            if state.input_path != input_path:
                print(f"WARNING: Campaign was for '{state.input_path}', now processing '{input_path}'")
            print(f"Resuming campaign: {state.campaign_id} ({state.status})")
            return state
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"WARNING: Corrupt campaign state, recreating: {e}")
            state_path.unlink(missing_ok=True)

    # Case 2: v1.0 checkpoint exists, no campaign state — silent upgrade (D-05)
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path) as f:
                checkpoint = json.load(f)
            metadata = checkpoint.get('metadata', {})
            processed_files = checkpoint.get('processed_files', [])
            checkpoint_ts = metadata.get('timestamp', datetime.now().isoformat())
            try:
                dt = datetime.fromisoformat(checkpoint_ts)
            except (ValueError, TypeError):
                dt = datetime.now()
            campaign_id = f"campaign_{dt.strftime('%Y%m%d_%H%M%S')}"
            state = CampaignState(
                campaign_id=campaign_id,
                input_path=input_path,
                status='interrupted',
                started_at=checkpoint_ts,
                files_processed=len(processed_files),
                options=cli_options
            )
            print(f"Upgraded to campaign tracking: {campaign_id}")  # D-06
            save_campaign_state_atomic(state, output_dir)
            return state
        except (json.JSONDecodeError, KeyError) as e:
            print(f"WARNING: Corrupt checkpoint during upgrade, starting fresh: {e}")

    # Case 3: Fresh start
    state = CampaignState(
        campaign_id=CampaignState.generate_campaign_id(),
        input_path=input_path,
        started_at=datetime.now().isoformat(),
        options=cli_options
    )
    print(f"Starting new campaign: {state.campaign_id}")
    save_campaign_state_atomic(state, output_dir)
    return state


def compute_folder_path(pdf_path: Path, input_path_root: Path) -> str:
    """Compute folder_path relative to input_path_root with normalization per D-07/D-08/D-09."""
    pdf_resolved = pdf_path.resolve()
    input_resolved = input_path_root.resolve()
    pdf_folder = pdf_resolved.parent
    try:
        rel_folder = pdf_folder.relative_to(input_resolved)
        folder_path = str(rel_folder)
    except ValueError:
        folder_path = str(pdf_folder)
        return folder_path
    if folder_path == '.':
        folder_path = ''
    return folder_path


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


def preprocess_image(pil_image: Image.Image) -> Image.Image:
    """
    Apply single-pass preprocessing for degraded scans per D-01.

    Pipeline: grayscale -> Gaussian blur (denoise) -> Otsu threshold.
    Converts PIL Image to OpenCV array, processes, converts back to PIL.

    Uses COLOR_RGB2GRAY (not BGR2GRAY) because PIL images are RGB.
    Blur BEFORE threshold (not after) to smooth noise before binarization.

    Args:
        pil_image: Original PIL Image from PDF page

    Returns:
        Preprocessed PIL Image (grayscale, denoised, binarized)
    """
    # Convert PIL to numpy array (OpenCV format)
    img_array = np.array(pil_image)

    # Step 1: Grayscale conversion
    # PIL images are RGB, so use COLOR_RGB2GRAY (not BGR2GRAY per Pitfall 2)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Step 2: Denoise with Gaussian blur (5x5 kernel, sigma=0 auto-calculated)
    # Must blur BEFORE threshold (Pitfall 1: threshold-then-blur is wrong order)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Step 3: Otsu's thresholding (automatic threshold determination)
    # cv2.THRESH_BINARY: pixels > threshold -> 255 (white), else 0 (black)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Convert back to PIL Image for pytesseract compatibility
    return Image.fromarray(binary)


def extract_id_with_rotation(image: Image.Image, debug: bool = False) -> tuple[list[str], int | None, str]:
    """
    Extract 5-digit IDs by trying OCR at all 4 rotations with early exit.
    Falls back to preprocessing (D-01/D-02/D-03) if direct OCR finds no match.

    Per Phase 2 decisions D-08, D-09: Try rotations [90, 270, 0, 180] sequentially.
    Exit loop on first rotation that yields valid 5-digit matches (saves compute).
    90-first order eliminates false positives from 0-degree matches (page numbers, dates).

    Per Phase 3 D-02: Returns ALL valid IDs from the successful rotation, not just first.

    Per Phase 5 D-01/D-02/D-03: When direct OCR fails, preprocess image with
    grayscale + Gaussian blur + Otsu threshold, then retry ALL 4 rotations.
    Per Phase 5 D-04: Notes column contains 'preprocessed' when fallback succeeds.
    Per Phase 5 D-05: Same digit whitelist for both direct and preprocessed passes.

    Args:
        image: PIL Image at 300 DPI
        debug: If True, print raw OCR text to stderr for each rotation

    Returns:
        Tuple of (ids_list, rotation_angle, notes) where ids_list is a list of
        valid ID strings, and notes is '' for direct success, 'preprocessed' for
        preprocessing success, or failure reason for no match
    """
    ocr_texts = []  # Collect OCR text for failure classification

    # === Direct OCR attempt (existing logic) ===
    for angle in [90, 270, 0, 180]:  # D-08: Rotation order optimized
        # Rotate image (expand=True prevents cropping)
        if angle == 0:
            rotated_image = image
        else:
            rotated_image = image.rotate(angle, expand=True)

        # Tesseract config: PSM 6, LSTM engine, digits only (D-05: same for both passes)
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

    # === Preprocessing fallback (Phase 5 D-01/D-02/D-03) ===
    # D-03: ALL failure types trigger preprocessing retry
    preprocessed = preprocess_image(image)
    ocr_texts_preprocessed = []

    for angle in [90, 270, 0, 180]:  # D-02: retry ALL rotations on preprocessed
        if angle == 0:
            rotated_image = preprocessed
        else:
            rotated_image = preprocessed.rotate(angle, expand=True)

        config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'  # D-05: same whitelist
        text = pytesseract.image_to_string(rotated_image, config=config).strip()
        ocr_texts_preprocessed.append(text)

        if debug:
            print(f"DEBUG [Preprocessed Rotation {angle}]: {repr(text)}", file=sys.stderr)

        normalized_text = normalize_digits(text)
        matches = re.findall(r'\b\d{5}\b', normalized_text)

        if matches:
            selected_ids = select_all_valid_ids(matches)
            if selected_ids:
                return selected_ids, angle, 'preprocessed'  # D-04: flag in notes

    # Both direct and preprocessed failed
    reason = classify_failure_reason(ocr_texts + ocr_texts_preprocessed)
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
                    'folder_path': r.get('folder_path', ''),
                    'page': r['page'],
                    'id': id_val,
                    'rotation_detected': r['rotation_detected'],
                    'notes': r['notes']
                })
        else:
            flattened.append({
                'filename': r['filename'],
                'folder_path': r.get('folder_path', ''),
                'page': r['page'],
                'id': '',
                'rotation_detected': r['rotation_detected'],
                'notes': r['notes']
            })

    # Create DataFrame
    df = pd.DataFrame(flattened)

    # Enforce column order per D-12: includes notes column and folder_path
    df = df[['filename', 'folder_path', 'page', 'id', 'rotation_detected', 'notes']]

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

    Structure: {"file.pdf": {"folder_path": "subdir1", "pages": {"1": ["12345"], "2": ["67890", "11234"], "3": []}}}
    Pages with no ID show as empty array (per D-04, PIPE-07).
    Page keys are strings (JSON keys must be strings).
    folder_path is per-file metadata included in the nested structure.

    Args:
        results: List of dicts from process_single_pdf() with 'ids' key (list)
        output_path: Path to output JSON file
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    nested = {}
    for row in results:
        filename = row['filename']
        page = str(row['page'])
        ids = row['ids']
        folder_path = row.get('folder_path', '')

        if filename not in nested:
            nested[filename] = {
                'folder_path': folder_path,
                'pages': {}
            }
        nested[filename]['pages'][page] = ids

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


def validate_sequence(results: list[dict]) -> list[dict]:
    """
    Flag out-of-sequence IDs using Theil-Sen robust regression + MAD outlier detection.

    Per D-06: Post-hoc trend-based sequence check within each file.
    Per D-07: Flag + confidence score for out-of-sequence IDs. Keep ID in results.
    Per D-08: 270-degree rotations are particularly suspect for false positives.

    Uses Theil-Sen estimator (median of pairwise slopes) instead of OLS linear
    regression. Theil-Sen is robust to up to ~29% outliers, preventing extreme
    values from pulling the fit line and causing false flags on normal IDs.

    For small samples (< 5 IDs), uses deviation-from-median instead of regression,
    since Theil-Sen's breakdown point (29%) is too easily exceeded with few points.

    For each file:
    1. Sort results by page number (handle imap_unordered order)
    2. Extract (page_number, id_value) pairs from rows with valid IDs
    3. Skip files with < 3 ID data points (unreliable detection)
    4. For 3-4 IDs: deviation-from-median outlier detection
    5. For 5+ IDs: Theil-Sen robust regression (page -> ID value)
    6. Calculate residuals and MAD (median absolute deviation)
    7. Flag ONLY IDs with |residual| > threshold as outliers
    8. Confidence = how far beyond threshold (higher % = more likely outlier)

    Args:
        results: Flat list of result dicts from process_all_pdfs/process_single_pdf

    Returns:
        Updated results list with sequence outlier flags in notes column.
        Original results are NOT modified (copies created).
    """
    # Group by filename
    by_file = defaultdict(list)
    for r in results:
        by_file[r['filename']].append(r)

    validated_results = []

    for filename, file_results in by_file.items():
        # Sort by page number before analysis (handle imap_unordered)
        file_results = sorted(file_results, key=lambda r: r['page'])

        # Extract rows with valid IDs (skip error rows and no-ID pages)
        valid_rows = [r for r in file_results if r['ids'] and r['page'] > 0
                      and 'error:' not in r.get('notes', '')]

        if len(valid_rows) < 3:
            validated_results.extend(file_results)
            continue

        # Flatten multi-ID pages: one (page, id_value) pair per ID
        page_id_pairs = []
        for r in valid_rows:
            for id_val in r['ids']:
                page_id_pairs.append((r['page'], int(id_val)))

        if len(page_id_pairs) < 3:
            validated_results.extend(file_results)
            continue

        pages = [p for p, _ in page_id_pairs]
        id_values = [i for _, i in page_id_pairs]

        # Choose detection method based on sample size:
        # - Small samples (< 5): Theil-Sen breakdown point (~29%) is too easily
        #   exceeded (e.g., 1 outlier in 3 = 33%), so use Tukey box-plot fences
        #   on the raw ID values for robust outlier detection.
        # - Larger samples (>= 5): Theil-Sen robust regression handles outliers well.
        if len(page_id_pairs) < 5:
            # Modified Z-score method on raw ID values: robust for small samples.
            # Theil-Sen breakdown point (~29%) is too easily exceeded with 3-4 points,
            # so we use deviation from median with MAD-based scoring instead.
            median_id = float(np.median(id_values))
            deviations = [abs(v - median_id) for v in id_values]
            mad_ids = float(np.median(deviations))

            if mad_ids == 0:
                # All IDs identical or nearly so -- no outliers possible
                validated_results.extend(file_results)
                continue

            # Modified Z-score threshold: flag if |0.6745 * deviation / MAD| > 3.5
            # This is the standard Iglewicz & Hoaglin cutoff for outlier detection.
            outlier_lookup = {}
            idx = 0
            for r in valid_rows:
                for id_val in r['ids']:
                    deviation = deviations[idx]
                    modified_z = 0.6745 * deviation / mad_ids
                    if modified_z > 3.5:
                        # Confidence: scale from 50% at threshold to 100% at 2x threshold
                        confidence_pct = min(100, int(modified_z / 3.5 * 50))
                        outlier_lookup[(r['page'], id_val)] = max(confidence_pct, 1)
                    idx += 1
        else:
            # Fit Theil-Sen robust regression: page_number (X) -> id_value (Y)
            # theilslopes(y, x) returns (slope, intercept, low_slope, high_slope)
            slope, intercept, _, _ = theilslopes(id_values, pages)

            # Calculate residuals (absolute difference from predicted)
            residuals = [abs(actual - (slope * page + intercept))
                         for page, actual in page_id_pairs]

            # Calculate MAD (median absolute deviation from median residual)
            median_residual = float(np.median(residuals))
            mad = float(np.median([abs(r - median_residual) for r in residuals]))

            # Determine threshold for outlier detection
            max_residual = max(residuals)

            if mad > 0:
                # Standard case: use 1.5 * MAD
                threshold = 1.5 * mad
            elif max_residual == 0:
                # Perfect fit, all residuals zero -- no outliers possible
                validated_results.extend(file_results)
                continue
            else:
                # MAD == 0 but some residuals are non-zero.
                # This happens when Theil-Sen fits the majority perfectly
                # (residuals cluster at the same small value) but outliers have
                # huge residuals. Use 3x median_residual as threshold; if median
                # is 0 (perfect fit for majority), use a minimal threshold of 1.0.
                threshold = max(median_residual * 3, 1.0)

            # Build outlier lookup for regression method
            outlier_lookup = {}
            idx = 0
            for r in valid_rows:
                for id_val in r['ids']:
                    residual = residuals[idx]
                    if residual > threshold:
                        # Higher residual = higher confidence it's an outlier
                        confidence_pct = min(100, int(residual / threshold * 100))
                        outlier_lookup[(r['page'], id_val)] = confidence_pct
                    idx += 1

        # Apply flags to results (only outlier rows get flagged)
        for r in file_results:
            updated_r = r.copy()

            if updated_r['ids'] and updated_r['page'] > 0 and 'error:' not in updated_r.get('notes', ''):
                # Collect outlier flags for ALL IDs in this row
                flags = []
                for id_val in updated_r['ids']:
                    key = (updated_r['page'], id_val)
                    if key in outlier_lookup:
                        conf = outlier_lookup[key]
                        flags.append(f"seq_outlier_conf_{conf}%")

                # Append combined flags ONCE (avoids duplicate flag bug)
                if flags:
                    combined_flag = '; '.join(flags)
                    if updated_r['notes']:
                        updated_r['notes'] += f"; {combined_flag}"
                    else:
                        updated_r['notes'] = combined_flag

            validated_results.append(updated_r)

    return validated_results


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
    # Per D-02: Check shutdown at file-level granularity (not page-level)
    # Worker completes current PDF or skips entirely — no partial files
    if _SHUTDOWN_EVENT is not None and _SHUTDOWN_EVENT.is_set():
        return []

    try:
        results = _process_single_pdf_with_retry(str(pdf_path), debug=False)

        # Inject folder_path into each result dict (D-07, D-08, D-09)
        if _INPUT_PATH_ROOT is not None:
            folder_path = compute_folder_path(pdf_path, Path(_INPUT_PATH_ROOT))
        else:
            folder_path = ''
        for result in results:
            result['folder_path'] = folder_path

        return results
    except Exception as e:
        # Log to errors.log (D-09)
        if _ERROR_LOG_PATH is not None:
            log_error_to_file(pdf_path.name, e, Path(_ERROR_LOG_PATH))

        # Compute folder_path for error dict
        folder_path = ''
        if _INPUT_PATH_ROOT is not None:
            folder_path = compute_folder_path(pdf_path, Path(_INPUT_PATH_ROOT))

        # Return error dict for CSV notes column (D-10)
        return [{
            'filename': pdf_path.name,
            'page': 0,
            'ids': [],
            'rotation_detected': None,
            'notes': f'error: {type(e).__name__}: {str(e)}',
            'folder_path': folder_path
        }]


def process_all_pdfs(pdf_paths: list[Path], workers: int,
                     checkpointed_results: list[dict] | None = None,
                     checkpoint_path: Path | None = None,
                     input_path: str = '',
                     checkpoint_frequency: int = 50,
                     campaign_state: CampaignState | None = None,
                     output_dir: Path | None = None) -> list[dict]:
    """
    Process all PDFs in parallel with progress bar, running stats, periodic checkpointing,
    and graceful shutdown support (Phase 7).

    Per D-03: Saves checkpoint every checkpoint_frequency files (default 50).
    Per D-04: Returns merged results (checkpointed + newly processed).
    Per D-14: Tracks resume-aware metrics (checkpointed vs newly processed counts).
    Per SHUT-01: Ctrl+C breaks loop, workers finish current file, state saved.

    Args:
        pdf_paths: List of REMAINING PDF file paths (already filtered)
        workers: Number of worker processes
        checkpointed_results: Previously checkpointed results to merge (default: empty)
        checkpoint_path: Path to .checkpoint.json file (None = no checkpointing)
        input_path: Original input path string (stored in checkpoint metadata)
        checkpoint_frequency: Save checkpoint every N files (default 50)
        campaign_state: CampaignState object for interruption tracking (Phase 6/7)
        output_dir: Output directory for campaign state saves

    Returns:
        Flat list of ALL result dicts (checkpointed + new)
    """
    global _SHUTDOWN_EVENT, _INTERRUPT_COUNT

    if checkpointed_results is None:
        checkpointed_results = []

    all_results = list(checkpointed_results)  # Copy to avoid mutating input
    processed_files = {r['filename'] for r in checkpointed_results}
    files_since_checkpoint = 0
    stats = {'ids': 0, 'no_id_pages': 0, 'errors': 0}

    # Calculate total for progress bar (remaining + already done)
    total_files = len(pdf_paths) + len(checkpointed_results)

    chunksize = max(1, min(10, len(pdf_paths) // (4 * workers)))

    # Phase 7: Install shutdown infrastructure before pool creation
    if _SHUTDOWN_EVENT is None:
        _SHUTDOWN_EVENT = mp.Event()
    _INTERRUPT_COUNT = 0
    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, _handle_sigint)

    try:
        with mp.Pool(processes=workers, maxtasksperchild=50, initializer=_init_worker) as pool:
            pbar = tqdm(
                total=total_files,
                initial=len(checkpointed_results),  # Resume offset
                desc="Processing PDFs",
                unit="file"
            )

            try:
                for file_results in pool.imap_unordered(
                    process_single_pdf_wrapper,
                    pdf_paths,
                    chunksize=chunksize
                ):
                    # Phase 7: Check shutdown flag before processing result (D-05)
                    if _SHUTDOWN_EVENT.is_set():
                        break

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

                        # Update campaign state alongside checkpoint (same frequency)
                        if campaign_state is not None and output_dir is not None:
                            campaign_state.files_processed = len(processed_files)
                            campaign_state.files_failed = sum(
                                1 for r in all_results if r.get('page') == 0 and 'error:' in r.get('notes', '')
                            )
                            save_campaign_state_atomic(campaign_state, output_dir)

                    pbar.update(1)
                    pbar.set_postfix({
                        'IDs': stats['ids'],
                        'No-ID': stats['no_id_pages'],
                        'Errors': stats['errors']
                    })

            finally:
                # Per SHUT-04: Always close tqdm to prevent terminal corruption
                pbar.close()

        # After pool context manager exits (close+join complete per SHUT-03):

        # Final checkpoint save (ensure all results persisted)
        if checkpoint_path:
            save_checkpoint_atomic(
                all_results, processed_files, input_path,
                checkpoint_path, checkpoint_frequency
            )

        # Handle interruption state (SHUT-05)
        if _SHUTDOWN_EVENT.is_set():
            if campaign_state is not None:
                campaign_state.status = 'interrupted'
                campaign_state.interruptions.append({
                    'timestamp': datetime.now().isoformat(),
                    'files_completed': len(processed_files),
                    'reason': 'user_interrupt'
                })
            if campaign_state is not None and output_dir is not None:
                campaign_state.files_processed = len(processed_files)
                campaign_state.files_failed = sum(
                    1 for r in all_results if r.get('page') == 0 and 'error:' in r.get('notes', '')
                )
                save_campaign_state_atomic(campaign_state, output_dir)

            # Per D-07: Brief summary on graceful shutdown
            total = len(pdf_paths) + len(checkpointed_results)
            ids_found = sum(len(r['ids']) for r in all_results if r.get('ids'))
            print(f"\nInterrupted: {len(processed_files)}/{total} files processed ({ids_found} IDs found). State saved. Resume with same command.")
        else:
            # Normal completion: finalize campaign state
            if campaign_state is not None and output_dir is not None:
                campaign_state.files_processed = len(processed_files)
                campaign_state.files_failed = sum(
                    1 for r in all_results if r.get('page') == 0 and 'error:' in r.get('notes', '')
                )
                save_campaign_state_atomic(campaign_state, output_dir)

    finally:
        # Restore original signal handler (important for tests and nested calls)
        signal.signal(signal.SIGINT, original_sigint)

    return all_results


def show_campaign_menu(campaign_state: CampaignState,
                       checkpoint_data: tuple[list[dict], set[str]],
                       all_pdf_count: int) -> int:
    """Display campaign status and numbered menu, validate input, return choice.

    Per D-01: Shows campaign ID, status, progress, failed count.
    Per D-02: Numbered options [1]-[6].
    Per D-03: Re-prompt loop on invalid input.
    Per D-10: Shows 'all files processed' when 100% complete.

    Args:
        campaign_state: CampaignState with campaign metadata
        checkpoint_data: Tuple of (results_list, processed_files_set)
        all_pdf_count: Total PDFs discovered (for completion check)

    Returns:
        int: User's menu choice (1-6)
    """
    _, processed_files = checkpoint_data

    # Print status header (D-01)
    print(f"\nCampaign: {campaign_state.campaign_id}")
    print(f"Status: {campaign_state.status}")
    print(f"Progress: {campaign_state.files_processed}/{campaign_state.total_files_discovered} files")
    print(f"Failed: {campaign_state.files_failed} files")
    print()

    # Build menu options (D-02)
    # D-10: If 100% complete, show indicator on Continue
    if len(processed_files) >= all_pdf_count:
        option_1 = "[1] Continue processing  (all files processed)"
    else:
        option_1 = "[1] Continue processing"

    # Discretion: Show failed count next to Re-run failures for quick visibility
    if campaign_state.files_failed > 0:
        option_2 = f"[2] Re-run failures ({campaign_state.files_failed} failed)"
    else:
        option_2 = "[2] Re-run failures"

    print(option_1)
    print(option_2)
    print("[3] View stats")
    print("[4] Export partial results")
    print("[5] Fresh start")
    print("[6] Quit")
    print()

    # Input validation loop (D-03)
    while True:
        try:
            raw = input("Enter choice (1-6): ")
            choice = int(raw)
            if 1 <= choice <= 6:
                return choice
            print("Invalid choice. Enter 1-6:")
        except ValueError:
            print("Invalid choice. Enter 1-6:")
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            sys.exit(0)


def handle_view_stats(campaign_state: CampaignState,
                      checkpoint_data: tuple[list[dict], set[str]]) -> str:
    """Display campaign statistics and return to menu.

    Per D-04: Shows files done/total, failed count, IDs found.

    Args:
        campaign_state: CampaignState with campaign metadata
        checkpoint_data: Tuple of (results_list, processed_files_set)

    Returns:
        'menu' to signal return to menu loop
    """
    results, _ = checkpoint_data

    ids_count = sum(len(r['ids']) for r in results if r.get('ids'))
    error_count = sum(
        1 for r in results
        if r.get('page') == 0 and r.get('notes', '').startswith('error:')
    )

    print(f"\nFiles processed: {campaign_state.files_processed}/{campaign_state.total_files_discovered}")
    print(f"Failed: {campaign_state.files_failed}")
    print(f"IDs found: {ids_count}")

    return 'menu'


def handle_export_partial(checkpoint_data: tuple[list[dict], set[str]],
                          output_csv: str, output_json: str) -> str:
    """Export partial results to CSV and JSON without sequence validation.

    Per D-11: Reuses existing write_results_csv and write_results_json.
    Per D-12: Prints confirmation message after export.
    Per D-13: Does NOT call validate_sequence (partial data has gaps).

    Args:
        checkpoint_data: Tuple of (results_list, processed_files_set)
        output_csv: Path to output CSV file
        output_json: Path to output JSON file

    Returns:
        'menu' to signal return to menu loop
    """
    results, _ = checkpoint_data
    write_results_csv(results, output_csv)
    write_results_json(results, output_json)
    print(f"Exported {len(results)} results to {output_csv}")
    return 'menu'


def handle_quit() -> str:
    """Handle quit menu option.

    Returns:
        'quit' to signal exit from menu loop
    """
    print("Exiting.")
    return 'quit'


def handle_continue() -> str:
    """Handle continue menu option.

    Returns:
        'continue' to signal resume processing
    """
    print("Continuing processing...")
    return 'continue'


def get_failed_filenames(checkpointed_results: list[dict]) -> set[str]:
    """Extract filenames of files that failed at the file level.

    Per D-05: Failed means page==0 and notes starting with 'error:'.
    Page-level errors (page>0) are not file-level failures.

    Args:
        checkpointed_results: List of result dicts from checkpoint

    Returns:
        Set of filenames that had file-level errors
    """
    return {
        r['filename'] for r in checkpointed_results
        if r.get('page') == 0 and r.get('notes', '').startswith('error:')
    }


def handle_rerun_failures(campaign_state: CampaignState,
                          checkpoint_data: tuple[list[dict], set[str]],
                          output_dir: Path,
                          output_csv: str, output_json: str,
                          workers: int, checkpoint_frequency: int) -> str:
    """Re-run only previously failed files and merge results.

    Per D-05: Identifies failed files by page==0 + notes.startswith('error:').
    Per D-06: Removes old error entries before reprocessing.
    Per D-07: Auto-writes CSV/JSON after re-run completes.

    Args:
        campaign_state: CampaignState with campaign metadata
        checkpoint_data: Tuple of (results_list, processed_files_set)
        output_dir: Output directory path
        output_csv: Path to output CSV file
        output_json: Path to output JSON file
        workers: Number of parallel workers
        checkpoint_frequency: Checkpoint save frequency

    Returns:
        'menu' if no failures found, 'rerun' after successful re-run
    """
    checkpointed_results, processed_files = checkpoint_data

    # Identify failed files (D-05)
    failed_filenames = get_failed_filenames(checkpointed_results)

    if not failed_filenames:
        print("No failed files to re-run.")
        return 'menu'

    # Remove old error entries before reprocessing (D-06)
    clean_results = [r for r in checkpointed_results if r['filename'] not in failed_filenames]

    # Rediscover failed file paths
    all_pdfs = discover_pdfs(campaign_state.input_path)
    failed_pdfs = [p for p in all_pdfs if p.name in failed_filenames]

    print(f"Re-running {len(failed_pdfs)} failed files...")

    # Set up checkpoint path
    checkpoint_path = output_dir / '.checkpoint.json'

    # Process only the failed files with clean results as base
    new_results = process_all_pdfs(
        failed_pdfs, workers=workers,
        checkpointed_results=clean_results,
        checkpoint_path=checkpoint_path,
        input_path=campaign_state.input_path,
        checkpoint_frequency=checkpoint_frequency,
        campaign_state=campaign_state,
        output_dir=output_dir
    )

    # Validate and write final output (D-07)
    validated_results = validate_sequence(new_results)
    write_results_csv(validated_results, output_csv)
    write_results_json(validated_results, output_json)
    print_rotation_summary(validated_results)

    # Finalize campaign state
    campaign_state.status = 'completed'
    campaign_state.completed_at = datetime.now().isoformat()
    save_campaign_state_atomic(campaign_state, output_dir)

    print("Re-run complete.")
    return 'rerun'


def handle_fresh_start(output_dir: Path) -> str:
    """Clear all checkpoint and campaign state files for a fresh start.

    Per D-04: Deletes checkpoint, campaign state, and error log.

    Args:
        output_dir: Output directory containing state files

    Returns:
        'fresh' to signal fresh start
    """
    checkpoint_path = output_dir / '.checkpoint.json'
    campaign_state_path = output_dir / 'campaign_state.json'
    error_log_path = output_dir / 'errors.log'

    if checkpoint_path.exists():
        checkpoint_path.unlink()
    if campaign_state_path.exists():
        campaign_state_path.unlink()
    if error_log_path.exists():
        error_log_path.unlink()

    print("Cleared checkpoint, campaign state, and error log.")
    return 'fresh'


def run_menu_loop(campaign_state: CampaignState,
                  checkpoint_data: tuple[list[dict], set[str]],
                  all_pdf_count: int,
                  output_csv: str, output_json: str,
                  output_dir: Path = None,
                  workers: int = 1,
                  checkpoint_frequency: int = 50) -> str:
    """Run the interactive menu loop, dispatching to handlers.

    Choices 1, 2, 5 are handled by pipeline-integrated handlers.
    Choices 3, 4, 6 are handled internally (view stats, export, quit).
    Loop continues when handler returns 'menu'.

    Args:
        campaign_state: CampaignState with campaign metadata
        checkpoint_data: Tuple of (results_list, processed_files_set)
        all_pdf_count: Total PDFs discovered
        output_csv: Path to output CSV
        output_json: Path to output JSON
        output_dir: Output directory path (for rerun/fresh handlers)
        workers: Number of parallel workers (for rerun handler)
        checkpoint_frequency: Checkpoint save frequency (for rerun handler)

    Returns:
        str: 'continue', 'rerun', 'fresh', or 'quit'
    """
    # Handler dispatch mapping
    handlers = {
        1: lambda: handle_continue(),
        2: lambda: handle_rerun_failures(
            campaign_state, checkpoint_data, output_dir,
            output_csv, output_json, workers, checkpoint_frequency
        ),
        3: lambda: handle_view_stats(campaign_state, checkpoint_data),
        4: lambda: handle_export_partial(checkpoint_data, output_csv, output_json),
        5: lambda: handle_fresh_start(output_dir),
        6: lambda: handle_quit(),
    }

    while True:
        choice = show_campaign_menu(campaign_state, checkpoint_data, all_pdf_count)

        if choice in handlers:
            result = handlers[choice]()
            if result != 'menu':
                return result
            # result == 'menu' -> loop continues


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
    global _ERROR_LOG_PATH, _INPUT_PATH_ROOT

    # Determine output directory from CSV path
    output_dir = Path(output_csv).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / '.checkpoint.json'
    error_log_path = output_dir / 'errors.log'
    stats_path = output_dir / 'batch_stats.json'
    campaign_state_path = output_dir / 'campaign_state.json'

    # Set module-level error log path for workers
    _ERROR_LOG_PATH = str(error_log_path)
    _INPUT_PATH_ROOT = input_path

    # D-07: --fresh flag deletes checkpoint and error log
    if fresh:
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            print("Deleted existing checkpoint (--fresh mode)")
        if error_log_path.exists():
            error_log_path.unlink()
            print("Deleted existing error log (--fresh mode)")
        if campaign_state_path.exists():
            campaign_state_path.unlink()
            print("Deleted existing campaign state (--fresh mode)")

    # Discover PDF files
    pdf_paths = discover_pdfs(input_path)

    if not pdf_paths:
        print(f"No PDF files found in {input_path}")
        return

    print(f"Found {len(pdf_paths)} PDF file(s)")

    # Campaign state lifecycle (Phase 6)
    cli_options = {
        'workers': workers,
        'checkpoint_frequency': _CHECKPOINT_FREQUENCY,
        'output_csv': output_csv,
        'output_json': output_json
    }
    campaign_state = load_or_create_campaign_state(output_dir, input_path, cli_options)
    campaign_state.total_files_discovered = len(pdf_paths)
    campaign_state.status = 'running'

    # Determine JSON output path (D-05: always generate both)
    if output_json is None:
        output_json = str(Path(output_csv).with_suffix('.json'))

    # Phase 8: Interactive campaign menu (D-08, D-09)
    checkpointed_results = []
    processed_files = set()
    menu_handled = False

    if not fresh and checkpoint_path.exists():
        checkpoint_data = load_checkpoint_if_exists(output_dir, input_path)
        if checkpoint_data:
            checkpointed_results, processed_files = checkpoint_data

            # Determine workers before menu (needed for rerun)
            menu_workers = workers if workers is not None else max(1, mp.cpu_count() - 1)

            action = run_menu_loop(
                campaign_state, checkpoint_data, len(pdf_paths),
                output_csv, output_json, output_dir,
                menu_workers, _CHECKPOINT_FREQUENCY
            )
            menu_handled = True

            if action == 'quit':
                return
            elif action == 'rerun':
                # Re-run handler already wrote outputs and finalized state
                return
            elif action == 'fresh':
                # State already cleared by handler, rediscover all files
                pdf_paths = discover_pdfs(input_path)
                if not pdf_paths:
                    print(f"No PDF files found in {input_path}")
                    return
                print(f"Found {len(pdf_paths)} PDF file(s)")
                # Recreate campaign state for fresh run
                campaign_state = load_or_create_campaign_state(output_dir, input_path, cli_options)
                campaign_state.total_files_discovered = len(pdf_paths)
                campaign_state.status = 'running'
                # Reset checkpoint data so normal flow starts fresh
                checkpointed_results = []
                processed_files = set()
                # Fall through to normal processing below
            elif action == 'continue':
                # Filter remaining PDFs and fall through to normal processing
                pdf_paths = filter_remaining_pdfs(pdf_paths, processed_files)
                if not pdf_paths:
                    # All files already processed (edge case -- 100% complete, user chose continue anyway)
                    print("All files already processed. Use --fresh to reprocess.")
                    all_results = checkpointed_results
                    campaign_state.status = 'completed'
                    campaign_state.completed_at = datetime.now().isoformat()
                    campaign_state.files_processed = len(set(r['filename'] for r in all_results))
                    save_campaign_state_atomic(campaign_state, output_dir)
                    all_results = validate_sequence(all_results)
                    write_results_csv(all_results, output_csv)
                    write_results_json(all_results, output_json)
                    print_rotation_summary(all_results)
                    print("Done.")
                    return
                # Fall through to normal processing with filtered pdfs

    # D-05: Auto-detect checkpoint for resume (non-menu path)
    if not menu_handled and not fresh:
        checkpoint_data = load_checkpoint_if_exists(output_dir, input_path)
        if checkpoint_data:
            checkpointed_results, processed_files = checkpoint_data
            pdf_paths = filter_remaining_pdfs(pdf_paths, processed_files)
            if not pdf_paths:
                print("All files already processed. Use --fresh to reprocess.")
                # Still write outputs from checkpoint data
                all_results = checkpointed_results

                # Finalize campaign state for completed resume
                campaign_state.status = 'completed'
                campaign_state.completed_at = datetime.now().isoformat()
                campaign_state.files_processed = len(set(r['filename'] for r in all_results))
                save_campaign_state_atomic(campaign_state, output_dir)

                # Phase 5 D-06/D-07: Post-hoc sequential validation
                all_results = validate_sequence(all_results)
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

        # Inject folder_path for single file mode
        for result in all_results:
            if 'folder_path' not in result:
                result['folder_path'] = compute_folder_path(pdf_paths[0], Path(input_path))
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
            checkpoint_frequency=_CHECKPOINT_FREQUENCY,
            campaign_state=campaign_state,
            output_dir=output_dir
        )

    # Phase 5 D-06/D-07: Post-hoc sequential validation
    all_results = validate_sequence(all_results)

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

    # Finalize campaign state
    campaign_state.status = 'completed'
    campaign_state.completed_at = datetime.now().isoformat()
    campaign_state.files_processed = len(set(r['filename'] for r in all_results))
    campaign_state.files_failed = sum(
        1 for r in all_results if r.get('page') == 0 and 'error:' in r.get('notes', '')
    )
    save_campaign_state_atomic(campaign_state, output_dir)

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
