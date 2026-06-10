# Phase 14: ID Lookup Generation - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate a sorted, Excel-friendly ID lookup CSV from scan results. Users run `python precede_ocr.py lookup results.csv` and get a clean CSV with columns: ID, Filename, Page, Folder — sorted numerically by ID, formatted for Excel (UTF-8 BOM, IDs as text not dates). This replaces the `cmd_lookup` stub from Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Data Filtering
- **D-01:** Exclude rows with blank IDs (no-match pages) from the lookup CSV. The lookup is purely for finding which file/page an ID lives in. No-match analysis belongs in Phase 15.
- **D-02:** Exclude error rows (page=0, notes starting with "error:") from the lookup CSV. Error investigation belongs in Phase 15.
- **D-03:** Keep all duplicate IDs — if the same ID appears in multiple files or pages, every occurrence is a valid lookup result. Deduplication is Phase 16's responsibility.

### Folder Extraction
- **D-04:** Use `folder_path` column from scan CSV if present. If the column is missing (older CSV format without folder_path), extract the parent directory path from the `filename` field. If filename has no path component, Folder is blank.

### Completion Summary
- **D-05:** Print summary stats on completion: total entries, unique IDs, files covered, and output path. Example: `Wrote 52,055 entries (48,901 unique IDs) from 30,316 files to output/lookup.csv`

### Claude's Discretion
- Excel compatibility implementation details (BOM byte, quoting strategy)
- Exact error messages for invalid/missing input CSV
- Whether to use pandas or csv module for output
- Progress indication for large files (if needed)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### CLI Architecture
- `.planning/phases/14-id-lookup-generation/` — Phase directory with this context file
- `.planning/REQUIREMENTS.md` — LOOK-01 (columns/sorting), LOOK-02 (Excel compatibility)
- `.planning/ROADMAP.md` — Phase 14 success criteria (5 items)

### Existing Implementation
- `precede_ocr.py` lines 2158-2161 — `cmd_lookup` stub to replace
- `precede_ocr.py` lines 2213-2226 — Lookup subparser argument definitions (scan_csv positional, --output flag)
- `precede_ocr.py` lines 560-618 — `write_results_csv` for reference on scan CSV format
- `precede_ocr.py` lines 193-206 — `compute_folder_path` for folder derivation logic

No external specs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cmd_lookup(args)` stub at line 2158 — replace body with real implementation
- Lookup subparser already defines `scan_csv` (positional) and `--output` (default: `output/lookup.csv`) arguments
- `pandas` already imported and used throughout the codebase for CSV operations
- `compute_folder_path()` at line 193 — folder derivation logic (for reference, though lookup reads from CSV not from file paths)
- `write_results_csv()` at line 560 — reference for scan CSV column order: `filename, folder_path, page, id, rotation_detected, notes`

### Established Patterns
- CSV output uses `pd.DataFrame.to_csv()` with `index=False`
- Output directories created with `Path(output_path).parent.mkdir(parents=True, exist_ok=True)`
- Handler functions follow `cmd_xxx(args)` signature, receive argparse Namespace
- Print summary stats to stdout after file operations

### Integration Points
- `cmd_lookup` is already wired to `lookup_parser.set_defaults(func=cmd_lookup)` at line 2226
- No changes needed to CLI dispatcher — just replace the stub body
- Input: scan results CSV (e.g., `output/results.csv` or `results.csv`)
- Output: lookup CSV (default `output/lookup.csv`)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The phase is a straightforward data transformation: read scan CSV, filter to ID rows, select/rename columns, sort by ID, write Excel-compatible CSV.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-id-lookup-generation*
*Context gathered: 2026-06-10*
