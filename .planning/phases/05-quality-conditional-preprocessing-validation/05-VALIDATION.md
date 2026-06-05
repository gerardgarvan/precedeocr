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
| 05-01-01 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::test_preprocess_image_pipeline -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::test_preprocessing_trigger_no_text -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::test_preprocessing_trigger_noise -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::test_preprocessing_trigger_no_match -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::test_preprocess_output_format -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 1 | QUAL-01 | unit | `pytest tests/test_precede_ocr.py::test_preprocessing_flag_in_notes -x` | ❌ W0 | ⬜ pending |
| 05-01-07 | 01 | 1 | QUAL-02 | unit | `pytest tests/test_precede_ocr.py::TestNormalizeDigits -x` | ✅ | ⬜ pending |
| 05-01-08 | 01 | 1 | QUAL-02 | unit | `pytest tests/test_precede_ocr.py::test_tesseract_digit_whitelist -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | D-06 | unit | `pytest tests/test_precede_ocr.py::test_validate_sequence_outlier_detection -x` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | D-06 | unit | `pytest tests/test_precede_ocr.py::test_validate_sequence_too_few_points -x` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | D-07 | unit | `pytest tests/test_precede_ocr.py::test_sequence_confidence_score_format -x` | ❌ W0 | ⬜ pending |
| 05-02-04 | 02 | 2 | D-07 | unit | `pytest tests/test_precede_ocr.py::test_notes_multiple_flags -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::test_preprocess_image_pipeline` — stubs for QUAL-01 preprocessing
- [ ] `tests/test_precede_ocr.py::test_preprocessing_trigger_*` — stubs for all 3 failure type triggers
- [ ] `tests/test_precede_ocr.py::test_preprocessing_flag_in_notes` — stubs for D-04 notes flag
- [ ] `tests/test_precede_ocr.py::test_tesseract_digit_whitelist` — stubs for QUAL-02 whitelist verification
- [ ] `tests/test_precede_ocr.py::test_validate_sequence_*` — stubs for D-06/D-07 sequence validation
- [ ] `tests/test_precede_ocr.py::test_notes_multiple_flags` — stubs for combined notes
- [ ] `pip install opencv-python` — required before preprocessing tests can run

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
