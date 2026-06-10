# Phase 15: Error Investigation & Reporting - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the `investigate` subcommand that diagnoses root causes of pipeline failures (49 failed files) and no-match pages (59 pages with no ID found), producing a quality report with actionable recommendations. Report-only — no modifications to existing results data.

</domain>

<decisions>
## Implementation Decisions

### Investigation Approach
- **D-01:** Re-render and re-OCR no-match pages for diagnosis. Do not rely on metadata-only analysis — re-open the actual PDFs, render the specific pages, and run OCR to capture what Tesseract sees.
- **D-02:** Use "quick scan" approach: render each no-match page, check if blank (all-white/all-black pixel analysis), then run a single OCR pass to capture raw text. Do NOT run all 8 passes — one pass is sufficient for categorization (blank page vs OCR failure vs missing ID label).

### Fix vs Report Scope
- **D-03:** Report only. The `investigate` command produces diagnostic reports but does NOT apply fixes or modify results.csv. Raw data stays untouched.
- **D-04:** Include copy-paste CLI commands in the report for each fixable category. The user can run these commands to fix issues themselves (e.g., `python precede_ocr.py scan <specific-path> --fresh` for files that now exist).

### Input Data Source
- **D-05:** Read from scan results CSV as a positional argument, consistent with `cmd_lookup` pattern. CLI: `python precede_ocr.py investigate results.csv --report output/quality_report.md`

### Claude's Discretion
- **Failed file re-verification:** Claude decides whether to re-attempt opening failed files (to check if FileNotFoundErrors are still valid or were transient). Recommended: re-verify existence since it's cheap and makes the report much more useful.
- **Page image saving:** Claude decides whether to save rendered no-match page images to disk for manual inspection. Consider cost/benefit — 59 PNGs is manageable but may not be essential if the report text is clear enough.
- **PDF path resolution:** Claude decides how to locate original PDFs for re-rendering. The CSV filename column contains paths. Options: infer from CSV paths directly, or add an optional `--pdf-dir` argument. Pick what works with the existing CSV data format.
- **Output CSV files:** Claude decides which CSV exports to produce beyond the mandatory `no_match_pages.csv` (per SC-4). A `failed_files.csv` is reasonable. Use judgment on what's useful.
- **Report detail level:** Claude decides between summary+tables vs full narrative. Recommend: scannable tables with per-file breakdowns, keeping it concise and actionable rather than forensic-narrative style.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — ERR-01 through ERR-04 definitions and acceptance criteria
- `.planning/ROADMAP.md` — Phase 15 success criteria (SC-1 through SC-5)

### Existing Code
- `precede_ocr.py:2228-2231` — `cmd_investigate` stub to replace
- `precede_ocr.py:2293-2301` — investigate subparser argument definitions (currently just `--report`)
- `precede_ocr.py:860-885` — `categorize_errors()` function for parsing error types from notes field
- `precede_ocr.py:788-825` — `calculate_batch_stats()` for understanding result data structure
- `precede_ocr.py:547-554` — Result dict format: `{filename, page, ids, rotation_detected, notes}`
- `precede_ocr.py:2159-2225` — `cmd_lookup()` as pattern for subcommand implementation (CSV reading, pandas, error handling)

### Data Format
- Result CSV columns: `filename, id, page, rotation_detected, notes`
- Error convention: page=0, notes="error: ExceptionType: message"
- No-match convention: page>0, empty ids, no "error:" in notes
- Error types in production: 46 FileNotFoundError, 3 EmptyFileError

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `categorize_errors(results)` — already parses error types from notes field, returns `{error_type: count}` dict
- `cmd_lookup(args)` — pattern for CSV-reading subcommand (pandas read, filtering, output writing)
- `process_single_pdf(filename)` — can be called for re-rendering individual pages
- `extract_id_with_rotation(img)` — core OCR function, can be called for re-OCR diagnosis
- PyMuPDF page rendering pattern at line ~530 — `doc[page_idx].get_pixmap(dpi=200)`

### Established Patterns
- Subcommand handlers: `cmd_*(args)` functions with argparse Namespace
- CSV processing: pandas with utf-8-sig encoding, QUOTE_NONNUMERIC
- Error logging: `log_error(filename, error, error_log_path)` appends to errors.log
- Atomic file writes: tempfile + os.replace pattern

### Integration Points
- `cmd_investigate(args)` stub already wired to argparse subparser at line 2301
- Investigate subparser needs `scan_csv` positional arg added (currently missing — only has `--report`)
- Output directory convention: `output/` folder

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-error-investigation-reporting*
*Context gathered: 2026-06-10*
