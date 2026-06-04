# Project Research Summary

**Project:** Precede OCR — PDF ID Scanner & Mapper
**Domain:** Batch PDF OCR with numeric ID extraction (30K+ PDFs, Windows)
**Researched:** 2026-06-04
**Confidence:** HIGH

## Executive Summary

This project requires building a high-volume batch OCR pipeline to extract 5-digit numeric IDs from ~30,429 multi-page, potentially rotated PDFs on Windows. Expert practitioners build such systems using a **producer-consumer architecture** with clear stage separation: file discovery, PDF-to-image conversion, OCR processing with multi-rotation handling, ID extraction via regex validation, and incremental result aggregation. The technology stack is mature and well-documented: Tesseract 5.x for OCR (already installed), pdf2image/Poppler for conversion, Python multiprocessing for parallelization, and pandas for structured output.

The recommended approach is to **build incrementally**: start with a single-file serial pipeline to validate OCR accuracy and ID extraction logic, then add multi-rotation support (0/90/180/270 degrees) to handle rotated IDs, followed by multiprocessing parallelization to handle the 30K scale, then error handling with checkpointing, and finally conditional preprocessing as a fallback for low-quality scans. This order validates core logic before adding complexity and matches natural dependency chains discovered in architecture research.

The key risks are Windows-specific: memory exhaustion from pdf2image loading all pages into RAM (must use `output_folder` + `paths_only=True`), Windows multiprocessing spawn overhead requiring careful worker initialization, and Tesseract's memory leak on Windows requiring process recycling every 100-500 files. These are **critical pitfalls** that cause silent failures and wasted processing time if not addressed from Phase 1. Additional risks include incorrect DPI (must be 300+), wrong PSM mode for isolated numbers (use PSM 7), and unreliable OSD rotation detection (brute-force all 4 rotations instead). Mitigation strategies are well-documented and proven effective.

## Key Findings

### Recommended Stack

The stack leverages mature, CPU-focused tools optimized for Windows batch processing. Tesseract 5.5.2 with LSTM neural networks provides the best accuracy-to-speed ratio for clean scanned documents (sub-1-second per page), avoiding GPU dependencies entirely. The combination of Pillow for simple operations and OpenCV for fallback preprocessing balances simplicity with power — use Pillow first, only invoke OpenCV when initial OCR fails.

**Core technologies:**
- **Tesseract 5.5.2 + pytesseract 0.3.13**: Industry-standard OCR with proven numeric ID extraction; already installed; CPU-optimized for this use case
- **pdf2image 1.17.0 + Poppler**: De facto standard for PDF-to-image conversion; critical `paths_only` parameter prevents memory exhaustion at scale
- **Pillow 12.2.0**: Primary preprocessing (grayscale, rotation) with simple API; sufficient for 80%+ of high-quality scans
- **OpenCV 4.13.0.92**: Fallback preprocessing only (adaptive thresholding, denoising) when Pillow+OCR fails; avoid over-processing
- **multiprocessing.Pool / concurrent.futures**: Windows spawn-based parallelization; mandatory for 30K scale; ProcessPoolExecutor recommended for cleaner API
- **tqdm 4.67.3**: Real-time progress tracking with ETA; essential UX for long-running batch; integrates with multiprocessing via `process_map()`
- **pandas 3.0.3**: Clean CSV/JSON export with proper handling of missing values and encoding edge cases

**Version confidence:** HIGH — all versions are latest stable as of 2026-06-04, verified against PyPI official pages and release notes.

### Expected Features

Research identified 13 table stakes features that must all work together for MVP, plus 14 differentiators that can be added incrementally based on observed bottlenecks. Anti-features research confirms this is a CLI-only, local-processing, one-shot batch job — no GUI, no cloud services, no database backend.

**Must have (table stakes):**
- **Recursive PDF discovery** — pathlib.rglob() for nested directories
- **Multi-page PDF handling** — pdf2image page iteration at 300 DPI
- **OCR text extraction** — pytesseract with proper PSM mode
- **Rotation handling** — try all 4 rotations (0/90/180/270) with early exit on match
- **Pattern validation** — regex `\d{5}` with boundaries to distinguish IDs from noise
- **Page-level mapping** — track (filename, page_num, id, rotation) for lookup use case
- **Missing ID detection** — flag pages with no matches (don't silently skip)
- **Multiple IDs per page** — output all matches, not just first
- **Structured output (CSV + JSON)** — CSV for Excel inspection, JSON for programmatic lookup
- **Parallel processing** — mandatory at 30K+ scale (8 cores = 20 hours vs. 166 hours serial)
- **Error handling** — isolate failures per file with structured logging and dead-letter queue
- **Progress visibility** — tqdm progress bars with percentage and ETA
- **Basic logging** — file-level success/failure for debugging and audit trail

**Should have (competitive):**
- **Image preprocessing pipeline** — conditional fallback (grayscale → threshold → denoise) for degraded scans; improves accuracy from 85-92% to 95-98%
- **OCR confidence scoring** — flag low-confidence results (<60) for manual review or retry with preprocessing
- **Resume capability** — checkpoint file tracking processed PDFs; critical for long batches that may crash
- **Character normalization** — post-OCR mapping (O→0, I/l→1, S→5) to fix common OCR confusions
- **Batch statistics report** — final summary of success rate, failures, total IDs found, average processing time
- **DPI optimization** — explicitly set 300 DPI (don't rely on defaults); consider 400 DPI for poor scans
- **PSM mode optimization** — start with PSM 7 (single line), fall back to PSM 6 (uniform block) if "Precede" label present

**Defer (v2+):**
- **Region of interest (ROI) detection** — use "Precede" cursive text as anchor to narrow OCR region; complex but reduces false positives
- **Duplicate ID detection** — post-processing check for same ID across multiple pages
- **Adaptive preprocessing** — automatically detect low-quality scans and apply preprocessing only when needed (high complexity)

**Complexity estimate:** 5-7 days for MVP table stakes, 8-12 days with key differentiators.

### Architecture Approach

Batch PDF OCR pipelines follow a **producer-consumer pattern** with stage separation for independent optimization and failure isolation. On Windows, multiprocessing uses "spawn" (not "fork"), requiring all data to be pickled and sent to child processes — this mandates passing file paths instead of Image objects and using worker initialization for heavy configuration. Build order is critical: validate single-file serial flow first (proves OCR logic works), then add multi-rotation (core to accuracy for rotated IDs), then parallelization (handles scale), then error handling (resilience at scale), and finally conditional preprocessing as fallback (avoid over-processing).

**Major components:**
1. **File Discovery** — pathlib recursive scan producing list of PDF paths; fast, no parallelization needed
2. **Page Extractor** — pdf2image converts PDFs to images at 300 DPI; use `output_folder` + `paths_only=True` to prevent memory exhaustion; parallelize at PDF level, not page level
3. **OCR Processor** — pytesseract with multi-rotation (0/90/180/270) and early exit on valid ID match; slowest stage, CPU-bound, parallelizes well
4. **Preprocessing Pipeline (conditional)** — Pillow grayscale + OpenCV threshold/denoise only when multi-rotation OCR finds no ID; fallback layer, not primary path
5. **ID Extractor** — regex validation with boundaries and optional context check (near "Precede" keyword); fast in-process filter, no parallelization
6. **Result Aggregator** — pandas incremental CSV writes (append mode) + final JSON output; serial writes prevent file corruption
7. **Progress Tracker** — tqdm with `process_map()` for automatic multiprocessing-aware progress bars
8. **Error Handler** — try-catch per PDF with structured logging, retry logic (exponential backoff, max 3 attempts), dead-letter queue for persistent failures

**Key architectural patterns:**
- **Multi-rotation strategy:** Brute-force all 4 rotations with regex validation instead of unreliable Tesseract OSD (OSD fails with sparse text like 5-digit IDs)
- **Conditional preprocessing:** Apply expensive preprocessing (20-50ms per page) only when needed; saves 1.7-4.2 hours across 300K pages
- **Process recycling:** Use `maxtasksperchild=100` to restart workers and release Tesseract's leaked memory on Windows
- **Coarse-grained parallelization:** Parallelize at PDF level (each worker handles one PDF end-to-end), not page level (IPC overhead on Windows spawn)

### Critical Pitfalls

These are ranked by severity and research confidence (all HIGH confidence from official docs + verified issues).

1. **Memory exhaustion from pdf2image without output folders** — Default behavior loads all PDF pages into RAM; at 30K+ PDFs with 10-50MB per page, OS kills process mid-batch. **Prevention:** Always use `convert_from_path(pdf, output_folder='/tmp', paths_only=True)` to write to disk and return paths instead of Image objects. Clean up temp files after each PDF. Critical for Phase 1.

2. **Windows multiprocessing spawn overhead with large pickle objects** — Passing Image objects or config dicts to workers causes 10x slowdown; Windows pickles everything for each task. **Prevention:** Pass file paths (strings) only; use `Pool(initializer=worker_init)` to load heavy objects once per worker; set `OMP_THREAD_LIMIT=1` for pytesseract. Critical for Phase 4 parallelization.

3. **Tesseract RAM not released on Windows** — Documented memory leak in Tesseract 4.x/5.x on Windows where RAM accumulates across OCR operations until crash. **Prevention:** Process in batches of 100-500 files with `maxtasksperchild=100` to automatically recycle workers and release memory. Monitor process memory and force restart when threshold exceeded. Critical for Phase 3 and 4.

4. **Insufficient image resolution for 5-digit IDs** — Default DPI (72-150) makes digits too small (<10 pixels x-height); Tesseract noise-filters them out or misrecognizes. **Prevention:** Explicitly set `dpi=300` in pdf2image (minimum for reliable digit recognition); verify converted image dimensions; consider DPI=400 for poor-quality scans. Critical for Phase 1.

5. **Wrong PSM mode for isolated 5-digit IDs** — Default PSM 3 (full page segmentation) returns "Empty page!!" on images with isolated numbers; Tesseract expects paragraphs, not sparse single-line data. **Prevention:** Use PSM 7 (single line) for isolated IDs: `config='--psm 7 --oem 3'`; fall back to PSM 6 if "Precede" label present. Test multiple PSM modes if initial attempt fails. Critical for Phase 3.

6. **Unreliable Tesseract OSD for rotation detection** — OSD (PSM 0) fails with sparse text, reports wrong orientations, or crashes with "Too few characters." **Prevention:** Skip OSD entirely; brute-force all 4 rotations (0/90/180/270) with regex validation to determine correct orientation; rotation is fast (just data rearrangement); use confidence scores from `image_to_data()` to pick best result. Critical for Phase 2.

7. **Digit confusion without character normalization** — OCR misreads O→0, I/l→1, S→5, B→8 even with whitelist config (LSTM engine sometimes ignores `tessedit_char_whitelist`). **Prevention:** Post-OCR normalization mapping + regex validation; log original output before normalization; use OEM 3 (combined legacy + LSTM) for better whitelist support. Critical for Phase 3.

8. **File handle leaks leading to resource exhaustion** — Opening files without explicit closure causes handles to accumulate; Windows hits per-process limit, preventing new files from opening. **Prevention:** Always use context managers (`with Image.open() as img:`); call `gc.collect()` periodically (every 100 files); monitor open handles. Critical for Phase 1 and must audit all workers in Phase 4.

## Implications for Roadmap

Based on combined research, the natural build order follows **feature dependencies and risk mitigation priorities**. Architecture research shows single-file serial flow must be validated first (proves OCR logic), then rotation handling (core to accuracy), then parallelization (enables scale), then error handling (resilience), and finally preprocessing (quality fallback). Pitfalls research confirms Phase 1 must address memory, file handles, and DPI immediately to prevent silent failures.

### Phase 1: Foundation — Single-File OCR Pipeline
**Rationale:** Validate entire pipeline end-to-end with one PDF before scaling. Catch integration issues early (Tesseract not found, Poppler missing). Prove OCR → ID extraction logic works without multiprocessing debugging overhead. Architecture research confirms this is mandatory foundation.

**Delivers:** Working single-file processor that outputs correct IDs with page numbers to CSV.

**Addresses (table stakes):**
- Recursive PDF discovery (single file for testing)
- Multi-page PDF handling (pdf2image wrapper)
- OCR text extraction (pytesseract wrapper)
- Pattern validation (regex for 5-digit IDs)
- Page-level mapping (filename, page, id tracking)
- Structured output (CSV writer)

**Avoids (critical pitfalls):**
- Memory exhaustion: Use `output_folder` + `paths_only=True` from start
- Insufficient resolution: Explicitly set `dpi=300`
- File handle leaks: Establish context manager patterns
- Wrong PSM mode: Start with PSM 7 research recommendation

**Research flags:** Standard patterns, skip research-phase. Well-documented in pytesseract + pdf2image official docs.

---

### Phase 2: Rotation Handling — Multi-Angle OCR
**Rationale:** IDs are rotated ~90 degrees per project requirements. Architecture research shows multi-rotation is core to accuracy and must be implemented before parallelization to debug rotation logic serially. Features research confirms rotation handling is table stakes. Build before scaling to avoid debugging rotations across multiple workers.

**Delivers:** Single-file processor that correctly extracts IDs from pages at any rotation (0/90/180/270 degrees).

**Implements:**
- Multi-rotation strategy (try all 4 angles with early exit)
- Rotation tracking in output (add `rotation_detected` column)
- Validation with regex after each rotation
- Confidence scoring to pick best result

**Avoids (critical pitfall):**
- Unreliable OSD: Skip Tesseract's PSM 0 rotation detection entirely; use brute-force multi-rotation with regex validation instead

**Uses (from stack):**
- Pillow `Image.rotate()` for 90-degree increments (fast, lossless)
- pytesseract `image_to_data()` for confidence scores

**Research flags:** Standard pattern (rotation handling well-documented). Skip research-phase.

---

### Phase 3: Scale — Parallel Processing
**Rationale:** 30K+ PDFs = 166 hours serial vs. 20 hours parallel (8 cores). Parallelization is non-negotiable at this scale per features research. Core logic validated in Phase 1-2, so parallelization is pure optimization without introducing logic bugs. Architecture research specifies Windows spawn constraints that must be designed around from start.

**Delivers:** Multi-worker processor handling 100+ PDFs in parallel without crashes; linear speedup with CPU count.

**Implements:**
- ProcessPoolExecutor with `max_workers=cpu_count()`
- Worker initialization pattern for heavy config (avoid pickle overhead)
- Coarse-grained parallelization (per-PDF, not per-page)
- tqdm progress tracking with `process_map()`
- Incremental CSV output (append mode, prevent memory exhaustion)

**Avoids (critical pitfalls):**
- Windows spawn overhead: Pass file paths only, use worker initialization
- Tesseract memory leak: Set `maxtasksperchild=100` for process recycling
- File handle leaks: Audit all workers for proper context managers

**Uses (from stack):**
- concurrent.futures.ProcessPoolExecutor (cleaner API than multiprocessing.Pool)
- tqdm.contrib.concurrent.process_map for automatic progress bars

**Research flags:** Needs careful testing on Windows. Standard patterns documented but Windows spawn behavior requires validation. Consider quick spike for worker initialization pattern before full phase.

---

### Phase 4: Resilience — Error Handling & Checkpointing
**Rationale:** At 30K scale, some PDFs will be corrupted, some OCR will fail, and long-running batches may crash mid-run. Architecture research shows error handling is meaningful only after parallelization (race conditions, worker crashes). Features research confirms resume capability is key differentiator for long batches. Real-world failure modes emerge at scale.

**Delivers:** Batch processor that completes 30K run even with 5% corrupted files; all failures logged; resume capability for crashes.

**Implements:**
- Try-catch per PDF with structured logging
- Retry logic (exponential backoff, max 3 attempts)
- Dead-letter queue for persistent failures
- Checkpoint file tracking processed PDFs
- Resume from last successful file
- Batch statistics report (success rate, failures, total IDs, avg time)

**Avoids (pitfall):**
- Catastrophic failure: Isolate poison pills so they don't block pipeline
- Lost progress: Write results incrementally + checkpoint every 100 files

**Uses (from stack):**
- Python logging with file + console handlers
- pathlib for checkpoint file operations

**Research flags:** Standard batch processing patterns. Skip research-phase.

---

### Phase 5: Quality — Conditional Preprocessing & Validation
**Rationale:** Architecture research emphasizes preprocessing is a **fallback**, not primary path. Preprocessing adds 20-50ms per page (1.7-4.2 hours across 300K pages); only apply when needed. Features research confirms preprocessing improves accuracy from 85-92% to 95-98% but should be conditional. Add last because it's optional optimization, not core functionality.

**Delivers:** Preprocessing pipeline that improves extraction rate on low-quality scans without degrading high-quality results.

**Implements:**
- Conditional preprocessing (only if multi-rotation OCR finds no ID)
- Tiered fallback: raw → Pillow grayscale → OpenCV threshold/denoise
- Character normalization (O→0, I→1, S→5 post-OCR)
- Confidence scoring with manual review threshold
- Sample validation (random 50 pages manual verification)

**Avoids (pitfall):**
- Over-aggressive preprocessing: Don't preprocess all images; use tiered fallback approach
- Ignoring confidence scores: Flag low-confidence results (<60) for manual review

**Uses (from stack):**
- Pillow for primary preprocessing (grayscale conversion)
- OpenCV for advanced fallback (adaptive thresholding, denoising)

**Research flags:** Preprocessing techniques well-documented. Skip research-phase. Consider A/B testing on sample corpus to validate effectiveness before full integration.

---

### Phase Ordering Rationale

**Why this order:**
1. **Phase 1 before 2-5:** Must validate core OCR logic works before adding complexity; integration issues (missing Tesseract, wrong paths) surface immediately in simple single-file test
2. **Phase 2 before 3:** Rotation logic easier to debug serially; adding parallelization to broken rotation logic creates race conditions that obscure root cause
3. **Phase 3 before 4:** Error handling requires understanding failure modes at scale; serial processing hides race conditions and worker crashes
4. **Phase 5 last:** Preprocessing is optional fallback; can be added incrementally without affecting existing pipeline; expensive (time cost) so validate it's needed first

**Dependency chain discovered in research:**
- Multi-rotation depends on validated single-rotation OCR (Phase 2 needs Phase 1)
- Parallelization depends on proven serial pipeline (Phase 3 needs Phase 1-2)
- Error handling depends on parallelization failure modes (Phase 4 needs Phase 3)
- Preprocessing depends on measuring baseline accuracy (Phase 5 needs Phase 1-3 to identify which pages fail)

**Pitfall avoidance:**
- Phase 1 addresses 4 critical pitfalls immediately (memory, DPI, handles, PSM) before they compound in later phases
- Phase 2 implements multi-rotation brute force early to avoid OSD pitfall
- Phase 3 designed around Windows spawn constraints from start (not retrofitted)
- Phase 4 prevents data loss from crashes via checkpointing
- Phase 5 conditional approach prevents over-preprocessing pitfall

### Research Flags

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** pytesseract + pdf2image integration well-documented in official docs; straightforward file I/O patterns
- **Phase 2 (Rotation):** Image rotation + multi-attempt OCR standard pattern; Pillow rotation docs + PyImageSearch tutorials cover this
- **Phase 4 (Resilience):** Checkpointing and error handling general batch processing patterns; Python logging stdlib well-documented
- **Phase 5 (Quality):** Preprocessing techniques documented in official Tesseract "Improving Quality" guide + multiple tutorials

**Phases needing careful validation (not research, but testing):**
- **Phase 3 (Parallelization):** Windows spawn behavior requires testing on target hardware; worker initialization pattern documented but performance characteristics vary; recommend quick spike (4-8 hours) to validate ProcessPoolExecutor + worker init + tqdm integration before committing to full phase
- **Phase 5 (Preprocessing):** A/B test on sample corpus (100 PDFs) to measure actual accuracy improvement before full integration; validate Pillow vs. OpenCV trade-offs on real data

**No phases need /gsd:research-phase** — all patterns sufficiently documented in this research. Validation needed, not additional research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | All versions verified against PyPI official pages as of 2026-06-04; Tesseract 5.x widely deployed; pdf2image mature standard; no experimental dependencies |
| **Features** | HIGH | Table stakes derived from universal batch OCR system expectations; differentiators match documented best practices; anti-features validated against project constraints (CLI-only, local, one-shot) |
| **Architecture** | HIGH | Producer-consumer pattern standard for batch processing; Windows spawn constraints documented in official Python docs; build order validated against dependency chains and pitfall research |
| **Pitfalls** | HIGH | Critical pitfalls sourced from official documentation (Tesseract, pdf2image GitHub issues) and Microsoft docs; memory issues verified across multiple sources; PSM/OSD behavior documented in official Tesseract guide |

**Overall confidence:** HIGH

Research converges on proven patterns with mature tooling. No experimental technologies, no unvalidated assumptions. Windows-specific constraints (spawn, memory leaks, path limits) are well-documented with tested mitigation strategies. Risk is low for this tech stack and architecture.

### Gaps to Address

**Minor gaps requiring validation during implementation:**

1. **Actual scan quality distribution:** Research assumes mix of high-quality and degraded scans; preprocessing effectiveness (Phase 5) depends on actual scan quality distribution in the 30K corpus. **Mitigation:** Run Phase 1-2 on sample (100 PDFs) to measure baseline success rate before designing Phase 5 preprocessing.

2. **Windows spawn performance on user's hardware:** Research documents spawn overhead, but actual performance (process creation time, pickle costs) varies with CPU, RAM, and disk speed. **Mitigation:** Phase 3 spike (4-8 hours) to benchmark ProcessPoolExecutor on target hardware with realistic workload before committing to full parallelization phase.

3. **"Precede" keyword consistency:** Research assumes "Precede" cursive text appears near IDs for contextual validation, but actual consistency unknown. **Mitigation:** Sample validation in Phase 1 to determine if contextual extraction (regex near "Precede") is viable or if isolated 5-digit regex sufficient.

4. **Tesseract 5.x memory leak severity:** Research documents Tesseract 4.x memory leak on Windows; Tesseract 5.x may have improved but not explicitly verified. **Mitigation:** Monitor memory during Phase 3 parallelization testing; adjust `maxtasksperchild` value based on observed leak rate (100-500 files).

5. **Multiple IDs per page frequency:** Research flags multiple IDs per page as table stakes feature, but actual frequency unknown. **Mitigation:** Phase 1 sample testing determines if this is edge case (<5% of pages) or common pattern, informing output format design.

**All gaps are validation questions, not research gaps.** Existing research provides proven mitigation strategies; implementation needs to tune parameters based on actual data characteristics.

## Sources

### Primary (HIGH confidence)

**Official Documentation:**
- pytesseract PyPI (version, API, config options)
- pdf2image PyPI + GitHub (memory management, parameters)
- Tesseract Official Documentation (PSM modes, improving quality, release notes)
- Python multiprocessing documentation (spawn vs fork, Pool API, Windows constraints)
- Microsoft documentation (Windows path limits, resource management)
- OpenCV official documentation (preprocessing functions)
- Pillow PyPI (image operations, rotation)

**Verified Technical Issues:**
- Tesseract GitHub Issue #2541 (RAM not released on Windows)
- Tesseract GitHub Issue #1701, #1926 (OSD unreliability)
- Tesseract GitHub Issue #4407 (whitelist not working)
- pdf2image GitHub Issue #54 (memory leak)
- Python CPython Issue #96953 (multiprocessing pickle performance)

### Secondary (MEDIUM confidence)

**Technical Comparisons:**
- PyImageSearch: Tesseract PSM Modes Explained (detailed tutorial with examples)
- Python Speed: Faster Multiprocessing Pickle (performance analysis)
- Medium: Python Multiprocessing Fork vs Spawn (Windows behavior)
- FreeCodeCamp: Image Preprocessing for Tesseract (preprocessing guidelines)

**Best Practices:**
- Batch OCR processing patterns (multiple 2026 sources converge on producer-consumer)
- OCR accuracy benchmarks (85-92% without preprocessing, 95-98% with)
- Error handling and retry logic (exponential backoff standard pattern)
- Progress tracking with tqdm (multiprocessing integration documented)

### Tertiary (LOW confidence)

- Joblib Loky speedup claims (6-10x) — not verified for this specific workload
- Specific accuracy percentages for Tesseract on numeric IDs — benchmarks are general text, not numeric-specific
- Optimal DPI for small digits — 300 DPI widely recommended, but "optimal" depends on scan quality

**Source aggregation:** 70+ sources reviewed across 4 research files; convergence across official docs, GitHub issues, and technical tutorials provides HIGH confidence for recommendations.

---

**Research completed:** 2026-06-04
**Ready for roadmap:** Yes

**Next steps for orchestrator:**
1. Load SUMMARY.md as context for roadmap creation
2. Use suggested 5-phase structure as starting point
3. Apply research flags (all phases skip research-phase; Phase 3 and 5 need validation spikes)
4. Reference STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md for detailed specifications during phase planning
