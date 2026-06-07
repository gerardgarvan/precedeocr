# Phase 9: Per-Folder Statistics & Reporting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 09-per-folder-statistics-reporting
**Areas discussed:** Report content, Problem detection, Console vs. report, Stats granularity

---

## Report Content

### Q1: How comprehensive should campaign_report.md be?

| Option | Description | Selected |
|--------|-------------|----------|
| Full report | Executive summary + per-folder stats table + problem area highlights + rotation/preprocessing breakdown + recommendations. One-stop reference for the entire campaign run. | ✓ |
| Minimal data dump | Just the per-folder stats table and totals. No narrative, no recommendations. Quick to scan but less actionable. | |
| You decide | Claude picks the right level of detail based on what the data contains. | |

**User's choice:** Full report (Recommended)
**Notes:** None

### Q2: Should the report include a per-file error listing or just per-folder aggregates?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-folder aggregates | Show error counts and success rates per folder. Individual file errors are already in CSV output — report stays concise. | ✓ |
| Per-file listing in problem folders | For folders flagged as problems, list each failed file and its error. More detailed but potentially very long for large campaigns. | |
| Both with collapsible sections | Aggregates for all folders, with per-file details only in problem folders. Uses Markdown headers so it's easy to skip. | |

**User's choice:** Per-folder aggregates (Recommended)
**Notes:** None

### Q3: Where should the report file be written?

| Option | Description | Selected |
|--------|-------------|----------|
| Same as CSV/JSON output dir | campaign_report.md goes alongside precede_results.csv and precede_results.json in the output directory. Everything in one place. | ✓ |
| Next to input directory | Write report beside the PDF source directory instead of the output directory. | |

**User's choice:** Same as CSV/JSON output dir (Recommended)
**Notes:** None

### Q4: Should the report auto-generate on every campaign completion, or only when explicitly requested?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generate always | Report written automatically when campaign completes or is exported. No extra CLI flag needed. | ✓ |
| CLI flag --report | Only generate report when user passes --report flag. Keeps default output lean. | |
| Both: auto + --no-report opt-out | Generate by default, but allow --no-report to suppress if not wanted. | |

**User's choice:** Auto-generate always (Recommended)
**Notes:** None

---

## Problem Detection

### Q5: What should trigger a folder being flagged as a 'problem area' in the report?

| Option | Description | Selected |
|--------|-------------|----------|
| Success rate below 80% | Flag folders where fewer than 80% of files produced at least one valid ID. Catches consistently bad folders without over-flagging. | ✓ |
| Any errors at all | Flag every folder with at least one failed file. Very conservative — may flag many folders with a single flaky PDF. | |
| You decide | Claude picks a reasonable threshold based on the data distribution (e.g., flag outliers relative to the campaign average). | |

**User's choice:** Success rate below 80% (Recommended)
**Notes:** None

### Q6: What kind of recommendations should be generated for problem folders?

| Option | Description | Selected |
|--------|-------------|----------|
| Pattern-based hints | Analyze error patterns and suggest actions: high preprocessing fallback -> 'low scan quality, consider rescanning'; all rotation failures -> 'unusual page orientation'; file-level errors -> 'corrupted PDFs, verify source files'. | ✓ |
| Generic guidance only | Same generic text for all problem folders. Simpler to implement. | |
| You decide | Claude determines what recommendations make sense based on available data. | |

**User's choice:** Pattern-based hints (Recommended)
**Notes:** None

### Q7: Should problem folders be visually highlighted in the Markdown table?

| Option | Description | Selected |
|--------|-------------|----------|
| Bold + emoji marker | Problem folders get a warning emoji prefix and bold text in the table row. Easy to spot when scanning. | ✓ |
| Separate section | Problem folders get their own section below the main table with details. Main table stays clean. | |
| Both | Mark in main table AND list separately in a 'Problem Areas' section with recommendations. | |

**User's choice:** Bold + emoji marker (Recommended)
**Notes:** None

---

## Console vs. Report

### Q8: How should ETA be displayed during processing?

| Option | Description | Selected |
|--------|-------------|----------|
| tqdm built-in ETA | tqdm has built-in ETA when total= is set. Already configured. Zero extra code. | ✓ |
| Custom ETA in postfix | Calculate ETA manually and show in postfix alongside IDs/No-ID/Errors. More control but duplicates tqdm's built-in. | |

**User's choice:** tqdm built-in ETA (Recommended)
**Notes:** None

### Q9: Should the menu 'View stats' show per-folder breakdown in the console?

| Option | Description | Selected |
|--------|-------------|----------|
| Enhanced console + report | Menu 'View stats' shows condensed per-folder table (top 10 worst folders + totals). Full detail in report. | ✓ |
| Console totals only | Keep menu showing just aggregate counts. Per-folder detail only in report file. | |
| Full per-folder in console | Complete per-folder breakdown in console. Could be very long. | |

**User's choice:** Enhanced console + report (Recommended)
**Notes:** None

### Q10: Should the exit summary include error type breakdown?

| Option | Description | Selected |
|--------|-------------|----------|
| Add error type breakdown | After existing batch summary, add breakdown of error types plus pointer to campaign_report.md. | ✓ |
| Keep current format | Just add a line pointing to the report file. | |
| You decide | Claude determines what to add. | |

**User's choice:** Add error type breakdown (Recommended)
**Notes:** None

---

## Stats Granularity

### Q11: Rotation distribution and preprocessing fallback — per-folder or aggregate?

| Option | Description | Selected |
|--------|-------------|----------|
| Both: aggregate + per-folder | Campaign-wide totals in summary, plus per-folder breakdown in detailed table. | ✓ |
| Campaign-wide aggregate only | One distribution for entire campaign. Simpler, less noise. | |
| Per-folder only | Stats only in per-folder rows. No separate aggregate section. | |

**User's choice:** Both: aggregate + per-folder (Recommended)
**Notes:** None

### Q12: How should the per-folder table be sorted?

| Option | Description | Selected |
|--------|-------------|----------|
| By success rate ascending | Worst folders first — problem areas at the top. Most actionable ordering. | ✓ |
| Alphabetical by folder path | Natural directory ordering. Easy to find a specific folder. | |
| By file count descending | Largest folders first. | |

**User's choice:** By success rate ascending (Recommended)
**Notes:** None

### Q13: Include 'Avg IDs/Page' column?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include it | Adds column to help spot folders with consistently zero or multiple IDs. | ✓ |
| No, keep table lean | Fewer columns, easier to read. | |

**User's choice:** Yes, include it (Recommended)
**Notes:** None

---

## Claude's Discretion

- Table column order and width in Markdown report
- Exact wording of pattern-based recommendations
- Number of folders shown in condensed console view (guideline: ~10 worst)
- Whether to include a "top performing folders" section in the report

## Deferred Ideas

None — discussion stayed within phase scope
