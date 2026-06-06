---
phase: 6
slug: enhanced-campaign-state-schema
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-05
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest tests/test_precede_ocr.py::test_campaign_state -x` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py -x -q`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | STATE-01 | unit | `pytest tests/test_precede_ocr.py::test_save_campaign_state_atomic -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 0 | STATE-01 | unit | `pytest tests/test_precede_ocr.py::test_load_campaign_state -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 0 | STATE-01 | integration | `pytest tests/test_precede_ocr.py::test_silent_upgrade -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 0 | STATE-02 | unit | `pytest tests/test_precede_ocr.py::test_folder_path_injection -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 0 | STATE-02 | unit | `pytest tests/test_precede_ocr.py::test_folder_path_root -x` | ❌ W0 | ⬜ pending |
| 06-01-06 | 01 | 0 | STATE-02 | unit | `pytest tests/test_precede_ocr.py::test_folder_path_windows_case -x` | ❌ W0 | ⬜ pending |
| 06-01-07 | 01 | 0 | STATE-03 | unit | `pytest tests/test_precede_ocr.py::test_interruption_log_schema -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::test_save_campaign_state_atomic` — stubs for STATE-01 atomic writes
- [ ] `tests/test_precede_ocr.py::test_load_campaign_state` — stubs for STATE-01 load/resume
- [ ] `tests/test_precede_ocr.py::test_silent_upgrade` — stubs for STATE-01 v1.0 upgrade (D-05, D-06)
- [ ] `tests/test_precede_ocr.py::test_folder_path_injection` — stubs for STATE-02 folder tracking (D-07)
- [ ] `tests/test_precede_ocr.py::test_folder_path_root` — stubs for STATE-02 root case (D-08)
- [ ] `tests/test_precede_ocr.py::test_folder_path_windows_case` — stubs for STATE-02 normalization (D-09)
- [ ] `tests/test_precede_ocr.py::test_interruption_log_schema` — stubs for STATE-03 schema

*Existing infrastructure covers framework needs — no new framework additions required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Windows path case normalization in real filesystem | STATE-02 | Automated mock cannot fully replicate Windows case-insensitive filesystem | Process PDFs in mixed-case directories, verify single folder_stats key |
| Campaign state survives Task Manager kill | STATE-01 | Requires forceful process termination | Run pipeline, kill via Task Manager, verify campaign_state.json is valid JSON |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
