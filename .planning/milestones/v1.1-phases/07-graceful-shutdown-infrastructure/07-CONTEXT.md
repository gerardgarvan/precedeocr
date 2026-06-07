# Phase 7: Graceful Shutdown Infrastructure - Context

**Gathered:** 2026-06-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Ctrl+C handling with worker protection and checkpoint preservation. User can press Ctrl+C to gracefully stop processing, with workers finishing their current file, state saved cleanly, tqdm closed without terminal corruption, and campaign state marked "interrupted" with timestamp.

This phase does NOT modify core OCR logic, add new CLI flags, or change output formats. It wraps the existing `process_all_pdfs()` pool lifecycle with shutdown awareness.

</domain>

<decisions>
## Implementation Decisions

### Signal & Event Architecture
- **D-01:** Use `multiprocessing.Event` as the cross-platform shutdown signal (locked from roadmap planning). Signals don't propagate reliably to child processes on Windows; Event is IPC-safe.
- **D-02:** Workers check the shutdown Event at file-level granularity only. A worker always completes the entire current PDF before exiting. No page-level interruption within a file. This keeps results clean (no partial-file entries in checkpoint) and aligns with SHUT-01 requirement text.

### Double Ctrl+C (Force-Quit)
- **D-03:** Second Ctrl+C force-terminates immediately. This follows standard CLI convention — users expect it.
- **D-04:** On force-quit, print a brief warning: something like "Force-quit! In-flight files may not be saved. Checkpoint has all completed files." Sets user expectations for the next resume.

### Pool Drain Behavior
- **D-05:** On first Ctrl+C, stop submitting new work to `imap_unordered` immediately (break out of the main iteration loop). Workers already in-flight finish their current file, but no new files get dispatched. This is the fastest clean shutdown path.

### Shutdown Feedback
- **D-06:** Immediately after first Ctrl+C, print a brief status line: `"\nCtrl+C received. Finishing N in-flight files... (press Ctrl+C again to force-quit)"` — tells user what's happening and how to bail.
- **D-07:** After graceful shutdown completes (workers drained, state saved), print a brief summary: something like `"Interrupted: 1,234/30,429 files processed (456 IDs found). State saved. Resume with same command."` — tells them where they stand without the full batch stats block.

### Claude's Discretion
- tqdm cleanup mechanics (how to close the progress bar without ANSI corruption — technical detail)
- Signal handler installation location (in `main()` vs `process_all_pdfs()` — architecture decision)
- Worker SIGINT protection approach (signal.signal in worker init vs pool initializer — platform detail)
- Pool termination sequence (terminate vs close+join ordering — deadlock prevention detail)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — SHUT-01 through SHUT-05 define the five acceptance criteria for this phase

### Architecture Context
- `.planning/ROADMAP.md` §Phase 7 — Phase goal, dependencies (Phase 6), success criteria
- `.planning/STATE.md` §Key Decisions — "Event-based shutdown, not signal-only" rationale
- `.planning/PROJECT.md` §Constraints — Windows 10 platform constraint, no manual intervention

### Existing Code
- `precede_ocr.py` lines 1012-1119 — `process_all_pdfs()` function with Pool lifecycle, imap_unordered loop, tqdm, checkpoint saves
- `precede_ocr.py` lines 972-1009 — `process_single_pdf_wrapper()` worker function (top-level for pickling)
- `precede_ocr.py` lines 91-128 — `CampaignState` dataclass with `interruptions` list, `status` field, `save_campaign_state_atomic()`
- `precede_ocr.py` lines 687-711 — `save_checkpoint_atomic()` for crash-safe checkpoint writes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CampaignState.interruptions` list — already exists, ready to append shutdown events with timestamps
- `CampaignState.status` field — already supports `"interrupted"` value
- `save_campaign_state_atomic()` — atomic write function, reusable for shutdown state saves
- `save_checkpoint_atomic()` — atomic checkpoint write, reusable for final pre-exit checkpoint
- `_CHECKPOINT_FREQUENCY` module-level config — checkpoint timing already established

### Established Patterns
- Module-level globals for worker config (`_ERROR_LOG_PATH`, `_INPUT_PATH_ROOT`) — workers read these; same pattern can be used for a shutdown Event
- `mp.Pool(processes=workers, maxtasksperchild=50)` — existing pool creation with task recycling
- Atomic writes via `tempfile + os.replace` — established crash-safe pattern
- `retry_once` decorator on worker — workers already have error resilience

### Integration Points
- `process_all_pdfs()` — main modification target (signal handler, Event check, drain logic)
- `process_single_pdf_wrapper()` — needs to check shutdown Event before starting work (or in pool initializer for SIGINT protection)
- `main()` — signal handler installation, campaign state finalization on interrupt
- `if __name__ == '__main__':` guard — Windows spawn mode requires careful placement

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-graceful-shutdown-infrastructure*
*Context gathered: 2026-06-06*
