# Phase 15: Error Investigation & Reporting - Research

**Researched:** 2026-06-10
**Domain:** Error diagnosis, OCR failure investigation, blank page detection, diagnostic reporting
**Confidence:** HIGH

## Summary

Phase 15 implements the `investigate` subcommand that diagnoses root causes of 49 failed files and 59 no-match pages from the production v1.2 run. The investigation re-renders and re-OCRs no-match pages using PyMuPDF + Pillow + pytesseract (already available), applies pixel-based blank page detection, categorizes failures, and produces structured markdown + CSV reports with actionable recommendations.

This is a report-only phase with zero modification risk — reads existing scan results CSV, writes diagnostic outputs, never modifies raw data. The implementation follows the established `cmd_lookup` pattern: argparse subcommand handler, pandas CSV processing, pathlib file operations, and TDD with pytest.

**Primary recommendation:** Use PIL/Pillow pixel analysis to detect blank pages (histogram-based thresholding), re-render no-match pages via PyMuPDF at DPI 200 with single OCR pass for diagnosis (not full 8-pass pipeline), categorize into blank/OCR-failure/missing-label, and export structured markdown report + CSV with copy-paste CLI commands for fixable errors.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Re-render and re-OCR no-match pages for diagnosis. Do not rely on metadata-only analysis — re-open the actual PDFs, render the specific pages, and run OCR to capture what Tesseract sees.
- **D-02:** Use "quick scan" approach: render each no-match page, check if blank (all-white/all-black pixel analysis), then run a single OCR pass to capture raw text. Do NOT run all 8 passes — one pass is sufficient for categorization (blank page vs OCR failure vs missing ID label).
- **D-03:** Report only. The `investigate` command produces diagnostic reports but does NOT apply fixes or modify results.csv. Raw data stays untouched.
- **D-04:** Include copy-paste CLI commands in the report for each fixable category. The user can run these commands to fix issues themselves (e.g., `python precede_ocr.py scan <specific-path> --fresh` for files that now exist).
- **D-05:** Read from scan results CSV as a positional argument, consistent with `cmd_lookup` pattern. CLI: `python precede_ocr.py investigate results.csv --report output/quality_report.md`

### Claude's Discretion
- **Failed file re-verification:** Claude decides whether to re-attempt opening failed files (to check if FileNotFoundErrors are still valid or were transient). Recommended: re-verify existence since it's cheap and makes the report much more useful.
- **Page image saving:** Claude decides whether to save rendered no-match page images to disk for manual inspection. Consider cost/benefit — 59 PNGs is manageable but may not be essential if the report text is clear enough.
- **PDF path resolution:** Claude decides how to locate original PDFs for re-rendering. The CSV filename column contains paths. Options: infer from CSV paths directly, or add an optional `--pdf-dir` argument. Pick what works with the existing CSV data format.
- **Output CSV files:** Claude decides which CSV exports to produce beyond the mandatory `no_match_pages.csv` (per SC-4). A `failed_files.csv` is reasonable. Use judgment on what's useful.
- **Report detail level:** Claude decides between summary+tables vs full narrative. Recommend: scannable tables with per-file breakdowns, keeping it concise and actionable rather than forensic-narrative style.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ERR-01 | User can investigate failed files — verify existence, categorize by error type (FileNotFoundError vs EmptyFileError), identify root causes | Pandas CSV filtering (page=0 + error: prefix), pathlib .exists() checks, categorize_errors() function reuse |
| ERR-02 | User can investigate no-match pages — determine if blank page, OCR failure, or missing ID label | PyMuPDF page.get_pixmap() re-rendering, PIL histogram analysis for blank detection, pytesseract single-pass OCR for text capture |
| ERR-03 | Pipeline fixes are applied for fixable errors (e.g., path resolution issues, retry logic) | CONTEXT.md clarifies this means "identified and documented" not "auto-applied" — report includes copy-paste commands per D-04 |
| ERR-04 | User receives a quality report (markdown) documenting all findings, error categories, and recommendations | Markdown generation with structured tables, pandas DataFrame.to_markdown() for tabular output, pathlib write_text() for file output |

</phase_requirements>

## Standard Stack

All dependencies already installed per project constraints. No new packages required.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.3 | CSV reading, filtering, categorization | Already used in cmd_lookup, Phase 14. DataFrame operations for error/no-match filtering, to_markdown() for tables in report |
| PyMuPDF (fitz) | 1.27.2 | PDF page re-rendering | Already core dependency (v1.2 Phase 10). page.get_pixmap(dpi=200) for re-rendering no-match pages per D-01 |
| Pillow (PIL) | 12.2.0 | Image analysis, blank page detection | Already core dependency. Image.histogram() for pixel distribution analysis, getextrema() for min/max pixel values |
| pytesseract | 0.3.13 | Single-pass OCR for diagnosis | Already core dependency. image_to_string() with existing config for capturing raw OCR text per D-02 |
| pathlib | stdlib | Path validation, file existence checks | Already used throughout codebase. .exists(), .is_file() for failed file re-verification per discretion area |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| argparse | stdlib | Subcommand CLI parsing | Already used in Phase 13. investigate subparser already wired at line 2293-2301 |
| re | stdlib | Error type extraction from notes field | Already used in categorize_errors() function at line 873 |
| csv | stdlib | QUOTE_NONNUMERIC for CSV export | Already used in cmd_lookup for no_match_pages.csv export |

### Alternatives Considered
None — all required tools already in the stack, zero new dependencies.

## Architecture Patterns

### Recommended Project Structure
```
precede_ocr.py
├── cmd_investigate(args)           # Main handler (lines 2228-2231 stub to replace)
├── investigate_failed_files()      # NEW: Re-verify file existence, categorize errors
├── investigate_no_match_pages()    # NEW: Re-render pages, detect blanks, run OCR
├── is_blank_page()                 # NEW: PIL histogram-based blank detection
├── generate_investigation_report() # NEW: Markdown report generation
└── categorize_errors()             # EXISTING: Reuse at line 860-885

tests/test_precede_ocr.py
└── TestInvestigateCommand          # NEW: TDD test class (11 tests recommended)
```

### Pattern 1: Subcommand Handler (follows cmd_lookup pattern)
**What:** Argparse Namespace unpacking, pandas CSV reading, validation, processing, output writing
**When to use:** All CLI subcommand implementations
**Example:**
```python
# Source: precede_ocr.py lines 2159-2226 (cmd_lookup)
def cmd_investigate(args):
    """Handler for investigate subcommand. Implements ERR-01 through ERR-04."""
    scan_csv_path = Path(args.scan_csv)
    report_path = Path(args.report)

    # Validate input file exists
    if not scan_csv_path.exists():
        print(f"Error: Scan CSV not found: {scan_csv_path}")
        sys.exit(1)

    # Read scan CSV
    try:
        df = pd.read_csv(scan_csv_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)

    # Validate expected columns
    required_cols = {'filename', 'page', 'id', 'notes'}
    if not required_cols.issubset(set(df.columns)):
        missing = required_cols - set(df.columns)
        print(f"Error: CSV missing required columns: {missing}")
        sys.exit(1)

    # Filter and process...
    # (processing logic here)

    # Write report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_content, encoding='utf-8')

    print(f"Investigation complete. Report written to {report_path}")
```

### Pattern 2: Error Filtering (reuse existing function)
**What:** Extract error rows from results DataFrame using categorize_errors()
**When to use:** Failed file investigation (ERR-01)
**Example:**
```python
# Source: precede_ocr.py lines 860-885
import re
from collections import Counter

def categorize_errors(results: list[dict]) -> dict[str, int]:
    """Extract and count error types from file-level error results."""
    error_pattern = re.compile(r'error:\s*(\w+):')
    error_counter = Counter()

    for r in results:
        notes = r.get('notes', '')
        if r.get('page') == 0 and 'error:' in notes:
            match = error_pattern.search(notes)
            if match:
                error_counter[match.group(1)] += 1
            else:
                error_counter['Unknown'] += 1

    return dict(error_counter.most_common())

# Usage in investigate:
error_rows = df[(df['page'] == 0) & (df['notes'].str.contains('error:', na=False))]
error_categories = categorize_errors(error_rows.to_dict('records'))
# error_categories = {'FileNotFoundError': 46, 'EmptyFileError': 3}
```

### Pattern 3: No-Match Filtering
**What:** Extract pages with no ID found (not errors, not successful)
**When to use:** No-match page investigation (ERR-02)
**Example:**
```python
# No-match convention per CONTEXT.md: page>0, empty ids, no "error:" in notes
no_match_rows = df[
    (df['page'] > 0) &                                    # Not error row
    (df['id'].isna() | (df['id'] == '')) &               # No ID found
    ~df['notes'].astype(str).str.startswith('error:', na=False)  # Not error
]
# Expected: ~59 rows matching production data
```

### Pattern 4: Blank Page Detection (PIL histogram analysis)
**What:** Analyze pixel distribution to detect all-white or all-black pages
**When to use:** Categorizing no-match pages (ERR-02)
**Example:**
```python
# Source: Web research on PIL histogram analysis
from PIL import Image

def is_blank_page(image: Image.Image, threshold: float = 0.99) -> tuple[bool, str]:
    """
    Detect if image is predominantly blank (white or black).

    Args:
        image: PIL Image object (RGB or L mode)
        threshold: Fraction of pixels that must be same color (default 0.99)

    Returns:
        (is_blank: bool, reason: str) - ("blank_white", "blank_black", or "")
    """
    # Convert to grayscale for simpler analysis
    if image.mode != 'L':
        image = image.convert('L')

    # Get histogram (256 bins for 0-255 grayscale values)
    hist = image.histogram()
    total_pixels = sum(hist)

    # Check if >99% of pixels are white (250-255 range)
    white_pixels = sum(hist[250:256])
    if white_pixels / total_pixels >= threshold:
        return True, "blank_white"

    # Check if >99% of pixels are black (0-5 range)
    black_pixels = sum(hist[0:6])
    if black_pixels / total_pixels >= threshold:
        return True, "blank_black"

    return False, ""
```

### Pattern 5: Page Re-rendering (PyMuPDF single page)
**What:** Re-open PDF and render specific page for diagnostic OCR
**When to use:** No-match page investigation per D-01/D-02
**Example:**
```python
# Source: precede_ocr.py lines 530-533 (DPI fallback pattern)
import fitz
from PIL import Image

def re_render_page(pdf_path: str, page_num: int, dpi: int = 200) -> Image.Image:
    """Re-render a specific page from PDF at given DPI."""
    doc = fitz.open(pdf_path)
    try:
        page = doc[page_num - 1]  # CSV uses 1-indexed, fitz uses 0-indexed
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img
    finally:
        doc.close()
```

### Pattern 6: Single-Pass OCR (diagnostic mode)
**What:** Run one OCR pass with standard config to capture raw text
**When to use:** No-match diagnosis per D-02 (not full 8-pass pipeline)
**Example:**
```python
# Source: precede_ocr.py lines 434-436 (OCR config)
import pytesseract

def run_diagnostic_ocr(image: Image.Image) -> str:
    """Run single OCR pass for diagnostic text capture."""
    # Use same config as main pipeline (Phase 11 benchmark)
    config = '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789 -c load_system_dawg=false -c load_freq_dawg=false'
    text = pytesseract.image_to_string(image, config=config).strip()
    return text
```

### Pattern 7: Markdown Report Generation
**What:** Build structured markdown with tables, sections, and copy-paste commands
**When to use:** ERR-04 quality report output
**Example:**
```python
# Source: pandas.DataFrame.to_markdown() + manual sections
def generate_investigation_report(failed_files_data, no_match_data, summary_stats):
    """Generate markdown investigation report per ERR-04."""
    sections = []

    # Header
    sections.append("# Error Investigation Report\n")
    sections.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    sections.append(f"**Scan CSV:** {scan_csv_path}\n\n")

    # Summary
    sections.append("## Summary\n\n")
    sections.append(f"- Total files processed: {summary_stats['total_files']}\n")
    sections.append(f"- Failed files: {summary_stats['failed_count']}\n")
    sections.append(f"- No-match pages: {summary_stats['no_match_count']}\n\n")

    # Failed Files Table (pandas to_markdown)
    if not failed_files_data.empty:
        sections.append("## Failed Files\n\n")
        sections.append(failed_files_data.to_markdown(index=False))
        sections.append("\n\n")

    # Copy-paste commands per D-04
    sections.append("### Recommended Actions\n\n")
    sections.append("```bash\n")
    sections.append("# Re-scan files that now exist:\n")
    sections.append("python precede_ocr.py scan <path> --fresh\n")
    sections.append("```\n\n")

    return "".join(sections)
```

### Anti-Patterns to Avoid
- **Full 8-pass OCR for diagnosis:** D-02 explicitly requires single-pass only. Full pipeline (4 rotations × 2 preprocessing states) is overkill and slow for categorization.
- **Modifying results.csv:** D-03 explicitly forbids modifications. Investigation is read-only.
- **Relying on notes metadata only:** D-01 requires re-rendering actual pages. Don't trust existing notes field alone for no-match diagnosis.
- **Hardcoded absolute paths in report:** Use relative paths or basename() so reports are portable.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Blank page detection | Custom pixel counting loops | PIL Image.histogram() | Optimized C implementation, handles all image modes, returns 256-bin distribution instantly |
| Markdown table generation | String concatenation with spacing | pandas DataFrame.to_markdown() | Handles column alignment, escaping, null values automatically |
| Error categorization | Manual string parsing loops | Existing categorize_errors() function | Already tested, handles edge cases (Unknown fallback), uses regex |
| CSV export with quoting | Manual csv.writer loops | pandas to_csv() with QUOTE_NONNUMERIC | Handles encoding, quoting, header, index=False consistently with cmd_lookup |

**Key insight:** This phase reuses 80%+ existing patterns from cmd_lookup (Phase 14) and core OCR functions (Phase 1-12). The only new logic is blank page detection (PIL histogram) and report formatting (markdown string building). Don't reimplement CSV handling, error parsing, or file validation.

## Common Pitfalls

### Pitfall 1: Assuming FileNotFoundError means file never existed
**What goes wrong:** Files may have been temporarily unavailable during scan but exist now
**Why it happens:** Network drives, external storage, file locks, antivirus scans
**How to avoid:** Re-verify file existence with pathlib .exists() during investigation (user discretion area recommends this)
**Warning signs:** Report shows "FileNotFoundError" but user says file is visible

### Pitfall 2: Treating all-white and all-black pages identically
**What goes wrong:** Blank white page = scanning issue; blank black page = PDF rendering issue (different root causes)
**Why it happens:** Both have no text, but black indicates alpha channel or rendering problem
**How to avoid:** Separate detection logic (white_pixels vs black_pixels in histogram), different categorization in report
**Warning signs:** User asks why some "blank" pages are actually black screens

### Pitfall 3: Running full OCR pipeline on 59 no-match pages
**What goes wrong:** D-02 requires single-pass only — running 8 passes takes 8x longer with no diagnostic value
**Why it happens:** Reusing extract_id_with_rotation() function (which does 8 passes + preprocessing)
**How to avoid:** Write separate run_diagnostic_ocr() function that does single pass, no rotation, no preprocessing
**Warning signs:** Investigation takes minutes instead of seconds

### Pitfall 4: Forgetting 1-indexed vs 0-indexed page numbers
**What goes wrong:** CSV stores page=1 for first page; PyMuPDF uses page[0] for first page
**Why it happens:** Different conventions between user-facing (1-indexed) and library (0-indexed)
**How to avoid:** Always `page_idx = csv_page_num - 1` when indexing into fitz document
**Warning signs:** "Page not found" errors or rendering wrong page

### Pitfall 5: Not handling PDF files that were moved/deleted
**What goes wrong:** CSV contains old paths, PDFs may have been reorganized since scan
**Why it happens:** Production scan was run days ago, file system may have changed
**How to avoid:** Wrap PDF opening in try/except, report "cannot re-verify" as separate category
**Warning signs:** FileNotFoundError during investigation for files that had different errors during scan

### Pitfall 6: Ambiguous "OCR failure" category
**What goes wrong:** "OCR failure" could mean blank page, low quality, or missing ID label (different fixes)
**Why it happens:** Lumping all non-blank/no-text cases together
**How to avoid:** Create subcategories: "blank_page" (PIL detects), "no_text_detected" (OCR returns empty), "text_found_no_id" (OCR returns text but no 5-digit match)
**Warning signs:** User can't tell which pages need rescanning vs which are legitimately blank

## Code Examples

Verified patterns from existing codebase and official sources:

### Failed File Investigation Pattern
```python
# Source: precede_ocr.py categorize_errors() + pandas filtering
def investigate_failed_files(df: pd.DataFrame) -> pd.DataFrame:
    """
    Re-verify failed files and categorize errors.
    Implements ERR-01.
    """
    from pathlib import Path

    # Filter to error rows (page=0, notes starts with "error:")
    error_rows = df[
        (df['page'] == 0) &
        (df['notes'].astype(str).str.startswith('error:', na=False))
    ].copy()

    # Extract error type from notes using existing categorize_errors pattern
    import re
    error_pattern = re.compile(r'error:\s*(\w+):')

    def extract_error_type(notes):
        match = error_pattern.search(notes)
        return match.group(1) if match else 'Unknown'

    error_rows['error_type'] = error_rows['notes'].apply(extract_error_type)

    # Re-verify file existence (user discretion recommends this)
    def check_exists(filename):
        return Path(filename).exists()

    error_rows['file_exists_now'] = error_rows['filename'].apply(check_exists)

    # Add recommendation column
    def get_recommendation(row):
        if row['error_type'] == 'FileNotFoundError' and row['file_exists_now']:
            return 'File now exists — rescan with: python precede_ocr.py scan {}'.format(row['filename'])
        elif row['error_type'] == 'EmptyFileError':
            return 'Zero-byte PDF — verify file integrity'
        else:
            return 'Manual investigation required'

    error_rows['recommendation'] = error_rows.apply(get_recommendation, axis=1)

    return error_rows[['filename', 'error_type', 'file_exists_now', 'notes', 'recommendation']]
```

### No-Match Page Investigation Pattern
```python
# Source: Combines PyMuPDF rendering + PIL histogram + pytesseract
def investigate_no_match_pages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Re-render and analyze no-match pages.
    Implements ERR-02 with D-01 and D-02 decisions.
    """
    import fitz
    from PIL import Image
    import pytesseract

    # Filter to no-match rows (page>0, no ID, not error)
    no_match_rows = df[
        (df['page'] > 0) &
        (df['id'].isna() | (df['id'] == '')) &
        ~df['notes'].astype(str).str.startswith('error:', na=False)
    ].copy()

    def diagnose_page(row):
        """Re-render page and categorize failure."""
        pdf_path = row['filename']
        page_num = int(row['page'])

        try:
            # Re-render page at DPI 200 (D-01)
            doc = fitz.open(pdf_path)
            page = doc[page_num - 1]  # Convert 1-indexed to 0-indexed
            pix = page.get_pixmap(dpi=200, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            doc.close()

            # Check if blank (D-02 quick scan)
            is_blank, blank_type = is_blank_page(img)
            if is_blank:
                return blank_type, "", "Blank page — verify source document"

            # Single OCR pass for text capture (D-02)
            config = '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789 -c load_system_dawg=false -c load_freq_dawg=false'
            text = pytesseract.image_to_string(img, config=config).strip()

            if not text:
                return "no_text_detected", "", "OCR found no text — check image quality"
            elif len(text) < 5 or not any(c.isdigit() for c in text):
                return "insufficient_text", text[:50], "OCR found text but no digits"
            else:
                return "text_no_id_match", text[:50], "OCR found digits but no 5-digit ID pattern"

        except Exception as e:
            return "investigation_failed", "", f"Could not re-render: {type(e).__name__}"

    # Apply diagnosis to each row
    no_match_rows[['category', 'ocr_sample', 'recommendation']] = no_match_rows.apply(
        lambda row: pd.Series(diagnose_page(row)), axis=1
    )

    return no_match_rows[['filename', 'page', 'category', 'ocr_sample', 'recommendation']]
```

### Blank Page Detection (PIL Histogram)
```python
# Source: PIL documentation + web research on histogram thresholding
def is_blank_page(image: Image.Image, threshold: float = 0.99) -> tuple[bool, str]:
    """
    Detect if image is predominantly blank using histogram analysis.

    Per ERR-02: Distinguish blank white (scanning issue) from blank black (rendering issue).

    Args:
        image: PIL Image (RGB or L mode)
        threshold: Fraction of pixels that must be uniform (default 0.99 = 99%)

    Returns:
        (is_blank, category) - (True, "blank_white"), (True, "blank_black"), or (False, "")
    """
    # Convert to grayscale for uniform analysis
    if image.mode != 'L':
        image = image.convert('L')

    # Get pixel value histogram (256 bins for 0-255 range)
    hist = image.histogram()
    total_pixels = sum(hist)

    # White detection: pixels in 250-255 range (near-white allows for compression artifacts)
    white_pixels = sum(hist[250:256])
    if white_pixels / total_pixels >= threshold:
        return True, "blank_white"

    # Black detection: pixels in 0-5 range (near-black)
    black_pixels = sum(hist[0:6])
    if black_pixels / total_pixels >= threshold:
        return True, "blank_black"

    return False, ""
```

### Markdown Report with DataFrame Tables
```python
# Source: pandas.DataFrame.to_markdown() + pathlib write_text
def generate_investigation_report(failed_df, no_match_df, scan_csv_path, report_path):
    """
    Generate markdown investigation report per ERR-04.

    Per D-04: Include copy-paste CLI commands for fixable errors.
    """
    from datetime import datetime

    sections = []

    # Header
    sections.append("# Error Investigation Report\n\n")
    sections.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    sections.append(f"**Scan CSV:** {scan_csv_path}\n\n")

    # Summary
    sections.append("## Summary\n\n")
    sections.append(f"- Failed files: {len(failed_df)}\n")
    sections.append(f"- No-match pages: {len(no_match_df)}\n\n")

    # Failed Files Section
    if not failed_df.empty:
        sections.append("## Failed Files Analysis\n\n")

        # Category breakdown
        error_counts = failed_df['error_type'].value_counts()
        sections.append("### Error Type Breakdown\n\n")
        for error_type, count in error_counts.items():
            sections.append(f"- **{error_type}**: {count} files\n")
        sections.append("\n")

        # Full table (pandas to_markdown)
        sections.append("### Detailed Findings\n\n")
        sections.append(failed_df.to_markdown(index=False))
        sections.append("\n\n")

        # Fixable errors (D-04 copy-paste commands)
        fixable = failed_df[
            (failed_df['error_type'] == 'FileNotFoundError') &
            (failed_df['file_exists_now'] == True)
        ]
        if not fixable.empty:
            sections.append("### Fixable Errors (Files Now Exist)\n\n")
            sections.append("```bash\n")
            for filename in fixable['filename'].unique():
                sections.append(f"python precede_ocr.py scan '{filename}'\n")
            sections.append("```\n\n")

    # No-Match Pages Section
    if not no_match_df.empty:
        sections.append("## No-Match Pages Analysis\n\n")

        # Category breakdown
        category_counts = no_match_df['category'].value_counts()
        sections.append("### Category Breakdown\n\n")
        for category, count in category_counts.items():
            sections.append(f"- **{category}**: {count} pages\n")
        sections.append("\n")

        # Full table
        sections.append("### Detailed Findings\n\n")
        sections.append(no_match_df.to_markdown(index=False))
        sections.append("\n\n")

    # Write to file
    report_content = "".join(sections)
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(report_content, encoding='utf-8')

    return report_path
```

## Environment Availability

All dependencies already installed — no external tools required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All investigation logic | ✓ | 3.14.2 | — |
| pandas | CSV reading, filtering, reporting | ✓ | 3.0.3 | — |
| PyMuPDF (fitz) | Page re-rendering | ✓ | 1.27.2 | — |
| Pillow (PIL) | Blank page detection | ✓ | 12.2.0 | — |
| pytesseract | Diagnostic OCR | ✓ | 0.3.13 | — |
| pytest | TDD test execution | ✓ | 9.0.2 | — |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini (testpaths=tests, python_files=test_*.py) |
| Quick run command | `pytest tests/test_precede_ocr.py::TestInvestigateCommand -x` |
| Full suite command | `pytest tests/test_precede_ocr.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ERR-01 | Failed file categorization (FileNotFoundError, EmptyFileError) | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_failed_file_categorization -x` | ❌ Wave 0 |
| ERR-01 | Failed file re-verification (existence check) | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_failed_file_reverification -x` | ❌ Wave 0 |
| ERR-02 | Blank page detection (white vs black) | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_blank_page_detection -x` | ❌ Wave 0 |
| ERR-02 | No-match page OCR diagnosis | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_no_match_diagnosis -x` | ❌ Wave 0 |
| ERR-03 | Copy-paste commands in report | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_fixable_error_commands -x` | ❌ Wave 0 |
| ERR-04 | Markdown report generation | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_markdown_report_generation -x` | ❌ Wave 0 |
| ERR-04 | no_match_pages.csv export | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_no_match_csv_export -x` | ❌ Wave 0 |
| ALL | CLI argument parsing (scan_csv positional, --report) | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_cli_args -x` | ❌ Wave 0 |
| ALL | Missing CSV file error handling | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_missing_csv_error -x` | ❌ Wave 0 |
| ALL | Invalid CSV columns error handling | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_invalid_csv_columns -x` | ❌ Wave 0 |
| ALL | End-to-end integration (sample CSV → report + CSV outputs) | integration | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_investigate_integration -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_precede_ocr.py::TestInvestigateCommand -x` (Phase 15 tests only)
- **Per wave merge:** `pytest tests/test_precede_ocr.py` (full suite, 247 existing + ~11 new = 258 tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_precede_ocr.py::TestInvestigateCommand` — new test class with ~11 tests covering ERR-01 through ERR-04
- [ ] Test fixtures: sample_error_csv, sample_no_match_csv, temp_pdf_with_blank_page (for re-rendering tests)
- [ ] Framework install: Already present (pytest 9.0.2) — no action needed

## Sources

### Primary (HIGH confidence)
- [precede_ocr.py lines 2159-2226](https://github.com/user/precedeocr) - cmd_lookup pattern for subcommand implementation
- [precede_ocr.py lines 860-885](https://github.com/user/precedeocr) - categorize_errors() function for error type extraction
- [precede_ocr.py lines 530-533](https://github.com/user/precedeocr) - PyMuPDF page.get_pixmap() rendering pattern
- [pandas 3.0.3 PyPI](https://pypi.org/project/pandas/) - DataFrame operations, to_markdown(), to_csv()
- [Pillow 12.2.0 PyPI](https://pypi.org/project/Pillow/) - Image.histogram() for pixel analysis
- [pytesseract 0.3.13 PyPI](https://pypi.org/project/pytesseract/) - image_to_string() API
- [pytest 9.0.2 PyPI](https://pypi.org/project/pytest/) - Test framework

### Secondary (MEDIUM confidence)
- [Pillow Concepts Documentation](https://pillow.readthedocs.io/en/stable/handbook/concepts.html) - Image modes, pixel access patterns
- [Thresholding of an Image using Python and Pillow](https://pythontic.com/image-processing/pillow/thresholding) - Histogram-based thresholding techniques
- [Tesseract OCR Not Working? - Fix Common Errors Easily](https://tesseract-ocr.com/troubleshoot/) - OCR failure diagnosis patterns
- [Intro to Image processing in Python with pillow - DEV Community](https://dev.to/kalebu/intro-to-image-processing-in-python-with-pillow-54lf) - PIL pixel analysis basics

### Tertiary (LOW confidence)
None — all techniques verified with official docs or existing codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All dependencies already installed and verified, zero new packages
- Architecture: HIGH - 80%+ reuses existing cmd_lookup pattern and core OCR functions
- Pitfalls: HIGH - Specific to this phase's user decisions (D-01/D-02 constraints), verified against production data format

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (30 days — stable domain, no fast-moving dependencies)
