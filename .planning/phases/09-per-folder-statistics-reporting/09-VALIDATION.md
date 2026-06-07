---
phase: 9
slug: per-folder-statistics-reporting
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pytest.ini |
| **Quick run command** | `python -m pytest tests/test_precede_ocr.py -x` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_precede_ocr.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | STAT-01 | unit | `python -m pytest tests/test_precede_ocr.py::test_tqdm_eta_display -x` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | STAT-02 | unit | `python -m pytest tests/test_precede_ocr.py::test_error_categorization -x` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | STAT-03 | unit | `python -m pytest tests/test_precede_ocr.py::test_folder_stats_aggregation -x` | ❌ W0 | ⬜ pending |
| 09-02-01 | 02 | 2 | STAT-04 | unit | `python -m pytest tests/test_precede_ocr.py::test_campaign_report_generation -x` | ❌ W0 | ⬜ pending |
| 09-02-02 | 02 | 2 | STAT-05 | unit | `python -m pytest tests/test_precede_ocr.py::test_preprocessing_rotation_stats -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::test_tqdm_eta_display` — covers STAT-01 (verify tqdm total= parameter set, ETA displayed)
- [ ] `tests/test_precede_ocr.py::test_error_categorization` — covers STAT-02 (categorize_errors() extracts exception types, print_batch_stats() displays breakdown)
- [ ] `tests/test_precede_ocr.py::test_folder_stats_aggregation` — covers STAT-03 (defaultdict accumulation, handle_view_stats() display)
- [ ] `tests/test_precede_ocr.py::test_campaign_report_generation` — covers STAT-04 (generate_campaign_report() creates Markdown with highlighting)
- [ ] `tests/test_precede_ocr.py::test_preprocessing_rotation_stats` — covers STAT-05 (rotation distribution and preprocessing fallback rate calculation)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| tqdm ETA updates visually during processing | STAT-01 | Visual tqdm progress bar cannot be captured in unit test snapshot | Run `python precede_ocr.py` on small folder, observe ETA countdown in terminal |
| Console output formatting of per-folder table | STAT-03 | Rich text alignment depends on terminal width | Run menu option 3 "View stats" and visually verify table alignment |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
