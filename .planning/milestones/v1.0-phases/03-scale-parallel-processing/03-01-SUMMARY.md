---
phase: 03-scale-parallel-processing
plan: 01
subsystem: pipeline
tags: [ocr, multi-id, json-output, csv-flattening, data-contract]

# Dependency graph
requires:
  - phase: 02-rotation-handling
    provides: "extract_id_with_rotation with multi-rotation OCR and early exit"
provides:
  - "select_all_valid_ids() for multi-ID extraction per page"
  - "Updated data contract: 'ids' list replaces 'id' single value"
  - "write_results_json() with nested {filename: {page: [ids]}} structure"
  - "CSV flattening: one row per ID when multiple IDs on one page"
  - "No-ID pages flagged as empty arrays in JSON and blank rows in CSV"
affects: [03-02-parallel-processing, batch-processing, output-formats]

# Tech tracking
tech-stack:
  added: [json, collections.defaultdict]
  patterns: [multi-id-data-contract, csv-flattening, nested-json-output]

key-files:
  created: []
  modified:
    - precede_ocr.py
    - tests/test_precede_ocr.py
    - tests/conftest.py

key-decisions:
  - "Return all valid IDs from successful rotation, not just first (D-02)"
  - "Filter trivial patterns without fallback in select_all_valid_ids (D-03)"
  - "CSV flattens multi-ID pages to one row per ID (D-01)"
  - "JSON uses nested {filename: {page: [ids]}} with empty arrays for no-ID pages (D-04)"
  - "Both CSV and JSON generated on every run (D-05)"

patterns-established:
  - "Multi-ID data contract: result dicts use 'ids' key with list[str] values"
  - "CSV flattening pattern: iterate r['ids'] to produce one row per ID"
  - "JSON nesting pattern: defaultdict(dict) -> nested[filename][page] = ids"

requirements-completed: [PIPE-06, PIPE-07, OUT-02]

# Metrics
duration: 5min
completed: 2026-06-05
---

# Phase 3 Plan 1: Multi-ID Data Contract and JSON Output Summary

**Multi-ID extraction returning all valid IDs per page, CSV one-row-per-ID flattening, and nested JSON output with empty-array no-ID flagging**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-05T14:31:54Z
- **Completed:** 2026-06-05T14:36:28Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Changed internal data contract from single-ID (`'id': str|None`) to multi-ID (`'ids': list[str]`) across entire pipeline
- Added `select_all_valid_ids()` that returns all valid IDs (no fallback to trivials, unlike deprecated `select_most_likely_id`)
- Updated `extract_id_with_rotation()` to return `(list[str], angle, notes)` instead of `(str|None, angle, notes)`
- Updated `write_results_csv()` to flatten multi-ID pages into one CSV row per ID (D-01)
- Added `write_results_json()` producing nested `{filename: {page: [ids]}}` structure (D-04)
- No-ID pages appear as empty arrays `[]` in JSON and blank id rows in CSV (PIPE-07)
- Both CSV and JSON always generated in `__main__` block (D-05)
- Test suite grown from 43 to 60 tests with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Multi-ID extraction and updated data contract** - `c176a79` (test: RED), `5135c0f` (feat: GREEN)
2. **Task 2: JSON output writer and no-ID page flagging** - `9428c13` (test: JSON output tests)

## Files Created/Modified
- `precede_ocr.py` - Added select_all_valid_ids(), write_results_json(), updated extract_id_with_rotation return type, updated process_single_pdf data contract, updated write_results_csv flattening, added --output-json CLI arg
- `tests/test_precede_ocr.py` - Added TestSelectAllValidIds (6 tests), TestWriteResultsJson (8 tests), updated all existing tests for new data contract
- `tests/conftest.py` - Updated sample_results fixture from 'id' to 'ids' key, added multi_id_results fixture

## Decisions Made
- **D-01 CSV flattening:** One row per ID. Pages with multiple IDs produce multiple rows sharing the same page number. Pages with no IDs produce one row with blank id column.
- **D-02 All IDs from rotation:** `select_all_valid_ids()` returns the complete list of valid matches from the successful rotation, not just the first.
- **D-03 No trivial fallback:** Unlike `select_most_likely_id()` which falls back to trivials when nothing else matches, `select_all_valid_ids()` returns empty list for all-trivial input.
- **D-04 JSON structure:** Nested `{filename: {page_str: [ids]}}` with page keys as strings and empty arrays for no-ID pages.
- **D-05 Dual output:** Both CSV and JSON generated on every run. JSON path defaults to CSV path with `.json` extension.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Implemented write_results_json in Task 1 instead of Task 2**
- **Found during:** Task 1 (data contract change)
- **Issue:** The JSON writer was tightly coupled with the data contract change. Implementing it alongside CSV in Task 1 ensured both output paths were validated together against the new `'ids'` list format.
- **Fix:** Included `write_results_json()` and `__main__` dual-output logic in the Task 1 GREEN phase implementation, then added dedicated JSON tests in Task 2.
- **Files modified:** precede_ocr.py
- **Verification:** All 60 tests pass including 8 JSON-specific tests
- **Committed in:** 5135c0f (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Minor ordering change. JSON writer implemented alongside CSV in Task 1 rather than separately in Task 2. All planned functionality delivered. No scope creep.

## Issues Encountered
None - plan executed cleanly.

## Known Stubs
None - all functions are fully wired with real data sources.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Data contract finalized: `'ids': list[str]` used throughout pipeline
- `process_single_pdf()` is a self-contained worker function ready for parallelization in Plan 02
- Both output writers (`write_results_csv`, `write_results_json`) handle the multi-ID format
- 60 tests provide comprehensive regression safety for Plan 02 parallelization work

## Self-Check: PASSED

- All 3 modified files exist on disk
- All 3 task commits verified in git log (c176a79, 5135c0f, 9428c13)
- 60/60 tests passing
- SUMMARY.md created at expected path

---
*Phase: 03-scale-parallel-processing*
*Completed: 2026-06-05*
