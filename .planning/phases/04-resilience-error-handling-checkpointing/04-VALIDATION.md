---
phase: 04
slug: resilience-error-handling-checkpointing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none — implicit discovery via tests/ directory |
| **Quick run command** | `pytest tests/test_precede_ocr.py -x` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py -x`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | QUAL-03 | unit | `pytest tests/test_precede_ocr.py::test_wrapper_handles_exception -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 0 | QUAL-03 | unit | `pytest tests/test_precede_ocr.py::test_retry_once_decorator -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | QUAL-03 | unit | `pytest tests/test_precede_ocr.py::test_error_logging -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 0 | RESL-01 | unit | `pytest tests/test_precede_ocr.py::test_checkpoint_save_atomic -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 0 | RESL-01 | unit | `pytest tests/test_precede_ocr.py::test_checkpoint_load -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 0 | RESL-01 | unit | `pytest tests/test_precede_ocr.py::test_filter_remaining_pdfs -x` | ❌ W0 | ⬜ pending |
| 04-01-07 | 01 | 0 | RESL-01 | unit | `pytest tests/test_precede_ocr.py::test_merge_results -x` | ❌ W0 | ⬜ pending |
| 04-01-08 | 01 | 0 | RESL-01 | integration | `pytest tests/test_precede_ocr.py::test_fresh_flag -x` | ❌ W0 | ⬜ pending |
| 04-01-09 | 01 | 0 | RESL-01 | unit | `pytest tests/test_precede_ocr.py::test_checkpoint_path_validation -x` | ❌ W0 | ⬜ pending |
| 04-01-10 | 01 | 0 | RESL-01 | unit | `pytest tests/test_precede_ocr.py::test_corrupt_checkpoint -x` | ❌ W0 | ⬜ pending |
| 04-01-11 | 01 | 0 | D-12/D-13/D-14 | unit | `pytest tests/test_precede_ocr.py::test_batch_stats_calculation -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py` — 11 new test functions covering checkpoint save/load, retry logic, error logging, stats calculation, --fresh flag, corrupt checkpoint handling
- [ ] `tests/conftest.py` — shared fixtures for temp checkpoint files, mock error log paths, simulated crashes (if not already present from Phase 3)

*Existing infrastructure: pytest 9.0.2 installed, tests/test_precede_ocr.py has 70+ tests for Phases 1-3.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interrupt & resume smoke test | RESL-01 | Requires actual process interruption (Ctrl+C) mid-batch | Run batch on 100 files, interrupt after ~50, verify checkpoint exists, re-run, verify only remaining files processed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
