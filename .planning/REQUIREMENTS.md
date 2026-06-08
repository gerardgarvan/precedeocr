# Requirements: Precede OCR v1.2 Performance Optimization

**Milestone:** v1.2 Performance Optimization
**Created:** 2026-06-07
**Goal:** Dramatically reduce total processing time for 30K+ PDF corpus

---

## Active Requirements

### PDF Rendering (RENDER)

- [x] **RENDER-01**: Pipeline uses PyMuPDF instead of pdf2image/Poppler for PDF-to-image conversion
- [x] **RENDER-02**: Pipeline renders at optimal DPI determined by benchmarking (200/250/300 tested for speed vs accuracy)

### Tesseract Tuning (TESS)

- [x] **TESS-01**: OCR uses character whitelist constrained to digits 0-9
- [ ] **TESS-02**: OCR uses OEM 1 (LSTM-only) mode if accuracy maintains >=94% baseline
- [ ] **TESS-03**: OCR uses PSM 7 (single-line) mode if accuracy maintains >=94% baseline
- [ ] **TESS-04**: OCR disables dictionary loading if accuracy maintains >=94% baseline

### Pipeline Optimization (PIPE)

- [x] **PIPE-01**: Worker count is benchmarked and set to optimal value for 20-core hybrid CPU
- [ ] **PIPE-02**: Multi-rotation strategy tries most common rotation first (based on corpus statistics)
- [ ] **PIPE-03**: Pipeline uses conditional DPI fallback (lower DPI first, 300 DPI only on failure)
- [ ] **PIPE-04**: PyMuPDF batch-renders all pages of a PDF before OCR loop

### Quality Gates (QUAL)

- [x] **QUAL-01**: All optimizations maintain >=94% OCR accuracy on test corpus
- [x] **QUAL-02**: Benchmark results documented (before/after speed comparison on representative sample)

---

## Future Requirements

None deferred — all identified optimizations included in this milestone.

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| GPU-accelerated OCR (EasyOCR/PaddleOCR) | CPU-only constraint; Tesseract sufficient for digits |
| Manual CPU affinity for P/E cores | Windows scheduler handles hybrid CPU automatically; manual affinity can decrease performance |
| Tesseract OSD for rotation detection | Unreliable per GitHub #4426; multi-rotation with regex validation proven |
| DPI > 300 | Diminishing returns; can degrade accuracy by oversizing fonts |
| Page-level multiprocessing | IPC overhead too high on Windows; PDF-level parallelism proven |
| Cloud OCR services | No API costs, no internet dependency |
| Resize/downscale before OCR | Counterproductive; render at target DPI directly |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| RENDER-01 | Phase 10 | Complete |
| RENDER-02 | Phase 10 | Complete |
| TESS-01 | Phase 10 | Complete |
| TESS-02 | Phase 11 | Pending |
| TESS-03 | Phase 11 | Pending |
| TESS-04 | Phase 11 | Pending |
| PIPE-01 | Phase 10 | Complete |
| PIPE-02 | Phase 12 | Pending |
| PIPE-03 | Phase 12 | Pending |
| PIPE-04 | Phase 12 | Pending |
| QUAL-01 | Phases 10, 11, 12 | Complete |
| QUAL-02 | Phases 10, 11, 12 | Complete |

**Coverage:** 12/12 requirements mapped (100%)

**Note:** QUAL-01 and QUAL-02 are embedded quality gates that apply to all phases, not separate phases. Each phase must maintain >=94% accuracy and document benchmarks.

---
*Last updated: 2026-06-07*
