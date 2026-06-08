---
phase: 10-drop-in-performance-gains
plan: 01
subsystem: pdf-rendering
tags: [performance, dependency-upgrade, rendering-engine]
dependency_graph:
  requires: []
  provides: [pymupdf-rendering]
  affects: [ocr-pipeline, process_single_pdf]
tech_stack:
  added: [pymupdf>=1.27.0]
  removed: [pdf2image==1.17.0, poppler]
  patterns: [in-memory-pixmap-rendering, resource-cleanup]
key_files:
  created: []
  modified:
    - precede_ocr.py
    - requirements.txt
decisions:
  - "PyMuPDF in-memory rendering replaces pdf2image disk-backed approach"
  - "No fallback to pdf2image - single rendering path for simplicity"
  - "doc.close() in finally block prevents memory leaks"
  - "File-level error handling on fitz.open() failure"
metrics:
  duration_minutes: 3
  tasks_completed: 2
  tests_passing: 230
  files_modified: 2
  lines_added: 31
  lines_removed: 68
  net_change: -37
completed: 2026-06-08T02:23:11Z
---

# Phase 10 Plan 01: PyMuPDF Rendering Swap Summary

**One-liner:** Replaced pdf2image/Poppler with PyMuPDF in-memory pixmap rendering (2-12x faster, zero disk I/O for intermediate images).

## What Was Built

Swapped the entire PDF-to-image rendering pipeline from pdf2image + Poppler (disk-backed) to PyMuPDF (in-memory pixmaps). This is the highest-impact optimization in Phase 10, with benchmarks showing 2-12x speedup for PDF rasterization.

**Core changes:**
- `fitz.open()` + `page.get_pixmap(dpi=300, alpha=False)` replaces `convert_from_path()`
- `Image.frombytes()` converts pixmap to PIL Image in-memory (no temp directory, no disk I/O)
- Removed 35 lines of Poppler auto-detection logic
- Updated requirements.txt: `pymupdf>=1.27.0` replaces `pdf2image==1.17.0`

**Impact:**
- Net -37 lines of code (68 removed, 31 added)
- Zero test changes required (tests mock at process_single_pdf level)
- All 230 tests pass
- No Poppler warnings on module import

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Replace pdf2image with PyMuPDF rendering in precede_ocr.py | 0df58e4 | precede_ocr.py |
| 2 | Update requirements.txt and verify test suite | 720221c | requirements.txt |

## Implementation Details

### Task 1: PyMuPDF Rendering Integration

**Changes to precede_ocr.py:**

1. **Import swap (line 30):**
   - Removed: `from pdf2image import convert_from_path`
   - Added: `import fitz  # PyMuPDF`
   - Removed: `import shutil` (only used for temp_dir cleanup)
   - Kept: `import tempfile` (used elsewhere for atomic checkpoint writes)

2. **Removed Poppler detection (lines 49-83):**
   - Deleted `_POPPLER_FIXED_PATHS` list
   - Deleted `POPPLER_PATH` variable and all auto-detection logic
   - Deleted warning message for missing Poppler
   - 35 lines removed

3. **Rewritten `process_single_pdf()` rendering (lines 476-511):**

**Old approach (disk-backed):**
```python
temp_dir = tempfile.mkdtemp(prefix='precede_ocr_')
try:
    image_paths = convert_from_path(
        pdf_path, dpi=300, output_folder=temp_dir,
        paths_only=True, fmt='png', poppler_path=POPPLER_PATH
    )
    for page_num, image_path in enumerate(image_paths, start=1):
        with Image.open(image_path) as img:
            # OCR processing...
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
```

**New approach (in-memory):**
```python
try:
    doc = fitz.open(pdf_path)
except Exception as e:
    return [{'filename': filename, 'page': 0, 'ids': [],
             'rotation_detected': None, 'notes': f'error: {type(e).__name__}: {e}'}]

try:
    for page_idx in range(len(doc)):
        page = doc[page_idx]
        pix = page.get_pixmap(dpi=300, alpha=False)  # In-memory RGB pixmap
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        # OCR processing...
finally:
    doc.close()  # Critical: prevent memory leaks
```

**Key differences:**
- No temporary directory creation or cleanup
- Separate try-except for `fitz.open()` errors (file-level error handling per D-02)
- `alpha=False` ensures RGB mode required for Tesseract OCR
- `doc.close()` in finally block prevents memory leaks (per must_have)
- Page iteration uses `range(len(doc))` instead of enumerating file paths
- Page numbers still 1-indexed (`page_idx + 1`) for output consistency

### Task 2: Dependency Update and Test Verification

**requirements.txt:**
- Replaced `pdf2image==1.17.0` with `pymupdf>=1.27.0`
- All other dependencies unchanged

**Test suite verification:**
- Ran `pytest tests/test_precede_ocr.py -x -v`
- All 230 tests pass without modification
- No test changes needed because tests mock `process_single_pdf_wrapper()` at a higher level
- No direct pdf2image references in test code

**Module import verification:**
- `python -c "import fitz; import precede_ocr; print('OK')"` succeeds
- No "WARNING: Could not auto-detect Poppler" message on import
- PyMuPDF version: 1.27.2.3

## Deviations from Plan

None - plan executed exactly as written.

## Performance Expectations

**Based on research synthesis (Phase 10 RESEARCH.md):**

- **PyMuPDF rendering speedup:** 2-12x faster than pdf2image
  - Benchmark A (2024 blog): 12x faster (0.5s vs 6s per page)
  - Benchmark B (2025 SO): 2-3x faster in typical usage
  - Conservative estimate: 5-10x for this use case (high-DPI rendering)

- **Memory impact:**
  - Eliminates temp directory overhead
  - In-memory pixmap processing reduces I/O wait
  - `doc.close()` in finally block prevents accumulation across 30K+ files

- **Disk I/O eliminated:**
  - Old: PDF → temp PNG files → read back into memory → delete
  - New: PDF → in-memory pixmap → PIL Image (zero disk writes)

**Next steps (Plan 02):**
- Benchmark actual speedup on user's hardware
- Test DPI optimization (200/250/300 for speed vs accuracy)
- Verify memory usage doesn't spike with multi-core processing

## Quality Verification

**Acceptance criteria met:**
- ✓ precede_ocr.py contains `import fitz`
- ✓ No `from pdf2image import convert_from_path`
- ✓ No `POPPLER_PATH` references
- ✓ No `_POPPLER_FIXED_PATHS` references
- ✓ No `convert_from_path(` calls
- ✓ Contains `fitz.open(pdf_path)` in process_single_pdf
- ✓ Contains `page.get_pixmap(dpi=300, alpha=False)`
- ✓ Contains `Image.frombytes("RGB", [pix.width, pix.height], pix.samples)`
- ✓ Contains `doc.close()` in finally block
- ✓ Module imports without errors

**Test coverage:**
- 230/230 tests pass (100% pass rate)
- No test modifications required
- No new tests added (rendering swap is internal implementation detail)

**Code quality:**
- Net -37 lines (removed more than added)
- Simpler code flow (no temp directory management)
- Better resource cleanup (doc.close() in finally)
- Improved error handling (separate try-except for file open vs page processing)

## Known Stubs

None identified.

## Self-Check

**Files created:**
- None (this is a swap, not new functionality)

**Files modified:**
- ✓ C:\Users\Owner\Documents\precedeocr\precede_ocr.py exists
- ✓ C:\Users\Owner\Documents\precedeocr\requirements.txt exists

**Commits exist:**
- ✓ 0df58e4: feat(10-01): replace pdf2image with PyMuPDF for in-memory PDF rendering
- ✓ 720221c: chore(10-01): update dependencies - replace pdf2image with pymupdf

**Verification commands:**
```bash
# All checks pass:
python -c "import fitz; import precede_ocr; print('OK')"  # OK
python -m pytest tests/test_precede_ocr.py -x  # 230 passed in 13.34s
grep -r "pdf2image\|POPPLER_PATH\|convert_from_path" precede_ocr.py requirements.txt tests/  # No matches
grep "import fitz" precede_ocr.py  # Match found
grep "pymupdf" requirements.txt  # Match found
```

## Self-Check: PASSED

All files exist, all commits recorded, all verifications pass.

---

**Next Plan:** 10-02 (Tesseract optimization + DPI/worker benchmarking)
