---
phase: 8
slug: interactive-campaign-menu
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-06
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pytest.ini` (existing) |
| **Quick run command** | `pytest tests/test_precede_ocr.py::TestMenu -x` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py::TestMenu -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | MENU-01 | unit | `pytest tests/test_precede_ocr.py::TestMenu::test_menu_shown_on_resume -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | MENU-01 | unit | `pytest tests/test_precede_ocr.py::TestMenu::test_input_validation -x` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | MENU-01 | unit | `pytest tests/test_precede_ocr.py::TestMenu::test_keyboard_interrupt -x` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | MENU-02 | unit | `pytest tests/test_precede_ocr.py::TestMenu::test_identify_failed_files -x` | ❌ W0 | ⬜ pending |
| 08-01-05 | 01 | 1 | MENU-02 | unit | `pytest tests/test_precede_ocr.py::TestMenu::test_rerun_removes_old_errors -x` | ❌ W0 | ⬜ pending |
| 08-01-06 | 01 | 1 | MENU-03 | integration | `pytest tests/test_precede_ocr.py::test_export_partial_skips_validation -x` | ❌ W0 | ⬜ pending |
| 08-01-07 | 01 | 1 | MENU-04 | integration | `pytest tests/test_precede_ocr.py::test_fresh_start_clears_state -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::TestMenu` class — test stubs for MENU-01 through MENU-04
- [ ] Integration test fixtures for campaign state + checkpoint mocking
- [ ] monkeypatch/StringIO patterns for multi-input scenarios

*Existing infrastructure covers test framework — pytest 9.0.2 already available, monkeypatch is built-in.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Menu displays correctly in Windows terminal | MENU-01 | Visual formatting, terminal width | Run `python precede_ocr.py test_dir/` with existing checkpoint, verify menu renders without ANSI artifacts |
| Ctrl+C during menu exits cleanly | MENU-01 | Requires real terminal signal | Run pipeline, press Ctrl+C at menu prompt, verify clean exit message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
