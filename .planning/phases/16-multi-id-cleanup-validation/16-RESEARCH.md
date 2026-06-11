# Phase 16: Multi-ID Cleanup & Validation - Research

**Researched:** 2026-06-10
**Domain:** Data quality validation, conservative deduplication, OCR noise detection
**Confidence:** HIGH

## Summary

Phase 16 implements the `clean-multi-ids` subcommand to distinguish real multi-ID pages from OCR noise across 5,141 multi-ID pages (11.2% of corpus). The approach uses CSV-only heuristics (no re-OCR) with three detection strategies: same-page exact duplicates, repeated-digit pattern matching (e.g., "11111"), and existing `seq_outlier_conf_N%` flags from the scan pipeline. A conservative bias toward preservation prevents false-positive removal of legitimate IDs.

**Primary recommendation:** Use pandas groupby + boolean indexing for same-page dedup, regex backreferences for repeated-digit detection, and interactive sample validation (200 IDs) before full cleanup to give users control over noise removal thresholds.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: CSV heuristics only** — Work entirely from scan results CSV data. Do NOT re-render pages or re-OCR. Fast and sufficient for noise detection.

**D-02: Same-page dedup + pattern heuristics** — Primary noise sources to detect:
1. Exact duplicate IDs on the same page (same filename + page + ID appearing more than once)
2. Repeated-digit IDs (e.g., "11111", "00000", "99999") — common OCR artifacts from lines/borders
3. Existing `seq_outlier_conf_N%` flags from `validate_sequential_ids()` in the notes field

**D-03: No cross-page frequency analysis** — Keep scope to same-page dedup and per-ID pattern detection.

**D-04: Interactive terminal prompt for sample validation** — Run analysis on 200-ID sample, display summary table (IDs flagged, reasons, confidence), then prompt "Apply to full dataset? [y/N]". User reviews inline and approves before full run proceeds.

**D-05: `--sample-size` argument** — Already defined in stub (default 200). Honor this for the sample subset.

**D-06: Three output files**:
1. `results_cleaned.csv` — original CSV with noise rows removed (default: `output/results_cleaned.csv` per `--output` arg)
2. `removed_ids.csv` — rows that were removed, with added columns for removal reason and confidence
3. `cleanup_report.md` — markdown report documenting heuristics applied, counts per category, and confidence metrics

**D-07: Raw data always preserved** — Original `results.csv` (input) is never modified. Consistent with Phase 15 D-03.

### Claude's Discretion

- Confidence thresholds for each heuristic (what percentage triggers flagging)
- Ordering of heuristic application (which checks run first)
- Cleanup report structure and detail level
- Whether to include a `--dry-run` flag for preview without writing files
- How to handle edge cases (e.g., a page with exactly 2 IDs where one is a repeated-digit pattern)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MULTI-01 | User can analyze multi-ID pages to determine which are real (multiple IDs per page) vs OCR noise | Pandas groupby patterns for same-page detection; regex patterns for repeated-digit artifacts; existing seq_outlier_conf flags from validate_sequential_ids() |
| MULTI-02 | Conservative deduplication flags likely noise without deleting — biases toward preservation, raw data always preserved | Pandas boolean indexing for non-destructive filtering; keep parameter strategies; preservation patterns from research |
| MULTI-03 | User can run cleanup via CLI subcommand with sample validation before full deployment | Interactive input() pattern; sample-first workflow; argparse --sample-size integration |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 3.0.3 | CSV I/O, groupby, deduplication | Already in use project-wide. DataFrame operations for multi-ID detection. groupby(['filename', 'page']) for same-page duplicate detection. duplicated() and drop_duplicates() with `subset` and `keep` parameters for conservative deduplication. |
| Python re | stdlib | Regex pattern matching | Repeated-digit detection with backreference pattern `r'^(\d)\1{4}$'` matches exactly 5 identical digits (e.g., "11111"). Native to Python 3.14.2. |
| pathlib | stdlib | Path operations | Already in use. Output directory creation, path validation. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| argparse | stdlib | CLI argument parsing | Already wired for clean-multi-ids subparser at line 2586. No new dependencies needed. |
| csv | stdlib | QUOTE_NONNUMERIC for Excel compatibility | Existing pattern from cmd_lookup and cmd_investigate (utf-8-sig + csv.QUOTE_NONNUMERIC). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python re | regex library | regex library supports more advanced features (variable-length lookbehind, recursion), but stdlib re is sufficient for simple repeated-digit patterns. No installation overhead. |
| input() | Click/Typer confirm() | Click/Typer provides richer CLI UX with --yes flags for non-interactive mode, but input() is stdlib and matches existing project pattern (campaign resume menu in main()). Adding Click/Typer would be new dependency. |
| pandas groupby | Manual dict-based grouping | Manual grouping with dict would require more code. Pandas groupby is idiomatic, readable, and already a dependency. |

**Installation:**
No new packages required. All libraries are stdlib or already installed (pandas 3.0.3).

## Architecture Patterns

### Recommended Data Flow
```
1. Load CSV → pandas DataFrame
2. Group by (filename, page) → identify multi-ID pages
3. For each multi-ID page group:
   a. Detect exact duplicates (same ID appears >1 time)
   b. Detect repeated-digit patterns (regex: ^(\d)\1{4}$)
   c. Parse existing seq_outlier_conf_N% flags
4. Mark rows for removal with reason + confidence
5. Sample validation: extract N flagged IDs → show summary → prompt user
6. If approved: split into cleaned + removed DataFrames
7. Write 3 output files (cleaned CSV, removed CSV, report MD)
```

### Pattern 1: Same-Page Duplicate Detection
**What:** Group by (filename, page), find duplicate ID values within each group
**When to use:** D-02 requirement — exact duplicate IDs on same page
**Example:**
```python
# Source: pandas official docs + project pattern adaptation
import pandas as pd

df = pd.read_csv('results.csv')

# Group by (filename, page) and mark duplicates within each group
df['is_duplicate'] = df.groupby(['filename', 'page'])['id'].transform(
    lambda x: x.duplicated(keep='first')
)

# Filter to duplicates (2nd, 3rd, etc occurrences on same page)
duplicates = df[df['is_duplicate']]
```

**Why groupby + transform:** `transform` applies `duplicated()` within each group and broadcasts result back to original DataFrame index, preserving row order. `keep='first'` preserves the first occurrence (conservative bias).

### Pattern 2: Repeated-Digit Detection
**What:** Regex backreference to match 5 identical digits
**When to use:** D-02 requirement — OCR artifacts like "11111", "00000"
**Example:**
```python
# Source: Python re documentation
import re

pattern = r'^(\d)\1{4}$'  # Capture 1 digit, repeat 4 more times (total 5)

# Test against ID column
df['is_repeated_digit'] = df['id'].astype(str).str.match(pattern, na=False)

# Examples:
# "11111" → True
# "00000" → True
# "12345" → False
# "11211" → False
```

**Why backreference:** `(\d)` captures a digit group, `\1{4}` repeats that exact digit 4 more times. Efficient single-pass check.

### Pattern 3: Parse Existing Outlier Flags
**What:** Extract `seq_outlier_conf_N%` from notes field
**When to use:** D-02 requirement — leverage existing statistical outlier detection
**Example:**
```python
# Source: Existing validate_sequential_ids() at line 1180-1304
import re

def extract_outlier_confidence(notes_str):
    """Extract confidence % from seq_outlier_conf_N% flag."""
    if pd.isna(notes_str) or not notes_str:
        return 0
    match = re.search(r'seq_outlier_conf_(\d+)%', notes_str)
    return int(match.group(1)) if match else 0

df['outlier_conf'] = df['notes'].apply(extract_outlier_confidence)

# Flag high-confidence outliers (e.g., > 50%)
df['is_outlier'] = df['outlier_conf'] > 50
```

**Why parse notes:** `validate_sequential_ids()` already runs during scan and flags statistical outliers. Reuse this signal instead of re-implementing.

### Pattern 4: Interactive Sample Validation
**What:** Show user a summary of flagged IDs from sample subset, prompt for approval
**When to use:** D-04 requirement — user control before full deployment
**Example:**
```python
# Source: Existing pattern from main() campaign resume menu
import random

# Sample N flagged rows
flagged_df = df[df['flagged_for_removal']]
sample_size = min(args.sample_size, len(flagged_df))
sample = flagged_df.sample(n=sample_size, random_state=42)

# Show summary
print(f"\n=== Sample Validation ({sample_size} flagged IDs) ===")
print(sample[['filename', 'page', 'id', 'removal_reason', 'confidence']].to_string(index=False))
print(f"\nTotal flagged: {len(flagged_df)} IDs")

# Prompt user
response = input("\nApply cleanup to full dataset? [y/N]: ").strip().lower()
if response != 'y':
    print("Cleanup cancelled. No files written.")
    sys.exit(0)
```

**Why input():** Matches existing project pattern. Simple, stdlib, no dependencies. Non-interactive mode can be added later with `--yes` flag if needed.

### Pattern 5: Multi-File Output
**What:** Write cleaned CSV, removed CSV, and markdown report
**When to use:** D-06 requirement
**Example:**
```python
# Source: cmd_investigate() pattern at lines 2447-2493
from pathlib import Path
import csv

output_path = Path(args.output)
output_path.parent.mkdir(parents=True, exist_ok=True)

# Write cleaned CSV (rows NOT flagged)
cleaned_df = df[~df['flagged_for_removal']]
cleaned_df.to_csv(output_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)

# Write removed CSV (rows flagged) with reason + confidence columns
removed_csv = output_path.parent / 'removed_ids.csv'
removed_df = df[df['flagged_for_removal']]
removed_df.to_csv(removed_csv, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC)

# Write markdown report
report_path = output_path.parent / 'cleanup_report.md'
report_path.write_text(generate_cleanup_report(cleaned_df, removed_df), encoding='utf-8')

# Print summary
print(f"Cleanup complete.")
print(f"  Cleaned CSV: {output_path}")
print(f"  Removed IDs: {removed_csv}")
print(f"  Report: {report_path}")
```

**Why separate files:** Non-destructive pattern. User can audit removed rows, inspect cleaned data, and revert if needed. Matches Phase 15 pattern.

### Anti-Patterns to Avoid

- **Modifying input CSV in-place:** Violates D-07. Always write new files, preserve original.
- **Deleting rows without audit trail:** `removed_ids.csv` must document what was removed and why.
- **Automatic cleanup without user approval:** D-04 requires interactive prompt. Respect user control.
- **Cross-page frequency analysis:** D-03 explicitly excludes this. Don't count how many times an ID appears across different pages.
- **Re-OCR or re-rendering:** D-01 locked decision. Work from CSV only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Duplicate detection within groups | Manual dict grouping + dedup logic | pandas `groupby().transform(lambda x: x.duplicated())` | Handles edge cases (NaN, mixed types), broadcasts results back to original index, optimized for large datasets. |
| Repeated-digit matching | String iteration with char comparison | re.match(r'^(\d)\1{4}$', id_str) | Backreferences are single-pass, readable, and handle edge cases (non-strings, NaN) when combined with str.match(na=False). |
| Interactive CLI prompts | Custom input validation loops | stdlib input() with .strip().lower() | Simple, sufficient for yes/no prompts. Adding Click/Typer later is easy if non-interactive mode needed. |
| CSV export with Excel compatibility | Manual CSV writing with open() | pandas to_csv(encoding='utf-8-sig', quoting=csv.QUOTE_NONNUMERIC) | BOM for Excel, QUOTE_NONNUMERIC prevents date/number coercion. Already validated in Phase 14. |

**Key insight:** Pandas groupby + transform is the idiomatic pattern for within-group operations. Re-implementing this manually introduces bugs (index misalignment, group boundary errors) and is slower for large datasets.

## Common Pitfalls

### Pitfall 1: False Positives from Legitimate Sequential IDs
**What goes wrong:** A page genuinely has two sequential IDs (e.g., front/back of a two-sided card scanned as one page). Dedup logic flags them as noise.
**Why it happens:** Over-aggressive deduplication without considering legitimate use cases.
**How to avoid:** Conservative thresholds. Only flag exact duplicates (same ID, same page) or high-confidence outliers (>80% conf). Low confidence outliers (<50%) should NOT be auto-removed.
**Warning signs:** Removed count is unexpectedly high (>20% of multi-ID pages). Review sample carefully.

### Pitfall 2: Index Misalignment After Filtering
**What goes wrong:** After filtering rows, DataFrame index has gaps (0, 2, 5, ...). Writing to CSV with default settings includes row numbers, confusing users.
**Why it happens:** pandas preserves original index after boolean filtering unless reset.
**How to avoid:** Always use `to_csv(index=False)` or `reset_index(drop=True)` before writing. Project pattern already uses `index=False` everywhere.
**Warning signs:** Output CSV has an extra unnamed column with non-sequential numbers.

### Pitfall 3: Regex Matching NaN or Non-String Values
**What goes wrong:** Applying regex directly to DataFrame column with NaN or int values raises TypeError.
**Why it happens:** `id` column may have mixed types (int, str, NaN) depending on CSV parsing.
**How to avoid:** Always use `df['id'].astype(str).str.match(pattern, na=False)`. The `na=False` parameter treats NaN as non-match instead of propagating NaN.
**Warning signs:** TypeError: expected string or bytes-like object during regex matching.

### Pitfall 4: Groupby with NaN Keys
**What goes wrong:** groupby(['filename', 'page']) drops rows where filename or page is NaN (e.g., error rows).
**Why it happens:** groupby default behavior is `dropna=True` in pandas 3.x.
**How to avoid:** Error rows (page=0) should be excluded before groupby analysis anyway (consistent with cmd_lookup pattern). Add explicit filter: `df = df[df['page'] > 0]` before groupby.
**Warning signs:** Row count decreases unexpectedly after groupby operations.

### Pitfall 5: Overwriting Original Input CSV
**What goes wrong:** Output path defaults to same filename as input, overwriting original data.
**Why it happens:** User passes same path to `--output` as `scan_csv` positional arg.
**How to avoid:** Validate that `args.output != args.scan_csv` before writing. Print clear error and exit(1) if paths match. Default output path is `output/results_cleaned.csv`, which differs from typical input path `results.csv`.
**Warning signs:** User reports "original data lost" after cleanup.

## Code Examples

Verified patterns from official sources and project codebase:

### Same-Page Duplicate Detection (Complete)
```python
# Source: pandas 3.0.3 docs + project adaptation
import pandas as pd

df = pd.read_csv('results.csv')

# Exclude error rows (page=0) before analysis
df_valid = df[df['page'] > 0].copy()

# Mark duplicates within each (filename, page) group
# keep='first' preserves first occurrence (conservative)
df_valid['is_duplicate'] = df_valid.groupby(['filename', 'page'])['id'].transform(
    lambda x: x.duplicated(keep='first')
)

# Add reason + confidence columns
df_valid.loc[df_valid['is_duplicate'], 'removal_reason'] = 'exact_duplicate_same_page'
df_valid.loc[df_valid['is_duplicate'], 'confidence'] = 100  # High confidence
```

### Repeated-Digit Pattern Detection (Complete)
```python
# Source: Python re module documentation
import re
import pandas as pd

df = pd.read_csv('results.csv')

# Pattern: capture one digit, repeat 4 more times (total 5 identical)
pattern = r'^(\d)\1{4}$'

# Apply regex with na=False to handle NaN gracefully
df['is_repeated_digit'] = df['id'].astype(str).str.match(pattern, na=False)

# Add reason + confidence
df.loc[df['is_repeated_digit'], 'removal_reason'] = 'repeated_digit_artifact'
df.loc[df['is_repeated_digit'], 'confidence'] = 95  # Very high confidence
```

### Extract Outlier Confidence from Notes (Complete)
```python
# Source: Existing validate_sequential_ids() logic at line 1292
import re
import pandas as pd

def extract_outlier_confidence(notes_str):
    """Extract confidence % from seq_outlier_conf_N% flag in notes."""
    if pd.isna(notes_str) or not notes_str:
        return 0
    match = re.search(r'seq_outlier_conf_(\d+)%', notes_str)
    return int(match.group(1)) if match else 0

df = pd.read_csv('results.csv')
df['outlier_conf'] = df['notes'].apply(extract_outlier_confidence)

# Flag only HIGH confidence outliers (e.g., > 80%) — conservative threshold
df['is_high_conf_outlier'] = df['outlier_conf'] > 80

# Add reason + confidence
df.loc[df['is_high_conf_outlier'], 'removal_reason'] = 'sequential_outlier'
df.loc[df['is_high_conf_outlier'], 'confidence'] = df.loc[df['is_high_conf_outlier'], 'outlier_conf']
```

### Combine Flags and Sample Validation (Complete)
```python
# Source: Project pattern from main() + cmd_investigate()
import sys
import random

# Combine all flags into single removal column (OR logic)
df['flagged_for_removal'] = (
    df.get('is_duplicate', False) |
    df.get('is_repeated_digit', False) |
    df.get('is_high_conf_outlier', False)
)

# Extract flagged subset
flagged_df = df[df['flagged_for_removal']].copy()

if len(flagged_df) == 0:
    print("No noise detected. Dataset is clean.")
    sys.exit(0)

# Sample for validation
sample_size = min(args.sample_size, len(flagged_df))
sample = flagged_df.sample(n=sample_size, random_state=42)

# Display summary
print(f"\n{'='*60}")
print(f"SAMPLE VALIDATION: {sample_size} flagged IDs (of {len(flagged_df)} total)")
print(f"{'='*60}\n")
print(sample[['filename', 'page', 'id', 'removal_reason', 'confidence']].to_string(index=False))

# Breakdown by reason
print(f"\n--- Breakdown (Full Dataset) ---")
for reason, count in flagged_df['removal_reason'].value_counts().items():
    print(f"  {reason}: {count}")

# Interactive prompt
print(f"\nApply cleanup to full dataset? This will:")
print(f"  - Write cleaned CSV with {len(df) - len(flagged_df)} rows (noise removed)")
print(f"  - Write removed_ids.csv with {len(flagged_df)} flagged rows (audit trail)")
print(f"  - Preserve original {args.scan_csv} (unchanged)")

response = input("\nProceed? [y/N]: ").strip().lower()
if response != 'y':
    print("Cleanup cancelled. No files written.")
    sys.exit(0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual duplicate removal with Excel filtering | Automated heuristic-based detection with sample validation | 2026 (this phase) | User can process 5,141 multi-ID pages in <1 minute instead of hours of manual review |
| Re-OCR flagged pages for verification | CSV-only analysis | Phase 16 decision (D-01) | 100x faster — no rendering overhead, sufficient for noise patterns |
| Drop all duplicates (pandas drop_duplicates) | Conservative flagging with keep='first' + confidence thresholds | Phase 16 decision (D-02) | Reduces false positives, preserves legitimate multi-ID pages |
| Automatic cleanup on all data | Sample validation with user approval | Phase 16 decision (D-04) | User control, prevents irreversible mistakes |

**Deprecated/outdated:**
- **Pandas 2.x groupby behavior:** pandas 3.0 changed default to `dropna=True` in groupby. Explicitly exclude NaN rows before groupby to avoid confusion.
- **ignore_index parameter:** Added in pandas 1.0, now recommended (2026) for single-step index reset in drop_duplicates(). Use `drop_duplicates(ignore_index=True)` instead of chaining `.reset_index(drop=True)`.

## Open Questions

None — research domain is well-understood. Standard pandas patterns, stdlib regex, existing project conventions cover all requirements.

## Environment Availability

All dependencies already installed. No external tools required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | CSV I/O, groupby, dedup | ✓ | 3.0.3 | — |
| Python re | Regex patterns | ✓ | stdlib 3.14.2 | — |
| pathlib | File operations | ✓ | stdlib 3.14.2 | — |
| argparse | CLI parsing | ✓ | stdlib 3.14.2 | — |
| csv | Excel-compatible CSV | ✓ | stdlib 3.14.2 | — |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (version from project) |
| Config file | tests/conftest.py (existing fixtures) |
| Quick run command | `pytest tests/test_precede_ocr.py::test_cmd_clean_multi_ids -x` |
| Full suite command | `pytest tests/test_precede_ocr.py -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MULTI-01 | Analyze multi-ID pages (real vs noise) | unit | `pytest tests/test_precede_ocr.py::test_clean_multi_ids_detection -x` | ❌ Wave 0 |
| MULTI-01 | Same-page exact duplicate detection | unit | `pytest tests/test_precede_ocr.py::test_same_page_duplicate_detection -x` | ❌ Wave 0 |
| MULTI-01 | Repeated-digit pattern detection | unit | `pytest tests/test_precede_ocr.py::test_repeated_digit_detection -x` | ❌ Wave 0 |
| MULTI-01 | Parse seq_outlier_conf flags | unit | `pytest tests/test_precede_ocr.py::test_parse_outlier_confidence -x` | ❌ Wave 0 |
| MULTI-02 | Conservative dedup preserves first occurrence | unit | `pytest tests/test_precede_ocr.py::test_conservative_dedup_preserves_first -x` | ❌ Wave 0 |
| MULTI-02 | Raw data never modified (input CSV untouched) | integration | `pytest tests/test_precede_ocr.py::test_clean_preserves_input_csv -x` | ❌ Wave 0 |
| MULTI-03 | CLI subcommand integration | integration | `pytest tests/test_precede_ocr.py::test_cmd_clean_multi_ids -x` | ❌ Wave 0 |
| MULTI-03 | Three output files generated | integration | `pytest tests/test_precede_ocr.py::test_clean_outputs_three_files -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_precede_ocr.py::test_cmd_clean_multi_ids -x` (quick integration test)
- **Per wave merge:** `pytest tests/test_precede_ocr.py -v` (full test suite — 259 existing + new tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_precede_ocr.py::test_same_page_duplicate_detection` — covers MULTI-01 same-page dedup
- [ ] `tests/test_precede_ocr.py::test_repeated_digit_detection` — covers MULTI-01 repeated-digit patterns
- [ ] `tests/test_precede_ocr.py::test_parse_outlier_confidence` — covers MULTI-01 seq_outlier parsing
- [ ] `tests/test_precede_ocr.py::test_conservative_dedup_preserves_first` — covers MULTI-02 keep='first'
- [ ] `tests/test_precede_ocr.py::test_clean_preserves_input_csv` — covers MULTI-02 raw data preservation
- [ ] `tests/test_precede_ocr.py::test_cmd_clean_multi_ids` — covers MULTI-03 full CLI integration
- [ ] `tests/test_precede_ocr.py::test_clean_outputs_three_files` — covers MULTI-03 output files
- [ ] `tests/conftest.py::sample_multi_id_csv` — fixture for multi-ID test data (shared across tests)

**Framework install:** Already installed — pytest in use (259 passing tests per STATE.md).

## Sources

### Primary (HIGH confidence)
- [pandas.DataFrame.duplicated — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.duplicated.html) - duplicated() API with subset and keep parameters
- [pandas.DataFrame.drop_duplicates — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html) - drop_duplicates() API with keep and ignore_index parameters
- [re — Regular expression operations — Python 3.14.6 documentation](https://docs.python.org/3/library/re.html) - Python regex module for backreference patterns
- [Regular expression HOWTO — Python 3.14.5 documentation](https://docs.python.org/3/howto/regex.html) - Regex best practices and examples
- Existing project code: `precede_ocr.py` lines 1180-1304 (validate_sequential_ids), 2159-2226 (cmd_lookup), 2432-2493 (cmd_investigate)
- Existing test fixtures: `tests/conftest.py` (pytest fixtures, sample data patterns)

### Secondary (MEDIUM confidence)
- [pandas: Find, count, drop duplicates (duplicated, drop_duplicates) | note.nkmk.me](https://note.nkmk.me/en/python-pandas-duplicated-drop-duplicates/) - Practical examples of duplicate detection patterns
- [Filter Pandas Dataframe with multiple conditions - GeeksforGeeks](https://www.geeksforgeeks.org/python/filter-pandas-dataframe-with-multiple-conditions/) - Boolean indexing with & and | operators
- [How to write Python Regular Expression find repeating digits in a number?](https://www.tutorialspoint.com/How-to-write-Python-Regular-Expression-find-repeating-digits-in-a-number) - Backreference pattern examples
- [Handling Duplicate Values in a Pandas DataFrame](https://stackabuse.com/handling-duplicate-values-in-a-pandas-dataframe/) - Best practices for duplicate handling
- [Data Cleansing Guide 2026: Techniques & Tools | Match Data Pro](https://matchdatapro.com/data-cleansing-the-complete-2026-technical-guide-for-data-engineers/) - Conservative data cleaning strategies
- [The Human Factor in Data Cleaning: Exploring Preferences and Biases](https://arxiv.org/html/2602.19368v1) - Research on omission bias and false positives in data cleaning (2026)

### Tertiary (LOW confidence)
- [Mastering Pandas Duplicate Removal and Index Management in 2026: A Complete Guide](https://copyprogramming.com/howto/removing-duplicate-values-after-pandas-groupby) - General groupby + dedup patterns (not verified with official docs)
- [OCR Data Entry: Preprocessing Text for NLP Tasks in 2026 | Label Your Data](https://labelyourdata.com/articles/ocr-data-entry) - General OCR noise characterization (not specific to numeric IDs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pandas 3.0.3 verified installed, stdlib modules, no new dependencies
- Architecture: HIGH — patterns verified from pandas official docs + existing project code
- Pitfalls: HIGH — derived from pandas 3.0 breaking changes, common groupby errors, project-specific conventions
- Validation: HIGH — pytest framework already in use, test patterns established in existing codebase

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (30 days — stable domain, pandas API mature)
