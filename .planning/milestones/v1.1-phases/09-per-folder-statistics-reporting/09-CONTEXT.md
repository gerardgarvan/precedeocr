# Phase 9: Per-Folder Statistics & Reporting - Context

**Gathered:** 2026-06-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver per-folder quality breakdown and comprehensive statistics for OCR campaigns. This includes real-time progress enhancement (ETA), enriched exit summaries, per-folder quality metrics, a Markdown report with problem area highlighting and pattern-based recommendations, and rotation/preprocessing distribution tracking. All statistics code aggregates locally in the main process — no Manager IPC.

</domain>

<decisions>
## Implementation Decisions

### Report Content
- **D-01:** Full comprehensive report — executive summary + per-folder stats table + problem area highlights + rotation/preprocessing breakdown + recommendations. One-stop reference for the entire campaign run.
- **D-02:** Per-folder aggregates only — no per-file error listing in the report. Individual file errors are already in CSV output; report stays concise.
- **D-03:** Report file (`campaign_report.md`) written to the same output directory as CSV/JSON (alongside `precede_results.csv` and `precede_results.json`).
- **D-04:** Report auto-generates on every campaign completion. No CLI flag needed, no opt-out.

### Problem Detection
- **D-05:** Problem threshold: folders with success rate below 80% are flagged as problem areas.
- **D-06:** Pattern-based recommendations — analyze error patterns per problem folder and suggest actions (high preprocessing fallback -> "low scan quality, consider rescanning"; rotation failures -> "unusual page orientation"; file-level errors -> "corrupted PDFs, verify source files").
- **D-07:** Problem folders highlighted with bold + warning emoji prefix in the Markdown table row. Easy to spot when scanning.

### Console vs. Report
- **D-08:** Use tqdm's built-in ETA for progress display (STAT-01). It's already configured with `total=` — just ensure ETA display is active. Zero extra code needed.
- **D-09:** Enhanced menu "View stats" (option 3) shows condensed per-folder table in console (top 10 worst folders + totals). Full detail in the Markdown report.
- **D-10:** Exit summary (print_batch_stats) enhanced with error type breakdown (e.g., "corrupted PDF: 12, timeout: 3, no pages: 5") plus a pointer to `campaign_report.md` for full details.

### Stats Granularity
- **D-11:** Rotation distribution (90/270/0/180) and preprocessing fallback rates shown both as campaign-wide aggregates in the summary section AND per-folder in the detailed table.
- **D-12:** Per-folder table sorted by success rate ascending — worst folders first (most actionable ordering).
- **D-13:** Per-folder table includes "Avg IDs/Page" column to help gauge extraction density and spot folders with consistently zero or multiple IDs.

### Claude's Discretion
- Table column order and width in Markdown report
- Exact wording of pattern-based recommendations
- Number of folders shown in condensed console view (guideline: ~10 worst)
- Whether to include a "top performing folders" section in the report (optional positive signal)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — STAT-01 through STAT-05 define all statistics requirements for this phase

### Architecture & Decisions
- `.planning/PROJECT.md` — Key Decisions table documents "Local stats aggregation, not Manager" pattern
- `.planning/ROADMAP.md` — Phase 9 success criteria and dependency on Phase 6 folder_path tracking

### Existing Code
- `precede_ocr.py` lines 126-147 — `CampaignState` dataclass with `folder_stats: dict` field (pre-allocated but empty)
- `precede_ocr.py` lines 777-832 — `calculate_batch_stats()` and `print_batch_stats()` existing stat functions
- `precede_ocr.py` lines 1090-1163 — `process_all_pdfs()` tqdm progress bar and running stats tracking
- `precede_ocr.py` lines 1273-1298 — `handle_view_stats()` current menu stats display
- `precede_ocr.py` lines 228-241 — `compute_folder_path()` folder path normalization

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CampaignState.folder_stats: dict` — pre-allocated field ready to be populated with per-folder data
- `calculate_batch_stats()` — returns structured dict with summary, performance, resume_context; can be extended for per-folder breakdown
- `print_batch_stats()` — console output pattern to follow for enhanced exit summary
- `handle_view_stats()` — menu handler to extend with condensed per-folder display
- `compute_folder_path()` — already normalizes paths relative to input root (Phase 6)
- `folder_path` field present in all result dicts (both success and error results)
- `rotation_detected` field present in result dicts for rotation distribution stats
- Result `notes` field contains preprocessing fallback info and error types

### Established Patterns
- Atomic JSON writes via `save_campaign_state_atomic()` (tempfile + os.replace)
- Worker results aggregated in main process loop (lines 1112-1159)
- Running stats dict tracked during processing: `stats['ids']`, `stats['no_id_pages']`, `stats['errors']`
- tqdm postfix for real-time stats: `pbar.set_postfix({...})`
- Menu handler functions return string signals ('menu', 'continue', 'quit')

### Integration Points
- `process_all_pdfs()` — where per-folder stats accumulation would happen (main process loop)
- `calculate_batch_stats()` — extend to include per-folder breakdown
- `print_batch_stats()` — extend with error type breakdown and report pointer
- `handle_view_stats()` — extend with condensed per-folder table
- Campaign completion flow in `main()` — where report generation would be triggered
- `write_results_csv()` / `write_results_json()` — pattern for file output alongside report

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-per-folder-statistics-reporting*
*Context gathered: 2026-06-07*
