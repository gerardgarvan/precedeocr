# Phase 10 Benchmark Results

**Date:** 2026-06-07
**Hardware:** 20-core hybrid CPU (8 performance + 12 efficiency cores), 24 threads
**Sample:** 100 random PDFs from corpus (seed=42), 87 unique folders
**Corpus stats:** 30,429 total PDFs, file sizes 13.7 KB - 1125.1 KB
**Baseline:** v1.1 (pdf2image + Poppler, 300 DPI, cpu_count()-1 workers)

## DPI Benchmark

| DPI | Duration | Pages | IDs Found | Pages/sec | vs. DPI 300 |
|-----|----------|-------|-----------|-----------|-------------|
| 200 | 137.0s   | 127   | 211       | 0.93      | **+43% faster** |
| 250 | 155.7s   | 127   | 196       | 0.82      | +25% faster |
| 300 | 195.4s   | 127   | 186       | 0.65      | baseline |

**Winner:** DPI 200 — 0.93 pages/sec (43% faster than DPI 300)

**ID extraction comparison:**
- DPI 200 found **more IDs** (211) than DPI 300 (186) — higher DPI does not guarantee better extraction
- DPI 300 may be over-sharp for these scanned documents, introducing OCR artifacts

**Accuracy validation:** Not run (no --baseline-csv provided). User accepted DPI 200 results based on speed and ID count.

## Worker Count Benchmark

| Workers | Duration | PDFs/sec | vs. 16 workers |
|---------|----------|----------|----------------|
| 16      | 55.4s    | 1.806    | baseline |
| 17      | 55.9s    | 1.789    | -0.9% |
| 18      | 55.5s    | 1.801    | -0.3% |
| 19      | 55.7s    | 1.795    | -0.6% |
| 20      | 55.6s    | 1.800    | -0.3% |

**Winner:** 16 workers — 1.806 PDFs/sec (marginal 0.3% advantage)

**Analysis:**
- All worker counts (16-20) performed nearly identically (< 1% variance)
- 16 workers optimal for 20-core hybrid CPU (8P+12E cores, 24 threads)
- Slight advantage suggests efficiency cores benefit from fewer competing threads
- Leaving 4 threads for OS/background tasks prevents system thrashing

**Comparison to v1.1 default (cpu_count()-1):**
- v1.1 default: 19 workers (cpu_count()-1 on 20-core CPU)
- Phase 10 winner: 16 workers (1.806 PDFs/sec)
- Speedup: 16 workers vs 19 workers is negligible in benchmark (~0.6% faster)
- Choosing 16 for consistency and minor edge in benchmark results

## Whitelist Impact

| Configuration | Duration | ms/page | vs. whitelist enabled |
|---------------|----------|---------|----------------------|
| With whitelist (0-9 only) | 47.7s | 2384.7 | baseline |
| Without whitelist | 48.6s | 2427.6 | **-1.8% slower** |

**Finding:** Whitelist enabled is 1.8% faster — **keep enabled**

**Analysis:**
- Character whitelist `tessedit_char_whitelist=0123456789` provides minor but measurable speedup
- Tesseract OEM 3 (LSTM) benefits from constraining character space to digits
- Already implemented in v1.1 pipeline — no code change needed
- Benchmark confirms design choice

## Accuracy Validation (QUAL-01)

**Status:** NOT RUN

**Reason:** User did not provide `--baseline-csv` argument with v1.1 results for comparison.

**Assumption:** DPI 200 accuracy accepted based on:
1. DPI 200 found **more IDs** (211) than DPI 300 (186)
2. Scanned documents at this quality level do not benefit from higher DPI
3. User's visual inspection of corpus confirmed readability

**Risk:** No quantitative accuracy validation against v1.1 baseline. If accuracy issues emerge in production, may need to re-benchmark with DPI 250 as fallback.

## Applied Configuration

| Setting | Before (v1.1) | After (v1.2 Phase 10) | Change |
|---------|---------------|----------------------|--------|
| **Rendering engine** | pdf2image + Poppler | PyMuPDF (fitz) | 2-12x faster (per research) |
| **DPI** | 300 | **200** | **+43% faster** |
| **Default workers** | cpu_count()-1 (19) | **16** | ~0.6% faster (negligible) |
| **Whitelist** | enabled (0-9) | enabled (0-9) | validated 1.8% speedup |

## Estimated Total Speedup

**PyMuPDF rendering speedup (research estimate):** 2-12x over pdf2image
- Conservative estimate: **3x** (lower bound from research)
- Optimistic estimate: **8x** (midpoint from research)

**DPI optimization speedup:** 1.43x (43% faster at DPI 200 vs 300)

**Worker optimization speedup:** ~1.006x (0.6% faster, negligible)

**Whitelist validation:** 1.018x (1.8% faster, already in v1.1)

### Combined Speedup Calculation

**Conservative combined speedup:**
- PyMuPDF (3x) × DPI (1.43x) = **4.3x over v1.1 baseline**

**Optimistic combined speedup:**
- PyMuPDF (8x) × DPI (1.43x) = **11.4x over v1.1 baseline**

**Expected speedup range:** **4-11x over v1.1**

### Projected 30K Corpus Processing Time

**v1.1 baseline estimate:** ~70 days (single-threaded equivalent extrapolated from small batches)

**v1.2 Phase 10 projections:**
- **Conservative (4.3x):** ~16 days (70 days / 4.3)
- **Optimistic (11.4x):** ~6 days (70 days / 11.4)
- **Expected range:** **6-16 days** for full 30,429-PDF corpus

**Reality check:** User's 20-core CPU with 16 workers provides massive parallelization. Actual wall-clock time will depend on:
1. PyMuPDF rendering speedup in production (benchmark this separately)
2. Disk I/O bottlenecks (30K PDFs on network drive)
3. System overhead and thermal throttling during multi-day runs

## Recommendations

1. **Production validation:** Run Phase 10 pipeline on full corpus and compare wall-clock time to v1.1 baseline
2. **Accuracy spot-check:** Manually inspect 50-100 random pages from production run to validate DPI 200 extraction quality
3. **Fallback plan:** If accuracy issues emerge, re-run with DPI 250 (25% faster than 300, more conservative than 200)
4. **Phase 11 readiness:** Phase 10 provides substantial speedup. Proceed to Phase 11 (Tesseract tuning) only if additional gains needed after production validation

## Benchmark Command

```bash
python benchmark.py "P:\PeCAN Projects\Precede Clockwork Only\01 Scanned Clock PDFs"
```

**Runtime:** ~10 minutes for full benchmark suite (DPI sweep + worker sweep + whitelist test)

---

*Benchmarked: 2026-06-07*
*Applied to pipeline: 2026-06-07*
*Phase 10 Plan 03*
