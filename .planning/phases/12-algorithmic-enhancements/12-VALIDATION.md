---
phase: 12
slug: algorithmic-enhancements
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-08
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pytest.ini |
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
| 12-01-01 | 01 | 1 | PIPE-02 | unit | `pytest tests/test_precede_ocr.py::test_rotation_reordering -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | PIPE-03 | unit | `pytest tests/test_precede_ocr.py::test_dpi_fallback -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | PIPE-04 | unit | `pytest tests/test_precede_ocr.py::test_batch_render_oom_fallback -x` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 2 | QUAL-01 | benchmark | `python benchmark.py <corpus> --rotation-dist --batch-render --dpi-fallback` | ❌ W0 | ⬜ pending |
| 12-02-02 | 02 | 2 | QUAL-02 | manual | Visual inspection of benchmark_results.md | ✅ Existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py::test_batch_render_oom_fallback` — Mock MemoryError during batch render, verify fallback to page-by-page
- [ ] `tests/test_precede_ocr.py::test_dpi_fallback_logic` — Mock failed DPI 200 OCR, verify DPI 300 retry with correct notes flagging
- [ ] `tests/test_precede_ocr.py::test_rotation_distribution_calculation` — Verify rotation_counts and rotation_pct() logic

*Existing infrastructure covers benchmark framework — only new unit test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Benchmark results documented | QUAL-02 | Output is free-form markdown | Verify benchmark_results.md contains before/after comparison tables |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
