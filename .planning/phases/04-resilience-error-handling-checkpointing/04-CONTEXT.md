# Phase 4: Resilience — Error Handling & Checkpointing - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Complete 30K batches even with corrupted files or crashes, resuming from last successful checkpoint. Add per-file error handling with retry, structured error logging, checkpoint persistence with resume capability, and batch statistics reporting.

Requirements: QUAL-03 (per-file error handling), RESL-01 (checkpoint resume).

</domain>

<decisions>
## Implementation Decisions

### Checkpoint Format
- **D-01:** JSON file (`.checkpoint.json`) stored in the output directory alongside CSV/JSON results
- **D-02:** Checkpoint stores full results (extracted IDs, page data, rotation info) for completed files — not just filenames
- **D-03:** Checkpoint saved periodically every N files (not after every file) — balances crash safety with I/O overhead
- **D-04:** On resume, previously-checkpointed results merge with newly-processed results for final output

### Resume Behavior
- **D-05:** Auto-detect checkpoint — if `.checkpoint.json` exists in output directory, automatically resume from it on re-run (no explicit flag needed)
- **D-06:** Print resume status at startup: "Resuming: X/Y files already processed"
- **D-07:** `--fresh` CLI flag deletes existing checkpoint and starts from scratch
- **D-08:** Validate input path — checkpoint stores the input path used; on resume, if input path doesn't match, warn the user. New files in directory are processed; removed files are skipped from results

### Error Logging
- **D-09:** Separate error log file (`errors.log`) in output directory with one entry per failed file: filename, error type, message, timestamp
- **D-10:** Keep existing brief error in CSV notes column (e.g., `error: TypeError: ...`) alongside the separate detailed error log
- **D-11:** Retry each failed file once before marking as permanently failed — handles transient issues (file locks, temp disk full)

### Batch Statistics
- **D-12:** Print summary on screen at end of run AND write `batch_stats.json` to output directory
- **D-13:** Standard metrics: total files, successful, failed, total pages, IDs found, no-ID pages, error count, wall-clock duration, files/second rate
- **D-14:** Resume-aware stats: distinguish between previously-checkpointed results and newly-processed results in current session

### Claude's Discretion
- Exact checkpoint save frequency (N value — e.g., every 50 or 100 files)
- Internal checkpoint JSON structure/schema
- Error log format details (plain text vs structured)
- Exact warning message wording for stale checkpoint detection
- How to handle edge case of checkpoint file corruption

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above and in:

### Project Requirements
- `.planning/REQUIREMENTS.md` — QUAL-03 and RESL-01 requirement definitions
- `.planning/ROADMAP.md` — Phase 4 success criteria (SC-1 through SC-4)

### Existing Implementation
- `precede_ocr.py` — Current pipeline; `process_single_pdf_wrapper` (line 452-474) has existing error catch pattern; `process_all_pdfs` (line 477-534) has parallel processing loop where checkpoint logic integrates; `main` (line 537-593) has CLI argparse where `--fresh` flag is added

### Prior Phase Context
- `.planning/STATE.md` — Notes that "Error dict pattern in wrapper provides foundation for Phase 4 error handling"

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `process_single_pdf_wrapper` (line 452-474): Already catches exceptions per file and returns error dict with `notes: 'error: {type}: {msg}'`. Foundation for retry logic.
- `process_all_pdfs` (line 477-534): Parallel processing loop with `pool.imap_unordered`. Running stats dict already tracks `ids`, `no_id_pages`, `errors`. Checkpoint save hooks integrate here.
- `write_results_csv` / `write_results_json`: Output writers that accept flat result lists. Checkpoint merge feeds combined results into these unchanged.
- tqdm progress bar: Already shows running error count in postfix. Resume can adjust `initial` parameter to show correct progress offset.

### Established Patterns
- CLI uses argparse with `--output-csv`, `--output-json`, `--workers`, `--debug` flags. `--fresh` follows same pattern.
- Output directory defaults to `output/`. All new files (checkpoint, error log, stats) go here.
- JSON used for structured output (results.json). Checkpoint and stats follow same format.
- `Path(output_path).parent.mkdir(parents=True, exist_ok=True)` pattern for directory creation.

### Integration Points
- `main()` function: Add checkpoint load/save logic, `--fresh` argument, batch stats writing
- `process_all_pdfs()`: Add checkpoint filtering of already-processed files, periodic checkpoint saves in the `imap_unordered` loop, retry logic in wrapper
- `process_single_pdf_wrapper()`: Add retry-once logic before returning error dict
- argparse block: Add `--fresh` flag

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

*Phase: 04-resilience-error-handling-checkpointing*
*Context gathered: 2026-06-05*
