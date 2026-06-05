---
phase: 3
slug: scale-parallel-processing
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-05
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (detected via pytest.ini) |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest tests/ -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | PIPE-06 | unit | `pytest tests/test_precede_ocr.py::test_select_all_valid_ids -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 0 | PIPE-06 | unit | `pytest tests/test_precede_ocr.py::test_extract_id_multiple_matches -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 0 | PIPE-07 | unit | `pytest tests/test_precede_ocr.py::test_csv_output_no_id_pages -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 0 | PIPE-07 | unit | `pytest tests/test_precede_ocr.py::test_json_output_no_id_pages -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 0 | OUT-02 | unit | `pytest tests/test_precede_ocr.py::test_write_results_json_structure -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 0 | Parallel | integration | `pytest tests/test_precede_ocr.py::test_parallel_processing -x` | ❌ W0 | ⬜ pending |
| 03-xx-xx | xx | x | PROG-01 | integration | Manual verification (tqdm output to stderr) | Manual only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::test_select_all_valid_ids` — tests returning all valid IDs (not just first)
- [ ] `tests/test_precede_ocr.py::test_extract_id_multiple_matches` — tests extract_id_with_rotation with multiple IDs on page
- [ ] `tests/test_precede_ocr.py::test_csv_output_no_id_pages` — verifies no-ID pages appear in CSV with blank id column
- [ ] `tests/test_precede_ocr.py::test_json_output_no_id_pages` — verifies no-ID pages show as empty array in JSON
- [ ] `tests/test_precede_ocr.py::test_write_results_json_structure` — validates nested dict structure per D-04
- [ ] `tests/test_precede_ocr.py::test_parallel_processing` — integration test with small batch (3-5 PDFs)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Progress bar displays file count, percentage, ETA | PROG-01 | tqdm writes to stderr; terminal rendering not capturable in unit tests | Run `python precede_ocr.py <test-dir>` with 5+ PDFs, visually confirm: progress bar shows file count/total, percentage, ETA, and rate |
| Inline stats show IDs found, no-ID pages, errors | D-09 | tqdm postfix is terminal-rendered | Run batch processing, visually confirm postfix updates with running counts during execution |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
