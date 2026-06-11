---
phase: 16-multi-id-cleanup-validation
plan: 00
subsystem: testing
tags: [wave-0, test-stubs, nyquist, fixtures]
dependency_graph:
  requires: []
  provides:
    - TestCleanMultiIds test class with 7 stubs
    - sample_multi_id_csv fixture
  affects:
    - tests/test_precede_ocr.py
    - tests/conftest.py
tech_stack:
  added: []
  patterns:
    - pytest fixture pattern for multi-ID test data
    - try/except import pattern for not-yet-implemented functions
    - SystemExit detection for stub functions
key_files:
  created:
    - ".planning/phases/16-multi-id-cleanup-validation/16-00-SUMMARY.md"
  modified:
    - "tests/conftest.py"
    - "tests/test_precede_ocr.py"
decisions:
  - id: "D-01"
    summary: "Use SystemExit detection pattern for stub cmd_clean_multi_ids"
    rationale: "cmd_clean_multi_ids exists as stub from Phase 13 (exits with code 1), not None like helper functions"
  - id: "D-02"
    summary: "All 7 tests SKIP in Wave 0 as expected RED state"
    rationale: "Nyquist compliance - tests exist before implementation"
metrics:
  duration_minutes: 3
  files_modified: 2
  tests_added: 7
  tests_passing: 259
  tests_skipped: 7
  loc_added: 209
completed_at: "2026-06-11T01:47:50Z"
---

# Phase 16 Plan 00: Multi-ID Cleanup Test Stubs Summary

**One-liner:** Created Wave 0 test stubs and fixtures for clean-multi-ids feature following Nyquist pattern - all 7 tests SKIP awaiting Wave 1 implementation.

---

## Execution Report

**Plan:** 16-00-PLAN.md (Wave 0 - Test Infrastructure)
**Status:** ✅ Complete
**Duration:** ~3 minutes
**Tasks completed:** 1/1

### What Was Built

Created test infrastructure for Phase 16 clean-multi-ids feature:

1. **Fixture:** `sample_multi_id_csv` in tests/conftest.py
   - 8 test rows covering multi-ID pages, exact duplicates, repeated-digit patterns, and seq_outlier flags
   - Follows existing fixture pattern (temp_dir dependency, CSV write, return path)

2. **Test stubs:** TestCleanMultiIds class with 7 test methods
   - `test_same_page_duplicate_detection` - validates keep='first' deduplication (MULTI-01)
   - `test_repeated_digit_detection` - flags 11111, 00000 as artifacts (MULTI-01)
   - `test_parse_outlier_confidence` - extracts confidence from seq_outlier_conf_N% notes (MULTI-01)
   - `test_conservative_dedup_preserves_first` - validates conservative dedup with 3x duplicates (MULTI-02)
   - `test_clean_preserves_input_csv` - verifies raw data never modified (MULTI-02, D-07)
   - `test_cmd_clean_multi_ids` - validates cleaned CSV has fewer rows than input (MULTI-03)
   - `test_clean_outputs_three_files` - verifies 3 output files with required columns (MULTI-03, D-06)

3. **Import guards:** try/except imports for 5 not-yet-implemented functions
   - detect_same_page_duplicates, detect_repeated_digit_ids, extract_outlier_confidence, generate_cleanup_report, cmd_clean_multi_ids
   - Helper functions are None → direct pytest.skip
   - cmd_clean_multi_ids exists as stub → SystemExit detection pattern

### Test Results

```
tests/test_precede_ocr.py::TestCleanMultiIds::test_same_page_duplicate_detection SKIPPED
tests/test_precede_ocr.py::TestCleanMultiIds::test_repeated_digit_detection SKIPPED
tests/test_precede_ocr.py::TestCleanMultiIds::test_parse_outlier_confidence SKIPPED
tests/test_precede_ocr.py::TestCleanMultiIds::test_conservative_dedup_preserves_first SKIPPED
tests/test_precede_ocr.py::TestCleanMultiIds::test_clean_preserves_input_csv SKIPPED
tests/test_precede_ocr.py::TestCleanMultiIds::test_cmd_clean_multi_ids SKIPPED
tests/test_precede_ocr.py::TestCleanMultiIds::test_clean_outputs_three_files SKIPPED

======================= 259 passed, 7 skipped in 10.60s =======================
```

**Status:** All tests SKIP as expected (RED state for Wave 0). No regressions - existing 259 tests pass.

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] SystemExit detection for stub functions**
- **Found during:** Task 1 test execution
- **Issue:** Tests for cmd_clean_multi_ids failed with SystemExit instead of skipping. cmd_clean_multi_ids exists as stub (from Phase 13) that exits with code 1, not None like helper functions.
- **Fix:** Wrapped cmd_clean_multi_ids calls in try/except SystemExit, check exit code == 1 to detect stub, then pytest.skip
- **Files modified:** tests/test_precede_ocr.py (3 test methods)
- **Commit:** f9c33fb (same commit - discovered during initial test run)

---

## Requirements Validated

- ✅ **MULTI-01:** Test stubs cover same-page dedup, repeated-digit detection, seq_outlier parsing (3 tests)
- ✅ **MULTI-02:** Test stubs cover conservative dedup and raw data preservation (2 tests)
- ✅ **MULTI-03:** Test stubs cover CLI integration and 3-file output (2 tests)

**Wave 0 Success Criteria Met:**
- [x] 7 test stubs exist in TestCleanMultiIds class
- [x] sample_multi_id_csv fixture exists in conftest.py
- [x] All stubs SKIP because production functions not yet importable
- [x] All 259 existing tests still pass
- [x] VALIDATION.md Wave 0 requirements satisfied

---

## Decisions Made

**D-01: SystemExit detection pattern for stub cmd_clean_multi_ids**
- cmd_clean_multi_ids exists as stub (Phase 13) that calls sys.exit(1)
- Unlike helper functions (None until implemented), cmd_clean_multi_ids is importable
- Solution: try/except SystemExit, check exit code == 1, then pytest.skip("is stub")
- Pattern handles transition from stub to implementation cleanly

---

## Known Stubs

None - this plan creates test stubs for Wave 1 implementation. Production stubs exist in precede_ocr.py but are out of scope for this plan.

---

## Files Modified

### tests/conftest.py
- **Change:** Added sample_multi_id_csv fixture (14 lines)
- **Purpose:** Provide multi-ID test data with duplicates, repeated-digit patterns, seq_outlier flags
- **Pattern:** Follows existing sample_investigate_csv pattern

### tests/test_precede_ocr.py
- **Change:** Added Phase 16 imports block (26 lines) + TestCleanMultiIds class (169 lines)
- **Purpose:** Test stubs for all clean-multi-ids functionality
- **Pattern:** Follows existing TestCmdLookup/TestInvestigateCommand patterns

---

## Commit Log

**f9c33fb** - test(16-00): add Wave 0 test stubs for clean-multi-ids feature

- Add sample_multi_id_csv fixture with multi-ID pages, duplicates, and noise patterns
- Add TestCleanMultiIds class with 7 test stubs
- Add try/except imports for detect_same_page_duplicates, detect_repeated_digit_ids, extract_outlier_confidence, generate_cleanup_report, cmd_clean_multi_ids
- All 7 tests SKIP (functions not yet implemented) - expected RED state for Wave 0
- Existing 259 tests still pass (no regressions)

---

## Next Steps

**Wave 1 (16-01-PLAN.md):** Implement production functions to make all 7 tests GREEN
- detect_same_page_duplicates() - pandas groupby dedup logic
- detect_repeated_digit_ids() - regex pattern matching
- extract_outlier_confidence() - parse seq_outlier_conf_N% from notes
- generate_cleanup_report() - markdown report generation
- cmd_clean_multi_ids() - replace stub with full implementation

**Blocked by:** None (Wave 0 complete)

---

## Self-Check: PASSED

**Created files verified:**
```
✅ .planning/phases/16-multi-id-cleanup-validation/16-00-SUMMARY.md (this file)
```

**Modified files verified:**
```
✅ tests/conftest.py - sample_multi_id_csv fixture exists
✅ tests/test_precede_ocr.py - TestCleanMultiIds class exists with 7 methods
```

**Commits verified:**
```
✅ f9c33fb - test(16-00): add Wave 0 test stubs for clean-multi-ids feature
```

**Test results verified:**
```
✅ 7 tests SKIP (expected Wave 0 state)
✅ 259 tests PASS (no regressions)
```

All claims verified. Self-check PASSED.

---

*Summary created: 2026-06-11*
*Phase: 16-multi-id-cleanup-validation*
*Plan: 00 (Wave 0 - Test Stubs)*
