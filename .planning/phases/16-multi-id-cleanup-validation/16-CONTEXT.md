# Phase 16: Multi-ID Cleanup & Validation - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement the `clean-multi-ids` subcommand that analyzes 5,141 multi-ID pages to distinguish real multi-ID pages from OCR noise, then produces a cleaned dataset with noise removed. Conservative approach: bias toward preservation, raw data never modified.

Requirements in scope: MULTI-01, MULTI-02, MULTI-03

</domain>

<decisions>
## Implementation Decisions

### Noise Detection
- **D-01:** CSV heuristics only — do NOT re-render pages or re-OCR. Work entirely from the scan results CSV data. Fast and sufficient for noise detection.
- **D-02:** Same-page dedup + pattern heuristics. Primary noise sources to detect:
  1. Exact duplicate IDs on the same page (same filename + page + ID appearing more than once)
  2. Repeated-digit IDs (e.g., "11111", "00000", "99999") — common OCR artifacts from lines/borders
  3. Existing `seq_outlier_conf_N%` flags from `validate_sequential_ids()` in the notes field
- **D-03:** No cross-page frequency analysis. Keep scope to same-page dedup and per-ID pattern detection.

### Sample Validation
- **D-04:** Interactive terminal prompt for sample validation. Run analysis on 200-ID sample, display summary table (IDs flagged, reasons, confidence), then prompt "Apply to full dataset? [y/N]". User reviews inline and approves before full run proceeds.
- **D-05:** `--sample-size` argument already defined in stub (default 200). Honor this for the sample subset.

### Output Format
- **D-06:** Three output files:
  1. `results_cleaned.csv` — original CSV with noise rows removed (default: `output/results_cleaned.csv` per `--output` arg)
  2. `removed_ids.csv` — rows that were removed, with added columns for removal reason and confidence
  3. `cleanup_report.md` — markdown report documenting heuristics applied, counts per category, and confidence metrics
- **D-07:** Raw data always preserved — original `results.csv` (input) is never modified. Consistent with Phase 15 D-03.

### Claude's Discretion
- Confidence thresholds for each heuristic (what percentage triggers flagging)
- Ordering of heuristic application (which checks run first)
- Cleanup report structure and detail level
- Whether to include a `--dry-run` flag for preview without writing files
- How to handle edge cases (e.g., a page with exactly 2 IDs where one is a repeated-digit pattern)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — MULTI-01, MULTI-02, MULTI-03 definitions and acceptance criteria
- `.planning/ROADMAP.md` — Phase 16 success criteria (SC-1 through SC-5)

### Existing Code
- `precede_ocr.py:2496-2499` — `cmd_clean_multi_ids` stub to replace
- `precede_ocr.py:2569-2586` — clean-multi-ids subparser argument definitions (scan_csv, --output, --sample-size)
- `precede_ocr.py:1180-1300` — `validate_sequential_ids()` with Theil-Sen regression + modified Z-score outlier detection (produces `seq_outlier_conf_N%` notes)
- `precede_ocr.py:574-608` — CSV flattening logic (one row per ID, multi-ID pages = multiple rows with same filename+page)
- `precede_ocr.py:2159-2225` — `cmd_lookup()` as pattern for subcommand implementation
- `precede_ocr.py:2432-2493` — `cmd_investigate()` as pattern for subcommand with multiple output files

### Data Format
- CSV columns: `filename, folder_path, page, id, rotation_detected, notes`
- Multi-ID pages: same filename + same page, multiple rows with different IDs
- Existing noise flag: `seq_outlier_conf_N%` in notes field (from scan pipeline)
- Production stats: 5,141 pages with 2+ IDs (11.2% of 46,124 pages)

### Prior Phase Context
- `.planning/phases/13-cli-subcommand-foundation/13-CONTEXT.md` — CLI architecture decisions
- `.planning/phases/15-error-investigation-reporting/15-CONTEXT.md` — Report-only pattern, CSV output conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `validate_sequential_ids()` at line ~1180 — Already does statistical outlier detection with Theil-Sen regression. Flags IDs with `seq_outlier_conf_N%` in notes. clean-multi-ids can consume these flags directly from the CSV.
- `cmd_lookup()` / `cmd_investigate()` — Established patterns for CSV-reading subcommands with pandas, validation, and multi-file output.
- CSV output pattern: `utf-8-sig` encoding + `csv.QUOTE_NONNUMERIC` for Excel compatibility.

### Established Patterns
- Subcommand handlers: `cmd_*(args)` functions with argparse Namespace
- Input validation: check file exists, read CSV, validate required columns, sys.exit(1) on error
- Output directory: `output/` folder, `mkdir(parents=True, exist_ok=True)`
- Report generation: markdown format with sections, tables, and summary statistics

### Integration Points
- `cmd_clean_multi_ids(args)` stub already wired to argparse subparser at line 2586
- Subparser already defines `scan_csv`, `--output`, `--sample-size` arguments
- Output goes alongside other output files in `output/` directory

</code_context>

<specifics>
## Specific Ideas

- The 200-ID sample validation uses an interactive `input()` prompt in the terminal (same pattern as the campaign resume menu in `main()`)
- Repeated-digit detection: regex pattern like `r'^(\d)\1{4}$'` matches 5 identical digits
- Same-page duplicate detection: group by (filename, page), find duplicate IDs within each group
- The cleanup report should show before/after counts so the user can assess impact

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 16-multi-id-cleanup-validation*
*Context gathered: 2026-06-10*
