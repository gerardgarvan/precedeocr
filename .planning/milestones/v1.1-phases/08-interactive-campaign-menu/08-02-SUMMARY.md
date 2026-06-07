---
phase: 08-interactive-campaign-menu
plan: 02
subsystem: cli
tags: [menu, pipeline-integration, rerun-failures, fresh-start, campaign-state]

# Dependency graph
requires:
  - phase: 08-interactive-campaign-menu
    plan: 01
    provides: show_campaign_menu, handle_view_stats, handle_export_partial, handle_quit, run_menu_loop
  - phase: 06-enhanced-campaign-state-schema
    provides: CampaignState dataclass, campaign_state.json, atomic writes
  - phase: 07-graceful-shutdown-infrastructure
    provides: Graceful Ctrl+C shutdown, interruption tracking
provides:
  - handle_continue function for resume processing
  - get_failed_filenames helper for identifying file-level errors
  - handle_rerun_failures with error removal, reprocessing, auto-write outputs
  - handle_fresh_start deleting checkpoint, campaign state, and error log
  - Full menu integration in main() with quit/rerun/fresh/continue action routing
  - TestMenuIntegration class with 15 integration tests
affects: [09-comprehensive-statistics, main-pipeline, campaign-menu]

# Tech tracking
tech-stack:
  added: []
  patterns: [handler-returns-action-string, menu-guard-with-checkpoint-exists, menu-handled-flag-for-dual-path]

key-files:
  created: []
  modified:
    - precede_ocr.py
    - tests/test_precede_ocr.py

key-decisions:
  - "Replaced direct_actions dict with unified handler dispatch in run_menu_loop (all 6 choices via handlers dict)"
  - "Used menu_handled flag to prevent double checkpoint loading (menu path vs non-menu path)"
  - "handle_rerun_failures returns 'rerun' and main() exits after rerun (handler owns full lifecycle)"

patterns-established:
  - "Menu integration guard: not fresh and checkpoint_path.exists() gates menu display"
  - "Action routing in main(): quit=return, rerun=return, fresh=rediscover+fallthrough, continue=filter+fallthrough"
  - "Error identification: page==0 + notes.startswith('error:') = file-level failure (D-05)"

requirements-completed: [MENU-01, MENU-02, MENU-04]

# Metrics
duration: 5min
completed: 2026-06-07
---

# Phase 08 Plan 02: Pipeline-Integrated Menu Handlers Summary

**Continue/rerun-failures/fresh-start handlers wired into main() with full action routing, error identification by page==0+error: prefix, and auto-write outputs after re-run**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-07T15:20:04Z
- **Completed:** 2026-06-07T15:26:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- 4 new functions in precede_ocr.py: handle_continue, get_failed_filenames, handle_rerun_failures, handle_fresh_start
- Full menu integration in main() with conditional display (checkpoint exists AND not fresh)
- Re-run failures handler removes old error entries (D-06), processes only failed files, auto-writes CSV/JSON (D-07)
- Fresh start handler deletes checkpoint, campaign state, and error log files
- run_menu_loop updated with unified handler dispatch (all 6 options)
- 15 integration tests in TestMenuIntegration class, all passing
- Full test suite: 203 tests passing, zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Write TestMenuIntegration tests (RED phase)** - `3205506` (test)
2. **Task 2: Implement handlers and wire menu into main() (GREEN phase)** - `69c9179` (feat)

_Note: TDD tasks -- RED tests written first (Task 1), GREEN implementation verified (Task 2)._

## Files Created/Modified
- `precede_ocr.py` - Added handle_continue, get_failed_filenames, handle_rerun_failures, handle_fresh_start; updated run_menu_loop signature and dispatch; wired menu into main() with action routing
- `tests/test_precede_ocr.py` - Added TestMenuIntegration class with 15 tests; updated test_main_resumes_from_checkpoint to mock menu

## Decisions Made
- Replaced direct_actions + handlers split with unified handlers dict in run_menu_loop (cleaner, all choices go through same dispatch)
- Used menu_handled flag in main() to prevent double checkpoint loading between menu path and legacy path
- handle_rerun_failures owns full lifecycle: identify failures, clean checkpoint, process, validate, write outputs, finalize state

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_main_resumes_from_checkpoint regression**
- **Found during:** Task 2 (main() wiring)
- **Issue:** Existing test called main() with checkpoint but no menu mock, causing stdin read error
- **Fix:** Added `patch('precede_ocr.run_menu_loop', return_value='continue')` to the existing test
- **Files modified:** tests/test_precede_ocr.py
- **Verification:** Full test suite passes (203 tests)
- **Committed in:** 69c9179 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed test_main_fresh_rediscovers_pdfs mock interference**
- **Found during:** Task 2 (test verification)
- **Issue:** Test patched builtins.open globally, breaking load_checkpoint_if_exists JSON reading; also single-PDF mock hit single-file path instead of parallel path
- **Fix:** Added load_checkpoint_if_exists mock; changed to 2 dummy PDFs to hit parallel processing path
- **Files modified:** tests/test_precede_ocr.py
- **Verification:** All 15 TestMenuIntegration tests pass
- **Committed in:** 69c9179 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs from test/implementation interaction)
**Impact on plan:** Both auto-fixes necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed test adjustments above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Complete interactive campaign menu system functional end-to-end (all 6 options)
- Phase 8 fully complete: Plan 01 (menu infrastructure) + Plan 02 (pipeline handlers + main wiring)
- Ready for Phase 9 (comprehensive statistics) -- menu provides user-facing stats entry point

## Self-Check: PASSED

- FOUND: precede_ocr.py
- FOUND: tests/test_precede_ocr.py
- FOUND: 08-02-SUMMARY.md
- FOUND: commit 3205506
- FOUND: commit 69c9179

---
*Phase: 08-interactive-campaign-menu*
*Completed: 2026-06-07*
