---
phase: 1
slug: foundation-single-file-ocr-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-04
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.3+ |
| **Config file** | pytest.ini (Wave 0 creates) |
| **Quick run command** | `pytest tests/test_precede_ocr.py -v -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_{module}.py -v -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 0 | PIPE-01 | unit | `pytest tests/test_file_discovery.py::test_single_file -x` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 0 | PIPE-02 | unit | `pytest tests/test_pdf_conversion.py::test_dpi_300 -x` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 0 | PIPE-04 | unit | `pytest tests/test_id_extraction.py::test_regex_match -x` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 0 | PIPE-05 | integration | `pytest tests/test_pipeline.py::test_id_mapping -x` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 0 | OUT-01 | integration | `pytest tests/test_output.py::test_csv_format -x` | ❌ W0 | ⬜ pending |
| 01-01-06 | 01 | 0 | D-04 | unit | `pytest tests/test_rotation.py::test_multi_rotation -x` | ❌ W0 | ⬜ pending |
| 01-01-07 | 01 | 0 | D-06 | integration | `pytest tests/test_output.py::test_all_pages_included -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_pdf_conversion.py` — covers PIPE-02 (DPI validation)
- [ ] `tests/test_id_extraction.py` — covers PIPE-04 (regex + normalization)
- [ ] `tests/test_rotation.py` — covers D-04 (multi-rotation logic, early exit)
- [ ] `tests/test_output.py` — covers OUT-01, D-06, D-07 (CSV format, columns, all pages)
- [ ] `tests/test_pipeline.py` — covers PIPE-05 (end-to-end integration)
- [ ] `pytest.ini` — pytest configuration
- [ ] `tests/conftest.py` — shared fixtures (sample PDF, temp directories)
- [ ] Framework install: `pip install pytest==8.3.5` — if not detected

*Test data requirements:*
- Sample PDF with 3-5 pages containing 5-digit IDs at various rotations
- Sample PDF with 1 page containing no ID (tests D-06 no-match row)
- Sample PDF with page containing multiple 5-digit numbers (tests D-03 selection logic)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual check of OCR accuracy on sample PDF | PIPE-04 | OCR accuracy depends on scan quality; automated tests use synthetic data | Process 1 real PDF with known IDs, compare CSV output against manually counted IDs |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
