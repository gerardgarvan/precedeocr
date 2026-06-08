---
phase: 10-drop-in-performance-gains
plan: 02
subsystem: benchmarking
tags: [performance, benchmarking, optimization, validation]
dependency_graph:
  requires: [pymupdf-rendering]
  provides: [benchmark-infrastructure]
  affects: [performance-tuning, quality-validation]
tech_stack:
  added: []
  removed: []
  patterns: [standalone-benchmark-script, random-sampling, statistical-timing]
key_files:
  created:
    - benchmark.py
  modified: []
decisions:
  - "Standalone benchmark.py script separate from main pipeline (D-06)"
  - "100-PDF random sample with seed=42 for reproducibility (D-07)"
  - "DPI benchmark tests 200/250/300 with comparison tables (D-03)"
  - "Worker benchmark tests 16-20 for 20-core hybrid CPU (D-04)"
  - "Whitelist benchmark compares speed on 20-PDF subset (D-05)"
  - "Accuracy validation via page-by-page ID comparison against v1.1 baseline (D-08)"
  - "time.perf_counter() for precise wall-clock timing"
  - "Direct PyMuPDF rendering in run_single_pdf_at_dpi() avoids modifying main pipeline"
metrics:
  duration_minutes: 3
  tasks_completed: 1
  tests_passing: 230
  files_modified: 1
  lines_added: 533
  lines_removed: 0
  net_change: 533
completed: 2026-06-08T02:28:54Z
---

# Phase 10 Plan 02: Benchmark Infrastructure Summary

**One-liner:** Created standalone benchmark.py script with DPI (200/250/300), worker count (16-20), whitelist, and accuracy validation capabilities on 100-PDF random sample.

## What Was Built

A comprehensive standalone benchmarking script (`benchmark.py`) that tests optimal DPI settings, worker counts, whitelist impact, and accuracy validation on a random 100-PDF sample from the real corpus. This enables systematic performance optimization and quality validation before hard-coding values in the main pipeline.

**Core capabilities:**

1. **Random corpus sampling:** `select_benchmark_corpus()` selects 100 PDFs with reproducible seed, prints statistics (total PDFs, folders represented, file size range)

2. **DPI benchmarking:** `benchmark_dpi()` tests 200/250/300 DPI settings, measures total time, pages/sec throughput, IDs found, and compares accuracy against 300 DPI baseline

3. **Worker count benchmarking:** `benchmark_workers()` tests 16-20 worker counts using the main pipeline's `process_all_pdfs()` function, measures PDFs/sec throughput

4. **Whitelist impact testing:** `benchmark_whitelist()` compares OCR speed with vs without character whitelist on 20-PDF subset, reports ms/page and speedup percentage

5. **Accuracy validation:** `validate_accuracy()` performs page-by-page ID comparison against v1.1 baseline CSV, reports accuracy percentage and lists mismatches

6. **CLI interface:** Full argparse CLI with `corpus_dir`, `--baseline-csv`, `--sample-size`, `--seed`, `--skip-dpi`, `--skip-workers`, `--skip-whitelist` flags

**Impact:**
- User can now run systematic benchmarks on their hardware before modifying the main pipeline
- Reproducible testing via seed parameter
- Clear comparison tables for decision-making
- Accuracy gating prevents regressions below 94% baseline

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create benchmark.py with DPI, worker, whitelist, and accuracy benchmarks | 13c506d | benchmark.py |

## Implementation Details

### Task 1: Benchmark Script Creation

**File created:** `benchmark.py` (533 lines)

**Function implementations:**

**1. `select_benchmark_corpus(corpus_dir, sample_size=100, seed=42)`**
- Uses `Path.rglob('*.pdf')` to collect all PDFs recursively
- Uses `random.seed(seed)` + `random.sample()` for reproducible sampling
- Prints statistics: total PDFs found, sample size, folders represented, file size range (KB)
- Returns list of Path objects

**2. `run_single_pdf_at_dpi(pdf_path, dpi)`**
- Opens PDF with `fitz.open()`
- Renders each page with `page.get_pixmap(dpi=dpi, alpha=False)`
- Converts to PIL Image with `Image.frombytes()`
- Runs `extract_id_with_rotation()` for OCR extraction
- Returns list of result dicts (same format as main pipeline)
- Handles errors gracefully (returns error dict on failure)
- Includes `doc.close()` in finally block to prevent memory leaks

**3. `benchmark_dpi(pdf_paths, dpi_values=[200, 250, 300])`**
- Tests each DPI value sequentially
- Uses `time.perf_counter()` for precise wall-clock timing
- Processes all sample PDFs at each DPI setting
- Tracks: total time, pages processed, IDs found, pages/sec throughput
- Caches results for accuracy comparison
- Prints formatted comparison table
- Identifies winner (fastest pages/sec)
- Compares accuracy between winner and 300 DPI baseline
- Returns pandas DataFrame with results

**4. `benchmark_workers(pdf_paths, worker_counts=[16, 17, 18, 19, 20])`**
- Tests each worker count sequentially
- Uses main pipeline's `process_all_pdfs()` function with minimal args
- Disables checkpointing (checkpoint_frequency=999999)
- Measures total time and PDFs/sec throughput
- Prints formatted comparison table
- Identifies winner (fastest PDFs/sec)
- Returns pandas DataFrame with results
- Handles KeyboardInterrupt gracefully

**5. `benchmark_whitelist(pdf_paths, sample_count=20)`**
- Tests on 20-PDF subset for faster iteration
- Two configs tested:
  - With whitelist: `'--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'`
  - Without whitelist: `'--psm 6 --oem 3'`
- Renders each page at 300 DPI
- Runs OCR directly with `pytesseract.image_to_string()` for all 4 rotations
- Measures total time, pages processed, ms/page
- Calculates speedup percentage
- Prints formatted comparison table
- Returns pandas DataFrame with results

**6. `validate_accuracy(sample_results, baseline_csv_path)`**
- Loads v1.1 baseline CSV with pandas
- Groups baseline by (filename, page) → set of IDs
- Groups sample results by (filename, page) → set of IDs
- Compares pages present in BOTH datasets
- Calculates accuracy = matches / total_compared * 100
- Prints page-by-page mismatches (first 10)
- Asserts against 94% threshold (PASS/FAIL)
- Returns accuracy percentage

**7. `main()` — CLI entry point**
- Uses argparse for CLI interface:
  - `corpus_dir` (positional): Path to PDF corpus
  - `--baseline-csv`: Path to v1.1 baseline CSV for accuracy validation
  - `--sample-size` (default 100): Number of PDFs to sample
  - `--seed` (default 42): Random seed for reproducibility
  - `--skip-dpi`: Skip DPI benchmark
  - `--skip-workers`: Skip worker count benchmark
  - `--skip-whitelist`: Skip whitelist benchmark
- Flow:
  1. Select 100-PDF sample with `select_benchmark_corpus()`
  2. Run DPI benchmark (unless --skip-dpi)
  3. Run worker benchmark (unless --skip-workers)
  4. Run whitelist benchmark (unless --skip-whitelist)
  5. If --baseline-csv provided: run accuracy validation on DPI 300 results
  6. Print summary
- Wrapped in `if __name__ == '__main__':` guard (Windows requirement)

**Key design decisions:**

- **Standalone script (D-06):** Not integrated into main pipeline — imports pipeline functions
- **Direct rendering for DPI tests:** `run_single_pdf_at_dpi()` renders at specific DPI without modifying `process_single_pdf()`
- **Pipeline integration for worker tests:** Uses `process_all_pdfs()` directly to test real-world parallelism
- **Small sample for whitelist test:** 20 PDFs sufficient since whitelist is per-page OCR config
- **Reproducible sampling (D-07):** Seed parameter ensures same PDFs selected across runs
- **Statistical timing:** `time.perf_counter()` provides nanosecond precision wall-clock timing
- **Formatted tables:** Simple string formatting for readable comparison output
- **Accuracy validation (D-08):** Page-by-page comparison against baseline prevents regressions

## Deviations from Plan

None - plan executed exactly as written.

## Quality Verification

**Acceptance criteria met:**
- ✓ benchmark.py exists in project root
- ✓ benchmark.py contains `def select_benchmark_corpus(` with seed parameter
- ✓ benchmark.py contains `def benchmark_dpi(` with dpi_values parameter defaulting to [200, 250, 300]
- ✓ benchmark.py contains `def benchmark_workers(` with worker_counts parameter defaulting to [16, 17, 18, 19, 20]
- ✓ benchmark.py contains `def benchmark_whitelist(`
- ✓ benchmark.py contains `def validate_accuracy(`
- ✓ benchmark.py contains `if __name__ == '__main__':` guard
- ✓ benchmark.py contains `import argparse`
- ✓ benchmark.py contains `from precede_ocr import` (imports pipeline functions)
- ✓ benchmark.py contains `import fitz` (for DPI-specific rendering)
- ✓ benchmark.py contains `time.perf_counter()` (precise timing)
- ✓ benchmark.py contains `random.seed(` and `random.sample(` (reproducible sampling)
- ✓ `python -c "import benchmark"` exits with code 0
- ✓ `python benchmark.py --help` exits with code 0 and shows usage

**Verification commands:**
```bash
# All checks pass:
python -c "import benchmark; print('benchmark.py imports OK')"  # OK
python benchmark.py --help  # Shows full CLI help
grep "def select_benchmark_corpus" benchmark.py  # Found
grep "def benchmark_dpi" benchmark.py  # Found
grep "def benchmark_workers" benchmark.py  # Found
grep "def validate_accuracy" benchmark.py  # Found
grep "if __name__" benchmark.py  # Found
```

**Test coverage:**
- No new automated tests needed (benchmark script is for manual execution)
- All 230 existing tests still pass
- Script tested via import and --help invocation

**Code quality:**
- 533 lines of clean, documented code
- All functions have docstrings explaining purpose and args
- CLI help text references Phase 10 decisions (D-06, D-07, D-08)
- Error handling for missing PDFs, baseline CSV load failures, exceptions during rendering
- Windows multiprocessing compatibility (`if __name__ == '__main__':` guard)

## Known Stubs

None identified. All functions are fully implemented with:
- Actual file I/O (PDF reading, CSV loading)
- Real OCR execution (pytesseract calls)
- Statistical timing (perf_counter)
- Formatted table output (pandas DataFrame)
- Accuracy validation logic (set comparison)

## Usage Examples

**Basic DPI benchmark:**
```bash
python benchmark.py C:\path\to\corpus
```

**Full benchmark with accuracy validation:**
```bash
python benchmark.py C:\path\to\corpus --baseline-csv results_v1.1.csv
```

**Custom sample size and seed:**
```bash
python benchmark.py C:\path\to\corpus --sample-size 50 --seed 123
```

**Skip worker benchmark (run DPI and whitelist only):**
```bash
python benchmark.py C:\path\to\corpus --skip-workers
```

## Self-Check

**Files created:**
- ✓ C:\Users\Owner\Documents\precedeocr\benchmark.py exists

**Files modified:**
- None (this plan only creates benchmark.py)

**Commits exist:**
- ✓ 13c506d: feat(10-02): create benchmark.py for DPI, worker count, whitelist, and accuracy validation

**Verification commands:**
```bash
# All checks pass:
python -c "import benchmark; print('OK')"  # OK
python benchmark.py --help  # Shows usage
grep "def select_benchmark_corpus" benchmark.py  # Found
grep "def benchmark_dpi" benchmark.py  # Found
grep "def benchmark_workers" benchmark.py  # Found
grep "def benchmark_whitelist" benchmark.py  # Found
grep "def validate_accuracy" benchmark.py  # Found
grep "if __name__" benchmark.py  # Found
grep "from precede_ocr import" benchmark.py  # Found
grep "import fitz" benchmark.py  # Found
grep "time.perf_counter" benchmark.py  # Found
grep "random.seed" benchmark.py  # Found
grep "random.sample" benchmark.py  # Found
```

## Self-Check: PASSED

All files exist, all commits recorded, all verifications pass.

---

**Next Plan:** 10-03 (Apply benchmark findings — hard-code optimal DPI and worker count in pipeline)
