# Requirements: Precede OCR

**Defined:** 2026-06-05
**Core Value:** Reliably extract every Precede ID from every page across 30K+ PDFs so the user can look up which file and page any given ID lives in.

## v1.1 Requirements

Requirements for Campaign Runner milestone. Each maps to roadmap phases.

### Campaign State

- [ ] **STATE-01**: Campaign persists state (ID, status, progress, options) to JSON file with atomic writes
- [ ] **STATE-02**: Campaign tracks per-folder file paths in result data for downstream statistics
- [ ] **STATE-03**: Campaign logs interruption events with timestamps for debugging

### Graceful Shutdown

- [ ] **SHUT-01**: User can press Ctrl+C to gracefully stop processing (workers finish current file before exit)
- [ ] **SHUT-02**: Workers are protected from SIGINT so they don't crash mid-OCR
- [ ] **SHUT-03**: Pool cleanup follows safe sequence to prevent deadlocks and zombie processes
- [ ] **SHUT-04**: tqdm progress bar closes cleanly on shutdown (no terminal corruption)
- [ ] **SHUT-05**: Campaign state is marked "interrupted" with timestamp on Ctrl+C

### Interactive Menu

- [ ] **MENU-01**: User sees interactive menu when resuming a campaign (Continue / Re-run failures / View stats / Export partial / Fresh start / Quit)
- [ ] **MENU-02**: User can re-run only previously failed files
- [ ] **MENU-03**: User can export partial CSV/JSON results mid-campaign
- [ ] **MENU-04**: User can start a fresh campaign that clears all prior state

### Statistics & Reporting

- [ ] **STAT-01**: User sees completion progress during processing (files done/total, IDs found, ETA)
- [ ] **STAT-02**: User sees success/failure counts and error summary on campaign exit
- [ ] **STAT-03**: User can view per-folder quality breakdown (success rate, error count, IDs per directory)
- [ ] **STAT-04**: Campaign generates a Markdown report with per-folder stats, problem area highlights, and recommendations
- [ ] **STAT-05**: Statistics include preprocessing fallback trigger rates and rotation distribution

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
| STATE-01 | — | Pending |
| STATE-02 | — | Pending |
| STATE-03 | — | Pending |
| SHUT-01 | — | Pending |
| SHUT-02 | — | Pending |
| SHUT-03 | — | Pending |
| SHUT-04 | — | Pending |
| SHUT-05 | — | Pending |
| MENU-01 | — | Pending |
| MENU-02 | — | Pending |
| MENU-03 | — | Pending |
| MENU-04 | — | Pending |
| STAT-01 | — | Pending |
| STAT-02 | — | Pending |
| STAT-03 | — | Pending |
| STAT-04 | — | Pending |
| STAT-05 | — | Pending |

**Coverage:**
- v1.1 requirements: 15 total
- Mapped to phases: 0
- Unmapped: 15

---
*Requirements defined: 2026-06-05*
*Last updated: 2026-06-05 after initial definition*
