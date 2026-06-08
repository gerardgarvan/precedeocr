---
phase: 12-algorithmic-enhancements
plan: 01
subsystem: testing-infrastructure
tags: [benchmarking, unit-tests, tdd, phase-12]
dependency_graph:
  requires: [QUAL-01, PIPE-02]
  provides: [benchmark-rotation-dist, benchmark-batch-render, benchmark-dpi-fallback, test-phase-12]
  affects: [benchmark.py, tests/test_precede_ocr.py]
tech_stack:
  added: []
  patterns: [benchmark-methodology, tdd-red-phase, xfail-markers]
key_files:
  created: [.planning/phases/12-algorithmic-enhancements/12-01-SUMMARY.md]
  modified: [benchmark.py, tests/test_precede_ocr.py]
decisions:
  - "Reused Phase 10-11 benchmark methodology (100-PDF sample, seed=42, timing + accuracy validation)"
  - "All 6 tests marked @pytest.mark.xfail for TDD RED phase (Plan 02 will implement production code)"
  - "Benchmark functions self-contained (batch rendering logic is temporary scaffolding for measurement, not production code)"
metrics:
  duration: 272
  tasks_completed: 2
  files_modified: 2
  tests_added: 6
  test_status: "230 passed, 3 xfailed, 3 xpassed"
  completed_at: "2026-06-08T20:43:38Z"
---

# Phase 12 Plan 01: Benchmark Infrastructure and Unit Tests Summary

**One-liner:** Added 3 benchmark functions (rotation distribution, batch rendering, DPI fallback) and 6 unit tests for Phase 12 algorithmic enhancements, following TDD RED phase.

## What Was Built

### 1. Benchmark Functions (benchmark.py)

**`benchmark_rotation_distribution(pdf_paths)`**
- Processes 100-PDF sample at DPI 200, counts rotation_detected values
- Prints markdown table: Rotation | Count | Percentage for angles [90, 270, 0, 180]
- Compares most common rotation to current hard-coded order [90, 270, 0, 180]
- Recommends reordering if data contradicts current order (D-02, D-03)
- Returns Counter object for downstream analysis

**`benchmark_batch_rendering(pdf_paths)`**
- Compares two approaches: (1) Batch render all pages upfront with MemoryError fallback, (2) Page-by-page rendering
- Times each approach separately, computes ms/page, speedup factor
- Verifies ID extraction is identical between approaches (accuracy validation)
- Logs OOM fallback count if MemoryError occurs
- Returns dict with timing results
- Note: Batch rendering logic is temporary scaffolding for measurement (Plan 02 will implement in production code)

**`benchmark_dpi_fallback(pdf_paths)`**
- For each page: tries DPI 200 first, then DPI 300 on failure (per D-04, D-05, D-08)
- Tracks stats: total_pages, success_200, success_300_fallback, total_fail
- Tracks timing: time_200_total, time_300_fallback_total
- Prints summary with success rates and percentages
- Validates D-06 assumption (prints "D-06 VALIDATED" if DPI 200 success rate ≥70%)
- Returns stats dict

**CLI Integration**
- Added `--rotation-dist`, `--batch-render`, `--dpi-fallback` flags to argparse
- Wired execution blocks in `main()` after Phase 11 section
- Added `Counter` import to collections imports

### 2. Unit Tests (tests/test_precede_ocr.py)

**TestPhase12Enhancements class** (6 new tests, all marked @pytest.mark.xfail)

1. **test_batch_render_oom_fallback:** Mocks MemoryError during batch rendering, verifies fallback to page-by-page and logging.warning call
2. **test_batch_render_success:** Verifies batch rendering succeeds with 3 pages, returns 3 results
3. **test_dpi_fallback_triggers_on_total_failure:** Mocks DPI 200 failure, verifies DPI 300 retry and 'dpi_fallback' in notes
4. **test_dpi_fallback_not_triggered_on_success:** Verifies DPI 300 NOT attempted when DPI 200 succeeds (get_pixmap called once)
5. **test_dpi_fallback_notes_preprocessed:** Verifies notes == 'dpi_fallback+preprocessed' when DPI 300 succeeds with preprocessing
6. **test_dpi_fallback_both_fail:** Verifies empty IDs and original failure notes when both DPI 200 and 300 fail

**Helper: `_make_mock_doc(num_pages, pixmap_side_effect)`**
- Creates mock fitz.Document with N pages, supports side_effect dict for per-page behavior

**Test results:** 230 passed, 3 xfailed, 3 xpassed (3 tests unexpectedly pass due to existing code behavior, which is acceptable)

## Deviations from Plan

None. Plan executed exactly as written.

## Implementation Notes

### Benchmark Patterns Followed
- **100-PDF sample (seed=42):** Consistent with Phase 10-11 methodology
- **DPI 200 default:** All benchmarks use DPI 200 per Phase 10 winner
- **Timing + accuracy validation:** Batch rendering verifies IDs match between approaches
- **Markdown tables:** Consistent output format with existing benchmarks
- **Counter for rotation stats:** Reuses pattern from precede_ocr.py line 867

### TDD RED Phase
- All 6 tests will FAIL (marked xfail) until Plan 02 implements production code
- Tests serve as acceptance gates for Plan 02 implementation
- 3 tests unexpectedly PASS (xpassed) due to existing code behavior — this is fine, indicates partial compatibility

### Batch Rendering Benchmark Implementation
- Batch rendering logic implemented locally within `benchmark_batch_rendering()` as self-contained measurement scaffolding
- This is NOT the production implementation (that's Plan 02's job)
- Pattern matches `process_pdf_with_config()` approach (Phase 11 benchmark also implemented Tesseract config testing locally)
- Goal is to answer "is batch rendering faster?" before modifying production code

## Key Files

**Created:**
- `.planning/phases/12-algorithmic-enhancements/12-01-SUMMARY.md` (this file)

**Modified:**
- `benchmark.py` (+305 lines): 3 new benchmark functions, 3 CLI flags, Counter import
- `tests/test_precede_ocr.py` (+205 lines): TestPhase12Enhancements class with 6 tests

## Known Stubs

None. This plan adds benchmarking and testing infrastructure only — no stubs introduced.

## Dependencies

**Requires:**
- QUAL-01: Benchmark infrastructure for accuracy validation
- PIPE-02: Rotation distribution tracking pattern (precede_ocr.py:867-876)

**Provides:**
- `benchmark_rotation_distribution`: Validates rotation order via corpus statistics
- `benchmark_batch_rendering`: Measures batch vs page-by-page timing
- `benchmark_dpi_fallback`: Validates DPI 200→300 fallback coverage
- `TestPhase12Enhancements`: Unit tests for batch rendering, DPI fallback, rotation logic

**Affects:**
- `benchmark.py`: Extended with Phase 12 benchmarks
- `tests/test_precede_ocr.py`: New test class for Phase 12 behaviors

## Metrics

- **Duration:** 272 seconds (4.5 minutes)
- **Tasks completed:** 2/2
- **Files modified:** 2
- **Lines added:** 510 (305 benchmark.py + 205 tests)
- **Tests added:** 6 (all xfail-marked)
- **Test status:** 230 passed, 3 xfailed, 3 xpassed
- **Commits:** 2 (1 per task)

## Verification

**Automated checks (all passing):**
1. `python -c "from benchmark import benchmark_rotation_distribution, benchmark_batch_rendering, benchmark_dpi_fallback; print('OK')"` → OK
2. `python -m pytest tests/test_precede_ocr.py -x` → 230 passed, 3 xfailed, 3 xpassed
3. `python benchmark.py --help` → Shows `--rotation-dist`, `--batch-render`, `--dpi-fallback` flags

**Manual verification (success criteria met):**
- ✓ Three benchmark functions importable from benchmark.py
- ✓ Three CLI flags wired in benchmark.py main()
- ✓ Six unit tests exist in TestPhase12Enhancements, all xfail-marked
- ✓ Existing 230 tests still pass
- ✓ Benchmark functions follow established Phase 10-11 patterns

## Next Steps

**Plan 02: Implement Phase 12 production code**
- Modify `process_single_pdf()` to implement batch rendering with OOM fallback (D-09, D-10, D-11)
- Add DPI 300 fallback layer wrapping `extract_id_with_rotation()` calls (D-04, D-05, D-07, D-08)
- Run `benchmark_rotation_distribution()` on 100-PDF sample to validate rotation order (D-02)
- If data shows different most-common rotation, reorder arrays at lines 389 and 426 (D-03)
- Remove @pytest.mark.xfail from TestPhase12Enhancements tests (transition from RED to GREEN)
- Verify all 6 tests pass with production implementation

**Plan 03: Benchmarking and Validation**
- Run all three Phase 12 benchmarks on 100-PDF sample
- Document results in `12-benchmark-results.md`
- Validate QUAL-01 (≥94% accuracy maintained)
- Measure actual speedup from each enhancement
- Ship any measurable improvement per D-14

## Self-Check: PASSED

**Files exist:**
- ✓ `benchmark.py` contains `def benchmark_rotation_distribution`
- ✓ `benchmark.py` contains `def benchmark_batch_rendering`
- ✓ `benchmark.py` contains `def benchmark_dpi_fallback`
- ✓ `benchmark.py` contains `--rotation-dist`
- ✓ `benchmark.py` contains `--batch-render`
- ✓ `benchmark.py` contains `--dpi-fallback`
- ✓ `benchmark.py` contains `from collections import defaultdict, Counter`
- ✓ `tests/test_precede_ocr.py` contains `class TestPhase12Enhancements`
- ✓ All 6 test methods present and xfail-marked

**Commits exist:**
- ✓ 8195df2: feat(12-01): add Phase 12 benchmark functions and CLI flags
- ✓ 5f42e8a: test(12-01): add Phase 12 unit tests for production code behaviors

**Tests passing:**
- ✓ Full test suite: 230 passed, 3 xfailed, 3 xpassed
- ✓ Imports: All benchmark functions importable
- ✓ CLI: All flags present in --help output
