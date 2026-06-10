---
phase: 14
slug: id-lookup-generation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing — 236 tests passing) |
| **Config file** | tests/ directory (existing) |
| **Quick run command** | `python -m pytest tests/test_lookup.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_lookup.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 0 | LOOK-01, LOOK-02 | unit | `python -m pytest tests/test_lookup.py -v` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | LOOK-01 | unit | `python -m pytest tests/test_lookup.py -v` | ❌ W0 | ⬜ pending |
| 14-01-03 | 01 | 1 | LOOK-02 | unit | `python -m pytest tests/test_lookup.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_lookup.py` — test stubs for LOOK-01 (sorting, columns, filtering) and LOOK-02 (Excel compatibility: BOM, quoting, ID-as-text)
- [ ] Shared fixtures for sample scan CSVs (with and without folder_path column)

*Existing test infrastructure (pytest, tests/ directory) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Excel opens lookup CSV correctly | LOOK-02 | Requires Excel application | Open output/lookup.csv in Excel, verify: no encoding errors, IDs show as text not dates, columns aligned |
| Production-scale performance | LOOK-01 | Requires 52K-row production data | Run `python precede_ocr.py lookup output/results.csv`, verify completion and correct row count |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
