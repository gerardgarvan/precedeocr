# Phase 5: Quality — Conditional Preprocessing & Validation - Context

**Gathered:** 2026-06-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Improve extraction rate on low-quality scans by adding a conditional preprocessing fallback and post-hoc sequential validation, without degrading results on clean scans. Covers QUAL-01 (preprocessing fallback) and QUAL-02 (character normalization — satisfied by existing digit whitelist).

</domain>

<decisions>
## Implementation Decisions

### Preprocessing Pipeline
- **D-01:** Single-pass preprocessing: grayscale + Otsu threshold + light denoise (OpenCV). No escalating pipeline — one combo handles most degraded scans.
- **D-02:** Preprocessing retry re-runs ALL 4 rotations [90, 270, 0, 180] on the preprocessed image, not just a subset. Preprocessing may reveal text at a different rotation than the original attempt.

### Preprocessing Trigger
- **D-03:** ALL failure types trigger preprocessing retry: `no_text_detected`, `only_noise_matches`, and `no_match_any_rotation`. Maximizes recovery rate.

### Output Tracking
- **D-04:** Use existing `notes` column to indicate preprocessing was used (e.g., `preprocessed`). No new CSV column — keeps schema stable. Users filter in Excel via text filter on notes.

### Normalization Strategy
- **D-05:** Keep digit whitelist (`tessedit_char_whitelist=0123456789`) for BOTH direct and preprocessed OCR passes. The whitelist forces Tesseract to output digits only, making `normalize_digits()` a safety net rather than primary mechanism. QUAL-02 is effectively satisfied by the whitelist constraining output to digits.

### Sequential ID Validation (Folded Scope)
- **D-06:** Post-hoc trend-based sequence check within each file. IDs within a file generally follow a sequential pattern (increasing or decreasing). IDs that deviate wildly from the trend are flagged.
- **D-07:** Flag + confidence score for out-of-sequence IDs. Keep the ID in results but add a confidence indicator based on deviation from the expected sequence trend. Noted in the output so the user can review flagged entries.
- **D-08:** 270-degree rotation results are particularly suspect for producing false positives (user observation from real data). The sequence check helps catch these.

### Claude's Discretion
- Specific OpenCV preprocessing parameters (kernel sizes, blur strength) — Claude picks based on OCR best practices
- Confidence score formula and thresholds for sequence deviation
- How to handle files with too few IDs to establish a reliable trend (e.g., single-page PDFs)

### Folded Todos
None — no matching todos found.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Pipeline
- `precede_ocr.py` — Main pipeline with `extract_id_with_rotation()` (line 199), `normalize_digits()` (line 84), `classify_failure_reason()` (line 170), `process_single_pdf()` (line 259)
- `tests/test_precede_ocr.py` — 111 existing tests covering OCR, rotation, CSV/JSON output, checkpointing, resilience

### Stack Reference
- `.planning/research/STACK.md` — OpenCV 4.13.0.92 listed for advanced preprocessing (adaptive thresholding, noise reduction, morphological ops)

### Requirements
- `.planning/REQUIREMENTS.md` — QUAL-01 (preprocessing fallback), QUAL-02 (digit normalization)

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `normalize_digits()` (line 84) — Already handles O/0, I/1, S/5, B/8, Z/2 substitution. Called at line 243 before regex matching.
- `classify_failure_reason()` (line 170) — Returns failure category (`no_text_detected`, `only_noise_matches`, `no_match_any_rotation`). Direct input for preprocessing trigger logic.
- `extract_id_with_rotation()` (line 199) — Core OCR function. Preprocessing retry wraps around this or inserts before the rotation loop.
- `select_all_valid_ids()` (line 149) — Filters trivial patterns. Reusable for preprocessed results.

### Established Patterns
- **Rotation loop with early exit** — [90, 270, 0, 180] order, stops on first valid match. Preprocessing retry should follow the same pattern.
- **Digit whitelist OCR config** — `--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789`. Keep for both direct and preprocessed passes.
- **Failure classification** — Three-way classification already exists. Preprocessing trigger uses this directly.
- **Notes column for metadata** — Already used for failure reasons and error messages. Natural place for `preprocessed` flag.

### Integration Points
- `extract_id_with_rotation()` — Preprocessing logic inserts here (preprocess image, then re-run rotation loop)
- `process_single_pdf()` — Drives per-page processing; preprocessing retry called when initial extraction fails
- `write_results_csv()` — Notes column already in output; no schema change needed
- OpenCV (`cv2`) — Not yet imported. Needs to be added as import for preprocessing functions.

</code_context>

<specifics>
## Specific Ideas

- **Sequential IDs:** User observed that IDs within a file generally follow a numeric sequence. 270-degree rotation results frequently produce numbers that break this sequence — strong signal for false positives.
- **Trend-based validation:** Don't require strict consecutive numbering (gaps are OK). Check for outliers that deviate wildly from the overall increasing/decreasing trend within a file.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-quality-conditional-preprocessing-validation*
*Context gathered: 2026-06-05*
