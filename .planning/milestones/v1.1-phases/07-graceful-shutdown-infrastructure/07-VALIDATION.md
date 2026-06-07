---
phase: 7
slug: graceful-shutdown-infrastructure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pytest.ini |
| **Quick run command** | `pytest tests/test_precede_ocr.py -k shutdown -x` |
| **Full suite command** | `pytest tests/test_precede_ocr.py` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py -k shutdown -x`
- **After every plan wave:** Run `pytest tests/test_precede_ocr.py`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | SHUT-01 | integration | `pytest tests/test_precede_ocr.py::test_graceful_shutdown_completes_current_file -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | SHUT-02 | unit | `pytest tests/test_precede_ocr.py::test_worker_ignores_sigint -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | SHUT-03 | integration | `pytest tests/test_precede_ocr.py::test_pool_cleanup_no_zombies -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | SHUT-04 | unit | `pytest tests/test_precede_ocr.py::test_tqdm_cleanup_on_interrupt -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | SHUT-05 | integration | `pytest tests/test_precede_ocr.py::test_campaign_state_interrupted_on_ctrlc -x` | ❌ W0 | ⬜ pending |
| 07-01-06 | 01 | 1 | D-03/D-04 | integration | `pytest tests/test_precede_ocr.py::test_double_ctrlc_force_quit -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::test_graceful_shutdown_completes_current_file` — stub for SHUT-01
- [ ] `tests/test_precede_ocr.py::test_worker_ignores_sigint` — stub for SHUT-02
- [ ] `tests/test_precede_ocr.py::test_pool_cleanup_no_zombies` — stub for SHUT-03
- [ ] `tests/test_precede_ocr.py::test_tqdm_cleanup_on_interrupt` — stub for SHUT-04
- [ ] `tests/test_precede_ocr.py::test_campaign_state_interrupted_on_ctrlc` — stub for SHUT-05
- [ ] `tests/test_precede_ocr.py::test_double_ctrlc_force_quit` — stub for D-03/D-04
- [ ] `tests/conftest.py` updates — mock signal delivery, temp campaign state fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Terminal displays clean exit message without ANSI corruption | SHUT-04 | Requires visual terminal inspection | 1. Run batch on 10+ PDFs 2. Press Ctrl+C mid-run 3. Verify no garbled ANSI codes in terminal output 4. Verify next command prompt renders correctly |
| No zombie worker processes after Ctrl+C | SHUT-03/SHUT-05 | Requires Task Manager inspection | 1. Run batch on 50+ PDFs 2. Press Ctrl+C 3. Open Task Manager 4. Verify no orphan python.exe processes remain |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
