# Research Summary: OCR Pipeline Performance Optimization (v1.2)

**Domain:** Batch OCR performance optimization
**Researched:** 2026-06-07
**Overall confidence:** MEDIUM-HIGH

## Executive Summary

This research synthesizes findings for optimizing the existing v1.1 batch OCR pipeline (94.9% accuracy baseline) that processes ~30,429 multi-page PDFs on Windows 10 with a 20-core hybrid CPU. The v1.2 milestone targets dramatic throughput improvements by replacing slow PDF rendering (pdf2image/Poppler), tuning Tesseract configuration for digit-only extraction, and optimizing parallelism for the hybrid CPU architecture.

The key architectural insight is **PDF rendering dominates total runtime**. User reports and benchmarks show PyMuPDF renders PDFs 2-12x faster than pdf2image (7-page PDF: 800ms vs 10s), making this the single highest-impact optimization. Combined with Tesseract tuning (character whitelist for 0-9, PSM 7 for single-line digits, OEM 1 LSTM-only mode) and DPI optimization (testing 200-250 DPI vs 300 DPI for speed/accuracy tradeoff), the expected combined speedup is **2-15x end-to-end**, dominated by rendering improvements.

Critical risks center on accuracy degradation from aggressive optimization. PSM 7 (single-line mode) may fail if IDs surrounded by other text; lower DPI may reduce accuracy on degraded scans; disabling Tesseract dictionaries may hurt recognition of nearby text. Research validates **phased approach with benchmarking**: Phase 1 applies drop-in optimizations (PyMuPDF, character whitelist, DPI tuning, worker count) with minimal accuracy risk, Phase 2 tests advanced Tesseract configs requiring corpus validation, Phase 3 adds algorithmic enhancements only if needed. Each phase independently benchmarked for speed and accuracy (maintain ≥94% baseline).

## Key Findings

### Stack: PyMuPDF + Tesseract Optimization

**Core technology change:**
- **Replace pdf2image → PyMuPDF** for PDF-to-image rendering. PyMuPDF is 2.3x faster than pdf2jpg, 1.76x faster than XPDF in official benchmarks. User reports: 7-page PDF in 800ms (PyMuPDF) vs 10s (pdf2image). File sizes 10-20% smaller. No Poppler dependency required. Drop-in API change: `convert_from_path()` → `page.get_pixmap(dpi=300)`. **Confidence: HIGH** (PyMuPDF official docs, multiple 2026 comparison articles).

**Tesseract configuration tuning:**
- **Character whitelist:** `-c tessedit_char_whitelist=0123456789` constrains search space to digits only. Standard optimization for known character sets. Estimated 10-30% OCR speedup. **Confidence: MEDIUM** (Tesseract docs, PyImageSearch tutorials).
- **PSM 7 (single-line mode):** Better for isolated 5-digit IDs than PSM 6 (single column). Recommended for number plates, timestamps. Estimated 5-15% OCR speedup. Trade: may fail if ID surrounded by other text. **Confidence: MEDIUM** (Tesseract PSM tuning guides).
- **OEM 1 (LSTM-only):** Faster than OEM 3 (default) which tries legacy+LSTM. LSTM better context handling for degraded scans. Estimated 10-30% OCR speedup per page. Requires tessdata_fast or tessdata_best (LSTM-only traineddata). **Confidence: MEDIUM** (Tesseract release notes, community comparisons).
- **Disable dictionaries:** `-c load_system_dawg=false -c load_freq_dawg=false` for non-dictionary content (5-digit IDs). Estimated 5-10% OCR speedup. Low confidence; may reduce accuracy on text near IDs. **Confidence: LOW** (Tesseract docs, needs testing).

**DPI optimization:**
- **300 DPI industry standard** for OCR; beyond 300 DPI "does typically not improve results further" and may degrade accuracy by oversizing fonts. For digits at typical size, 200-250 DPI acceptable. For small text (<10pt), 400-600 DPI may help. **Test corpus for minimum viable DPI**: benchmark 200/250/300 DPI for speed/accuracy tradeoff. Potential 0-50% speedup if currently over-rendering. **Confidence: HIGH** (OCR best practices from Pitt, Penn State, Nutrient guides).

**Process pool tuning:**
- Project uses `cpu_count()-1` (19 workers on 20-core CPU). **Benchmark 16-20 workers** to verify optimal saturation. Windows 11+ scheduler handles P-core/E-core assignment automatically; manual affinity "should generally be avoided" per Microsoft docs (can decrease performance by interfering with scheduler). **Confidence: MEDIUM** (Python multiprocessing docs, Microsoft Win32 process docs).

### Architecture: Phased Optimization with Benchmarking

**Three-phase approach to manage risk:**

**Phase 1: Drop-in Performance Gains (Low-Hanging Fruit)**
- PyMuPDF PDF rendering (2-12x rendering speedup)
- Tesseract character whitelist (10-30% OCR speedup)
- Optimal DPI benchmarking (verify 300 DPI, test 200/250 DPI)
- Process pool worker count tuning (benchmark 16-20 workers)

**Expected combined speedup:** 2-15x (dominated by PyMuPDF)
**Complexity:** Low (config changes, API swaps)
**Risk:** Very low (PyMuPDF = visual fidelity, whitelist = subset constraint)

**Phase 2: Advanced Config Tuning (Requires Corpus Validation)**
- Tesseract OEM 1 LSTM-only (10-30% OCR speedup, verify tessdata compatibility)
- PSM 7 single-line mode (5-15% OCR speedup, test accuracy impact)
- Disable Tesseract dictionaries (5-10% OCR speedup, low confidence)
- Grayscale-only preprocessing (3-8% preprocessing speedup, test accuracy)

**Expected incremental speedup:** 1.5-2x on top of Phase 1
**Complexity:** Medium (requires A/B testing on corpus)
**Risk:** Medium (config changes may affect accuracy)

**Phase 3: Algorithmic Enhancements (If Phase 1+2 Insufficient)**
- Smart rotation reordering (10-25% rotation overhead reduction, uses existing stats from v1.1)
- Conditional DPI fallback (15-35% rendering speedup, mirrors existing preprocessing pattern)
- Batch PyMuPDF rendering (5-15% rendering speedup, memory trade-off)

**Expected incremental speedup:** 1.2-1.5x on top of Phase 1+2
**Complexity:** High (algorithmic changes, state management, memory profiling)
**Risk:** Medium-high (increased code complexity, memory usage, new failure modes)

### Critical Pitfalls

**Anti-patterns explicitly avoided:**

1. **Manual CPU affinity for P/E-cores:** Windows 11+ scheduler handles hybrid CPU automatically. Manual affinity "should generally be avoided" per MS docs; can decrease performance. Trust OS scheduler; benchmark worker counts instead. **Confidence: HIGH** (Microsoft Win32 docs, Windows Forum discussions).

2. **Tesseract OSD (Orientation+Script Detection):** PSM 0/1 for auto-rotation unreliable per GitHub issue #4426 ("Poor Rotation / Layout detection" June 2025). Project correctly uses multi-rotation brute-force (90/270/0/180) with regex validation. Enhance with smart reordering based on corpus stats from v1.1, not OSD. **Confidence: HIGH** (Tesseract GitHub, PyImageSearch tutorials).

3. **DPI >300 for digit OCR:** Diminishing returns; may degrade accuracy by oversizing fonts. Stick to 200-300 DPI range. Benchmark lower DPI for speed gains without accuracy loss. **Confidence: HIGH** (OCR best practices guides).

4. **Preprocessing all pages upfront:** Conditional preprocessing (v1.0) targets only failed OCR. Preprocessing everything wastes CPU on clean scans (majority of corpus at 94.9% baseline). Keep conditional fallback. **Confidence: HIGH** (project-specific validated pattern).

5. **GPU-accelerated OCR (EasyOCR, PaddleOCR):** Tesseract CPU-first design already fast for digits (<1s/page). GPU adds dependency, complexity, cost. EasyOCR slower on CPU. Optimize Tesseract config instead. **Confidence: MEDIUM** (OCR engine comparisons 2026).

6. **Page-level multiprocessing:** Overhead of IPC per page. Project correctly uses PDF-level parallelism (each worker handles full PDF). Finer-grained parallelism degrades performance on Windows (spawn cost). Keep coarse-grained: one PDF per worker. **Confidence: HIGH** (PyMuPDF multiprocessing docs, project-specific pattern).

7. **Resize/downscale before OCR:** Counterproductive. OCR needs 200-300 DPI minimum. Downscaling from 300 DPI degrades accuracy. Only upscale if source <200 DPI. Render at target DPI directly with PyMuPDF `get_pixmap(dpi=N)`. **Confidence: HIGH** (OCR best practices, image preprocessing research).

## Implications for Roadmap

Based on research, performance optimization should be built in 3 phases with **stop conditions after each phase** to avoid premature optimization. Order dictated by risk vs reward: low-hanging fruit (Phase 1) → corpus validation (Phase 2) → algorithmic complexity (Phase 3).

### Phase 1: Drop-in Performance Gains
**Rationale:** Highest individual speedup factors (PyMuPDF rendering dominates), lowest implementation risk (config changes, API swaps), no accuracy risk (PyMuPDF = visual fidelity, whitelist = subset constraint). Fast to validate (benchmark, commit, move on).

**Delivers:**
1. Replace pdf2image with PyMuPDF for PDF rendering (2-12x rendering speedup)
2. Add Tesseract character whitelist `0123456789` (10-30% OCR speedup)
3. Benchmark DPI: test 200/250/300 DPI on representative corpus for optimal speed/accuracy tradeoff
4. Benchmark worker count: test 16-20 workers on 20-core hybrid CPU for optimal saturation

**Addresses:** Table stakes — PyMuPDF is industry standard for fast PDF-to-image, character whitelist is standard when character set known, DPI tuning is standard OCR optimization, worker count tuning is standard multiprocessing optimization.

**Avoids:** Anti-features — no manual CPU affinity (trust OS scheduler), no DPI >300 (diminishing returns), no resize/downscale (counterproductive).

**Uses (from stack):** PyMuPDF (new dependency), pytesseract (existing), multiprocessing (existing).

**Research flag:** No deeper research needed — PyMuPDF API well-documented, Tesseract config options standard, DPI optimization well-established. **Benchmark required:** speed and accuracy on representative corpus (e.g., 1000 PDFs) to validate speedup and maintain ≥94% baseline accuracy.

**Stop condition:** If Phase 1 achieves acceptable total runtime for 30K+ corpus (e.g., <24 hours end-to-end), stop. Do NOT proceed to Phase 2 unless further optimization ROI justifies increased code complexity.

---

### Phase 2: Advanced Config Tuning
**Rationale:** Speedup gains smaller than Phase 1 (10-30% vs 2-12x), requires corpus-wide accuracy validation (time-intensive), config interactions need testing (OEM+PSM+whitelist combinations). Defer until Phase 1 validated.

**Delivers:**
5. Tesseract OEM 1 (LSTM-only) mode (10-30% OCR speedup, verify tessdata compatibility)
6. PSM 7 (single-line mode) for isolated IDs (5-15% OCR speedup, test accuracy impact)
7. Disable Tesseract dictionaries for digit-only content (5-10% OCR speedup, low confidence)
8. Grayscale-only preprocessing (3-8% preprocessing speedup, test accuracy impact)

**Addresses:** Differentiators — advanced Tesseract tuning beyond standard configs, preprocessing simplification.

**Avoids:** Anti-features — no OSD (unreliable), no preprocessing all pages (conditional fallback proven).

**Uses (from stack):** pytesseract config params (existing), PIL/OpenCV (existing).

**Research flag:** No deeper research needed — all configs documented in Tesseract official docs. **A/B testing required:** each config change must be benchmarked on corpus for accuracy impact. Test interactions (e.g., OEM 1 + PSM 7 + whitelist together).

**Stop condition:** If accuracy drops below 94% baseline with any config, revert that config. If incremental speedup <1.5x on top of Phase 1, stop (diminishing returns). Do NOT proceed to Phase 3 unless Phase 1+2 still insufficient.

---

### Phase 3: Algorithmic Enhancements
**Rationale:** Highest complexity-to-speedup ratio, requires new infrastructure (stats tracking, fallback logic, memory management), premature optimization if Phase 1+2 achieve target throughput. Only proceed if Phases 1+2 insufficient.

**Delivers:**
9. Smart rotation reordering based on corpus stats from v1.1 (10-25% rotation overhead reduction if IDs clustered at 90°)
10. Conditional DPI fallback: start at 200 DPI, re-render at 300 DPI only if OCR fails (15-35% rendering speedup if 70%+ succeed at lower DPI)
11. Batch PyMuPDF rendering: pre-render all pages before OCR loop (5-15% rendering speedup, memory trade-off)

**Addresses:** Differentiators — smart strategies beyond config tuning, algorithmic optimizations.

**Avoids:** Anti-features — no page-level multiprocessing (IPC overhead), no caching across runs (single-shot batch job).

**Uses (from stack):** PyMuPDF (Phase 1), campaign stats from v1.1 (existing), tempfile for batch rendering (stdlib).

**Research flag:** No deeper research needed — smart rotation builds on v1.1 stats infrastructure, conditional DPI mirrors existing preprocessing fallback, batch rendering documented in PyMuPDF multiprocessing guide. **Memory profiling required:** batch rendering holds N pages * ~1-2MB per 300 DPI image in memory; validate on multi-page PDFs.

**Stop condition:** If code complexity outweighs speedup gains (<1.2x incremental), stop. If memory usage becomes problematic (OOM on multi-page PDFs), revert batch rendering.

---

### Phase Ordering Rationale

**Why this order:**
1. **Phase 1 first:** Lowest risk, highest reward. PyMuPDF rendering dominates total runtime based on benchmarks. Get 2-15x speedup with minimal code changes before attempting riskier optimizations.

2. **Phase 2 after Phase 1:** Requires accuracy validation on corpus (time-intensive). Only proceed if Phase 1 insufficient for target throughput. Each config change must be A/B tested; interactions between configs (OEM+PSM+whitelist) need validation.

3. **Phase 3 last (only if needed):** Highest complexity, lowest per-feature speedup. Smart rotation requires v1.1 stats infrastructure; conditional DPI requires fallback logic; batch rendering requires memory management. Only justified if Phase 1+2 still leave throughput gap.

**Dependency chain discovered in research:**
- PyMuPDF rendering (Phase 1) enables batch rendering optimization (Phase 3)
- DPI tuning (Phase 1) informs conditional DPI fallback (Phase 3)
- Rotation stats from v1.1 enable smart reordering (Phase 3)
- Tesseract config optimizations (Phase 1+2) are independent of algorithmic enhancements (Phase 3)

**Architecture preserves v1.0/v1.1 patterns:**
- All phases enhance existing `process_single_pdf()` / multi-rotation loop without breaking checkpoints or campaign management
- Worker functions remain PDF-level (coarse-grained parallelism)
- Atomic checkpoint writes unchanged (crash-safe resume)
- Campaign stats from v1.1 can inform Phase 3 rotation reordering

**Pitfall avoidance:**
- Phase 1 establishes PyMuPDF baseline and optimal DPI before advanced tuning
- Phase 2 validates each config change individually for accuracy impact before combining
- Phase 3 deferred until Phases 1+2 proven insufficient (avoid premature optimization)

### Research Flags for Phases

**Phases likely needing deeper research during planning:**
- **None** — all optimization techniques documented in official PyMuPDF, Tesseract, and Python multiprocessing guides. Research synthesis provides sufficient detail for implementation.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Drop-in Gains):** PyMuPDF API well-documented, Tesseract whitelist standard, DPI optimization standard, worker tuning standard. **Benchmarking required,** not additional research.
- **Phase 2 (Advanced Config):** All Tesseract configs in official docs. **A/B testing required** for accuracy validation, not additional research.
- **Phase 3 (Algorithmic):** Smart rotation builds on v1.1, conditional DPI mirrors v1.0 preprocessing fallback, batch rendering in PyMuPDF multiprocessing guide. **Memory profiling required,** not additional research.

**No phases need `/gsd:research-phase`** — all patterns sufficiently documented in this research synthesis and official documentation (PyMuPDF, Tesseract, Python stdlib). Implementation needs benchmarking and validation, not additional research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack (PyMuPDF)** | HIGH | Official PyMuPDF docs, multiple 2026 benchmarks (PyMuPDF vs pdfplumber, Battle of PDF Titans), user reports (800ms vs 10s for 7-page PDF). Drop-in replacement for pdf2image. No GPU required, Windows-compatible. |
| **Stack (Tesseract config)** | MEDIUM-HIGH | Character whitelist, PSM modes, OEM modes, dictionary disabling all documented in official Tesseract docs. PSM 7 and OEM 1 require corpus testing for accuracy impact. Whitelist is standard optimization (HIGH confidence). Dictionary disabling is LOW confidence (needs testing). |
| **Features (DPI optimization)** | HIGH | 300 DPI industry standard for OCR per Pitt, Penn State, Nutrient guides. "Beyond 300 DPI does typically not improve results further" per Broadcom OCR guide. 200-250 DPI acceptable for digits at typical size. Small text (<10pt) may need 400-600 DPI. |
| **Features (Worker tuning)** | MEDIUM | Python multiprocessing docs confirm `cpu_count()` standard, but optimal worker count depends on workload (CPU-bound vs I/O-bound). Hybrid CPU (P/E-cores) handled by Windows 11+ scheduler automatically per Microsoft docs. Manual affinity "should generally be avoided." **Benchmarking required** to verify optimal count (16-20 workers). |
| **Architecture (Phased approach)** | HIGH | Phased optimization with stop conditions is standard performance engineering practice. Phase 1 low-risk/high-reward, Phase 2 medium-risk/medium-reward, Phase 3 high-risk/low-reward matches industry best practices. Benchmark-driven validation prevents premature optimization. |
| **Pitfalls (Anti-features)** | HIGH | OSD unreliability documented in Tesseract GitHub #4426. DPI >300 diminishing returns per OCR best practices. Manual CPU affinity discouraged per Microsoft docs. Page-level multiprocessing IPC overhead validated in PyMuPDF multiprocessing guide. Preprocessing conditional fallback proven in v1.0. |

**Overall confidence:** MEDIUM-HIGH

Research is comprehensive with authoritative sources (official docs for PyMuPDF, Tesseract, Python multiprocessing; 2026 benchmarks from reputable sources; OCR best practices from educational institutions and enterprise guides). PyMuPDF speedup claims are HIGH confidence (official benchmarks + user reports). Tesseract config optimizations are MEDIUM confidence (documented in official docs but require corpus testing for accuracy impact). Worker tuning and DPI optimization need benchmarking on actual hardware/corpus to validate claims.

**Recommendation:** Proceed with phased approach. **Phase 1 is low-risk with proven technologies** (PyMuPDF widely adopted, character whitelist standard, DPI tuning standard). **Phases 2+3 are medium-risk** (Tesseract config changes may affect accuracy, algorithmic enhancements add complexity). Each phase must be independently benchmarked for speed and accuracy before proceeding to next phase. Stop if target throughput achieved or accuracy drops below baseline.

## Gaps to Address

**Areas where research was inconclusive:**

1. **Tesseract dictionary disabling impact:** Research documents that disabling `load_system_dawg` and `load_freq_dawg` can improve recognition on non-dictionary content (receipts, IDs), but may reduce accuracy on standard text. **Gap:** No specific benchmarks for 5-digit numeric IDs surrounded by cursive "Precede" label. **Mitigation:** Phase 2 must A/B test this config on representative corpus; if accuracy drops, revert. Mark as **LOW confidence** feature.

2. **PyMuPDF vs pdf2image exact speedup on Windows:** Research shows 2-12x range from various benchmarks, but no direct head-to-head on Windows 10 with identical multi-page PDFs. User reports (800ms vs 10s) suggest 12x, but official PyMuPDF benchmark shows 2.3x vs pdf2jpg, 1.76x vs XPDF (not pdf2image directly). **Gap:** Actual speedup on project's hardware/corpus unknown. **Mitigation:** Phase 1 must benchmark before/after on representative 1000 PDFs to measure real-world speedup. Expect 2-12x range, but validate.

3. **Optimal worker count for 20-core hybrid CPU on Windows:** Research documents that Windows 11+ scheduler handles P/E-core assignment, but optimal worker count (16 vs 19 vs 20 vs 24) depends on workload characteristics (CPU-bound vs I/O-bound ratio). **Gap:** No specific guidance for OCR workload (4 rotation attempts + preprocessing fallback) on hybrid CPU. **Mitigation:** Phase 1 must benchmark 16-20 worker counts to find optimal saturation point. Monitor CPU utilization; if <85%, increase workers; if context switching overhead high, decrease workers.

4. **Conditional DPI fallback effectiveness:** Research suggests 200-250 DPI may suffice for clean scans, but project's corpus has "scanned images vary in quality" per constraints. **Gap:** Unknown what percentage of corpus succeeds at 200 DPI vs requires 300 DPI. If <70% succeed at lower DPI, conditional fallback adds overhead without benefit. **Mitigation:** Phase 3 (if needed) must benchmark accuracy at 200 DPI on representative corpus before implementing fallback logic. If >90% need 300 DPI anyway, skip conditional fallback (not worth complexity).

5. **Memory usage for batch PyMuPDF rendering:** Research documents PyMuPDF internal caching benefits from batch access, but memory trade-off is N pages * ~1-2MB per 300 DPI image. **Gap:** Unknown typical page count per PDF in corpus. If PDFs average 10 pages, batch rendering holds 10-20MB per PDF per worker (19 workers * 20MB = 380MB), acceptable. If PDFs average 100 pages, batch rendering holds 190MB per worker (19 workers * 190MB = 3.6GB), potentially problematic. **Mitigation:** Phase 3 (if needed) must profile memory usage on largest PDFs in corpus before enabling batch rendering. If memory spikes cause OOM, revert or add max-pages-per-batch limit.

**All gaps require benchmarking/profiling on actual hardware and corpus, not additional research.** Existing research provides optimization strategies; implementation needs to validate assumptions with empirical data.

## Topics Needing Phase-Specific Research Later

**None.** All performance optimization techniques are documented in official sources:
- PyMuPDF: official docs, multiprocessing guide, performance comparison methodology
- Tesseract: official docs for PSM/OEM/whitelist/dictionaries, GitHub issues for known limitations
- Python multiprocessing: stdlib docs for Pool, worker tuning, Windows spawn behavior
- OCR best practices: educational guides (Pitt, Penn State), enterprise guides (Nutrient, Broadcom)

**Implementation needs empirical validation, not additional research:**
- Phase 1: Benchmark PyMuPDF speedup, DPI accuracy, worker saturation on actual hardware/corpus
- Phase 2: A/B test Tesseract configs for accuracy impact on representative corpus
- Phase 3: Profile memory usage for batch rendering, validate smart rotation speedup from v1.1 stats

**No `/gsd:research-phase` calls needed** — proceed directly to `/gsd:plan-phase` with benchmarking/validation steps included in phase plans.

## Sources

### Performance Benchmarks & Comparisons
- [PyMuPDF Appendix 4: Performance Comparison Methodology](https://pymupdf.readthedocs.io/en/latest/app4.html)
- [PyMuPDF Multiprocessing Documentation](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html)
- [PyMuPDF vs pdfplumber in 2026](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/)
- [Battle of the PDF Titans: PyMuPDF, pdfplumber, pdf2image, and Textract](https://openwebtech.com/battle-of-the-pdf-titans-apache-tika-pymupdf-pdfplumber-pdf2image-and-textract/)
- [PaddleOCR vs Tesseract vs EasyOCR: OCR Speed and Accuracy 2026](https://www.codesota.com/ocr/paddleocr-vs-tesseract)

### Tesseract Configuration & Optimization
- [Tuning Tesseract PSM and OEM for Precise OCR Character Recognition](https://sqlpey.com/python/tesseract-psm-oem-tuning/)
- [Tesseract: Improving the quality of the output](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [Improve Accuracy by tuning PSM values of Tesseract – Part 1](https://www.cloudthat.com/resources/blog/improve-accuracy-by-tuning-psm-values-of-tesseract-part-1)
- [Improve Accuracy by tuning PSM values of Tesseract – Part 2](https://www.cloudthat.com/resources/blog/improve-accuracy-by-tuning-psm-values-of-tesseract-part-2)
- [All Tesseract OCR options – Muthukrishnan](https://muthu.co/all-tesseract-ocr-options/)
- [Whitelisting and Blacklisting Characters with Tesseract and Python](https://pyimagesearch.com/2021/09/06/whitelisting-and-blacklisting-characters-with-tesseract-and-python/)

### DPI & Image Quality Best Practices
- [Best Practices - OCR @ Pitt](https://pitt.libguides.com/ocr/bestpractices)
- [Image Quality and Resolution for OCR results](https://knowledge.broadcom.com/external/article/254861/image-quality-and-resolution-for-ocr-res.html)
- [Planning and Executing a Successful OCR project - Penn State](https://guides.libraries.psu.edu/c.php?g=1202269&p=8791865)
- [OCR best practices - Document Engine - Nutrient](https://www.nutrient.io/guides/document-engine/ocr/best-practices/)
- [PyMuPDF Pixmap and Image Processing](https://pymupdf.readthedocs.io/en/latest/pixmap.html)

### Python Multiprocessing & Memory Management
- [Multiprocessing in Python: A Guide to Using Multiple CPU Cores](https://medium.com/@aruns89/multiprocessing-in-python-a-guide-to-using-multiple-cpu-cores-f2b3c1bcc83a)
- [Python multiprocessing documentation](https://docs.python.org/3/library/multiprocessing.html)
- [Memory Leak in Python multiprocessing.Pool](https://fromkk.com/posts/memory-leak-in-python-multiprocessing-dot-pool/)
- [Python multiprocessing.pool Memory Usage Growing: Causes and Solutions](https://www.pythontutorials.net/blog/memory-usage-keep-growing-with-python-s-multiprocessing-pool/)

### Windows Hybrid CPU & Affinity
- [How to Permanently Set CPU Affinity in Windows 11 & 10](https://windowsforum.com/threads/how-to-permanently-set-cpu-affinity-in-windows-11-10-for-optimal-performance.369250/)
- [CPU affinity in Windows: controls cores and priority](https://www.pchardwarepro.com/en/How-to-manage-CPU-cores-with-affinity-and-priority-in-Windows/)
- [Multiple Processors - Win32 apps | Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/procthread/multiple-processors)
- [Processor Groups - Win32 apps | Microsoft Learn](https://learn.microsoft.com/en-us/windows/win32/procthread/processor-groups)

### OCR Preprocessing & Image Processing
- [Image preprocessing and modified adaptive thresholding for improving OCR](https://arxiv.org/abs/2111.14075)
- [Enhancing OCR Accuracy with OpenCV and PyTesseract](https://trenton3983.github.io/posts/ocr-image-processing-pytesseract-cv2/)
- [OpenCV vs Pillow for Image Processing](https://primeprogram.medium.com/opencv-vs-pillow-which-is-better-for-image-processing-93f68ab81137)

### 2026 OCR Landscape & Trends
- [OCR 2026: Everything You Need to Know, Trends, Tools & Tips](https://www.makoletdigimarket.com/stop-retyping-how-ocr-in-2026-actually-works-and-where-its-going/)
- [OCR Accuracy Benchmarks: The 2026 Digital Transformation Revolution](https://medium.com/@info_59976/ocr-accuracy-benchmarks-the-2026-digital-transformation-revolution-2f7095c2696f)
- [The Definitive Guide to OCR in 2026: From Pipelines to VLMs](https://slavadubrov.github.io/blog/2026/03/04/the-definitive-guide-to-ocr-in-2026-from-pipelines-to-vlms/)
