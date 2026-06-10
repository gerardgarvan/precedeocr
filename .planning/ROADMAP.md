# Roadmap: v1.3 Results Cleanup & ID Lookup

**Milestone:** v1.3 Results Cleanup & ID Lookup
**Created:** 2026-06-09
**Goal:** Produce a clean, Excel-friendly ID lookup file from production results, and investigate/fix pipeline errors and multi-ID noise.

---

## Phases

- [x] **Phase 13: CLI Subcommand Foundation** - Refactor main() to use argparse subparsers for scan/lookup/investigate/clean-multi-ids commands (completed 2026-06-10)
- [ ] **Phase 14: ID Lookup Generation** - Generate sorted ID lookup CSV with Excel-compatible formatting
- [ ] **Phase 15: Error Investigation & Reporting** - Investigate failed files and no-match pages, produce quality report
- [ ] **Phase 16: Multi-ID Cleanup & Validation** - Analyze and clean multi-ID pages with conservative deduplication

---

## Phase Details

### Phase 13: CLI Subcommand Foundation
**Goal**: Establish integrated CLI subcommand architecture to support lookup/investigate/clean operations
**Depends on**: Nothing (first phase)
**Requirements**: LOOK-03
**Success Criteria** (what must be TRUE):
  1. User can run `python precede_ocr.py scan <dir>` and get identical output to v1.2
  2. User can invoke `python precede_ocr.py --help` and see available subcommands (scan, lookup, investigate, clean-multi-ids)
  3. All 236 existing tests pass without modification
  4. Subcommand dispatcher routes to appropriate handler functions
**Plans:** 1/1 plans complete

Plans:
- [x] 13-01-PLAN.md -- Add handler functions and subparser CLI architecture

### Phase 14: ID Lookup Generation
**Goal**: Users can generate a sorted, Excel-friendly ID lookup CSV from scan results
**Depends on**: Phase 13
**Requirements**: LOOK-01, LOOK-02
**Success Criteria** (what must be TRUE):
  1. User can run `python precede_ocr.py lookup results.csv` and get sorted ID lookup CSV
  2. Lookup CSV opens correctly in Excel with no encoding issues, proper column alignment, and IDs displayed as text (not dates)
  3. Lookup CSV contains columns: ID, Filename, Page, Folder
  4. IDs are sorted numerically in ascending order
  5. Folder paths are correctly extracted from filenames
**Plans**: TBD

### Phase 15: Error Investigation & Reporting
**Goal**: Users understand root causes of failed files and no-match pages with actionable recommendations
**Depends on**: Phase 13
**Requirements**: ERR-01, ERR-02, ERR-03, ERR-04
**Success Criteria** (what must be TRUE):
  1. User can run `python precede_ocr.py investigate` and get comprehensive error report
  2. Report categorizes all 49 failed files by error type (FileNotFoundError vs EmptyFileError) with root cause analysis
  3. Report analyzes all 59 no-match pages with categorization (blank page, OCR failure, missing ID label)
  4. Report exports `no_match_pages.csv` with filename, page, category, and actionable recommendations
  5. Pipeline fixes are identified and documented for fixable errors
**Plans**: TBD

### Phase 16: Multi-ID Cleanup & Validation
**Goal**: Users can distinguish real multi-ID pages from OCR noise and generate cleaned dataset
**Depends on**: Phase 13
**Requirements**: MULTI-01, MULTI-02, MULTI-03
**Success Criteria** (what must be TRUE):
  1. User can run `python precede_ocr.py clean-multi-ids results.csv` and get cleaned output
  2. Sample validation runs on 200-ID subset before full deployment with user approval prompt
  3. Deduplication preserves legitimate sequential IDs while removing OCR artifacts
  4. Raw data is always preserved (original results.csv untouched)
  5. Cleanup report documents heuristics applied, IDs removed, and confidence metrics
**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 13. CLI Subcommand Foundation | 1/1 | Complete    | 2026-06-10 |
| 14. ID Lookup Generation | 0/? | Not started | - |
| 15. Error Investigation & Reporting | 0/? | Not started | - |
| 16. Multi-ID Cleanup & Validation | 0/? | Not started | - |

---

## Coverage

**Requirements mapped:** 10/10 (100%)

| Phase | Requirements | Count |
|-------|--------------|-------|
| 13 | LOOK-03 | 1 |
| 14 | LOOK-01, LOOK-02 | 2 |
| 15 | ERR-01, ERR-02, ERR-03, ERR-04 | 4 |
| 16 | MULTI-01, MULTI-02, MULTI-03 | 3 |

**Total:** 10 requirements

---

## Notes

**Phase ordering rationale:**
- Phase 13 (CLI refactor) is foundation for all other phases -- must come first
- Phases 14-16 are independent after Phase 13 completes
- Ordered by value/risk ratio: lookup (high value, zero risk) -> investigate (medium value, zero risk) -> multi-ID (high value, low risk with validation)

**Research flags:**
- All phases use standard patterns (argparse subparsers, pandas CSV operations, error categorization)
- No phases require deeper research -- all techniques identified in project research

**Risk mitigation:**
- Phase 13: Pure refactor with test validation minimizes risk
- Phase 14: Zero risk -- reads existing CSV, creates new file
- Phase 15: Zero risk -- reads checkpoint, writes reports
- Phase 16: Conservative approach (exact-match dedup, sample validation) prevents overzealous filtering

---
*Last updated: 2026-06-10*
