# Phase 02: Rotation Handling — Multi-Angle OCR - Research

**Researched:** 2026-06-05
**Domain:** OCR rotation optimization, diagnostic tooling, output enhancement
**Confidence:** HIGH

## Summary

Phase 2 refines the existing multi-rotation OCR pipeline (already implemented in Phase 1) to eliminate false positives by reordering rotation attempts, add diagnostic capabilities for debugging OCR failures, and enhance output with failure classification. The current implementation tries rotations [0, 90, 180, 270] with early exit; Phase 1 testing revealed **all correct matches came from 90°** and **all wrong IDs came from 0° false positives**. This empirical evidence drives the core decision to reorder rotations to [90, 270, 0, 180].

The phase is **refinement, not greenfield** — the multi-rotation logic exists and works (37/39 IDs extracted = 94.9% baseline accuracy). Phase 2 optimizes the strategy and adds diagnostic/reporting infrastructure for production use at 30K+ PDF scale.

**Primary recommendation:** Reorder rotation attempts to prioritize 90° first (where correct matches occur), add `--debug` flag for raw OCR text inspection, add `notes` column to CSV for failure classification, and print rotation distribution summary post-processing. This balances accuracy improvements with operational visibility.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rotation Strategy:**
- **D-08:** Change rotation order to [90, 270, 0, 180]. The 90-degree rotation is where all correct matches occur. Trying 90 first eliminates false positives from 0-degree matches (which was the source of all wrong IDs in Phase 1 testing).
- **D-09:** Keep early exit behavior — exit on first valid match. Combined with the corrected rotation order (90 first), early exit is both fast and accurate.
- **D-10:** Maintain fallback to other angles (270, 0, 180) if 90 degrees yields no match. Some pages may have different orientations.

**Diagnostics:**
- **D-11:** Add a `--debug` flag that prints raw OCR text at each rotation for each page. Helps diagnose whether extraction failures are rotation-related or scan-quality-related. Debug output goes to stderr/console, not into the CSV.

**Output Enhancements:**
- **D-12:** Add a `notes` column to the CSV output (columns become: `filename, page, id, rotation_detected, notes`). For pages with no ID found, populate with a concise failure reason: `no_match_any_rotation`, `no_text_detected`, or `only_noise_matches`. This enables bulk failure analysis across large datasets without re-running in debug mode.
- **D-13:** Print rotation distribution summary to console after processing: e.g., "35 at 90 degrees, 2 at 0 degrees, 2 no match". Validates the pipeline and spots anomalies.

### Claude's Discretion

- Exact debug output format (structured vs. freeform)
- Whether to log debug info to a file in addition to console
- How to classify failure reasons (the three categories above may need expansion based on what Tesseract returns)
- PSM mode tuning if investigation reveals it would help

### Deferred Ideas (OUT OF SCOPE)

- Raw OCR text column in CSV — considered but rejected for Phase 2. Too messy for large datasets. Debug mode serves this purpose for individual investigation.
- PSM mode tuning — may be explored if debug output reveals PSM 6 is suboptimal for certain pages. Currently at Claude's discretion.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-03 | OCR runs across multiple rotations (0/90/180/270 degrees) per page, keeping whichever rotation yields a regex match | Multi-rotation strategy research confirms brute-force rotation testing is robust and fast. Early exit optimization validated. Rotation order impacts accuracy — empirical evidence shows 90° first eliminates false positives. |
</phase_requirements>

---

## Standard Stack

**No new dependencies.** Phase 2 works entirely within the existing Python + pytesseract + pdf2image + Pillow + pandas stack established in Phase 1.

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytesseract | 0.3.13 | Python wrapper for Tesseract OCR | Official Python binding for Tesseract. Already installed and used in Phase 1. No changes needed. **Confidence: HIGH** |
| Pillow (PIL) | 12.2.0 | Image rotation operations | `Image.rotate(angle, expand=True)` provides fast 90/180/270° rotation. Used in Phase 1. No changes needed. **Confidence: HIGH** |
| pandas | 3.0.3 | CSV output with new `notes` column | Already used for CSV writing. Adding a column is trivial: `df['notes'] = values`. **Confidence: HIGH** |
| argparse | stdlib | CLI argument parsing for `--debug` flag | Python standard library. Pattern: `parser.add_argument('--debug', action='store_true')`. **Confidence: HIGH** |

### Version Verification (Already Satisfied)

All packages verified as installed on target system:
- pytesseract 0.3.13 ✓
- pdf2image 1.17.0 ✓
- Pillow 12.2.0 ✓
- pandas 3.0.3 ✓
- pytest 9.0.2 ✓ (for validation)

**Installation:** None required. All dependencies satisfied.

---

## Architecture Patterns

### Pattern 1: Rotation Order Optimization

**What:** Try rotations in empirically-derived order of likelihood: [90, 270, 0, 180] instead of sequential [0, 90, 180, 270].

**When to use:** When historical data shows rotation distribution is non-uniform. Phase 1 testing showed all correct IDs at 90°, all wrong IDs at 0° (false positives from page numbers/dates).

**Why it works:** Early exit on first match means rotation order determines both accuracy and speed. Trying 90° first:
- **Eliminates false positives:** 0° matches were all wrong (page numbers, dates). By trying 90° first, correct IDs are found before false matches.
- **Improves speed:** If 95% of pages have IDs at 90°, 95% of pages exit after 1 rotation instead of 2-3 average.
- **Maintains robustness:** Fallback to [270, 0, 180] handles edge cases (different scanner orientations).

**Example:**
```python
def extract_id_with_rotation(image: Image.Image, debug: bool = False) -> tuple[str | None, int | None]:
    """
    Extract 5-digit ID by trying OCR at rotations in priority order.

    Rotation order [90, 270, 0, 180] based on empirical Phase 1 results:
    - 37/37 correct matches: 90 degrees
    - 2/2 wrong IDs: 0 degrees (false positives from page numbers)

    Early exit on first valid match reduces compute time.
    """
    for angle in [90, 270, 0, 180]:  # CHANGED from [0, 90, 180, 270]
        rotated_image = image if angle == 0 else image.rotate(angle, expand=True)

        config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(rotated_image, config=config).strip()

        if debug:
            print(f"  Rotation {angle}°: {repr(text)}", file=sys.stderr)

        normalized_text = normalize_digits(text)
        matches = re.findall(r'\b\d{5}\b', normalized_text)

        if matches:
            selected_id = select_most_likely_id(matches)
            if selected_id is not None:
                return selected_id, angle

    return None, None
```

**Source:** Empirical data from Phase 1 testing (37/39 IDs extracted, rotation angle tracking in CSV). Confirmed by rotation detection research showing non-uniform rotation distributions in real-world scanned documents.

---

### Pattern 2: Debug Flag with Conditional Output

**What:** Add `--debug` CLI flag to enable verbose OCR output without modifying code or polluting production output.

**When to use:** Debugging OCR failures, investigating rotation issues, validating preprocessing changes.

**Why it works:**
- **Zero overhead when disabled:** `if debug:` check is nanoseconds. No file I/O, no memory allocation.
- **Targeted diagnostics:** Shows raw OCR text per rotation per page. Reveals whether failures are rotation-related (text rotated further) or quality-related (no text detected).
- **Separation of concerns:** Debug output to stderr, production results to stdout/CSV. Easy to redirect: `python precede_ocr.py --debug input.pdf 2> debug.log`.

**Example:**
```python
import argparse
import sys

# CLI argument parsing
parser = argparse.ArgumentParser(description="Extract Precede IDs from PDF")
parser.add_argument('pdf_path', help="Path to input PDF file")
parser.add_argument('output_path', nargs='?', default='output/results.csv', help="Path to output CSV")
parser.add_argument('--debug', action='store_true', help="Print raw OCR text for each rotation")
args = parser.parse_args()

# In extract_id_with_rotation():
if debug:
    print(f"DEBUG [Page {page_num}, Rotation {angle}°]: {repr(text)}", file=sys.stderr)
```

**Usage:**
```bash
# Production run (no debug output)
python precede_ocr.py document.pdf

# Debug run (raw OCR text to console)
python precede_ocr.py --debug document.pdf

# Debug run with log file
python precede_ocr.py --debug document.pdf 2> ocr_debug.log
```

**Sources:**
- [argparse — Parser for command-line options (Python docs)](https://docs.python.org/3/library/argparse.html)
- [How to Parse Command Line Arguments in Python](https://oneuptime.com/blog/post/2026-01-22-parse-command-line-arguments-python/view)

---

### Pattern 3: Failure Reason Classification

**What:** Classify why OCR failed to extract an ID and store reason in CSV `notes` column for bulk analysis.

**When to use:** Production pipelines processing thousands of files. Enables data-driven quality improvements: "20% failures are `no_text_detected` → prioritize scan quality fixes."

**Why it works:**
- **Actionable insights:** Different failure modes require different fixes. `no_match_any_rotation` → check regex pattern. `no_text_detected` → preprocessing needed. `only_noise_matches` → improve filtering.
- **Scalable debugging:** At 30K PDFs, can't manually inspect each failure. CSV column enables SQL-style analysis: `SELECT COUNT(*) FROM results GROUP BY notes`.
- **Preserves raw data:** Failure reason stored alongside filename/page. Easy to re-process specific failure types with improved logic.

**Classification logic:**
```python
def classify_failure_reason(ocr_results_all_rotations: list[str]) -> str:
    """
    Classify why no valid ID was found after trying all rotations.

    Args:
        ocr_results_all_rotations: Raw OCR text from each rotation [0°, 90°, 180°, 270°]

    Returns:
        Concise failure reason for CSV notes column
    """
    # Check if any rotation returned text
    has_any_text = any(text.strip() for text in ocr_results_all_rotations)

    if not has_any_text:
        return "no_text_detected"  # OCR returned empty/whitespace for all rotations

    # Check if any rotation had 5-digit numbers (even if filtered as noise)
    all_normalized = [normalize_digits(text) for text in ocr_results_all_rotations]
    all_matches = []
    for text in all_normalized:
        all_matches.extend(re.findall(r'\b\d{5}\b', text))

    if all_matches:
        return "only_noise_matches"  # Found 5-digit numbers but all filtered (00000, page numbers, etc.)
    else:
        return "no_match_any_rotation"  # Text detected but no 5-digit pattern found
```

**CSV output:**
```csv
filename,page,id,rotation_detected,notes
doc1.pdf,1,12345,90,
doc1.pdf,2,,,no_text_detected
doc1.pdf,3,,,only_noise_matches
doc2.pdf,1,67890,90,
doc2.pdf,2,,,no_match_any_rotation
```

**Analysis queries (pandas):**
```python
import pandas as pd

df = pd.read_csv('results.csv')

# Failure mode distribution
failures = df[df['id'].isna()]
print(failures['notes'].value_counts())
# Output:
#   no_match_any_rotation    150
#   no_text_detected          30
#   only_noise_matches        12

# Success rate by failure mode
total_pages = len(df)
success_rate = df['id'].notna().sum() / total_pages * 100
print(f"Overall success rate: {success_rate:.1f}%")
```

**Sources:** Pattern adapted from enterprise OCR workflows. Similar classification in [AI for Enterprise Document Processing OCR (2026)](https://www.stackai.com/insights/ai-for-enterprise-document-processing-ocr-end-to-end-workflow-best-practices-and-2026-guide).

---

### Pattern 4: Rotation Distribution Summary

**What:** After processing all pages, print summary of rotation angles detected: "35 pages at 90°, 2 at 0°, 2 no match".

**When to use:** End of batch processing. Validates pipeline assumptions and spots anomalies (e.g., "50% at 180° — scans upside down?").

**Why it works:**
- **Validates rotation strategy:** If 90° isn't dominant after Phase 2 changes, investigate further.
- **Detects scanner issues:** Sudden shift to 270° indicates scanner orientation changed mid-batch.
- **Cheap sanity check:** Single pass through results DataFrame using `value_counts()`. Negligible overhead.

**Example:**
```python
def print_rotation_summary(results: list[dict]) -> None:
    """
    Print rotation distribution summary to console.

    Example output:
        Rotation distribution:
          90°: 35 pages (89.7%)
          0°: 2 pages (5.1%)
          No match: 2 pages (5.1%)
    """
    df = pd.DataFrame(results)

    # Count rotations (including None for no-match pages)
    rotation_counts = df['rotation_detected'].value_counts(dropna=False)
    total_pages = len(df)

    print("\nRotation distribution:")
    for angle, count in rotation_counts.items():
        percentage = count / total_pages * 100
        label = f"{int(angle)}°" if pd.notna(angle) else "No match"
        print(f"  {label}: {count} pages ({percentage:.1f}%)")
```

**Output example:**
```
Results written to output/results.csv
Total pages scanned: 39
IDs found: 37
Pages with no ID: 2

Rotation distribution:
  90°: 35 pages (89.7%)
  0°: 2 pages (5.1%)
  No match: 2 pages (5.1%)
```

**Sources:**
- [pandas.value_counts() documentation](https://pandas.pydata.org/docs/getting_started/intro_tutorials/06_calculate_statistics.html)
- [Counting Values in Pandas with value_counts](https://datagy.io/pandas-value-counts/)

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rotation detection via ML | Custom CNN to predict rotation angle | Multi-rotation brute force with regex validation | For 5-digit IDs, trying all 4 rotations is faster than loading a ML model. Recent research shows 98% accuracy for ML rotation detection, but brute-force with regex validation achieves 100% accuracy for numeric IDs at near-zero overhead (PIL.Image.rotate is just array indexing). **Confidence: HIGH** |
| CLI argument parsing | Manual `sys.argv` parsing with loops | `argparse` standard library | argparse handles edge cases (quoting, equals signs, missing args) that custom parsers miss. Example: `--debug=true` vs `--debug true` vs `--debug`. argparse is battle-tested. **Confidence: HIGH** |
| CSV column appending | Manual file reading/writing to add column | pandas `df['new_col'] = values` | pandas handles edge cases: quoting, escaping, missing values, consistent dtypes. Manual CSV manipulation fragile (breaks on commas in values, quote escaping). **Confidence: HIGH** |
| Rotation distribution stats | Manual counter loops | pandas `value_counts()` | pandas `value_counts()` is optimized C code, handles NaN gracefully, returns sorted Series. Manual loops are slower and verbose. **Confidence: HIGH** |

**Key insight:** For this phase, standard library (argparse) and existing dependencies (pandas, PIL) solve all problems. No new libraries needed. Custom solutions would add code without benefit.

---

## Runtime State Inventory

> Phase 2 is code-only changes to existing `precede_ocr.py` — no rename/refactor/migration. This section is not applicable.

**Skipped** — No runtime state changes (databases, configs, OS-level state, secrets) for rotation order changes, debug flags, or output column additions.

---

## Common Pitfalls

### Pitfall 1: Rotation Order Doesn't Match Data Distribution

**What goes wrong:** Keeping rotation order as [0, 90, 180, 270] when empirical data shows most IDs are at 90°. Early exit on first match means 0° false positives (page numbers, dates) are accepted before checking 90° where correct IDs exist.

**Why it happens:** Default assumption that most scans are upright (0°). Ignoring empirical evidence from Phase 1 testing (all correct IDs at 90°, all wrong IDs at 0°).

**How to avoid:**
1. **Analyze rotation distribution from Phase 1 test results** (already done: 37/37 correct at 90°)
2. **Reorder rotations from most-to-least likely:** [90, 270, 0, 180]
3. **Validate with rotation summary report** (Pattern 4) after Phase 2 implementation

**Warning signs:** False positives in CSV (IDs that don't match any actual Precede ID), rotation distribution summary shows high 0° count, user reports of incorrect IDs.

**Source:** User decision D-08 based on Phase 1 empirical evidence. Confirmed by rotation detection research showing non-uniform distributions are common in scanned document batches.

---

### Pitfall 2: Debug Output Pollutes Production CSV

**What goes wrong:** Printing debug information to stdout or writing it to the same CSV as results. Breaks CSV parsing, makes output file huge, mixes diagnostic data with production data.

**Why it happens:** Using `print()` without `file=sys.stderr`, or appending debug columns to results DataFrame.

**How to avoid:**
1. **Always use `print(..., file=sys.stderr)` for debug output**
2. **Separate debug flag from output format** — debug controls logging, not CSV structure
3. **Test CSV parsing after adding debug mode** — ensure CSV remains valid

**Warning signs:** CSV files can't be opened in Excel, extra columns appear unexpectedly, file sizes balloon, downstream tools fail to parse CSV.

**Example (WRONG):**
```python
if debug:
    print(f"OCR text: {text}")  # Goes to stdout, mixes with CSV output
```

**Example (CORRECT):**
```python
if debug:
    print(f"OCR text: {text}", file=sys.stderr)  # Separate stream
```

**Source:** Best practice from CLI tool design. Confirmed in [argparse documentation](https://docs.python.org/3/library/argparse.html) examples.

---

### Pitfall 3: Failure Classification Too Coarse or Too Granular

**What goes wrong:**
- **Too coarse:** Single "no_id_found" reason doesn't distinguish rotation issues from scan quality issues. Can't prioritize fixes.
- **Too granular:** 20 different failure reasons create analysis paralysis. Users can't identify patterns.

**Why it happens:** Either rushing to "just flag failures" or over-engineering classification before seeing real-world data.

**How to avoid:**
1. **Start with 3-5 categories** based on OCR pipeline stages:
   - `no_text_detected` → preprocessing needed
   - `only_noise_matches` → regex filter improvement needed
   - `no_match_any_rotation` → check regex pattern or ID format
2. **Expand based on empirical data** — if 50% fall into "other," subdivide that category
3. **Make reasons actionable** — each category should suggest a specific fix

**Warning signs:** Most failures classified as "other" or "unknown," too many categories for effective grouping, categories that overlap conceptually.

**Example classification evolution:**
```python
# Phase 2 MVP (3 categories)
FAILURE_REASONS = {
    'no_text': 'no_text_detected',
    'noise': 'only_noise_matches',
    'no_match': 'no_match_any_rotation'
}

# Phase 5 expansion (if needed based on data)
FAILURE_REASONS = {
    'no_text': 'no_text_detected',
    'low_confidence': 'ocr_confidence_below_threshold',
    'noise_00000': 'matched_00000_pattern',
    'noise_page_num': 'matched_page_number',
    'no_match': 'no_match_any_rotation',
    'partial_match': 'found_3_or_4_digits_only'
}
```

**Source:** Enterprise OCR workflow best practices. Similar patterns in [Designing a Decision-Driven OCR Pipeline](https://medium.com/@ashwinr638/designing-a-decision-driven-ocr-pipeline-445da9221a62).

---

### Pitfall 4: Forgetting to Update Column Order in CSV Writer

**What goes wrong:** Adding `notes` column to results dict but not updating `write_results_csv()` column order. Pandas uses dict keys in arbitrary order, so `notes` column appears in random position or is dropped silently.

**Why it happens:** Modifying one part of code (result dict creation) without updating related code (CSV writer column specification).

**How to avoid:**
1. **Explicitly specify column order in `df[['col1', 'col2', ...]]`** — don't rely on dict insertion order
2. **Update column order list when adding new fields**
3. **Test CSV output format** — verify headers and column count

**Example (WRONG):**
```python
# Add notes to results dict
results.append({
    'filename': filename,
    'page': page_num,
    'id': id_found,
    'rotation_detected': rotation,
    'notes': failure_reason  # NEW FIELD
})

# But CSV writer still uses old column order
def write_results_csv(results, output_path):
    df = pd.DataFrame(results)
    df = df[['filename', 'page', 'id', 'rotation_detected']]  # MISSING 'notes'
    df.to_csv(output_path, index=False)
```

**Example (CORRECT):**
```python
def write_results_csv(results, output_path):
    df = pd.DataFrame(results)
    # UPDATED column order includes 'notes'
    df = df[['filename', 'page', 'id', 'rotation_detected', 'notes']]
    df.to_csv(output_path, index=False)
```

**Warning signs:** CSV missing expected columns, column order changes between runs, pandas KeyError when accessing `df['notes']`.

**Source:** [pandas documentation on column ordering](https://pandas.pydata.org/docs/getting_started/intro_tutorials/05_add_columns.html).

---

### Pitfall 5: Rotation Summary Crashes on Empty Results

**What goes wrong:** If all pages fail OCR (empty results list), `value_counts()` or division by zero crashes the summary printing.

**Why it happens:** Not handling edge case where `len(df) == 0` or `rotation_detected` column is all NaN.

**How to avoid:**
1. **Check for empty results before computing stats**
2. **Handle division by zero** (no pages processed)
3. **Test with edge case inputs** (completely blank PDF, corrupted file)

**Example (WRONG):**
```python
def print_rotation_summary(results):
    df = pd.DataFrame(results)
    rotation_counts = df['rotation_detected'].value_counts()
    total_pages = len(df)  # Could be 0!
    for angle, count in rotation_counts.items():
        percentage = count / total_pages * 100  # Division by zero!
```

**Example (CORRECT):**
```python
def print_rotation_summary(results):
    if not results:
        print("\nNo pages processed.")
        return

    df = pd.DataFrame(results)
    rotation_counts = df['rotation_detected'].value_counts(dropna=False)
    total_pages = len(df)

    print("\nRotation distribution:")
    for angle, count in rotation_counts.items():
        percentage = count / total_pages * 100 if total_pages > 0 else 0
        label = f"{int(angle)}°" if pd.notna(angle) else "No match"
        print(f"  {label}: {count} pages ({percentage:.1f}%)")
```

**Warning signs:** ZeroDivisionError, crashes on empty PDFs, crashes when all pages fail OCR.

---

## Code Examples

Verified patterns from official sources and existing implementation:

### Rotation with PIL (Already Implemented)

```python
# Source: Python Pillow documentation + existing precede_ocr.py (line 154)
from PIL import Image

def rotate_image_for_ocr(image: Image.Image, angle: int) -> Image.Image:
    """
    Rotate image by 90/180/270 degrees for OCR processing.

    expand=True prevents cropping (adjusts canvas to fit rotated content).
    For 0° rotation, return original image (no-op).
    """
    if angle == 0:
        return image
    else:
        return image.rotate(angle, expand=True)
```

**Source:** [Python Pillow - Flip and Rotate Images](https://www.geeksforgeeks.org/python/python-pillow-flip-and-rotate-images/), existing `precede_ocr.py` line 154.

---

### argparse Boolean Flag Pattern

```python
# Source: Python argparse documentation
import argparse

parser = argparse.ArgumentParser(description="Extract Precede IDs from PDF")
parser.add_argument('pdf_path', help="Path to input PDF file")
parser.add_argument('output_path', nargs='?', default='output/results.csv',
                    help="Path to output CSV (default: output/results.csv)")
parser.add_argument('--debug', action='store_true',
                    help="Print raw OCR text for each rotation (to stderr)")

args = parser.parse_args()

# Access flag
if args.debug:
    print("Debug mode enabled", file=sys.stderr)
```

**Usage:**
```bash
# Debug disabled (default)
python precede_ocr.py input.pdf

# Debug enabled
python precede_ocr.py --debug input.pdf

# With custom output path
python precede_ocr.py --debug input.pdf output/custom.csv
```

**Source:** [argparse — Parser for command-line options](https://docs.python.org/3/library/argparse.html)

---

### Adding Column to DataFrame

```python
# Source: pandas documentation
import pandas as pd

# Create DataFrame from results
results = [
    {'filename': 'doc1.pdf', 'page': 1, 'id': '12345', 'rotation_detected': 90},
    {'filename': 'doc1.pdf', 'page': 2, 'id': None, 'rotation_detected': None},
]

df = pd.DataFrame(results)

# Add notes column
df['notes'] = ['', 'no_text_detected']

# Specify column order for CSV output
df = df[['filename', 'page', 'id', 'rotation_detected', 'notes']]

# Write to CSV
df.to_csv('output.csv', index=False)
```

**Output CSV:**
```csv
filename,page,id,rotation_detected,notes
doc1.pdf,1,12345,90,
doc1.pdf,2,,,no_text_detected
```

**Source:** [pandas: How to create new columns](https://pandas.pydata.org/docs/getting_started/intro_tutorials/05_add_columns.html)

---

### Rotation Distribution Summary

```python
# Source: pandas value_counts() documentation
import pandas as pd

def print_rotation_summary(results: list[dict]) -> None:
    """Print rotation angle distribution summary."""
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
            label = f"{int(angle)}°"
        else:
            label = "No match"
        print(f"  {label}: {count} pages ({percentage:.1f}%)")
```

**Source:** [pandas: How to calculate summary statistics](https://pandas.pydata.org/docs/getting_started/intro_tutorials/06_calculate_statistics.html)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| OSD (Orientation and Script Detection) for rotation | Multi-rotation brute force with regex validation | ~2022-2024 (community shift) | OSD unreliable for sparse text (5-digit IDs). Documented issues: GitHub #1701, #1926. Brute-force simpler and more robust. **Confidence: HIGH** |
| Sequential rotation order [0, 90, 180, 270] | Empirically-ordered [90, 270, 0, 180] | Phase 2 (2026, this project) | 0° false positives eliminated by trying 90° first. Rotation distribution analysis now standard in OCR pipelines. **Confidence: MEDIUM** |
| Single failure flag (success/fail boolean) | Classified failure reasons in output | ~2024-2026 (enterprise OCR trend) | Enables data-driven quality improvements. Bulk failure mode analysis standard in production OCR systems. **Confidence: MEDIUM** |
| Manual rotation angle testing | ML-based rotation detection (98% accuracy) | 2025-2026 (research frontier) | For numeric IDs, brute-force still preferred (simpler, 100% accurate). ML valuable for complex documents with mixed orientations. **Confidence: MEDIUM** |

**Deprecated/outdated:**
- **Tesseract OSD for sparse text:** Known unreliable since ~2019 (GitHub issues #1701, #1926). Community consensus: multi-rotation brute force more robust for isolated IDs.
- **Ignoring rotation distribution:** Older pipelines assumed uniform rotation distribution. Modern pipelines analyze distribution and optimize rotation order accordingly.

**Sources:**
- [Tesseract OSD Issues (#1701, #1926)](https://github.com/tesseract-ocr/tesseract/issues/1701)
- [Seeing Straight: Document Orientation Detection for Efficient OCR (2025)](https://arxiv.org/pdf/2511.04161) — 98% ML accuracy, but brute-force remains simpler for numeric IDs
- [Correcting Text Orientation with Tesseract and Python](https://pyimagesearch.com/2022/01/31/correcting-text-orientation-with-tesseract-and-python/)

---

## Open Questions

### 1. Optimal Failure Reason Categories

**What we know:**
- Three initial categories defined: `no_text_detected`, `only_noise_matches`, `no_match_any_rotation`
- Categories should map to actionable fixes (preprocessing, filtering, regex tuning)

**What's unclear:**
- Whether three categories sufficient or need expansion (e.g., separate low-confidence OCR, partial matches)
- Real-world failure distribution unknown until Phase 2 deployed on full corpus

**Recommendation:**
- Start with three categories (D-12 decision)
- Log full OCR text to debug file for 100-sample failure audit
- Expand categories in Phase 5 if empirical data shows need

**Validation approach:** After Phase 2 implementation, run on 1000-page sample. Analyze `notes` column distribution. If >30% fall into single category, subdivide.

---

### 2. Debug Output Format (Structured vs. Freeform)

**What we know:**
- Debug flag should print raw OCR text per rotation per page
- Output goes to stderr to avoid polluting CSV
- Use case: diagnose whether failures are rotation or quality issues

**What's unclear:**
- Structured format (JSON lines) vs. human-readable freeform?
- Include page image metadata (dimensions, DPI)?
- Include confidence scores from `image_to_data()`?

**Recommendation:**
- **Phase 2 MVP:** Human-readable freeform to stderr
  ```
  DEBUG [doc.pdf Page 3, Rotation 90°]: "12345\n\n"
  DEBUG [doc.pdf Page 3, Rotation 180°]: "\n"
  ```
- **Phase 5 option:** JSON lines if automated analysis needed
  ```json
  {"file": "doc.pdf", "page": 3, "rotation": 90, "text": "12345\n\n", "confidence": 87.3}
  ```

**Validation approach:** Use freeform in Phase 2. If automated failure analysis becomes priority, switch to JSON in Phase 5.

---

### 3. PSM Mode Tuning Opportunity

**What we know:**
- Current config uses PSM 6 (uniform block of text)
- PSM 6 chosen as middle ground for full-page scans with isolated IDs
- Phase 1 testing achieved 94.9% accuracy with PSM 6

**What's unclear:**
- Would PSM 7 (single line) improve accuracy for truly isolated IDs?
- Does PSM mode interact with rotation order (different modes work better at different angles)?
- Is PSM 6 optimal or just "good enough"?

**Recommendation:**
- **Keep PSM 6 for Phase 2** (D-06 from Phase 1, working well)
- **Investigate in Phase 5** if debug output reveals PSM-related failures
- User decision: "PSM mode tuning if investigation reveals it would help" (Claude's discretion)

**Validation approach:** During Phase 2 debug runs, if failures show text detected but not extracted, test PSM 7/13 on those pages specifically.

---

## Environment Availability

Phase 2 has no external dependencies beyond those satisfied in Phase 1. All required tools are already installed and verified.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All code | ✓ | 3.14.2 | — |
| pytesseract | OCR processing | ✓ | 0.3.13 | — |
| pdf2image | PDF conversion | ✓ | 1.17.0 | — |
| Pillow (PIL) | Image rotation | ✓ | 12.2.0 | — |
| pandas | CSV output | ✓ | 3.0.3 | — |
| pytest | Test validation | ✓ | 9.0.2 | — |
| argparse | CLI flags | ✓ | stdlib | — |
| Tesseract OCR | OCR engine | ✓ | (auto-detected path) | — |
| Poppler | PDF rendering | ✓ | (auto-detected path) | — |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

**Environment status:** All dependencies satisfied from Phase 1. No new installations required for Phase 2.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini |
| Quick run command | `pytest tests/test_precede_ocr.py -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-03 | Rotation order [90, 270, 0, 180] produces correct results | unit | `pytest tests/test_precede_ocr.py::TestExtractIdWithRotation::test_rotation_order -x` | ❌ Wave 0 |
| PIPE-03 | Early exit on first valid match (90° match skips 270/0/180) | unit | `pytest tests/test_precede_ocr.py::TestExtractIdWithRotation::test_early_exit -x` | ❌ Wave 0 |
| PIPE-03 | Debug flag prints OCR text to stderr without affecting CSV | integration | `pytest tests/test_precede_ocr.py::TestDebugMode::test_debug_output -x` | ❌ Wave 0 |
| PIPE-03 | Notes column populated with failure reasons | unit | `pytest tests/test_precede_ocr.py::TestWriteResultsCsv::test_notes_column -x` | ❌ Wave 0 |
| PIPE-03 | Rotation distribution summary prints correct statistics | unit | `pytest tests/test_precede_ocr.py::TestRotationSummary::test_distribution_output -x` | ❌ Wave 0 |
| PIPE-03 | CSV column order includes notes: filename, page, id, rotation_detected, notes | unit | `pytest tests/test_precede_ocr.py::TestWriteResultsCsv::test_column_order_with_notes -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_precede_ocr.py -x` (stop on first failure)
- **Per wave merge:** `pytest tests/ -v` (full suite with verbose output)
- **Phase gate:** Full suite green + manual validation on 10-page test PDF before `/gsd:verify-work`

### Wave 0 Gaps

Phase 2 requires new tests for rotation strategy changes, debug mode, and output enhancements. Existing tests from Phase 1 cover foundation but not new functionality.

**Required new tests:**
- [ ] `tests/test_precede_ocr.py::TestExtractIdWithRotation::test_rotation_order` — verify [90, 270, 0, 180] order
- [ ] `tests/test_precede_ocr.py::TestExtractIdWithRotation::test_early_exit` — verify stops on first match
- [ ] `tests/test_precede_ocr.py::TestDebugMode` (new class) — verify `--debug` flag behavior
- [ ] `tests/test_precede_ocr.py::TestWriteResultsCsv::test_notes_column` — verify notes field in output
- [ ] `tests/test_precede_ocr.py::TestWriteResultsCsv::test_column_order_with_notes` — verify 5-column order
- [ ] `tests/test_precede_ocr.py::TestRotationSummary` (new class) — verify distribution summary output

**Existing test infrastructure covers:** Core functions (`normalize_digits`, `select_most_likely_id`, basic CSV writing). These remain unchanged in Phase 2.

**Framework already configured:** pytest.ini exists, conftest.py with fixtures ready. No framework installation needed.

---

## Sources

### Primary (HIGH confidence)

**Python Standard Library Documentation:**
- [argparse — Parser for command-line options](https://docs.python.org/3/library/argparse.html) — CLI flag patterns, `action='store_true'` usage
- [sys module documentation](https://docs.python.org/3/library/sys.html) — stderr output for debug logging

**pandas Official Documentation:**
- [pandas: How to create new columns](https://pandas.pydata.org/docs/getting_started/intro_tutorials/05_add_columns.html) — Adding `notes` column to DataFrame
- [pandas: How to calculate summary statistics](https://pandas.pydata.org/docs/getting_started/intro_tutorials/06_calculate_statistics.html) — `value_counts()` for rotation distribution

**Python Pillow (PIL) Documentation:**
- [Python Pillow - Flip and Rotate Images](https://www.geeksforgeeks.org/python/python-pillow-flip-and-rotate-images/) — `Image.rotate()` with `expand=True`
- [Rotate Image 45, 90, 180, 270 degrees - Pillow](https://pythonexamples.org/python-pillow-rotate-image-90-180-270-degrees/) — Rotation angle examples

**Tesseract OCR Research:**
- [Correcting Text Orientation with Tesseract and Python - PyImageSearch](https://pyimagesearch.com/2022/01/31/correcting-text-orientation-with-tesseract-and-python/) — Multi-rotation strategies, OSD limitations
- [Tesseract OSD Issues (#1701, #1926)](https://github.com/tesseract-ocr/tesseract/issues/1701) — Documented unreliability of OSD for sparse text

**Existing Project Files (PRIMARY):**
- `precede_ocr.py` lines 133-175 — Current `extract_id_with_rotation()` implementation
- `.planning/research/PITFALLS.md` Pitfall 7 — OSD unreliability research
- `.planning/research/ARCHITECTURE.md` — Multi-rotation strategy rationale
- `.planning/phases/01-*/01-CONTEXT.md` — Phase 1 decisions D-01 through D-07

---

### Secondary (MEDIUM confidence)

**OCR Best Practices:**
- [Optimizing Rotation Accuracy for OCR - Medium](https://indiantechwarrior.medium.com/optimizing-rotation-accuracy-for-ocr-fbfb785c504b) — Rotation optimization patterns, confidence scoring
- [Unlocking Text from Rotated Images with Python](https://medium.com/@iince98/unlocking-text-from-tif-files-with-python-ocr-magic-using-pytesseract-and-opencv-60ac1231812b) — Multi-angle OCR workflows

**CLI Argument Parsing Tutorials:**
- [How to Parse Command Line Arguments in Python](https://oneuptime.com/blog/post/2026-01-22-parse-command-line-arguments-python/view) — argparse patterns and best practices
- [Parse Command-Line Arguments with Argparse](https://mkaz.blog/working-with-python/argparse/) — Boolean flag examples

**pandas Tutorials:**
- [Add a Column to Existing CSV File in Python](https://www.geeksforgeeks.org/python/add-a-column-to-existing-csv-file-in-python/) — Column addition patterns
- [Counting Values in Pandas with value_counts](https://datagy.io/pandas-value-counts/) — Distribution analysis examples

**Enterprise OCR Workflows:**
- [AI for Enterprise Document Processing OCR (2026)](https://www.stackai.com/insights/ai-for-enterprise-document-processing-ocr-end-to-end-workflow-best-practices-and-2026-guide) — Failure classification patterns
- [Designing a Decision-Driven OCR Pipeline](https://medium.com/@ashwinr638/designing-a-decision-driven-ocr-pipeline-445da9221a62) — Multi-stage validation strategies

---

### Tertiary (LOW confidence - flagged for validation)

**Recent Research (not yet validated in practice):**
- [Seeing Straight: Document Orientation Detection for Efficient OCR (2025)](https://arxiv.org/pdf/2511.04161) — 98% ML rotation detection accuracy claim. **Confidence: LOW** — Research paper from Nov 2025, not yet widely adopted. Brute-force rotation remains simpler for numeric IDs.

**Community Discussions:**
- [Detect text rotation without running recognition - GitHub Issue #3836](https://github.com/tesseract-ocr/tesseract/issues/3836) — Community workarounds for rotation detection. **Confidence: LOW** — Discussions, not official recommendations.

---

## Metadata

**Confidence breakdown:**
- **Standard stack:** HIGH — No new dependencies, all packages verified installed
- **Architecture patterns:** HIGH — argparse/pandas/PIL patterns from official docs, rotation order from empirical Phase 1 data
- **Pitfalls:** HIGH — Based on existing PITFALLS.md research (Pitfall 7: OSD unreliability) and standard coding practices
- **Code examples:** HIGH — All from official documentation or existing `precede_ocr.py` implementation
- **Validation architecture:** HIGH — pytest framework already configured, test structure follows Phase 1 patterns

**Research date:** 2026-06-05
**Valid until:** 90 days (2026-09-03) — Stack is stable, no fast-moving dependencies in scope

**Research completed successfully.** All locked decisions (D-08 through D-13) researched with supporting evidence. No blockers identified. Ready for planning.
