---
phase: 05-quality-conditional-preprocessing-validation
verified: 2026-06-05T22:00:00Z
status: passed
score: 7/7 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 10/10
  gaps_closed:
    - "OLS linregress replaced with Theil-Sen robust regression (theilslopes)"
    - "Confidence scoring corrected: higher residual = higher confidence of being outlier"
    - "Duplicate flag bug fixed via collect-then-append pattern"
    - "Normal sequential IDs no longer falsely flagged by extreme outlier pull"
  gaps_remaining: []
  regressions: []
---

# Phase 5: Quality -- Conditional Preprocessing & Validation Verification Report

**Phase Goal:** Improve extraction rate on low-quality scans without degrading high-quality results, with post-hoc sequential ID validation to flag probable false positives.
**Verified:** 2026-06-05T22:00:00Z
**Status:** passed
**Re-verification:** Yes -- after gap closure plan 05-03 (Theil-Sen robust regression replacing OLS linregress)

## Goal Achievement

### Observable Truths

The must-haves below combine the phase-level success criteria (from ROADMAP.md) with the gap closure truths (from 05-03-PLAN.md). Previously-passed items received quick regression checks; gap closure items received full 3-level verification.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Low-quality scans that fail initial OCR are automatically preprocessed and retried | VERIFIED | `preprocess_image()` at line 202, called at line 302 in `extract_id_with_rotation()`, 8 tests pass in TestPreprocessingFallback |
| 2 | Common OCR digit confusion is normalized before regex matching | VERIFIED | `normalize_digits()` used in both direct (line 289) and preprocessed (line 318) OCR passes, 11 tests in TestNormalizeDigits |
| 3 | Preprocessing is conditional (only when initial OCR fails) | VERIFIED | Preprocessing called only after direct OCR loop completes without match (lines 300-302), `test_direct_success_skips_preprocessing` passes |
| 4 | User can identify which extractions used preprocessing vs. direct OCR | VERIFIED | Notes column contains `'preprocessed'` on line 324, `test_preprocessed_notes_value` passes |
| 5 | True outliers are flagged with seq_outlier_conf_XX% and normal IDs receive NO flags (Theil-Sen) | VERIFIED | `theilslopes` at line 766, `test_outlier_not_pulled_by_extreme` passes (UAT scenario: only page 3 flagged), `test_wild_outlier_flagged` asserts normal IDs NOT flagged |
| 6 | Confidence percentage reflects outlier severity (higher % = more likely outlier) | VERIFIED | Formula `min(100, int(residual / threshold * 100))` at line 802, `test_outlier_confidence_is_high` asserts confidence > 50% for extreme outlier |
| 7 | Duplicate flags never occur on multi-ID pages | VERIFIED | Collect-then-append pattern at lines 812-825, `test_no_duplicate_flags_multi_id_page` asserts count <= 1 |

**Score:** 7/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `precede_ocr.py` | `preprocess_image()` function | VERIFIED | Exists line 202, grayscale + Gaussian blur + Otsu threshold pipeline |
| `precede_ocr.py` | `validate_sequence()` using Theil-Sen | VERIFIED | Exists line 668, `theilslopes` at line 766, dual-path detection (modified Z-score for n<5, Theil-Sen for n>=5) |
| `precede_ocr.py` | `from scipy.stats import theilslopes` | VERIFIED | Line 29 -- linregress fully removed (grep confirms zero matches) |
| `precede_ocr.py` | `import cv2` and `import numpy as np` | VERIFIED | Lines 24-25 |
| `tests/test_precede_ocr.py` | `test_outlier_not_pulled_by_extreme` | VERIFIED | Line 1597, simulates UAT scenario with 10 IDs and 1 extreme outlier |
| `tests/test_precede_ocr.py` | `test_outlier_confidence_is_high` | VERIFIED | Line 1620, asserts confidence > 50% |
| `tests/test_precede_ocr.py` | `test_no_duplicate_flags_multi_id_page` | VERIFIED | Line 1638, asserts count <= 1 |
| `tests/test_precede_ocr.py` | TestPreprocessImage class (6 tests) | VERIFIED | Line 1233 |
| `tests/test_precede_ocr.py` | TestPreprocessingFallback class (8 tests) | VERIFIED | Line 1277 |
| `tests/test_precede_ocr.py` | TestValidateSequence class (16 tests) | VERIFIED | Line 1404 |
| `tests/test_precede_ocr.py` | TestMainSequenceValidation class (1 test) | VERIFIED | Line 1655 |
| `requirements.txt` | opencv-python | VERIFIED | `opencv-python==4.13.0.92` present |
| `requirements.txt` | scipy | MISSING | scipy not in requirements.txt (but installed and working) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `extract_id_with_rotation` | `preprocess_image` | Called when direct OCR finds no IDs | WIRED | Line 302: `preprocessed = preprocess_image(image)` |
| `preprocess_image` | `cv2.threshold` | Otsu thresholding | WIRED | Line 234: `cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)` |
| `preprocess_image` | `cv2.GaussianBlur` | Noise reduction | WIRED | Line 230: `cv2.GaussianBlur(gray, (5, 5), 0)` |
| `main (checkpoint path)` | `validate_sequence` | Post-hoc validation before CSV/JSON | WIRED | Line 1017: `all_results = validate_sequence(all_results)` |
| `main (processing path)` | `validate_sequence` | Post-hoc validation before CSV/JSON | WIRED | Line 1055: `all_results = validate_sequence(all_results)` |
| `validate_sequence` | `theilslopes` | Theil-Sen robust regression (n>=5) | WIRED | Line 766: `slope, intercept, _, _ = theilslopes(id_values, pages)` |
| `validate_sequence` | `np.median` | MAD calculation | WIRED | Lines 741, 743, 773-774: `np.median` for deviations, residuals, MAD |
| `validate_sequence` | `outlier_lookup` dict | Collect-then-append flag pattern | WIRED | Lines 795-803 (regression), 752-761 (modified Z-score), applied at lines 812-825 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `preprocess_image` | binary (thresholded image) | `cv2.threshold` with THRESH_OTSU | Yes -- computed from pixel values | FLOWING |
| `validate_sequence` (n>=5) | residuals | `theilslopes` on (page, id_value) pairs | Yes -- calculated from actual IDs | FLOWING |
| `validate_sequence` (n<5) | deviations | Deviation from median of id_values | Yes -- calculated from actual IDs | FLOWING |
| `validate_sequence` | outlier_lookup | Built from residuals/deviations exceeding threshold | Yes -- populated only for true outliers | FLOWING |
| `extract_id_with_rotation` | preprocessed image | `preprocess_image(image)` | Yes -- transforms input image | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| validate_sequence imports successfully | `python -c "from precede_ocr import validate_sequence; print('OK')"` | OK | PASS |
| theilslopes available | `python -c "from scipy.stats import theilslopes; print('OK')"` | OK | PASS |
| linregress fully removed from precede_ocr.py | `grep linregress precede_ocr.py` | No matches | PASS |
| theilslopes used in precede_ocr.py | `grep theilslopes precede_ocr.py` | 3 matches (import, comment, call) | PASS |
| Full test suite passes | `pytest tests/test_precede_ocr.py -x --tb=no -q` | 141 passed, 1 warning in 9.40s | PASS |
| Validation tests pass (16 tests) | `pytest tests/test_precede_ocr.py::TestValidateSequence -v` | 16 passed in 1.82s | PASS |
| Integration test passes | `pytest tests/test_precede_ocr.py::TestMainSequenceValidation -v` | 1 passed in 1.74s | PASS |
| Preprocessing tests pass | `pytest tests/test_precede_ocr.py::TestPreprocessImage -v` | 6 passed (regression check) | PASS |
| Preprocessing fallback tests pass | `pytest tests/test_precede_ocr.py::TestPreprocessingFallback -v` | 8 passed (regression check) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QUAL-01 | 05-01, 05-02, 05-03 | Low-quality scans are preprocessed (grayscale, threshold, denoise) as a fallback when initial OCR finds no match | SATISFIED | `preprocess_image()` implements grayscale + Gaussian blur + Otsu threshold pipeline; `validate_sequence()` uses Theil-Sen robust regression for post-hoc outlier detection; 31 tests pass across preprocessing and validation |
| QUAL-02 | 05-01 | Common OCR digit confusion (O/0, I/1, S/5) is normalized before regex matching | SATISFIED | `normalize_digits()` used in both direct (line 289) and preprocessed (line 318) OCR passes; digit whitelist config `tessedit_char_whitelist=0123456789` enforced in both passes |

**No orphaned requirements.** REQUIREMENTS.md maps QUAL-01 and QUAL-02 to Phase 5; both are claimed by plans and satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `requirements.txt` | N/A | scipy missing from requirements.txt | Warning | scipy is installed and working, but not in requirements.txt -- users following install instructions may miss it |
| `tests/test_precede_ocr.py` | 1250 | `Image.getdata()` deprecation warning | Info | Deprecation warning in Pillow 14 (2027-10-15) -- use `get_flattened_data` instead |

**Classification:**
- Warning (scipy missing): Not a blocker -- scipy is installed and all tests pass. Should be added to requirements.txt for completeness.
- Info (Pillow deprecation): Future maintenance issue, not blocking current functionality.

### Human Verification Required

None. All functionality is testable via automated tests and all 141 tests pass.

---

## Re-Verification: Gap Closure Assessment

### Previous State (Pre-05-03)
The initial verification (now overwritten) reported status: passed with 10/10 truths. However, UAT testing revealed that the validate_sequence() implementation had critical correctness issues:
1. OLS linregress was pulled by extreme outliers, causing false flags on normal IDs
2. Confidence scoring was inverted (0% for worst outliers)
3. Duplicate flags appeared on multi-ID pages

### Gap Closure Plan 05-03 Changes
Plan 05-03 replaced `linregress` with `theilslopes` (Theil-Sen robust regression), added modified Z-score fallback for small samples (n<5), corrected the confidence formula, and implemented the collect-then-append flag pattern.

### Verification of Gap Closure

| Gap | Fixed | Evidence |
|-----|-------|----------|
| OLS pulled by extreme outliers | YES | `theilslopes` at line 766; `test_outlier_not_pulled_by_extreme` passes -- only page 3 flagged in UAT scenario |
| Confidence inverted (0% for outliers) | YES | Formula `min(100, int(residual / threshold * 100))` at line 802; `test_outlier_confidence_is_high` asserts > 50% |
| Duplicate flags on multi-ID pages | YES | Collect-then-append at lines 812-825; `test_no_duplicate_flags_multi_id_page` asserts count <= 1 |
| Normal IDs falsely flagged | YES | `test_wild_outlier_flagged` now asserts normal IDs NOT flagged; all 16 TestValidateSequence tests pass |

### Regressions
None detected. All 141 tests pass including all original tests from Plans 01 and 02.

---

## Verification Summary

**Phase 5 goal ACHIEVED.** All three plans (01: conditional preprocessing, 02: sequential validation, 03: robust regression gap closure) are fully implemented and verified.

### Plan 01: Conditional Preprocessing Fallback
- `preprocess_image()` function implements OpenCV grayscale + Gaussian blur + Otsu threshold pipeline
- Wired into `extract_id_with_rotation()` as fallback when direct OCR fails
- All 4 rotations retried on preprocessed image
- Notes column contains `'preprocessed'` flag
- Conditional trigger verified -- clean scans skip preprocessing
- 14 tests pass (6 unit + 8 integration)
- QUAL-01 satisfied

### Plan 02: Sequential ID Validation
- `validate_sequence()` function implements outlier detection wired into `main()`
- Both code paths (checkpoint resume and fresh processing) call `validate_sequence()`
- Files with < 3 IDs skip validation
- Results sorted by page before analysis
- Notes column combines flags with semicolons
- 13 original tests pass

### Plan 03: Robust Regression Gap Closure
- Theil-Sen `theilslopes` replaces OLS `linregress` (fully removed)
- Modified Z-score fallback for small samples (n < 5) where Theil-Sen breakdown point is exceeded
- Corrected confidence formula: `min(100, int(residual / threshold * 100))`
- Collect-then-append pattern prevents duplicate flags
- MAD==0 with non-zero residuals handled via `max(3 * median_residual, 1.0)` threshold
- 3 new regression tests + 3 updated tests, 16 total TestValidateSequence tests pass
- UAT scenario (IDs 16243-16284 with outlier 89791) correctly flags only the outlier

### Test Coverage
- **Total tests:** 141 (stable from Plan 03 completion)
- **Pass rate:** 100% (141 passed, 1 deprecation warning)
- **Coverage:** All must-haves covered by automated tests

### Minor Issue: scipy Missing from requirements.txt
While scipy is installed and working, it is not listed in requirements.txt. This should be added:
```
scipy>=1.10.0
```
This is a documentation issue, not a functional gap.

---

_Verified: 2026-06-05T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
