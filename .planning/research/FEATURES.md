# Feature Landscape: OCR Pipeline Performance Optimization

**Domain:** Batch OCR performance optimization for 30K+ PDF corpus
**Researched:** 2026-06-07
**Context:** Optimizing existing multi-rotation OCR pipeline (94.9% accuracy baseline) for throughput on 20-core hybrid CPU

## Table Stakes

Features that OCR performance optimization pipelines expect. Missing = incomplete optimization effort.

| Feature | Why Expected | Complexity | Dependency | Speedup Estimate | Notes |
|---------|--------------|------------|------------|------------------|-------|
| **PyMuPDF PDF rendering** | Industry standard for fast PDF-to-image conversion; 2.3x faster than pdf2jpg, 1.76x faster than XPDF. Direct replacement for pdf2image. User reports: 7-page PDF in 800ms vs 10s with pdf2image. | **Low** | Requires pdf2image removal, drop-in API change from `convert_from_path()` to `page.get_pixmap(dpi=300)` | **2-12x rendering** (based on PyMuPDF vs pdf2image benchmarks) | DPI parameter auto-saves to output image (better than matrix). PyMuPDF doesn't require Poppler external dependency. 10-20% smaller file sizes than pdf2image. **Confidence: HIGH** |
| **Tesseract character whitelist** | Constrains search space to 0-9 for 5-digit IDs; standard optimization when character set is known. Config: `-c tessedit_char_whitelist=0123456789` | **Low** | Single config parameter in existing pytesseract call | **10-30% OCR speed** (estimated from constrained search space) | Reduces false positives (O/0, I/1, S/5 confusion already handled). Works with existing PSM 6. Combine with existing normalization logic. **Confidence: MEDIUM** |
| **Optimal DPI tuning** | 300 DPI industry standard for OCR; higher DPI degrades performance without accuracy gain. Current implementation likely defaults to 300 DPI. | **Low** | Verify current DPI, benchmark 200/250/300 DPI for digit-only accuracy | **Variable** (0-50% if over-rendering) | For small text (<10pt), 400-600 DPI may help. For digits at typical size, 200-250 DPI acceptable. Test corpus for minimum viable DPI. **Confidence: HIGH** |
| **Process pool worker tuning** | Standard multiprocessing optimization for CPU-bound tasks. Project uses `cpu_count()-1` already; verify this is optimal for 20-core hybrid CPU (P-cores + E-cores). | **Low** | Benchmark with different worker counts (16, 19, 20, 24) on hybrid CPU | **Variable** (5-20% if misconfigured) | Windows scheduler handles P/E-core assignment automatically in Win11+. Manual affinity setting "should generally be avoided" per MS docs. Test if `cpu_count()` (20) vs `cpu_count()-1` (19) matters. **Confidence: MEDIUM** |
| **Worker process recycling** | Prevents memory leaks in long-running multiprocessing jobs. Use `maxtasksperchild` parameter. Project already uses process recycling per v1.0 decisions. | **Low** | Already implemented; verify parameter value is reasonable (100-500 tasks) | **N/A** (stability, not speed) | `maxtasksperchild=100` typical for OCR workloads with third-party libraries (pytesseract, OpenCV). Slight overhead from process restart, negligible for multi-page PDFs. **Confidence: HIGH** |

## Differentiators

Features that accelerate performance beyond standard optimizations. Not expected, but high-value.

| Feature | Value Proposition | Complexity | Dependency | Speedup Estimate | Notes |
|---------|-------------------|------------|------------|------------------|-------|
| **Tesseract OEM 1 (LSTM-only)** | Faster than OEM 3 (default) which tries legacy+LSTM. Modern LSTM engine handles digits well. Trade: slower initialization, but amortized over multi-page PDFs. | **Low** | Config parameter: `--oem 1` in pytesseract call. Requires `tessdata_fast` or `tessdata_best` (LSTM-only traineddata). | **10-30% OCR speed** (per-page) | LSTM better context handling for degraded scans. If using tessdata_fast/best, OEM 0/2 won't work (LSTM-only). Verify installed tessdata supports OEM 1. **Confidence: MEDIUM** |
| **Smart rotation early termination** | Skip remaining rotations once regex match found. Project already does this (90/270/0/180 with early stop). Enhance: track rotation success stats, reorder by likelihood. | **Medium** | Extend existing multi-rotation logic; add rotation distribution tracking to campaign stats | **10-25% rotation overhead** (if IDs clustered at 90°) | If 80% of IDs are 90°, reordering to [90, 270, 0, 180] saves 2.25 passes avg vs [0, 90, 180, 270]. Stats from v1.1 show rotation distribution — use for heuristic ordering. **Confidence: MEDIUM** |
| **Conditional DPI fallback** | Start at 200 DPI, re-render at 300 DPI only if OCR fails. Mirrors existing conditional preprocessing strategy. | **Medium** | Modify PDF rendering to accept DPI param; track DPI used in results CSV | **15-35% rendering** (if 70%+ succeed at 200 DPI) | Trade: extra rendering pass on failure (uncommon if baseline is 94.9% success). Best for clean scans where lower DPI suffices. Test on corpus: does 200 DPI maintain >90% accuracy? **Confidence: MEDIUM** |
| **PSM 7 for single-line digits** | Treats image as single line vs PSM 6 (single column). Better for isolated 5-digit IDs. Potential accuracy+speed gain. | **Low** | Change `--psm 6` to `--psm 7` in pytesseract config; benchmark on test corpus | **5-15% OCR speed** (simpler layout assumption) | PSM 7 recommended for number plates, timestamps. Trade: may fail if ID surrounded by other text. Test on representative pages. PSM 8 (single word) too restrictive. **Confidence: MEDIUM** |
| **Batch PyMuPDF rendering** | Pre-render all pages in PDF before OCR loop vs on-demand per-page. Enables better caching, reduces file open/close overhead. | **Medium** | Refactor to: open PDF → render all pages → close PDF → OCR loop over cached images | **5-15% rendering** (amortized open/close, better caching) | PyMuPDF internal cache benefits from batch access. Memory trade: N pages * ~1-2MB per 300 DPI image. For 10-page PDF: 10-20MB temp storage. Use temp directory cleanup. **Confidence: MEDIUM** |
| **Disable Tesseract dictionaries** | Set `load_system_dawg=false`, `load_freq_dawg=false` for non-dictionary content (5-digit IDs). Reduces search overhead. | **Low** | Add config params: `-c load_system_dawg=false -c load_freq_dawg=false` | **5-10% OCR speed** (for numeric-only content) | Dictionaries hurt accuracy on receipts, IDs, non-standard text. May slightly reduce accuracy on text near IDs (e.g., "Precede" label). Test impact on existing 94.9% baseline. **Confidence: LOW** |
| **Grayscale-only preprocessing** | Skip conditional OpenCV fallback; always grayscale before OCR. Simplifies pipeline, reduces color data. | **Low** | Modify preprocessing: always grayscale, skip conditional threshold/denoise unless OCR fails | **3-8% preprocessing** (if currently processing color images) | Trade: may reduce accuracy on color-dependent scans (rare for scanned docs). Grayscale "reduces computational requirements" per research. Test on corpus. **Confidence: MEDIUM** |

## Anti-Features

Features to explicitly NOT build. Common performance traps to avoid.

| Anti-Feature | Why Avoid | What to Do Instead | Complexity |
|--------------|-----------|-------------------|------------|
| **Manual CPU affinity for P/E-cores** | Windows 11+ scheduler handles hybrid CPU automatically. Manual affinity "should generally be avoided" per MS docs; can decrease performance by interfering with scheduler. | Trust OS scheduler. Benchmark with `cpu_count()` vs `cpu_count()-1` workers to verify saturation. | N/A |
| **Tesseract OSD (Orientation+Script Detection)** | PSM 0/1 for auto-rotation unreliable ("Poor Rotation / Layout detection" GitHub #4426). Project correctly uses multi-rotation brute-force with regex validation. | Keep existing 4-rotation strategy (90/270/0/180). Enhance with smart reordering based on corpus stats. | N/A |
| **DPI >300 for digit OCR** | Diminishing returns; may degrade accuracy by oversizing fonts. "Beyond 300 DPI does typically not improve results further." | Stick to 200-300 DPI range. Benchmark lower DPI (200/250) for speed gains without accuracy loss. | N/A |
| **Preprocessing all pages upfront** | Conditional preprocessing (v1.0) targets only failed OCR. Preprocessing everything wastes CPU on clean scans (majority of corpus at 94.9% baseline). | Keep conditional fallback. Only preprocess (threshold, denoise) after initial OCR fails. | N/A |
| **GPU-accelerated OCR (EasyOCR, PaddleOCR)** | Tesseract CPU-first design already fast for digits (<1s/page). GPU adds dependency, complexity, cost. EasyOCR slower on CPU. | Optimize Tesseract config (whitelist, PSM, OEM). Project constraint: local processing, no cloud. | N/A |
| **Page-level multiprocessing** | Overhead of IPC per page. Project correctly uses PDF-level parallelism (each worker handles full PDF). Finer-grained parallelism degrades performance on Windows (spawn cost). | Keep coarse-grained parallelism: one PDF per worker. Pool.map(process_pdf, pdf_paths). | N/A |
| **Caching OCR results across runs** | Single-shot batch job (out of scope per PROJECT.md). Checkpoint/resume handles interruption. Cross-run caching adds complexity for marginal benefit (re-running rare). | Use existing checkpoint/resume for crash recovery. No need for persistent cache beyond campaign_state.json. | N/A |
| **Resize/downscale before OCR** | Counterproductive. OCR needs 200-300 DPI minimum. Downscaling from 300 DPI degrades accuracy. Only upscale if source <200 DPI. | Render at target DPI directly (200-300). Avoid post-rendering resize. PyMuPDF `get_pixmap(dpi=N)` handles this. | N/A |
| **EXIF orientation detection** | PDFs don't have EXIF data (camera metadata). Only relevant for JPEG/photo inputs. Project processes scanned PDFs (rasterized pages). | Not applicable. Continue multi-rotation strategy for scanned document orientation. | N/A |

## Feature Dependencies

```
PyMuPDF rendering
  ↓
Optimal DPI tuning (200-300 DPI parameter)
  ↓
Batch rendering (optional: render all pages before OCR)
  ↓
Tesseract config optimization (whitelist, PSM 7, OEM 1, disable dictionaries)
  ↓
Smart rotation early termination (track stats, reorder rotations)
  ↓
Conditional DPI fallback (optional: re-render at higher DPI on failure)
```

**Independent optimizations:**
- Process pool worker tuning (parallel to above)
- Grayscale-only preprocessing (replaces conditional preprocessing)

## MVP Recommendation

### Phase 1: Drop-in Performance Gains (Low-Hanging Fruit)
**Prioritize:**
1. **PyMuPDF PDF rendering** — 2-12x rendering speedup, drop-in replacement
2. **Tesseract character whitelist** — 10-30% OCR speedup, single config line
3. **Optimal DPI benchmarking** — Verify 300 DPI is optimal; test 200/250 DPI for speed
4. **Process pool worker count tuning** — Benchmark 16-20 workers on 20-core CPU

**Expected combined speedup:** 2-15x (dominated by PyMuPDF rendering improvement)

**Complexity:** Low — all config-level changes, no algorithm rewrites

**Risk:** Very low — PyMuPDF API well-documented, Tesseract configs safe

### Phase 2: Advanced Config Tuning
**Defer to Phase 2:**
5. **Tesseract OEM 1 (LSTM-only)** — 10-30% OCR speedup, verify tessdata compatibility
6. **PSM 7 (single-line mode)** — 5-15% OCR speedup, test on corpus for accuracy impact
7. **Disable Tesseract dictionaries** — 5-10% OCR speedup, low-confidence (needs testing)
8. **Grayscale-only preprocessing** — 3-8% preprocessing speedup, test accuracy impact

**Expected incremental speedup:** 1.5-2x on top of Phase 1

**Complexity:** Medium — requires corpus benchmarking, accuracy validation

**Risk:** Medium — config changes may affect accuracy (need A/B testing)

### Phase 3: Algorithmic Enhancements (If Needed)
**Defer to Phase 3 (only if Phase 1+2 insufficient):**
9. **Smart rotation reordering** — 10-25% rotation overhead reduction, uses existing stats
10. **Conditional DPI fallback** — 15-35% rendering speedup, mirrors existing preprocessing pattern
11. **Batch PyMuPDF rendering** — 5-15% rendering speedup, memory trade-off

**Expected incremental speedup:** 1.2-1.5x on top of Phase 1+2

**Complexity:** High — algorithmic changes, state management, memory profiling

**Risk:** Medium-high — increased code complexity, memory usage, new failure modes

### Rationale for Ordering

**Phase 1 prioritized** because:
- Lowest implementation risk (config changes, API swaps)
- Highest individual speedup factors (PyMuPDF rendering dominates)
- No accuracy risk (PyMuPDF = visual fidelity, whitelist = subset constraint)
- Fast to validate (benchmark, commit, move on)

**Phase 2 deferred** because:
- Requires corpus-wide accuracy validation (time-intensive)
- Speedup gains smaller than Phase 1 (10-30% vs 2-12x)
- Config interactions need testing (OEM+PSM+whitelist combinations)

**Phase 3 deferred** because:
- Highest complexity-to-speedup ratio
- Requires new infrastructure (stats tracking, fallback logic, memory management)
- Premature optimization if Phase 1+2 achieve target throughput

### Stop Conditions

**Do NOT proceed to Phase 2/3 if:**
- Phase 1 achieves acceptable total runtime for 30K+ corpus (e.g., <24 hours end-to-end)
- Further optimization ROI doesn't justify increased code complexity
- Accuracy drops below 94% baseline (current: 94.9%)

**Benchmark after each phase:**
- Total runtime on representative subset (e.g., 1000 PDFs)
- Per-page OCR latency (avg, p50, p95, p99)
- Accuracy on test corpus (maintain ≥94%)
- Memory usage (peak RSS, avg per worker)

## Performance Profiling Recommendations

### Instrumentation Points (for identifying actual bottlenecks)
1. **PDF rendering time** (per page)
2. **OCR time** (per rotation attempt, per page)
3. **Preprocessing time** (when triggered)
4. **Regex extraction time** (negligible, but measure)
5. **Rotation attempts per page** (for smart reordering heuristic)
6. **Worker utilization** (idle time, queue depth)

### Profiling Tools
- **cProfile** for function-level hotspots
- **memory_profiler** for memory leak detection
- **py-spy** for sampling profiler (low overhead)
- **psutil** for per-worker CPU/memory tracking

### Key Metrics to Track
| Metric | Target | Rationale |
|--------|--------|-----------|
| **Pages/second/worker** | 5-10 pps | Tesseract <1s/page at 300 DPI + rendering overhead |
| **Worker CPU utilization** | >85% | Low util = I/O bottleneck or queue starvation |
| **Memory per worker** | <500MB | PyMuPDF + PIL + OpenCV overhead |
| **Rendering vs OCR ratio** | 1:3 to 1:5 | OCR should dominate (4 rotation attempts) |

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
- [Tesseract Traineddata Files for Version 4.00+](https://tesseract-ocr.github.io/tessdoc/Data-Files.html)

### DPI & Image Quality Best Practices
- [Best Practices - OCR @ Pitt](https://pitt.libguides.com/ocr/bestpractices)
- [Image Quality and Resolution for OCR results](https://knowledge.broadcom.com/external/article/254861/image-quality-and-resolution-for-ocr-res.html)
- [Planning and Executing a Successful OCR project - Penn State](https://guides.libraries.psu.edu/c.php?g=1202269&p=8791865)
- [OCR best practices - Document Engine - Nutrient](https://www.nutrient.io/guides/document-engine/ocr/best-practices/)
- [PyMuPDF Pixmap and Image Processing](https://pymupdf.readthedocs.io/en/latest/pixmap.html)
- [PyMuPDF Images Documentation](https://pymupdf.readthedocs.io/en/latest/recipes-images.html)

### Rotation Detection & Alternatives
- [The Best Tesseract OCR Alternatives in 2026 - Klippa](https://www.klippa.com/en/blog/information/the-best-alternative-to-tesseract/)
- [PaddleOCR vs Tesseract: Which is the best open source OCR?](https://www.koncile.ai/en/ressources/paddleocr-analyse-avantages-alternatives-open-source)
- [Seeing Straight: Document Orientation Detection for Efficient OCR](https://arxiv.org/abs/2511.04161)
- [Correcting Text Orientation with Tesseract and Python](https://pyimagesearch.com/2022/01/31/correcting-text-orientation-with-tesseract-and-python/)

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
- [Trenton3983: Enhancing OCR Accuracy with OpenCV and PyTesseract](https://trenton3983.github.io/posts/ocr-image-processing-pytesseract-cv2/)
- [OpenCV vs Pillow for Image Processing](https://primeprogram.medium.com/opencv-vs-pillow-which-is-better-for-image-processing-93f68ab81137)

### Batch Processing & Caching Strategies
- [OCR Batch Workflows: Scalable Text Extraction with ZenML](https://www.zenml.io/blog/ocr-batch-workflows-scalable-text-extraction-with-zenml)
- [Claude Cost Optimization 2026: Batch API and Prompt Caching](https://pecollective.com/tools/claude-pricing-guide/)
- [Batch OCR Automation: High-Volume Document Processing Lifehacks](https://mmaseis.com/batch-ocr-processing-for-documents-lifehacks/)

### Early Termination & Confidence Thresholds
- [On optimal stopping strategies for text recognition in a video stream](https://link.springer.com/article/10.1007/s10032-019-00333-0)
- [AI for Enterprise Document Processing OCR: 2026 Guide](https://www.stackai.com/insights/ai-for-enterprise-document-processing-ocr-end-to-end-workflow-best-practices-and-2026-guide)
- [Understanding Confidence Threshold in AI Systems](https://www.llamaindex.ai/glossary/what-is-confidence-threshold)

### 2026 OCR Landscape & Trends
- [OCR 2026: Everything You Need to Know, Trends, Tools & Tips](https://www.makoletdigimarket.com/stop-retyping-how-ocr-in-2026-actually-works-and-where-its-going/)
- [OCR Accuracy Benchmarks: The 2026 Digital Transformation Revolution](https://medium.com/@info_59976/ocr-accuracy-benchmarks-the-2026-digital-transformation-revolution-2f7095c2696f)
- [The Definitive Guide to OCR in 2026: From Pipelines to VLMs](https://slavadubrov.github.io/blog/2026/03/04/the-definitive-guide-to-ocr-in-2026-from-pipelines-to-vlms/)
