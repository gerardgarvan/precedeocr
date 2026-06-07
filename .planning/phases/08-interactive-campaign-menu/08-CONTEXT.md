# Phase 8: Interactive Campaign Menu - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Interactive menu displayed on pipeline startup when a prior campaign checkpoint exists. Offers actions: continue processing, re-run failures, view stats, export partial results, start fresh, or quit. Uses stdlib `input()` only (no external dependencies). Menu is shown only when workers are idle (before processing begins).

</domain>

<decisions>
## Implementation Decisions

### Menu Display
- **D-01:** Minimal status info before menu options: campaign ID, status (interrupted/completed), files done/total, failed count
- **D-02:** Numbered list format: `[1] Continue  [2] Re-run failures  [3] View stats  [4] Export partial  [5] Fresh start  [6] Quit`
- **D-03:** Input validation with re-prompt loop: show "Invalid choice. Enter 1-6:" on bad input, loop until valid
- **D-04:** "View stats" prints summary (files done/total, failed count, IDs found so far) then returns to menu — does not exit

### Re-run Failures
- **D-05:** "Failed" means files with notes starting with `'error:'` — actual processing exceptions. Not no-ID pages.
- **D-06:** Replace old error entries in checkpoint before reprocessing — remove error results for those files, process them fresh, new results replace old errors
- **D-07:** After re-run completes, automatically write final output (CSV/JSON) with merged results — same as normal completion flow

### Menu Trigger Logic
- **D-08:** Menu appears when `.checkpoint.json` exists for the current input path. No checkpoint = no menu, go straight to processing
- **D-09:** `--fresh` flag skips menu entirely — deletes checkpoint/state first, then processes. Consistent with current behavior
- **D-10:** When checkpoint shows 100% complete, still show menu but with "Continue" unavailable/grayed (e.g., "All files processed"). User can still re-run failures, view stats, export, or start fresh

### Export Partial
- **D-11:** Partial exports write to the same output paths (--output-csv, --output-json locations). Final run overwrites with complete data
- **D-12:** After exporting, print confirmation message ("Exported N results to output/results.csv") and return to menu
- **D-13:** Partial export skips sequence validation — partial data has gaps that trigger false warnings. Validation is a final-output step only

### Claude's Discretion
- Exact wording of menu header and status lines
- How "Continue unavailable" is displayed when 100% complete (omit option, show with note, etc.)
- Whether to show "N failed files" count next to "Re-run failures" option for quick visibility
- Stats detail level in "View stats" (beyond files done/total/failed/IDs found)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements fully captured in decisions above and in:

### Project & Requirements
- `.planning/PROJECT.md` — Project constraints, key decisions, current state
- `.planning/REQUIREMENTS.md` — MENU-01 through MENU-04 requirement definitions
- `.planning/ROADMAP.md` — Phase 8 success criteria (5 items)

### Upstream Phase Artifacts
- `.planning/phases/06-enhanced-campaign-state-schema/` — Campaign state schema, atomic writes, folder_path tracking
- `.planning/phases/07-graceful-shutdown-infrastructure/` — Shutdown signal handling, worker protection, campaign interruption tracking

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CampaignState` dataclass (lines 125-147): Already tracks status, files_processed, files_failed, interruptions — provides data for menu display
- `load_or_create_campaign_state()` (lines 165-225): Loads existing campaign state — menu reads this for status info
- `load_checkpoint_if_exists()` (lines 749-769): Returns (results, processed_files) — needed to identify failed files for re-run and to export partial results
- `write_results_csv()` / `write_results_json()` (lines 550-642): Reuse directly for partial export
- `calculate_batch_stats()` (lines 777-832): Reuse for "View stats" action

### Established Patterns
- Atomic writes via tempfile + fsync + os.replace — use same pattern if menu writes any state
- argparse CLI with `--fresh` flag — menu integrates after arg parsing, before processing
- Module-level globals for worker config — menu runs in main process only, no multiprocessing concerns
- tqdm progress bar for processing feedback — menu is pre-processing, no overlap

### Integration Points
- `main()` function (lines 1210-1375): Menu inserts between `load_or_create_campaign_state()` (~line 1265) and checkpoint loading / processing start (~line 1273)
- `process_all_pdfs()` (lines 1052-1207): Called after menu for "Continue" and "Re-run failures" actions
- Error identification: Checkpoint results with `notes.startswith('error:')` identify failed files for re-run

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. User consistently chose recommended (simplest) options across all areas.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 08-interactive-campaign-menu*
*Context gathered: 2026-06-06*
