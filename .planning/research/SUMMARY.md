# Project Research Summary

**Project:** Precede OCR — v1.3 Results Cleanup & ID Lookup
**Domain:** OCR Post-Processing, Data Cleanup, and Lookup Generation
**Researched:** 2026-06-09
**Confidence:** HIGH

## Executive Summary

This milestone transforms raw OCR scan output (52,055 IDs extracted from 30,365 PDFs) into a production-ready ID lookup system while investigating and resolving data quality issues. The research reveals that **no new dependencies are needed** — the existing pandas 3.0.3 + Python stdlib stack fully covers all post-processing, deduplication, error investigation, and quality reporting requirements.

The recommended approach uses **integrated CLI subcommands** within the existing `precede_ocr.py` rather than separate utility scripts. This architecture maintains code cohesion, provides a unified user interface, and reduces maintenance burden while enabling clear separation of concerns through argparse subparsers. Post-processing operations are I/O-bound (not CPU-bound) and complete in seconds on the 52K-row dataset, requiring no parallelization.

The primary risk is **overzealous noise filtering silently deleting real IDs**. With 5,141 multi-ID pages (11.2% of corpus), aggressive deduplication could remove legitimate sequential IDs while trying to eliminate OCR artifacts. Mitigation: preserve raw data, bias toward retention over deletion, validate filter decisions on random samples before full deployment, and use exact-match-only deduplication within pages.

## Key Findings

### Recommended Stack

**NO NEW DEPENDENCIES NEEDED.** All v1.3 requirements map to existing pandas 3.0.3 + Python stdlib capabilities:

**Core technologies:**
- **pandas 3.0.3**: ID lookup generation (`sort_values`, `to_csv`), deduplication (`drop_duplicates`, `duplicated`), error analysis (`groupby`, `value_counts`) — handles 52K rows in <1 second total
- **pathlib (stdlib)**: Extract folder paths from filenames, already used in v1.0 for file discovery
- **json (stdlib)**: Load campaign_state.json for failure investigation, already used for checkpointing
- **collections.Counter/defaultdict (stdlib)**: Error frequency analysis, rotation distribution, already used in v1.1 reporting
- **f-string templates (stdlib)**: Quality report generation using existing v1.1 markdown pattern from campaign_report.md

**Libraries evaluated and rejected:**
- **ydata-profiling**: Overkill for targeted error analysis (generates full EDA reports), 52K rows manageable with manual pandas analysis
- **openpyxl/xlsxwriter**: Not needed — CSV with UTF-8 BOM (`encoding='utf-8-sig'`) is Excel-compatible without styling libraries
- **pandera**: Schema validation overkill for one-time post-processing analysis

### Expected Features

**Must have (table stakes):**
- **ID Lookup CSV (sorted by ID)**: Primary deliverable — enables "which file has ID 12345?" queries in Excel
- **Failed File Investigation**: 49 failures (46 FileNotFoundError, 3 EmptyFileError) must be categorized and root causes identified
- **No-Match Page Investigation**: 59 pages with no ID extraction must be analyzed (real blanks vs OCR failures)
- **Multi-ID Deduplication**: 5,141 pages with multiple IDs need filtering to separate real multi-page documents from OCR noise
- **Error/Quality Report**: Structured markdown report documenting findings, error categories, root causes, recommendations

**Should have (competitive):**
- **Confidence-Based Duplicate Filtering**: Use Tesseract confidence scores (accept >90%, review 70-90%, reject <70%) to eliminate OCR artifacts without manual review
- **Bounding Box Overlap Detection**: Detect same ID read multiple times at different rotations via spatial overlap (IoU/NMS) if confidence filtering insufficient
- **Statistical Outlier Detection**: Flag anomalous results using IQR or Modified Z-Score (e.g., pages with 10+ IDs) to surface edge cases

**Defer (v2+):**
- **Automated Re-Processing Pipeline**: Nice-to-have diagnostic tool for failed files, not critical for v1.3 deliverables
- **Visual Inspection UI**: Only if automated filtering fails to reduce manual review workload to <50 pages

### Architecture Approach

The existing v1.0-v1.2 pipeline produces `results.csv` (scan output) and `checkpoint.json` (per-file results). V1.3 extends this with **post-processing subcommands** integrated into `precede_ocr.py` using argparse subparsers. This maintains single entry point, enables shared utilities (checkpoint reading, CSV parsing), and follows industry best practices (git, docker, AWS CLI all use subcommands).

**Major components:**
1. **CLI Subcommand Dispatcher** — `python precede_ocr.py scan|lookup|investigate|clean-multi-ids` routes to handler functions
2. **Lookup Generator** — transforms scan CSV to ID lookup CSV (sort by ID, add folder column, optional deduplication)
3. **Error Investigator** — analyzes checkpoint.json failures, categorizes by error type (FileNotFoundError, EmptyFileError), produces markdown report
4. **Multi-ID Analyzer** — detects OCR noise patterns (sequence outliers, rotation consistency, confidence scores), applies conservative deduplication heuristics
5. **Shared Utilities** — read_checkpoint_data(), read_scan_csv(), generate_error_report() reused across subcommands

**Data flow:** Post-processing is I/O-bound (pandas operations <1s on 52K rows), requires no parallelization, produces user-facing CSV outputs and technical markdown reports.

### Critical Pitfalls

1. **Overzealous Noise Filtering Silently Deletes Real IDs** — Conservative filters set too strict (e.g., reject OCR confidence <80%) remove legitimate IDs from degraded but valid scans. **Mitigation:** Bias toward preservation, create "low_confidence" flag instead of deleting, validate filter on 200-ID sample before full run, preserve raw data for recovery.

2. **Deduplication False Positives Lose Multi-ID Context** — Dedup logic treats multiple legitimate IDs on same page as "duplicates" and arbitrarily keeps one. With 5,141 multi-ID pages (11.2% of corpus), this is a known production pattern, not an error. **Mitigation:** Preserve multi-ID pages (2-5 IDs normal, >5 suspicious), exact-match deduplication only (no fuzzy matching across pages), validate sequential ID patterns.

3. **FileNotFoundError Misdiagnosis (Race Condition vs Real Missing Files)** — 46 FileNotFoundError failures might be Windows multiprocessing 'spawn' race conditions or Unicode path encoding issues, not actually missing files. **Mitigation:** Manually verify file existence, test with failing paths in single-threaded mode, use absolute paths (`Path.resolve()`), add retry logic with backoff.

4. **Lookup CSV Corruption from Unescaped Special Characters** — pandas default CSV export breaks in Excel (UTF-8 without BOM shows mojibake, commas in filenames split columns, 5-digit IDs interpreted as dates). **Mitigation:** Export with `encoding='utf-8-sig'`, `quoting=csv.QUOTE_NONNUMERIC`, `index=False`, test roundtrip in actual Excel.

5. **No-Match Page Investigation Confirms Broken OCR, Ignores User-Facing Impact** — Technical report identifies root causes but fails to produce actionable output (which files affected, what to do). **Mitigation:** Export `no_match_pages.csv` with filename/page/reason/recommendation columns, integrate status into main lookup file, attach sample preprocessed images for validation.

## Implications for Roadmap

Based on research, suggested phase structure follows incremental risk-reduction approach:

### Phase 1: CLI Refactor (Foundation)
**Rationale:** Pure refactor with zero functional changes establishes subcommand architecture before adding new features. Validates existing behavior preserved while creating foundation for lookup/investigate/clean commands.

**Delivers:**
- Refactored `main()` using argparse subparsers
- Existing OCR pipeline moved to `cmd_scan()` function
- `python precede_ocr.py scan <dir>` produces identical output to v1.2
- All 236 existing tests pass

**Addresses:** Architecture pattern (integrated subcommands vs separate scripts)
**Avoids:** Code fragmentation, duplicated utilities, maintenance burden
**Risk:** LOW — pure refactor, no logic changes
**Research flag:** SKIP research-phase (standard argparse pattern, well-documented)

---

### Phase 2: Lookup Generation (Immediate Value)
**Rationale:** Highest-value, zero-risk feature — reads existing CSV, transforms, writes new CSV without touching pipeline. Delivers primary v1.3 goal (sorted ID lookup for Excel) with no dependencies on error investigation or multi-ID cleanup.

**Delivers:**
- `python precede_ocr.py lookup results.csv` generates sorted lookup CSV
- Columns: ID, Filename, Page, Folder
- Excel-compatible export (`utf-8-sig`, proper quoting)
- Folder paths extracted from filenames via pathlib

**Addresses:** ID Lookup CSV (table stakes feature)
**Avoids:** Lookup CSV corruption pitfall (Excel encoding/formatting issues)
**Uses:** pandas `sort_values`, `to_csv`, pathlib `Path.parent`
**Risk:** ZERO — reads existing data, creates new file, no pipeline modification
**Research flag:** SKIP research-phase (standard pandas CSV transformation)

---

### Phase 3: Error Investigation (Diagnostic Value)
**Rationale:** Analyzes existing checkpoint.json to categorize 49 failed files and 59 no-match pages. Independent of lookup generation and multi-ID cleanup. Produces both technical report (root cause analysis) and user-facing output (no_match_pages.csv with recommendations).

**Delivers:**
- `python precede_ocr.py investigate` produces error_report.md
- Categorizes failures by type (FileNotFoundError, EmptyFileError, etc.)
- Analyzes no-match pages (blank/degraded/ocr_failed categories)
- Exports `no_match_pages.csv` with actionable recommendations
- Manual verification of FileNotFoundError root causes (race condition vs missing files)

**Addresses:** Failed File Investigation, No-Match Page Investigation (table stakes)
**Avoids:** FileNotFoundError misdiagnosis pitfall, no-match investigation without user impact
**Uses:** pandas filtering, `groupby`, `value_counts`, json checkpoint loading
**Risk:** ZERO — reads existing checkpoint, writes reports, no pipeline changes
**Research flag:** SKIP research-phase (standard data analysis, error categorization patterns established)

---

### Phase 4: Multi-ID Cleanup (Quality Improvement)
**Rationale:** Most complex feature — requires heuristics to distinguish real multi-ID pages from OCR noise. Built last to leverage validation experience from Phases 2-3. Uses conservative exact-match-only deduplication to avoid false positives.

**Delivers:**
- `python precede_ocr.py clean-multi-ids results.csv` produces cleaned CSV
- Heuristic 1: Remove `seq_outlier_conf_0%` IDs on multi-ID pages (uses existing pipeline sequence validation)
- Heuristic 2: Rotation consistency (mixed rotations = OCR noise, consistent = real)
- Heuristic 3: Statistical outlier detection (IQR method flags pages with >Q3+1.5×IQR IDs)
- Sample validation on 200-ID subset before full deployment
- Preserves raw data for recovery if filter tuning needed

**Addresses:** Multi-ID Deduplication (table stakes), Confidence-Based Filtering (competitive)
**Avoids:** Overzealous filtering pitfall, deduplication false positives pitfall
**Uses:** pandas `groupby`, `duplicated`, sequence validation from existing notes field
**Risk:** LOW — heuristics may need tuning, but original data preserved, sample validation prevents silent data loss
**Research flag:** SKIP research-phase (deduplication patterns researched, validation approach defined)

---

### Phase Ordering Rationale

- **Phase 1 before all others:** CLI refactor is foundation for Phases 2-4 (all use subcommands). Pure refactor with test validation minimizes risk.
- **Phases 2-4 are independent:** Can be built in parallel after Phase 1 complete. Ordered by value/risk ratio: lookup (high value, zero risk) → investigate (medium value, zero risk) → multi-ID (high value, low risk with validation).
- **Multi-ID cleanup last:** Most complex heuristics, benefits from experience with data patterns observed in Phases 2-3. Conservative approach (exact-match only, sample validation) prevents pitfall #1 (overzealous filtering).
- **No external research needed:** All patterns established in research phase, implementation uses standard pandas/stdlib operations.

### Research Flags

**Phases with standard patterns (SKIP research-phase):**
- **Phase 1 (CLI Refactor):** argparse subparsers well-documented in official Python docs, industry standard pattern (git, docker, AWS CLI)
- **Phase 2 (Lookup Generation):** pandas CSV transformation standard operation, `sort_values`/`to_csv` covered in official docs
- **Phase 3 (Error Investigation):** Error categorization patterns established, pandas filtering/aggregation standard
- **Phase 4 (Multi-ID Cleanup):** Deduplication techniques researched (IQR outlier detection, IoU/NMS, confidence thresholding), validation approach defined

**No phases need deeper research** — all required patterns, libraries, and heuristics identified in project research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | pandas 3.0.3 + stdlib fully covers requirements, no new dependencies, performance tested to millions of rows (52K trivial) |
| **Features** | HIGH | Table stakes features (lookup, error investigation, multi-ID cleanup) clearly defined, competitive features (confidence filtering, bounding box) scoped for v2+ |
| **Architecture** | HIGH | Subcommand pattern well-researched (official argparse docs, multiple 2026 best practice articles), integration points clear, backward compatibility plan defined |
| **Pitfalls** | MEDIUM | Top 5 pitfalls identified with mitigation strategies, but heuristics (confidence thresholds, dedup rules) need validation on production data — sample testing reduces risk |

**Overall confidence:** HIGH

### Gaps to Address

**Heuristic tuning during implementation:**
- **Multi-ID confidence threshold:** Start with `seq_outlier_conf_0%` (most conservative), tune based on 200-ID sample validation. If false negative rate >1%, adjust.
- **Statistical outlier threshold:** IQR method (Q3 + 1.5×IQR) is standard, but production data may require adjustment to 2.0×IQR if flagging too many legitimate multi-page documents.
- **Rotation consistency logic:** If sequential IDs have different rotations (e.g., 10001 at 90°, 10002 at 0°), keep both (likely real) vs same ID at different rotations (likely OCR noise at multiple passes).

**Validation checkpoints:**
- **Excel roundtrip test:** Export lookup CSV → Open in Excel → Verify appearance → Re-save → Verify data integrity. Catches encoding/formatting issues before user delivery.
- **FileNotFoundError reproduction:** Extract 46 failing file paths, test in isolation (single-threaded) to distinguish multiprocessing race conditions from real missing files.
- **No-match page sampling:** Manually inspect 5-10 examples per category (blank/degraded/ocr_failed) to validate automated categorization logic.

**Recovery plan if heuristics fail:**
- All phases preserve raw data (original results.csv, checkpoint.json)
- Cleaned output can be regenerated with adjusted filters
- Low recovery cost (minutes to re-run post-processing) vs high cost if raw data lost (hours to re-run OCR)

## Sources

### Primary (HIGH confidence)

**Technology Stack:**
- pandas 3.0.3 official documentation — drop_duplicates, sort_values, groupby, to_csv methods
- Python argparse documentation — subparser pattern for CLI subcommands
- pandas.DataFrame.to_csv — Excel-compatible CSV export settings

**Feature Patterns:**
- Tesseract OCR confidence levels — industry standard thresholds (>90% accept, 70-90% review, <70% reject)
- Intersection over Union (IoU) — bounding box overlap detection (NMS)
- IQR Method Outlier Detection — statistical anomaly flagging

**Architecture Patterns:**
- Command-Line Subcommands with Python's argparse (Medium) — best practices for CLI design
- How to Build CLI Applications with argparse (OneUpTime) — subcommand implementation patterns

### Secondary (MEDIUM confidence)

**Pitfall Research:**
- OCR Post-Processing Error Correction (arXiv) — false positive rate concerns in OCR filtering
- Noise-Robust De-Duplication at Scale (arXiv) — OCR extraction errors in deduplication
- Fuzzy Matching 101 (DataLadder) — threshold tuning to prevent false positives
- Fix FileNotFoundError With Multiprocessing (Super Fast Python) — Windows race condition patterns

**CSV Export Issues:**
- How to Fix CSV Encoding Problems (CSV Viewer) — UTF-8 BOM for Excel compatibility
- Why Excel corrupts CSV data (POWER CSV) — auto-formatting pitfalls (date conversion, scientific notation)

**Data Quality:**
- 7 Essential Data Quality Checks with Pandas (KDnuggets) — validation patterns
- Data Quality Audit Guide 2026 (Improvado) — report structure (executive summary, error breakdown, root cause analysis, recommendations)

### Tertiary (LOW confidence)

- Pandas Profiling for EDA (ydata-profiling) — evaluated for automated profiling, rejected as overkill for 52K rows
- Data Validation with Pandera — evaluated for schema validation, rejected for one-time analysis

---
*Research completed: 2026-06-09*
*Ready for roadmap: yes*
