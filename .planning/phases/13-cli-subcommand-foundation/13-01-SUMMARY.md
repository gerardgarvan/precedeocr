---
phase: 13-cli-subcommand-foundation
plan: 01
subsystem: cli
tags: [argparse, subparsers, cli-refactor, subcommands]

# Dependency graph
requires: []
provides:
  - Subparser CLI architecture with scan, lookup, investigate, clean-multi-ids subcommands
  - cmd_scan() wrapper dispatching to existing main()
  - Stub handlers (cmd_lookup, cmd_investigate, cmd_clean_multi_ids) with argument definitions
affects: [14-id-lookup-generation, 15-error-investigation, 16-multi-id-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns: [argparse-subparser-dispatch, set_defaults-func-pattern, stub-handler-pattern]

key-files:
  created: []
  modified: [precede_ocr.py]

key-decisions:
  - "Clean break: subcommand required, bare invocation no longer works (D-01)"
  - "Stub handlers define full argument interfaces for --help discovery (D-05)"
  - "main() unchanged; cmd_scan() is thin wrapper unpacking Namespace (D-07)"

patterns-established:
  - "Subcommand dispatch: set_defaults(func=cmd_xxx) + args.func(args)"
  - "Stub pattern: print message + sys.exit(1) for unimplemented commands"
  - "Handler naming: cmd_scan(), cmd_lookup(), cmd_investigate(), cmd_clean_multi_ids()"

requirements-completed: [LOOK-03]

# Metrics
duration: 3min
completed: 2026-06-10
---

# Phase 13 Plan 01: CLI Subcommand Foundation Summary

**Argparse subparser architecture with 4 subcommands (scan, lookup, investigate, clean-multi-ids) and set_defaults dispatch**

## Performance

- **Duration:** 3 min
- **Started:** 2026-06-10T19:41:10Z
- **Completed:** 2026-06-10T19:44:04Z
- **Tasks:** 2 (1 implementation + 1 verification)
- **Files modified:** 1

## Accomplishments
- Refactored flat argparse CLI into subparser architecture with 4 subcommands
- cmd_scan() wrapper delegates to unchanged main() with keyword argument unpacking
- Three stub handlers (lookup, investigate, clean-multi-ids) print "not yet implemented" and exit 1
- All stub subcommands define their expected arguments for --help discovery
- No-args invocation shows help text and exits 0
- All 236 existing tests pass without modification
- Zero new dependencies added (argparse and sys already in stdlib)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add handler functions and replace flat argparse with subparser architecture** - `29ad354` (feat)
2. **Task 2: Verify CLI subcommand behavior end-to-end** - verification-only, no code changes

## Files Created/Modified
- `precede_ocr.py` - Added cmd_scan(), cmd_lookup(), cmd_investigate(), cmd_clean_multi_ids() handlers; replaced flat argparse with subparser dispatch architecture (+118 lines, -14 lines)

## Decisions Made
- Clean break from v1.2 CLI: `python precede_ocr.py scan <dir>` replaces `python precede_ocr.py <dir>` (D-01)
- No-args shows help via sys.argv length check before parse_args, exits 0 (D-02)
- All flags are scan-specific, no global/shared flags (D-03)
- Stub message format: "{name} command not yet implemented. Coming in a future update." with sys.exit(1) (D-04)
- Stub subcommands define full argument interfaces for --help discovery (D-05)
- main() signature and body completely unchanged; cmd_scan() is thin wrapper (D-07)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

| File | Location | Stub | Reason | Resolved By |
|------|----------|------|--------|-------------|
| precede_ocr.py | line 2158 | cmd_lookup() prints "not yet implemented" | Intentional stub | Phase 14 |
| precede_ocr.py | line 2164 | cmd_investigate() prints "not yet implemented" | Intentional stub | Phase 15 |
| precede_ocr.py | line 2170 | cmd_clean_multi_ids() prints "not yet implemented" | Intentional stub | Phase 16 |

All stubs are intentional per the plan. They establish the CLI interface early and will be implemented in subsequent phases.

## Next Phase Readiness
- CLI foundation complete with all 4 subcommands registered
- Phase 14 can implement cmd_lookup() handler replacing the stub
- Phase 15 can implement cmd_investigate() handler replacing the stub
- Phase 16 can implement cmd_clean_multi_ids() handler replacing the stub
- All three phases are independent of each other (only depend on Phase 13)

## Self-Check: PASSED

- FOUND: precede_ocr.py
- FOUND: .planning/phases/13-cli-subcommand-foundation/13-01-SUMMARY.md
- FOUND: commit 29ad354

---
*Phase: 13-cli-subcommand-foundation*
*Completed: 2026-06-10*
