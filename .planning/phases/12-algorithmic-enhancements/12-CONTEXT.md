# Phase 12: Algorithmic Enhancements - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Achieve 1.2-1.5x incremental speedup through smart algorithmic strategies: validate/reorder rotation priority from corpus statistics, add conditional DPI 300 fallback for failed pages, and batch-render all PDF pages before OCR loop. All must maintain >=94% accuracy. Each enhancement benchmarked independently before applying.

Requirements in scope: PIPE-02, PIPE-03, PIPE-04, QUAL-01, QUAL-02

</domain>

<decisions>
## Implementation Decisions

### Rotation Reordering (PIPE-02)
- **D-01:** Keep current hard-coded order [90, 270, 0, 180] as default. Domain knowledge already places 90 first (IDs are typically ~90 degrees rotated).
- **D-02:** Add rotation distribution report to benchmark.py output on 100-PDF sample. This validates the order via corpus statistics (satisfies success criterion SC2).
- **D-03:** If benchmark data shows a different rotation is most common (e.g., 270 > 90), reorder the array to match data. Still hard-coded, just data-informed. One-line change.

### Conditional DPI Fallback (PIPE-03)
- **D-04:** DPI 300 retry fires ONLY after ALL 8 OCR passes fail at DPI 200 — both direct OCR (4 rotations) and preprocessing fallback (4 rotations) must fail before re-rendering.
- **D-05:** DPI 300 retry does full 8 passes (4 direct + 4 preprocessed rotations). If we're re-rendering anyway, give the page the full treatment.
- **D-06:** Phase 10 benchmark (211/211 IDs at DPI 200 = 100% success) is sufficient proof of the >70% threshold. No formal re-validation needed.
- **D-07:** Flag DPI 300 fallback success in notes column as `dpi_fallback` (or `dpi_fallback+preprocessed` if preprocessing also needed). Consistent with existing `preprocessed` note pattern.
- **D-08:** DPI 300 re-render is page-by-page for individual failed pages only — do NOT re-render the whole PDF at 300. Keep the batch rendering at DPI 200.

### Batch Rendering (PIPE-04)
- **D-09:** Render ALL pages of a PDF into a list of PIL Images upfront before the OCR loop. This separates the rendering phase from the OCR phase.
- **D-10:** On MemoryError, catch and fall back to page-by-page rendering for that specific PDF. Most PDFs in corpus are small (max 1125 KB per Phase 10 stats).
- **D-11:** Log OOM fallback as a warning with filename and page count. Useful for diagnosing memory issues in production.

### Benchmarking & Validation
- **D-12:** Proceed without production validation on full 30K corpus. Build Phase 12 enhancements first, then validate on full corpus. Phase 12 enhancements are low-risk improvements worth having regardless of runtime.
- **D-13:** Benchmark each enhancement independently first (extend benchmark.py), following the established Phases 10-11 methodology. Reuse 100-PDF sample (seed=42).
- **D-14:** Ship any measurable improvement regardless of magnitude. Relaxed from 1.2x roadmap threshold, consistent with Phase 11 D-08. DPI fallback improves accuracy coverage (not just speed). Batch rendering simplifies code flow.

### Claude's Discretion
- Order of benchmarking the three enhancements
- Benchmark output format and reporting details
- How to structure the batch rendering (list of Images vs generator)
- Whether batch rendering benchmark needs accuracy validation or just timing
- How to handle the `doc` (PyMuPDF Document) lifecycle with batch rendering

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline Source
- `precede_ocr.py` — Multi-rotation OCR at line 361 (`extract_id_with_rotation`), rotation order at line 389 (`[90, 270, 0, 180]`), page rendering at line 491-497 (page-by-page loop with `get_pixmap(dpi=200)`), process_single_pdf at line 453
- `benchmark.py` — Existing benchmark infrastructure to extend with rotation distribution, batch rendering, and DPI fallback testing

### Project Artifacts
- `.planning/REQUIREMENTS.md` — PIPE-02, PIPE-03, PIPE-04, QUAL-01, QUAL-02 definitions
- `.planning/ROADMAP.md` — Phase 12 success criteria (5 items) and stop conditions
- `.planning/phases/10-drop-in-performance-gains/10-CONTEXT.md` — Phase 10 decisions (PyMuPDF rendering, DPI 200, hard-coded winners pattern)
- `.planning/phases/11-advanced-config-tuning/11-CONTEXT.md` — Phase 11 decisions (OEM 1, dict-off, ship-any-improvement policy)
- `.planning/phases/10-drop-in-performance-gains/benchmark_results.md` — DPI 200 validation (211/211 IDs, 43% faster than 300)
- `.planning/phases/11-advanced-config-tuning/benchmark_results.md` — Phase 11 benchmark baseline (1067.3 ms/page, OEM 1 + dict-off)

### Test Suite
- `tests/test_precede_ocr.py` — 230 passing tests. Phase 12 changes (batch rendering, DPI fallback) will need new test coverage.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `extract_id_with_rotation()` at `precede_ocr.py:361` — Core OCR function. DPI fallback wraps around this (call at DPI 200, if no result, re-render page at 300 and call again).
- `process_single_pdf()` at `precede_ocr.py:453` — Batch rendering changes happen here. Current loop at lines 491-497 renders one page at a time.
- `benchmark.py` — Full benchmark infrastructure: corpus selection, timing, accuracy validation, comparison tables. Extend with rotation distribution, batch rendering test, and DPI fallback test.
- Rotation distribution tracking at `precede_ocr.py:866-870` — Already computes `rotation_counts` and `rotation_pct()` for campaign reports. Benchmark can reuse this pattern.
- `preprocess_image()` — Existing preprocessing fallback (grayscale + blur + Otsu). DPI fallback is a separate layer above this.

### Established Patterns
- **Hard-coded winners:** Benchmark to find optimal value, then hard-code. No CLI flags. (Phase 10)
- **Ship any improvement:** Even 1.01x is free speed for flag changes. (Phase 11 D-08)
- **100-PDF sample (seed=42):** Consistent benchmark corpus across all phases.
- **Notes column flagging:** `preprocessed` for preprocessing fallback. New: `dpi_fallback`, `dpi_fallback+preprocessed`.
- **Error handling:** try/except with structured error result dicts. MemoryError catch for OOM fallback follows this pattern.

### Integration Points
- Rotation order array at `precede_ocr.py:389` and `:426` — Both locations use `[90, 270, 0, 180]`, must be updated together if reordered
- `process_single_pdf()` at `precede_ocr.py:491-513` — Restructure from page-by-page to batch render + OCR loop
- DPI fallback wraps `extract_id_with_rotation()` call at `precede_ocr.py:500` — needs access to PyMuPDF page object for re-rendering
- `benchmark.py` — Add `benchmark_batch_rendering()`, `benchmark_dpi_fallback()`, and `rotation_distribution()` functions

</code_context>

<specifics>
## Specific Ideas

- User wants to proceed without running full 30K corpus first — build enhancements, then validate in production
- Consistent with Phase 11 ship-any-improvement policy — no minimum speedup threshold
- DPI fallback is as much about accuracy coverage (catching pages that fail at DPI 200) as it is about speed
- Batch rendering OOM fallback should be logged as warning, not silent
- DPI 300 retry re-renders individual failed pages only, not whole PDF — keeps batch rendering benefits

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 12-algorithmic-enhancements*
*Context gathered: 2026-06-08*
