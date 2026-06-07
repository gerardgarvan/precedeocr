# Roadmap: Precede OCR v1.1

**Milestone:** v1.1 Campaign Runner
**Created:** 2026-06-05
**Status:** Active

## Overview

This roadmap delivers campaign management for the v1.0 OCR pipeline, adding production-grade UX for long-running batch jobs: interactive menus, graceful shutdown, per-folder quality insights, and comprehensive statistics. Phases 6-9 wrap the existing pipeline without modifying core OCR logic.

## Phases

- [ ] **Phase 6: Enhanced Campaign State Schema** - Campaign persists state with folder tracking and interruption logging
- [ ] **Phase 7: Graceful Shutdown Infrastructure** - Ctrl+C handling with worker protection and checkpoint preservation
- [ ] **Phase 8: Interactive Campaign Menu** - Resume menu with continue/re-run/stats/export options
- [ ] **Phase 9: Per-Folder Statistics & Reporting** - Quality breakdown by directory with Markdown report generation

## Phase Details

### Phase 6: Enhanced Campaign State Schema
**Goal**: Campaign persists state (ID, status, progress, folder tracking, interruption log) with atomic writes and path normalization

**Depends on**: Nothing (first phase in v1.1, builds on v1.0 checkpoint system)

**Requirements**: STATE-01, STATE-02, STATE-03

**Success Criteria** (what must be TRUE):
1. User can see campaign_state.json file created with campaign ID, status, and progress snapshot
2. User can see per-folder file paths tracked in result data for downstream statistics
3. User can see interruption events logged with timestamps in campaign state after Ctrl+C
4. User can resume processing after crash and campaign state accurately reflects pre-crash progress
5. User can verify campaign state updates are atomic (no partial writes on crash)

**Plans:** 3 plans

Plans:
- [x] 06-01-PLAN.md -- CampaignState dataclass, atomic save/load, silent upgrade, folder_path utility + unit tests
- [x] 06-02-PLAN.md -- Wire campaign state into pipeline (main, process_all_pdfs, wrapper) + integration tests
- [x] 06-03-PLAN.md -- Gap closure: propagate folder_path into CSV and JSON output files

---

### Phase 7: Graceful Shutdown Infrastructure
**Goal**: User can press Ctrl+C to gracefully stop processing with workers finishing current files, state saved cleanly, and no terminal corruption

**Depends on**: Phase 6 (requires campaign state to mark interrupted)

**Requirements**: SHUT-01, SHUT-02, SHUT-03, SHUT-04, SHUT-05

**Success Criteria** (what must be TRUE):
1. User can press Ctrl+C during processing and workers finish current PDF before exiting (not mid-OCR crash)
2. User can press Ctrl+C and see checkpoint/campaign state saved with all completed files recorded
3. User can press Ctrl+C and terminal displays clean exit message without ANSI code corruption
4. User can resume after Ctrl+C and campaign state shows "interrupted" status with timestamp
5. User can verify no zombie worker processes remain in Task Manager after Ctrl+C shutdown

**Plans:** 2 plans

Plans:
- [x] 07-01-PLAN.md -- Shutdown tests + implementation (signal handler, worker protection, Event, pool drain, tqdm cleanup, campaign state interruption)
- [x] 07-02-PLAN.md -- Manual verification checkpoint: Ctrl+C testing on Windows 10

---

### Phase 8: Interactive Campaign Menu
**Goal**: User sees interactive menu when resuming a campaign with options to continue, re-run failures, view stats, export partial results, or start fresh

**Depends on**: Phase 6 (requires campaign state for resume detection), Phase 7 (requires graceful shutdown before menu can safely continue processing)

**Requirements**: MENU-01, MENU-02, MENU-03, MENU-04

**Success Criteria** (what must be TRUE):
1. User sees interactive menu on startup if checkpoint exists with clear action choices
2. User can select "Continue" and processing resumes with remaining unprocessed PDFs
3. User can select "Re-run failures" and only previously failed files are reprocessed
4. User can select "Export partial" and CSV/JSON files are generated from current checkpoint mid-campaign
5. User can select "Fresh start" and all prior checkpoint/campaign state is cleared for new run

**Plans:** 2 plans

Plans:
- [x] 08-01-PLAN.md -- Menu display, input validation, handler dispatch, view stats, export partial, quit + unit tests
- [ ] 08-02-PLAN.md -- Re-run failures, fresh start, continue handlers + main() integration + integration tests

---

### Phase 9: Per-Folder Statistics & Reporting
**Goal**: User sees per-folder quality breakdown (success rate, error count, IDs per directory) with Markdown report highlighting problem areas

**Depends on**: Phase 6 (requires folder_path tracking in results)

**Requirements**: STAT-01, STAT-02, STAT-03, STAT-04, STAT-05

**Success Criteria** (what must be TRUE):
1. User sees real-time progress during processing showing files done/total, IDs found, and estimated completion time
2. User sees success/failure counts and error summary displayed on campaign exit
3. User can view per-folder quality breakdown showing success rate and error count for each directory
4. User can open campaign_report.md and see per-folder statistics table with problem area highlights and recommendations
5. User can see preprocessing fallback trigger rates and rotation distribution (90/270/0/180) in campaign report

**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Enhanced Campaign State Schema | 3/3 | Complete | 2026-06-06 |
| 7. Graceful Shutdown Infrastructure | 0/2 | Planned | - |
| 8. Interactive Campaign Menu | 0/2 | Planned | - |
| 9. Per-Folder Statistics & Reporting | 0/0 | Not started | - |

---

## Notes

**Phase numbering**: Continues from v1.0 milestone (ended at Phase 5). v1.1 phases 6-9.

**Architecture principle**: Campaign features wrap existing v1.0 pipeline without modifying core OCR logic. All phases additive, backward compatible.

**Critical testing**: Phase 7 (graceful shutdown) requires extensive manual QA on Windows 10 - Ctrl+C at various points, second Ctrl+C force-quit, zombie process verification in Task Manager.

**Research**: All phases have sufficient documentation in research/SUMMARY.md. No phases require `/gsd:research-phase`.

---
*Last updated: 2026-06-07*
