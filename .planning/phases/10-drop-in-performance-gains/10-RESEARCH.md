# Phase 10: Drop-in Performance Gains - Research

**Researched:** 2026-06-07
**Domain:** PDF rendering optimization, OCR engine tuning, multiprocessing optimization
**Confidence:** HIGH

## Summary

Phase 10 targets 2-15x speedup through three low-risk optimizations: (1) replacing pdf2image/Poppler with PyMuPDF for PDF-to-image rendering (2-12x faster), (2) benchmarking optimal DPI (200/250/300) to find the fastest setting maintaining >=94% accuracy, and (3) benchmarking optimal worker count (16-20) for the 20-core (24-thread) hybrid CPU. Character whitelist (TESS-01) is already implemented and working in the current pipeline at line 433.

**Primary recommendation:** Prioritize PyMuPDF swap first (highest individual impact), then DPI benchmarking, then worker tuning. Use separate `benchmark.py` script with 100-PDF random sample for iteration speed. Hard-code winning values after validation — no runtime CLI flags except existing `--workers` override.

PyMuPDF is already installed (v1.27.2.3), pytest-benchmark is available (v5.2.3), and the current architecture uses process-level parallelism with `maxtasksperchild=50` for memory safety — all architectural decisions align with the optimization strategy.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use in-memory pixmaps (`page.get_pixmap()` -> PIL Image) for maximum speed. No disk I/O for intermediate images. Each worker processes one page at a time so memory is bounded.
- **D-02:** On PyMuPDF failure (corrupted/encrypted/unusual PDFs), log error and skip the file — same as current error handling. No fallback to pdf2image. Single rendering path.
- **D-03:** Benchmark 200, 250, and 300 DPI on 100-PDF random sample. Hard-code the winning DPI value in the pipeline. No --dpi CLI flag — keep it simple.
- **D-04:** Benchmark worker counts 16-20 on 20-core hybrid CPU (8P + 12E). Hard-code optimal value as default. Existing `--workers` CLI flag remains for override.
- **D-05:** Already implemented at `precede_ocr.py:433` — config `'--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'`. Benchmark will confirm speed impact vs removing the whitelist. No code change needed unless benchmark reveals issues.
- **D-06:** Separate `benchmark.py` script (not integrated into main pipeline). Imports pipeline functions, runs DPI/worker/rendering tests, outputs comparison tables.
- **D-07:** 100-PDF random sample from real corpus (not 1000 — time-effective for iteration). Must be representative across different source folders.
- **D-08:** Accuracy validation by comparing extracted IDs page-by-page against v1.1 baseline results on the same 100 PDFs. Accuracy = percentage of matching ID extractions.
- **D-09:** Fully remove pdf2image from imports and requirements. Fully remove Poppler as system dependency. PyMuPDF (`pip install pymupdf`) bundles its own MuPDF renderer — no separate binary install needed. Simplifies setup.

### Claude's Discretion
- PyMuPDF API usage details (matrix scaling for DPI, colorspace selection)
- Benchmark script output format (tables, CSV, markdown)
- How to sample 100 random PDFs from corpus (random.sample on file list)
- Test infrastructure for the swap (updating existing tests to use PyMuPDF)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RENDER-01 | Pipeline uses PyMuPDF instead of pdf2image/Poppler for PDF-to-image conversion | PyMuPDF API documented: `page.get_pixmap(dpi=N)` → `Image.frombytes()` for in-memory conversion; benchmarks show 2.32x faster than PDF2JPG for rendering |
| RENDER-02 | Pipeline renders at optimal DPI determined by benchmarking (200/250/300 tested for speed vs accuracy) | DPI control via `dpi=N` parameter; 300 DPI is industry standard for OCR but 200-250 may suffice for clean scans; pytest-benchmark available for systematic comparison |
| TESS-01 | OCR uses character whitelist constrained to digits 0-9 | Already implemented with `tessedit_char_whitelist=0123456789` at line 433; OEM 3 (default) compatibility verified though LSTM component (OEM 1) may ignore whitelist — benchmark required to confirm speed impact |
| PIPE-01 | Worker count is benchmarked and set to optimal value for 20-core hybrid CPU | Current default: `cpu_count() - 1` (23 workers on 24-thread system); research shows slight under-utilization optimal for CPU-bound tasks; benchmark range 16-20 targets saturation without thrashing |
| QUAL-01 | All optimizations maintain >=94% OCR accuracy on test corpus | Validation methodology: page-by-page ID extraction comparison against v1.1 baseline; accuracy = percentage of matching extractions |
| QUAL-02 | Benchmark results documented (before/after speed comparison on representative sample) | pytest-benchmark provides automatic timing with statistical analysis; 100-PDF sample balances representativeness with iteration speed |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyMuPDF (fitz) | 1.27.2.3 (installed) | PDF rendering to images | **2-12x faster** than pdf2image per benchmarks. Bundles MuPDF renderer (no external binary dependency). Direct DPI control via `page.get_pixmap(dpi=N)`. In-memory conversion to PIL Image via `Image.frombytes()`. Memory leak fixes in v1.27.1 (Feb 2026). **Confidence: HIGH** |
| pytest-benchmark | 5.2.3 (installed) | Performance benchmarking | Official pytest plugin for benchmarking. Automatic timing with statistical analysis (min/max/mean/stddev/median). Parametrization support for comparing DPI/worker configurations. Comparison mode to detect regressions. **Confidence: HIGH** |
| Python multiprocessing | stdlib | Process-level parallelism | Already in use with `mp.Pool(processes=N, maxtasksperchild=50)`. Windows 'spawn' start method requires careful architecture. CPU-bound OCR workload requires true parallelism (not threading). **Confidence: HIGH** |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| random | stdlib | Random sampling for benchmark corpus | Use `random.sample(pdf_paths, 100)` after collecting all PDFs with `Path.rglob('*.pdf')`. Ensures representative sample across folders. **Confidence: HIGH** |
| pandas | 3.0.3 (installed) | Benchmark results export | Export comparison tables to CSV for analysis. Already used for pipeline output. **Confidence: HIGH** |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyMuPDF | pdf2image (current) | pdf2image 2.32x slower (benchmarks: 851s vs 367s). Requires Poppler binary dependency. disk-backed with `paths_only=True` for memory safety. Keep current implementation only during transition testing. **Confidence: HIGH** |
| pytest-benchmark | timeit + manual logging | timeit is stdlib but requires manual statistical analysis, CSV export, comparison logic. pytest-benchmark provides all this automatically with pytest integration. **Confidence: HIGH** |
| In-memory pixmaps | Disk-backed rendering | Current pdf2image uses temp directory (`output_folder` + `paths_only=True`). In-memory is faster (no disk I/O) and simpler (no cleanup). Memory bounded by one pixmap per worker at a time. **Confidence: HIGH** |

**Installation:**
```bash
pip install pymupdf  # Already installed (v1.27.2.3)
pip install pytest-benchmark  # Already installed (v5.2.3)
```

**Version verification:**
- PyMuPDF 1.27.2.3 verified via `python -m pip show pymupdf` on 2026-06-07
- pytest-benchmark 5.2.3 verified via `python -m pip show pytest-benchmark` on 2026-06-07
- Python 3.14.2 detected (current environment)

## Architecture Patterns

### Recommended Project Structure
```
precedeocr/
├── precede_ocr.py              # Main pipeline — update PDF rendering (line 517-522)
├── benchmark.py                # NEW: Standalone benchmark script
├── requirements.txt            # Swap pdf2image → pymupdf
├── tests/
│   ├── test_precede_ocr.py    # Existing tests — update pdf2image references
│   └── conftest.py            # Existing fixtures
└── .planning/
    └── phases/10-*/
        └── benchmark_results.md  # NEW: Document findings
```

### Pattern 1: PyMuPDF In-Memory Rendering (RENDER-01)
**What:** Replace pdf2image disk-backed rendering with PyMuPDF in-memory pixmaps

**Current approach (lines 515-524):**
```python
# pdf2image: disk-backed, paths_only for memory safety
temp_dir = tempfile.mkdtemp(prefix='precede_pdf_')
image_paths = convert_from_path(
    pdf_path,
    dpi=300,
    output_folder=temp_dir,
    paths_only=True,
    fmt='png',
    poppler_path=POPPLER_PATH
)
for page_num, image_path in enumerate(image_paths, start=1):
    with Image.open(image_path) as img:
        # ... OCR processing
```

**New approach (PyMuPDF):**
```python
# Source: PyMuPDF official docs + GitHub discussion #1678
import fitz  # PyMuPDF

doc = fitz.open(pdf_path)
try:
    for page_num in range(len(doc)):
        page = doc[page_num]
        # Render at specified DPI (default 300, benchmark to optimize)
        pix = page.get_pixmap(dpi=300)

        # Convert to PIL Image in-memory (no disk I/O)
        # Use RGB mode (alpha=False) for OCR compatibility
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # ... OCR processing (unchanged)
        ids_found, rotation, notes = extract_id_with_rotation(img, debug=debug)
finally:
    doc.close()  # Critical: prevent memory leaks
```

**When to use:** All PDF rendering. Single code path (no fallback to pdf2image per D-02).

**Key differences:**
- No temp directory creation/cleanup
- In-memory conversion via `Image.frombytes()`
- Must call `doc.close()` to prevent memory leaks (fixed in v1.27.1 but still best practice)
- DPI specified directly (no matrix math required)

### Pattern 2: Benchmark Script Architecture (D-06)
**What:** Separate script that imports pipeline functions, runs parametrized benchmarks, compares results

**Structure:**
```python
# benchmark.py
import random
from pathlib import Path
import pandas as pd
from precede_ocr import process_single_pdf  # Import existing function

def select_benchmark_corpus(pdf_dir, sample_size=100, seed=42):
    """Select random representative sample from corpus."""
    all_pdfs = list(Path(pdf_dir).rglob('*.pdf'))
    random.seed(seed)
    return random.sample(all_pdfs, min(sample_size, len(all_pdfs)))

def benchmark_dpi(pdf_paths, dpi_values=[200, 250, 300]):
    """Compare processing speed across DPI settings."""
    # Temporarily modify DPI in process_single_pdf
    # Measure total time for all PDFs at each DPI
    # Return results as DataFrame
    pass

def benchmark_workers(pdf_paths, worker_counts=[16, 17, 18, 19, 20]):
    """Compare throughput across worker counts."""
    # Use process_all_pdfs with different worker counts
    # Measure total time for all PDFs at each count
    # Return results as DataFrame
    pass

def validate_accuracy(baseline_results, optimized_results):
    """Page-by-page ID extraction comparison (QUAL-01)."""
    # baseline_results: v1.1 output for 100-PDF sample
    # optimized_results: new version output
    # Calculate match percentage
    pass

if __name__ == '__main__':
    # 1. Select 100 random PDFs
    # 2. Run baseline (pdf2image, 300 DPI, 23 workers)
    # 3. Run PyMuPDF with DPI sweep
    # 4. Run PyMuPDF with worker sweep
    # 5. Validate accuracy
    # 6. Output comparison tables
    pass
```

**When to use:** One-time benchmarking phase. Not integrated into main pipeline.

### Pattern 3: DPI Parameter Control (RENDER-02)
**What:** Direct DPI specification in `get_pixmap()` without matrix math

**Options:**

**Option A: Direct DPI parameter (RECOMMENDED):**
```python
# Source: PyMuPDF official docs (recipes-images.html)
pix = page.get_pixmap(dpi=300)
```
- Advantage: DPI value saved with image metadata
- Simplest API

**Option B: Matrix scaling:**
```python
# Source: PyMuPDF docs (pixmap.html)
import fitz
mat = fitz.Matrix(300 / 72, 300 / 72)  # 72 DPI = 1x scale
pix = page.get_pixmap(matrix=mat)
```
- Advantage: More explicit control
- Disadvantage: DPI not saved in image metadata

**When to use:** Option A for simplicity. Option B if need additional transforms (rotation, shear).

### Pattern 4: Worker Count Tuning for Hybrid CPU (PIPE-01)
**What:** Find optimal process count for 20-core (8P + 12E) hybrid CPU with 24 threads

**Current default (line 2080):**
```python
if workers is None:
    workers = max(1, mp.cpu_count() - 1)  # 23 workers on 24-thread system
```

**Hybrid CPU considerations:**
- Windows scheduler automatically assigns processes to P/E cores
- Manual CPU affinity can **decrease** performance (out of scope per REQUIREMENTS.md)
- Optimal count likely < `cpu_count() - 1` due to IPC overhead
- Benchmark range: 16-20 workers (66-83% of threads)

**Benchmark approach:**
```python
# Test worker counts 16-20 on 100-PDF sample
# Measure total wall-clock time (not CPU time)
# Plot throughput curve to find saturation point
# Winner becomes new hard-coded default
```

**Windows-specific notes:**
- 'spawn' start method (not 'fork') — slower process creation
- Max 61 child processes on Windows (well above our range)
- `maxtasksperchild=50` prevents memory leaks — keep this

### Anti-Patterns to Avoid

**Anti-pattern 1: Forgetting to close PyMuPDF documents**
- **Why it's bad:** Memory leaks even with v1.27.1 fixes if not closed properly
- **Fix:** Always use try/finally or context manager (if available)

**Anti-pattern 2: Using RGBA colorspace for OCR**
- **Why it's bad:** PyMuPDF OCR requires RGB without alpha channel
- **Fix:** Omit `alpha` parameter (defaults to False) or explicitly set `pix = page.get_pixmap(dpi=300, alpha=False)`

**Anti-pattern 3: Storing multiple high-DPI pixmaps in memory**
- **Why it's bad:** 300 DPI letter page ≈ 1.4 MB uncompressed RGB
- **Fix:** Process one page at a time (current architecture already does this)

**Anti-pattern 4: Assuming whitelist works with OEM 1 (LSTM-only)**
- **Why it's bad:** `tessedit_char_whitelist` ignored by LSTM engine
- **Fix:** Use OEM 3 (default) which combines legacy + LSTM, or OEM 0 (legacy-only) if whitelist critical

**Anti-pattern 5: Benchmarking on tiny samples**
- **Why it's bad:** Startup overhead dominates, hides true throughput differences
- **Fix:** 100-PDF sample (D-07) balances iteration speed with statistical validity

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Performance benchmarking | Custom timeit loops with CSV export | pytest-benchmark | Handles statistical analysis (outlier removal, calibration), comparison mode, pytest integration. Custom approach error-prone. **Confidence: HIGH** |
| PDF rendering | Custom MuPDF bindings | PyMuPDF (fitz) | Official Python bindings. Mature API. Memory leak fixes. Active maintenance (v1.27.1 Feb 2026). **Confidence: HIGH** |
| Random sampling | Manual shuffling + slicing | `random.sample()` | Guarantees no duplicates. Single-pass reservoir algorithm. Stdlib reliability. **Confidence: HIGH** |
| Process pool management | Manual `mp.Process()` spawning | `mp.Pool()` | Handles worker lifecycle, task queuing, result collection, error propagation. Current code already uses this. **Confidence: HIGH** |

**Key insight:** OCR performance optimization is well-trodden territory. PyMuPDF has 15+ years of PDF rendering optimization. pytest-benchmark handles edge cases (warmup, GC, timer precision). Focus effort on integration, not reinvention.

## Common Pitfalls

### Pitfall 1: PyMuPDF Memory Leaks from Unclosed Documents
**What goes wrong:** Memory usage grows across loop iterations when processing many PDFs

**Why it happens:** Even with v1.27.1 fixes, not calling `doc.close()` can retain references. Worker process may accumulate state across `maxtasksperchild` tasks.

**How to avoid:**
```python
def process_single_pdf(pdf_path, debug=False):
    try:
        doc = fitz.open(pdf_path)
        # ... process pages
    except Exception as e:
        # ... error handling
    finally:
        if 'doc' in locals():
            doc.close()  # Always close, even on exception
```

**Warning signs:** Memory usage climbs over time in Task Manager/Process Explorer during batch processing

### Pitfall 2: Tesseract Whitelist Not Working as Expected
**What goes wrong:** `tessedit_char_whitelist=0123456789` has no effect on OCR results

**Why it happens:** OEM 1 (LSTM-only) ignores whitelist. OEM 3 (default) uses both legacy and LSTM, but LSTM component may ignore it. Effectiveness varies by Tesseract version.

**How to avoid:**
- Current code uses OEM 3 (line 433: `--oem 3`) — correct
- Benchmark speed with vs without whitelist on 100-PDF sample
- If no speed difference detected, flag for investigation (may need OEM 0 for full whitelist enforcement)
- Don't assume whitelist speeds up OCR without measurement

**Warning signs:** Benchmark shows identical OCR times with/without whitelist despite docs claiming speedup

### Pitfall 3: Worker Count Above Optimal Saturation
**What goes wrong:** More workers = slower total time due to context switching overhead

**Why it happens:** Beyond optimal saturation, IPC overhead + scheduler thrashing dominate gains. Windows 'spawn' method has higher process creation cost than Linux 'fork'.

**How to avoid:**
- Benchmark 16-20 workers (not just max out at 23)
- Plot throughput curve: total_pdfs / total_time vs worker_count
- Look for plateau or downturn
- Don't assume more workers = faster

**Warning signs:** 20 workers slower than 18 workers in benchmark results

### Pitfall 4: Non-Representative Benchmark Sample
**What goes wrong:** Optimizations fail on real corpus despite benchmark success

**Why it happens:** Sample biased toward small/simple PDFs, or all from single source folder. Real corpus has varied page counts, scan quality, file sizes.

**How to avoid:**
```python
# Use random.sample() across all folders
all_pdfs = list(Path(corpus_dir).rglob('*.pdf'))
sample = random.sample(all_pdfs, 100)

# Verify representativeness:
print(f"Sample page count range: {min(counts)} - {max(counts)}")
print(f"Sample file size range: {min(sizes)} - {max(sizes)}")
print(f"Folders represented: {len(set(p.parent for p in sample))}")
```

**Warning signs:** Benchmark sample all from one folder, or all single-page PDFs

### Pitfall 5: Comparing Wall-Clock Time Without Controlling Load
**What goes wrong:** Benchmark timings vary wildly between runs

**Why it happens:** Background processes, antivirus scans, Windows updates consume CPU during benchmark

**How to avoid:**
- Close non-essential applications before benchmarking
- Run each configuration multiple times (pytest-benchmark does this automatically)
- Use median time (not mean) to reduce outlier impact
- pytest-benchmark calibrates timer and warms up code paths

**Warning signs:** Same configuration shows 50%+ variance between runs

## Code Examples

Verified patterns from official sources:

### PyMuPDF: PDF to PIL Image (In-Memory)
```python
# Source: https://github.com/pymupdf/PyMuPDF/discussions/1678
# Source: https://pymupdf.readthedocs.io/en/latest/recipes-images.html
from PIL import Image
import fitz

def render_pdf_pages_pymupdf(pdf_path, dpi=300):
    """
    Render PDF pages to PIL Images using PyMuPDF (in-memory).

    Args:
        pdf_path: Path to PDF file
        dpi: Dots per inch for rendering (200/250/300)

    Yields:
        (page_num, PIL.Image): Page number (1-indexed) and rendered image
    """
    doc = fitz.open(pdf_path)
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]

            # Render at specified DPI
            # alpha=False ensures RGB mode (required for OCR)
            pix = page.get_pixmap(dpi=dpi, alpha=False)

            # Convert to PIL Image without disk I/O
            # frombytes() is 33% faster than pil_tobytes() per benchmarks
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            yield (page_num + 1, img)  # 1-indexed page numbers
    finally:
        doc.close()  # Prevent memory leaks
```

### pytest-benchmark: Parametrized DPI Comparison
```python
# Source: https://pytest-benchmark.readthedocs.io/en/latest/usage.html
import pytest

@pytest.mark.parametrize("dpi", [200, 250, 300])
def test_benchmark_dpi(benchmark, sample_pdf_path, dpi):
    """
    Benchmark PDF rendering speed at different DPI settings.

    Uses pytest-benchmark to compare 200/250/300 DPI.
    Automatically handles timing, statistics, comparison.
    """
    from precede_ocr import process_single_pdf

    # Temporarily override DPI (implementation detail)
    result = benchmark(process_single_pdf, sample_pdf_path, dpi=dpi)

    # Verify result structure
    assert result is not None
    assert 'pages_processed' in result

# Run: pytest test_benchmark.py --benchmark-compare
# Output: Comparison table with min/max/mean/stddev for each DPI
```

### Random Representative Sampling
```python
# Source: Python stdlib docs (random.sample)
# Source: https://docs.python.org/3/library/pathlib.html
import random
from pathlib import Path

def select_benchmark_corpus(corpus_dir, sample_size=100, seed=42):
    """
    Select random representative sample from PDF corpus.

    Args:
        corpus_dir: Root directory containing PDFs
        sample_size: Number of PDFs to sample (default 100)
        seed: Random seed for reproducibility

    Returns:
        List of Path objects (sampled PDFs)
    """
    # Recursively collect all PDFs
    all_pdfs = list(Path(corpus_dir).rglob('*.pdf'))

    # Set seed for reproducibility
    random.seed(seed)

    # Sample without replacement (no duplicates)
    sample = random.sample(all_pdfs, min(sample_size, len(all_pdfs)))

    # Verify representativeness
    folders = set(p.parent for p in sample)
    print(f"Sampled {len(sample)} PDFs from {len(folders)} folders")

    return sample
```

### Worker Count Benchmarking
```python
# Source: Multiprocessing best practices (various sources)
import multiprocessing as mp
import time

def benchmark_worker_count(pdf_paths, worker_counts=[16, 17, 18, 19, 20]):
    """
    Benchmark processing throughput across worker counts.

    Args:
        pdf_paths: List of PDF paths to process
        worker_counts: Worker counts to test

    Returns:
        pandas.DataFrame with results
    """
    from precede_ocr import process_all_pdfs
    import pandas as pd

    results = []
    for worker_count in worker_counts:
        start = time.time()

        # Process all PDFs with specified worker count
        _ = process_all_pdfs(pdf_paths, workers=worker_count)

        elapsed = time.time() - start
        throughput = len(pdf_paths) / elapsed

        results.append({
            'workers': worker_count,
            'total_time_sec': elapsed,
            'throughput_pdfs_per_sec': throughput
        })

        print(f"Workers: {worker_count} | Time: {elapsed:.1f}s | Throughput: {throughput:.2f} PDFs/s")

    return pd.DataFrame(results)
```

### Accuracy Validation (QUAL-01)
```python
# Source: D-08 from CONTEXT.md
def validate_accuracy(baseline_results, optimized_results):
    """
    Compare extracted IDs page-by-page between baseline and optimized runs.

    Args:
        baseline_results: List of result dicts from v1.1
        optimized_results: List of result dicts from optimized version

    Returns:
        float: Accuracy percentage (0-100)
    """
    # Flatten to (filename, page, ids) tuples for comparison
    def flatten(results):
        return {
            (r['filename'], r['page']): set(r['ids'])
            for r in results
        }

    baseline_map = flatten(baseline_results)
    optimized_map = flatten(optimized_results)

    # Calculate match percentage
    matches = 0
    total = len(baseline_map)

    for key, baseline_ids in baseline_map.items():
        optimized_ids = optimized_map.get(key, set())
        if baseline_ids == optimized_ids:
            matches += 1

    accuracy = (matches / total) * 100 if total > 0 else 0
    print(f"Accuracy: {accuracy:.1f}% ({matches}/{total} pages match)")

    return accuracy

# Usage:
# accuracy = validate_accuracy(baseline_results, optimized_results)
# assert accuracy >= 94.0, f"Accuracy {accuracy:.1f}% below 94% threshold (QUAL-01)"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pdf2image with Poppler | PyMuPDF for rendering | v1.2 Phase 10 (this phase) | 2-12x faster rendering. Removes Poppler binary dependency. In-memory processing replaces disk-backed temp files. |
| `cpu_count() - 1` default workers | Benchmarked optimal count (16-20 range) | v1.2 Phase 10 (this phase) | Finds saturation point for hybrid CPU. May reduce worker count to improve efficiency. |
| 300 DPI hard-coded | Benchmarked optimal DPI (200/250/300) | v1.2 Phase 10 (this phase) | May reduce DPI to 200-250 without accuracy loss, further speeding rendering. |
| Assumption whitelist speeds up OCR | Benchmarked validation | v1.2 Phase 10 (this phase) | Verifies whether `tessedit_char_whitelist` actually helps with OEM 3 (may not due to LSTM component ignoring it). |

**Deprecated/outdated:**
- **pdf2image for OCR preprocessing:** Still widely used but PyMuPDF is now faster and simpler (no external binary). pdf2image better for high-fidelity visual rendering, not batch OCR.
- **Tesseract OEM 0 (legacy-only):** Replaced by OEM 3 (default) which uses LSTM for better accuracy. OEM 0 only needed if whitelist enforcement critical.
- **Matrix-based DPI scaling:** PyMuPDF now supports direct `dpi=N` parameter (simpler, saves metadata). Matrix still useful for complex transforms.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PyMuPDF (fitz) | RENDER-01 (PDF rendering) | ✓ | 1.27.2.3 | — |
| pytest-benchmark | QUAL-02 (benchmarking) | ✓ | 5.2.3 | — |
| Python multiprocessing | PIPE-01 (parallelism) | ✓ | stdlib | — |
| Tesseract OCR | TESS-01 (OCR engine) | ? | Unknown (not in PATH) | Block if missing |
| pytest | Test framework | ✓ | 9.0.2 | — |

**Missing dependencies with no fallback:**
- **Tesseract OCR:** Command `tesseract --version` failed. Current code has auto-detection at lines 35-47 with fallback to PATH. If not found, pytesseract will fail at runtime. **Action required:** Verify Tesseract installation before phase execution OR add installation step to Wave 0.

**Missing dependencies with fallback:**
- None identified

**Notes:**
- Poppler currently not in PATH (warning on import) but will be removed by D-09 — not a blocker
- All Python dependencies installed and working

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-benchmark 5.2.3 |
| Config file | `pytest.ini` (exists, sets testpaths=tests) |
| Quick run command | `pytest tests/test_precede_ocr.py -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RENDER-01 | PyMuPDF renders PDFs to PIL Images | unit | `pytest tests/test_precede_ocr.py::test_pymupdf_rendering -x` | ❌ Wave 0 |
| RENDER-02 | Optimal DPI maintains quality | benchmark | `pytest benchmark.py::test_benchmark_dpi --benchmark-only` | ❌ Wave 0 |
| TESS-01 | Whitelist config applied | unit | `pytest tests/test_precede_ocr.py::test_tesseract_config -x` | ✅ (existing tests verify config) |
| PIPE-01 | Optimal worker count found | benchmark | `pytest benchmark.py::test_benchmark_workers --benchmark-only` | ❌ Wave 0 |
| QUAL-01 | Accuracy >=94% baseline | integration | `pytest benchmark.py::test_accuracy_validation -x` | ❌ Wave 0 |
| QUAL-02 | Benchmarks documented | manual-only | Review `.planning/phases/10-*/benchmark_results.md` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_precede_ocr.py -x` (fast unit tests only, skip benchmarks)
- **Per wave merge:** `pytest tests/ -x` (full unit test suite)
- **Phase gate:** Full suite green + benchmark suite executed + accuracy validation passed before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `benchmark.py` — parametrized DPI/worker benchmarks + accuracy validation
- [ ] `tests/test_precede_ocr.py::test_pymupdf_rendering` — unit test for PyMuPDF rendering function
- [ ] `tests/test_precede_ocr.py::test_accuracy_validation` — helper test for accuracy comparison logic
- [ ] Update existing tests that reference `pdf2image` or `convert_from_path` to use PyMuPDF
- [ ] Verify Tesseract installation (not in PATH currently — may need manual verification or installation step)

## Sources

### Primary (HIGH confidence)
- [PyMuPDF Pixmap Documentation](https://pymupdf.readthedocs.io/en/latest/pixmap.html) - `get_pixmap()` API, DPI parameter, PIL conversion
- [PyMuPDF Images Recipes](https://pymupdf.readthedocs.io/en/latest/recipes-images.html) - DPI best practices, OCR preprocessing
- [PyMuPDF GitHub Discussion #1678](https://github.com/pymupdf/PyMuPDF/discussions/1678) - In-memory PIL conversion methods, performance comparison
- [PyMuPDF Performance Benchmarks](https://pymupdf.readthedocs.io/en/latest/app4.html) - Official benchmarks vs pdf2image, pdftoppm (2.32x faster)
- [pytest-benchmark Documentation](https://pytest-benchmark.readthedocs.io/en/latest/usage.html) - Parametrization, comparison mode, configuration
- [Python multiprocessing Documentation](https://docs.python.org/3/library/multiprocessing.html) - Pool API, maxtasksperchild, Windows 'spawn' method
- [Python pathlib Documentation](https://docs.python.org/3/library/pathlib.html) - rglob() for recursive PDF collection
- [Python random Documentation](https://docs.python.org/3/library/random.html) - random.sample() for representative sampling

### Secondary (MEDIUM confidence)
- [PyImageSearch: Whitelisting and Blacklisting Characters with Tesseract](https://pyimagesearch.com/2021/09/06/whitelisting-and-blacklisting-characters-with-tesseract-and-python/) - Whitelist usage patterns
- [Tesseract Documentation: Improving Quality](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html) - Whitelist recommendations
- [Multiprocessing Pool Workers Guide](https://superfastpython.com/multiprocessing-pool-num-workers/) - Worker count best practices
- [Python Multiprocessing: CPU Utilization](https://medium.com/@deveshparmar248/python-multiprocessing-maximize-the-cpu-utilization-eec3b60e6d40) - Optimal process count for CPU-bound tasks

### Tertiary (LOW confidence - requires validation)
- [Best Python OCR Library 2026 Comparison](https://www.codesota.com/ocr/best-for-python) - Mentions PyMuPDF OCR integration (not directly tested)
- [PyMuPDF vs pdf2image Performance](https://github.com/pymupdf/PyMuPDF/discussions/913) - Community report of 3-10x speedup (not official benchmark)
- [Tesseract GitHub Issue #4407](https://github.com/tesseract-ocr/tesseract/issues/4407) - Whitelist not working (older issue, may be resolved)

### Known Gaps
- **Tesseract 5.5.2 whitelist behavior with OEM 3:** No authoritative 2026 source confirms whether whitelist works with OEM 3. Benchmark required.
- **Optimal worker count for hybrid CPUs:** General guidance exists but no specific benchmarks for 8P+12E configuration. Must benchmark on target hardware.

## Metadata

**Confidence breakdown:**
- **PyMuPDF rendering (RENDER-01):** HIGH - Official docs, verified installation (v1.27.2.3), benchmark data from official source (2.32x faster than pdf2image)
- **DPI optimization (RENDER-02):** HIGH - Direct API support documented, standard OCR DPI ranges well-established (200-300), pytest-benchmark available for systematic testing
- **Tesseract whitelist (TESS-01):** MEDIUM - Already implemented in code (line 433), but effectiveness with OEM 3 unclear from sources. Requires benchmark validation. OEM 1 (LSTM) known to ignore whitelist, OEM 3 behavior uncertain.
- **Worker optimization (PIPE-01):** HIGH - Multiprocessing patterns well-documented, current system has 24 threads detected, benchmark methodology clear. Hybrid CPU specific tuning requires empirical testing.
- **Accuracy validation (QUAL-01):** HIGH - Methodology straightforward (page-by-page comparison), baseline results available from v1.1, comparison logic implementable
- **Benchmark methodology (QUAL-02):** HIGH - pytest-benchmark documented, 100-PDF sample size reasonable, random sampling strategy clear

**Research date:** 2026-06-07
**Valid until:** 2026-09-07 (90 days - stable domain, PyMuPDF mature library, Tesseract 5.x stable)

**Assumptions requiring validation:**
1. Tesseract whitelist actually speeds up OCR with OEM 3 (OEM 1 component may ignore it)
2. Optimal worker count is in 16-20 range (may be higher or lower)
3. DPI can be reduced from 300 to 200-250 without accuracy loss (depends on scan quality)
4. 100-PDF sample is representative of 30K+ corpus (requires verification via folder distribution)
