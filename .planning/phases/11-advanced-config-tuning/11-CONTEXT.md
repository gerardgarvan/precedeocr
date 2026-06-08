# Phase 11: Advanced Config Tuning - Context

**Gathered:** 2026-06-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Achieve 1.5-2x incremental speedup through aggressive Tesseract configuration changes: switch to OEM 1 (LSTM-only), test PSM 7 (single-line), and disable dictionary loading. Each change is independently benchmarked for speed and accuracy, then winning combinations tested. All must maintain >=94% accuracy (soft margin: 93-94% acceptable if speed gain is substantial).

Requirements in scope: TESS-02, TESS-03, TESS-04, QUAL-01, QUAL-02

</domain>

<decisions>
## Implementation Decisions

### Testing Strategy
- **D-01:** Test each config change (OEM 1, PSM 7, dict-off) independently first, then test the winning combination. This catches interaction effects between configs.
- **D-02:** Extend existing `benchmark.py` with a new `benchmark_tesseract_config()` function. Reuse corpus selection, timing, and accuracy validation infrastructure from Phase 10.
- **D-03:** Accuracy baseline is Phase 10's DPI-200 results (the current pipeline state). Regressions measured from HERE, not from v1.1.

### PSM 7 Approach
- **D-04:** Try PSM 7 on full page images first (just swap the flag). If accuracy holds on full pages, no extra complexity. If it drops below threshold, keep PSM 6 — don't attempt region cropping.
- **D-05:** If PSM 7 fails accuracy, do NOT try PSM 13 or other PSM variants. Keep PSM 6 (proven at 94.9%) and move on to dictionary tuning.

### Revert Policy
- **D-06:** Apply any config that individually passes accuracy. Partial wins are shipped. E.g., if OEM 1 passes but PSM 7 fails, apply OEM 1 alone.
- **D-07:** Accuracy threshold has soft margin: 93-94% acceptable if the speed gain is substantial. Report the tradeoff and let user decide. Below 93% is a hard fail.

### Stop Condition
- **D-08:** Ship any improvement regardless of magnitude. Even 1.1x speedup is free speed since configs are just flag changes with zero code complexity cost. The 1.5x roadmap threshold is relaxed.
- **D-09:** Phase 12 gate: after Phase 11 benchmarks, estimate total 30K corpus runtime with Phases 10+11 combined. If under 24 hours, Phase 12 is unnecessary. Only proceed to Phase 12 if still too slow.

### Claude's Discretion
- Order of testing the three configs (which to try first)
- Benchmark output format and reporting details
- How to structure the combination testing (which combos to test)
- Whether to run the full 100-PDF sample or smaller subset for initial screening

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline Source
- `precede_ocr.py` — Tesseract config at lines 397 and 432 (`--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789`). Two locations to update.
- `benchmark.py` — Existing benchmark infrastructure to extend with Tesseract config testing

### Project Artifacts
- `.planning/REQUIREMENTS.md` — TESS-02, TESS-03, TESS-04, QUAL-01, QUAL-02 definitions
- `.planning/ROADMAP.md` — Phase 11 success criteria (5 items)
- `.planning/phases/10-drop-in-performance-gains/10-CONTEXT.md` — Phase 10 decisions (D-05 whitelist, D-06 benchmark approach)
- `.planning/phases/10-drop-in-performance-gains/benchmark_results.md` — Phase 10 benchmark results (DPI 200 baseline)

### Test Suite
- `tests/test_precede_ocr.py` — 230 passing tests. Config changes should not require test modifications unless OCR behavior changes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `benchmark.py` — Full benchmark infrastructure: corpus selection (`select_benchmark_corpus`), per-PDF processing (`run_single_pdf_at_dpi`), timing, comparison tables. Extend with Tesseract config variants.
- `extract_id_with_rotation()` — Core OCR function at `precede_ocr.py`. Config string is built inline at lines 397 and 432. Both locations use identical config.
- `benchmark_results.md` — Phase 10 results document provides template for Phase 11 documentation.

### Established Patterns
- **Config string is inline:** Tesseract config built as string literal at two locations in `extract_id_with_rotation()`. Both must be updated together.
- **Benchmark methodology:** 100-PDF random sample (seed=42), `time.perf_counter()` timing, comparison tables, accuracy validation via page-by-page ID comparison.
- **Hard-coded winners:** Phase 10 pattern — benchmark to find optimal value, then hard-code it. No CLI flags for config variants.

### Integration Points
- Tesseract config strings at `precede_ocr.py:397` and `precede_ocr.py:432` — change OEM, PSM, and/or add dictionary flags
- `benchmark.py` — add `benchmark_tesseract_config()` function
- `.planning/phases/11-advanced-config-tuning/benchmark_results.md` — document Phase 11 results

</code_context>

<specifics>
## Specific Ideas

- User wants to reuse Phase 10 benchmark infrastructure (extend, not replace)
- Phase 10 DPI-200 results are the new accuracy baseline (not v1.1)
- Soft accuracy margin: 93-94% OK if speed gain justifies it — user decides on borderline cases
- Ship partial wins — don't require all three configs to pass
- Phase 12 decision depends on estimated total corpus runtime after Phase 11

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 11-advanced-config-tuning*
*Context gathered: 2026-06-08*
