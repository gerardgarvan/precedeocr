---
phase: 5
slug: quality-conditional-preprocessing-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | None — defaults work (tests/ directory auto-discovered) |
| **Quick run command** | `pytest tests/test_precede_ocr.py -x` |
| **Full suite command** | `pytest tests/test_precede_ocr.py` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py -x`
- **After every plan wave:** Run `pytest tests/test_precede_ocr.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessImage::test_returns_pil_image -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessImage::test_output_is_grayscale -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessImage::test_output_is_binary -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessImage::test_handles_rgb_input -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessImage::test_handles_grayscale_input -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessImage::test_preserves_dimensions -x` | ❌ W0 | ⬜ pending |
| 05-01-07 | 01 | 1 | QUAL-02 | unit | `pytest tests/test_precede_ocr.py::TestNormalizeDigits -x` | ✅ | ⬜ pending |
| 05-01-08 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessingFallback::test_direct_success_skips_preprocessing -x` | ❌ W0 | ⬜ pending |
| 05-01-09 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessingFallback::test_preprocessing_triggered_on_no_text -x` | ❌ W0 | ⬜ pending |
| 05-01-10 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessingFallback::test_preprocessing_triggered_on_noise_matches -x` | ❌ W0 | ⬜ pending |
| 05-01-11 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessingFallback::test_preprocessing_triggered_on_no_match -x` | ❌ W0 | ⬜ pending |
| 05-01-12 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessingFallback::test_preprocessed_notes_value -x` | ❌ W0 | ⬜ pending |
| 05-01-13 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::TestPreprocessingFallback::test_both_fail_returns_failure_reason -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | D-06 | unit | `pytest tests/test_precede_ocr.py::TestValidateSequence::test_wild_outlier_flagged -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | D-06 | unit | `pytest tests/test_precede_ocr.py::TestValidateSequence::test_fewer_than_3_ids_skipped -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | D-07 | unit | `pytest tests/test_precede_ocr.py::TestValidateSequence::test_notes_combined_with_semicolon -x` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | 2 | D-07 | unit | `pytest tests/test_precede_ocr.py::TestValidateSequence::test_empty_notes_no_semicolons -x` | ❌ W0 | ⬜ pending |
| 05-02-05 | 02 | 2 | D-06 | unit | `pytest tests/test_precede_ocr.py::TestValidateSequence::test_mad_zero_no_outliers -x` | ❌ W0 | ⬜ pending |
| 05-02-06 | 02 | 2 | D-06 | unit | `pytest tests/test_precede_ocr.py::TestValidateSequence::test_sorts_by_page_before_regression -x` | ❌ W0 | ⬜ pending |
| 05-02-07 | 02 | 2 | D-06 | integration | `pytest tests/test_precede_ocr.py::TestMainSequenceValidation::test_main_calls_validate_sequence -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::TestPreprocessImage` — 6 tests for QUAL-01 preprocessing pipeline (Plan 01 Task 1)
- [ ] `tests/test_precede_ocr.py::TestPreprocessingFallback` — 8 tests for conditional preprocessing trigger (Plan 01 Task 2)
- [ ] `tests/test_precede_ocr.py::TestValidateSequence` — 13 tests for D-06/D-07 sequence validation (Plan 02 Task 1)
- [ ] `tests/test_precede_ocr.py::TestMainSequenceValidation` — 1 integration test for main() wiring (Plan 02 Task 2)
- [ ] `pip install opencv-python` — required before preprocessing tests can run
- [ ] `pip install scipy` — required before sequence validation tests can run

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual inspection of preprocessed image quality | QUAL-01 | Subjective quality judgment | Run `--debug` on a known-degraded PDF, inspect preprocessed page output visually |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
