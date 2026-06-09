# Requirements: Precede OCR v1.3 Results Cleanup & ID Lookup

**Milestone:** v1.3 Results Cleanup & ID Lookup
**Created:** 2026-06-09
**Goal:** Produce a clean, Excel-friendly ID lookup file from production results, and investigate/fix pipeline errors and multi-ID noise.

---

## Active Requirements

### ID Lookup (LOOK)

- [ ] **LOOK-01**: User can generate an ID lookup CSV sorted by ID number with columns: ID, Filename, Page, Folder
- [ ] **LOOK-02**: Lookup CSV opens correctly in Excel (UTF-8 BOM encoding, proper quoting, IDs not interpreted as dates)
- [ ] **LOOK-03**: User can run `python precede_ocr.py lookup <scan.csv>` as a CLI subcommand

### Error Investigation (ERR)

- [ ] **ERR-01**: User can investigate failed files — verify existence, categorize by error type (FileNotFoundError vs EmptyFileError), identify root causes
- [ ] **ERR-02**: User can investigate no-match pages — determine if blank page, OCR failure, or missing ID label
- [ ] **ERR-03**: Pipeline fixes are applied for fixable errors (e.g., path resolution issues, retry logic)
- [ ] **ERR-04**: User receives a quality report (markdown) documenting all findings, error categories, and recommendations

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
| LOOK-01 | TBD | Pending |
| LOOK-02 | TBD | Pending |
| LOOK-03 | TBD | Pending |
| ERR-01 | TBD | Pending |
| ERR-02 | TBD | Pending |
| ERR-03 | TBD | Pending |
| ERR-04 | TBD | Pending |
| MULTI-01 | TBD | Pending |
| MULTI-02 | TBD | Pending |
| MULTI-03 | TBD | Pending |

**Coverage:** 0/10 requirements mapped (roadmap pending)

---
*Last updated: 2026-06-09*
