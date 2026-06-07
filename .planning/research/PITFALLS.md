# Performance Optimization Pitfalls

**Domain:** Adding performance optimizations to existing OCR batch pipeline
**Researched:** 2026-06-07
**Context:** v1.2 milestone adding performance optimizations to v1.1 baseline (94.9% accuracy, 230 tests passing)

## Executive Summary

Performance optimizations introduce subtle behavioral changes that can silently degrade accuracy while improving throughput. The critical risk is **trading proven 94.9% accuracy for speed gains** without detecting the regression until after processing thousands of files. PyMuPDF migration, Tesseract configuration changes, DPI reduction, and parallelism tuning all have accuracy cliffs where small parameter changes cause large quality drops. The existing checkpoint/resume system and test suite must remain compatible, and Windows 'spawn' mode multiprocessing adds platform-specific complexity.

**Most dangerous pitfall:** PyMuPDF rendering differences that look visually identical but produce different OCR results downstream (detected only through accuracy measurement, not visual inspection).

---

## Critical Pitfalls

Mistakes that cause rewrites, major accuracy regressions, or data loss.

### Pitfall 1: PyMuPDF Rendering Differences Breaking Downstream OCR
**What goes wrong:** Images from PyMuPDF's `get_pixmap()` look visually identical to pdf2image output but produce different OCR results. Object detection models and Tesseract behave differently due to subtle PNG compression, color space, or alpha channel differences. **Accuracy can drop 5-10% without any visual warning.**

**Why it happens:**
- PyMuPDF uses different PNG compression parameters (10-20% smaller files)
- Default color space handling differs (RGB vs GRAY vs CMYK)
- Alpha channel behavior differs (`alpha=True` parameter semantics)
- DPI/resolution translation not 1:1 (pdf2image defaults to 200 DPI, PyMuPDF uses scaling matrix)
- CMYK color space PDFs may render incorrectly (MuPDF only supports Gray/RGB/CMYK, requires manual conversion)

**Consequences:**
- Silent accuracy regression (visually correct images, wrong OCR results)
- Preprocessing pipeline fails (OpenCV expects specific color space)
- Rotation detection breaks (different pixel intensities change thresholding behavior)
- Test suite passes visually but accuracy drops on real corpus

**Prevention:**
1. **Mandatory accuracy regression testing**: Run existing test corpus (230 tests + real samples) through PyMuPDF pipeline and compare accuracy metric to 94.9% baseline
2. **Color space normalization**: Explicitly convert to RGB or GRAY after rendering: `pix = page.get_pixmap(colorspace="rgb")` or convert CMYK manually
3. **Match pdf2image DPI exactly**: Use `mat = fitz.Matrix(dpi/72, dpi/72)` then `page.get_pixmap(matrix=mat)` to replicate 300 DPI behavior
4. **Disable alpha channel initially**: Use `alpha=False` (default) to match pdf2image's non-transparent output
5. **A/B testing on sample set**: Process 100 random PDFs with both pipelines, diff the OCR outputs, investigate any differences before full migration

**Detection:**
- Accuracy metric drops below 94.9% on existing test corpus
- Preprocessing failures increase (color space conversion errors)
- Rotation detection success rate changes
- Different character confusion patterns (O/0, I/1, S/5 ratios shift)

**Phase assignment:** Phase 1 (PDF rendering migration) — must validate before proceeding to Phase 2

**Sources:**
- [How to match PyMuPdf output to pdf2image output? · pymupdf/PyMuPDF · Discussion #913](https://github.com/pymupdf/PyMuPDF/discussions/913)
- [PyMuPDF Colorspace documentation](https://pymupdf.readthedocs.io/en/latest/colorspace.html)
- [Features Comparison - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/about.html)

**Confidence:** HIGH

---

### Pitfall 2: DPI Reduction Below Accuracy Threshold
**What goes wrong:** Reducing rendering DPI from 300 to 200 or 150 to improve speed causes 20%+ accuracy drop on degraded scans. The accuracy cliff is sharp: 300 DPI → 94.9% accuracy, 200 DPI → ~75% accuracy on low-quality scans.

**Why it happens:**
- 300 DPI is the industry minimum for reliable OCR (2026 standard)
- Below 300 DPI, small text and degraded scans lose critical detail
- Tesseract's character recognition models trained on higher-DPI inputs
- Preprocessing (thresholding, denoising) amplifies artifacts at low DPI
- IDs are already small on page (~5 digits) — DPI reduction makes them sub-recognition threshold

**Consequences:**
- Massive accuracy regression on worst-quality scans (the hardest cases drop from 70% → 20%)
- Preprocessing fallback becomes ineffective (can't recover lost detail)
- Per-folder quality statistics show degradation in specific directories
- Campaign reports highlight problem folders that were fine in v1.1

**Prevention:**
1. **Hard minimum of 300 DPI**: Never render below 300 DPI for OCR pipeline
2. **Test on degraded scan corpus**: Validate any DPI changes specifically on low-quality test samples
3. **DPI as tunable parameter**: Allow users to increase DPI (e.g., 400-600) for small text, not decrease below 300
4. **Monitor per-folder accuracy**: Track which folders degrade with DPI changes

**Detection:**
- Overall accuracy drops below 94.9% baseline
- Per-folder statistics show specific directories with accuracy collapse
- Preprocessing fallback success rate increases (more pages need fallback)
- Campaign reports flag more "problem folders"

**Phase assignment:** Phase 1 (PDF rendering migration) — validate before optimizing Tesseract config

**Sources:**
- [OCR Accuracy Explained: How to Improve It](https://www.llamaindex.ai/blog/ocr-accuracy)
- [OCR Accuracy: How Accurate Is OCR Data Extraction in 2026?](https://www.ocrdataextraction.com/accuracy)
- [Enhancing OCR Accuracy in Low-Quality Scans](https://sparkco.ai/blog/enhancing-ocr-accuracy-in-low-quality-scans)

**Confidence:** HIGH

---

### Pitfall 3: Tesseract Config Changes Silent Accuracy Regressions
**What goes wrong:** Changing Tesseract PSM, OEM, or character whitelist to improve speed causes subtle accuracy regressions. Character whitelist (`tessedit_char_whitelist=0123456789`) sometimes **completely ignored** or causes empty output. PSM changes alter segmentation behavior, breaking multi-ID detection. OEM mode changes (legacy vs LSTM) trade speed for accuracy.

**Why it happens:**
- Character whitelist bugs: documented issues where whitelist ignored or returns empty strings (Tesseract GitHub #3759)
- PSM mode mismatches: PSM 6 (default, full page) vs PSM 7 (single line) vs PSM 8 (single word) — wrong mode misses IDs
- OEM mode tradeoffs: Legacy engine (OEM 0) faster but less accurate, LSTM (OEM 1) slower but more accurate
- Config interactions: Some config combinations incompatible (whitelist + certain OEM modes fail)
- Version-specific behavior: Tesseract 4.x vs 5.x handle config differently

**Consequences:**
- Silent character misrecognition (whitelist fails, Tesseract reads letters as digits)
- Empty OCR results on valid pages (whitelist returns empty string bug)
- Multi-ID pages lose IDs (PSM 7/8 too restrictive, only finds first ID)
- Speed improvement with accuracy regression (OEM 0 faster but wrong results)

**Prevention:**
1. **Test config changes on full corpus**: Run 230-test suite + real samples with each config change
2. **Validate whitelist actually works**: Check that output contains only 0-9, no letters, no empty results
3. **Preserve PSM 6 for multi-ID pages**: Only use PSM 7/8 if single-ID-per-page guaranteed (current corpus has multi-ID pages per FEATURES.md)
4. **Stick with OEM 3 (default)**: Avoid legacy engine (OEM 0) unless speed gain worth accuracy risk
5. **Log config parameters in checkpoint**: Track which Tesseract config produced each result for debugging

**Detection:**
- Test suite failures (expected IDs not found)
- Empty results increase (whitelist bug)
- Multi-ID pages report fewer IDs than v1.1
- Character confusion patterns change (letters in output when whitelist should block)

**Phase assignment:** Phase 2 (Tesseract optimization) — requires careful A/B testing

**Sources:**
- [Tesseract misses whitelisted characters · Issue #3759](https://github.com/tesseract-ocr/tesseract/issues/3759)
- [Limiting Characters in Tesseract OCR: Complete Guide to 2026 Best Practices](https://copyprogramming.com/howto/limit-characters-tesseract-is-looking-for)
- [Tesseract Page Segmentation Modes (PSMs) Explained](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/)
- [Tuning Tesseract PSM and OEM for Precise OCR Character Recognition](https://sqlpey.com/python/tesseract-psm-oem-tuning/)

**Confidence:** HIGH

---

### Pitfall 4: Unnecessary Preprocessing Degrading Clean Scans
**What goes wrong:** Applying aggressive preprocessing (adaptive thresholding, morphological operations) to clean scans **reduces accuracy** instead of improving it. Over-preprocessing destroys fine detail, introduces artifacts, and causes Tesseract to misread clear text.

**Why it happens:**
- Current pipeline uses **conditional preprocessing** (fallback only when initial OCR fails)
- Performance optimizations may apply preprocessing unconditionally for "consistency"
- Adaptive thresholding on clean scans creates false edges and noise
- Morphological operations (erosion/dilation) distort character shapes on high-quality images
- Gaussian blur on sharp scans loses detail

**Consequences:**
- Accuracy drops 5-10% on clean scans (the majority of corpus)
- Best-case performance degrades to improve worst-case (net negative)
- Per-folder statistics show clean folders regressing
- Test suite failures on previously-passing clean samples

**Prevention:**
1. **Preserve conditional preprocessing**: Keep v1.1 behavior (preprocess only on OCR failure)
2. **Test preprocessing on clean samples**: Validate that clean scans maintain 94.9%+ accuracy
3. **Separate clean vs degraded test sets**: Track accuracy separately for each quality tier
4. **Profile preprocessing overhead**: Measure if conditional preprocessing is actually slower (likely not)

**Detection:**
- Accuracy drops on clean scans (test suite failures)
- Per-folder statistics show clean folders regressing
- Visual inspection shows artifacts (false edges, character distortion)

**Phase assignment:** Phase 2/3 (Tesseract/preprocessing optimization) — preserve existing behavior

**Sources:**
- [Preprocessing Images to Improve OCR & DarkShield Results - IRI](https://www.iri.com/blog/data-protection/preprocessing-images-for-ocr-darkshield/)
- [Improve OCR accuracy using advanced preprocessing techniques](https://www.nitorinfotech.com/blog/improve-ocr-accuracy-using-advanced-preprocessing-techniques/)
- [PreP-OCR: A Complete Pipeline for Document Image Restoration and Enhanced OCR Accuracy](https://arxiv.org/html/2505.20429v1)

**Confidence:** MEDIUM (based on general preprocessing best practices, not project-specific data)

---

### Pitfall 5: Rotation Strategy Changes Breaking Multi-ID Pages
**What goes wrong:** Optimizing rotation strategy to reduce OCR passes (from 4 rotations to 2, or using OSD auto-detect) causes multi-ID pages to miss IDs. Different IDs on same page may require different rotations. OSD auto-detect is **unreliable** (fails 20% of time per Tesseract #4426).

**Why it happens:**
- Current multi-rotation strategy: try 90°, 270°, 0°, 180° until regex validates `\d{5}`
- Optimization attempts: Use OSD to detect rotation once, skip other angles
- OSD unreliability: Tesseract 5.3.1 OSD randomly fails ~20% of time on same input
- Multi-ID pages: If page has IDs at 90° and 270°, single rotation detection misses one
- Regex validation is the **reliable signal** — OSD is not

**Consequences:**
- IDs missed on multi-ID pages (only find first ID, skip others)
- Accuracy drops on rotated pages (OSD guesses wrong, skips correct rotation)
- Test suite failures on multi-ID test cases
- Campaign reports show increased "no ID found" pages

**Prevention:**
1. **Keep 4-rotation strategy**: Multi-rotation with regex validation is robust
2. **Avoid OSD for initial detection**: OSD documented as unreliable (Tesseract #4426)
3. **Early-exit on regex match**: Once `\d{5}` found, stop trying rotations (already implemented?)
4. **Profile actual rotation overhead**: 4 OCR passes on 5-digit IDs may be faster than OSD + 1 pass
5. **Test multi-ID pages specifically**: Validate any rotation changes on multi-ID test corpus

**Detection:**
- Multi-ID test cases fail (expected 2+ IDs, found only 1)
- "No ID found" rate increases on rotated pages
- Per-folder statistics show rotation detection failures

**Phase assignment:** Phase 3 (Rotation optimization) — risky change, requires thorough testing

**Sources:**
- [Poor Rotation / Layout detection · Issue #4426](https://github.com/tesseract-ocr/tesseract/issues/4426)
- [Page Segmentation Mode 0 -- Orientation and script detection (OSD) only Failed · Issue #202](https://github.com/tesseract-ocr/tesseract/issues/202)
- [OSD with --psm 0 creates wrong result in latest version · Issue #1926](https://github.com/tesseract-ocr/tesseract/issues/1926)

**Confidence:** HIGH

---

### Pitfall 6: Checkpoint Format Incompatibility Breaking Resume
**What goes wrong:** Changes to internal data structures (PDF renderer, OCR results format) break checkpoint/resume compatibility. Users lose partial progress when upgrading from v1.1 to v1.2 mid-campaign.

**Why it happens:**
- v1.1 checkpoint format assumes pdf2image behavior (specific metadata)
- PyMuPDF migration may change image metadata stored in checkpoint
- Config changes (Tesseract PSM/OEM) may require re-processing to maintain consistency
- JSON schema changes without migration path

**Consequences:**
- Checkpoint files from v1.1 unreadable in v1.2 (schema mismatch)
- Users forced to restart 30K-file campaigns from scratch
- Data loss if mid-campaign upgrade attempted
- Corruption if v1.2 writes to v1.1 checkpoint file

**Prevention:**
1. **Version checkpoints**: Add `"version": "1.2"` to checkpoint JSON schema
2. **Graceful migration**: Detect v1.1 checkpoints, either migrate or warn user to finish campaign first
3. **Schema compatibility testing**: Load v1.1 checkpoints in v1.2 code, verify no crashes
4. **Separate checkpoint files per version**: Use `campaign_state_v1.2.json` instead of overwriting `campaign_state.json`
5. **Document upgrade path**: In README, warn users to complete in-progress campaigns before upgrading

**Detection:**
- JSON decode errors when loading checkpoint
- KeyError/AttributeError when accessing checkpoint fields
- Corrupted checkpoint files (partial writes during migration)

**Phase assignment:** Phase 1 (PyMuPDF migration) — validate checkpoint compatibility before release

**Sources:**
- [Backward Compatibility in Schema Evolution: Guide](https://www.dataexpert.io/blog/backward-compatibility-schema-evolution-guide)
- [Schema Evolution & Compatibility Types | Confluent Documentation](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)
- [How to Implement API Versioning and Backward Compatibility](https://technori.com/2026/03/25054-how-to-implement-api-versioning-and-backward-compatibility/ava/)

**Confidence:** MEDIUM (general software engineering risk, not OCR-specific)

---

## Moderate Pitfalls

Mistakes that cause performance degradation, increased failures, or maintenance burden.

### Pitfall 7: Hybrid CPU Over-Subscription on Windows
**What goes wrong:** Setting worker pool to `cpu_count()` (20 cores) on hybrid CPU (8 P-cores + 12 E-cores) causes **worse** performance than fewer workers. E-cores slower for OCR workload, process scheduler thrashes, memory bandwidth saturated.

**Why it happens:**
- Windows 10 scheduler may not distinguish P-cores vs E-cores optimally
- E-cores are 40-60% slower for CPU-intensive tasks (OCR)
- 20 workers contend for memory bandwidth (PDF loading, image buffers)
- Windows 'spawn' mode creates fresh Python interpreter per worker (higher overhead than Linux 'fork')
- Context switching overhead increases with worker count

**Consequences:**
- Total throughput **decreases** with more workers (counterintuitive)
- Memory pressure increases (20 concurrent PDF loads)
- System becomes unresponsive (scheduler thrashing)
- Workers spend more time in I/O wait than processing

**Prevention:**
1. **Benchmark worker counts**: Test 4, 8, 12, 16, 20 workers, measure total throughput
2. **Start with P-core count**: Use 8 workers (P-core count) as baseline
3. **Profile CPU utilization**: Check if P-cores at 100% and E-cores idle (indicates scheduler issue)
4. **Add `--workers` CLI flag**: Let users tune based on their CPU architecture
5. **Document optimal setting**: In README, recommend 8-12 workers for hybrid CPUs

**Detection:**
- Throughput decreases when workers increase from 8 → 20
- Task Manager shows high E-core usage, low P-core usage (scheduler misallocating)
- Memory usage spikes (>16GB with 20 workers)
- System responsiveness degrades

**Phase assignment:** Phase 4 (Parallelism tuning) — requires benchmarking on target hardware

**Sources:**
- [What Is Performance Hybrid Architecture?](https://www.intel.com/content/www/us/en/support/articles/000091896/processors.html)
- [Hybrid CPU Performance on Windows 10 and 11 – Alois Kraus](https://aloiskraus.wordpress.com/2024/02/08/hybrid-cpu-performance-on-windows-10-and-11/)
- [CPU Efficiency Cores vs Performance Cores: Why Are They Different?](https://www.corsair.com/us/en/explorer/gamer/gaming-pcs/cpu-efficiency-cores-vs-performance-cores-why-are-they-different/)

**Confidence:** HIGH

---

### Pitfall 8: Memory Leaks from Worker Pool Not Closed Properly
**What goes wrong:** Failing to close multiprocessing.Pool with context manager or explicit `close()`/`terminate()` causes memory to accumulate unbounded until OOM crash mid-campaign.

**Why it happens:**
- `Pool._cache` holds MapResults indefinitely if pool not closed
- Workers hold references to processed images/data
- Garbage collector cannot reclaim memory until pool terminated
- Historical Python bug (fixed but behavior depends on proper usage)

**Consequences:**
- Memory usage grows linearly with processed files (instead of staying constant)
- OOM crash after thousands of files (campaign fails mid-run)
- Checkpoint saves before crash, but restart hits same issue
- System swap thrashing (Windows page file exhaustion)

**Prevention:**
1. **Use context manager**: `with Pool(processes=N) as pool:` (auto-cleanup)
2. **Explicit cleanup**: If not using context manager, call `pool.close()` and `pool.join()` in `finally:` block
3. **Worker recycling**: Use `maxtasksperchild=100` to recycle workers every 100 PDFs (prevents worker-level leaks)
4. **Monitor memory growth**: Profile memory usage over 1000 files, verify it plateaus
5. **Graceful shutdown**: Ensure Ctrl+C handler closes pool before exit

**Detection:**
- Memory usage grows linearly with processed files (Task Manager)
- OOM crash after N thousand files (N depends on RAM)
- Workers not terminating after campaign complete
- Python process memory >16GB (should plateau around 2-4GB)

**Phase assignment:** Phase 1/4 (Parallelism implementation) — validate before scaling to full corpus

**Sources:**
- [Memory Leak in Python multiprocessing.Pool - KK's Blog](https://fromkk.com/posts/memory-leak-in-python-multiprocessing-dot-pool/)
- [Issue 34172: multiprocessing.Pool and ThreadPool leak resources after being deleted](https://bugs.python.org/issue34172)
- [How Do I Limit Memory Consumption While Using Python Multiprocessing?](https://techbullion.com/how-do-i-limit-memory-consumption-while-using-python-multiprocessing/)
- [Top Strategies to Manage High Memory Usage with Python Multiprocessing](https://sqlpey.com/python/top-strategies-to-manage-high-memory-usage-with-python-multiprocessing/)

**Confidence:** HIGH

---

### Pitfall 9: Windows Spawn Mode Pickling Failures
**What goes wrong:** Windows 'spawn' mode requires all worker function arguments to be picklable. Passing unpicklable objects (lambdas, local functions, open file handles, compiled regexes in closures) causes cryptic PicklingError crashes.

**Why it happens:**
- Windows uses 'spawn' start method (not 'fork') — fresh interpreter per worker
- All function arguments serialized via pickle and sent to worker process
- Lambdas, nested functions, closures not picklable
- Compiled regex patterns (`re.compile()`) picklable only if module-level
- Open file handles (PDFs) not picklable

**Consequences:**
- PicklingError crashes at pool startup or task submission
- Cryptic error messages (doesn't clearly explain what's not picklable)
- Code works in testing (small scale) but fails at production scale
- Hard to debug (depends on internal structure of passed objects)

**Prevention:**
1. **Module-level functions only**: Define worker functions at module level, not nested
2. **Module-level regex**: `PRECEDE_ID_REGEX = re.compile(r'\d{5}')` at module level
3. **Pass paths not handles**: Pass `str` path to PDF, open inside worker function
4. **Avoid closures**: Don't capture variables from outer scope in worker functions
5. **Test pickling explicitly**: `pickle.dumps(worker_func)` to verify picklability before pool.map()

**Detection:**
- PicklingError at pool.map() call
- `AttributeError: Can't pickle local object` errors
- Workers fail to start (pool.map() hangs then errors)

**Phase assignment:** Phase 1/4 (Parallelism implementation) — Windows-specific constraint

**Sources:**
- [Fix: Python multiprocessing Not Working (freeze_support, Pickle Errors, Zombie Processes)](https://fixdevs.com/blog/python-multiprocessing-not-working/)
- [Python Multiprocessing, Revisited: Fork vs Spawn](https://medium.com/@Nexumo_/python-multiprocessing-revisited-fork-vs-spawn-5b9216fd5710)
- [multiprocessing — Process-based parallelism](https://docs.python.org/3/library/multiprocessing.html)

**Confidence:** HIGH

---

### Pitfall 10: Benchmark Invalidation from Test Corpus Drift
**What goes wrong:** Performance optimizations benchmarked on small test set (100 PDFs, 230 tests) show speed gains, but full corpus (30,429 PDFs) shows accuracy regression or no speed gain. Test set not representative of worst-case files.

**Why it happens:**
- Test corpus selected for coverage, not difficulty (clean scans over-represented)
- Worst-quality scans under-represented in test set (long tail of problem files)
- Small test set averages hide worst-case behavior
- Performance improvements measured on best-case, regression hits worst-case
- Per-folder quality variation not reflected in test corpus

**Consequences:**
- Optimizations validated on tests but fail on real corpus
- Accuracy regressions discovered after processing thousands of real files
- Campaign reports show new problem folders not in test set
- User frustration from "tested and validated" changes failing in production

**Prevention:**
1. **Stratified test corpus**: Include worst-case files (low quality, multi-ID, rotated, degraded)
2. **Per-folder sampling**: Sample from each directory to catch folder-specific issues
3. **Benchmark on realistic scale**: Test on 1000-file subset of real corpus, not just 230-test suite
4. **Track worst-case metrics**: Monitor P95/P99 accuracy, not just average
5. **Staged rollout**: Process 10% of corpus with optimizations, validate accuracy before full run

**Detection:**
- Test suite passes but full corpus accuracy drops
- Campaign reports flag problem folders not in test set
- Per-folder statistics show bimodal distribution (test set clean, real corpus degraded)

**Phase assignment:** Phase 5 (Validation) — requires representative test corpus before release

**Sources:**
- [OCR Accuracy Explained: How to Improve It](https://www.llamaindex.ai/blog/ocr-accuracy)
- [How to Use OCR Testing Images for Accuracy Validation?](https://aimonk.com/how-to-use-ocr-testing-images-accuracy-validation/)

**Confidence:** MEDIUM (general testing best practice, not OCR-specific)

---

## Minor Pitfalls

Small mistakes that cause inefficiency or maintenance burden but not data loss.

### Pitfall 11: Premature Optimization Without Profiling
**What goes wrong:** Optimizing parts of pipeline that aren't bottlenecks (e.g., optimizing JSON writing when 95% of time is OCR). No speed gain, added complexity, maintenance burden.

**Why it happens:**
- Assumptions about bottlenecks without measurement
- "PDF rendering is slow" → optimize rendering, but OCR is actual bottleneck
- Micro-optimizations (list comprehensions, caching) with negligible impact
- Tesseract OCR dominates runtime (likely >90% of total time)

**Consequences:**
- Wasted development time on non-bottlenecks
- Code complexity increases with no throughput gain
- Technical debt from premature abstractions
- Real bottlenecks remain unaddressed

**Prevention:**
1. **Profile first**: Use `cProfile` or manual timing to measure where time spent
2. **80/20 rule**: Optimize the 20% of code that consumes 80% of runtime
3. **Measure impact**: Benchmark before/after each optimization to validate gain
4. **Start with Tesseract**: OCR likely dominates — optimize Tesseract config before anything else

**Detection:**
- Optimization shows <5% speedup on benchmarks
- Profiling reveals time spent elsewhere
- Code reviews flag unnecessary complexity

**Phase assignment:** Phase 5 (Profiling) — should be Phase 0 (before any optimization)

**Sources:**
- General software engineering best practice

**Confidence:** HIGH

---

### Pitfall 12: Logging Overhead in Tight Loops
**What goes wrong:** Adding verbose logging inside per-page OCR loop (e.g., logging every rotation attempt, every image conversion) causes 10-20% slowdown. I/O overhead of logging dominates in tight loops.

**Why it happens:**
- Logging to file on every page processed (30K+ pages × 4 rotations = 120K+ log writes)
- String formatting overhead (`f"Processing {file} page {page}"` computed even if log level disabled)
- Lock contention in multiprocessing (workers serialize on shared log file)

**Consequences:**
- Performance optimization negated by logging overhead
- Log files grow to gigabytes (hard to search)
- Worker contention on log file lock (serializes parallel work)

**Prevention:**
1. **Conditional logging**: Only log at INFO level for major milestones (file start/complete), DEBUG for details
2. **Lazy formatting**: Use `logger.debug("msg %s", var)` not `logger.debug(f"msg {var}")` (formatting skipped if DEBUG disabled)
3. **Batch logging**: Accumulate per-worker stats, log once per file instead of per page
4. **Separate worker logs**: Each worker writes to own log file (no lock contention)

**Detection:**
- Profiling shows significant time in logging calls
- Removing logging improves throughput >5%
- Log file grows faster than processed files

**Phase assignment:** All phases — design decision for instrumentation

**Confidence:** MEDIUM (general performance best practice)

---

### Pitfall 13: Hard-Coded Paths Breaking Cross-System Testing
**What goes wrong:** Hard-coding Tesseract path (`C:\Program Files\Tesseract-OCR\tesseract.exe`) works on dev machine but breaks on test machine or other user systems.

**Why it happens:**
- Tesseract installed in different location per system
- Installers (Windows, Homebrew, apt) use different default paths
- Project constraints say "Tesseract already installed" but not where

**Consequences:**
- Pipeline fails on other systems with cryptic "tesseract not found" error
- CI/CD fails if Tesseract path differs
- Users must edit source code to change path (poor UX)

**Prevention:**
1. **Auto-detect from PATH**: Use `pytesseract.get_tesseract_version()` to check if tesseract in PATH
2. **Config file or CLI flag**: Let users specify `--tesseract-path` if not in PATH
3. **Graceful error message**: If not found, print helpful message: "Tesseract not found. Install from [URL] or use --tesseract-path"
4. **Detect on first run**: Check PATH, if not found, prompt user once and save to config file

**Detection:**
- TesseractNotFoundError on systems where Tesseract not in PATH
- CI/CD failures on fresh containers

**Phase assignment:** All phases — portability concern

**Confidence:** HIGH

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **Phase 1: PyMuPDF Migration** | Rendering differences break downstream OCR | Mandatory accuracy regression testing on full test corpus before proceeding |
| **Phase 1: PyMuPDF Migration** | DPI reduction below 300 causes accuracy cliff | Hard minimum 300 DPI, validate on degraded scans |
| **Phase 1: PyMuPDF Migration** | Checkpoint format incompatibility | Version checkpoints, test v1.1 → v1.2 migration path |
| **Phase 2: Tesseract Optimization** | Character whitelist ignored or returns empty | Validate whitelist works, don't rely on it for critical filtering |
| **Phase 2: Tesseract Optimization** | PSM mode change misses multi-ID pages | Preserve PSM 6, test multi-ID cases |
| **Phase 2: Tesseract Optimization** | Unnecessary preprocessing degrades clean scans | Preserve conditional preprocessing (fallback only) |
| **Phase 3: Rotation Optimization** | OSD auto-detect unreliable (20% failure rate) | Keep 4-rotation strategy with regex validation |
| **Phase 3: Rotation Optimization** | Single rotation detection misses multi-ID pages | Test multi-ID cases specifically |
| **Phase 4: Parallelism Tuning** | Hybrid CPU over-subscription degrades throughput | Benchmark worker counts, start with P-core count (8) |
| **Phase 4: Parallelism Tuning** | Memory leaks from unclosed pools | Use context manager or explicit close(), add maxtasksperchild |
| **Phase 4: Parallelism Tuning** | Windows spawn mode pickling failures | Module-level functions and regexes, pass paths not handles |
| **Phase 5: Profiling/Validation** | Test corpus not representative of worst-case | Stratified sampling from real corpus, track P95/P99 metrics |
| **Phase 5: Profiling/Validation** | Premature optimization without profiling | Profile first, optimize bottlenecks (likely Tesseract OCR) |
| **All Phases** | Logging overhead in tight loops | Conditional logging, lazy formatting, batch stats |

---

## Regression Testing Strategy

To avoid silent accuracy degradation during performance optimization:

### Mandatory Pre-Release Validation

1. **Baseline measurement**: Capture v1.1 accuracy on fixed test corpus (230 tests + 1000-file real sample)
2. **Per-phase validation**: After each phase, re-run full test corpus and compare to baseline
3. **Threshold**: Any accuracy drop >0.5% (94.9% → 94.4%) triggers investigation
4. **Per-folder tracking**: Monitor per-folder statistics to catch directory-specific regressions
5. **Worst-case metrics**: Track P95/P99 accuracy (worst-performing 5% of files), not just average

### Test Corpus Design

- **230 existing tests**: Already pass in v1.1, must pass in v1.2
- **Stratified sampling**: 1000-file sample from real corpus, stratified by folder
- **Quality tiers**: Separate clean scans (>99% OCR confidence) from degraded scans (<70% confidence)
- **Multi-ID pages**: Dedicated test cases for pages with 2+ IDs at different rotations
- **Edge cases**: Blank pages, corrupted PDFs, extremely large files, unusual rotations

### Continuous Validation

- **A/B testing**: Process same 100 files with v1.1 and v1.2, diff outputs
- **Checkpoint compatibility**: Load v1.1 checkpoint in v1.2, verify no schema errors
- **Memory profiling**: Process 1000 files, verify memory plateaus (no leaks)
- **Throughput benchmarking**: Measure files/hour, compare to v1.1 baseline

---

## Quick Reference: Risk Matrix

| Pitfall | Severity | Likelihood | Detection Difficulty | Phase |
|---------|----------|------------|---------------------|-------|
| PyMuPDF rendering differences | **CRITICAL** | High | High (visual inspection fails) | 1 |
| DPI reduction below 300 | **CRITICAL** | Medium | Medium (accuracy drop) | 1 |
| Tesseract config regressions | **CRITICAL** | High | Medium (test suite may miss) | 2 |
| Unnecessary preprocessing | **HIGH** | Medium | Low (test suite catches) | 2-3 |
| Rotation strategy breaking multi-ID | **HIGH** | Medium | Low (test suite catches) | 3 |
| Checkpoint format incompatibility | **HIGH** | Medium | Low (errors on load) | 1 |
| Hybrid CPU over-subscription | **MEDIUM** | High | Low (profiling obvious) | 4 |
| Memory leaks from unclosed pools | **MEDIUM** | Medium | Medium (slow growth) | 1-4 |
| Windows spawn pickling failures | **MEDIUM** | Medium | Low (errors at startup) | 1-4 |
| Non-representative test corpus | **MEDIUM** | High | High (not caught until production) | 5 |
| Premature optimization | **LOW** | High | Low (profiling reveals) | 5 |
| Logging overhead | **LOW** | Medium | Medium (profiling may miss) | All |
| Hard-coded paths | **LOW** | Low | Low (errors on other systems) | All |

---

## Summary

**Most critical risk:** PyMuPDF rendering differences that look identical but break OCR (requires mandatory accuracy regression testing before migration).

**Second critical risk:** DPI reduction below 300 DPI causing 20%+ accuracy cliff on degraded scans (hard minimum 300 DPI).

**Third critical risk:** Tesseract config changes (PSM, OEM, whitelist) silently regressing accuracy (requires A/B testing on full corpus).

**Platform risk:** Windows 'spawn' mode multiprocessing (pickling constraints, hybrid CPU scheduler behavior).

**Validation requirement:** Track accuracy metrics per phase, compare to 94.9% baseline, reject changes that regress >0.5%.

**Test corpus gap:** Existing 230 tests may not represent worst-case files — add stratified sampling from real corpus.

---

## Sources

### PyMuPDF Migration
- [How to match PyMuPdf output to pdf2image output? · pymupdf/PyMuPDF · Discussion #913](https://github.com/pymupdf/PyMuPDF/discussions/913)
- [Features Comparison - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/about.html)
- [PyMuPDF Colorspace documentation](https://pymupdf.readthedocs.io/en/latest/colorspace.html)
- [Battle of the PDF Titans: Apache Tika, PyMuPDF, pdfplumber, pdf2image, and Textract](https://openwebtech.com/battle-of-the-pdf-titans-apache-tika-pymupdf-pdfplumber-pdf2image-and-textract/)

### OCR Accuracy and DPI
- [OCR Accuracy Explained: How to Improve It](https://www.llamaindex.ai/blog/ocr-accuracy)
- [OCR Accuracy: How Accurate Is OCR Data Extraction in 2026?](https://www.ocrdataextraction.com/accuracy)
- [Enhancing OCR Accuracy in Low-Quality Scans](https://sparkco.ai/blog/enhancing-ocr-accuracy-in-low-quality-scans)
- [OCR Accuracy Benchmarks: The 2026 Digital Transformation Revolution](https://medium.com/@info_59976/ocr-accuracy-benchmarks-the-2026-digital-transformation-revolution-2f7095c2696f)

### Tesseract Configuration
- [Tesseract misses whitelisted characters · Issue #3759](https://github.com/tesseract-ocr/tesseract/issues/3759)
- [Limiting Characters in Tesseract OCR: Complete Guide to 2026 Best Practices](https://copyprogramming.com/howto/limit-characters-tesseract-is-looking-for)
- [Tesseract Page Segmentation Modes (PSMs) Explained](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/)
- [Tuning Tesseract PSM and OEM for Precise OCR Character Recognition](https://sqlpey.com/python/tesseract-psm-oem-tuning/)
- [Poor Rotation / Layout detection · Issue #4426](https://github.com/tesseract-ocr/tesseract/issues/4426)

### Image Preprocessing
- [Preprocessing Images to Improve OCR & DarkShield Results - IRI](https://www.iri.com/blog/data-protection/preprocessing-images-for-ocr-darkshield/)
- [Improve OCR accuracy using advanced preprocessing techniques](https://www.nitorinfotech.com/blog/improve-ocr-accuracy-using-advanced-preprocessing-techniques/)
- [PreP-OCR: A Complete Pipeline for Document Image Restoration and Enhanced OCR Accuracy](https://arxiv.org/html/2505.20429v1)

### Multiprocessing and Windows
- [Memory Leak in Python multiprocessing.Pool - KK's Blog](https://fromkk.com/posts/memory-leak-in-python-multiprocessing-dot-pool/)
- [Issue 34172: multiprocessing.Pool and ThreadPool leak resources after being deleted](https://bugs.python.org/issue34172)
- [Fix: Python multiprocessing Not Working (freeze_support, Pickle Errors, Zombie Processes)](https://fixdevs.com/blog/python-multiprocessing-not-working/)
- [Python Multiprocessing, Revisited: Fork vs Spawn](https://medium.com/@Nexumo_/python-multiprocessing-revisited-fork-vs-spawn-5b9216fd5710)
- [Top Strategies to Manage High Memory Usage with Python Multiprocessing](https://sqlpey.com/python/top-strategies-to-manage-high-memory-usage-with-python-multiprocessing/)

### Hybrid CPU Architecture
- [What Is Performance Hybrid Architecture?](https://www.intel.com/content/www/us/en/support/articles/000091896/processors.html)
- [Hybrid CPU Performance on Windows 10 and 11 – Alois Kraus](https://aloiskraus.wordpress.com/2024/02/08/hybrid-cpu-performance-on-windows-10-and-11/)
- [CPU Efficiency Cores vs Performance Cores: Why Are They Different?](https://www.corsair.com/us/en/explorer/gamer/gaming-pcs/cpu-efficiency-cores-vs-performance-cores-why-are-they-different/)

### Testing and Validation
- [How to Use OCR Testing Images for Accuracy Validation?](https://aimonk.com/how-to-use-ocr-testing-images-accuracy-validation/)
- [Backward Compatibility in Schema Evolution: Guide](https://www.dataexpert.io/blog/backward-compatibility-schema-evolution-guide)
- [Batch OCR Automation: High-Volume Document Processing Lifehacks](https://mmaseis.com/batch-ocr-processing-for-documents-lifehacks/)
