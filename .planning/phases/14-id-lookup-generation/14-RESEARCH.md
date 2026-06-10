# Phase 14: ID Lookup Generation - Research

**Researched:** 2026-06-10
**Domain:** CSV data transformation and Excel compatibility
**Confidence:** HIGH

## Summary

Phase 14 implements a straightforward data transformation: read the scan results CSV, filter to rows with valid IDs, extract/rename columns, sort numerically by ID, and write an Excel-compatible CSV. The technical domain is well-established with pandas 3.0.3 as the standard tool.

**Key requirements:** UTF-8 BOM encoding for Excel compatibility, numeric sorting on the ID column, and prevention of Excel's auto-conversion of numeric IDs to dates.

**Primary recommendation:** Use `pandas.DataFrame.to_csv()` with `encoding='utf-8-sig'` and `quoting=csv.QUOTE_NONNUMERIC` to ensure Excel opens the file correctly. Convert ID column to string dtype before export to prevent date interpretation. Filter using pandas boolean indexing (`df[df['id'] != '']`) to exclude blank and error rows.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Data Filtering:**
- **D-01:** Exclude rows with blank IDs (no-match pages) from the lookup CSV. The lookup is purely for finding which file/page an ID lives in. No-match analysis belongs in Phase 15.
- **D-02:** Exclude error rows (page=0, notes starting with "error:") from the lookup CSV. Error investigation belongs in Phase 15.
- **D-03:** Keep all duplicate IDs — if the same ID appears in multiple files or pages, every occurrence is a valid lookup result. Deduplication is Phase 16's responsibility.

**Folder Extraction:**
- **D-04:** Use `folder_path` column from scan CSV if present. If the column is missing (older CSV format without folder_path), extract the parent directory path from the `filename` field. If filename has no path component, Folder is blank.

**Completion Summary:**
- **D-05:** Print summary stats on completion: total entries, unique IDs, files covered, and output path. Example: `Wrote 52,055 entries (48,901 unique IDs) from 30,316 files to output/lookup.csv`

### Claude's Discretion

- Excel compatibility implementation details (BOM byte, quoting strategy)
- Exact error messages for invalid/missing input CSV
- Whether to use pandas or csv module for output
- Progress indication for large files (if needed)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOOK-01 | User can generate an ID lookup CSV sorted by ID number with columns: ID, Filename, Page, Folder | Pandas `sort_values()` with `na_position='last'` for numeric sorting; DataFrame column selection for output schema |
| LOOK-02 | Lookup CSV opens correctly in Excel (UTF-8 BOM encoding, proper quoting, IDs not interpreted as dates) | `encoding='utf-8-sig'` for UTF-8 BOM; `quoting=csv.QUOTE_NONNUMERIC` to quote string IDs; convert ID column to string dtype before export |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **pandas** | 3.0.3 | CSV I/O and data transformation | Already imported and used throughout codebase. Mature DataFrame API for filtering (`df[condition]`), column selection, sorting (`sort_values()`), and CSV export (`to_csv()`). Version verified via `pip show pandas`. |
| **pathlib** | stdlib | Path manipulation (fallback folder extraction) | Already used in codebase (line 193-206). Modern OOP API for extracting parent directories from filenames when `folder_path` column is missing. |
| **csv** | stdlib | Quoting constants (`QUOTE_NONNUMERIC`) | Provides constants for pandas `to_csv()` quoting parameter. Required import: `import csv`. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **argparse** | stdlib | Already wired to `cmd_lookup(args)` | No new work — lookup subparser already defines `scan_csv` positional and `--output` flag (line 2213-2226). |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas | csv module (stdlib) | csv.DictReader/DictWriter would work but require more boilerplate for filtering, sorting, and column renaming. pandas is already a project dependency and provides cleaner API. |
| `to_csv()` | `to_excel()` | Would require openpyxl or xlsxwriter dependency. User workflow is CSV → Excel open, not native .xlsx generation. Adding dependency for no user benefit. |
| UTF-8 BOM | UTF-8 plain | Excel requires BOM to recognize UTF-8 encoding. Without BOM, special characters may display as garbage (e.g., ï»¿ in headers). |

**Installation:**

No new dependencies — all libraries already installed (pandas 3.0.3 verified, pathlib/csv/argparse are stdlib).

**Version verification:**

pandas 3.0.3 confirmed via `python -c "import pandas; print(pandas.__version__)"` on 2026-06-10. Latest release per PyPI (May 2026).

## Project Constraints (from CLAUDE.md)

**Platform:** Windows 10 — all tooling must work on Windows
- pathlib handles cross-platform paths correctly (`Path("dir") / "file"` not `"dir\\file"`)
- pandas `to_csv()` works identically on Windows

**Dependencies:** Python 3.x ecosystem
- pandas 3.0.3 requires Python 3.9+ (running Python 3.14.2)
- No external binaries required (unlike Tesseract/Poppler in scan pipeline)

**No manual intervention:** Must run fully automated once pointed at a directory
- CLI already wired: `python precede_ocr.py lookup results.csv`
- Error handling must print clear messages and exit with non-zero code on failure

## Architecture Patterns

### Recommended Data Flow

```
Input: scan results CSV (from Phase 12/13)
  ↓
1. Read CSV with pandas.read_csv()
  ↓
2. Filter rows: exclude blank IDs and error rows
  ↓
3. Select/rename columns: ID, Filename, Page, Folder
  ↓
4. Convert ID column to string dtype
  ↓
5. Sort by ID (numeric)
  ↓
6. Write CSV with UTF-8 BOM and QUOTE_NONNUMERIC
  ↓
Output: Excel-compatible lookup CSV
```

### Pattern 1: Reading Scan CSV

**What:** Load scan results CSV into pandas DataFrame
**When to use:** Start of `cmd_lookup()` function
**Example:**

```python
# Source: Existing pattern from precede_ocr.py line 560-618
import pandas as pd
from pathlib import Path

def cmd_lookup(args):
    scan_csv_path = Path(args.scan_csv)

    # Validate input exists
    if not scan_csv_path.exists():
        print(f"Error: Scan CSV not found: {scan_csv_path}")
        sys.exit(1)

    # Read scan CSV
    # Expected columns: filename, folder_path, page, id, rotation_detected, notes
    df = pd.read_csv(scan_csv_path)
```

### Pattern 2: Filtering Data (D-01, D-02, D-03)

**What:** Exclude rows with blank IDs or error indicators
**When to use:** After loading DataFrame
**Example:**

```python
# Source: pandas boolean indexing (standard pattern)
# https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html

# D-01: Exclude blank IDs (no-match pages)
df = df[df['id'] != '']

# D-02: Exclude error rows (page=0 or notes starting with "error:")
df = df[df['page'] != 0]
df = df[~df['notes'].str.startswith('error:', na=False)]

# D-03: Keep all duplicate IDs — no deduplication logic needed
```

### Pattern 3: Column Selection and Folder Handling (D-04)

**What:** Extract required columns and handle missing `folder_path` column
**When to use:** After filtering
**Example:**

```python
# Source: D-04 from CONTEXT.md, compute_folder_path() from precede_ocr.py line 193-206
from pathlib import Path

# D-04: Use folder_path column if present, else extract from filename
if 'folder_path' in df.columns:
    # folder_path column exists (new format from Phase 12)
    df_lookup = df[['id', 'filename', 'page', 'folder_path']].copy()
else:
    # folder_path column missing (older CSV format)
    # Extract parent directory from filename
    df_lookup = df[['id', 'filename', 'page']].copy()
    df_lookup['folder_path'] = df['filename'].apply(
        lambda fname: str(Path(fname).parent) if Path(fname).parent != Path('.') else ''
    )

# Rename columns to match spec: ID, Filename, Page, Folder
df_lookup.columns = ['ID', 'Filename', 'Page', 'Folder']
```

### Pattern 4: Sorting Numerically (LOOK-01)

**What:** Sort by ID column in ascending numeric order
**When to use:** Before writing output CSV
**Example:**

```python
# Source: pandas.DataFrame.sort_values documentation
# https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html

# Convert ID to integer for numeric sorting (handles '12345' as 12345 not '12345')
# IDs are 5-digit strings after filtering, safe to convert
df_lookup['ID'] = df_lookup['ID'].astype(int)

# Sort by ID in ascending order
# na_position='last' is default (not relevant after filtering blanks, but explicit is better)
df_lookup = df_lookup.sort_values(by='ID', ascending=True, na_position='last')

# Convert ID back to string for Excel export (prevents date interpretation)
df_lookup['ID'] = df_lookup['ID'].astype(str)
```

### Pattern 5: Excel-Compatible CSV Export (LOOK-02)

**What:** Write CSV with UTF-8 BOM and proper quoting to prevent Excel auto-conversion
**When to use:** Final step before printing summary
**Example:**

```python
# Source: pandas to_csv documentation + WebSearch findings
# https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
import csv

output_path = Path(args.output)
output_path.parent.mkdir(parents=True, exist_ok=True)

# LOOK-02: Excel compatibility via UTF-8 BOM and quoting
df_lookup.to_csv(
    output_path,
    index=False,              # Exclude row numbers (standard pattern from line 607)
    encoding='utf-8-sig',     # UTF-8 with BOM for Excel recognition
    quoting=csv.QUOTE_NONNUMERIC  # Quote string columns to prevent date conversion
)
```

### Pattern 6: Summary Statistics (D-05)

**What:** Print completion summary with stats
**When to use:** After successful CSV write
**Example:**

```python
# Source: D-05 from CONTEXT.md, similar to write_results_csv() line 609-617
total_entries = len(df_lookup)
unique_ids = df_lookup['ID'].nunique()
files_covered = df_lookup['Filename'].nunique()

print(f"Wrote {total_entries:,} entries ({unique_ids:,} unique IDs) from {files_covered:,} files to {output_path}")
```

### Anti-Patterns to Avoid

- **Converting ID to int for export:** Keep IDs as strings in final CSV. Excel interprets numeric values as numbers/dates. Strings (quoted via `QUOTE_NONNUMERIC`) display as text.
- **Using UTF-8 without BOM:** Excel won't recognize encoding and may display garbage characters. Always use `encoding='utf-8-sig'`.
- **Skipping validation:** Always check input file exists and has expected columns before processing. Fail fast with clear error messages.
- **In-place sorting:** Use `df.sort_values()` (returns new DataFrame) not `df.sort_values(inplace=True)` to avoid subtle bugs in later operations.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing with edge cases | Custom CSV reader with string split | `pandas.read_csv()` | Handles quoted fields, escaped characters, different line endings, encoding detection. Edge cases: commas in filenames, quotes in notes field, UTF-8 BOM. |
| Numeric string sorting | Custom sort with integer conversion | `df.astype(int).sort_values().astype(str)` | pandas handles type conversion safely. Custom sort may fail on non-numeric IDs or NaN values. |
| Excel encoding issues | Manual BOM byte writing | `encoding='utf-8-sig'` parameter | pandas handles BOM correctly. Manual approach risks incorrect byte order or double-BOM on re-export. |
| Column renaming logic | Dictionary mapping with manual iteration | `df.columns = [...]` or `df.rename(columns={...})` | pandas provides clean API. Manual iteration error-prone for missing columns or wrong order. |

**Key insight:** CSV format has many edge cases (quoted commas, multiline fields, encoding variants). pandas `to_csv()` handles all standard cases correctly. Excel compatibility (BOM, quoting) is solved problem via `utf-8-sig` and `QUOTE_NONNUMERIC`.

## Common Pitfalls

### Pitfall 1: Excel Interprets Numeric IDs as Dates

**What goes wrong:** Excel auto-converts values like "12345" to dates or scientific notation when opening CSV files. User sees corrupted IDs.

**Why it happens:** Excel's heuristic type inference runs on CSV import. Numeric-looking strings without quotes are interpreted as numbers. 5-digit numbers can match date formats (e.g., Excel serial dates).

**How to avoid:**
1. Keep ID column as string dtype (not int) in final DataFrame
2. Use `quoting=csv.QUOTE_NONNUMERIC` to wrap string values in quotes
3. Quoted strings in CSV are preserved as text in Excel

**Warning signs:**
- IDs displayed in scientific notation (e.g., 1.2345E+04)
- IDs converted to date format (e.g., 12/31/1933)
- Leading zeros stripped (not relevant for 5-digit IDs without leading zeros, but good practice)

**Source verification:** [Stop Excel from Converting Text to Number or Date format](https://www.winhelponline.com/blog/stop-excel-convert-text-to-number-date-format-csv-file/) — recommends Text Import Wizard or quoting strategies. Our approach (quoting) is programmatic solution.

### Pitfall 2: UTF-8 Encoding Not Recognized by Excel

**What goes wrong:** Excel displays garbage characters (ï»¿, é for ñ, etc.) when opening UTF-8 CSV without BOM.

**Why it happens:** Excel defaults to system encoding (Windows-1252 on English Windows). UTF-8 requires BOM (byte order mark) for Excel to detect encoding automatically.

**How to avoid:**
- Use `encoding='utf-8-sig'` instead of `encoding='utf-8'`
- `utf-8-sig` automatically writes BOM (EF BB BF bytes) at file start
- Excel recognizes BOM and switches to UTF-8 mode

**Warning signs:**
- Non-ASCII characters (folder names with accents, special symbols) display incorrectly
- Column headers corrupted if they contain non-ASCII characters

**Source verification:** [Excel compatible Unicode CSV files from Python](https://tobywf.com/2017/08/unicode-csv-excel/) and [pandas to_csv encoding option "utf-8-BOM" issue](https://github.com/pandas-dev/pandas/issues/44323) — confirm `utf-8-sig` is standard solution.

### Pitfall 3: Filtering Logic Misses Edge Cases

**What goes wrong:** Error rows or blank ID rows slip through into lookup CSV, breaking user expectations (D-01, D-02).

**Why it happens:**
- Using `df[df['id'] == '']` to filter blanks misses NaN values
- Using `df['notes'].str.startswith('error:')` fails on NaN notes (raises TypeError)
- Page 0 comparison fails if page column is float dtype with NaN

**How to avoid:**
- Blank ID filtering: `df[df['id'] != '']` catches both empty strings and excludes NaN
- Error note filtering: `df[~df['notes'].str.startswith('error:', na=False)]` — `na=False` treats NaN as non-match
- Page filtering: `df[df['page'] != 0]` works if page is int; if mixed types, use `df[df['page'].notna() & (df['page'] != 0)]`

**Warning signs:**
- Lookup CSV contains rows with blank ID column
- Lookup CSV contains rows with Page=0
- Lookup CSV contains rows with notes like "error: FileNotFoundError"

### Pitfall 4: Numeric Sorting on String Column

**What goes wrong:** IDs sorted lexicographically instead of numerically (e.g., "10234" comes before "9876").

**Why it happens:** pandas `sort_values()` uses column dtype to determine sort order. String dtype → lexicographic sort. "10234" < "9876" alphabetically.

**How to avoid:**
1. Convert ID to int: `df['ID'] = df['ID'].astype(int)`
2. Sort: `df.sort_values(by='ID')`
3. Convert back to string: `df['ID'] = df['ID'].astype(str)`

Temporary int conversion ensures numeric ordering. Final string dtype prevents Excel date interpretation.

**Warning signs:**
- Sorted CSV shows IDs like: 10012, 10034, 10234, 9876 (lexicographic order)
- Expected: 9876, 10012, 10034, 10234 (numeric order)

### Pitfall 5: Missing folder_path Column Handling

**What goes wrong:** Older scan CSVs (pre-Phase 12) don't have `folder_path` column. Code crashes with KeyError.

**Why it happens:** Phase 12 added `folder_path` column to scan output. Production run results have it, but older test data may not.

**How to avoid (D-04):**
- Check if column exists: `if 'folder_path' in df.columns:`
- If missing, extract from filename: `Path(filename).parent`
- If filename has no path component (bare filename), Folder is blank string

**Warning signs:**
- KeyError: 'folder_path' when reading CSV
- Test failures on older fixture data

## Code Examples

Verified patterns from official sources and existing codebase:

### Complete cmd_lookup Implementation Sketch

```python
# Source: Integration of patterns from pandas docs + CONTEXT.md decisions
import sys
import csv
import pandas as pd
from pathlib import Path

def cmd_lookup(args):
    """
    Generate sorted ID lookup CSV from scan results.

    Implements LOOK-01 and LOOK-02 requirements.
    Follows D-01 through D-05 decisions from CONTEXT.md.
    """
    scan_csv_path = Path(args.scan_csv)
    output_path = Path(args.output)

    # Validate input
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
    if not required_cols.issubset(df.columns):
        print(f"Error: CSV missing required columns. Expected: {required_cols}")
        sys.exit(1)

    # D-01: Exclude blank IDs
    df = df[df['id'] != '']

    # D-02: Exclude error rows
    df = df[df['page'] != 0]
    df = df[~df['notes'].str.startswith('error:', na=False)]

    # D-04: Handle folder_path column (present in new format, missing in old)
    if 'folder_path' in df.columns:
        df_lookup = df[['id', 'filename', 'page', 'folder_path']].copy()
    else:
        df_lookup = df[['id', 'filename', 'page']].copy()
        df_lookup['folder_path'] = df['filename'].apply(
            lambda fname: str(Path(fname).parent) if Path(fname).parent != Path('.') else ''
        )

    # Rename columns per LOOK-01
    df_lookup.columns = ['ID', 'Filename', 'Page', 'Folder']

    # LOOK-01: Sort numerically by ID
    df_lookup['ID'] = df_lookup['ID'].astype(int)
    df_lookup = df_lookup.sort_values(by='ID', ascending=True)
    df_lookup['ID'] = df_lookup['ID'].astype(str)  # Back to string for Excel

    # LOOK-02: Write Excel-compatible CSV
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_lookup.to_csv(
        output_path,
        index=False,
        encoding='utf-8-sig',  # UTF-8 with BOM
        quoting=csv.QUOTE_NONNUMERIC  # Quote strings to prevent date conversion
    )

    # D-05: Print summary
    total_entries = len(df_lookup)
    unique_ids = df_lookup['ID'].nunique()
    files_covered = df_lookup['Filename'].nunique()
    print(f"Wrote {total_entries:,} entries ({unique_ids:,} unique IDs) from {files_covered:,} files to {output_path}")
```

### Filtering with Boolean Indexing

```python
# Source: pandas boolean indexing documentation
# https://pandas.pydata.org/docs/user_guide/indexing.html#boolean-indexing

# Single condition
df_filtered = df[df['id'] != '']

# Multiple conditions with & (and)
df_filtered = df[(df['id'] != '') & (df['page'] != 0)]

# Negation with ~
df_filtered = df[~df['notes'].str.startswith('error:', na=False)]

# String methods require .str accessor
# na=False treats NaN as False (doesn't match condition)
```

### Handling Missing Columns Gracefully

```python
# Source: Python conditional logic + pandas column access
# https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.columns.html

if 'folder_path' in df.columns:
    # Column exists — use it directly
    folder = df['folder_path']
else:
    # Column missing — compute from filename
    folder = df['filename'].apply(lambda f: str(Path(f).parent))

# Alternative: Use .get() with default
# df.get('folder_path', df['filename'].apply(...))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| UTF-8 encoding | UTF-8 BOM (utf-8-sig) | pandas 0.17+ (2015) | Excel compatibility without manual BOM bytes. Standard practice for Excel CSV export. |
| Manual quoting logic | `quoting=csv.QUOTE_NONNUMERIC` | csv module (stdlib) | Prevents Excel auto-conversion. Simpler than custom quoting logic. |
| String splitting for CSV | pandas read_csv/to_csv | pandas 0.1+ (2011) | Handles edge cases (quoted commas, multiline fields, encodings). Production-grade CSV handling. |

**Deprecated/outdated:**

- **Manual BOM writing:** Writing `b'\xef\xbb\xbf'` bytes before CSV data. Replaced by `encoding='utf-8-sig'` parameter.
- **Text Import Wizard instructions:** Telling users to manually import CSV via Excel wizard. Programmatic quoting solves the problem at source.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All functionality | ✓ | 3.14.2 | — |
| pandas | CSV I/O and transformations | ✓ | 3.0.3 | — |
| pathlib | Folder extraction (D-04 fallback) | ✓ | stdlib | — |
| csv | Quoting constants | ✓ | stdlib | — |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

All required libraries available and compatible. No environment setup needed.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini |
| Quick run command | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup -x` |
| Full suite command | `python -m pytest tests/test_precede_ocr.py -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOOK-01 | Generate lookup CSV with columns ID, Filename, Page, Folder sorted by ID | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_basic -x` | ❌ Wave 0 |
| LOOK-01 | Sort IDs numerically (10234 after 9876, not before) | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_numeric_sort -x` | ❌ Wave 0 |
| LOOK-01 | Exclude blank ID rows (D-01) | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_filter_blanks -x` | ❌ Wave 0 |
| LOOK-01 | Exclude error rows (D-02) | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_filter_errors -x` | ❌ Wave 0 |
| LOOK-01 | Keep duplicate IDs (D-03) | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_keep_duplicates -x` | ❌ Wave 0 |
| LOOK-01 | Handle missing folder_path column (D-04) | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_legacy_csv -x` | ❌ Wave 0 |
| LOOK-01 | Print summary stats (D-05) | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_summary -x` | ❌ Wave 0 |
| LOOK-02 | Write UTF-8 BOM for Excel | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_utf8_bom -x` | ❌ Wave 0 |
| LOOK-02 | Quote string columns to prevent date conversion | unit | `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup_quoting -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_precede_ocr.py::test_cmd_lookup -x` (fast subset)
- **Per wave merge:** `python -m pytest tests/test_precede_ocr.py -v` (full suite — 236 existing tests + new lookup tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_basic` — Covers LOOK-01 basic functionality (read CSV, filter, sort, write)
- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_numeric_sort` — Covers numeric vs lexicographic sorting
- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_filter_blanks` — Covers D-01 (exclude blank IDs)
- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_filter_errors` — Covers D-02 (exclude error rows)
- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_keep_duplicates` — Covers D-03 (no deduplication)
- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_legacy_csv` — Covers D-04 (missing folder_path column)
- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_summary` — Covers D-05 (print summary stats)
- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_utf8_bom` — Covers LOOK-02 UTF-8 BOM
- [ ] `tests/test_precede_ocr.py::test_cmd_lookup_quoting` — Covers LOOK-02 quoting strategy
- [ ] `tests/conftest.py` — Fixtures for sample scan CSV data (if not already present)

**Framework install:** Already installed — pytest 9.0.2 detected.

## Sources

### Primary (HIGH confidence)

- [pandas.DataFrame.to_csv — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html) - Official API reference for encoding and quoting parameters
- [pandas.DataFrame.sort_values — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html) - Official API reference for sorting with na_position
- Python 3.14.2 environment verification (2026-06-10)
- pandas 3.0.3 version verification via `pip show pandas` (2026-06-10)
- Existing codebase patterns:
  - `write_results_csv()` (line 560-618) — CSV output pattern
  - `compute_folder_path()` (line 193-206) — Folder extraction logic
  - `cmd_lookup()` stub and argparse wiring (line 2158-2226)

### Secondary (MEDIUM confidence)

- [Excel compatible Unicode CSV files from Python - tobywf](https://tobywf.com/2017/08/unicode-csv-excel/) - UTF-8 BOM explanation
- [to_csv() enconding option "utf-8-BOM" · Issue #44323 · pandas-dev/pandas](https://github.com/pandas-dev/pandas/issues/44323) - Discussion of utf-8-sig for BOM
- [Stop Excel from Converting Text to Number or Date format when Opening a CSV file](https://www.winhelponline.com/blog/stop-excel-convert-text-to-number-date-format-csv-file/) - Excel auto-conversion prevention
- [How to Prevent Excel from Corrupting CSV Data](https://dataflowmapper.com/blog/stop-excel-ruining-csv-data-integrity) - Quoting strategies
- [Pandas Dataframes: CSV Quoting and Escaping Strategies](https://queirozf.com/entries/pandas-dataframes-csv-quoting-and-escaping-strategies) - QUOTE_NONNUMERIC usage
- [pandas Sort: Your Guide to Sorting Data in Python – Real Python](https://realpython.com/pandas-sort-python/) - Sorting tutorial
- [Pandas - Cleaning Empty Cells](https://www.w3schools.com/python/pandas/pandas_cleaning_empty_cells.asp) - Filtering patterns
- [How to Filter Out Records with Null or Empty Strings in Python Pandas](https://saturncloud.io/blog/how-to-filter-out-records-with-null-or-empty-strings-in-python-pandas/) - Boolean indexing

### Tertiary (LOW confidence)

None — all findings verified with official docs or existing codebase patterns.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pandas 3.0.3 verified, stdlib libraries confirmed
- Architecture: HIGH - Straightforward data pipeline with established patterns
- Pitfalls: HIGH - Verified via official docs and WebSearch cross-reference (UTF-8 BOM, quoting, numeric sorting)
- Excel compatibility: MEDIUM - Based on community best practices and pandas docs, but not directly tested against Excel 2026 (user will validate in testing)
- Test infrastructure: HIGH - pytest 9.0.2 confirmed, existing test suite structure established

**Research date:** 2026-06-10
**Valid until:** 60 days (stable domain — CSV handling and pandas API unlikely to change rapidly)
