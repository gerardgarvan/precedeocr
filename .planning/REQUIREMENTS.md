# Requirements: Precede OCR v1.3 Results Cleanup & ID Lookup

**Milestone:** v1.3 Results Cleanup & ID Lookup
**Created:** 2026-06-09
**Goal:** Produce a clean, Excel-friendly ID lookup file from production results, and investigate/fix pipeline errors and multi-ID noise.

---

## Active Requirements

### ID Lookup (LOOK)

- [x] **LOOK-01**: User can generate an ID lookup CSV sorted by ID number with columns: ID, Filename, Page, Folder
- [x] **LOOK-02**: Lookup CSV opens correctly in Excel (UTF-8 BOM encoding, proper quoting, IDs not interpreted as dates)
- [x] **LOOK-03**: User can run `python precede_ocr.py lookup <scan.csv>` as a CLI subcommand

### Error Investigation (ERR)

- [x] **ERR-01**: User can investigate failed files — verify existence, categorize by error type (FileNotFoundError vs EmptyFileError), identify root causes
- [x] **ERR-02**: User can investigate no-match pages — determine if blank page, OCR failure, or missing ID label
- [x] **ERR-03**: Pipeline fixes are applied for fixable errors (e.g., path resolution issues, retry logic)
- [x] **ERR-04**: User receives a quality report (markdown) documenting all findings, error categories, and recommendations

### Multi-ID Cleanup (MULTI)

- [ ] **MULTI-01**: User can analyze multi-ID pages to determine which are real (multiple IDs per page) vs OCR noise
- [ ] **MULTI-02**: Conservative deduplication flags likely noise without deleting — biases toward preservation, raw data always preserved
- [ ] **MULTI-03**: User can run cleanup via CLI subcommand with sample validation before full deployment

---

## Future Requirements

- Automated re-processing pipeline for failed files (re-run with targeted fixes)
- Visual inspection UI for manual review of ambiguous pages

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| Database backend (SQLite) | CSV is sufficient for Excel-based lookup workflow |
| Cloud OCR re-processing | Local Tesseract only, per project constraints |
| GUI/web interface for lookup | CLI + Excel is the user's workflow |
| Fuzzy ID matching | Exact 5-digit match only — fuzzy adds false positive risk |
| Full EDA profiling (ydata-profiling) | Overkill for targeted error analysis on 52K rows |

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| LOOK-01 | Phase 14 | Complete |
| LOOK-02 | Phase 14 | Complete |
| LOOK-03 | Phase 13 | Complete |
| ERR-01 | Phase 15 | Complete |
| ERR-02 | Phase 15 | Complete |
| ERR-03 | Phase 15 | Complete |
| ERR-04 | Phase 15 | Complete |
| MULTI-01 | Phase 16 | In Progress (Wave 0 test stubs complete) |
| MULTI-02 | Phase 16 | In Progress (Wave 0 test stubs complete) |
| MULTI-03 | Phase 16 | In Progress (Wave 0 test stubs complete) |

**Coverage:** 10/10 requirements mapped (100%)

**Notes:**
- Phase 16 Wave 0 (16-00-PLAN.md) complete: Created 7 test stubs for MULTI-01 through MULTI-03
- Phase 16 Wave 1 (16-01-PLAN.md) pending: Will implement production code to validate requirements

---
*Last updated: 2026-06-11*
