---
phase: 13
slug: cli-subcommand-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pytest.ini (testpaths=tests, python_files=test_*.py) |
| **Quick run command** | `pytest tests/test_precede_ocr.py -x` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py -x`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | LOOK-03 | integration | `python precede_ocr.py lookup --help` | ✅ precede_ocr.py | ⬜ pending |
| 13-01-02 | 01 | 1 | N/A (refactor) | unit + integration | `pytest tests/ -v` | ✅ tests/test_precede_ocr.py | ⬜ pending |
| 13-01-03 | 01 | 1 | N/A (refactor) | unit | `pytest tests/test_precede_ocr.py::TestEndToEndIntegration::test_main_writes_batch_stats_json -v` | ✅ tests/test_precede_ocr.py | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. 236 existing tests validate that `main()` remains functional and importable. No new test stubs needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `--help` shows 4 subcommands | LOOK-03 | CLI output formatting | Run `python precede_ocr.py --help` and verify scan, lookup, investigate, clean-multi-ids listed |
| `scan` produces identical output | Phase success criteria #1 | End-to-end output comparison | Run `python precede_ocr.py scan <test-dir>` and compare output to v1.2 baseline |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
