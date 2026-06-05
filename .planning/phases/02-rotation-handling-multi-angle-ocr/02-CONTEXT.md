# Phase 2: Rotation Handling — Multi-Angle OCR - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Optimize the existing multi-rotation OCR pipeline to eliminate false positives from wrong rotation angles, add diagnostic capabilities, and improve reporting. Phase 1 already implemented 4-rotation OCR with early exit — Phase 2 refines the rotation strategy based on real-world test results (37/39 correct, wrong IDs from 0-degree false positives, 2 missed pages).

Requirements covered: PIPE-03

</domain>

<decisions>
## Implementation Decisions

### Rotation Strategy
- **D-08:** Change rotation order to [90, 270, 0, 180]. The 90-degree rotation is where all correct matches occur. Trying 90 first eliminates false positives from 0-degree matches (which was the source of all wrong IDs in Phase 1 testing).
- **D-09:** Keep early exit behavior — exit on first valid match. Combined with the corrected rotation order (90 first), early exit is both fast and accurate.
- **D-10:** Maintain fallback to other angles (270, 0, 180) if 90 degrees yields no match. Some pages may have different orientations.

### Diagnostics
- **D-11:** Add a `--debug` flag that prints raw OCR text at each rotation for each page. Helps diagnose whether extraction failures are rotation-related or scan-quality-related. Debug output goes to stderr/console, not into the CSV.

### Output Enhancements
- **D-12:** Add a `notes` column to the CSV output (columns become: `filename, page, id, rotation_detected, notes`). For pages with no ID found, populate with a concise failure reason: `no_match_any_rotation`, `no_text_detected`, or `only_noise_matches`. This enables bulk failure analysis across large datasets without re-running in debug mode.
- **D-13:** Print rotation distribution summary to console after processing: e.g., "35 at 90 degrees, 2 at 0 degrees, 2 no match". Validates the pipeline and spots anomalies.

### Claude's Discretion
- Exact debug output format (structured vs. freeform)
- Whether to log debug info to a file in addition to console
- How to classify failure reasons (the three categories above may need expansion based on what Tesseract returns)
- PSM mode tuning if investigation reveals it would help

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Implementation
- `precede_ocr.py` — Current pipeline implementation. `extract_id_with_rotation()` at line ~133 is the primary function to modify (rotation order, debug output, failure reasons).

### Research Documents
- `.planning/research/PITFALLS.md` — Pitfall 7 (OSD unreliability), Pitfall 6 (PSM modes), Pitfall 12 (regex over-matching)
- `.planning/research/ARCHITECTURE.md` — Multi-rotation strategy rationale

### Project Documents
- `.planning/PROJECT.md` — Core value, constraints
- `.planning/REQUIREMENTS.md` — PIPE-03 is the target requirement
- `.planning/ROADMAP.md` — Phase 2 success criteria
- `.planning/phases/01-foundation-single-file-ocr-pipeline/01-CONTEXT.md` — Phase 1 decisions D-01 through D-07

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `extract_id_with_rotation()` — Core function to modify. Currently iterates [0, 90, 180, 270] with early exit. Change order to [90, 270, 0, 180].
- `normalize_digits()` — Already handles OCR digit confusion. No changes needed.
- `select_most_likely_id()` — Filters trivial patterns. Could be extended to classify failure reasons.
- `write_results_csv()` — Needs `notes` column added to DataFrame output.

### Established Patterns
- Tesseract config: `--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789`
- Memory-safe pdf2image: `output_folder` + `paths_only=True`
- Auto-detect paths for Tesseract and Poppler (cross-machine compatibility)

### Integration Points
- `process_single_pdf()` — Must propagate `notes` field in result dicts
- `write_results_csv()` — Must include `notes` in column order
- CLI argument parsing in `__main__` block — Add `--debug` flag

</code_context>

<specifics>
## Specific Ideas

- Every correct match in Phase 1 testing came from 90-degree rotation. All wrong IDs were 0-degree false positives. This strongly supports 90-first ordering.
- 2 pages had genuine IDs that OCR missed entirely. Debug mode will help diagnose whether these are rotation issues or scan quality issues (deferred to Phase 5 if quality-related).
- The user processes 30K+ PDFs — failure info in the CSV is critical for batch analysis without re-running individual files in debug mode.

</specifics>

<deferred>
## Deferred Ideas

- Raw OCR text column in CSV — considered but rejected for Phase 2. Too messy for large datasets. Debug mode serves this purpose for individual investigation.
- PSM mode tuning — may be explored if debug output reveals PSM 6 is suboptimal for certain pages. Currently at Claude's discretion.

</deferred>

---

*Phase: 02-rotation-handling-multi-angle-ocr*
*Context gathered: 2026-06-05*
