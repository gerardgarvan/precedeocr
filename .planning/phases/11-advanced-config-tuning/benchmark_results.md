# Phase 11 Benchmark Results

**Date:** 2026-06-08
**Hardware:** 20-core hybrid CPU (8 performance + 12 efficiency cores)
**Sample:** 100 random PDFs from corpus (seed=42)
**Baseline:** Phase 10 config (PSM 6, OEM 3, whitelist, DPI 200)

## Independent Config Tests

| Config | Duration (s) | Pages | IDs Found | ms/page | Speedup | Accuracy | Result |
|--------|--------------|-------|-----------|---------|---------|----------|--------|
| baseline_phase10 | 136.3 | 127 | 211 | 1072.9 | 1.00x | 100.00% | baseline |
| oem1_only | 135.5 | 127 | 211 | 1066.9 | 1.01x | 100.00% | PASS |
| psm7_only | 212.6 | 127 | 1 | 1673.9 | 0.64x | 0.00% | FAIL |
| dict_off_only | 135.7 | 127 | 211 | 1068.6 | 1.00x | 100.00% | PASS |

## Combination Tests

| Config | Duration (s) | Pages | IDs | ms/page | Speedup | Accuracy | Result |
|--------|--------------|-------|-----|---------|---------|----------|--------|
| oem1+dict_off | 135.6 | 127 | 211 | 1067.3 | 1.01x | 100.00% | PASS |

## Applied Configuration

| Setting | Phase 10 | Phase 11 | Change |
|---------|----------|----------|--------|
| OEM mode | OEM 3 (auto-detect) | **OEM 1 (LSTM-only)** | **applied** |
| PSM mode | PSM 6 (uniform block) | PSM 6 (unchanged) | reverted (PSM 7 failed) |
| Dictionary | enabled | **disabled** | **applied** |

## Speedup Summary

- **Individual best:** oem1_only at 1.01x speedup (1066.9 ms/page vs 1072.9 ms/page baseline)
- **Combined best:** oem1+dict_off at 1.01x speedup (1067.3 ms/page)
- **Phase 10 baseline:** 1072.9 ms/page (DPI 200, OEM 3, PSM 6, whitelist)
- **Phase 11 result:** 1067.3 ms/page (DPI 200, OEM 1, PSM 6, whitelist, dict-off)
- **Phase 11 incremental speedup:** 1.01x (marginal but free)

## Accuracy Analysis

Per D-07 decision framework:
- **Configs with >=94% accuracy:** PASS (shipped)
- **Configs with 93-94% accuracy:** SOFT (user decision required)
- **Configs with <93% accuracy:** FAIL (reverted)

### Results by Config

**OEM 1 (LSTM-only): PASS**
- Accuracy: 100.00% (211/211 IDs matched baseline)
- Speedup: 1.01x (5.6 ms/page faster)
- Decision: Applied per D-06 (partial wins shipped)

**PSM 7 (single-line): FAIL**
- Accuracy: 0.00% (only 1 ID found vs 211 baseline)
- Speedup: 0.64x (slower AND less accurate)
- Decision: Reverted per D-04/D-05 (catastrophic failure, do NOT try other PSM variants)

**Dict-off (disable dictionary loading): PASS**
- Accuracy: 100.00% (211/211 IDs matched baseline)
- Speedup: 1.00x (4.3 ms/page faster, within measurement noise)
- Decision: Applied per D-06 (partial wins shipped)

**OEM 1 + Dict-off combination: PASS**
- Accuracy: 100.00% (211/211 IDs matched baseline)
- Speedup: 1.01x (5.6 ms/page faster)
- Decision: Applied per D-08 (ship any improvement regardless of magnitude)

## PSM 7 Failure Analysis

PSM 7 (single-line text mode) was tested on full page images per D-04. Results:

- **Expected behavior:** PSM 7 optimized for single lines of text
- **Actual behavior:** Catastrophic failure — found only 1 ID across 127 pages (0.00% accuracy vs baseline)
- **Root cause:** Full PDF pages contain multiple text regions (page numbers, dates, handwritten notes). PSM 7's single-line constraint caused Tesseract to ignore most of the page.
- **Attempted fix:** None — per D-05, do NOT try PSM 13 or region cropping. Keep PSM 6 (proven at 94.9% accuracy in v1.1 and 100% in Phase 10).

**Conclusion:** PSM 6 (uniform block of text) is the correct mode for full-page scanned documents. PSM 7 would require region cropping (out of scope for Phase 11 per D-05).

## Phase 12 Gate Assessment (per D-09)

**Estimated total 30K corpus runtime with Phases 10+11 combined:**

1. **Phase 10 speedup:** 4-11x over v1.1 baseline (conservative: 4.3x, optimistic: 11.4x)
2. **Phase 11 incremental:** 1.01x over Phase 10 baseline
3. **Combined speedup:** 4.3x × 1.01 = 4.34x (conservative) to 11.4x × 1.01 = 11.51x (optimistic)

**Projected wall-clock time for 30,429 PDFs:**
- v1.1 baseline: ~70 days (single-threaded equivalent)
- Phase 10+11 conservative: ~16 days (70 days / 4.34)
- Phase 10+11 optimistic: ~6 days (70 days / 11.51)
- **Expected range: 6-16 days**

**Phase 12 recommendation:**
- If production run completes in <24 hours: Phase 12 unnecessary (stop here)
- If production run takes 2-7 days: Phase 12 optional (marginal benefit)
- If production run takes >7 days: Proceed to Phase 12 for algorithmic enhancements

**Decision point:** Run full corpus with Phase 10+11 config first, measure actual wall-clock time, THEN decide on Phase 12.

## Decisions Applied

- **D-04:** PSM 7 tried on full pages, failed catastrophically → kept PSM 6
- **D-05:** PSM 7 failed → did NOT try other PSM variants (PSM 13, etc.)
- **D-06:** Applied partial wins — OEM 1 passed (applied), dict-off passed (applied), PSM 7 reverted
- **D-07:** All passing configs had >=94% accuracy (actually 100%) — no SOFT decisions needed
- **D-08:** Shipped the oem1+dict_off combo (1.01x is free speed for flag changes, zero complexity cost)

## Config String (Applied to precede_ocr.py)

**Lines 397 and 432 (both locations updated identically):**

```python
config = '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789 -c load_system_dawg=false -c load_freq_dawg=false'
```

**Changes from Phase 10 baseline:**
- `--oem 3` → `--oem 1` (skip engine auto-detection, use LSTM-only)
- Added `-c load_system_dawg=false -c load_freq_dawg=false` (skip dictionary loading)
- `--psm 6` unchanged (PSM 7 failed)
- `-c tessedit_char_whitelist=0123456789` unchanged (validated in Phase 10)

## Benchmark Command

```bash
# Generate baseline CSV (Phase 10 state)
python benchmark.py "P:\PeCAN Projects\Precede Clockwork Only\01 Scanned Clock PDFs" --generate-baseline baseline_phase10.csv --skip-dpi --skip-workers --skip-whitelist

# Run Tesseract config benchmark
python benchmark.py "P:\PeCAN Projects\Precede Clockwork Only\01 Scanned Clock PDFs" --tesseract-config --baseline-csv baseline_phase10.csv --skip-dpi --skip-workers --skip-whitelist
```

**Runtime:** ~12-15 minutes for full benchmark suite (baseline generation + 4 independent configs + 1 combination)

---

*Benchmarked: 2026-06-08*
*Applied to pipeline: 2026-06-08*
*Phase 11 Plan 02*
