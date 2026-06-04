# Technology Stack

**Project:** Precede OCR — PDF ID Scanner & Mapper
**Researched:** 2026-06-04
**Target Platform:** Windows 10
**Scale:** ~30,429 multi-page PDFs with rotation handling

## Recommended Stack

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

## Alternatives Considered

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

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **numpy** | Latest stable | Array operations for OpenCV | OpenCV returns numpy arrays. Required dependency for opencv-python. Auto-installed with OpenCV. **Confidence: HIGH** |
| **scipy** | Latest stable | Advanced image rotation (optional) | `scipy.ndimage.rotate()` for arbitrary-angle rotation. Optional: Pillow's `Image.rotate()` sufficient for 90° increments. Include if advanced rotation needed. **Confidence: MEDIUM** |

**Installation:**
```bash
# numpy auto-installed with opencv-python
pip install scipy  # Optional, only if advanced rotation needed
```

## Installation Summary

**Full stack installation:**
```bash
# Core dependencies (Tesseract and Poppler already installed on Windows)
pip install pytesseract==0.3.13
pip install pdf2image==1.17.0
pip install Pillow==12.2.0
pip install opencv-python==4.13.0.92
pip install pandas==3.0.3
pip install tqdm==4.67.3

# Optional advanced rotation
pip install scipy
```

**System requirements:**
- **OS:** Windows 10 (project constraint)
- **Python:** 3.8+ (pytesseract requirement)
- **Tesseract OCR:** 5.5.2 (already installed)
- **Poppler:** Latest stable (already installed)
- **RAM:** 8GB+ recommended for parallel processing
- **CPU:** Multi-core (4+ cores) for effective parallelization

## Architecture Notes

### Multi-Rotation OCR Strategy

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

### Preprocessing Pipeline

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

### Parallelization Strategy

**Coarse-grained parallelization (per-PDF):**
- Each worker process handles one PDF end-to-end
- No shared state between workers
- Simple Pool.map(process_pdf, pdf_paths)
- Recommended: `processes=cpu_count()` or `cpu_count() - 1`

**Fine-grained parallelization (per-page) NOT recommended:**
- Overhead of IPC (inter-process communication) for each page
- Process spawn cost on Windows higher than Linux
- Coarse-grained sufficient for 30K PDFs

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

## Confidence Assessment

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

## Version Lock Rationale

All versions are latest stable as of 2026-06-04:
- **pytesseract 0.3.13:** Latest release (Aug 2024), stable
- **pdf2image 1.17.0:** Latest release (Jan 2024), mature
- **Pillow 12.2.0:** Latest release (April 2026), actively maintained
- **opencv-python 4.13.0.92:** Latest release (Feb 2026), current
- **pandas 3.0.3:** Latest release (May 2026), current
- **tqdm 4.67.3:** Latest release (Feb 2026), current

Recommend pinning these versions in requirements.txt for reproducibility.

## Sources

### Official Documentation
- [pytesseract · PyPI](https://pypi.org/project/pytesseract/)
- [pdf2image · PyPI](https://pypi.org/project/pdf2image/)
- [opencv-python · PyPI](https://pypi.org/project/opencv-python/)
- [Pillow · PyPI](https://pypi.org/project/Pillow/)
- [pandas · PyPI](https://pypi.org/project/pandas/)
- [tqdm · PyPI](https://pypi.org/project/tqdm/)
- [Tesseract Release Notes](https://tesseract-ocr.github.io/tessdoc/ReleaseNotes.html)
- [multiprocessing — Python Documentation](https://docs.python.org/3/library/multiprocessing.html)

### Technical Comparisons and Best Practices
- [Best Python OCR Library in 2026: 6 Libraries Tested](https://www.codesota.com/ocr/best-for-python)
- [Tesseract vs EasyOCR vs OpenAI: Accuracy, Speed & Cost 2026](https://ttsforfree.com/en/blogs/image-to-text-python-tesseract-vs-easyocr/)
- [Ultimate guide to Python Tesseract - Nutrient](https://www.nutrient.io/blog/tesseract-python-guide/)
- [Enhancing OCR Accuracy with OpenCV and PyTesseract](https://trenton3983.github.io/posts/ocr-image-processing-pytesseract-cv2/)
- [OpenCV vs Pillow for Image Processing](https://primeprogram.medium.com/opencv-vs-pillow-which-is-better-for-image-processing-93f68ab81137)
- [Multiprocessing - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html)
- [Tesseract Page Segmentation Modes (PSMs) Explained](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/)
- [pathlib vs os.path Best Practices](https://medium.com/codeelevation/pathlib-vs-os-in-python-which-one-should-you-use-ed40a432673c)
- [Progress Bars for Python Multiprocessing Tasks](https://leimao.github.io/blog/Python-tqdm-Multiprocessing/)

### Community Resources
- [GitHub - tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract)
- [GitHub - Belval/pdf2image](https://github.com/Belval/pdf2image)
- [Poor Rotation / Layout detection Issue #4426](https://github.com/tesseract-ocr/tesseract/issues/4426)

---

**Stack complete.** All versions verified against official sources as of 2026-06-04. Recommendations are prescriptive and actionable for roadmap creation.
