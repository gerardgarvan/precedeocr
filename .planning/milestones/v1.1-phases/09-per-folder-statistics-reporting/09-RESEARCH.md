# Phase 9: Per-Folder Statistics & Reporting - Research

**Researched:** 2026-06-07
**Domain:** Statistics aggregation, progress tracking, Markdown report generation
**Confidence:** HIGH

## Summary

Phase 9 delivers comprehensive campaign statistics through four enhancement layers: (1) real-time progress with ETA via tqdm's built-in capabilities, (2) enriched exit summaries with error type breakdown, (3) per-folder quality metrics aggregated in the main process, and (4) auto-generated Markdown reports with problem area highlighting and pattern-based recommendations.

The technical approach leverages stdlib-only aggregation (collections.defaultdict for folder grouping, collections.Counter for error categorization), tqdm's existing postfix mechanism for running stats display, and f-string templates for Markdown generation (pandas.to_markdown requires tabulate>=0.9.0 upgrade but adds complexity for minimal benefit). All statistics accumulate in the main process loop where worker results are already being processed — no IPC overhead, no Manager bottleneck.

**Primary recommendation:** Use collections.defaultdict(lambda: defaultdict(int)) for nested per-folder stats, enhance existing calculate_batch_stats() to include folder breakdown and error categorization, generate Markdown reports with f-string templates for full control over formatting and highlighting, and upgrade tabulate to 0.10.0 only if pandas.to_markdown becomes required in future phases.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Report Content:**
- **D-01:** Full comprehensive report — executive summary + per-folder stats table + problem area highlights + rotation/preprocessing breakdown + recommendations. One-stop reference for the entire campaign run.
- **D-02:** Per-folder aggregates only — no per-file error listing in the report. Individual file errors are already in CSV output; report stays concise.
- **D-03:** Report file (`campaign_report.md`) written to the same output directory as CSV/JSON (alongside `precede_results.csv` and `precede_results.json`).
- **D-04:** Report auto-generates on every campaign completion. No CLI flag needed, no opt-out.

**Problem Detection:**
- **D-05:** Problem threshold: folders with success rate below 80% are flagged as problem areas.
- **D-06:** Pattern-based recommendations — analyze error patterns per problem folder and suggest actions (high preprocessing fallback -> "low scan quality, consider rescanning"; rotation failures -> "unusual page orientation"; file-level errors -> "corrupted PDFs, verify source files").
- **D-07:** Problem folders highlighted with bold + warning emoji prefix in the Markdown table row. Easy to spot when scanning.

**Console vs. Report:**
- **D-08:** Use tqdm's built-in ETA for progress display (STAT-01). It's already configured with `total=` — just ensure ETA display is active. Zero extra code needed.
- **D-09:** Enhanced menu "View stats" (option 3) shows condensed per-folder table in console (top 10 worst folders + totals). Full detail in the Markdown report.
- **D-10:** Exit summary (print_batch_stats) enhanced with error type breakdown (e.g., "corrupted PDF: 12, timeout: 3, no pages: 5") plus a pointer to `campaign_report.md` for full details.

**Stats Granularity:**
- **D-11:** Rotation distribution (90/270/0/180) and preprocessing fallback rates shown both as campaign-wide aggregates in the summary section AND per-folder in the detailed table.
- **D-12:** Per-folder table sorted by success rate ascending — worst folders first (most actionable ordering).
- **D-13:** Per-folder table includes "Avg IDs/Page" column to help gauge extraction density and spot folders with consistently zero or multiple IDs.

### Claude's Discretion

- Table column order and width in Markdown report
- Exact wording of pattern-based recommendations
- Number of folders shown in condensed console view (guideline: ~10 worst)
- Whether to include a "top performing folders" section in the report (optional positive signal)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STAT-01 | User sees completion progress during processing (files done/total, IDs found, ETA) | tqdm with `total=` parameter auto-calculates ETA; existing postfix mechanism displays running stats (IDs, errors) — no code changes needed for ETA |
| STAT-02 | User sees success/failure counts and error summary on campaign exit | Extend calculate_batch_stats() to include error type breakdown via Counter; enhance print_batch_stats() to display categorized errors and report pointer |
| STAT-03 | User can view per-folder quality breakdown (success rate, error count, IDs per directory) | Aggregate folder stats in process_all_pdfs() loop using defaultdict; extend handle_view_stats() to display top N worst folders sorted by success rate |
| STAT-04 | Campaign generates a Markdown report with per-folder stats, problem area highlights, and recommendations | F-string template for full report; pandas DataFrame for table sorting/aggregation; problem folders flagged with bold + emoji; pattern-based recommendations from error analysis |
| STAT-05 | Statistics include preprocessing fallback trigger rates and rotation distribution | Count 'preprocessed' in notes field for fallback rate; aggregate rotation_detected values for distribution; display both campaign-wide and per-folder |

</phase_requirements>

## Standard Stack

### Core Statistics & Aggregation
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **collections.defaultdict** | stdlib | Nested per-folder statistics aggregation | Auto-creates missing keys on first access — perfect for grouping results by folder_path without manual initialization. Single-line folder stat accumulation. **Confidence: HIGH** |
| **collections.Counter** | stdlib | Error type counting and categorization | Optimized for frequency counting (~0.03s for 1M items). Provides .most_common() for sorted error breakdowns. Standard pattern for categorization tasks. **Confidence: HIGH** |
| **pandas.DataFrame** | 3.0.3 | Table sorting and per-folder aggregation | Already installed. Powerful groupby() and agg() for folder-level rollups. to_dict() for iteration during report generation. **Confidence: HIGH** |

### Progress Tracking
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **tqdm** | 4.67.3 | Progress bar with automatic ETA | Already installed and configured. Auto-calculates ETA when `total=` is set (line 1106). set_postfix() displays running stats (lines 1155-1159). Zero new dependencies. **Confidence: HIGH** |

### Markdown Report Generation
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **f-string templates** | stdlib (Python 3.6+) | Multi-line Markdown generation | Full control over formatting, highlighting, and layout. No external dependencies. Supports dynamic content, decimal precision, alignment. Standard for report generation. **Confidence: HIGH** |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pathlib** | stdlib | Path operations for report file | Already used extensively (lines 228-241). Path.parent for output directory access. **Confidence: HIGH** |
| **datetime** | stdlib | Timestamps for report generation | Already imported (line 153). .isoformat() for ISO 8601 timestamps. **Confidence: HIGH** |
| **re** | stdlib | Error type extraction from notes field | Extract exception type from "error: {ExceptionType}: {message}" pattern in notes field. Already imported in test suite. **Confidence: HIGH** |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **f-string templates** | pandas.to_markdown() | to_markdown() requires tabulate>=0.9.0 (current: 0.8.10). Upgrade path exists (0.10.0 released March 2026) but adds dependency management overhead. f-strings provide full formatting control without upgrade. Trade simplicity for flexibility. **Confidence: MEDIUM** |
| **f-string templates** | pytablewriter | External dependency. Overkill for single-use Markdown table. f-strings sufficient for this use case. **Confidence: MEDIUM** |
| **collections.Counter** | Manual dict with .get(key, 0) | Counter is cleaner, faster (~3x vs dict.get()), and provides .most_common() built-in. No reason to avoid stdlib solution. **Confidence: HIGH** |
| **Main process aggregation** | multiprocessing.Manager.dict | Manager adds 10-100x IPC overhead per update. D-04 decision explicitly chose local aggregation. Worker results already flow to main process (lines 1112-1159). **Confidence: HIGH** |

**Installation:**

No new dependencies required — all stdlib or already installed (tqdm 4.67.3, pandas 3.0.3).

**Optional upgrade path (if pandas.to_markdown becomes required in future):**

```bash
python -m pip install --upgrade tabulate  # 0.8.10 -> 0.10.0
```

**Version verification:** All recommended packages verified current as of 2026-06-07.

## Architecture Patterns

### Recommended Integration Points

```
precede_ocr.py
├── process_all_pdfs() [lines 1090-1212]
│   ├── Main worker result loop [lines 1112-1159]
│   │   └── ADD: Accumulate per-folder stats here
│   └── ADD: Call generate_campaign_report() after final state save
│
├── calculate_batch_stats() [lines 777-809]
│   └── EXTEND: Add folder_breakdown and error_categories to return dict
│
├── print_batch_stats() [lines 812-832]
│   └── EXTEND: Print error type breakdown + report pointer
│
└── handle_view_stats() [lines 1273-1298]
    └── EXTEND: Show top N worst folders table
```

### Pattern 1: Local Statistics Accumulation

**What:** Aggregate per-folder stats in the main process loop where worker results are already processed

**When to use:** When worker results flow through a central collection point (lines 1112-1159)

**Example:**

```python
# Source: Existing pattern from lines 1129-1159 + collections.defaultdict best practice
from collections import defaultdict, Counter

# Initialize folder stats tracker (add near line 1090)
folder_stats = defaultdict(lambda: {
    'total_pages': 0,
    'files': set(),
    'failed_files': set(),
    'ids_found': 0,
    'no_id_pages': 0,
    'rotations': Counter(),
    'preprocessing_fallbacks': 0
})

# Accumulate in worker result loop (extend lines 1122-1159)
for file_results in pool.imap_unordered(process_single_pdf_wrapper, pdf_paths, chunksize=chunksize):
    if _SHUTDOWN_EVENT.is_set():
        break

    all_results.extend(file_results)

    # Extract folder_path from first result (all pages in same file have same folder)
    if file_results:
        folder_path = file_results[0].get('folder_path', '')
        filename = file_results[0]['filename']

        folder_stats[folder_path]['files'].add(filename)

        # Check if file-level error (page==0 + error in notes)
        if file_results[0]['page'] == 0 and 'error:' in file_results[0].get('notes', ''):
            folder_stats[folder_path]['failed_files'].add(filename)

        # Aggregate page-level stats
        for r in file_results:
            folder_stats[folder_path]['total_pages'] += 1

            if r['ids']:
                folder_stats[folder_path]['ids_found'] += len(r['ids'])
            elif r['page'] > 0 and 'error:' not in r.get('notes', ''):
                folder_stats[folder_path]['no_id_pages'] += 1

            if r.get('rotation_detected'):
                folder_stats[folder_path]['rotations'][r['rotation_detected']] += 1

            if 'preprocessed' in r.get('notes', ''):
                folder_stats[folder_path]['preprocessing_fallbacks'] += 1
```

**Why this works:** Zero IPC overhead (data already in main process), leverages existing loop, defaultdict auto-creates nested structures, Counter optimizes frequency counting.

### Pattern 2: Error Type Categorization

**What:** Extract exception types from notes field and group for error breakdown display

**When to use:** For STAT-02 error summary on campaign exit

**Example:**

```python
# Source: Python regex pattern extraction + collections.Counter
from collections import Counter
import re

def categorize_errors(results: list[dict]) -> dict[str, int]:
    """Extract and count error types from results.

    Notes field format: "error: {ExceptionType}: {message}"
    Returns dict mapping error type to count.
    """
    error_pattern = re.compile(r'error:\s*(\w+):')
    error_counter = Counter()

    for r in results:
        if r.get('page') == 0 and 'error:' in r.get('notes', ''):
            match = error_pattern.search(r['notes'])
            if match:
                error_type = match.group(1)
                error_counter[error_type] += 1
            else:
                error_counter['Unknown'] += 1

    return dict(error_counter.most_common())
```

**Why this works:** Regex extracts structured error types from existing notes field, Counter provides .most_common() for sorted display, pattern matches existing error format from line 1047.

### Pattern 3: Markdown Report Generation with F-strings

**What:** Multi-line f-string template for full Markdown report with dynamic content

**When to use:** For STAT-04 campaign report generation

**Example:**

```python
# Source: Python f-string multiline best practices + pandas aggregation
from pathlib import Path
from datetime import datetime
import pandas as pd

def generate_campaign_report(
    campaign_state: CampaignState,
    all_results: list[dict],
    folder_stats: dict,
    output_dir: Path
) -> None:
    """Generate comprehensive Markdown report per D-01 through D-13."""

    # Calculate campaign-wide stats
    total_files = len(set(r['filename'] for r in all_results))
    failed_files = len(set(r['filename'] for r in all_results
                          if r.get('page') == 0 and 'error:' in r.get('notes', '')))
    success_rate = (total_files - failed_files) / total_files * 100 if total_files > 0 else 0

    # Aggregate rotation distribution (campaign-wide)
    rotation_counts = Counter(r['rotation_detected'] for r in all_results if r.get('rotation_detected'))
    total_rotations = sum(rotation_counts.values())

    # Build per-folder DataFrame for sorting and table generation
    folder_rows = []
    for folder_path, stats in folder_stats.items():
        total_files_folder = len(stats['files'])
        failed_files_folder = len(stats['failed_files'])
        success_files = total_files_folder - failed_files_folder
        success_rate_folder = (success_files / total_files_folder * 100) if total_files_folder > 0 else 0
        avg_ids_per_page = stats['ids_found'] / stats['total_pages'] if stats['total_pages'] > 0 else 0

        folder_rows.append({
            'Folder': folder_path if folder_path else '(root)',
            'Files': total_files_folder,
            'Success Rate': success_rate_folder,
            'Failed': failed_files_folder,
            'Total Pages': stats['total_pages'],
            'IDs Found': stats['ids_found'],
            'Avg IDs/Page': avg_ids_per_page,
            'Preprocessing Fallbacks': stats['preprocessing_fallbacks']
        })

    df = pd.DataFrame(folder_rows)
    df = df.sort_values('Success Rate', ascending=True)  # D-12: worst first

    # Identify problem folders (D-05: success rate < 80%)
    problem_folders = df[df['Success Rate'] < 80.0]

    # Generate Markdown table manually with highlighting
    table_lines = []
    table_lines.append("| Folder | Files | Success Rate | Failed | Total Pages | IDs Found | Avg IDs/Page | Preprocessing Fallbacks |")
    table_lines.append("|--------|-------|--------------|--------|-------------|-----------|--------------|-------------------------|")

    for _, row in df.iterrows():
        folder_display = row['Folder']

        # D-07: Highlight problem folders with bold + emoji
        if row['Success Rate'] < 80.0:
            folder_display = f"⚠️ **{row['Folder']}**"

        table_lines.append(
            f"| {folder_display} | {row['Files']} | {row['Success Rate']:.1f}% | "
            f"{row['Failed']} | {row['Total Pages']} | {row['IDs Found']} | "
            f"{row['Avg IDs/Page']:.2f} | {row['Preprocessing Fallbacks']} |"
        )

    table_markdown = '\n'.join(table_lines)

    # Generate pattern-based recommendations (D-06)
    recommendations = []
    for _, row in problem_folders.iterrows():
        folder = row['Folder']
        if row['Preprocessing Fallbacks'] / row['Total Pages'] > 0.5:
            recommendations.append(f"- **{folder}**: High preprocessing fallback rate ({row['Preprocessing Fallbacks']}/{row['Total Pages']} pages) suggests low scan quality. Consider rescanning source documents.")
        elif row['Failed'] / row['Files'] > 0.3:
            recommendations.append(f"- **{folder}**: High file-level failure rate ({row['Failed']}/{row['Files']} files) suggests corrupted PDFs. Verify source file integrity.")

    recommendations_section = '\n'.join(recommendations) if recommendations else "No specific issues detected."

    # Build full report with f-string template
    report = f"""# Campaign Report: {campaign_state.campaign_id}

**Generated:** {datetime.now().isoformat()}
**Input Path:** {campaign_state.input_path}
**Duration:** {campaign_state.started_at} → {campaign_state.completed_at or 'In progress'}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Total Files** | {total_files} |
| **Successful** | {total_files - failed_files} ({success_rate:.1f}%) |
| **Failed** | {failed_files} |
| **Total Pages Processed** | {len(all_results)} |
| **IDs Found** | {sum(len(r['ids']) for r in all_results)} |
| **No-ID Pages** | {sum(1 for r in all_results if not r['ids'] and r['page'] > 0 and 'error:' not in r.get('notes', ''))} |

### Rotation Distribution (Campaign-Wide)

| Rotation | Count | Percentage |
|----------|-------|------------|
| 90° | {rotation_counts.get(90, 0)} | {rotation_counts.get(90, 0) / total_rotations * 100 if total_rotations > 0 else 0:.1f}% |
| 270° | {rotation_counts.get(270, 0)} | {rotation_counts.get(270, 0) / total_rotations * 100 if total_rotations > 0 else 0:.1f}% |
| 0° | {rotation_counts.get(0, 0)} | {rotation_counts.get(0, 0) / total_rotations * 100 if total_rotations > 0 else 0:.1f}% |
| 180° | {rotation_counts.get(180, 0)} | {rotation_counts.get(180, 0) / total_rotations * 100 if total_rotations > 0 else 0:.1f}% |

---

## Per-Folder Statistics

{table_markdown}

---

## Problem Areas & Recommendations

{recommendations_section}

---

## Output Files

- **Results CSV:** `precede_results.csv`
- **Results JSON:** `precede_results.json`
- **Campaign State:** `campaign_state.json`
- **Checkpoint:** `.checkpoint.json`

---

*Report auto-generated on campaign completion*
"""

    report_path = output_dir / 'campaign_report.md'
    report_path.write_text(report, encoding='utf-8')
    print(f"\nCampaign report written to: {report_path}")
```

**Why this works:** F-strings provide full control over Markdown formatting and highlighting, no external dependencies, supports dynamic content with precision formatting (.1f, .2f), cleanly handles problem folder highlighting per D-07.

### Anti-Patterns to Avoid

- **Using multiprocessing.Manager for stats aggregation:** Manager adds 10-100x IPC overhead. Main process already receives all worker results — aggregate there. (Violates D-04 decision)
- **Blocking progress bar updates for stats calculation:** Keep aggregation lightweight (Counter, dict updates) to avoid slowing tqdm refresh rate. Defer expensive calculations (pandas groupby) to report generation.
- **Hardcoding Markdown table formatting:** Use f-strings with dynamic content, not copy-paste table rows. Makes highlighting and conditional formatting error-prone.
- **Ignoring folder_path normalization:** Existing compute_folder_path() normalizes relative paths (lines 228-241). Don't re-implement — trust existing field.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Frequency counting | Manual dict with loops: `for item: counts[item] = counts.get(item, 0) + 1` | collections.Counter | Counter is 3x faster, provides .most_common(), cleaner syntax. Tested and optimized for this exact use case. |
| Nested dict initialization | Manual key checks: `if key not in d: d[key] = {}` | collections.defaultdict | defaultdict auto-creates on first access. Single-line nested aggregation. Standard library solution. |
| Markdown table alignment | String manipulation with .ljust()/.rjust() | Markdown pipe syntax with consistent spacing | Markdown renderers handle alignment. Manual spacing breaks on variable-width fonts. Pipe syntax is standard. |
| Error pattern extraction | String splitting and index access | Regular expressions (re module) | Regex handles edge cases (extra whitespace, unexpected formats). Single compiled pattern faster than multiple string ops. |
| Per-folder aggregation | Manual loops over all_results for each folder | pandas groupby() + agg() | pandas handles grouping, aggregation, and sorting in optimized C code. Single line vs. nested loops. |

**Key insight:** Statistics and aggregation are solved problems in Python stdlib. collections module covers 90% of counting/grouping needs, pandas handles complex aggregations, re handles pattern extraction. Focus implementation effort on business logic (problem detection, recommendations), not reinventing Counter.

## Common Pitfalls

### Pitfall 1: tqdm ETA Not Displaying

**What goes wrong:** Progress bar shows percentage and rate but no ETA

**Why it happens:** tqdm only calculates ETA when `total=` parameter is set. If total is None or zero, ETA is undefined.

**How to avoid:** Verify `total=` is set correctly (line 1106 already does this: `total=total_files`). ETA appears automatically as "XX:XX remaining" in the progress bar.

**Warning signs:** Progress bar shows "? it/s" or no time estimate. Check that total_files calculation includes both new and checkpointed files (line 1092).

### Pitfall 2: Folder Stats Missing for Error Files

**What goes wrong:** Failed files don't appear in per-folder statistics, causing success rate calculation errors

**Why it happens:** Error results have page==0 and single-entry result list. Easy to skip in aggregation loop if checking page > 0.

**How to avoid:** Always aggregate at file level using file_results[0] for folder_path and filename. Check for errors with page==0 + 'error:' in notes. Include failed files in folder's file set.

**Warning signs:** Per-folder totals don't match campaign totals. Folders with 100% success rate despite campaign errors.

**Prevention code:**

```python
# Always extract folder_path from first result (works for both success and error)
folder_path = file_results[0].get('folder_path', '')
filename = file_results[0]['filename']
folder_stats[folder_path]['files'].add(filename)

# Separate check for file-level errors
if file_results[0]['page'] == 0 and 'error:' in file_results[0].get('notes', ''):
    folder_stats[folder_path]['failed_files'].add(filename)
```

### Pitfall 3: Pattern-Based Recommendations Too Generic

**What goes wrong:** Recommendations say "consider rescanning" for every problem folder without analyzing actual error patterns

**Why it happens:** Skipping D-06 requirement to analyze per-folder error patterns and match to specific recommendations

**How to avoid:** Calculate diagnostic ratios (preprocessing_fallback_rate, file_error_rate, page_error_rate) for each problem folder. Match thresholds to specific recommendations:
- High preprocessing rate (>50%) → scan quality issue → recommend rescanning
- High file error rate (>30%) → corrupted PDFs → recommend verifying source files
- High rotation variance → unusual orientations → recommend checking scanner settings

**Warning signs:** All problem folders get same recommendation. Recommendations don't match actual error types in CSV output.

### Pitfall 4: Markdown Table Column Alignment Breaks on Long Folder Paths

**What goes wrong:** Folder paths with many subdirectories break table alignment, making report unreadable

**Why it happens:** Manually padding columns with fixed widths assumes max path length. Long paths overflow, misaligning subsequent columns.

**How to avoid:** Use Markdown pipe syntax without manual padding — let the renderer handle alignment. If visual alignment in source matters, calculate max width dynamically per column and pad with f-string formatting.

**Warning signs:** Table columns misaligned in rendered Markdown. Folder path column extends into adjacent columns.

**Prevention pattern:**

```python
# Simple approach: No manual padding, let Markdown renderer handle it
table_lines.append(f"| {folder_display} | {row['Files']} | {row['Success Rate']:.1f}% | ...")

# Advanced approach: Dynamic padding based on max column width
max_folder_len = max(len(str(row['Folder'])) for _, row in df.iterrows())
table_lines.append(f"| {folder_display:<{max_folder_len}} | {row['Files']:>5} | ...")
```

### Pitfall 5: tabulate Version Mismatch Blocking pandas.to_markdown()

**What goes wrong:** Calling df.to_markdown() raises ImportError: "Pandas requires version '0.9.0' or newer of 'tabulate'"

**Why it happens:** Environment has tabulate 0.8.10 (verified installed), but pandas 3.0.3 requires tabulate>=0.9.0

**How to avoid:** Either (1) use f-string templates instead of pandas.to_markdown() (recommended for this phase), or (2) upgrade tabulate to 0.10.0 (latest as of March 2026). F-strings avoid dependency upgrade and provide more control over highlighting.

**Warning signs:** ImportError on df.to_markdown() call mentioning tabulate version requirement

**Resolution:**

```bash
# Option 1: Avoid pandas.to_markdown() — use f-strings (recommended)
# No changes needed, pattern shown in Architecture section

# Option 2: Upgrade tabulate (only if pandas.to_markdown() required later)
python -m pip install --upgrade tabulate  # 0.8.10 -> 0.10.0
```

## Code Examples

Verified patterns from official sources and existing codebase:

### tqdm Postfix Update for Running Stats

```python
# Source: tqdm documentation + existing code at lines 1155-1159
# Already implemented — shows how to extend

pbar.set_postfix({
    'IDs': stats['ids'],
    'No-ID': stats['no_id_pages'],
    'Errors': stats['errors']
})

# To add folder count:
pbar.set_postfix({
    'IDs': stats['ids'],
    'No-ID': stats['no_id_pages'],
    'Errors': stats['errors'],
    'Folders': len(folder_stats)
})
```

### Error Type Extraction and Counting

```python
# Source: Python re module + collections.Counter
from collections import Counter
import re

def categorize_errors(results: list[dict]) -> dict[str, int]:
    """Extract error types from notes field and count occurrences.

    Notes format: "error: FileNotFoundError: file.pdf not found"
    Returns: {'FileNotFoundError': 12, 'PDFPageCountError': 5, ...}
    """
    error_pattern = re.compile(r'error:\s*(\w+):')
    error_counter = Counter()

    for r in results:
        notes = r.get('notes', '')
        if r.get('page') == 0 and 'error:' in notes:
            match = error_pattern.search(notes)
            if match:
                error_type = match.group(1)
                error_counter[error_type] += 1
            else:
                # Fallback for unstructured errors
                error_counter['Unknown'] += 1

    return dict(error_counter.most_common())

# Usage in enhanced print_batch_stats():
error_breakdown = categorize_errors(all_results)
if error_breakdown:
    print("\nError breakdown:")
    for error_type, count in error_breakdown.items():
        print(f"  {error_type}: {count}")
```

### Nested defaultdict for Per-Folder Aggregation

```python
# Source: collections.defaultdict documentation + best practices
from collections import defaultdict, Counter

# Initialize with lambda returning dict of default values
folder_stats = defaultdict(lambda: {
    'total_pages': 0,
    'files': set(),
    'failed_files': set(),
    'ids_found': 0,
    'no_id_pages': 0,
    'rotations': Counter(),
    'preprocessing_fallbacks': 0
})

# Single-line aggregation in loop (no key existence checks)
folder_path = file_results[0].get('folder_path', '')
folder_stats[folder_path]['total_pages'] += 1
folder_stats[folder_path]['ids_found'] += len(r['ids'])
folder_stats[folder_path]['rotations'][r['rotation_detected']] += 1
```

### Condensed Per-Folder Table for Console Display

```python
# Source: D-09 decision + pandas sorting
def display_condensed_folder_stats(folder_stats: dict, top_n: int = 10) -> None:
    """Show top N worst folders in console per D-09."""

    # Build DataFrame for sorting
    folder_rows = []
    for folder_path, stats in folder_stats.items():
        total_files = len(stats['files'])
        failed_files = len(stats['failed_files'])
        success_rate = ((total_files - failed_files) / total_files * 100) if total_files > 0 else 0

        folder_rows.append({
            'Folder': folder_path if folder_path else '(root)',
            'Files': total_files,
            'Success Rate': success_rate,
            'Failed': failed_files
        })

    df = pd.DataFrame(folder_rows)
    df = df.sort_values('Success Rate', ascending=True)  # Worst first

    # Display top N
    print(f"\nTop {top_n} worst folders by success rate:")
    print("-" * 60)
    for _, row in df.head(top_n).iterrows():
        print(f"{row['Folder']:<30} | {row['Files']:>5} files | {row['Success Rate']:>5.1f}% success | {row['Failed']:>3} failed")

    # Campaign totals
    total_files_all = sum(len(stats['files']) for stats in folder_stats.values())
    total_failed_all = sum(len(stats['failed_files']) for stats in folder_stats.values())
    overall_success = ((total_files_all - total_failed_all) / total_files_all * 100) if total_files_all > 0 else 0

    print("-" * 60)
    print(f"{'OVERALL':<30} | {total_files_all:>5} files | {overall_success:>5.1f}% success | {total_failed_all:>3} failed")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual progress printing | tqdm with auto ETA | tqdm 4.67.3 (Feb 2026) | ETA calculation and display built-in when total= is set. Zero code needed. |
| dict.get(key, 0) for counting | collections.Counter | Python 3.x stdlib | 3x faster, cleaner syntax, .most_common() built-in |
| Manual nested dict init | collections.defaultdict | Python 3.x stdlib | Auto-creates missing keys, single-line aggregation |
| pandas.to_markdown() | F-string templates | Design choice | More control over formatting and highlighting, no tabulate dependency version conflict |
| tabulate 0.8.10 | tabulate 0.10.0 | March 2026 release | Pandas 3.0.3 requires >=0.9.0. Upgrade available but not required for f-string approach. |

**Deprecated/outdated:**

- **Manual dict initialization for nested stats:** Use defaultdict(lambda: {...}) instead. Cleaner and less error-prone.
- **Hardcoded table column widths in Markdown:** Markdown renderers handle alignment automatically with pipe syntax. Manual padding breaks on variable-width content.

## Open Questions

None — all requirements well-defined in CONTEXT.md, existing code provides clear integration points, stdlib modules cover all technical needs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All code | ✓ | 3.14.2 | — |
| pytest | Test validation | ✓ | 9.0.2 | — |
| tqdm | Progress bar + ETA | ✓ | 4.67.3 | — |
| pandas | Table aggregation | ✓ | 3.0.3 | — |
| collections | Stats aggregation | ✓ | stdlib | — |
| re | Error pattern extraction | ✓ | stdlib | — |
| pathlib | Path operations | ✓ | stdlib | — |
| datetime | Timestamps | ✓ | stdlib | — |
| tabulate | pandas.to_markdown() | ✓ | 0.8.10 (requires >=0.9.0 for pandas 3.0.3) | Use f-strings instead (recommended) |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- **tabulate >=0.9.0** — Optional for pandas.to_markdown(). Fallback: Use f-string templates for Markdown generation (recommended approach). Upgrade path available (pip install --upgrade tabulate → 0.10.0) if needed in future phases.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini |
| Quick run command | `python -m pytest tests/test_precede_ocr.py -x` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STAT-01 | tqdm displays ETA during processing | unit | `python -m pytest tests/test_precede_ocr.py::test_tqdm_eta_display -x` | ❌ Wave 0 |
| STAT-02 | Exit summary shows error type breakdown | unit | `python -m pytest tests/test_precede_ocr.py::test_error_categorization -x` | ❌ Wave 0 |
| STAT-03 | View stats shows per-folder quality breakdown | unit | `python -m pytest tests/test_precede_ocr.py::test_folder_stats_aggregation -x` | ❌ Wave 0 |
| STAT-04 | Campaign report generated with problem highlights | unit | `python -m pytest tests/test_precede_ocr.py::test_campaign_report_generation -x` | ❌ Wave 0 |
| STAT-05 | Report includes preprocessing/rotation distribution | unit | `python -m pytest tests/test_precede_ocr.py::test_preprocessing_rotation_stats -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_precede_ocr.py::test_{relevant_function} -x`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_precede_ocr.py::test_tqdm_eta_display` — covers STAT-01 (verify tqdm total= parameter set, ETA displayed)
- [ ] `tests/test_precede_ocr.py::test_error_categorization` — covers STAT-02 (categorize_errors() extracts exception types, print_batch_stats() displays breakdown)
- [ ] `tests/test_precede_ocr.py::test_folder_stats_aggregation` — covers STAT-03 (defaultdict accumulation, handle_view_stats() display)
- [ ] `tests/test_precede_ocr.py::test_campaign_report_generation` — covers STAT-04 (generate_campaign_report() creates Markdown with highlighting)
- [ ] `tests/test_precede_ocr.py::test_preprocessing_rotation_stats` — covers STAT-05 (rotation distribution and preprocessing fallback rate calculation)

## Sources

### Primary (HIGH confidence)

**Python Standard Library Documentation:**
- [collections — Container datatypes](https://docs.python.org/3/library/collections.html) - Counter and defaultdict official docs
- [re — Regular expression operations](https://docs.python.org/3/library/re.html) - Pattern extraction for error categorization

**Official Package Documentation:**
- [tqdm · PyPI](https://pypi.org/project/tqdm/) - Version 4.67.3, official release info
- [tqdm.tqdm - tqdm documentation](https://tqdm.github.io/docs/tqdm/) - Postfix and ETA parameters
- [pandas.DataFrame.to_markdown — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_markdown.html) - Markdown export capabilities
- [tabulate · PyPI](https://pypi.org/project/tabulate/) - Version history and 0.10.0 release (March 2026)

**Existing Codebase:**
- `precede_ocr.py` lines 1090-1212 - process_all_pdfs() with tqdm and stats aggregation patterns
- `precede_ocr.py` lines 777-832 - calculate_batch_stats() and print_batch_stats() baseline implementation
- `precede_ocr.py` lines 1273-1298 - handle_view_stats() menu handler
- `precede_ocr.py` lines 228-241 - compute_folder_path() normalization

### Secondary (MEDIUM confidence)

**Best Practices and Tutorials:**
- [Ultimate guide to tqdm library in Python](https://deepnote.com/blog/ultimate-guide-to-tqdm-library-in-python) - Postfix usage and customization
- [How to Use Python's collections Module Effectively](https://medium.com/@AlexanderObregon/how-to-use-pythons-collections-module-effectively-2e32b6bf6eae) - Counter and defaultdict performance and use cases
- [Python F-String: A Complete Guide | DataCamp](https://www.datacamp.com/tutorial/python-f-string) - Multi-line f-string formatting
- [Python Collections Module Tutorial: Guide to High-Performance Data Structures](https://netalith.com/blogs/computer-science/python-collections-module-tutorial-2026) - Nested defaultdict patterns for aggregation

### Tertiary (LOW confidence)

None — all critical claims verified with official documentation or existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib or already installed (tqdm 4.67.3, pandas 3.0.3 verified)
- Architecture: HIGH - Integration points clearly mapped in existing code (lines 1090-1298), patterns proven in stdlib
- Pitfalls: MEDIUM-HIGH - tqdm ETA and folder stats pitfalls well-documented in sources; tabulate version mismatch discovered via environment check
- Environment: HIGH - All tools verified available via python -c and pip show commands

**Research date:** 2026-06-07
**Valid until:** ~30 days (2026-07-07) — stdlib patterns stable, tqdm/pandas versions current as of research date
