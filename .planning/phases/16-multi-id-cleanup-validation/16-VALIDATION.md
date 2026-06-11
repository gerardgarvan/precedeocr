---
phase: 16
slug: multi-id-cleanup-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — 259 tests passing) |
| **Config file** | tests/conftest.py (existing fixtures) |
| **Quick run command** | `pytest tests/test_precede_ocr.py::test_cmd_clean_multi_ids -x` |
| **Full suite command** | `pytest tests/test_precede_ocr.py -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py::test_cmd_clean_multi_ids -x`
- **After every plan wave:** Run `pytest tests/test_precede_ocr.py -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 0 | MULTI-01 | unit | `pytest tests/test_precede_ocr.py::test_same_page_duplicate_detection -x` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 0 | MULTI-01 | unit | `pytest tests/test_precede_ocr.py::test_repeated_digit_detection -x` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 0 | MULTI-01 | unit | `pytest tests/test_precede_ocr.py::test_parse_outlier_confidence -x` | ❌ W0 | ⬜ pending |
| 16-01-04 | 01 | 0 | MULTI-02 | unit | `pytest tests/test_precede_ocr.py::test_conservative_dedup_preserves_first -x` | ❌ W0 | ⬜ pending |
| 16-01-05 | 01 | 0 | MULTI-02 | integration | `pytest tests/test_precede_ocr.py::test_clean_preserves_input_csv -x` | ❌ W0 | ⬜ pending |
| 16-01-06 | 01 | 0 | MULTI-03 | integration | `pytest tests/test_precede_ocr.py::test_cmd_clean_multi_ids -x` | ❌ W0 | ⬜ pending |
| 16-01-07 | 01 | 0 | MULTI-03 | integration | `pytest tests/test_precede_ocr.py::test_clean_outputs_three_files -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::test_same_page_duplicate_detection` — stubs for MULTI-01 same-page dedup
- [ ] `tests/test_precede_ocr.py::test_repeated_digit_detection` — stubs for MULTI-01 repeated-digit patterns
- [ ] `tests/test_precede_ocr.py::test_parse_outlier_confidence` — stubs for MULTI-01 seq_outlier parsing
- [ ] `tests/test_precede_ocr.py::test_conservative_dedup_preserves_first` — stubs for MULTI-02 keep='first'
- [ ] `tests/test_precede_ocr.py::test_clean_preserves_input_csv` — stubs for MULTI-02 raw data preservation
- [ ] `tests/test_precede_ocr.py::test_cmd_clean_multi_ids` — stubs for MULTI-03 CLI integration
- [ ] `tests/test_precede_ocr.py::test_clean_outputs_three_files` — stubs for MULTI-03 output files
- [ ] `tests/conftest.py::sample_multi_id_csv` — fixture for multi-ID test data (shared across tests)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 200-ID sample validation prompt | MULTI-03 SC-2 | Interactive terminal input (input() prompt) | Run `python precede_ocr.py clean-multi-ids results.csv`, verify sample summary displays, type 'y' to approve |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
