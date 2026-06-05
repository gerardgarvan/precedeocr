---
status: testing
phase: 05-quality-conditional-preprocessing-validation
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md
started: 2026-06-05T15:10:00Z
updated: 2026-06-05T15:10:00Z
---

## Current Test

number: 1
name: Test Suite Passes (138 Tests)
expected: |
  Run `pytest tests/test_precede_ocr.py -x` and all 138 tests pass with no errors.
  This covers 14 new preprocessing tests (6 preprocess_image + 8 fallback) and 14 new sequence validation tests (13 validate_sequence + 1 integration).
awaiting: user response

## Tests

### 1. Test Suite Passes (138 Tests)
expected: Run `pytest tests/test_precede_ocr.py -x` — all 138 tests pass, including 28 new Phase 5 tests covering preprocessing and sequence validation.
result: [pending]

### 2. OpenCV and Scipy Dependencies Installed
expected: Run `python -c "import cv2; print(cv2.__version__)"` prints 4.13.x and `python -c "from scipy.stats import linregress; print('OK')"` prints OK. Both dependencies added in requirements.txt.
result: [pending]

### 3. Preprocessing Fallback on a Real PDF
expected: Run the pipeline on a PDF with mixed quality pages. Pages where direct OCR finds no IDs should trigger preprocessing fallback. Check CSV output — pages rescued by preprocessing have 'preprocessed' in the notes column.
result: [pending]

### 4. Clean Scans Skip Preprocessing
expected: Run on a known clean/clear PDF. IDs are extracted via direct OCR. The notes column for those pages should NOT contain 'preprocessed' — preprocessing is only triggered when direct OCR fails.
result: [pending]

### 5. Out-of-Sequence IDs Flagged in Output
expected: In the CSV output, if a file has pages with IDs that don't follow the sequential trend (e.g., most IDs are 10001-10009 but one page has 99999), the outlier should have `seq_outlier_conf_XX%` in the notes column.
result: [pending]

### 6. Notes Column Combines Flags Correctly
expected: If a page was both rescued by preprocessing AND flagged as a sequence outlier, the notes column should show both flags separated by a semicolon, e.g., `preprocessed; seq_outlier_conf_23%`.
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps

[none yet]
