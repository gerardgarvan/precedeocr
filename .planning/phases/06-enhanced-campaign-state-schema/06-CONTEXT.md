# Phase 6: Enhanced Campaign State Schema - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Campaign persists state (ID, status, progress, folder tracking, interruption log) to `campaign_state.json` with atomic writes and path normalization. This creates a campaign metadata layer that supplements the existing `.checkpoint.json` without replacing it. The checkpoint stores granular per-file results; the campaign state stores orchestration metadata for downstream features (menu, stats, shutdown tracking).

</domain>

<decisions>
## Implementation Decisions

### Campaign Identity
- **D-01:** Campaign ID uses auto-generated timestamp format: `campaign_20260605_143022` (ISO-ish, human-readable, sortable)
- **D-02:** No input directory name in the campaign ID — input path stored as a separate field in state

### State Detail Level
- **D-03:** Campaign state is "practical" level — stores: campaign ID, status (running/interrupted/completed), total/processed/failed counts, start time, last update time, interruption log, input path, CLI options snapshot
- **D-04:** Interruption log entries include timestamp + progress snapshot (files_processed, files_remaining) — not just bare timestamps

### Backward Compatibility
- **D-05:** Silent upgrade from v1.0 checkpoints — if `.checkpoint.json` exists but no `campaign_state.json`, auto-create campaign state from checkpoint metadata (derive campaign ID from checkpoint timestamp, set status to 'interrupted')
- **D-06:** User sees a brief "Upgraded to campaign tracking" message on silent upgrade — no confirmation prompt required

### Folder Tracking
- **D-07:** `folder_path` field added to result dicts in `process_single_pdf_wrapper()` — stores path relative to the input directory (e.g., `subdir1/batch2`)
- **D-08:** Files directly in the input directory (not in a subdirectory) get `folder_path: ''` (empty string) — Phase 9 can display as "(root)" or input dir name
- **D-09:** Path normalization uses `Path.resolve()` before computing relative paths to handle Windows case-insensitivity

### Claude's Discretion
- Campaign state JSON schema field names and nesting structure
- Whether to use dataclasses or plain dicts for internal state representation
- Checkpoint frequency and state update timing (align with existing checkpoint_frequency=50 pattern)
- Error handling for edge cases (missing fields in upgraded state, concurrent access)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Pipeline
- `precede_ocr.py` lines 555-579 — `save_checkpoint_atomic()` implements the atomic write pattern (tempfile + fsync + os.replace) that campaign state must follow
- `precede_ocr.py` lines 582-602 — `load_checkpoint_if_exists()` shows current checkpoint load/validate pattern
- `precede_ocr.py` lines 840-862 — `process_single_pdf_wrapper()` returns result dicts; `folder_path` field must be added here
- `precede_ocr.py` lines 865-955 — `process_all_pdfs()` handles parallel processing + checkpointing; campaign state updates integrate here
- `precede_ocr.py` lines 957-1098 — `main()` entry point; campaign state load/create/upgrade logic goes here

### Research Documents
- `.planning/research/SUMMARY.md` — Full research synthesis with architecture, pitfalls, and stack recommendations
- `.planning/research/ARCHITECTURE.md` — Data flow and component design for campaign management
- `.planning/research/PITFALLS.md` — Critical pitfalls #4 (checkpoint corruption) and #10 (path normalization) directly apply to this phase
- `.planning/research/STACK.md` — Technology choices (tempfile + os.replace, pathlib, json stdlib, dataclasses)

### Requirements
- `.planning/REQUIREMENTS.md` — STATE-01, STATE-02, STATE-03 are the requirements for this phase

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `save_checkpoint_atomic()` — Atomic write pattern (tempfile + fsync + os.replace) can be reused or generalized for campaign state writes
- `load_checkpoint_if_exists()` — Pattern for safe JSON load with corruption handling; campaign state loader follows same structure
- Existing result dict structure (`filename`, `page`, `ids`, `rotation_detected`, `notes`) — `folder_path` added as new field, backward compatible

### Established Patterns
- Atomic file writes: tempfile in same directory + fsync + os.replace (validated in v1.0, used for checkpoint)
- Module-level globals for worker config: `_ERROR_LOG_PATH` pattern used for cross-process state on Windows spawn
- Pool with `if __name__ == '__main__'` guard for Windows multiprocessing
- Path handling via pathlib throughout

### Integration Points
- `process_single_pdf_wrapper()` — Add `folder_path` to returned result dicts (additive, no breaking change)
- `main()` — Add campaign state create/load/upgrade/update calls around existing checkpoint logic
- `save_checkpoint_atomic()` — May generalize into shared atomic write utility, or campaign state gets its own parallel function
- Output directory — `campaign_state.json` lives alongside `.checkpoint.json` in the output directory

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Research documents provide prescriptive architecture patterns that cover implementation details.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-enhanced-campaign-state-schema*
*Context gathered: 2026-06-05*
