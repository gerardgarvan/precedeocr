---
status: complete
phase: 05-quality-conditional-preprocessing-validation
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md
started: 2026-06-05T15:10:00Z
updated: 2026-06-05T15:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test Suite Passes (138 Tests)
expected: Run `pytest tests/test_precede_ocr.py -x` — all 138 tests pass, including 28 new Phase 5 tests covering preprocessing and sequence validation.
result: pass

### 2. OpenCV and Scipy Dependencies Installed
expected: Run `python -c "import cv2; print(cv2.__version__)"` prints 4.13.x and `python -c "from scipy.stats import linregress; print('OK')"` prints OK. Both dependencies added in requirements.txt.
result: pass

### 3. Preprocessing Fallback on a Real PDF
expected: Run the pipeline on a PDF with mixed quality pages. Pages where direct OCR finds no IDs should trigger preprocessing fallback. Check CSV output — pages rescued by preprocessing have 'preprocessed' in the notes column.
result: pass

### 4. Clean Scans Skip Preprocessing
expected: Run on a known clean/clear PDF. IDs are extracted via direct OCR. The notes column for those pages should NOT contain 'preprocessed' — preprocessing is only triggered when direct OCR fails.
result: pass

### 5. Out-of-Sequence IDs Flagged in Output
expected: In the CSV output, if a file has pages with IDs that don't follow the sequential trend (e.g., most IDs are 10001-10009 but one page has 99999), the outlier should have `seq_outlier_conf_XX%` in the notes column.
result: issue
reported: "it appears but doesn't appear to be useful. The flag is applied to every row including perfectly sequential IDs. True outliers (89791, 91895, 82885) get conf_0% while normal sequential IDs get high percentages. Confidence is inverted because regression is pulled toward outliers."
severity: major

### 6. Notes Column Combines Flags Correctly
expected: If a page was both rescued by preprocessing AND flagged as a sequence outlier, the notes column should show both flags separated by a semicolon, e.g., `preprocessed; seq_outlier_conf_23%`.
result: pass

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Out-of-sequence IDs flagged with confidence score; normal sequential IDs not flagged"
  status: failed
  reason: "User reported: sequence validation flags every row (not just outliers), confidence is inverted — true outliers get 0% while sequential IDs get high percentages. Linear regression pulled toward extreme outliers causes inverted residuals."
  severity: major
  test: 5
  root_cause: "Linear regression is not robust to outliers. A single extreme value (e.g., 89791 among 16243-16284) pulls the fit line, making normal IDs have larger residuals than the outlier itself. Additionally, the flag is applied to ALL rows instead of only those exceeding the MAD threshold."
  artifacts:
    - path: "precede_ocr.py"
      issue: "validate_sequence() uses ordinary linear regression (not robust) and flags all rows instead of only outliers"
  missing:
    - "Use robust regression (e.g., median-based Theil-Sen) or iterative outlier removal"
    - "Only append seq_outlier flag to rows that EXCEED the threshold, not all rows"
    - "Invert confidence so outliers get high % and normal IDs get none"
  debug_session: ""
