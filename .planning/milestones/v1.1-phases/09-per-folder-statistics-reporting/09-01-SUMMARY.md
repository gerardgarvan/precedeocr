---
phase: 09-per-folder-statistics-reporting
plan: 01
subsystem: statistics-engine
tags: [stats, per-folder, error-breakdown, reporting]
dependency_graph:
  requires: [STATE-06, SHUT-01, MENU-01]
  provides: [STAT-01, STAT-02, STAT-03, STAT-05]
  affects: [process_all_pdfs, calculate_batch_stats, print_batch_stats, handle_view_stats]
tech_stack:
  added: []
  patterns: [local-aggregation, defaultdict-accumulation, counter-frequency]
key_files:
  created: []
  modified:
    - precede_ocr.py
    - tests/test_precede_ocr.py
decisions:
  - title: "Local folder stats aggregation in main process"
    rationale: "Avoids multiprocessing.Manager IPC overhead (10-100x slower). Workers return results to main, main accumulates per-folder metrics in defaultdict. Zero IPC cost."
    alternatives: ["Manager.dict shared state (rejected: IPC bottleneck)", "Workers track own stats (rejected: merge complexity)"]
  - title: "Counter for rotation distribution tracking"
    rationale: "Natural fit for counting rotation angles (0/90/180/270). Efficient, built-in frequency ordering via most_common()."
  - title: "Top 10 worst folders display in menu"
    rationale: "Condensed view surfaces problem areas quickly. Full details available in campaign_report.md (future). Sorted by success rate ascending shows worst first."
metrics:
  duration_minutes: 7
  tasks_completed: 3
  tests_added: 17
  files_modified: 2
  lines_added: 389
  lines_removed: 6
  completed_at: "2026-06-07T15:59:04Z"
---

# Phase 09 Plan 01: Per-Folder Statistics & Error Breakdown Summary

**One-liner:** Local folder stats accumulation with error categorization, enhanced exit summary, and condensed worst-folders view in campaign menu.

## What Was Built

Added per-folder statistics infrastructure to `precede_ocr.py` that collects quality metrics during processing and surfaces them via enhanced console output. Implements STAT-01 (tqdm ETA), STAT-02 (error breakdown), STAT-03 (per-folder tracking), and STAT-05 (rotation/preprocessing stats).

### Key Components

1. **categorize_errors() function** (precede_ocr.py:835-859)
   - Extracts exception types from `notes` field (`error: ExceptionType: message` format)
   - Returns frequency-ordered dict using Counter.most_common()
   - Handles unknown error formats gracefully (categorizes as 'Unknown')

2. **Enhanced calculate_batch_stats()** (precede_ocr.py:777-811)
   - Calls categorize_errors() to build error_categories dict
   - Added to return value alongside existing summary/performance/resume_context

3. **Enhanced print_batch_stats()** (precede_ocr.py:829-847)
   - Displays "Error breakdown:" section with per-type counts when errors present
   - Always shows "Full details: campaign_report.md" pointer (per D-10)

4. **Folder stats accumulation** (precede_ocr.py:1132-1143, 1190-1215)
   - Added defaultdict with lambda factory for per-folder metrics
   - Tracks: total_pages, files (set), failed_files (set), ids_found, no_id_pages, rotations (Counter), preprocessing_fallbacks
   - Accumulates in process_all_pdfs() main loop (zero IPC overhead)
   - Persisted to campaign_state.folder_stats before return (sets converted to lists for JSON serialization)

5. **Enhanced handle_view_stats()** (precede_ocr.py:1365-1427)
   - Replaced basic stats with condensed per-folder table
   - Shows top 10 worst folders sorted by success rate ascending
   - Displays: folder name, file count, success rate %, failed count
   - Includes OVERALL totals row
   - Empty folder_stats handled gracefully (no table shown)

6. **tqdm postfix enhancement** (precede_ocr.py:1230-1235)
   - Added 'Folders' count to existing IDs/No-ID/Errors display
   - ETA already functional (total=total_files set on line 1148)

### Test Coverage

Added 17 comprehensive tests across 5 test classes (tests/test_precede_ocr.py:2766-3011):

- **TestCategorizeErrors (6 tests):** Single/multiple error types, non-error filtering, unknown format handling, empty results, frequency ordering
- **TestEnhancedBatchStats (4 tests):** Error categories in calculate_batch_stats, error breakdown display, report pointer
- **TestHandleViewStatsFolder (3 tests):** Folder breakdown display, empty stats handling, success rate sorting
- **TestTqdmEtaDisplay (2 tests):** tqdm total= parameter verification, Folders postfix presence
- **TestPreprocessingRotationStats (2 tests):** Rotation tracking, preprocessing fallback counting

All 220 tests pass (203 existing + 17 new).

## Deviations from Plan

None. Plan executed exactly as written. All required functions added, all tests pass.

## Verification Results

```bash
# All Phase 9 tests pass
$ python -m pytest tests/test_precede_ocr.py::TestCategorizeErrors tests/test_precede_ocr.py::TestEnhancedBatchStats tests/test_precede_ocr.py::TestHandleViewStatsFolder tests/test_precede_ocr.py::TestTqdmEtaDisplay tests/test_precede_ocr.py::TestPreprocessingRotationStats -v
============================= 17 passed in 2.26s ==============================

# Full test suite passes
$ python -m pytest tests/test_precede_ocr.py -x
============================ 220 passed in 13.94s =============================

# categorize_errors extracts error types correctly
$ python -c "from precede_ocr import categorize_errors; print(categorize_errors([{'page':0,'notes':'error: FileNotFoundError: x','filename':'a.pdf','ids':[]}]))"
{'FileNotFoundError': 1}

# folder_stats accumulation present in source
$ python -c "import inspect; from precede_ocr import process_all_pdfs; s=inspect.getsource(process_all_pdfs); assert 'folder_stats' in s; print('OK')"
OK

# handle_view_stats shows success_rate
$ python -c "import inspect; from precede_ocr import handle_view_stats; s=inspect.getsource(handle_view_stats); assert 'success_rate' in s; print('OK')"
OK
```

## Requirements Satisfied

- **STAT-01:** tqdm ETA display verified (total= parameter already set in v1.0, confirmed via test)
- **STAT-02:** Error type breakdown added to exit summary via categorize_errors() + enhanced print_batch_stats()
- **STAT-03:** Per-folder tracking via folder_stats defaultdict, displayed in handle_view_stats() condensed table
- **STAT-05:** Rotation distribution (Counter) and preprocessing fallback rate tracked per folder

## Known Stubs

None. All functionality is fully wired:
- categorize_errors() extracts real error types from notes field
- folder_stats accumulates real metrics from worker results
- handle_view_stats() displays real folder_stats from campaign_state
- print_batch_stats() shows real error_categories from calculate_batch_stats()

## Self-Check: PASSED

**Created files exist:**
- N/A (no new files created, only modifications)

**Modified files exist:**
```bash
$ ls -l precede_ocr.py tests/test_precede_ocr.py
-rwxr-xr-x 1 Owner 197121  84242 Jun  7 15:59 precede_ocr.py
-rwxr-xr-x 1 Owner 197121 106429 Jun  7 15:52 tests/test_precede_ocr.py
```

**Commits exist:**
```bash
$ git log --oneline -3
494b8d2 feat(09-01): enhance handle_view_stats with per-folder breakdown
b3a10b3 feat(09-01): add categorize_errors and folder stats accumulation
e7f9a43 feat(08-02): integrate re-run failures, fresh start, export partial handlers
```

All claimed functionality verified present in codebase.
