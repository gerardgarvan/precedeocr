# Technology Stack

**Project:** Precede OCR — PDF ID Scanner & Mapper
**Last Updated:** 2026-06-05
**Target Platform:** Windows 10
**Scale:** ~30,429 multi-page PDFs with rotation handling

---

## v1.0 Stack (Validated)

### Core OCR Engine
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Tesseract OCR** | 5.5.2 | OCR engine for text extraction | Industry-standard open-source OCR with LSTM neural networks (v5.x). 32-bit float ops reduce RAM usage. Best accuracy-to-speed balance for clean scanned documents (sub-1-second per page). CPU-first design avoids GPU requirements. Already installed per project constraints. **Confidence: HIGH** |
| **pytesseract** | 0.3.13 | Python wrapper for Tesseract | Official Python binding. Simple API (`image_to_string`, `image_to_data`). Mature (Python 3.8+). Direct integration with PIL/Pillow. **Confidence: HIGH** |

**Installation:**
```bash
# Tesseract 5.5.2 already installed (Windows installer from UB Mannheim)
pip install pytesseract==0.3.13
```

**Rationale:** Tesseract 5.x delivers best OCR accuracy for printed text in scanned documents. Processes typical page in <1s. No GPU/cloud dependencies. Handles 5-digit numeric IDs reliably with proper preprocessing. Alternative EasyOCR offers better layout handling but requires GPU for competitive speed and adds unnecessary complexity for this numeric-ID-only use case.

### PDF-to-Image Conversion
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pdf2image** | 1.17.0 | Convert PDF pages to PIL Images | Wraps Poppler's pdftoppm/pdftocairo utilities. Supports high-DPI rendering (300+ DPI) required for OCR accuracy. Handles multi-page PDFs efficiently. `use_pdftocairo` parameter improves performance. `paths_only` parameter prevents OOM on large PDFs. **Confidence: HIGH** |
| **Poppler** | Latest stable | PDF rendering engine | Already installed per project constraints. Cross-platform PDF utilities (pdftoppm, pdftocairo). Industry standard for PDF rasterization. **Confidence: HIGH** |

**Installation:**
```bash
# Poppler already installed (Windows binaries in PATH)
pip install pdf2image==1.17.0
```

**Rationale:** pdf2image is the standard Python solution for PDF-to-image conversion. Mature library (1.17.0 released Jan 2024). Direct integration with Pillow for OCR pipeline. Poppler's pdftoppm produces high-quality rasters at 300 DPI. Alternative PyMuPDF (fitz) offers speed advantages but pdf2image's simplicity and Poppler backend match project needs.

### Image Preprocessing
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Pillow (PIL)** | 12.2.0 | Basic image operations | Python's standard imaging library. Handles format conversion, basic transforms (resize, rotate). Native integration with pytesseract and pdf2image. Lightweight for basic preprocessing. Mature (status 6 - Mature). **Confidence: HIGH** |
| **OpenCV (opencv-python)** | 4.13.0.92 | Advanced preprocessing | Superior for complex preprocessing: adaptive thresholding (Otsu, Sauvola), noise reduction (Gaussian blur, morphological ops), edge detection, perspective correction. CPU-optimized. Required for fallback preprocessing on degraded scans. **Confidence: HIGH** |

**Installation:**
```bash
pip install Pillow==12.2.0
pip install opencv-python==4.13.0.92
```

**Rationale:** Use **Pillow for initial pipeline** (rotation, grayscale conversion, basic quality images) — simpler API, lower overhead. Use **OpenCV for fallback preprocessing** when OCR confidence is low — adaptive thresholding, denoise, contrast enhancement. Combined approach (Pillow primary, OpenCV fallback) balances simplicity with power. Sources confirm this pattern: "OpenCV for preprocessing, PyTorch for training" but we only need preprocessing here.

**Preprocessing Strategy:**
1. **Primary path:** Pillow grayscale + 300 DPI render
2. **Fallback path (if no ID found):** OpenCV adaptive threshold + Gaussian blur + morphological operations
3. **Rotation:** Test 0/90/180/270 degrees using Pillow's `Image.rotate()` (simpler) or OpenCV's `cv2.rotate()` (if integrated in fallback)

### Parallelization
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **multiprocessing** | stdlib | CPU-bound parallel processing | Python stdlib. Required for scaling to 30K+ PDFs. Pool.map() for embarrassingly parallel tasks (each PDF independent). Windows uses 'spawn' start method — requires `if __name__ == '__main__'` guard. Speed improvements: 100%+ (2x faster) for PDF processing workloads. **Confidence: HIGH** |

**Usage Pattern:**
```python
from multiprocessing import Pool, cpu_count

if __name__ == '__main__':
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(process_pdf, pdf_paths)
```

**Rationale:** multiprocessing.Pool is the standard for CPU-bound parallel Python on Windows. OCR is CPU-intensive (Tesseract uses CPU, not GPU). Each PDF is independent — no shared state. Pool.map() provides simple interface. Windows 'spawn' start method is slower than Linux 'fork' but functional. Expect 2x+ speedup on multi-core systems.

### Progress Tracking
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **tqdm** | 4.67.3 | Progress visualization | Wraps iterables with smart progress bars. Shows percentage, iteration rate, ETA. Low overhead (60ns/iter). Works with multiprocessing via `tqdm(pool.imap(...))` or tqdm-multiprocess package. Essential UX for 30K+ file batch job. **Confidence: HIGH** |

**Installation:**
```bash
pip install tqdm==4.67.3
```

**Rationale:** tqdm is the standard Python progress bar. Minimal code: `tqdm(iterable)`. Provides critical user feedback for long-running batch jobs (30K PDFs = hours). Multiprocessing integration via `pool.imap()` + tqdm wrapper avoids garbled output. Alternative: custom logging, but tqdm's UX is superior.

### Output Formatting
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pandas** | 3.0.3 | CSV/JSON export | Standard DataFrame library. Clean API for structured data: `df.to_csv()` and `df.to_json()`. Handles missing values (NaN → null). `orient='records'` for JSON produces list-of-dicts format for lookups. Efficient I/O for large datasets. **Confidence: HIGH** |

**Installation:**
```bash
pip install pandas==3.0.3
```

**Rationale:** pandas provides the cleanest interface for CSV/JSON export. Alternative: Python's csv module + json module, but pandas handles edge cases (missing values, encoding) and produces cleaner output with less code. `orient='records'` for JSON: `[{filename: ..., page: ..., id: ...}]` format is ideal for programmatic lookup.

### File System Operations
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pathlib** | stdlib | Path manipulation | Modern OOP path API. Cross-platform compatibility. Cleaner syntax: `Path("dir") / "file.pdf"`. Built-in methods: `.exists()`, `.is_file()`, `.glob()`. Recommended over os.path for Python 3+. **Confidence: HIGH** |

**Usage:**
```python
from pathlib import Path

pdf_files = list(Path("target_dir").rglob("*.pdf"))
```

**Rationale:** pathlib is Python 3's standard for path operations. Cleaner, safer than os.path string manipulation. Recursive glob: `.rglob("*.pdf")` for directory traversal. Cross-platform (Windows/Linux/Mac). 2025 best practice: "use pathlib for path manipulation, os for OS features."

### Supporting Libraries (v1.0)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **numpy** | Latest stable | Array operations for OpenCV | OpenCV returns numpy arrays. Required dependency for opencv-python. Auto-installed with OpenCV. **Confidence: HIGH** |
| **scipy** | Latest stable | Advanced image rotation (optional) | `scipy.ndimage.rotate()` for arbitrary-angle rotation. Optional: Pillow's `Image.rotate()` sufficient for 90° increments. Include if advanced rotation needed. **Confidence: MEDIUM** |

---

## v1.1 Campaign Management Additions

**Purpose:** Interactive campaign menu, graceful Ctrl+C handling, statistics tracking, state persistence for resume capability.

### Signal Handling & Graceful Shutdown

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **signal** (stdlib) | Python 3.14 | Handle SIGINT (Ctrl+C) on Windows | Windows supports SIGINT natively. Python stdlib signal module supports SIGINT, SIGTERM, SIGBREAK on Windows. Default action raises KeyboardInterrupt. **Confidence: HIGH** |
| **multiprocessing.Event** (stdlib) | Python 3.14 | Cross-process shutdown flag | More reliable than signals for Windows multiprocessing. Event is a simple flag shared across processes. Worker processes check flag periodically, finish current work, then exit. Platform-independent (works on Windows 'spawn' mode). Recommended pattern: main process sets Event on SIGINT, workers check Event before starting new files. **Confidence: HIGH** |

**Integration Pattern:**
```python
import signal
import multiprocessing

shutdown_event = multiprocessing.Event()

def signal_handler(signum, frame):
    print("\nShutdown requested. Finishing current files...")
    shutdown_event.set()

def worker_func(pdf_path):
    if shutdown_event.is_set():
        return None  # Skip if shutdown requested
    # Process PDF...
    return result

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    with multiprocessing.Pool() as pool:
        results = list(tqdm(pool.imap_unordered(worker_func, pdf_paths), total=len(pdf_paths)))
```

### Interactive CLI Menus

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **questionary** | 2.1.1 | Interactive CLI prompts and menus | Cross-platform (Windows compatible) via prompt_toolkit. Modern, actively maintained (released Aug 2025). Clean API: `questionary.select(message, choices).ask()`. Supports Python 3.9-3.14. Best choice for campaign menu (continue/re-run/stats/export options). **Confidence: HIGH** |

**Installation:**
```bash
pip install questionary==2.1.1
```

**Fallback Option (if questionary has Windows issues):**
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **pick** | 2.6.0 | Simple terminal-based selection | Uses blessed backend for Windows compatibility (`pip install "pick[blessed]"`). Simpler API than questionary. Supports Python 3.8-3.14. Released Feb 2026. Fallback if questionary has issues. **Confidence: MEDIUM** |

**Installation (fallback):**
```bash
pip install "pick[blessed]==2.6.0"
```

**Usage Pattern:**
```python
import questionary

action = questionary.select(
    "Campaign menu:",
    choices=[
        "Continue processing",
        "Re-run failed files only",
        "View statistics",
        "Export partial results",
        "Exit"
    ]
).ask()
```

### Statistics Tracking & Aggregation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **collections.defaultdict** (stdlib) | Python 3.14 | Per-folder statistics aggregation | Auto-creates missing keys on first access. Perfect for nested stats: `folder_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0})`. Zero dependencies. Fast. Pairs with Counter for frequency analysis. **Confidence: HIGH** |
| **collections.Counter** (stdlib) | Python 3.14 | Count frequencies (errors by type, IDs per folder) | Specialized for counting with `most_common(n)`, `update()`, `total()` (Python 3.10+). Better than defaultdict(int) for analysis tasks. Use for "top 10 error types" or "folders with most failures". **Confidence: HIGH** |
| **dataclasses** (stdlib) | Python 3.14 | Type-safe campaign state structure | Clean state modeling: `@dataclass class CampaignState`. Built-in `asdict()` for JSON serialization. No dependencies. Pairs well with dataclasses-json for persistence. **Confidence: HIGH** |

**Usage Pattern:**
```python
from collections import defaultdict, Counter
from pathlib import Path

# Per-folder statistics
folder_stats = defaultdict(lambda: {'total': 0, 'success': 0, 'failed': 0, 'ids_found': 0})

for pdf_path in pdf_paths:
    folder = str(Path(pdf_path).parent)
    folder_stats[folder]['total'] += 1
    # Update based on result...

# Error frequency analysis
error_counts = Counter()
for result in results:
    if result.error:
        error_counts[result.error_type] += 1

print("Top 5 error types:")
for error_type, count in error_counts.most_common(5):
    print(f"  {error_type}: {count}")
```

### Campaign State Persistence

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **dataclasses-json** | 0.6.7 | Serialize/deserialize dataclasses to JSON | Simple decorator: `@dataclass_json @dataclass class CampaignState`. Automatic type handling (nested dataclasses, datetime, UUID). Actively maintained (June 2024 release). Supports Python 3.7-3.12 (no official 3.13+ yet, but works). Clean API: `.to_json()`, `.from_json()`. **Confidence: MEDIUM** (pre-1.0.0, but stable) |
| **json** (stdlib) | Python 3.14 | JSON encoding/decoding | Fallback if dataclasses-json has issues. Use with dataclasses.asdict() for serialization. More manual but zero dependencies. **Confidence: HIGH** |
| **tempfile + os.replace** | Python 3.14 (stdlib) | Atomic state file writes | **Already validated in v1.0 checkpoint system.** Pattern: `NamedTemporaryFile(dir=state_dir, delete=False)` → write → fsync → `os.replace(temp, final)`. Atomic on Windows (os.replace uses MoveFileEx). Crash-safe. **Confidence: HIGH** |

**Installation:**
```bash
pip install dataclasses-json==0.6.7
```

**Usage Pattern:**
```python
from dataclasses import dataclass
from dataclasses_json import dataclass_json
import tempfile
import os

@dataclass_json
@dataclass
class CampaignState:
    total_files: int
    processed_files: int
    failed_files: list
    folder_stats: dict
    last_updated: str

def save_state(state: CampaignState, state_path: str):
    state_dir = os.path.dirname(state_path)
    with tempfile.NamedTemporaryFile(mode='w', dir=state_dir, delete=False, suffix='.json') as tmp:
        tmp.write(state.to_json(indent=2))
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, state_path)  # Atomic

def load_state(state_path: str) -> CampaignState:
    with open(state_path) as f:
        return CampaignState.from_json(f.read())
```

### Progress Tracking Enhancement

| Technology | Version | Purpose | Integration Notes |
|------------|---------|---------|-------------------|
| **tqdm** (already in v1.0) | 4.67.3 | Progress bars with graceful shutdown | For v1.1: use `pool.imap_unordered()` instead of `pool.map()` to enable tqdm wrapper: `tqdm(pool.imap_unordered(func, items), total=len(items))`. Updates as workers complete files. Works with Event-based shutdown (workers finish current file, progress bar shows completion). **Confidence: HIGH** |

---

## Alternatives Considered (v1.0)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **OCR Engine** | Tesseract 5.5.2 | EasyOCR | EasyOCR has better accuracy on complex layouts/fonts but is slower on CPU (requires GPU for speed). Project has simple numeric IDs in scanned docs — Tesseract's strength. EasyOCR adds deep learning overhead for minimal benefit. **Confidence: MEDIUM** |
| **OCR Engine** | Tesseract 5.5.2 | PaddleOCR | PaddleOCR excels at multi-language, table extraction. Overkill for 5-digit numeric IDs. Tesseract simpler, faster for this use case. **Confidence: MEDIUM** |
| **OCR Engine** | Tesseract 5.5.2 | Cloud OCR (Google Vision, AWS Textract) | Out of scope per project constraints. Tesseract local, no API costs, no internet dependency. **Confidence: HIGH** |
| **PDF Library** | pdf2image + Poppler | PyMuPDF (fitz) | PyMuPDF faster for large batches, but pdf2image + Poppler already installed and simpler API. PyMuPDF worth considering if performance bottleneck emerges. **Confidence: MEDIUM** |
| **Image Preprocessing** | Pillow + OpenCV | OpenCV only | OpenCV more powerful but steeper learning curve. Pillow sufficient for primary path. Combined approach balances simplicity and power. **Confidence: HIGH** |
| **Image Preprocessing** | Pillow + OpenCV | Pillow only | Pillow lacks advanced preprocessing (adaptive thresholding, morphological ops). Insufficient for degraded scans. OpenCV required for fallback. **Confidence: HIGH** |
| **Parallelization** | multiprocessing | threading | OCR is CPU-bound, not I/O-bound. Python's GIL blocks true threading parallelism. multiprocessing required for CPU scaling. **Confidence: HIGH** |
| **Parallelization** | multiprocessing | concurrent.futures | concurrent.futures.ProcessPoolExecutor wraps multiprocessing. Simpler API but multiprocessing.Pool more common in OCR pipelines. Both valid. **Confidence: MEDIUM** |
| **Progress Tracking** | tqdm | logging | logging lacks visual progress. tqdm provides ETA, percentage, rate — critical UX for long jobs. **Confidence: HIGH** |
| **Output Formatting** | pandas | csv + json modules | csv + json modules work but require more boilerplate. pandas handles edge cases (NaN, encoding) cleanly. **Confidence: HIGH** |

## Alternatives Considered (v1.1 Campaign Management)

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **questionary** | simple-term-menu | **NEVER on Windows** — simple-term-menu explicitly does not support Windows (Linux/macOS only). Use questionary or pick instead. |
| **questionary** | pick | Use pick if questionary has Windows compatibility issues in practice. pick is simpler (less features) but more reliable on Windows with blessed backend. |
| **questionary** | InquirerPy | Use InquirerPy if you need fuzzy search or more complex prompt features. questionary sufficient for simple select menus. |
| **multiprocessing.Event** | signal-based shutdown | Use Event for cross-process coordination. Signals are OS-dependent (Windows has limited signal support). Event is platform-independent and pairs well with multiprocessing.Pool. |
| **dataclasses-json** | json + dataclasses.asdict() | Use stdlib approach if dataclasses-json has Python 3.14 compatibility issues (library officially supports 3.7-3.12). More manual but zero dependencies. |
| **tempfile + os.replace** | atomicwrites library | Use atomicwrites if you need more robust cross-platform guarantees or if manual approach has edge cases. stdlib approach already validated in v1.0, so prefer that. |
| **defaultdict + Counter** | pandas for stats | **NO** — pandas already in stack for output formatting. Don't use pandas for in-memory statistics aggregation (overkill, slower). Use collections for lightweight aggregation. |
| **JSON state persistence** | shelve | **NEVER** — shelve does not support concurrent read/write (only one writer at a time). Has corruption risks on macOS. Not suitable for campaign state with resume capability. Use JSON with atomic writes. |
| **JSON state persistence** | SQLite | Use SQLite if state grows complex (e.g., per-file metadata, relational queries). For v1.1 campaign state (simple dict/list structures), JSON sufficient. SQLite overkill. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **simple-term-menu** | Does not support Windows (POSIX/Linux/macOS only). Explicitly states "Currently, Linux and macOS are supported." Project runs on Windows 10. | questionary or pick with blessed backend |
| **shelve** | No concurrent read/write support. Silent corruption risk on macOS. Only one program can write at a time. Unsuitable for campaign state resume. | JSON with atomic writes (tempfile + os.replace) |
| **pickle for state** | Binary format (not human-readable for debugging). Security risk if loading untrusted data. Harder to debug corrupted state. | JSON (text format, easy to inspect/debug) |
| **os.rename** | Not atomic on Windows in all cases (cross-volume moves). | os.replace (atomic on all platforms since Python 3.3) |
| **signal-only shutdown** | Windows has limited signal support (only SIGINT, SIGTERM, SIGBREAK, SIGABRT, SIGFPE, SIGILL, SIGSEGV). Signals don't propagate reliably to child processes on Windows 'spawn' mode. | multiprocessing.Event (cross-process flag) + signal handler in main process |
| **PySimpleGUI** | No longer actively developed (deprecated in 2026). Not recommended for new projects. | questionary (CLI prompts) or PyQt/Tkinter (if GUI needed) |
| **console-menu** | Less actively maintained than questionary. Fewer features. questionary is better supported. | questionary |

---

## Installation Summary

**Full v1.0 + v1.1 stack installation:**
```bash
# Core dependencies (Tesseract and Poppler already installed on Windows)
pip install pytesseract==0.3.13
pip install pdf2image==1.17.0
pip install Pillow==12.2.0
pip install opencv-python==4.13.0.92
pip install pandas==3.0.3
pip install tqdm==4.67.3

# v1.1 Campaign Management additions
pip install questionary==2.1.1
pip install dataclasses-json==0.6.7

# Optional (fallback if questionary has Windows issues)
pip install "pick[blessed]==2.6.0"

# Optional (advanced rotation, v1.0)
pip install scipy
```

**System requirements:**
- **OS:** Windows 10 (project constraint)
- **Python:** 3.8+ (pytesseract requirement), 3.14 recommended
- **Tesseract OCR:** 5.5.2 (already installed)
- **Poppler:** Latest stable (already installed)
- **RAM:** 8GB+ recommended for parallel processing
- **CPU:** Multi-core (4+ cores) for effective parallelization

---

## Architecture Notes

### Multi-Rotation OCR Strategy (v1.0)

Tesseract does not reliably auto-detect rotation. Two approaches:

**Option A: PSM Mode 0 + OCR (TWO-PASS)**
1. Run `pytesseract.image_to_osd(image)` to detect orientation (PSM mode 0)
2. Rotate image based on OSD result
3. Run OCR with detected orientation

**Option B: Try All Rotations (FOUR-PASS WITH VALIDATION)**
1. Generate 4 rotated versions (0°, 90°, 180°, 270°) using Pillow
2. Run OCR on each version
3. Validate with regex `\d{5}` (5-digit ID)
4. Keep result with highest confidence or first valid match

**Recommendation:** **Option B (four-pass)** because:
- OSD (Option A) unreliable per GitHub issues ("Poor Rotation / Layout detection" #4426, June 2025)
- Regex validation (`\d{5}`) provides strong signal for correct orientation
- 4 OCR passes acceptable for 5-digit IDs (fast)
- More robust than relying on Tesseract's OSD

### Preprocessing Pipeline (v1.0)

**Primary path (clean scans):**
1. pdf2image: PDF → PIL Image (300 DPI)
2. Pillow: Convert to grayscale
3. Pillow: Rotate (0°, 90°, 180°, 270°)
4. pytesseract: OCR each rotation
5. Regex: Extract `\d{5}` patterns

**Fallback path (no ID found):**
1. OpenCV: Adaptive thresholding (Otsu or Sauvola)
2. OpenCV: Gaussian blur for noise reduction
3. OpenCV: Morphological operations (dilation/erosion)
4. Retry OCR with preprocessed image

### Parallelization Strategy (v1.0)

**Coarse-grained parallelization (per-PDF):**
- Each worker process handles one PDF end-to-end
- No shared state between workers
- Simple Pool.map(process_pdf, pdf_paths)
- Recommended: `processes=cpu_count()` or `cpu_count() - 1`

**Fine-grained parallelization (per-page) NOT recommended:**
- Overhead of IPC (inter-process communication) for each page
- Process spawn cost on Windows higher than Linux
- Coarse-grained sufficient for 30K PDFs

### Graceful Shutdown Strategy (v1.1)

**Pattern:**
1. Main process catches SIGINT (Ctrl+C) via signal handler
2. Signal handler sets multiprocessing.Event flag
3. Workers check Event before starting each new file
4. Workers finish current file if already started
5. Workers skip new files if Event is set
6. Main process waits for pool to drain (workers exit gracefully)

**Why this approach:**
- Event is cross-process (workers can check flag)
- Workers finish current file (not killed mid-processing)
- Clean shutdown without data corruption
- tqdm shows progress until shutdown completes
- Platform-independent (works on Windows 'spawn' mode)

### Windows-Specific Considerations

**Multiprocessing on Windows:**
- Uses 'spawn' start method (not 'fork')
- Requires `if __name__ == '__main__':` guard around Pool code
- All imports must be at module level (not inside main guard)
- Slower process creation than Linux, but functional

**Path handling:**
- Use pathlib for cross-platform path operations
- Avoid hardcoded backslashes: `Path("dir") / "file"` not `"dir\\file"`

**Tesseract path:**
- If Tesseract not in PATH, set: `pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'`

**Signal handling:**
- Windows supports only: SIGINT, SIGTERM, SIGBREAK, SIGABRT, SIGFPE, SIGILL, SIGSEGV
- SIGINT (Ctrl+C) raises KeyboardInterrupt by default
- Signals don't propagate to child processes reliably on Windows 'spawn' mode
- **Solution:** Catch SIGINT in main process, set multiprocessing.Event, workers check Event

**Interactive menus:**
- simple-term-menu does NOT work on Windows (Linux/macOS only)
- questionary works via prompt_toolkit (cross-platform)
- pick requires blessed backend for Windows: `pip install "pick[blessed]"`

**Atomic file operations:**
- os.replace is atomic on Windows (uses MoveFileEx)
- tempfile must be in same directory as target (same filesystem)
- fsync required before replace to ensure data on disk

---

## Confidence Assessment

### v1.0 Technologies

| Technology | Confidence | Rationale |
|------------|------------|-----------|
| Tesseract 5.5.2 | HIGH | Official release notes, PyPI, mature ecosystem |
| pytesseract 0.3.13 | HIGH | PyPI official page, well-documented |
| pdf2image 1.17.0 | HIGH | PyPI official page, active development |
| Pillow 12.2.0 | HIGH | PyPI official page, status 6 (Mature) |
| opencv-python 4.13.0.92 | HIGH | PyPI official page, latest 2026 release |
| pandas 3.0.3 | HIGH | PyPI official page, latest 2026 release |
| tqdm 4.67.3 | HIGH | PyPI official page, latest 2026 release |
| multiprocessing | HIGH | Python stdlib documentation |
| pathlib | HIGH | Python stdlib documentation |
| EasyOCR comparison | MEDIUM | Multiple 2025-2026 comparison articles, but not tested directly |
| PyMuPDF alternative | MEDIUM | Multiple sources mention speed, not verified for this use case |
| scipy for rotation | MEDIUM | Official docs, but optional for this project |

### v1.1 Campaign Management Technologies

| Technology | Confidence | Rationale |
|------------|------------|-----------|
| signal (stdlib) | HIGH | Official Python 3.14 docs, Windows SIGINT support verified |
| multiprocessing.Event | HIGH | Stdlib, recommended pattern for Windows graceful shutdown (multiple sources) |
| questionary | HIGH | Official PyPI, released Aug 2025, cross-platform via prompt_toolkit |
| pick (fallback) | MEDIUM | Official PyPI, released Feb 2026, but fallback option only |
| dataclasses-json | MEDIUM | Official PyPI (June 2024), but pre-1.0.0 and no official Python 3.13+ support yet |
| defaultdict/Counter | HIGH | Python stdlib docs, 2026 best practices articles |
| tempfile + os.replace | HIGH | Already validated in v1.0, official stdlib docs, atomic on Windows |
| tqdm with imap | HIGH | Multiple 2026 articles, GitHub discussions, proven pattern |

---

## Version Lock Rationale

All versions are latest stable as of 2026-06-05:
- **pytesseract 0.3.13:** Latest release (Aug 2024), stable
- **pdf2image 1.17.0:** Latest release (Jan 2024), mature
- **Pillow 12.2.0:** Latest release (April 2026), actively maintained
- **opencv-python 4.13.0.92:** Latest release (Feb 2026), current
- **pandas 3.0.3:** Latest release (May 2026), current
- **tqdm 4.67.3:** Latest release (Feb 2026), current
- **questionary 2.1.1:** Latest release (Aug 2025), actively maintained
- **dataclasses-json 0.6.7:** Latest release (June 2024), pre-1.0.0 but stable
- **pick 2.6.0:** Latest release (Feb 2026), fallback option

Recommend pinning these versions in requirements.txt for reproducibility.

---

## Sources

### Official Documentation
- [signal — Python 3.14.5 Documentation](https://docs.python.org/3/library/signal.html)
- [multiprocessing — Python 3.14 Documentation](https://docs.python.org/3/library/multiprocessing.html)
- [collections — Python 3.14 Documentation](https://docs.python.org/3/library/collections.html)
- [tempfile — Python 3.14 Documentation](https://docs.python.org/3/library/tempfile.html)
- [shelve — Python 3.14 Documentation](https://docs.python.org/3/library/shelve.html)
- [Data Persistence — Python 3.14.5 Documentation](https://docs.python.org/3/library/persistence.html)
- [pytesseract · PyPI](https://pypi.org/project/pytesseract/)
- [pdf2image · PyPI](https://pypi.org/project/pdf2image/)
- [opencv-python · PyPI](https://pypi.org/project/opencv-python/)
- [Pillow · PyPI](https://pypi.org/project/Pillow/)
- [pandas · PyPI](https://pypi.org/project/pandas/)
- [tqdm · PyPI](https://pypi.org/project/tqdm/)
- [Tesseract Release Notes](https://tesseract-ocr.github.io/tessdoc/ReleaseNotes.html)
- [questionary 2.1.1 · PyPI](https://pypi.org/project/questionary/)
- [pick 2.6.0 · PyPI](https://pypi.org/project/pick/)
- [simple-term-menu 1.6.6 · PyPI](https://pypi.org/project/simple-term-menu/)
- [InquirerPy 0.3.4 · PyPI](https://pypi.org/project/inquirerpy/)
- [dataclasses-json 0.6.7 · PyPI](https://pypi.org/project/dataclasses-json/)

### Best Practices & Patterns
- [Graceful exit with Python multiprocessing | The-Fonz blog](https://the-fonz.gitlab.io/posts/python-multiprocessing/)
- [Python Multiprocessing graceful shutdown in the proper order | peterspython.com](https://www.peterspython.com/en/blog/python-multiprocessing-graceful-shutdown-in-the-proper-order)
- [Handling SIGINT in multiprocessing on Windows - Python Discussions](https://discuss.python.org/t/handling-sigint-in-multiprocessing-on-windows/90064)
- [Python Multiprocessing: How to Stop a Process – 2026 Best Practices](https://copyprogramming.com/howto/python-python-multiprocessing-stop-a-process-code-example)
- [Mastering Python's Collections Counter in 2026](https://copyprogramming.com/howto/python-collections-counter-vs-defaultdict-int)
- [Running tqdm with Python multiprocessing | Redowan's Reflections](https://rednafi.com/python/tqdm-with-multiprocessing/)
- [Progress Bars for Python Multiprocessing Tasks - Lei Mao's Log Book](https://leimao.github.io/blog/Python-tqdm-Multiprocessing/)
- [Crash-safe JSON at scale: atomic writes + recovery without a DB](https://dev.to/constanta/crash-safe-json-at-scale-atomic-writes-recovery-without-a-db-3aic)
- [How to Implement Atomic File Writing in Python (No Partial Writes) | BSWEN](https://docs.bswen.com/blog/2026-04-04-atomic-file-writing-python/)
- [Best Python OCR Library in 2026: 6 Libraries Tested](https://www.codesota.com/ocr/best-for-python)
- [Tesseract vs EasyOCR vs OpenAI: Accuracy, Speed & Cost 2026](https://ttsforfree.com/en/blogs/image-to-text-python-tesseract-vs-easyocr/)
- [Ultimate guide to Python Tesseract - Nutrient](https://www.nutrient.io/blog/tesseract-python-guide/)
- [Enhancing OCR Accuracy with OpenCV and PyTesseract](https://trenton3983.github.io/posts/ocr-image-processing-pytesseract-cv2/)
- [OpenCV vs Pillow for Image Processing](https://primeprogram.medium.com/opencv-vs-pillow-which-is-better-for-image-processing-93f68ab81137)
- [Multiprocessing - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html)
- [Tesseract Page Segmentation Modes (PSMs) Explained](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/)
- [pathlib vs os.path Best Practices](https://medium.com/codeelevation/pathlib-vs-os-in-python-which-one-should-you-use-ed40a432673c)
- [questionary Python Guide [2026] | PyPI Tutorial](https://generalistprogrammer.com/tutorials/questionary-python-package-guide)

### Community Resources
- [GitHub - tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)
- [GitHub - Belval/pdf2image](https://github.com/Belval/pdf2image)
- [Poor Rotation / Layout detection Issue #4426](https://github.com/tesseract-ocr/tesseract/issues/4426)
- [GitHub - wbenny/python-graceful-shutdown](https://github.com/wbenny/python-graceful-shutdown)
- [GitHub - IngoMeyer441/simple-term-menu](https://github.com/IngoMeyer441/simple-term-menu)
- [GitHub - lidatong/dataclasses-json](https://github.com/lidatong/dataclasses-json)
- [How to update single progress bar in multiprocessing map() · tqdm Discussion #1121](https://github.com/tqdm/tqdm/discussions/1121)

---

**Stack complete.** All v1.0 technologies validated in production. v1.1 additions researched and verified against official sources as of 2026-06-05. Recommendations are prescriptive and actionable for roadmap creation.
