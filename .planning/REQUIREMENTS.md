# Requirements: Precede OCR

**Defined:** 2026-06-05
**Core Value:** Reliably extract every Precede ID from every page across 30K+ PDFs so the user can look up which file and page any given ID lives in.

## v1.1 Requirements

Requirements for Campaign Runner milestone. Each maps to roadmap phases.

### Campaign State

- [x] **STATE-01**: Campaign persists state (ID, status, progress, options) to JSON file with atomic writes
- [x] **STATE-02**: Campaign tracks per-folder file paths in result data for downstream statistics
- [x] **STATE-03**: Campaign logs interruption events with timestamps for debugging

### Graceful Shutdown

- [x] **SHUT-01**: User can press Ctrl+C to gracefully stop processing (workers finish current file before exit)
- [x] **SHUT-02**: Workers are protected from SIGINT so they don't crash mid-OCR
- [x] **SHUT-03**: Pool cleanup follows safe sequence to prevent deadlocks and zombie processes
- [x] **SHUT-04**: tqdm progress bar closes cleanly on shutdown (no terminal corruption)
- [x] **SHUT-05**: Campaign state is marked "interrupted" with timestamp on Ctrl+C

### Interactive Menu

- [x] **MENU-01**: User sees interactive menu when resuming a campaign (Continue / Re-run failures / View stats / Export partial / Fresh start / Quit)
- [x] **MENU-02**: User can re-run only previously failed files
- [x] **MENU-03**: User can export partial CSV/JSON results mid-campaign
- [x] **MENU-04**: User can start a fresh campaign that clears all prior state

### Statistics & Reporting

- [x] **STAT-01**: User sees completion progress during processing (files done/total, IDs found, ETA)
- [x] **STAT-02**: User sees success/failure counts and error summary on campaign exit
- [x] **STAT-03**: User can view per-folder quality breakdown (success rate, error count, IDs per directory)
- [x] **STAT-04**: Campaign generates a Markdown report with per-folder stats, problem area highlights, and recommendations
- [x] **STAT-05**: Statistics include preprocessing fallback trigger rates and rotation distribution

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Analytics

- **ANLYT-01**: OCR confidence scores aggregated to page-level
- **ANLYT-02**: Smart ETA with historical data and per-folder rate prediction
- **ANLYT-03**: Anomaly detection flags for outlier folders

### Campaign History

- **HIST-01**: Batch comparison reports across multiple campaign runs

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web dashboard / GUI | CLI-only per project constraints |
| Automatic failure retry | Dangerous without root cause understanding; manual re-run option provided |
| Database-backed state | JSON sufficient per constraints; no database dependencies |
| Parallel campaign execution | Confusing UX; one active campaign at a time |
| Interactive page-by-page review | Violates "no manual intervention" constraint |
| Cloud storage integration | Local-only tool per constraints |
| Adaptive worker scaling | Adds complexity; static worker count sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STATE-01 | Phase 6 | Complete |
| STATE-02 | Phase 6 | Complete |
| STATE-03 | Phase 6 | Complete |
| SHUT-01 | Phase 7 | Complete |
| SHUT-02 | Phase 7 | Complete |
| SHUT-03 | Phase 7 | Complete |
| SHUT-04 | Phase 7 | Complete |
| SHUT-05 | Phase 7 | Complete |
| MENU-01 | Phase 8 | Complete |
| MENU-02 | Phase 8 | Complete |
| MENU-03 | Phase 8 | Complete |
| MENU-04 | Phase 8 | Complete |
| STAT-01 | Phase 9 | Complete |
| STAT-02 | Phase 9 | Complete |
| STAT-03 | Phase 9 | Complete |
| STAT-04 | Phase 9 | Complete |
| STAT-05 | Phase 9 | Complete |

**Coverage:**
- v1.1 requirements: 15 total
- Mapped to phases: 15
- Unmapped: 0

---
*Requirements defined: 2026-06-05*
*Last updated: 2026-06-05 after roadmap creation*
