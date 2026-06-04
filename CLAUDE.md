<!-- GSD:project-start source:PROJECT.md -->
## Project

**Precede OCR — PDF ID Scanner & Mapper**

A batch OCR pipeline that scans ~30,429 multi-page PDF files containing scanned/photographed images, extracts 5-digit numeric "Precede" IDs from each page, and produces structured output (CSV + JSON) mapping every ID to its source file and page number. The IDs are typically rotated ~90 degrees on the page and appear below the word "Precede" in cursive.

**Core Value:** Reliably extract every Precede ID from every page across 30K+ PDFs so the user can look up which file and page any given ID lives in.

### Constraints

- **Platform**: Windows 10 — all tooling must work on Windows
- **Dependencies**: Tesseract OCR + Poppler already installed; Python 3.x ecosystem
- **Scale**: ~30,429 PDFs with multiple pages each — must parallelize; single-threaded would be impractical
- **OCR quality**: Scanned images vary in quality; preprocessing pipeline needed for degraded scans
- **No manual intervention**: Must run fully automated once pointed at a directory
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core OCR Engine
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Tesseract OCR** | 5.5.2 | OCR engine for text extraction | Industry-standard open-source OCR with LSTM neural networks (v5.x). 32-bit float ops reduce RAM usage. Best accuracy-to-speed balance for clean scanned documents (sub-1-second per page). CPU-first design avoids GPU requirements. Already installed per project constraints. **Confidence: HIGH** |
| **pytesseract** | 0.3.13 | Python wrapper for Tesseract | Official Python binding. Simple API (`image_to_string`, `image_to_data`). Mature (Python 3.8+). Direct integration with PIL/Pillow. **Confidence: HIGH** |
# Tesseract 5.5.2 already installed (Windows installer from UB Mannheim)
### PDF-to-Image Conversion
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pdf2image** | 1.17.0 | Convert PDF pages to PIL Images | Wraps Poppler's pdftoppm/pdftocairo utilities. Supports high-DPI rendering (300+ DPI) required for OCR accuracy. Handles multi-page PDFs efficiently. `use_pdftocairo` parameter improves performance. `paths_only` parameter prevents OOM on large PDFs. **Confidence: HIGH** |
| **Poppler** | Latest stable | PDF rendering engine | Already installed per project constraints. Cross-platform PDF utilities (pdftoppm, pdftocairo). Industry standard for PDF rasterization. **Confidence: HIGH** |
# Poppler already installed (Windows binaries in PATH)
### Image Preprocessing
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **Pillow (PIL)** | 12.2.0 | Basic image operations | Python's standard imaging library. Handles format conversion, basic transforms (resize, rotate). Native integration with pytesseract and pdf2image. Lightweight for basic preprocessing. Mature (status 6 - Mature). **Confidence: HIGH** |
| **OpenCV (opencv-python)** | 4.13.0.92 | Advanced preprocessing | Superior for complex preprocessing: adaptive thresholding (Otsu, Sauvola), noise reduction (Gaussian blur, morphological ops), edge detection, perspective correction. CPU-optimized. Required for fallback preprocessing on degraded scans. **Confidence: HIGH** |
### Parallelization
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **multiprocessing** | stdlib | CPU-bound parallel processing | Python stdlib. Required for scaling to 30K+ PDFs. Pool.map() for embarrassingly parallel tasks (each PDF independent). Windows uses 'spawn' start method — requires `if __name__ == '__main__'` guard. Speed improvements: 100%+ (2x faster) for PDF processing workloads. **Confidence: HIGH** |
### Progress Tracking
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **tqdm** | 4.67.3 | Progress visualization | Wraps iterables with smart progress bars. Shows percentage, iteration rate, ETA. Low overhead (60ns/iter). Works with multiprocessing via `tqdm(pool.imap(...))` or tqdm-multiprocess package. Essential UX for 30K+ file batch job. **Confidence: HIGH** |
### Output Formatting
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pandas** | 3.0.3 | CSV/JSON export | Standard DataFrame library. Clean API for structured data: `df.to_csv()` and `df.to_json()`. Handles missing values (NaN → null). `orient='records'` for JSON produces list-of-dicts format for lookups. Efficient I/O for large datasets. **Confidence: HIGH** |
### File System Operations
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pathlib** | stdlib | Path manipulation | Modern OOP path API. Cross-platform compatibility. Cleaner syntax: `Path("dir") / "file.pdf"`. Built-in methods: `.exists()`, `.is_file()`, `.glob()`. Recommended over os.path for Python 3+. **Confidence: HIGH** |
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
# numpy auto-installed with opencv-python
## Installation Summary
# Core dependencies (Tesseract and Poppler already installed on Windows)
# Optional advanced rotation
- **OS:** Windows 10 (project constraint)
- **Python:** 3.8+ (pytesseract requirement)
- **Tesseract OCR:** 5.5.2 (already installed)
- **Poppler:** Latest stable (already installed)
- **RAM:** 8GB+ recommended for parallel processing
- **CPU:** Multi-core (4+ cores) for effective parallelization
## Architecture Notes
### Multi-Rotation OCR Strategy
- OSD (Option A) unreliable per GitHub issues ("Poor Rotation / Layout detection" #4426, June 2025)
- Regex validation (`\d{5}`) provides strong signal for correct orientation
- 4 OCR passes acceptable for 5-digit IDs (fast)
- More robust than relying on Tesseract's OSD
### Preprocessing Pipeline
### Parallelization Strategy
- Each worker process handles one PDF end-to-end
- No shared state between workers
- Simple Pool.map(process_pdf, pdf_paths)
- Recommended: `processes=cpu_count()` or `cpu_count() - 1`
- Overhead of IPC (inter-process communication) for each page
- Process spawn cost on Windows higher than Linux
- Coarse-grained sufficient for 30K PDFs
### Windows-Specific Considerations
- Uses 'spawn' start method (not 'fork')
- Requires `if __name__ == '__main__':` guard around Pool code
- All imports must be at module level (not inside main guard)
- Slower process creation than Linux, but functional
- Use pathlib for cross-platform path operations
- Avoid hardcoded backslashes: `Path("dir") / "file"` not `"dir\\file"`
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
- **pytesseract 0.3.13:** Latest release (Aug 2024), stable
- **pdf2image 1.17.0:** Latest release (Jan 2024), mature
- **Pillow 12.2.0:** Latest release (April 2026), actively maintained
- **opencv-python 4.13.0.92:** Latest release (Feb 2026), current
- **pandas 3.0.3:** Latest release (May 2026), current
- **tqdm 4.67.3:** Latest release (Feb 2026), current
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
