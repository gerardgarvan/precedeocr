# Precede OCR — PDF ID Scanner & Mapper

## What This Is

A batch OCR pipeline that scans ~30,429 multi-page PDF files containing scanned/photographed images, extracts 5-digit numeric "Precede" IDs from each page, and produces structured output (CSV + JSON) mapping every ID to its source file and page number. Includes campaign management: interactive resume menu, graceful shutdown, per-folder quality statistics, and auto-generated reports.

## Core Value

Reliably extract every Precede ID from every page across 30K+ PDFs so the user can look up which file and page any given ID lives in.

## Current State

Shipped v1.2 Performance Optimization — 5,471 LOC Python (2,151 pipeline + 3,320 tests).
259 tests passing. 100% accuracy on benchmark sample.
Production run complete: 30,365 files processed in 1h40m, 52,055 IDs extracted, 49 failures, 59 no-match pages.
Tech stack: Python 3, pytesseract, PyMuPDF (fitz), OpenCV, Pillow, pandas, scipy.

CLI: `python precede_ocr.py scan <file_or_dir> --output-csv --output-json --workers N --debug --fresh`
Subcommands: scan, lookup, investigate, clean-multi-ids (Phase 13 foundation — lookup in Phase 14, investigate in Phase 15; clean-multi-ids stub pending Phase 16)
Lookup: `python precede_ocr.py lookup results.csv --output output/lookup.csv` — generates sorted, Excel-compatible ID lookup CSV
Investigate: `python precede_ocr.py investigate results.csv --report output/quality_report.md` — diagnoses failed files and no-match pages, produces quality report + CSV exports

**Campaign features (v1.1):**
- Interactive 6-option resume menu (continue, re-run failures, view stats, export partial, fresh start, quit)
- Graceful Ctrl+C shutdown with worker protection and clean state persistence
- Per-folder quality statistics with condensed console view (top 10 worst folders)
- Auto-generated campaign_report.md with problem highlighting and recommendations
- Error categorization and rotation/preprocessing distribution tracking

## Current Milestone: v1.3 Results Cleanup & ID Lookup

**Goal:** Produce a clean, Excel-friendly ID lookup file from production results, and investigate/fix pipeline errors and multi-ID noise.

**Target features:**
- ID lookup CSV sorted by ID with columns: ID, Filename, Page, Folder
- Investigate and fix 49 failed files (46 FileNotFoundError, 3 EmptyFileError)
- Investigate and fix 59 no-match pages where OCR found no ID
- Investigate 5,141 multi-ID pages to determine real vs OCR noise, clean up false positives
- Error/quality report documenting findings and remaining issues

## Requirements

### Validated

- ✓ Convert each PDF page to a high-DPI image (300+ DPI) for OCR — v1.0
- ✓ Extract 5-digit numeric IDs from OCR output via regex — v1.0
- ✓ Map each ID to its source filename and page number — v1.0
- ✓ Output results as CSV (`filename, id, page, rotation_detected, notes`) — v1.0
- ✓ Handle ~90-degree rotated text (multi-rotation OCR strategy) — v1.0
- ✓ Recursively discover all `.pdf` files in a target directory — v1.0
- ✓ Output results as JSON (`{filename: {page: [ids], ...}}`) — v1.0
- ✓ Flag pages where no ID is found (not silently dropped) — v1.0
- ✓ Handle multiple IDs per page if present — v1.0
- ✓ Parallelize processing to handle 30,429 files efficiently — v1.0
- ✓ Per-file error handling so a single corrupted PDF does not crash the batch — v1.0
- ✓ Checkpoint/resume capability to continue after crash or interruption — v1.0
- ✓ Preprocess low-quality scans (grayscale, threshold, denoise) as fallback — v1.0
- ✓ Handle OCR near-misses (O/0, I/1, S/5 confusion) with normalization — v1.0
- ✓ Interactive campaign menu on start/resume — v1.1
- ✓ Graceful Ctrl+C handling (finishes current files, saves state cleanly) — v1.1
- ✓ Comprehensive statistics: completion progress, quality metrics, per-folder breakdown — v1.1
- ✓ Per-directory status tracking to identify problem areas — v1.1
- ✓ Switch PDF rendering to PyMuPDF for faster rasterization — v1.2
- ✓ Optimize Tesseract configuration for digit-only extraction — v1.2
- ✓ Reduce per-page OCR passes with smarter rotation strategy — v1.2
- ✓ Tune parallel worker allocation for hybrid CPU architecture — v1.2
- ✓ Profile and optimize end-to-end pipeline throughput — v1.2

### Active

- ✓ Generate ID lookup CSV sorted by ID (columns: ID, Filename, Page, Folder) — v1.3 Phase 14
- ✓ Investigate and fix failed files (FileNotFoundError, EmptyFileError) — v1.3 Phase 15
- ✓ Investigate and fix no-match pages (59 pages with no ID extracted) — v1.3 Phase 15
- [ ] Investigate multi-ID pages (5,141 pages) and clean up false positives — v1.3
- ✓ Produce error/quality report documenting findings — v1.3 Phase 15

### Out of Scope

- GUI or web interface — CLI/script only, output to files
- Search CLI tool — user will search CSV/JSON manually or via Excel
- Cloud OCR services — using local Tesseract, no API costs at scale
- Rewriting or modifying the source PDFs — read-only processing
- Real-time/streaming processing — one-shot batch job
- Database backend — CSV/JSON is portable and sufficient
- Custom OCR model training — Tesseract's numeric recognition is sufficient

## Context

- PDFs are scanned or photographed documents (rasterized pages, no embedded text layer)
- Each page contains a "Precede" label in cursive font with a 5-digit numeric ID below it
- The IDs are oriented at approximately 90 degrees from upright reading position
- Total corpus: ~30,429 PDF files, each with multiple pages
- Running on Windows 10 with Tesseract OCR and Poppler already installed

## Constraints

- **Platform**: Windows 10 — all tooling must work on Windows
- **Dependencies**: Tesseract OCR + Poppler already installed; Python 3.x ecosystem
- **Scale**: ~30,429 PDFs with multiple pages each — must parallelize; single-threaded would be impractical
- **OCR quality**: Scanned images vary in quality; preprocessing pipeline needed for degraded scans
- **No manual intervention**: Must run fully automated once pointed at a directory

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + pytesseract + pdf2image | User's stated preference, well-suited ecosystem for OCR batch work | ✓ Good — clean API, mature libraries |
| Multi-rotation OCR (90/270/0/180) | IDs are rotated ~90 degrees; brute-force all rotations with regex validation | ✓ Good — 94.9% accuracy, simple and reliable |
| CSV + JSON dual output | CSV for Excel/manual inspection, JSON for programmatic lookup | ✓ Good — both generated by default, minimal overhead |
| Local Tesseract (no cloud OCR) | Dependencies already installed, no API costs at scale, simpler pipeline | ✓ Good — zero cost, no network dependency |
| multiprocessing.Pool parallelization | 30K+ files makes serial processing impractical; cpu_count()-1 workers | ✓ Good — process recycling prevents memory leaks |
| Atomic checkpoint writes (tempfile + os.replace) | Prevents corruption on crash | ✓ Good — crash-safe resume verified |
| Separate campaign_state.json from .checkpoint.json | Campaign metadata (ID, status, interruptions) decoupled from granular results | ✓ Good — independent evolution, silent upgrade from v1.0 |
| Conditional preprocessing (OpenCV fallback) | Only preprocess when initial OCR fails — avoids degrading good scans | ✓ Good — targeted improvement without side effects |
| Stdlib-only menu (input, not questionary) | Avoid external deps and Windows terminal compat issues; menu shown when workers idle | ✓ Good — zero dependencies, cross-platform |
| Local stats aggregation, not Manager | Avoids 10-100x IPC overhead; folder_stats accumulated in main process from worker results | ✓ Good — zero overhead, clean data flow |
| F-string templates for report (not pandas.to_markdown) | Full control over highlighting, no tabulate version upgrade needed | ✓ Good — custom formatting with problem folder emphasis |
| multiprocessing.Event for cooperative shutdown | Workers check event flag, not killed by signal; prevents mid-OCR corruption | ✓ Good — clean shutdown on Windows |
| Theil-Sen robust regression for sequence validation | OLS too sensitive to outliers; Theil-Sen + modified Z-score more reliable | ✓ Good — corrected from initial OLS approach in Phase 5 gap closure |
| PSM 6 for Tesseract | Middle ground for full-page scans with isolated IDs | ✓ Good — better than PSM 7 (too restrictive) or PSM 3 (too broad) |
| OEM 1 (LSTM-only) + dict-off | OEM 1 skips engine auto-detection; dict-off removes dictionary init overhead | ✓ Marginal — 1.01x speedup but free (flag changes only), 100% accuracy. Phase 11 |
| Batch page rendering with OOM fallback | Pre-render all pages before OCR loop; catch MemoryError and fall back to page-by-page | ✓ Good — code clarity, MemoryError safety. No speedup (OCR is bottleneck). Phase 12 |
| DPI 300 fallback for failed pages | Re-render individual failed pages at DPI 300 after all 8 OCR passes fail at DPI 200 | ✓ Good — recovers 1.6% of pages, achieving 100% coverage. Phase 12 |
| Rotation order [90, 270, 0, 180] validated | Corpus benchmark: 90° (47.2%), 0° (46.4%), 270° (5.6%), 180° (0.8%) — current order optimal | ✓ Good — data-validated, no change needed. Phase 12 |
| Memory-safe pdf2image (output_folder + paths_only) | Prevents OOM on multi-page PDFs | ✓ Good — critical for large corpus processing |
| PyMuPDF replaces pdf2image/Poppler | 2-12x faster rendering, in-memory pixmaps, no Poppler binary dependency | ✓ Good — Phase 10, simpler code (-37 lines) |
| DPI 200 (down from 300) | Benchmarked 43% faster, found more IDs (211 vs 186 on 100-PDF sample) | ✓ Good — Phase 10 benchmark validated |
| 16 workers hard-coded default | Benchmarked optimal for 20-core hybrid CPU (8P+12E); 16-20 nearly identical | ✓ Good — Phase 10, --workers override preserved |
| Subcommand CLI architecture (argparse subparsers) | Enables lookup/investigate/clean-multi-ids as separate commands; scan wraps main() unchanged | ✓ Good — Phase 13, clean extension points for Phases 14-16 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-10 — Phase 15 (Error Investigation & Reporting) complete*
