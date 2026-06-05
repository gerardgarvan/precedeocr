# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — PDF ID Scanner & Mapper

**Shipped:** 2026-06-05
**Phases:** 5 | **Plans:** 10

### What Was Built
- Complete OCR pipeline (precede_ocr.py, 1,101 LOC) that extracts 5-digit Precede IDs from multi-page PDFs
- Multi-rotation OCR strategy with prioritized rotation order (90/270/0/180)
- Parallel processing with multiprocessing.Pool for 30K+ file batches
- Crash-safe checkpoint/resume with atomic writes and retry logic
- Conditional preprocessing fallback (OpenCV) and Theil-Sen robust sequence validation
- 141 tests (1,689 LOC) with 94.9% baseline OCR accuracy

### What Worked
- Sequential phase dependency chain validated each layer before adding complexity (OCR first, then rotation, then parallelization, then resilience, then quality)
- Starting with a real PDF for validation in Phase 1 caught real-world issues early (Tesseract path detection, Poppler versioned subdirectories)
- Brute-force multi-rotation OCR with regex validation was simple and effective — no need for OSD or complex orientation detection
- Phase 5 gap closure cycle (OLS → Theil-Sen regression) was caught by audit process before milestone completion

### What Was Inefficient
- Phase 5 required a gap closure plan (05-03) to fix validate_sequence() — initial OLS regression approach was too sensitive to outliers, should have researched robust statistics earlier
- Some SUMMARY.md files lacked one-liner fields, requiring manual cleanup during milestone archival
- Initial REQUIREMENTS.md had parallel processing (SCALE-01/02) in v1 scope but it was actually deferred to v2 while Phase 3 implemented it anyway — requirements scoping was slightly inconsistent

### Patterns Established
- Atomic checkpoint writes (tempfile + os.replace) as standard crash-safety pattern
- Module-level wrapper functions for Windows multiprocessing compatibility (spawn/pickle constraints)
- Notes column chaining: each phase extends the notes field with semicolons, never overwrites
- Conditional preprocessing: try direct OCR first, only preprocess on failure

### Key Lessons
1. Research robust statistics approaches (Theil-Sen, RANSAC) before implementing regression-based validation — OLS is rarely appropriate for OCR data with potential outliers
2. Windows multiprocessing requires `if __name__ == '__main__'` guards, module-level functions, and picklable config — design for this from the start
3. Auto-detecting tool paths (Tesseract, Poppler) with recursive search is worth the upfront effort — eliminates user environment setup issues

### Cost Observations
- Model mix: ~40% opus (planning), ~60% sonnet (execution)
- Notable: 2-day milestone from project init to shipped — sequential phases kept scope tight

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 5 | 10 | Initial development — established sequential phase pattern |

### Cumulative Quality

| Milestone | Tests | LOC (Pipeline) | LOC (Tests) |
|-----------|-------|-----------------|-------------|
| v1.0 | 141 | 1,101 | 1,689 |

### Top Lessons (Verified Across Milestones)

1. Validate core logic with real data before adding complexity layers
2. Design for Windows multiprocessing constraints from day one
