---
phase: 15-error-investigation-reporting
plan: 01
subsystem: error-investigation
tags: [cli, error-diagnosis, reporting, tdd]
dependency_graph:
  requires: [14-01]
  provides: [investigate-command]
  affects: [precede_ocr.py, tests]
tech_stack:
  added: []
  patterns: [PIL-histogram-analysis, PyMuPDF-page-rendering, markdown-report-generation]
key_files:
  created: []
  modified:
    - precede_ocr.py
    - tests/test_precede_ocr.py
    - tests/conftest.py
decisions:
  - id: D-01
    summary: Re-render actual pages for no-match diagnosis
    rationale: Cannot rely on metadata alone per CONTEXT.md locked decision
  - id: D-02
    summary: Single OCR pass for diagnosis
    rationale: Full 8-pass pipeline overkill for categorization per CONTEXT.md locked decision
  - id: D-03
    summary: Report only, no modifications to results.csv
    rationale: Investigation is read-only per CONTEXT.md locked decision
  - id: D-04
    summary: Include copy-paste CLI commands in report
    rationale: User can run commands to fix issues per CONTEXT.md locked decision
  - id: D-05
    summary: Read from scan_csv positional argument
    rationale: Consistent with cmd_lookup pattern per CONTEXT.md locked decision
metrics:
  duration_seconds: 308
  tasks_completed: 1
  tests_added: 12
  tests_total: 259
  files_modified: 3
  loc_added: 270
  completed_date: 2026-06-10
---

# Phase 15 Plan 01: Error Investigation & Reporting Summary

**One-liner:** Implemented `investigate` subcommand with error categorization, blank page detection, OCR failure diagnosis, and markdown quality reports.

## What Was Built

Replaced the `cmd_investigate` stub with full implementation for diagnosing the 49 failed files and 59 no-match pages from the production v1.2 run. The investigation re-renders and re-OCRs no-match pages, categorizes failures by type, and produces structured markdown + CSV reports with actionable recommendations and copy-paste CLI commands.

**Key capabilities:**

1. **Failed file investigation (ERR-01):**
   - Categorizes errors by type (FileNotFoundError, EmptyFileError)
   - Re-verifies file existence to detect transient errors
   - Generates recommendations (rescan if file now exists, verify integrity, etc.)

2. **No-match page investigation (ERR-02):**
   - Re-renders pages using PyMuPDF at DPI 200
   - Detects blank pages (white vs black) using PIL histogram analysis
   - Runs single-pass OCR to categorize as: no_text_detected, insufficient_text, or text_no_id_match
   - Handles investigation failures gracefully

3. **Quality reporting (ERR-04):**
   - Markdown report with Summary, Failed Files Analysis, No-Match Pages Analysis sections
   - Category breakdowns with counts
   - Full tabular findings (pandas to_markdown)
   - Copy-paste bash commands for fixable errors (ERR-03)
   - CSV exports: no_match_pages.csv and failed_files.csv

4. **CLI integration:**
   - `python precede_ocr.py investigate results.csv --report output/quality_report.md`
   - Positional scan_csv argument consistent with cmd_lookup pattern
   - Optional --report flag for custom output path

## Implementation Details

### Helper Functions

- **is_blank_page(image, threshold=0.99):** PIL histogram-based blank detection
  - Returns (True, "blank_white") if 99%+ pixels in 250-255 range
  - Returns (True, "blank_black") if 99%+ pixels in 0-5 range
  - Returns (False, "") otherwise

- **investigate_failed_files(df):** Error categorization and re-verification
  - Filters error rows (page=0, notes startswith "error:")
  - Extracts error type via regex pattern from categorize_errors()
  - Re-verifies file existence with pathlib .exists()
  - Generates recommendations based on error type and current state

- **investigate_no_match_pages(df):** Page re-rendering and OCR diagnosis
  - Filters no-match rows (page>0, empty id, no error prefix)
  - Re-renders each page with fitz.open() + page.get_pixmap(dpi=200)
  - Checks is_blank_page() before running OCR
  - Single OCR pass with standard config (no full 8-pass pipeline)
  - Categorizes as blank_white, blank_black, no_text_detected, insufficient_text, text_no_id_match, or investigation_failed

- **generate_investigation_report(failed_df, no_match_df, scan_csv_path):** Markdown generation
  - Header with timestamp and scan CSV path
  - Summary section with counts
  - Failed Files Analysis with error type breakdown + full table + fixable commands
  - No-Match Pages Analysis with category breakdown + full table

### TDD Implementation

**RED phase:**
- Added sample_investigate_csv fixture to conftest.py
- Added TestInvestigateCommand class with 12 tests
- Tests skipped when functions not yet implemented

**GREEN phase:**
- Implemented 4 helper functions + cmd_investigate handler
- Added scan_csv positional argument to investigate subparser
- All 12 new tests passed
- Full regression suite passed (259 tests total)

**No REFACTOR needed** - code is clean and follows existing patterns.

## Testing

**Test coverage:**
- 12 new tests in TestInvestigateCommand class
- 259 total tests passing (247 existing + 12 new)

**Test types:**
- Unit: is_blank_page (white/black/content), investigate_failed_files (categorization/existence), investigate_no_match_pages (categorization/ocr-failure), generate_investigation_report (structure/fixable-commands)
- Integration: cmd_investigate (full workflow with mocked fitz/pytesseract)
- Error handling: missing CSV, invalid columns
- CLI: argparse configuration for scan_csv positional and --report option

**Validation commands:**
- `pytest tests/test_precede_ocr.py::TestInvestigateCommand -x` - Phase 15 tests only
- `pytest tests/test_precede_ocr.py` - Full suite (259 tests)
- `python precede_ocr.py investigate --help` - CLI smoke test

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None - all functionality fully implemented.

## Commits

| Commit | Type | Message |
|--------|------|---------|
| e2d4796 | test | Add failing tests for investigate subcommand |
| 0acc553 | feat | Implement cmd_investigate with error diagnosis and reporting |

## Dependencies

**Upgraded:**
- tabulate: 0.8.10 → 0.10.0 (required by pandas 3.0.3 for to_markdown)

**Note:** This created dependency conflicts with pycanon 1.1.0, but pycanon is not used in this project and the conflicts do not affect functionality.

## Files Changed

| File | Lines Added | Purpose |
|------|-------------|---------|
| precede_ocr.py | +266 | 4 helper functions + cmd_investigate implementation + scan_csv arg |
| tests/test_precede_ocr.py | +226 | TestInvestigateCommand class with 12 tests + imports |
| tests/conftest.py | +12 | sample_investigate_csv fixture |

**Total:** 504 LOC added across 3 files

## Requirements Validated

- ✓ **ERR-01:** User can investigate failed files — verify existence, categorize by error type (FileNotFoundError vs EmptyFileError), identify root causes
- ✓ **ERR-02:** User can investigate no-match pages — determine if blank page, OCR failure, or missing ID label
- ✓ **ERR-03:** Pipeline fixes are applied for fixable errors — report includes copy-paste CLI commands
- ✓ **ERR-04:** User receives a quality report (markdown) documenting all findings, error categories, and recommendations

## Next Steps

- Phase 16: Implement clean-multi-ids subcommand for conservative deduplication of 5,141 multi-ID pages
- Run investigate command on production results.csv to generate quality_report.md
- Review actual error patterns and no-match categories from production data

## Self-Check: PASSED

**Created files exist:** N/A (no new files created, only modifications)

**Modified files exist:**
- FOUND: C:\Users\Owner\Documents\precedeocr\precede_ocr.py
- FOUND: C:\Users\Owner\Documents\precedeocr\tests\test_precede_ocr.py
- FOUND: C:\Users\Owner\Documents\precedeocr\tests\conftest.py

**Commits exist:**
- FOUND: e2d4796 (test commit)
- FOUND: 0acc553 (feat commit)

**Tests pass:**
- PASSED: pytest tests/test_precede_ocr.py::TestInvestigateCommand -x (12 tests)
- PASSED: pytest tests/test_precede_ocr.py (259 tests)

**CLI works:**
- PASSED: python precede_ocr.py investigate --help (shows scan_csv and --report)
