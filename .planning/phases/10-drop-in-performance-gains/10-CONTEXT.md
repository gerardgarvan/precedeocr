# Phase 10: Drop-in Performance Gains - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Achieve 2-15x speedup through low-risk, high-impact optimizations: replace pdf2image/Poppler with PyMuPDF for PDF rendering, benchmark optimal DPI (200/250/300) and worker count (16-20), and validate all changes maintain >=94% OCR accuracy. Character whitelist (TESS-01) is already implemented.

Requirements in scope: RENDER-01, RENDER-02, TESS-01, PIPE-01, QUAL-01, QUAL-02

</domain>

<decisions>
## Implementation Decisions

### PyMuPDF Rendering (RENDER-01)
- **D-01:** Use in-memory pixmaps (`page.get_pixmap()` -> PIL Image) for maximum speed. No disk I/O for intermediate images. Each worker processes one page at a time so memory is bounded.
- **D-02:** On PyMuPDF failure (corrupted/encrypted/unusual PDFs), log error and skip the file — same as current error handling. No fallback to pdf2image. Single rendering path.

### DPI Optimization (RENDER-02)
- **D-03:** Benchmark 200, 250, and 300 DPI on 100-PDF random sample. Hard-code the winning DPI value in the pipeline. No --dpi CLI flag — keep it simple.

### Worker Count Tuning (PIPE-01)
- **D-04:** Benchmark worker counts 16-20 on 20-core hybrid CPU (8P + 12E). Hard-code optimal value as default. Existing `--workers` CLI flag remains for override.

### Character Whitelist (TESS-01)
- **D-05:** Already implemented at `precede_ocr.py:433` — config `'--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'`. Benchmark will confirm speed impact vs removing the whitelist. No code change needed unless benchmark reveals issues.

### Benchmarking Methodology (QUAL-01, QUAL-02)
- **D-06:** Separate `benchmark.py` script (not integrated into main pipeline). Imports pipeline functions, runs DPI/worker/rendering tests, outputs comparison tables.
- **D-07:** 100-PDF random sample from real corpus (not 1000 — time-effective for iteration). Must be representative across different source folders.
- **D-08:** Accuracy validation by comparing extracted IDs page-by-page against v1.1 baseline results on the same 100 PDFs. Accuracy = percentage of matching ID extractions.

### Dependency Transition
- **D-09:** Fully remove pdf2image from imports and requirements. Fully remove Poppler as system dependency. PyMuPDF (`pip install pymupdf`) bundles its own MuPDF renderer — no separate binary install needed. Simplifies setup.

### Claude's Discretion
- PyMuPDF API usage details (matrix scaling for DPI, colorspace selection)
- Benchmark script output format (tables, CSV, markdown)
- How to sample 100 random PDFs from corpus (random.sample on file list)
- Test infrastructure for the swap (updating existing tests to use PyMuPDF)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline Source
- `precede_ocr.py` — Main pipeline. PDF rendering at line 517-522 (convert_from_path), OCR config at line 433 (Tesseract config with whitelist), worker pool at line 1412 (mp.Pool), worker count default at line 2079-2080

### Project Artifacts
- `.planning/REQUIREMENTS.md` — RENDER-01, RENDER-02, TESS-01, PIPE-01, QUAL-01, QUAL-02 requirement definitions
- `.planning/ROADMAP.md` — Phase 10 success criteria (5 items)
- `.planning/PROJECT.md` — Key decisions table, constraints, current state

### Test Suite
- `tests/test_precede_ocr.py` — Existing tests (230 passing). Must update tests that reference pdf2image.
- `tests/conftest.py` — Test configuration/fixtures

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `process_single_pdf()` — Core per-PDF processing function. Rendering swap happens here (line 517-522). Rest of function (OCR, rotation, regex matching) stays the same.
- `process_all_pdfs()` — Pool management with `mp.Pool(processes=workers, maxtasksperchild=50)`. Worker count change is a one-line default update.
- `_init_worker()` — Worker initializer for signal handling. No changes needed.
- Error handling pattern: try/except around rendering with structured error result dicts.

### Established Patterns
- **Memory safety**: Current approach uses `output_folder` + `paths_only=True` to prevent OOM. PyMuPDF in-memory swap means this safety net changes — one pixmap at a time per worker replaces it.
- **Temp directory cleanup**: `tempfile.mkdtemp()` with cleanup in finally block. PyMuPDF in-memory eliminates need for temp dirs entirely.
- **Process recycling**: `maxtasksperchild=50` prevents memory leaks. Keep this with PyMuPDF.
- **Tesseract config**: Already centralized as string literal at two locations (line 433, 468). Both use same whitelist config.

### Integration Points
- `from pdf2image import convert_from_path` (line 31) — Replace with `import fitz`
- `convert_from_path()` call (line 517-522) — Replace with `fitz.open()` + `page.get_pixmap()`
- Temp directory creation/cleanup around rendering — Can be removed with in-memory approach
- `requirements.txt` or `pyproject.toml` — Swap pdf2image for pymupdf
- CLI `--workers` default (line 2080) — Update default after benchmarking
- DPI constant `dpi=300` (line 519) — Update after benchmarking

</code_context>

<specifics>
## Specific Ideas

- User wants 100-PDF sample (not 1000) for benchmark iteration speed
- User explicitly chose simplicity: hard-coded winners, no fallback paths, clean dependency removal
- Existing `--workers` flag stays as escape hatch for worker count override

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 10-drop-in-performance-gains*
*Context gathered: 2026-06-07*
