---
phase: 10
slug: drop-in-performance-gains
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/conftest.py |
| **Quick run command** | `python -m pytest tests/test_precede_ocr.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_precede_ocr.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | RENDER-01 | unit | `python -m pytest tests/test_precede_ocr.py -k "pymupdf or render" -v` | ❌ W0 | ⬜ pending |
| 10-01-02 | 01 | 1 | RENDER-01 | integration | `python -m pytest tests/test_precede_ocr.py -k "process_single" -v` | ✅ | ⬜ pending |
| 10-02-01 | 02 | 1 | RENDER-02, PIPE-01 | benchmark | `python benchmark.py --sample 100` | ❌ W0 | ⬜ pending |
| 10-02-02 | 02 | 1 | QUAL-01 | accuracy | `python benchmark.py --accuracy` | ❌ W0 | ⬜ pending |
| 10-02-03 | 02 | 1 | QUAL-02 | benchmark | `python benchmark.py --compare` | ❌ W0 | ⬜ pending |
| 10-03-01 | 03 | 2 | TESS-01 | benchmark | `python benchmark.py --whitelist` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_precede_ocr.py` — add PyMuPDF rendering tests (RENDER-01)
- [ ] `benchmark.py` — create benchmark script with DPI/worker/whitelist tests (RENDER-02, PIPE-01, TESS-01, QUAL-01, QUAL-02)
- [ ] `tests/conftest.py` — add fixtures for PyMuPDF mock objects

*Existing test infrastructure (pytest, conftest.py) covers base pipeline tests. New tests needed for PyMuPDF-specific rendering and benchmark validation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual quality of rendered images | RENDER-01 | Subjective visual comparison | Compare PyMuPDF vs pdf2image renders side-by-side on 5 PDFs with varying quality |
| Real-corpus benchmark on 30K+ PDFs | QUAL-02 | Requires full corpus access, long runtime | Run full pipeline on actual corpus directory, compare total time vs v1.1 baseline |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
