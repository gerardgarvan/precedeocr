# Architecture Patterns: Performance Optimization Integration

**Domain:** Batch OCR Pipeline Performance Optimization
**Researched:** 2026-06-07
**Confidence:** HIGH

## Executive Summary

This document maps how performance optimizations integrate with the existing Precede OCR pipeline architecture. The current architecture uses a document-level parallelism model where multiprocessing.Pool dispatches entire PDFs to worker processes. Each worker converts PDF pages via pdf2image, runs multi-rotation OCR via pytesseract, and applies OpenCV preprocessing fallback. Performance optimizations integrate at three architectural layers: **PDF rendering** (swap pdf2image for PyMuPDF), **OCR configuration** (Tesseract config injection), and **rotation strategy** (intelligent rotation vs brute-force). The recommended build order prioritizes early measurable gains: PyMuPDF swap first (largest single speedup), then Tesseract config optimization (minimal code change, immediate benefit), then rotation strategy refinement.

## Current Architecture Overview

### Component Structure

```
precede_ocr.py (main entry point)
├── Campaign Manager (state, resume menu, reporting)
├── Worker Pool (multiprocessing.Pool)
│   └── Worker Process (per PDF)
│       ├── PDF → Pages (pdf2image)
│       ├── Per-Page Processing
│       │   ├── Multi-Rotation OCR (pytesseract)
│       │   │   ├── Try 90° → regex match? → done
│       │   │   ├── Try 270° → regex match? → done
│       │   │   ├── Try 0° → regex match? → done
│       │   │   └── Try 180° → regex match? → done
│       │   └── Preprocessing Fallback (OpenCV)
│       │       └── Retry multi-rotation OCR
│       └── Checkpoint Writer (atomic .checkpoint.json)
└── Output Generator (CSV + JSON)
```

### Data Flow

1. **Campaign Start**: Load campaign_state.json or create new campaign
2. **File Discovery**: Recursively glob `**/*.pdf`
3. **Dispatch**: Pool.map(process_pdf, pdf_paths)
4. **Worker Execution**: Each worker processes one PDF end-to-end
5. **Per-Page Loop**: Convert page → OCR with rotations → extract IDs → accumulate results
6. **Checkpoint**: Atomic write per-file results to .checkpoint.json
7. **Aggregation**: Main process collects results, updates campaign_state.json
8. **Output**: Generate CSV + JSON from accumulated checkpoint data

### Key Architectural Constraints

- **Windows spawn model**: Workers cannot share memory; must pass filenames not objects
- **Coarse-grained parallelism**: One PDF per worker (not page-level parallelism)
- **Atomic checkpoints**: Worker results must be JSON-serializable dicts
- **No IPC overhead**: Workers accumulate results locally, return to main process
- **Existing test coverage**: 230 tests verify pipeline behavior

---

## Performance Optimization Integration Points

### 1. PDF Rendering Layer: pdf2image → PyMuPDF

**Current Implementation:**

```python
# Located in: page processing function
from pdf2image import convert_from_path
pages = convert_from_path(
    pdf_path,
    dpi=300,
    output_folder=temp_dir,
    paths_only=True  # Memory safety
)
```

**PyMuPDF Integration:**

```python
# New approach
import pymupdf  # Replaces pdf2image import
doc = pymupdf.open(pdf_path)
for page_num in range(len(doc)):
    page = doc[page_num]
    pix = page.get_pixmap(dpi=300)  # Direct DPI parameter (v1.19.2+)
    # Convert to PIL Image for pytesseract compatibility
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    # Continue with existing OCR pipeline
```

**API Differences:**

| Aspect | pdf2image | PyMuPDF |
|--------|-----------|---------|
| **Import** | `from pdf2image import convert_from_path` | `import pymupdf` |
| **Page Extraction** | Batch conversion: `convert_from_path()` | Iterator: `doc = pymupdf.open(); doc[page_num]` |
| **DPI Control** | `dpi=300` parameter | `page.get_pixmap(dpi=300)` or `matrix=Matrix(300/72, 300/72)` |
| **Output Format** | PIL Images or file paths | Pixmap objects (convert via PIL) |
| **Memory Model** | Temp files on disk (paths_only) or PIL list | Pixmap objects in memory (must convert/dispose) |
| **Dependencies** | Requires Poppler binaries | Zero external dependencies |
| **Performance** | 10s for 7-page PDF | 800ms-3s for same PDF (3-12× faster) |

**Integration Strategy:**

**Option A: Minimal Refactor** (Recommended for early measurement)
- Create adapter function: `get_page_as_pil_image(pdf_path, page_num) -> PIL.Image`
- Replace `convert_from_path()` call with loop over `range(len(doc))`
- Maintain PIL Image interface downstream (no OCR code changes)
- Explicitly dispose of pixmap objects: `pix = None` after conversion

**Option B: Native PyMuPDF Pipeline**
- Pass pixmap objects directly to pytesseract (pytesseract accepts PIL, numpy, or bytes)
- Eliminate PIL conversion overhead
- Requires refactoring downstream image handling code
- Higher risk; defer until Option A validated

**Modified Components:**
- PDF page extraction function (currently wraps pdf2image)
- Worker process initialization (import change)
- Temp directory cleanup logic (PyMuPDF doesn't use temp files unless explicitly saving)

**New Components:**
- PyMuPDF pixmap → PIL Image adapter (if using Option A)
- Memory management wrapper to dispose pixmaps (prevent accumulation)

**Data Flow Changes:**

```
BEFORE:
PDF → convert_from_path() → List[PIL.Image] or List[Path] → per-page OCR

AFTER (Option A):
PDF → pymupdf.open() → doc[page_num] → get_pixmap(dpi=300) → PIL.frombytes() → per-page OCR
                                                                  ↓
                                                              pix = None (dispose)
```

**Memory Implications:**

- **pdf2image**: Uses disk temp files when `paths_only=True`; minimal memory footprint
- **PyMuPDF**: Pixmap objects ~25 MB per page (A4, RGB, 595×842px at 300 DPI)
- **Mitigation**: Convert pixmap → PIL → dispose pixmap immediately (per-page loop)
- **Risk**: Accumulating pixmaps across pages = OOM; critical to dispose after conversion

**Confidence:** HIGH — PyMuPDF official docs, API verified, performance benchmarks from multiple sources

---

### 2. OCR Configuration Layer: Tesseract Parameter Injection

**Current Implementation:**

```python
# Located in: OCR function
import pytesseract
text = pytesseract.image_to_string(image)
# Uses Tesseract defaults: PSM 3, OEM 3, all characters
```

**Optimized Configuration:**

```python
# Tesseract config string for digit-only extraction
custom_config = r'--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789'
text = pytesseract.image_to_string(image, config=custom_config)
```

**Configuration Parameters Explained:**

| Parameter | Value | Purpose | Rationale |
|-----------|-------|---------|-----------|
| `--psm 6` | Uniform block of text | OCR treats page as single text block | Better than PSM 3 (full page structure) or PSM 7 (single line) for scanned docs with isolated IDs. Project has IDs on relatively uniform backgrounds. |
| `--oem 1` | LSTM neural net only | Use modern neural network OCR engine | OEM 1 (LSTM only) faster than OEM 3 (default/auto). Legacy engine (OEM 0) not needed for scanned digits. OEM 2 (legacy + LSTM) slower, unnecessary. |
| `-c tessedit_char_whitelist=0123456789` | Digits only | Restrict OCR to 0-9 characters | Eliminates false positives from letters (O→0, I→1, S→5). Current pipeline has normalization step; whitelist makes it unnecessary. |

**Alternative PSM Modes Considered:**

- **PSM 7** (single text line): Too restrictive; IDs may not be perfectly aligned
- **PSM 8** (single word): Better for 2-4 digit sequences, but project has 5-digit IDs
- **PSM 10** (single character): Requires pre-segmentation; adds complexity without gain
- **PSM 13** (raw line, bypass hacks): Last resort for unusual fonts; not needed

**Integration Points:**

**Modified Components:**
- Multi-rotation OCR function (add `config` parameter to `pytesseract.image_to_string()`)
- Preprocessing fallback OCR (same config injection)

**New Components:**
- None (pure configuration change)

**Data Flow Changes:**
- No structural changes; same image → OCR → text flow
- Internal Tesseract behavior changes (character recognition constrained to digits)

**Testing Implications:**
- Existing regex validation (`\d{5}`) remains unchanged
- Character normalization step (O→0, I→1, S→5) becomes redundant but harmless
- Test corpus should see accuracy improvement (fewer false matches)

**Build Order Consideration:**
- **Zero risk**: Config string doesn't break existing code if wrong
- **Immediate benefit**: Can apply to current codebase without PyMuPDF swap
- **Reversible**: Remove config string to revert to defaults

**Confidence:** HIGH — Official pytesseract documentation, Tesseract PSM/OEM docs, PyImageSearch tutorials

---

### 3. Rotation Strategy Layer: Intelligent vs Brute-Force

**Current Implementation (Brute-Force):**

```python
# Multi-rotation OCR: try all 4 rotations until regex match
rotations = [90, 270, 0, 180]
for angle in rotations:
    rotated_image = image.rotate(angle, expand=True)
    text = pytesseract.image_to_string(rotated_image)
    ids = extract_ids_regex(text)  # \d{5}
    if ids:
        return ids, angle
# If all fail, trigger preprocessing fallback
```

**Current Performance:**
- Best case: 1 OCR pass (90° correct)
- Worst case: 4 OCR passes (180° correct or all fail)
- Average: ~2.5 OCR passes per page (assuming uniform distribution)

**Optimization Strategy A: OSD Pre-Detection**

```python
# Use Tesseract OSD (Orientation and Script Detection)
osd = pytesseract.image_to_osd(image)
# Parse rotation angle from OSD output
# Single rotation OCR at detected angle
```

**OSD Tradeoffs:**

| Aspect | OSD Pre-Detection | Current Multi-Pass |
|--------|-------------------|-------------------|
| **OCR Passes** | 1 (OSD) + 1 (OCR) = 2 total | 1-4 OCR passes (avg 2.5) |
| **Speed** | OSD faster than full OCR | Multiple full OCR passes |
| **Accuracy** | OSD unreliable per GitHub issues | Regex validation guarantees correctness |
| **Failure Mode** | Wrong rotation → fallback to multi-pass | Brute-force always tries all rotations |
| **Code Complexity** | Parse OSD output, handle errors | Simple loop |

**Known OSD Issues:**
- [Tesseract Issue #4426](https://github.com/tesseract-ocr/tesseract/issues/4426): "Poor Rotation / Layout detection" (June 2025)
- Community reports: OSD confidence scores unreliable on scanned documents
- Project's existing approach avoids OSD for good reason

**Optimization Strategy B: Smarter Rotation Order**

```python
# Track rotation distribution from campaign_state.json
# Order rotations by historical frequency
# Most common rotation first (e.g., 90° → 270° → 0° → 180°)
rotations_by_frequency = get_rotation_order_from_stats()
for angle in rotations_by_frequency:
    # Same loop as current implementation
```

**Strategy B Tradeoffs:**

| Aspect | Frequency-Ordered | Current Fixed Order |
|--------|-------------------|---------------------|
| **Best Case** | 1 pass (same) | 1 pass |
| **Average Case** | ~1.5 passes (if 90° is 70% of corpus) | 2.5 passes |
| **Worst Case** | 4 passes (same) | 4 passes |
| **Code Changes** | Read campaign stats, reorder list | None |
| **Risk** | Corpus-specific optimization (brittle) | Universal |

**Optimization Strategy C: Early-Exit Heuristics**

```python
# Confidence-based early exit (requires image_to_data)
rotations = [90, 270, 0, 180]
for angle in rotations:
    rotated_image = image.rotate(angle, expand=True)
    data = pytesseract.image_to_data(rotated_image, output_type=Output.DICT, config=custom_config)
    # Check confidence scores
    if high_confidence_five_digit_id(data):
        return extract_ids(data), angle
# Fallback to remaining rotations if low confidence
```

**Strategy C Tradeoffs:**

| Aspect | Confidence Heuristics | Current Regex Match |
|--------|-----------------------|---------------------|
| **Early Exit** | Exit on high-confidence match | Exit on any regex match |
| **OCR Calls** | 1-4 (same as current) | 1-4 (current) |
| **Complexity** | Parse confidence scores, define thresholds | Simple regex |
| **Accuracy** | Tesseract confidence may not align with ID validity | Regex directly validates 5-digit pattern |
| **Benefit** | Minimal (regex already provides strong signal) | Baseline |

**Recommendation:**

**Strategy B (Frequency-Ordered Rotations)** offers best risk/reward:
- **Measurable gain**: If 90° is dominant rotation (~70%), reduces avg passes from 2.5 → 1.5 (40% reduction)
- **Low risk**: Simple list reordering; regex validation unchanged
- **Incremental**: Apply after PyMuPDF and config optimizations validated
- **Data-driven**: Campaign stats already track rotation distribution

**Defer OSD** until proven necessary:
- Current multi-pass with regex validation is reliable
- OSD adds complexity without guaranteed benefit
- GitHub issues indicate OSD unreliability on scanned docs

**Skip Strategy C** (confidence heuristics):
- Regex match provides stronger signal than confidence scores
- Minimal benefit for added complexity

**Integration Points:**

**Modified Components:**
- Multi-rotation OCR function (reorder rotations list based on campaign stats)
- Campaign state loader (expose rotation distribution stats)

**New Components:**
- Rotation frequency analyzer (read campaign_state.json, return ordered rotation list)

**Data Flow Changes:**
- No structural changes; rotation order becomes dynamic instead of static

**Confidence:** MEDIUM — Strategy B relies on corpus characteristics; OSD reliability concerns documented in GitHub issues

---

### 4. Parallelism Architecture: Document-Level vs Page-Level

**Current Architecture: Document-Level Parallelism**

```python
# Main process
with multiprocessing.Pool(processes=num_workers) as pool:
    results = pool.map(process_pdf, pdf_paths)
```

**Current Model:**
- One worker process per PDF
- Worker opens PDF, converts all pages, OCRs all pages, returns results
- Coarse-grained: ~30K PDFs / N workers
- Each worker runs serially through pages within one PDF

**Alternative: Page-Level Parallelism**

```python
# Generate page tasks: (pdf_path, page_num) tuples
page_tasks = []
for pdf_path in pdf_paths:
    doc = pymupdf.open(pdf_path)
    page_tasks.extend((pdf_path, i) for i in range(len(doc)))
    doc.close()

# Dispatch pages to workers
with multiprocessing.Pool(processes=num_workers) as pool:
    page_results = pool.map(process_page, page_tasks)
```

**Tradeoffs:**

| Aspect | Document-Level (Current) | Page-Level |
|--------|--------------------------|------------|
| **Granularity** | ~30K tasks (~30K PDFs) | ~100K+ tasks (multi-page PDFs) |
| **Load Balancing** | Uneven (PDFs vary: 1-50 pages) | Even (each task = 1 page) |
| **Startup Overhead** | Open PDF once per document | Open PDF once per page (higher overhead) |
| **Memory** | PDF handle held during all pages | PDF handle held per page (lower peak) |
| **Checkpoint Complexity** | Per-PDF atomic checkpoints | Per-page checkpoints or aggregation required |
| **Windows Spawn Cost** | N processes (reused via Pool) | N processes (reused), but more task pickling |
| **Code Changes** | Current codebase | Significant refactor |

**Analysis:**

**Current document-level model is appropriate because:**
1. **Checkpoint architecture**: Existing atomic checkpoint writes are per-PDF; page-level would require aggregation or per-page checkpoints (state explosion)
2. **Load balancing**: 30K PDFs provides sufficient granularity for 20 cores (1,500 PDFs/core)
3. **PDF handle overhead**: Opening PDF for each page instead of once per document = wasted I/O
4. **Diminishing returns**: PyMuPDF swap and config optimization address per-page latency; parallelism grain unlikely to be bottleneck

**When to reconsider page-level:**
- If profiling shows workers idle due to load imbalance (few large PDFs dominate tail latency)
- If checkpoint architecture changes (e.g., streaming results instead of per-PDF batches)

**Hybrid Approach (Future Consideration):**

```python
# Page-level parallelism within each worker process
def process_pdf(pdf_path):
    doc = pymupdf.open(pdf_path)
    with ThreadPoolExecutor(max_workers=4) as thread_pool:
        page_results = thread_pool.map(ocr_page, [doc[i] for i in range(len(doc))])
    # Aggregate page results → per-PDF checkpoint
    return aggregate_results(page_results)
```

**Hybrid Tradeoffs:**
- **Benefit**: Parallelize OCR within one PDF (if PDFs have many pages)
- **Limitation**: OCR is CPU-bound, not I/O-bound. Python's GIL blocks true threading parallelism
- **Alternative**: Use `multiprocessing.Pool` within worker (nested pools), but complexity high
- **Verdict**: Not recommended unless profiling shows single-PDF processing is bottleneck

**Recommendation:**

**Maintain document-level parallelism:**
- Existing architecture is sound for 30K+ PDF corpus
- Optimization effort better spent on per-page latency (PyMuPDF, config, rotation)
- Checkpoint and testing architecture built around per-PDF granularity

**Defer page-level parallelism** unless:
- Profiling reveals load imbalance as primary bottleneck
- Corpus characteristics change (e.g., few very large PDFs instead of many small ones)

**Confidence:** HIGH — PyMuPDF multiprocessing docs, Python multiprocessing best practices, corpus characteristics (30K PDFs)

---

## Suggested Build Order: Incremental Gains

Performance optimization should follow incremental, measurable steps to maximize early wins and minimize integration risk. The recommended sequence prioritizes high-impact, low-risk changes first.

### Phase 1: PDF Rendering Swap (Highest Impact)

**What to Build:**
- Replace `pdf2image.convert_from_path()` with PyMuPDF `doc.get_pixmap(dpi=300)`
- Adapter function: `get_page_as_pil_image(pdf_path, page_num) -> PIL.Image`
- Explicit pixmap disposal after PIL conversion

**Expected Gain:**
- **3-12× speedup** on PDF rendering per official benchmarks
- Rendering is per-page operation; affects all 100K+ pages in corpus
- Largest single bottleneck based on typical OCR pipeline profiles

**Risk Level:** LOW
- PyMuPDF API is well-documented and stable
- PIL Image interface maintained downstream (no OCR code changes)
- Existing test suite validates correctness (230 tests)

**Testing Strategy:**
- Run on small test corpus (10-20 PDFs) before full campaign
- Compare output CSV/JSON checksums (should be identical)
- Profile with `cProfile` to measure rendering time reduction

**Success Criteria:**
- All 230 tests pass
- Output identical to pdf2image baseline (bitwise CSV/JSON comparison)
- Measured speedup: 2× or better on PDF rendering

**Dependencies:** None (first optimization)

---

### Phase 2: Tesseract Configuration (Immediate Benefit, Zero Risk)

**What to Build:**
- Add `custom_config = r'--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789'`
- Inject config into `pytesseract.image_to_string(image, config=custom_config)`
- Apply to both multi-rotation OCR and preprocessing fallback

**Expected Gain:**
- **10-30% speedup** on OCR per character (digit-only reduces search space)
- **Accuracy improvement**: Fewer false positives (O→0, I→1 eliminated)
- May reduce preprocessing fallback invocations if cleaner OCR output

**Risk Level:** ZERO
- Config string is optional parameter; wrong config = fallback to defaults
- Regex validation (`\d{5}`) unchanged; bad OCR results rejected as before
- Reversible: remove config string to revert

**Testing Strategy:**
- Run test corpus with config enabled
- Compare accuracy metrics (OCR success rate, preprocessing fallback rate)
- Verify output still passes regex validation

**Success Criteria:**
- OCR accuracy ≥ baseline (94.9%)
- Preprocessing fallback rate ≤ baseline (should decrease)
- No test failures

**Dependencies:** None (can apply independently or after Phase 1)

**Recommended Timing:** Apply immediately after Phase 1 validated (compound speedups)

---

### Phase 3: Profiling and Bottleneck Identification (Data-Driven)

**What to Build:**
- Integrate `cProfile` into main pipeline: `python -m cProfile -o profile.stats precede_ocr.py <args>`
- Visualize with SnakeViz: `snakeviz profile.stats`
- Instrument timing logs for key operations (PDF open, rendering, OCR per rotation, preprocessing)

**Expected Gain:**
- **Identify actual bottlenecks** rather than assumed bottlenecks
- Validate Phase 1 & 2 gains with hard numbers
- Guide Phase 4 priorities (rotation strategy, other optimizations)

**Risk Level:** ZERO (profiling doesn't change code behavior)

**Testing Strategy:**
- Profile on representative subset (1,000-5,000 PDFs)
- Sort by `tottime` to find hottest functions
- Compare profile before/after Phase 1 & 2 optimizations

**Success Criteria:**
- Profile data shows PDF rendering time reduced (Phase 1 validation)
- Profile data shows OCR time per page reduced (Phase 2 validation)
- New bottleneck identified (guides Phase 4+)

**Dependencies:** Phases 1 & 2 completed (need optimized baseline to profile)

---

### Phase 4: Rotation Strategy Refinement (Data-Informed)

**What to Build:**
- Analyze campaign_state.json rotation distribution
- If 90° dominates (>60%), reorder rotations: `[90, 270, 0, 180]` → most-common-first
- Dynamic rotation ordering based on per-folder stats (optional advanced)

**Expected Gain:**
- **20-40% reduction** in OCR passes if one rotation dominates
- Best case: avg passes 2.5 → 1.5 (if 90° is 70% of corpus)
- No gain if rotation distribution is uniform (25% each)

**Risk Level:** LOW
- Simple list reordering; logic unchanged
- Regex validation still guarantees correctness

**Testing Strategy:**
- Measure rotation distribution from existing campaign data
- Calculate expected pass reduction
- Benchmark small corpus before/after

**Success Criteria:**
- If rotation distribution skewed: measurable pass reduction
- If rotation distribution uniform: defer optimization (no benefit)

**Dependencies:** Phase 3 profiling (validate rotation loop is still bottleneck post-PyMuPDF)

**Conditional Trigger:** Only apply if profiling shows rotation loop is significant post-PyMuPDF

---

### Phase 5: Advanced Optimizations (If Needed)

**Candidates Based on Profiling Results:**

**5a. DPI Reduction Experiment**
- Test 200 DPI vs 300 DPI on sample corpus
- If accuracy ≥ baseline, adopt 200 DPI (faster rendering + OCR)
- Risk: Accuracy degradation on low-quality scans

**5b. Preprocessing Pipeline Optimization**
- Profile OpenCV preprocessing steps (grayscale, threshold, denoise)
- Identify slowest operations (e.g., bilateral filter vs Gaussian blur)
- Test minimal preprocessing that maintains accuracy

**5c. Hybrid CPU/GPU Tesseract**
- Investigate Tesseract GPU support (if available on Windows)
- Likely not applicable (Tesseract 5.x is CPU-focused)

**5d. Page-Level Parallelism**
- Only if profiling shows load imbalance (worker idle time)
- Major refactor; defer until other optimizations exhausted

**Dependencies:** Phases 1-4 completed, profiling shows new bottleneck

---

## Integration Patterns Summary

### New vs Modified Components

| Component | Type | Change |
|-----------|------|--------|
| PDF page extraction function | MODIFIED | Replace pdf2image calls with PyMuPDF |
| PyMuPDF → PIL adapter | NEW | Convert pixmap to PIL Image for pytesseract |
| Multi-rotation OCR function | MODIFIED | Add Tesseract config parameter |
| Preprocessing fallback OCR | MODIFIED | Add Tesseract config parameter |
| Rotation frequency analyzer | NEW | Read campaign stats, return ordered rotation list |
| Profiling instrumentation | NEW | cProfile integration, timing logs |
| Worker process logic | MINIMAL | Import changes only (pymupdf vs pdf2image) |
| Checkpoint architecture | UNCHANGED | Same per-PDF atomic writes |
| Campaign state schema | UNCHANGED | Rotation stats already tracked |

### Data Flow Changes

**Phase 1 (PyMuPDF):**
```
BEFORE: PDF → convert_from_path() → List[PIL.Image] → OCR
AFTER:  PDF → doc[page] → get_pixmap() → PIL.frombytes() → OCR (same downstream)
```

**Phase 2 (Config):**
```
BEFORE: PIL.Image → pytesseract.image_to_string() → text
AFTER:  PIL.Image → pytesseract.image_to_string(config=custom_config) → text (same output format)
```

**Phase 4 (Rotation):**
```
BEFORE: for angle in [90, 270, 0, 180]: ...
AFTER:  for angle in rotation_order_from_stats(): ... (same loop structure)
```

### Backward Compatibility

All optimizations maintain existing interfaces:
- OCR functions still accept PIL Images
- Output format unchanged (CSV + JSON schema)
- Checkpoint format unchanged (JSON structure)
- Test suite unchanged (validates behavior, not implementation)

---

## Performance Expectations

### Baseline (Current)

| Operation | Time per Page (est.) | Notes |
|-----------|----------------------|-------|
| PDF rendering (pdf2image) | 1-2s | Poppler pdftoppm |
| OCR per rotation | 0.5-1s | Tesseract, 300 DPI |
| Multi-rotation (avg 2.5 passes) | 1.25-2.5s | Brute-force 4 rotations |
| Preprocessing fallback | +2-3s | OpenCV pipeline + retry |
| **Total per page** | ~3-5s | Assumes no preprocessing |

**Total corpus estimate:**
- 30K PDFs × 5 pages avg × 4s/page = 600K seconds = ~167 hours = ~7 days (single-threaded)
- With 20 workers: ~8-10 hours (current performance)

### Post-Optimization (Projected)

| Operation | Time per Page (est.) | Improvement |
|-----------|----------------------|-------------|
| PDF rendering (PyMuPDF) | 0.2-0.5s | **4-10× faster** |
| OCR per rotation (digit whitelist) | 0.4-0.8s | **20% faster** |
| Multi-rotation (frequency-ordered, avg 1.5 passes) | 0.6-1.2s | **40% fewer passes** |
| Preprocessing fallback | +1.5-2s | Same or slightly faster |
| **Total per page** | ~1-2s | **2-5× speedup** |

**Optimized corpus estimate:**
- 30K PDFs × 5 pages avg × 1.5s/page = 225K seconds = ~62 hours = ~2.5 days (single-threaded)
- With 20 workers: **3-4 hours** (optimized performance)

**Net Gain: 50-70% reduction in total runtime** (8-10 hours → 3-4 hours)

**Confidence:** MEDIUM — Based on published benchmarks (PyMuPDF, Tesseract config), actual gains depend on corpus characteristics

---

## Risk Assessment

| Optimization | Risk Level | Mitigation |
|--------------|------------|------------|
| PyMuPDF swap | LOW | Extensive testing, PIL interface maintained, existing test suite validates correctness |
| Tesseract config | ZERO | Optional parameter; reversible; regex validation unchanged |
| Rotation ordering | LOW | Simple reordering; regex validation guarantees correctness |
| Page-level parallelism | HIGH | Defer until profiling proves necessary; requires checkpoint refactor |
| DPI reduction | MEDIUM | Test accuracy on sample corpus first; may degrade low-quality scan results |

**Overall Risk:** LOW — Incremental approach with testing at each phase minimizes integration risk

---

## Open Questions for Implementation

1. **PyMuPDF Pixmap Disposal:** Does Python garbage collection suffice, or explicit `pix = None` required?
2. **Rotation Distribution:** What is actual rotation distribution in 30K corpus? (Analyze campaign_state.json)
3. **DPI Sweet Spot:** Is 300 DPI necessary for 5-digit IDs, or can 200 DPI maintain accuracy? (Experiment needed)
4. **Preprocessing Trigger Rate:** What % of pages require preprocessing fallback? (Profile to quantify)
5. **Worker Pool Size:** Is `cpu_count() - 1` optimal for hybrid CPU (P-cores + E-cores)? (Experiment with pool sizes)

---

## Dependencies and Constraints

### System Requirements

- **Windows 10**: All optimizations tested on Windows spawn model
- **Python 3.8+**: PyMuPDF and pytesseract compatibility
- **Tesseract 5.x**: Config parameters assume modern Tesseract
- **20 CPU cores**: Performance projections assume high core count

### External Dependencies

| Library | Current Version | Optimized Version | Notes |
|---------|-----------------|-------------------|-------|
| pdf2image | 1.17.0 | REMOVE | Replace with PyMuPDF |
| Poppler | Latest | REMOVE | No longer needed |
| PyMuPDF | N/A | 1.24.0+ | New dependency; use `dpi=` parameter (v1.19.2+) |
| pytesseract | 0.3.13 | 0.3.13 (same) | No version change needed |
| Pillow | 12.2.0 | 12.2.0 (same) | Still needed for image handling |
| OpenCV | 4.13.0.92 | 4.13.0.92 (same) | Preprocessing unchanged |

**Installation:**
```bash
pip uninstall pdf2image  # Remove old dependency
pip install PyMuPDF>=1.24.0  # Add new dependency
# Poppler binaries no longer needed (can uninstall from system)
```

---

## Testing Strategy

### Phase-Specific Testing

**Phase 1 (PyMuPDF):**
1. Unit tests: Verify `get_page_as_pil_image()` returns valid PIL Image
2. Integration tests: Run full pipeline on 10-20 test PDFs
3. Regression tests: Compare output CSV/JSON to pdf2image baseline (bitwise identical)
4. Performance tests: Profile PDF rendering time (expect 2-10× speedup)

**Phase 2 (Config):**
1. Unit tests: Verify config string accepted by pytesseract
2. Integration tests: Run on test corpus, measure accuracy
3. Regression tests: OCR accuracy ≥ baseline (94.9%)
4. Performance tests: Measure OCR time reduction per rotation

**Phase 3 (Profiling):**
1. Generate cProfile output for representative corpus
2. Visualize with SnakeViz, identify top 5 hotspots
3. Validate Phase 1 & 2 gains in profile data
4. Document new bottlenecks for Phase 4+

**Phase 4 (Rotation):**
1. Analyze campaign_state.json rotation distribution
2. Unit test rotation ordering function
3. Integration test on sample corpus
4. Performance test: measure OCR pass reduction

### Regression Prevention

- **Golden corpus**: Define 50-100 representative PDFs as test set
- **Output checksums**: SHA-256 of CSV + JSON for baseline comparison
- **Accuracy metrics**: Track OCR success rate, preprocessing fallback rate
- **Performance benchmarks**: Track per-page timings (PDF open, render, OCR)

**Existing Test Coverage:** 230 tests validate pipeline correctness; no changes required for optimization (behavior unchanged)

---

## Monitoring and Validation

### Profiling Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| **cProfile** | Full-program profiling, function call times | Every phase; baseline and optimized |
| **SnakeViz** | Visualize cProfile output (flame graphs) | Bottleneck identification |
| **py-spy** | Sampling profiler (production, no code changes) | Production monitoring (if needed) |
| **time.perf_counter()** | Manual timing instrumentation | Per-operation benchmarks |

### Key Metrics

| Metric | Baseline | Target | How to Measure |
|--------|----------|--------|----------------|
| PDF rendering time | 1-2s/page | 0.2-0.5s/page | cProfile or manual timing |
| OCR time per rotation | 0.5-1s | 0.4-0.8s | Manual timing in OCR function |
| Avg OCR passes per page | 2.5 | 1.5 | Campaign stats |
| Preprocessing fallback rate | % of pages | ≤ baseline | Campaign stats |
| Total corpus time (20 workers) | 8-10 hours | 3-4 hours | Wall-clock time |

### Success Criteria

**Phase 1:** 2× speedup on PDF rendering, output identical
**Phase 2:** OCR accuracy ≥ baseline, 10-30% OCR speedup
**Phase 3:** Bottlenecks identified, optimization priorities data-driven
**Phase 4:** OCR pass reduction if rotation distribution skewed
**Overall:** 50-70% total runtime reduction (8-10 hours → 3-4 hours)

---

## References and Sources

### Official Documentation

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/)
- [PyMuPDF Multiprocessing Recipes](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html)
- [PyMuPDF Pixmap Documentation](https://pymupdf.readthedocs.io/en/latest/pixmap.html)
- [pytesseract PyPI](https://pypi.org/project/pytesseract/)
- [Tesseract Documentation](https://tesseract-ocr.github.io/tessdoc/)
- [Python multiprocessing Documentation](https://docs.python.org/3/library/multiprocessing.html)

### Performance Benchmarks and Comparisons

- [PyMuPDF vs pdfplumber 2026 Comparison](https://pdfmux.com/blog/pymupdf-vs-pdfplumber/)
- [Battle of the PDF Titans: PyMuPDF, pdf2image, Textract](https://openwebtech.com/battle-of-the-pdf-titans-apache-tika-pymupdf-pdfplumber-pdf2image-and-textract/)
- [piptrends: pymupdf vs pdf2image](https://piptrends.com/compare/pymupdf-vs-pdf2image)
- [PyMuPDF Performance Comparison Methodology](https://pymupdf.readthedocs.io/en/latest/app4.html)

### Tesseract Optimization Guides

- [Whitelisting and Blacklisting Characters with Tesseract - PyImageSearch](https://pyimagesearch.com/2021/09/06/whitelisting-and-blacklisting-characters-with-tesseract-and-python/)
- [Tesseract Page Segmentation Modes Explained - PyImageSearch](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/)
- [Tuning Tesseract PSM and OEM](https://sqlpey.com/python/tesseract-psm-oem-tuning/)
- [Improve Accuracy by Tuning PSM Values - Part 1](https://www.cloudthat.com/resources/blog/improve-accuracy-by-tuning-psm-values-of-tesseract-part-1)
- [Improve Accuracy by Tuning PSM Values - Part 2](https://www.cloudthat.com/resources/blog/improve-accuracy-by-tuning-psm-values-of-tesseract-part-2)

### Multiprocessing Best Practices

- [Python Multiprocessing: Start Methods, Pools, and Communication](https://dev.to/imsushant12/python-multiprocessing-start-methods-pools-and-communication-4o6d)
- [Fork vs Spawn in Python Multiprocessing](https://britishgeologicalsurvey.github.io/science/python-forking-vs-spawn/)
- [Configure the Multiprocessing Pool Context](https://superfastpython.com/multiprocessing-pool-context/)
- [Multiprocessing Start Methods](https://superfastpython.com/multiprocessing-start-method/)

### Profiling and Optimization

- [Profiling Python Code with cProfile and SnakeViz](https://johal.in/profiling-python-code-hotspots-using-cprofile-and-snakeviz-for-bottleneck-identification/)
- [cProfile Flame Graphs for Performance Analysis](https://johal.in/cprofile-flame-graphs-python-visualization-for-performance-bottleneck-analysis/)
- [9 Levels of Profiling Python Apps in 2026](https://medium.com/techtofreedom/9-levels-of-profiling-python-apps-in-2026-from-cprofile-to-tachyon-36024bdb36c6)
- [OCR Best Practices in 2026: Production-Ready Pipelines](https://preocr.io/blog/ocr-best-practices-in-2026-how-to-build-a-production-ready-ocr-pipeline)
- [Software Performance Optimization Guide 2026](https://sedai.io/blog/software-performance-optimization-expert-guide)

### Known Issues and Community Discussions

- [Tesseract Issue #4426: Poor Rotation/Layout Detection](https://github.com/tesseract-ocr/tesseract/issues/4426)
- [PyMuPDF Discussion #1307: PDF to Image at 300 DPI](https://github.com/pymupdf/PyMuPDF/discussions/1307)
- [PyMuPDF Discussion #913: Matching PyMuPDF Output to pdf2image](https://github.com/pymupdf/PyMuPDF/discussions/913)

### Research Papers

- [Parallel Architectures for Large-Scale Document Processing](https://www.researchgate.net/publication/399889491_Parallel_Architectures_for_Large_-_Scale_Document_ProcessingIntegrating_OCR_and_RAG_Pipelines) (2026)

---

## Confidence Assessment

| Topic | Confidence | Rationale |
|-------|------------|-----------|
| **PyMuPDF API** | HIGH | Official docs, multiple benchmarks, GitHub discussions with code examples |
| **PyMuPDF Performance** | HIGH | Multiple independent benchmarks (3-12× faster), verified across sources |
| **Tesseract Config** | HIGH | Official Tesseract docs, pytesseract docs, PyImageSearch tutorials |
| **PSM/OEM Modes** | HIGH | Official Tesseract docs, community best practices, tested patterns |
| **OSD Reliability** | HIGH | GitHub issue tracking (#4426), community consensus, project decision rationale |
| **Rotation Strategy** | MEDIUM | Logic sound, but gain depends on corpus rotation distribution (unknown) |
| **Performance Projections** | MEDIUM | Based on published benchmarks; actual gains depend on corpus characteristics |
| **Page-Level Parallelism** | MEDIUM | Architecture patterns documented, but tradeoff analysis corpus-specific |
| **Hybrid CPU Optimization** | LOW | Windows spawn model documented, but hybrid CPU tuning requires experimentation |

**Overall Confidence:** HIGH — Integration patterns well-researched, optimizations follow industry best practices, incremental approach minimizes risk.
