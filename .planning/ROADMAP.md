# Roadmap: Precede OCR

**Project:** PDF ID Scanner & Mapper
**Milestone:** v1
**Created:** 2026-06-04
**Granularity:** Standard

## Core Value

Reliably extract every Precede ID from every page across 30K+ PDFs so the user can look up which file and page any given ID lives in.

## Phases

- [x] **Phase 1: Foundation** - Single-file OCR pipeline that extracts IDs from one PDF
- [x] **Phase 2: Rotation Handling** - Multi-angle OCR for rotated IDs (0/90/180/270 degrees)
- [x] **Phase 3: Scale** - Parallel processing for 30K+ PDFs with progress tracking (completed 2026-06-05)
- [ ] **Phase 4: Resilience** - Error handling, retry logic, and resume capability
- [ ] **Phase 5: Quality** - Conditional preprocessing and character normalization

## Phase Details

### Phase 1: Foundation — Single-File OCR Pipeline
**Goal**: Validate entire pipeline end-to-end with one PDF, proving OCR and ID extraction logic works before scaling.
**Depends on**: Nothing (first phase)
**Requirements**: PIPE-01, PIPE-02, PIPE-04, PIPE-05, OUT-01
**Success Criteria** (what must be TRUE):
  1. User can point the tool at a single PDF and it extracts all 5-digit numeric IDs from every page
  2. Each extracted ID is correctly mapped to its source filename and page number
  3. Results are written as CSV with columns: filename, id, page
  4. The tool handles multi-page PDFs without memory exhaustion
  5. Images are converted at 300+ DPI for reliable digit recognition
**Plans:** 2/2 plans executed
Plans:
- [x] 01-01-PLAN.md — Setup environment and implement complete OCR pipeline (precede_ocr.py)
- [x] 01-02-PLAN.md — Create test infrastructure and validate with real PDF

### Phase 2: Rotation Handling — Multi-Angle OCR
**Goal**: Optimize rotation strategy to eliminate false positives by prioritizing 90-degree rotation, add debug diagnostics, failure classification in CSV notes column, and rotation distribution summary.
**Depends on**: Phase 1
**Requirements**: PIPE-03
**Success Criteria** (what must be TRUE):
  1. User can extract IDs from pages rotated at 0, 90, 180, or 270 degrees
  2. The tool tries all 4 rotations and returns the first valid ID match
  3. Detected rotation angle is tracked in output (CSV includes rotation_detected column)
  4. OCR completes successfully regardless of page orientation
**Plans:** 1/1 plans executed
Plans:
- [x] 02-01-PLAN.md — Implement rotation reorder, debug flag, failure classification, notes column, and rotation summary

### Phase 3: Scale — Parallel Processing
**Goal**: Process 30K+ PDFs efficiently using parallel workers with progress visibility.
**Depends on**: Phase 2
**Requirements**: PIPE-06, PIPE-07, OUT-02, PROG-01
**Success Criteria** (what must be TRUE):
  1. User can process 100+ PDFs in parallel without crashes or memory exhaustion
  2. Multiple IDs on a single page are all captured and output
  3. Pages where no ID is found are flagged in output (not silently dropped)
  4. Results are written as JSON mapping filename to pages to IDs
  5. Progress is displayed with file count, percentage complete, and ETA
**Plans:** 2/2 plans complete
Plans:
- [x] 03-01-PLAN.md — Multi-ID extraction, data contract change, JSON output writer
- [x] 03-02-PLAN.md — Parallel processing with multiprocessing.Pool, directory CLI, tqdm progress

### Phase 4: Resilience — Error Handling & Checkpointing
**Goal**: Complete 30K batches even with corrupted files or crashes, resuming from last successful file.
**Depends on**: Phase 3
**Requirements**: QUAL-03, RESL-01
**Success Criteria** (what must be TRUE):
  1. User can resume processing after a crash or interruption from the last checkpoint
  2. A single failed PDF does not crash the entire batch
  3. Failed files are logged with error details for investigation
  4. User can review batch statistics (total files, successful, failed, IDs found)
**Plans:** 2 plans
Plans:
- [x] 04-01-PLAN.md — Resilience utility functions: retry decorator, error logging, checkpoint save/load, batch stats
- [ ] 04-02-PLAN.md — Wire resilience into pipeline: checkpoint in process loop, resume in main, --fresh flag, stats output

### Phase 5: Quality — Conditional Preprocessing & Validation
**Goal**: Improve extraction rate on low-quality scans without degrading high-quality results.
**Depends on**: Phase 4
**Requirements**: QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):
  1. Low-quality scans that fail initial OCR are automatically preprocessed (grayscale, threshold, denoise) and retried
  2. Common OCR digit confusion (O/0, I/1, S/5) is normalized before regex matching
  3. Preprocessing is applied conditionally only when initial OCR finds no ID
  4. User can identify which extractions used preprocessing vs. direct OCR
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-06-04 |
| 2. Rotation Handling | 1/1 | Complete | 2026-06-05 |
| 3. Scale | 2/2 | Complete   | 2026-06-05 |
| 4. Resilience | 0/2 | Planning complete | - |
| 5. Quality | 0/0 | Not started | - |

## Dependencies

```
Phase 1 (Foundation)
  └─> Phase 2 (Rotation Handling)
       └─> Phase 3 (Scale)
            └─> Phase 4 (Resilience)
                 └─> Phase 5 (Quality)
```

**Critical path**: All phases are sequential. Each phase builds on validated functionality from the previous phase.

## Notes

### Research Integration
Research identified 5 critical Windows-specific pitfalls that must be addressed from Phase 1:
- Memory exhaustion from pdf2image (use output_folder + paths_only=True)
- Insufficient DPI (explicitly set 300+ DPI)
- File handle leaks (use context managers)
- Wrong PSM mode (use PSM 7 for isolated IDs)
- Tesseract memory leak (process recycling in Phase 3)

### Validation Needs
- **Phase 3**: Test ProcessPoolExecutor on Windows to validate spawn overhead mitigation
- **Phase 5**: A/B test preprocessing on sample corpus to measure actual accuracy improvement

### Build Order Rationale
1. Phase 1 validates core OCR logic works before adding complexity
2. Phase 2 debugs rotation logic serially before parallelization
3. Phase 3 adds parallelization only after proven serial pipeline
4. Phase 4 adds error handling after understanding failure modes at scale
5. Phase 5 adds preprocessing as optional fallback after measuring baseline accuracy

---
*Last updated: 2026-06-05*
