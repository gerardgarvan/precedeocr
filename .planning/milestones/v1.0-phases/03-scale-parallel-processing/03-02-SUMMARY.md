---
phase: 03-scale-parallel-processing
plan: 02
subsystem: pipeline
tags: [multiprocessing, parallel, tqdm, progress-bar, cli, batch-processing, windows-spawn]

# Dependency graph
requires:
  - phase: 03-scale-parallel-processing
    plan: 01
    provides: "Multi-ID data contract (ids: list[str]), process_single_pdf worker, write_results_csv/json"
provides:
  - "discover_pdfs() for recursive PDF directory scanning or single file handling"
  - "process_single_pdf_wrapper() picklable wrapper for multiprocessing on Windows"
  - "process_all_pdfs() with Pool.imap_unordered, tqdm progress, running stats"
  - "main() refactored entry point with directory+file CLI"
  - "CLI --workers flag for worker count override"
  - "CLI input_path positional arg accepting file or directory"
  - "Process recycling via maxtasksperchild=50"
affects: [04-resilience, batch-processing, cli-interface]

# Tech tracking
tech-stack:
  added: [multiprocessing, tqdm]
  patterns: [pool-imap-unordered, module-level-wrapper-for-windows-spawn, maxtasksperchild-recycling, tqdm-postfix-stats]

key-files:
  created: []
  modified:
    - precede_ocr.py
    - tests/test_precede_ocr.py

key-decisions:
  - "Default workers = cpu_count()-1, overridable with --workers N (D-06)"
  - "Process recycling with maxtasksperchild=50 to prevent Tesseract memory leaks (D-07)"
  - "tqdm per-file progress bar with running stats postfix: IDs found, no-ID pages, errors (D-08/D-09)"
  - "Single file bypasses multiprocessing pool, preserves debug mode"
  - "CLI changed from pdf_path to input_path positional arg (breaking change, intentional)"

patterns-established:
  - "Module-level wrapper functions for Windows spawn pickling compatibility"
  - "Pool.imap_unordered with chunksize=max(1, len(paths)//(4*workers)) for IPC efficiency"
  - "tqdm.set_postfix for running stats display during batch processing"
  - "Error-resilient wrapper: catch all exceptions, return error dict with notes field"

requirements-completed: [PIPE-06, PIPE-07, OUT-02, PROG-01]

# Metrics
duration: 8min
completed: 2026-06-05
---

# Phase 3 Plan 2: Parallel Processing Pipeline Summary

**Multiprocessing.Pool with imap_unordered for 30K+ PDF batch processing, tqdm progress bar with running stats, directory-mode CLI, and process recycling via maxtasksperchild=50**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-05T15:10:00Z
- **Completed:** 2026-06-05T15:29:06Z
- **Tasks:** 2 (1 TDD task + 1 human verification checkpoint)
- **Files modified:** 2

## Accomplishments
- Added `discover_pdfs()` for recursive PDF discovery in directories or single-file handling with validation
- Added `process_single_pdf_wrapper()` as a module-level picklable wrapper for Windows multiprocessing spawn
- Added `process_all_pdfs()` with `mp.Pool(processes=workers, maxtasksperchild=50)` and `imap_unordered` for streaming results
- Integrated tqdm progress bar showing file count, percentage, ETA, and running stats (IDs found, no-ID pages, errors)
- Refactored CLI to accept `input_path` (file or directory) with `--workers`, `--output-csv`, `--output-json`, and `--debug` flags
- Refactored inline `__main__` logic into `main()` function for testability and clean entry point
- Test suite grown from 60 to 70 tests with zero regressions
- Human-verified end-to-end: single file mode, directory parallel mode, progress bar, CSV+JSON outputs

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): PDF discovery, wrapper, and parallel processing engine tests** - `5512d5c` (test)
2. **Task 1 (GREEN): Implement parallel processing with multiprocessing.Pool** - `e94dd5c` (feat)
3. **Task 2: Human verification checkpoint** - approved, no commit

## Files Created/Modified
- `precede_ocr.py` - Added discover_pdfs(), process_single_pdf_wrapper(), process_all_pdfs(), main() function; added multiprocessing and tqdm imports; updated CLI with input_path positional arg and --workers flag
- `tests/test_precede_ocr.py` - Added TestDiscoverPdfs (6 tests), TestProcessSinglePdfWrapper (2 tests), TestProcessAllPdfs (2 tests)

## Decisions Made
- **D-06 Worker count:** Default workers = `cpu_count() - 1`, overridable with `--workers N` CLI flag. Leaves one core free for OS/tqdm updates.
- **D-07 Process recycling:** `maxtasksperchild=50` recycles worker processes after 50 PDFs to prevent Tesseract memory leak accumulation over 30K+ files.
- **D-08 Progress bar:** tqdm wraps `imap_unordered` iterator with total file count, showing percentage, elapsed time, rate, and ETA.
- **D-09 Running stats:** `pbar.set_postfix()` displays live IDs found, no-ID pages, and error counts during processing.
- **Single-file bypass:** When only one PDF is found, processing runs directly (no pool) to preserve `--debug` mode functionality and avoid multiprocessing overhead.
- **CLI breaking change:** Positional arg renamed from `pdf_path` to `input_path` to reflect directory support. Intentional per phase scope.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - plan executed cleanly.

## Known Stubs
None - all functions are fully wired with real data sources.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete parallel pipeline ready for 30K+ PDF processing
- 70 tests provide comprehensive regression safety for Phase 4 resilience work
- Error dict pattern in process_single_pdf_wrapper provides foundation for Phase 4 error handling/retry
- process_all_pdfs stats tracking (errors count) ready for Phase 4 batch statistics
- CLI accepts both single file and directory, ready for Phase 4 resume/checkpoint features

## Self-Check: PASSED

- All 2 modified files exist on disk (precede_ocr.py, tests/test_precede_ocr.py)
- Both task commits verified in git log (5512d5c, e94dd5c)
- 70/70 tests passing
- SUMMARY.md created at expected path

---
*Phase: 03-scale-parallel-processing*
*Completed: 2026-06-05*
