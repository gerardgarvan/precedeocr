# Phase 3: Scale — Parallel Processing - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Process 30K+ PDFs efficiently using parallel workers with progress visibility. Also: capture multiple IDs per page (PIPE-06), flag no-ID pages in output (PIPE-07), add JSON output (OUT-02), and display processing progress (PROG-01).

</domain>

<decisions>
## Implementation Decisions

### Multiple IDs per page
- **D-01:** One row per ID in CSV output. Same page appears in multiple rows when it has multiple IDs. Easy to filter/sort in Excel.
- **D-02:** Keep early exit on first successful rotation. Return ALL valid 5-digit matches from that rotation, not just the first. Assumes all IDs on a page share the same orientation.
- **D-03:** Continue filtering trivial/repeating patterns (00000, 11111, etc.). These are OCR noise, not real Precede IDs.

### JSON output structure
- **D-04:** Nested by filename structure: `{"file.pdf": {"1": ["12345"], "2": ["67890", "11234"], "3": []}}`. Pages with no ID show as empty array. Natural for browsing by file.
- **D-05:** Always generate both CSV and JSON in every run. No flags needed — both are lightweight to produce.

### Worker configuration & memory
- **D-06:** Default worker count = cpu_count() - 1 (leave one core free). User can override with `--workers N` flag.
- **D-07:** Process recycling via maxtasksperchild=50. Workers are recycled after processing 50 PDFs to prevent memory growth from Tesseract leaks over 30K+ files.

### Progress display
- **D-08:** Per-file progress bar using tqdm. Tracks files completed out of total (not per-page). Shows ETA, rate.
- **D-09:** Inline stats in tqdm postfix showing running counts: IDs found, no-ID pages, errors. Gives confidence the pipeline is working throughout the run.

### Claude's Discretion
- Exact tqdm configuration (bar format, refresh interval)
- multiprocessing.Pool vs concurrent.futures.ProcessPoolExecutor choice
- How to aggregate results from workers (queue vs return values)
- Batch size for imap_unordered chunking
- Output file naming when input is a directory (output/results.csv, output/results.json)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above and in:

### Project requirements
- `.planning/REQUIREMENTS.md` — PIPE-06, PIPE-07, OUT-02, PROG-01 requirement definitions
- `.planning/ROADMAP.md` — Phase 3 success criteria and dependency on Phase 2

### Research
- `.planning/ROADMAP.md` Notes section — 5 critical Windows pitfalls, including process recycling for Tesseract memory leaks

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `process_single_pdf()` in `precede_ocr.py:221` — Self-contained worker function. Creates temp dir, processes all pages, cleans up. Natural parallelization unit.
- `write_results_csv()` in `precede_ocr.py:282` — Uses pandas DataFrame. Can extend to add `write_results_json()` alongside.
- `normalize_digits()` and `classify_failure_reason()` — Pure functions, safe for multiprocessing.

### Established Patterns
- Memory-safe pdf2image: `output_folder` + `paths_only=True` — prevents OOM. Must be preserved in parallel workers.
- Context managers for image files (`with Image.open(...)`) — prevents file handle leaks.
- Auto-detect Tesseract/Poppler paths at module level — works with multiprocessing spawn since imports happen per-process.

### Integration Points
- `select_most_likely_id()` at `precede_ocr.py:102` — Currently returns first valid match. Must be changed to return ALL valid matches for PIPE-06.
- `extract_id_with_rotation()` at `precede_ocr.py:163` — Returns `(id, rotation, notes)`. Return type changes to `(list[str], rotation, notes)` for multiple IDs.
- `process_single_pdf()` result schema — Currently `{'id': str}`. Changes to `{'ids': list[str]}` or produces multiple rows per page.
- CLI argparse block at `precede_ocr.py:344` — Currently takes single `pdf_path`. Needs directory input mode and `--workers` flag.
- Notes column already tracks no-match failure reasons — PIPE-07 partially implemented.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-scale-parallel-processing*
*Context gathered: 2026-06-05*
