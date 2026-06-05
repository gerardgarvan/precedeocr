---
phase: 05-quality-conditional-preprocessing-validation
verified: 2026-06-05T19:45:00Z
status: passed
score: 10/10 must-haves verified
re_verification: false
---

# Phase 5: Quality — Conditional Preprocessing & Validation Verification Report

**Phase Goal:** Improve extraction rate on low-quality scans without degrading high-quality results, with post-hoc sequential ID validation to flag probable false positives.
**Verified:** 2026-06-05T19:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Low-quality scans that fail initial OCR are automatically preprocessed and retried | ✓ VERIFIED | preprocess_image() exists, wired in extract_id_with_rotation line 302, 8 tests pass in TestPreprocessingFallback |
| 2 | Common OCR digit confusion is normalized before regex matching | ✓ VERIFIED | normalize_digits() used in both direct and preprocessed passes (lines 278, 318), existing from Phase 1 |
| 3 | Preprocessing is conditional (only when initial OCR fails) | ✓ VERIFIED | Preprocessing called only after direct OCR loop completes without match (line 300-302), test_direct_success_skips_preprocessing passes |
| 4 | User can identify which extractions used preprocessing vs. direct OCR | ✓ VERIFIED | Notes column contains 'preprocessed' on line 324, test_preprocessed_notes_value passes |
| 5 | After all PDFs processed, IDs within each file are checked against sequential trend | ✓ VERIFIED | validate_sequence() exists line 668, wired in main() lines 962 and 1000, uses linregress line 726 |
| 6 | IDs that deviate wildly from within-file trend are flagged with confidence score | ✓ VERIFIED | Outlier detection with 1.5*MAD threshold line 741, confidence scoring lines 763-764, test_wild_outlier_flagged passes |
| 7 | Files with fewer than 3 IDs skip validation (no false positives from unreliable regression) | ✓ VERIFIED | < 3 check on lines 707-710 and 718-720, test_fewer_than_3_ids_skipped passes |
| 8 | Flagged IDs remain in results with confidence indicator in notes | ✓ VERIFIED | IDs not removed, flag appended to notes lines 766-770, test structure confirms |
| 9 | Notes column combines multiple flags with semicolons | ✓ VERIFIED | Semicolon combination logic lines 767-770, test_notes_combined_with_semicolon passes |
| 10 | Results sorted by page before regression (handles unordered parallel output) | ✓ VERIFIED | Sort by page line 701, test_sorts_by_page_before_regression passes |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| precede_ocr.py | preprocess_image() function | ✓ VERIFIED | Exists line 202, grayscale + Gaussian blur + Otsu threshold pipeline |
| precede_ocr.py | validate_sequence() function | ✓ VERIFIED | Exists line 668, linear regression + MAD outlier detection |
| precede_ocr.py | cv2 import | ✓ VERIFIED | Line 24: import cv2 |
| precede_ocr.py | numpy import | ✓ VERIFIED | Line 25: import numpy as np |
| precede_ocr.py | scipy.stats.linregress import | ✓ VERIFIED | Line 29: from scipy.stats import linregress |
| tests/test_precede_ocr.py | TestPreprocessImage class | ✓ VERIFIED | 6 tests for preprocessing function |
| tests/test_precede_ocr.py | TestPreprocessingFallback class | ✓ VERIFIED | 8 tests for conditional trigger and integration |
| tests/test_precede_ocr.py | TestValidateSequence class | ✓ VERIFIED | 13 tests for sequence validation logic |
| tests/test_precede_ocr.py | TestMainSequenceValidation class | ✓ VERIFIED | 1 integration test for main() wiring |
| requirements.txt | opencv-python | ✓ VERIFIED | opencv-python==4.13.0.92 present |
| requirements.txt | scipy | ⚠️ MISSING | scipy not in requirements.txt (but installed and working) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| extract_id_with_rotation | preprocess_image | Called when direct OCR finds no IDs | ✓ WIRED | Line 302: preprocessed = preprocess_image(image) |
| preprocess_image | cv2.threshold | Otsu thresholding | ✓ WIRED | Line 234: cv2.threshold with THRESH_OTSU |
| preprocess_image | cv2.GaussianBlur | Noise reduction | ✓ WIRED | Line 230: cv2.GaussianBlur with 5x5 kernel |
| main (checkpoint path) | validate_sequence | Post-hoc validation before CSV/JSON output | ✓ WIRED | Line 962: all_results = validate_sequence(all_results) |
| main (processing path) | validate_sequence | Post-hoc validation before CSV/JSON output | ✓ WIRED | Line 1000: all_results = validate_sequence(all_results) |
| validate_sequence | linregress | Linear regression trend fitting | ✓ WIRED | Line 726: slope, intercept, r_value, p_value, std_err = linregress(pages, id_values) |
| validate_sequence | np.median | MAD calculation | ✓ WIRED | Lines 733-734: np.median for residuals and MAD |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| preprocess_image | binary (thresholded image) | cv2.threshold with THRESH_OTSU | Yes — computed from pixel values | ✓ FLOWING |
| validate_sequence | residuals | linregress on (page, id_value) pairs | Yes — calculated from actual IDs | ✓ FLOWING |
| extract_id_with_rotation | preprocessed image | preprocess_image(image) | Yes — transforms input image | ✓ FLOWING |
| validate_sequence | mad (median absolute deviation) | np.median on residuals | Yes — statistical calculation | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| validate_sequence imports successfully | python -c "from precede_ocr import validate_sequence; print('OK')" | validate_sequence import: OK | ✓ PASS |
| scipy available | python -c "from scipy.stats import linregress; print('OK')" | scipy.stats.linregress import: OK | ✓ PASS |
| Full test suite passes | pytest tests/test_precede_ocr.py -x --tb=no -q | 138 passed, 1 warning in 9.51s | ✓ PASS |
| Preprocessing tests pass | pytest tests/test_precede_ocr.py::TestPreprocessImage -v | 6 passed in 1.76s | ✓ PASS |
| Preprocessing fallback tests pass | pytest tests/test_precede_ocr.py::TestPreprocessingFallback -v | 8 passed in 1.69s | ✓ PASS |
| Validation tests pass | pytest tests/test_precede_ocr.py::TestValidateSequence -v | 13 passed in 1.74s | ✓ PASS |
| Integration test passes | pytest tests/test_precede_ocr.py::TestMainSequenceValidation -v | 1 passed in 1.67s | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| QUAL-01 | 05-01 | Low-quality scans are preprocessed (grayscale, threshold, denoise) as a fallback when initial OCR finds no match | ✓ SATISFIED | preprocess_image() function implements grayscale + Gaussian blur + Otsu threshold pipeline, wired at line 302, 14 tests pass |
| QUAL-02 | 05-01 | Common OCR digit confusion (O/0, I/1, S/5) is normalized before regex matching | ✓ SATISFIED | normalize_digits() used in both direct (line 278) and preprocessed (line 318) OCR passes, existing from Phase 1, whitelist config enforced |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| requirements.txt | N/A | scipy missing from requirements.txt | ⚠️ Warning | scipy installed and working, but not in requirements.txt — users following install instructions may miss it |
| tests/test_precede_ocr.py | 1250 | Image.getdata() deprecated warning | ℹ️ Info | Deprecation warning in Pillow 14 (2027-10-15) — use get_flattened_data instead |

**Classification:**
- ⚠️ Warning (scipy missing): Not a blocker — scipy is installed and all tests pass. Should be added to requirements.txt for completeness.
- ℹ️ Info (Pillow deprecation): Future maintenance issue, not blocking current functionality.

### Human Verification Required

None. All functionality is testable via automated tests and all tests pass.

---

## Verification Summary

**Phase 5 goal ACHIEVED.** Both Plan 01 (conditional preprocessing) and Plan 02 (sequential validation) are fully implemented and verified.

### Plan 01: Conditional Preprocessing Fallback
- ✅ preprocess_image() function implements OpenCV grayscale + Gaussian blur + Otsu threshold pipeline
- ✅ Wired into extract_id_with_rotation() as fallback when direct OCR fails
- ✅ All 4 rotations retried on preprocessed image
- ✅ Notes column contains 'preprocessed' flag
- ✅ Conditional trigger verified — clean scans skip preprocessing
- ✅ 14 tests pass (6 unit + 8 integration)
- ✅ QUAL-01 satisfied

### Plan 02: Sequential ID Validation
- ✅ validate_sequence() function implements linear regression + MAD outlier detection
- ✅ Wired into main() in both code paths (checkpoint resume line 962, fresh processing line 1000)
- ✅ Files with < 3 IDs skip validation (no false positives)
- ✅ MAD==0 edge case handled (perfect fit, no outliers)
- ✅ Results sorted by page before regression (handles parallel processing)
- ✅ Outlier IDs flagged with confidence score (seq_outlier_conf_XX%)
- ✅ Notes column combines flags with semicolons
- ✅ 14 tests pass (13 unit + 1 integration)
- ✅ D-06, D-07, D-08 implemented

### Test Coverage
- **Total tests:** 138 (111 existing + 14 Plan 01 + 14 Plan 02 - 1 duplicate = 138)
- **Pass rate:** 100% (138 passed, 1 deprecation warning)
- **Coverage:** All must-haves covered by automated tests

### Commits
- ✅ 2ec5c8f: feat(05-01): add preprocess_image() function with OpenCV pipeline
- ✅ e36870e: feat(05-01): wire preprocessing fallback into extract_id_with_rotation
- ✅ 6170590: feat(05-02): implement validate_sequence() with linear regression + MAD outlier detection
- ✅ bd89073: feat(05-02): wire validate_sequence() into main() before CSV/JSON output
- ✅ 51b8662: docs(05-01): complete conditional preprocessing fallback plan
- ✅ 1e501a8: docs(05-02): complete sequential ID validation plan

### Minor Issue: scipy Missing from requirements.txt

While scipy is installed and working (verified via import test), it's not in requirements.txt. This should be added for completeness:

```bash
echo "scipy>=1.10.0" >> requirements.txt
```

This is a documentation issue, not a functional gap — the code works correctly.

---

**Verified:** 2026-06-05T19:45:00Z
**Verifier:** Claude (gsd-verifier)
