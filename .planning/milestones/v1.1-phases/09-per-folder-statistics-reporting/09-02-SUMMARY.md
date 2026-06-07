---
phase: 09-per-folder-statistics-reporting
plan: 02
subsystem: reporting
tags: [markdown-report, campaign-report, statistics, auto-generation]
dependency_graph:
  requires: [09-01]
  provides: [campaign-report-generation]
  affects: [main-completion-flow, rerun-completion-flow]
tech_stack:
  added: []
  patterns: [markdown-generation, pattern-based-recommendations, folder-stats-computation]
key_files:
  created: []
  modified:
    - path: precede_ocr.py
      changes: [generate_campaign_report, compute_folder_stats_from_results, main-wiring, handle_rerun_failures-wiring]
    - path: tests/test_precede_ocr.py
      changes: [TestCampaignReportGeneration, TestReportGenerationWiring]
decisions:
  - key: Auto-generate report on all completion paths
    rationale: Per D-04, no CLI flag needed. Report generated automatically after every campaign completion (main normal flow, early-exit paths, rerun handler)
  - key: Compute folder_stats from results for early-exit paths
    rationale: process_all_pdfs() populates folder_stats in normal flow, but early-exit paths (all files already processed) need compute_folder_stats_from_results() helper
  - key: Problem folder threshold 80%
    rationale: Per D-05, folders with success rate below 80% are flagged with warning emoji + bold in report
metrics:
  duration_minutes: 6
  completed_at: "2026-06-07T20:09:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
  tests_added: 10
  commits: 2
---

# Phase 09 Plan 02: Markdown Report Generation & Wiring Summary

**One-liner:** Comprehensive campaign_report.md with executive summary, per-folder stats, rotation distribution, problem area highlighting, and pattern-based recommendations, auto-generated on all completion paths.

## What Was Built

Implemented `generate_campaign_report()` function and wired it into all campaign completion paths (main normal flow, early-exit paths, rerun handler) to auto-generate campaign_report.md with:

- Executive summary with campaign-wide metrics (total files, success rate, IDs found, preprocessing fallback rate)
- Error breakdown table categorized by exception type
- Campaign-wide rotation distribution table (90/270/0/180) with percentages
- Per-folder statistics table sorted by success rate ascending (worst first)
- Problem folder highlighting (below 80% success) with warning emoji + bold
- Pattern-based recommendations for high preprocessing fallback and file-level failure rates
- Avg IDs/Page column for each folder
- Per-folder rotation distribution (90/270/0/180 format)

## Tasks Completed

### Task 1: Implement generate_campaign_report() function (TDD)
- **Commit:** 0d8b091
- **Files:** precede_ocr.py, tests/test_precede_ocr.py
- **Changes:**
  - Added `generate_campaign_report()` after `categorize_errors()` (line 877)
  - Generates campaign_report.md with comprehensive markdown formatting
  - Calculates campaign-wide metrics from all_results
  - Builds per-folder statistics table from campaign_state.folder_stats
  - Sorts folder table by success rate ascending (worst first per D-12)
  - Highlights problem folders (below 80%) with warning emoji + bold (D-07)
  - Pattern-based recommendations: high preprocessing → rescan, high failures → verify integrity (D-06)
  - Added 7 tests in TestCampaignReportGeneration class
  - All tests pass (TDD GREEN phase)

### Task 2: Wire generate_campaign_report() into completion paths
- **Commit:** 12106c0
- **Files:** precede_ocr.py, tests/test_precede_ocr.py
- **Changes:**
  - Added `compute_folder_stats_from_results()` helper after `generate_campaign_report()` (line 1072)
  - Wired report generation into main() after `print_batch_stats()` (line 2111)
  - Wired report generation into handle_rerun_failures() after `print_rotation_summary()` (line 1807)
  - Added report generation to menu early-exit path (line 2010)
  - Added report generation to non-menu early-exit path (line 2040)
  - Populated folder_stats for single-file mode (line 2073)
  - Added 3 tests in TestReportGenerationWiring class
  - All tests pass (10 total Phase 9 Plan 02 tests)

## Verification

✓ All 230 tests pass (full test suite)
✓ generate_campaign_report and compute_folder_stats_from_results imports work
✓ main() contains generate_campaign_report call
✓ handle_rerun_failures() contains generate_campaign_report call
✓ Report file created at output_dir/campaign_report.md
✓ Report contains executive summary, rotation distribution, per-folder table, problem areas, recommendations
✓ Problem folders highlighted with warning emoji + bold
✓ Per-folder table sorted by success rate ascending
✓ Avg IDs/Page column present

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All data flows from campaign_state.folder_stats (populated by Plan 01) and all_results.

## Integration Notes

- **Depends on Plan 01:** folder_stats populated by process_all_pdfs() (Plan 01)
- **Depends on categorize_errors():** Error breakdown table uses categorize_errors() from Plan 01
- **Completion flows:** Report generated on:
  1. Normal main() completion after print_batch_stats()
  2. Early-exit paths (menu continue, non-menu checkpoint complete)
  3. Single-file mode completion
  4. handle_rerun_failures() completion after reprocessing failed files
- **D-04 compliance:** No CLI flag needed - auto-generates on every campaign completion

## Self-Check: PASSED

✓ precede_ocr.py modified (581 insertions)
✓ tests/test_precede_ocr.py modified (272 insertions)
✓ Commit 0d8b091 exists (test + feat combined)
✓ Commit 12106c0 exists (wiring)
✓ All 10 Phase 9 Plan 02 tests pass
✓ Full test suite passes (230 tests)

## Output Artifacts

- **precede_ocr.py:** generate_campaign_report() function (line 877-1069)
- **precede_ocr.py:** compute_folder_stats_from_results() helper (line 1072-1131)
- **tests/test_precede_ocr.py:** TestCampaignReportGeneration (7 tests)
- **tests/test_precede_ocr.py:** TestReportGenerationWiring (3 tests)
- **campaign_report.md:** Generated on every campaign completion (not committed, runtime output)

## Next Steps

Phase 09 complete (2/2 plans). Ready for phase transition to Phase 10 or milestone completion.
