# Milestones

## v1.1 Campaign Runner (Shipped: 2026-06-07)

**Phases completed:** 4 phases, 9 plans, 13 tasks

**Key accomplishments:**

- CampaignState dataclass with atomic save/load, silent v1.0 checkpoint upgrade, and folder path normalization using Path.resolve()
- Campaign state fully wired into main() and process_all_pdfs() with folder_path injection in all result dicts
- CSV and JSON output now include folder_path from result dicts, enabling downstream Phase 9 statistics and closing STATE-02 gap
- multiprocessing.Event-based cooperative shutdown with signal handler, worker SIGINT protection, tqdm cleanup, and campaign state interruption tracking
- All 5 graceful shutdown tests passed on Windows 10 with real Ctrl+C signals against 32K PDF corpus
- Stdlib input()-based campaign menu with 6 options, validation loop, view-stats/export-partial/quit handlers, and dictionary-dispatch menu loop
- Continue/rerun-failures/fresh-start handlers wired into main() with full action routing, error identification by page==0+error: prefix, and auto-write outputs after re-run
- One-liner:
- One-liner:

---

## v1.0 PDF ID Scanner & Mapper (Shipped: 2026-06-05)

**Phases completed:** 5 phases, 10 plans, 10 tasks

**Key accomplishments:**

- End-to-end OCR pipeline (precede_ocr.py) extracting 5-digit IDs from multi-page PDFs with 94.9% baseline accuracy
- Multi-rotation OCR strategy (90/270/0/180) with debug diagnostics and failure classification
- Parallel processing via multiprocessing.Pool for 30K+ PDFs with tqdm progress, process recycling, and multi-ID support
- Crash-safe checkpoint/resume with atomic writes, retry logic, error logging, and batch statistics
- Conditional preprocessing fallback (OpenCV) and Theil-Sen robust sequence validation for quality assurance
- 141 tests with comprehensive coverage across all pipeline functions

---
