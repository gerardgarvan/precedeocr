---
phase: 11
slug: advanced-config-tuning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-08
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pytest.ini` — defines testpaths, file patterns |
| **Quick run command** | `pytest tests/test_precede_ocr.py -x` |
| **Full suite command** | `pytest tests/` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_precede_ocr.py -x`
- **After every plan wave:** Run `pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | TESS-02, TESS-03, TESS-04 | integration | `python benchmark.py <corpus> --baseline-csv <phase10.csv>` | ✅ benchmark.py (extend) | ⬜ pending |
| 11-02-01 | 02 | 2 | QUAL-01 | integration | `python benchmark.py <corpus> --baseline-csv <phase10.csv>` | ✅ benchmark.py (extend) | ⬜ pending |
| 11-02-02 | 02 | 2 | QUAL-02 | manual | Human review of `benchmark_results.md` | ❌ W0 creates | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `benchmark.py::benchmark_tesseract_config()` — function to test OEM/PSM/dict configs independently and in combination
- [ ] `benchmark.py::process_pdf_with_config()` — helper to run OCR with custom config string
- [ ] `benchmark.py::validate_accuracy_vs_baseline()` — page-by-page accuracy comparison against Phase 10 baseline CSV
- [ ] `.planning/phases/11-advanced-config-tuning/benchmark_results.md` — Phase 11 results documentation template

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Benchmark results documented with before/after speed comparisons | QUAL-02 | Requires human review of documentation quality and completeness | Review `benchmark_results.md` for complete timing tables, accuracy comparisons, and config recommendations |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
