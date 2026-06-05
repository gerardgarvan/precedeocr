---
phase: 05-quality-conditional-preprocessing-validation
plan: 03
subsystem: ocr
tags: [scipy, theilslopes, robust-regression, outlier-detection, statistics]

# Dependency graph
requires:
  - phase: 05-02
    provides: "validate_sequence() with linear regression and MAD outlier detection"
provides:
  - "Robust outlier detection in validate_sequence() using Theil-Sen regression"
  - "Modified Z-score fallback for small sample sizes (< 5 IDs)"
  - "Correct confidence scoring (higher % = more likely outlier)"
  - "Duplicate flag prevention on multi-ID pages"
affects: []

# Tech tracking
tech-stack:
  added: [scipy.stats.theilslopes]
  patterns: [Theil-Sen robust regression, modified Z-score outlier detection, dual-path detection by sample size]

key-files:
  created: []
  modified: [precede_ocr.py, tests/test_precede_ocr.py]

key-decisions:
  - "Replaced OLS linregress with Theil-Sen (median of pairwise slopes) for robustness to up to 29% outliers"
  - "Added modified Z-score (Iglewicz & Hoaglin) for samples < 5 where Theil-Sen breakdown point is exceeded"
  - "Inverted confidence formula: higher residual = higher confidence of being outlier (was backwards)"
  - "MAD==0 fallback: use 3x median_residual threshold when Theil-Sen fits majority perfectly"

patterns-established:
  - "Dual-path outlier detection: modified Z-score for n < 5, Theil-Sen regression for n >= 5"
  - "Flag collection pattern: build all flags per row, then join and append once (prevents duplicates)"

requirements-completed: [QUAL-01, QUAL-02]

# Metrics
duration: 10min
completed: 2026-06-05
---

# Phase 05 Plan 03: Robust Sequence Validation Summary

**Theil-Sen robust regression replacing OLS linregress in validate_sequence(), with modified Z-score fallback for small samples and corrected confidence scoring**

## Performance

- **Duration:** 10 min
- **Started:** 2026-06-05T21:05:33Z
- **Completed:** 2026-06-05T21:15:13Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Fixed validate_sequence() to correctly identify only true outliers using Theil-Sen robust regression (immune to extreme value pull)
- Normal sequential IDs no longer receive false outlier flags (UAT regression test confirms)
- Confidence scores now increase with outlier severity (was inverted: 0% for worst outliers)
- Eliminated duplicate flags on multi-ID pages via collect-then-append pattern
- Added modified Z-score fallback for files with < 5 IDs where Theil-Sen breakdown point would be exceeded
- 141 tests passing (3 new + updates to existing), zero regressions

## Task Commits

Each task was committed atomically (TDD flow):

1. **Task 1 RED: Failing tests for Theil-Sen regression** - `51226c2` (test)
2. **Task 1 GREEN: Implement Theil-Sen robust regression** - `4d5a7cb` (feat)

_TDD commits: RED wrote 3 new tests + updated 3 existing tests to assert correct behavior, all failed against broken OLS implementation. GREEN replaced implementation, all 141 tests pass._

## Files Created/Modified
- `precede_ocr.py` - Replaced `from scipy.stats import linregress` with `theilslopes`; rewrote validate_sequence() with dual-path outlier detection, corrected confidence formula, and flag collection pattern
- `tests/test_precede_ocr.py` - Added test_outlier_not_pulled_by_extreme, test_outlier_confidence_is_high, test_no_duplicate_flags_multi_id_page; updated test_wild_outlier_flagged, test_exactly_3_ids_validated, test_main_calls_validate_sequence to assert normal IDs are NOT flagged

## Decisions Made

1. **Theil-Sen over OLS**: Theil-Sen uses median of pairwise slopes, robust to ~29% outliers. OLS (linregress) was pulled by extreme values causing false flags on normal IDs. Direct fix for UAT-reported issue.

2. **Modified Z-score for small samples**: With < 5 data points, a single outlier exceeds Theil-Sen's breakdown point (33% > 29% for n=3). Modified Z-score (0.6745 * deviation / MAD, threshold 3.5) handles this robustly using deviation from median ID values.

3. **MAD==0 fallback threshold**: When Theil-Sen fits the majority perfectly (most residuals cluster at same small value, MAD=0), use `max(3 * median_residual, 1.0)` as threshold. This catches outliers that have huge residuals while majority is well-fit.

4. **Confidence formula inversion**: Changed from `max(0, 100 - residual/threshold*50)` (higher residual = lower confidence, wrong) to `min(100, int(residual/threshold*100))` (higher residual = higher confidence of being outlier, correct).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MAD==0 edge case with Theil-Sen perfect fit**
- **Found during:** Task 1 GREEN phase
- **Issue:** When Theil-Sen fits the sequential majority perfectly (e.g., slope=1.0 for IDs 10001-10005), all non-outlier residuals are 0.0 and MAD=0. The original `if mad == 0: skip` logic missed genuine outliers.
- **Fix:** Added fallback: when MAD==0 and max_residual > 0, use `max(3 * median_residual, 1.0)` as threshold.
- **Files modified:** precede_ocr.py
- **Committed in:** 4d5a7cb

**2. [Rule 1 - Bug] Theil-Sen breakdown with < 5 data points**
- **Found during:** Task 1 GREEN phase
- **Issue:** Theil-Sen has a breakdown point of ~29%. With 3 IDs and 1 outlier (33%), the median of pairwise slopes is pulled by the outlier, producing wrong regression fit.
- **Fix:** Added dual-path detection: for n < 5 IDs, use modified Z-score on raw ID values (deviation from median, MAD-based threshold) instead of regression.
- **Files modified:** precede_ocr.py
- **Committed in:** 4d5a7cb

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness across all sample sizes. The plan's code assumed Theil-Sen would work for all n >= 3, but its breakdown point requires a fallback for very small samples.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 5 (Quality) is now fully complete with all 3 plans executed
- All v1 requirements validated
- 141 tests passing across the entire test suite
- Pipeline ready for production use on the 30K+ PDF corpus

## Self-Check: PASSED

- [x] precede_ocr.py exists
- [x] tests/test_precede_ocr.py exists
- [x] 05-03-SUMMARY.md exists
- [x] Commit 51226c2 (RED) verified
- [x] Commit 4d5a7cb (GREEN) verified
- [x] No stubs found

---
*Phase: 05-quality-conditional-preprocessing-validation*
*Completed: 2026-06-05*
