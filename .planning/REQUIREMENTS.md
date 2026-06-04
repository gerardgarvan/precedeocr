# Requirements: Precede OCR

**Defined:** 2026-06-04
**Core Value:** Reliably extract every Precede ID from every page across 30K+ PDFs so the user can look up which file and page any given ID lives in.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Pipeline

- [ ] **PIPE-01**: User can point the tool at a directory and it recursively discovers all `.pdf` files
- [ ] **PIPE-02**: Each PDF page is converted to a high-DPI image (300+ DPI) for OCR
- [ ] **PIPE-03**: OCR runs across multiple rotations (0/90/180/270 degrees) per page, keeping whichever rotation yields a regex match
- [ ] **PIPE-04**: 5-digit numeric IDs are extracted from OCR output via regex pattern
- [ ] **PIPE-05**: Each extracted ID is mapped to its source filename and page number
- [ ] **PIPE-06**: Multiple IDs on a single page are all captured
- [ ] **PIPE-07**: Pages where no ID is found are flagged in output (not silently dropped)

### Output

- [ ] **OUT-01**: Results are written as CSV with columns: filename, id, page, rotation_detected
- [ ] **OUT-02**: Results are written as JSON mapping filename to pages to IDs

### Quality

- [ ] **QUAL-01**: Low-quality scans are preprocessed (grayscale, threshold, denoise) as a fallback when initial OCR finds no match
- [ ] **QUAL-02**: Common OCR digit confusion (O/0, I/1, S/5) is normalized before regex matching
- [ ] **QUAL-03**: Per-file error handling ensures a single failed file does not crash the entire batch

### Resilience

- [ ] **RESL-01**: Processing can resume from a checkpoint file after a crash or interruption

### Progress

- [ ] **PROG-01**: Processing progress is displayed (file count and/or percentage complete)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Scale

- **SCALE-01**: Parallel processing via multiprocessing to handle 30K+ files efficiently
- **SCALE-02**: Configurable worker count based on hardware

### Reporting

- **REPT-01**: Batch statistics report (total files, successful, failed, IDs found)
- **REPT-02**: Per-file success/failure logging for audit trail
- **REPT-03**: OCR confidence scoring to flag uncertain extractions
- **REPT-04**: Duplicate ID detection across entire corpus

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| GUI or web interface | CLI/script only; output to CSV/JSON for Excel/programmatic access |
| Search CLI tool | User will search CSV/JSON manually or via Excel |
| Cloud OCR services | Local Tesseract already installed; no API costs at 30K+ scale |
| PDF modification | Read-only processing; never alter source files |
| Real-time/streaming | One-shot batch job, not continuous ingestion |
| Database backend | Overkill for one-time extraction; CSV/JSON is portable |
| Multiple OCR engines | Tesseract is sufficient; cross-verification adds complexity |
| Custom OCR model training | Tesseract's numeric recognition is strong enough |
| Document classification | All inputs are same type (scanned PDFs with Precede IDs) |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | Phase 1 | Pending |
| PIPE-02 | Phase 1 | Pending |
| PIPE-03 | Phase 2 | Pending |
| PIPE-04 | Phase 1 | Pending |
| PIPE-05 | Phase 1 | Pending |
| PIPE-06 | Phase 3 | Pending |
| PIPE-07 | Phase 3 | Pending |
| OUT-01 | Phase 1 | Pending |
| OUT-02 | Phase 3 | Pending |
| QUAL-01 | Phase 5 | Pending |
| QUAL-02 | Phase 5 | Pending |
| QUAL-03 | Phase 4 | Pending |
| RESL-01 | Phase 4 | Pending |
| PROG-01 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-06-04*
*Last updated: 2026-06-04 after roadmap creation*
