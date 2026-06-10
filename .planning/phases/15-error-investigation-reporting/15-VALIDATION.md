---
phase: 15
slug: error-investigation-reporting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pytest.ini (testpaths=tests, python_files=test_*.py) |
| **Quick run command** | `pytest tests/test_precede_ocr.py::TestInvestigateCommand -x` |
| **Full suite command** | `pytest tests/test_precede_ocr.py` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py::TestInvestigateCommand -x`
- **After every plan wave:** Run `pytest tests/test_precede_ocr.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 0 | ERR-01, ERR-02, ERR-03, ERR-04 | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | ERR-01 | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_failed_file_categorization -x` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | ERR-02 | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_blank_page_detection -x` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 2 | ERR-04 | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_markdown_report_generation -x` | ❌ W0 | ⬜ pending |
| 15-01-05 | 01 | 2 | ERR-04 | unit | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_no_match_csv_export -x` | ❌ W0 | ⬜ pending |
| 15-01-06 | 01 | 3 | ALL | integration | `pytest tests/test_precede_ocr.py::TestInvestigateCommand::test_investigate_integration -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::TestInvestigateCommand` — new test class with ~11 tests covering ERR-01 through ERR-04
- [ ] Test fixtures: sample_error_csv, sample_no_match_csv, temp_pdf_with_blank_page
- [ ] Framework install: Already present (pytest 9.0.2) — no action needed

*Existing infrastructure covers framework and conftest; new test class and fixtures required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Report readability | ERR-04 | Subjective formatting quality | Open quality_report.md, verify tables render in markdown viewer |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
