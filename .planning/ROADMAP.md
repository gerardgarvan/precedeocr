# Roadmap: Precede OCR

## Milestones

- ✅ **v1.0 MVP** — Phases 1-5 (shipped 2026-06-05)
- ✅ **v1.1 Campaign Runner** — Phases 6-9 (shipped 2026-06-07)
- 🔧 **v1.2 Performance Optimization** — Phases 10-12 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-5) — SHIPPED 2026-06-05</summary>

- [x] Phase 1: Core OCR Pipeline (2/2 plans) — completed 2026-06-03
- [x] Phase 2: Multi-Rotation Strategy (2/2 plans) — completed 2026-06-03
- [x] Phase 3: Batch Processing & Output (2/2 plans) — completed 2026-06-03
- [x] Phase 4: Preprocessing & Error Handling (2/2 plans) — completed 2026-06-04
- [x] Phase 5: Production Hardening (3/3 plans) — completed 2026-06-05

</details>

<details>
<summary>✅ v1.1 Campaign Runner (Phases 6-9) — SHIPPED 2026-06-07</summary>

- [x] Phase 6: Enhanced Campaign State Schema (3/3 plans) — completed 2026-06-06
- [x] Phase 7: Graceful Shutdown Infrastructure (2/2 plans) — completed 2026-06-06
- [x] Phase 8: Interactive Campaign Menu (2/2 plans) — completed 2026-06-07
- [x] Phase 9: Per-Folder Statistics & Reporting (2/2 plans) — completed 2026-06-07

</details>

<details open>
<summary>🔧 v1.2 Performance Optimization (Phases 10-12) — IN PROGRESS</summary>

- [x] **Phase 10: Drop-in Performance Gains** - PyMuPDF swap, Tesseract whitelist, DPI/worker benchmarking
- [x] **Phase 11: Advanced Config Tuning** - Tesseract OEM/PSM/dictionary optimization with corpus validation
- [ ] **Phase 12: Algorithmic Enhancements** - Smart rotation reordering, conditional DPI fallback, batch rendering

</details>

## Phase Details

### Phase 10: Drop-in Performance Gains
**Goal**: Achieve 2-15x speedup through low-risk, high-impact optimizations (PyMuPDF rendering, Tesseract whitelist, optimal DPI/worker tuning)
**Depends on**: v1.1 Campaign Runner (completed)
**Requirements**: RENDER-01, RENDER-02, TESS-01, PIPE-01, QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):
  1. User sees 2-15x faster total processing time on representative 1000-PDF benchmark compared to v1.1 baseline
  2. Pipeline renders PDFs using PyMuPDF instead of pdf2image with no visual quality degradation
  3. OCR accuracy remains >=94% baseline on test corpus with character whitelist enabled
  4. Pipeline uses optimal DPI (200/250/300 tested and fastest chosen) without accuracy drop
  5. Pipeline uses optimal worker count (16-20 tested and most efficient chosen) for 20-core CPU
**Plans:** 3/3 plans complete

Plans:
- [x] 10-01-PLAN.md — PyMuPDF rendering swap + dependency cleanup + test updates
- [x] 10-02-PLAN.md — Benchmark script for DPI, workers, whitelist, and accuracy validation
- [x] 10-03-PLAN.md — Apply benchmark winners and document results

### Phase 11: Advanced Config Tuning
**Goal**: Achieve 1.5-2x incremental speedup through aggressive Tesseract configuration requiring corpus-wide accuracy validation
**Depends on**: Phase 10
**Requirements**: TESS-02, TESS-03, TESS-04, QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):
  1. User sees 1.5-2x faster OCR execution per page compared to Phase 10 baseline
  2. OCR accuracy remains >=94% baseline with OEM 1 (LSTM-only) enabled
  3. OCR accuracy remains >=94% baseline with PSM 7 (single-line) enabled
  4. OCR accuracy remains >=94% baseline with dictionaries disabled, OR dictionary config reverted if accuracy drops
  5. Each Tesseract config change is independently benchmarked for speed and accuracy impact
**Plans:** 2/2 plans complete

Plans:
- [x] 11-01-PLAN.md — Extend benchmark.py with Tesseract config testing (OEM/PSM/dict variants)
- [x] 11-02-PLAN.md — Run benchmarks, apply winning configs, document results

### Phase 12: Algorithmic Enhancements
**Goal**: Achieve 1.2-1.5x incremental speedup through smart algorithmic strategies (rotation reordering, conditional DPI, batch rendering)
**Depends on**: Phase 11
**Requirements**: PIPE-02, PIPE-03, PIPE-04, QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):
  1. User sees 1.2-1.5x faster end-to-end processing compared to Phase 11 baseline
  2. Multi-rotation strategy tries most common rotation first based on v1.1 corpus statistics
  3. Pipeline attempts lower DPI (200) first and re-renders at 300 DPI only on OCR failure, if >70% of corpus succeeds at lower DPI
  4. PyMuPDF batch-renders all pages before OCR loop without causing OOM on largest PDFs in corpus
  5. OCR accuracy remains >=94% baseline with all algorithmic enhancements enabled
**Plans:** 2/3 plans executed

Plans:
- [x] 12-01-PLAN.md — Benchmark infrastructure + unit tests for Phase 12 enhancements
- [x] 12-02-PLAN.md — Implement batch rendering, DPI fallback, and rotation reorder in precede_ocr.py
- [ ] 12-03-PLAN.md — Run benchmarks, validate accuracy, document results

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core OCR Pipeline | v1.0 | 2/2 | Complete | 2026-06-03 |
| 2. Multi-Rotation Strategy | v1.0 | 2/2 | Complete | 2026-06-03 |
| 3. Batch Processing & Output | v1.0 | 2/2 | Complete | 2026-06-03 |
| 4. Preprocessing & Error Handling | v1.0 | 2/2 | Complete | 2026-06-04 |
| 5. Production Hardening | v1.0 | 3/3 | Complete | 2026-06-05 |
| 6. Enhanced Campaign State Schema | v1.1 | 3/3 | Complete | 2026-06-06 |
| 7. Graceful Shutdown Infrastructure | v1.1 | 2/2 | Complete | 2026-06-06 |
| 8. Interactive Campaign Menu | v1.1 | 2/2 | Complete | 2026-06-07 |
| 9. Per-Folder Statistics & Reporting | v1.1 | 2/2 | Complete | 2026-06-07 |
| 10. Drop-in Performance Gains | v1.2 | 3/3 | Complete    | 2026-06-08 |
| 11. Advanced Config Tuning | v1.2 | 2/2 | Complete    | 2026-06-08 |
| 12. Algorithmic Enhancements | v1.2 | 2/3 | In Progress|  |

## Notes (v1.2)

**Stop conditions:**
- After Phase 10: If 2-15x speedup achieves acceptable total runtime (<24 hours for 30K corpus), assess whether Phase 11 ROI justifies complexity
- After Phase 11: If any config drops accuracy below 94%, revert that config. If incremental speedup <1.5x, stop (diminishing returns)
- After Phase 12: If code complexity outweighs speedup (<1.2x incremental), stop. If memory usage causes OOM, revert batch rendering

**Quality gates (embedded in all phases):**
- QUAL-01: Every phase must maintain >=94% OCR accuracy on test corpus
- QUAL-02: Every phase must document before/after speed benchmarks on representative sample

**Research synthesis:**
- Phase 10 targets highest individual speedup factors (PyMuPDF rendering dominates at 2-12x) with lowest risk
- Phase 11 requires A/B testing each Tesseract config for accuracy impact
- Phase 12 adds algorithmic complexity; only proceed if Phases 10+11 insufficient for target throughput

---
*Last updated: 2026-06-08 after Phase 12 planning*
