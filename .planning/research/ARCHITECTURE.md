# Architecture Patterns: Batch PDF OCR Pipeline

**Domain:** Batch PDF OCR ID extraction system
**Scale:** ~30,429 multi-page PDFs on Windows with Python
**Researched:** 2026-06-04
**Overall Confidence:** HIGH

## Executive Summary

Batch PDF OCR pipelines follow a **producer-consumer pattern** with clear component boundaries: file discovery produces work items, page extraction converts PDFs to images, OCR processing extracts text, extraction logic finds IDs via regex, and result aggregation merges outputs. For 30K+ PDFs on Windows, **multiprocessing with spawn start method** is mandatory (Windows doesn't support fork), using `ProcessPoolExecutor` from `concurrent.futures` for clean API and easy thread/process switching.

**Key architectural insights:**
- **Stage separation** enables independent optimization and failure isolation
- **Queue-based decoupling** handles rate mismatches between fast producers and slow OCR
- **Multi-rotation strategy** processes pages at 0/90/180/270 degrees to handle rotated IDs
- **Preprocessing pipeline** (grayscale → threshold → denoise) runs conditionally as fallback for low-quality scans
- **Build order:** Core single-file flow first, then parallelization, then error handling, finally preprocessing

---

## Recommended Architecture

### High-Level Pipeline Flow

```
┌─────────────────┐
│  File Discovery │  (Producer)
│   Recursive     │
│   .pdf scan     │
└────────┬────────┘
         │ Queue: List[filepath]
         ▼
┌─────────────────┐
│ Page Extractor  │  (Producer)
│  PDF → Images   │
│  (pdf2image)    │
└────────┬────────┘
         │ Queue: List[(filepath, page_num, image)]
         ▼
┌─────────────────┐
│  OCR Processor  │  (Consumer Pool)
│  Multi-rotation │
│  (pytesseract)  │
└────────┬────────┘
         │ Queue: List[(filepath, page_num, text, rotation)]
         ▼
┌─────────────────┐
│ ID Extractor    │  (Filter)
│  Regex matcher  │
│  Validation     │
└────────┬────────┘
         │ Queue: List[(filepath, page_num, id, rotation)]
         ▼
┌─────────────────┐
│ Result Aggregator│  (Accumulator)
│  CSV + JSON     │
│  output writers │
└─────────────────┘
```

---

## Component Boundaries

| Component | Responsibility | Input | Output | Parallelizable? |
|-----------|---------------|-------|--------|-----------------|
| **File Discovery** | Recursively find all `.pdf` files in target directory | Directory path | List of PDF file paths | No (I/O-bound, fast) |
| **Page Extractor** | Convert PDF pages to high-DPI images (300+ DPI) | PDF file path | List of (page_num, PIL.Image) tuples | Yes (CPU-bound) |
| **OCR Processor** | Run Tesseract at 0/90/180/270° rotations, return best result | PIL.Image | (text, rotation_angle) tuple | Yes (CPU + I/O bound, slowest stage) |
| **Preprocessing Pipeline** | Grayscale → threshold → denoise (conditional fallback) | PIL.Image | PIL.Image (enhanced) | Yes (CPU-bound) |
| **ID Extractor** | Regex match 5-digit IDs, validate with pattern | OCR text | List of ID strings or empty | No (fast, in-process) |
| **Result Aggregator** | Accumulate results, write CSV + JSON atomically | Stream of (file, page, id, rotation) | CSV + JSON files | No (serial write to avoid corruption) |
| **Progress Tracker** | Real-time progress bars, ETA, throughput metrics | Event stream | Console output / logs | No (observability only) |
| **Error Handler** | Retry logic, dead-letter queue, logging | Failed work items | Retry queue or DLQ | No (coordination layer) |

### Communication Patterns

- **Between stages:** `multiprocessing.Queue` or return values from `ProcessPoolExecutor.map()`
- **Result collection:** Shared list with lock OR collect from worker returns (preferred for simplicity)
- **Progress tracking:** `tqdm` with `process_map` for automatic progress bars in parallel processing
- **Error propagation:** Exceptions captured in worker pool, logged, and routed to dead-letter queue

---

## Data Flow

### Detailed Processing Sequence

```python
# Conceptual data flow (simplified)

# Stage 1: Discovery
pdf_paths = discover_pdfs(root_dir)
# → ['path/to/file1.pdf', 'path/to/file2.pdf', ...]

# Stage 2: Page Extraction (parallelized)
pages = extract_all_pages(pdf_paths, dpi=300)
# → [(filepath, page_num, PIL.Image), ...]

# Stage 3: OCR Processing (parallelized, multi-rotation)
ocr_results = ocr_all_pages(pages)
# → [(filepath, page_num, text, rotation), ...]

# Stage 4: ID Extraction (in-process filter)
id_records = extract_ids(ocr_results)
# → [(filepath, page_num, id, rotation), ...] or (filepath, page_num, None, None) for no-ID pages

# Stage 5: Aggregation (serial)
write_csv(id_records, "output.csv")
write_json(id_records, "output.json")
```

### Multi-Rotation Strategy

For each page image:
1. Try OCR at **0° (upright)** with regex validation
2. If no 5-digit ID found, rotate **90°** and retry
3. If no match, rotate **180°** and retry
4. If no match, rotate **270°** and retry
5. If still no match after all rotations:
   - Apply **preprocessing pipeline** (grayscale → threshold → denoise)
   - Retry all 4 rotations on enhanced image
6. If still no match, flag page as **"no ID found"**

**Optimization:** Stop early if ID found (don't test all 4 rotations unnecessarily).

**Rationale:** IDs are rotated ~90° from upright, so trying all angles ensures detection regardless of scan orientation. Recent research shows 98% accuracy with rotation classification models, but regex validation after each rotation is simpler and sufficient for 5-digit numeric IDs.

---

## Parallelization Strategy for Windows Python

### Windows-Specific Constraints

**Critical:** Windows uses `spawn` start method (not `fork`), which means:
- Child processes don't inherit parent memory state
- All objects passed to workers must be **picklable**
- Entry point must be protected with `if __name__ == "__main__":`
- Slightly slower startup than fork, but **safer** (no state corruption)

### Recommended Approach: `concurrent.futures.ProcessPoolExecutor`

**Why this over `multiprocessing.Pool`?**
1. **Cleaner API:** Submit work and collect results separately
2. **Easy switching:** Change `ProcessPoolExecutor` → `ThreadPoolExecutor` with one line for testing
3. **Better error handling:** Exceptions propagate cleanly via `Future.result()`
4. **Future-proof:** Higher-level abstraction, easier to maintain

```python
from concurrent.futures import ProcessPoolExecutor
from tqdm.contrib.concurrent import process_map

# Pattern 1: Simple map (automatic progress bar with tqdm)
results = process_map(
    ocr_page_worker,
    page_data_list,
    max_workers=cpu_count(),
    chunksize=10
)

# Pattern 2: Manual executor (more control)
with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
    futures = [executor.submit(ocr_page_worker, page) for page in page_data_list]
    results = [f.result() for f in tqdm(futures, desc="OCR Progress")]
```

### Worker Pool Sizing

| Stage | Workers | Rationale |
|-------|---------|-----------|
| **File Discovery** | 1 | I/O-bound, sequential OK |
| **Page Extraction** | CPU count | CPU-bound (image decoding) |
| **OCR Processing** | CPU count | CPU + I/O hybrid, bottleneck stage |
| **Preprocessing** | CPU count | CPU-bound (image operations) |
| **ID Extraction** | In-process | Regex is fast, no parallelization needed |
| **Result Aggregation** | 1 | Serial write avoids file corruption |

**Note:** Use `os.cpu_count()` for worker count. On typical systems (4-16 cores), this provides good throughput without thrashing.

---

## Build Order and Dependencies

### Phase 1: Single-File Serial Pipeline (Foundation)

**Goal:** Validate entire pipeline end-to-end with one PDF file.

**Components to build:**
1. **File Discovery** (single file hardcoded for testing)
2. **Page Extractor** (pdf2image wrapper, one file)
3. **OCR Processor** (pytesseract wrapper, single rotation first)
4. **ID Extractor** (regex pattern for 5-digit IDs)
5. **Result Writer** (CSV output to stdout or file)

**Why this order?**
- Prove OCR → ID extraction logic works before scaling
- Catch integration issues early (Tesseract not found, poppler missing, etc.)
- Fast iteration: no multiprocessing debugging overhead

**Success criteria:** Given `test.pdf`, output correct IDs with page numbers.

---

### Phase 2: Multi-Rotation Logic (Quality)

**Goal:** Handle rotated IDs by trying 0/90/180/270° orientations.

**Add to existing pipeline:**
1. **Rotation loop** in OCR Processor (try all 4 angles)
2. **Early exit** on first successful ID match
3. **Rotation tracking** in output (add `rotation_detected` column)

**Why this order?**
- Rotation is core to accuracy (IDs are rotated ~90°)
- Implement before parallelization to debug rotation logic serially
- Validates multi-rotation strategy before scaling

**Success criteria:** Correctly extract IDs from rotated pages in test PDFs.

---

### Phase 3: Parallelization (Scale)

**Goal:** Process 30K+ PDFs efficiently using multiprocessing.

**Refactor existing pipeline:**
1. **Wrap workers** for picklability (`if __name__ == "__main__":` guard)
2. **Replace loops** with `ProcessPoolExecutor.map()` or `process_map()`
3. **Chunk work** appropriately (chunksize=10 for page extraction/OCR)
4. **Progress tracking** with `tqdm` integration

**Why this order?**
- Core logic validated in Phase 1 & 2
- Parallelization is optimization, not core functionality
- Easier to debug race conditions after logic is proven correct

**Success criteria:** Process 100+ PDFs in parallel without crashes, linear speedup.

---

### Phase 4: Error Handling (Resilience)

**Goal:** Handle corrupted PDFs, OCR failures, and partial results gracefully.

**Add to parallelized pipeline:**
1. **Try-except blocks** in each worker with structured logging
2. **Retry logic** for transient failures (exponential backoff, max 3 attempts)
3. **Dead-letter queue** for persistent failures (log to `failed_files.txt`)
4. **Partial result preservation** (don't discard good pages if one page fails)

**Why this order?**
- Error handling is meaningful only after parallelization (race conditions, worker crashes)
- Premature error handling complicates debugging in Phases 1-3
- Real-world failure modes emerge at scale

**Success criteria:** 30K PDF run completes even with 5% corrupted files, all failures logged.

---

### Phase 5: Preprocessing Pipeline (Fallback Quality)

**Goal:** Improve OCR accuracy on low-quality scans via image enhancement.

**Add as fallback:**
1. **Preprocessing module** (grayscale → threshold → denoise with OpenCV/Pillow)
2. **Conditional invocation** (only if multi-rotation OCR finds no ID)
3. **Re-run OCR** on enhanced image with multi-rotation

**Why this order (LAST)?**
- Preprocessing is a **fallback**, not always needed
- Adds complexity and processing time (only use when necessary)
- Requires OpenCV dependency (optional until now)
- Easy to add as post-processing step to existing pipeline

**Success criteria:** Pages with no ID found after rotation now extract IDs after preprocessing.

---

## Preprocessing Pipeline (Conditional Fallback)

### When to Apply

**Trigger:** After multi-rotation OCR returns no 5-digit ID match.

**Rationale:** Preprocessing adds ~20-50ms per page. Only apply when needed to avoid unnecessary overhead on high-quality scans.

### Standard Preprocessing Sequence

```python
# Conditional preprocessing (only if OCR failed)
def preprocess_image(img: PIL.Image) -> PIL.Image:
    """
    Standard Tesseract preprocessing pipeline.
    Order matters: grayscale → denoise → threshold.
    """
    # 1. Grayscale conversion
    img_gray = img.convert('L')  # Tesseract trained on binary-like images

    # 2. Denoise (remove salt-and-pepper noise)
    img_array = np.array(img_gray)
    img_denoised = cv2.fastNlMeansDenoising(img_array, h=10)

    # 3. Binarization (threshold to black/white)
    _, img_binary = cv2.threshold(
        img_denoised,
        0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    return PIL.Image.fromarray(img_binary)
```

### Impact on Accuracy

**Research findings:**
- **Grayscale + binarization:** Improves results significantly by reducing noise and increasing text/background contrast
- **Without preprocessing:** Accuracy drops significantly or returns empty results on degraded scans
- **Denoising:** Critical for scanned documents with artifacts; certain noise types can't be removed by Tesseract's built-in binarization

**Trade-off:** +20-50ms per page vs. recovering IDs from low-quality scans. Worth it for fallback layer.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: OCR Every Rotation Unconditionally

**What:** Always OCR at all 4 rotations (0/90/180/270°) even after finding a valid ID.

**Why bad:** Wastes 3x compute time. OCR is the slowest stage (~500ms-2s per page per rotation).

**Instead:** **Early exit on first match.** If 0° finds a 5-digit ID, skip 90/180/270°. For 30K PDFs × 10 pages avg × 4 rotations = 1.2M unnecessary OCR calls prevented.

---

### Anti-Pattern 2: Preprocessing All Images Upfront

**What:** Apply grayscale/threshold/denoise to every page before OCR.

**Why bad:**
- Adds 20-50ms × 300K pages = 1.7-4.2 hours of unnecessary processing
- High-quality scans don't need preprocessing (80%+ of pages in typical batch)
- Degrades quality on already-good images (over-processing artifacts)

**Instead:** **Conditional preprocessing as fallback.** Only enhance images that fail multi-rotation OCR. Reduces preprocessing to ~5-10% of pages (low-quality scans only).

---

### Anti-Pattern 3: Single-Threaded Sequential Processing

**What:** Process 30K PDFs in a single for-loop without parallelization.

**Why bad:**
- Estimated time: 30K PDFs × 10 pages × 2s OCR = 600K seconds = **166 hours (1 week)**
- With 8-core parallelization: 600K / 8 = **20 hours** (8x speedup)
- Single-threaded wastes 7 CPU cores on typical desktop/server

**Instead:** **ProcessPoolExecutor with worker pool.** Parallelize page extraction and OCR stages. Aim for ~linear speedup with CPU count.

---

### Anti-Pattern 4: Shared State Across Workers

**What:** Use global variables or shared mutable objects (lists, dicts) without locks in multiprocessing workers.

**Why bad:**
- Windows spawn mode doesn't share memory between processes
- Mutations in child processes don't propagate to parent
- Results get silently lost or corrupted

**Instead:** **Return results from workers.** Let `ProcessPoolExecutor.map()` collect return values. For shared state, use `multiprocessing.Manager` with locks (but prefer stateless workers).

---

### Anti-Pattern 5: Catching All Exceptions Silently

**What:** Wrap entire worker in `try-except: pass` to prevent crashes.

**Why bad:**
- Hides critical failures (Tesseract not found, corrupted PDFs, out of memory)
- Makes debugging impossible (which files failed? why?)
- Silently drops results without logging

**Instead:** **Structured error handling with logging.** Log exception type, file path, page number, and traceback. Route persistent failures to dead-letter queue for manual inspection. Re-raise unexpected exceptions (don't swallow `KeyboardInterrupt`, `SystemExit`).

---

### Anti-Pattern 6: One Giant Queue for All Stages

**What:** Put all work items (PDFs, pages, OCR results, IDs) into a single shared queue.

**Why bad:**
- Couples all stages tightly (can't optimize independently)
- Hard to track which stage is the bottleneck
- Complex synchronization logic (when to stop consuming?)

**Instead:** **Stage-separated queues or functional pipeline.** Use `ProcessPoolExecutor.map()` return values as input to next stage. Each stage is independent, testable, and optimizable. Example: `pdf_paths → pages → ocr_results → ids → output`.

---

## Scalability Considerations

### At 100 PDFs (~1K pages)

| Concern | Approach |
|---------|----------|
| **Processing time** | Single-threaded OK (~30 mins), parallelization optional |
| **Memory usage** | In-memory result accumulation (<100MB) |
| **Error handling** | Basic logging sufficient |
| **Progress tracking** | Simple print statements OK |

---

### At 10K PDFs (~100K pages) [TARGET SCALE]

| Concern | Approach |
|---------|----------|
| **Processing time** | Multiprocessing mandatory (8 cores = 3-6 hours vs. 24-48 hours serial) |
| **Memory usage** | Stream results to disk, don't accumulate all in memory (limit queue size) |
| **Error handling** | Retry logic + dead-letter queue for corrupted files |
| **Progress tracking** | Real-time progress bars (tqdm) with ETA, per-stage throughput metrics |
| **Output format** | CSV chunked writes (append mode) to avoid memory exhaustion, JSON at end |
| **Checkpointing** | Save intermediate results every 1K files to allow resume on crash |

---

### At 1M PDFs (~10M pages) [FUTURE SCALE]

| Concern | Approach |
|---------|----------|
| **Processing time** | Distributed processing (multiple machines), consider cloud batch services |
| **Memory usage** | Streaming architecture required, no in-memory accumulation |
| **Error handling** | Automated retry with exponential backoff, dedicated failure analysis pipeline |
| **Progress tracking** | Centralized monitoring (Prometheus + Grafana dashboards) |
| **Output format** | Partitioned Parquet files (columnar storage) for efficient querying |
| **Checkpointing** | Database-backed progress tracking, resume from any point |
| **Infrastructure** | Kubernetes job orchestration, auto-scaling worker pools |

**Note:** Current project scope (30K PDFs) fits comfortably in "10K scale" tier. Focus on efficient single-machine parallelization.

---

## Windows-Specific Implementation Notes

### Start Method: Always Spawn

```python
import multiprocessing as mp

if __name__ == "__main__":
    # Explicitly set spawn (redundant on Windows, but explicit is better)
    mp.set_start_method('spawn', force=True)

    # Rest of code here...
```

**Why:** Windows doesn't support `fork`. Spawn creates fresh interpreter for each worker (slower startup, but safer). Always protect entry point with `if __name__ == "__main__":` to prevent recursive process spawning.

---

### Pickling Requirements

**What can be passed to workers:**
- Built-in types (str, int, list, dict, tuple)
- PIL.Image objects (picklable)
- Function references (top-level functions, not lambdas)
- Custom classes with `__getstate__` / `__setstate__`

**What CANNOT be passed:**
- Lambda functions
- Nested functions (unless using `cloudpickle`)
- File handles (open files)
- Database connections
- Thread locks

**Solution:** Pass file paths (strings) instead of open file handles. Workers open files independently.

---

### Path Handling

**Critical:** Use `pathlib.Path` or `os.path` for cross-platform paths, but be aware:
- Windows uses backslashes (`C:\path\to\file.pdf`)
- Forward slashes work in most cases (`C:/path/to/file.pdf`)
- Avoid hardcoded paths in code (pass as CLI arguments)

```python
from pathlib import Path

# Good: cross-platform path handling
pdf_path = Path(input_dir) / "file.pdf"
pdf_path.resolve()  # Absolute path

# Bad: hardcoded Windows path
pdf_path = "C:\\Users\\Owner\\Documents\\file.pdf"  # Breaks on other systems
```

---

### Tesseract and Poppler on Windows

**Dependency check:**
```python
import pytesseract
from pdf2image import convert_from_path

# Verify Tesseract is in PATH
try:
    pytesseract.get_tesseract_version()
except Exception as e:
    raise RuntimeError("Tesseract not found. Install and add to PATH.") from e

# Verify Poppler is in PATH (pdf2image dependency)
try:
    convert_from_path("test.pdf", first_page=1, last_page=1)
except Exception as e:
    raise RuntimeError("Poppler not found. Install and add to PATH.") from e
```

**User's environment:** Tesseract + Poppler already installed. Verify on first run, fail fast with clear error message if missing.

---

## Progress Tracking and Observability

### Real-Time Progress Bars (tqdm)

```python
from tqdm.contrib.concurrent import process_map

# Automatic progress bar with multiprocessing
results = process_map(
    ocr_worker_function,
    page_data_list,
    max_workers=cpu_count(),
    desc="OCR Processing",
    unit="page",
    chunksize=10
)
```

**Output:**
```
OCR Processing: 67%|████████████████████▌         | 201/300 [02:15<01:05, 1.49page/s]
```

### Structured Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ocr_pipeline.log"),
        logging.StreamHandler()  # Also print to console
    ]
)

# In worker function
logging.info(f"Processing {filepath}, page {page_num}")
logging.error(f"OCR failed for {filepath}, page {page_num}: {error}")
```

### Key Metrics to Track

| Metric | How to Track | Purpose |
|--------|--------------|---------|
| **Throughput** | Pages processed per second | Identify bottleneck stages |
| **Error rate** | Failed pages / total pages | Detect systematic issues |
| **Processing time per stage** | Time each stage start/end | Optimize slowest stage |
| **Memory usage** | `psutil.virtual_memory()` | Prevent out-of-memory crashes |
| **Queue size** | Length of work queue | Detect producer/consumer imbalance |

**Tool recommendation:** Use `tqdm` for progress, `logging` for errors, and consider `prometheus_client` for production metrics if scaling beyond 30K PDFs.

---

## Error Handling Strategies

### Retry Logic (Exponential Backoff)

```python
import time
from functools import wraps

def retry_with_backoff(max_attempts=3, base_delay=2):
    """Retry decorator with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise  # Re-raise on final attempt
                    delay = base_delay * (2 ** attempt)
                    logging.warning(f"Attempt {attempt+1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator

@retry_with_backoff(max_attempts=3)
def ocr_page_worker(page_data):
    # OCR logic here
    pass
```

**When to retry:**
- Transient I/O errors (file locked, network timeout)
- Tesseract crashes (rare but happens on corrupted images)

**When NOT to retry:**
- `FileNotFoundError` (file genuinely missing)
- `KeyboardInterrupt` (user wants to stop)
- Regex validation failure (not an error, just no ID found)

---

### Dead-Letter Queue (DLQ)

```python
failed_files = []

def process_with_dlq(pdf_path):
    try:
        result = process_pdf(pdf_path)
        return result
    except Exception as e:
        logging.error(f"Failed to process {pdf_path}: {e}")
        failed_files.append((pdf_path, str(e)))
        return None  # Continue processing other files

# After processing all files
with open("dead_letter_queue.txt", "w") as f:
    for filepath, error in failed_files:
        f.write(f"{filepath}\t{error}\n")
```

**Purpose:** Isolate "poison pill" documents so they don't block the main pipeline. Review DLQ manually after batch completes.

---

### Partial Result Preservation

**Anti-pattern:** If one page in a 50-page PDF fails OCR, discard all 49 successful pages.

**Better approach:** Write results incrementally (append to CSV after each PDF or every N pages).

```python
import csv
from contextlib import contextmanager

@contextmanager
def csv_writer(filepath):
    """Context manager for incremental CSV writing."""
    with open(filepath, 'a', newline='') as f:
        writer = csv.writer(f)
        yield writer

# In processing loop
with csv_writer("output.csv") as writer:
    for pdf_path in pdf_paths:
        try:
            results = process_pdf(pdf_path)
            for row in results:
                writer.writerow(row)  # Append immediately
        except Exception as e:
            logging.error(f"Skipping {pdf_path}: {e}")
            continue  # Don't fail entire batch
```

**Benefit:** If pipeline crashes at 80% completion, 80% of results are already saved.

---

## Technology Stack Summary

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Core Language** | Python | 3.10+ | Scripting, multiprocessing support |
| **PDF to Image** | pdf2image | 1.16+ | Convert PDF pages to PIL images |
| **OCR Engine** | Tesseract OCR | 5.x | Text recognition (pre-installed) |
| **Python OCR Wrapper** | pytesseract | 0.3+ | Python API for Tesseract |
| **Image Processing** | Pillow (PIL) | 10.x | Image rotation, basic preprocessing |
| **Advanced Preprocessing** | OpenCV (cv2) | 4.x | Grayscale, threshold, denoise (optional) |
| **Parallelization** | concurrent.futures | stdlib | ProcessPoolExecutor, clean API |
| **Progress Tracking** | tqdm | 4.66+ | Real-time progress bars |
| **CLI Argument Parsing** | argparse | stdlib | Command-line interface |
| **Logging** | logging | stdlib | Structured error logging |
| **Data Output** | csv, json | stdlib | CSV and JSON writers |

**Dependencies installed:** Tesseract + Poppler (user's environment already configured).

**Why these choices:**
- **pdf2image:** De facto standard for PDF → image conversion in Python, uses Poppler under the hood
- **pytesseract:** Official Python wrapper for Tesseract, simple API
- **concurrent.futures:** Higher-level API than multiprocessing.Pool, easier to maintain
- **Pillow:** Lightweight, sufficient for rotation and basic preprocessing
- **OpenCV:** Only needed for advanced preprocessing (denoising), optional dependency

---

## Testing Strategy by Build Order

### Phase 1: Single-File Serial
- **Unit tests:** Each component in isolation (page extractor, OCR wrapper, ID regex)
- **Integration test:** End-to-end on `test.pdf` with known IDs
- **Success metric:** Correct IDs extracted, CSV output matches expected

### Phase 2: Multi-Rotation
- **Test cases:** PDFs rotated 0/90/180/270° manually
- **Expected behavior:** All rotations correctly detected and logged
- **Edge cases:** Pages with no ID (should flag, not crash)

### Phase 3: Parallelization
- **Stress test:** 100 PDFs in parallel, verify no crashes
- **Race condition check:** Run 10 times, verify identical output each time
- **Performance test:** Measure speedup vs. serial (expect ~linear with CPU count)

### Phase 4: Error Handling
- **Fault injection:** Corrupted PDFs, missing pages, permission errors
- **Expected behavior:** Failures logged, other files continue processing
- **DLQ validation:** Failed files listed in dead-letter queue

### Phase 5: Preprocessing
- **Quality test:** Low-quality scans with preprocessing vs. without
- **Expected improvement:** 10-20% more IDs extracted from degraded scans
- **Performance test:** Verify preprocessing only applied when needed (fallback)

---

## Sources

### Architecture and Design Patterns
- [OCR Models | docling-project](https://deepwiki.com/docling-project/docling/4.1-ocr-models)
- [GitHub - BoltzmannEntropy/batch-ocr](https://github.com/BoltzmannEntropy/batch-ocr)
- [GitHub - usnistgov/ocr-pipeline](https://github.com/usnistgov/ocr-pipeline)
- [15 Data Pipeline Architecture Patterns](https://medium.com/@reliabledataengineering/15-data-pipeline-architecture-patterns-every-engineer-should-know-ef0cf67935cb)
- [The Elegance of Modular Data Processing with Python's Pipeline Approach](https://medium.com/@dkraczkowski/the-elegance-of-modular-data-processing-with-pythons-pipeline-approach-e63bec11d34f)

### Multiprocessing and Parallelization
- [Python Multithreading vs Multiprocessing (2026)](https://www.trantorinc.com/blog/multithreading-vs-multiprocessing-in-python)
- [Python Multiprocessing Example: Process, Pool & Queue](https://www.digitalocean.com/community/tutorials/python-multiprocessing-example)
- [Multiprocessing - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html)
- [Fork vs Spawn in Python Multiprocessing](https://britishgeologicalsurvey.github.io/science/python-forking-vs-spawn/)
- [Python Multiprocessing: Start Methods, Pools, and Communication](https://dev.to/imsushant12/python-multiprocessing-start-methods-pools-and-communication-4o6d)
- [Concurrent Programming: concurrent.futures vs. multiprocessing](https://www.datanovia.com/learn/programming/python/advanced/parallel-processing/concurrent-programming.html)

### Batch Processing Patterns
- [How to Implement Batch Processing for Performance](https://oneuptime.com/blog/post/2026-01-25-batch-processing-performance/view)
- [Batch Data Processing Pipeline With SQS](https://undercodetesting.com/batch-data-processing-pipeline-with-sqs-a-practical-guide-for-aws-data-engineering/)
- [Python Producer-Consumer Pattern (2026)](https://copyprogramming.com/howto/how-to-properly-implement-producer-consumer-in-python)
- [Python Producer Consumer Multiprocessing](https://reelmind.ai/blog/python-producer-consumer-multiprocessing-optimize-ai-workflows)
- [Producer-Consumer Problem in Python](https://www.askpython.com/python/producer-consumer-problem)

### OCR and Image Processing
- [Image Preprocessing for Tesseract OCR](https://autbor.com/preprocessingocr/)
- [Image Preprocessing | tesseract-ocr](https://deepwiki.com/tesseract-ocr/tesseract/4.2-image-preprocessing)
- [Improving the quality of the output - Tesseract documentation](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [How to use image preprocessing to improve Tesseract accuracy](https://www.freecodecamp.org/news/getting-started-with-tesseract-part-ii-f7f9a0899b3f/)
- [Efficiency of image binarization for Tesseract OCR](https://medium.com/@maxshouman/efficiency-of-image-binarization-as-a-preprocessing-technique-for-tesseract-ocr-637ee8e6609f)

### Error Handling and Resilience
- [Error Handling & Retry Logic: Guide for B2B Enrichment Workflows](https://derrick-app.com/en/error-handling-retry-logic-2/)
- [Designing a Decision-Driven OCR Pipeline](https://medium.com/@ashwinr638/designing-a-decision-driven-ocr-pipeline-445da9221a62)
- [AI for Enterprise Document Processing OCR (2026)](https://www.stackai.com/insights/ai-for-enterprise-document-processing-ocr-end-to-end-workflow-best-practices-and-2026-guide)
- [What is Transformation Retry Depth for ETL Data Pipelines](https://www.integrate.io/blog/what-is-transformation-retry-depth-etl-data-pipelines/)

### Progress Tracking and Monitoring
- [Advanced Progress Monitoring in Python with tqdm (2026)](https://earezki.com/ai-news/2026-03-08-how-to-build-progress-monitoring-using-advanced-tqdm-for-async-parallel-pandas-logging-and-high-performance-workflows/)
- [How to Build Progress Monitoring Using Advanced tqdm](https://www.marktechpost.com/2026/03/07/how-to-build-progress-monitoring-using-advanced-tqdm-for-async-parallel-pandas-logging-and-high-performance-workflows/)
- [GitHub - tqdm/tqdm](https://github.com/tqdm/tqdm)
- [tqdm-loggable · PyPI](https://pypi.org/project/tqdm-loggable/)

### Rotation Detection
- [Seeing Straight: Document Orientation Detection for Efficient OCR (2026)](https://arxiv.org/abs/2511.04161)
- [Technical Analysis of Modern Non-LLM OCR Engines](https://intuitionlabs.ai/pdfs/technical-analysis-of-modern-non-llm-ocr-engines.pdf)

### Output Strategies
- [How AI Is Killing Legacy OCR (2026)](https://parsinto.com/blog/ocr-data-extraction-solutions-the-complete-2026-guide)
- [Batch OCR Software For High Volume Documents](https://klearstack.com/batch-ocr-software-enterprise-guide)
- [Best Table Parsing, Table OCR APIs in 2026](https://www.edenai.co/post/best-table-parsing-apis)

### Enterprise OCR Workflows
- [OCR Data Entry: How It Works and Why Teams Are Switching in 2026](https://www.lido.app/blog/ocr-data-entry)
- [AI for Enterprise Document Processing OCR (2026)](https://www.stackai.com/insights/ai-for-enterprise-document-processing-ocr-end-to-end-workflow-best-practices-and-2026-guide)
- [How to Extract Text from PDF in Python (2026)](https://dev.to/kreuzberg/how-to-extract-text-from-pdf-in-python-2026-3a97)
