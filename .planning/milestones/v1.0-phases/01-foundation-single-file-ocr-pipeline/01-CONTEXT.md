# Phase 1: Foundation — Single-File OCR Pipeline - Context

**Gathered:** 2026-06-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Build an end-to-end pipeline that takes a single PDF, converts each page to a high-DPI image, runs OCR with multi-rotation support, extracts 5-digit Precede IDs via regex, and outputs results as CSV. This phase proves the core OCR-to-ID extraction logic works before scaling to 30K+ files.

Requirements covered: PIPE-01, PIPE-02, PIPE-04, PIPE-05, OUT-01

</domain>

<decisions>
## Implementation Decisions

### ID Extraction Strategy
- **D-01:** Use pure regex scan (`\d{5}`) on full OCR text to find 5-digit IDs. Do NOT anchor to the "Precede" cursive text — cursive may not OCR reliably, and anchoring risks missing valid IDs.
- **D-02:** One ID per page. The data has exactly one Precede ID per page (multiple IDs exist per PDF file across its pages, not per page).
- **D-03:** When regex finds multiple 5-digit numbers on a single page, keep only one match — the most likely candidate. Filter out obvious noise (page numbers, dates) if possible.

### Rotation Handling (Pulled into Phase 1)
- **D-04:** Try all 4 rotations (0, 90, 180, 270 degrees) in Phase 1, with early exit on first valid match. This means Phase 1 produces real results on actual PDFs where IDs are rotated ~90 degrees.
- **D-05:** Phase 2 scope shifts from "implement rotation" to "optimize and track rotation" — rotation_detected column, rotation statistics, and potential PSM mode tuning.

### Output Format
- **D-06:** CSV includes a row for every page scanned, including pages where no ID was found (blank/null in the id column). This enables completeness auditing.
- **D-07:** CSV columns: `filename, page, id, rotation_detected`. The rotation_detected column records which angle yielded the match (0/90/180/270) or blank for no-match pages.

### Claude's Discretion
- Project structure (single script vs. modular files)
- PSM mode selection for Tesseract (research recommends PSM 7 for single line)
- Memory management approach (output_folder + paths_only for pdf2image)
- File handle cleanup patterns
- DPI setting (300+ DPI per research, exact value at Claude's discretion)
- How to determine "most likely" match when multiple 5-digit numbers appear on one page

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research Documents
- `.planning/research/ARCHITECTURE.md` — Pipeline architecture, component boundaries, multi-rotation strategy, build order
- `.planning/research/PITFALLS.md` — 15 pitfalls including memory exhaustion (Pitfall 1), DPI (Pitfall 5), file handles (Pitfall 3), PSM modes (Pitfall 6), OSD unreliability (Pitfall 7), regex over-matching (Pitfall 12)
- `.planning/research/STACK.md` — Technology stack decisions: pytesseract, pdf2image, Pillow, OpenCV, version locks
- `.planning/research/FEATURES.md` — Feature landscape, table stakes vs. differentiators, MVP recommendation

### Project Documents
- `.planning/PROJECT.md` — Core value, constraints, key decisions
- `.planning/REQUIREMENTS.md` — v1 requirements with REQ-IDs, traceability matrix
- `.planning/ROADMAP.md` — Phase definitions, success criteria, dependency chain

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No Python code exists yet.

### Established Patterns
- None — first phase establishes all patterns for subsequent phases.

### Integration Points
- Tesseract OCR: already installed on Windows, verify in PATH on first run
- Poppler: already installed on Windows, required by pdf2image for PDF-to-image conversion
- Output directory: CSV file written to user-specified or default location

</code_context>

<specifics>
## Specific Ideas

- One Precede ID exists per page, not multiple — the "multiple IDs per page" requirement (PIPE-06, Phase 3) may need revisiting based on this user clarification
- IDs are rotated ~90 degrees from upright reading position — all 4 rotations should be tried but 90 degrees is most likely to match
- The "Precede" cursive label above the ID should NOT be used as an anchor for extraction — rely on pure regex instead

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-single-file-ocr-pipeline*
*Context gathered: 2026-06-04*
