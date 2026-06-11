# Phase 16: Multi-ID Cleanup & Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 16-multi-id-cleanup-validation
**Areas discussed:** Noise detection approach, Sample validation flow, Output format & flagging

---

## Noise Detection Approach

| Option | Description | Selected |
|--------|-------------|----------|
| CSV heuristics only | Use existing seq_outlier flags + add pattern heuristics (repeated digits, ID frequency across pages). No PDF re-rendering. Fast, works on CSV data alone. | ✓ |
| Re-render + re-OCR | Re-open PDFs and re-OCR multi-ID pages to verify each ID. Most accurate but slow (5,141 pages to re-render). Similar to investigate command. | |
| You decide | Claude picks the approach based on accuracy vs speed trade-off for 5K+ pages | |

**User's choice:** CSV heuristics only (Recommended)
**Notes:** No page re-rendering needed. Fast approach working on existing CSV data.

### Follow-up: Dedup Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Same-page dedup + patterns | Remove exact duplicate IDs on the same page. Flag repeated-digit IDs (11111, 00000) and seq_outlier IDs. Simplest, addresses the main noise source. | ✓ |
| Full cross-page analysis | Also analyze ID frequency across the entire corpus — IDs appearing on only one page alongside other IDs get lower confidence. More thorough but more complex. | |
| You decide | Claude determines which heuristics add value based on the data characteristics | |

**User's choice:** Same-page dedup + patterns (Recommended)
**Notes:** No cross-page frequency analysis. Keep scope focused.

---

## Sample Validation Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Interactive terminal prompt | Run analysis on 200-ID sample, display summary table in terminal (IDs flagged, reasons, confidence), then ask 'Apply to full dataset? [y/N]'. User reviews inline and approves. | ✓ |
| Two-step with export | First run exports sample_review.csv for offline inspection in Excel. User reviews, then re-runs with --confirmed flag to apply to full dataset. | |
| Auto with --no-confirm flag | Default is interactive prompt, but --no-confirm flag skips validation for automation/scripting. Best of both worlds. | |

**User's choice:** Interactive terminal prompt (Recommended)
**Notes:** Inline review and approval before full dataset processing.

---

## Output Format & Flagging

| Option | Description | Selected |
|--------|-------------|----------|
| Cleaned CSV + removed CSV + report | results_cleaned.csv has noise rows removed. removed_ids.csv lists what was removed and why. cleanup_report.md documents heuristics, counts, and confidence. Three files, clear separation. | ✓ |
| Single flagged CSV + report | One CSV with all rows, plus a 'noise_flag' column (True/False) and 'noise_reason'. User filters in Excel. Report documents heuristics. Simpler but noisier output. | |
| You decide | Claude picks the output structure based on user workflow (Excel-based lookup) | |

**User's choice:** Cleaned CSV + removed CSV + report (Recommended)
**Notes:** Three-file output for clear separation of clean data, removed data, and documentation.

---

## Claude's Discretion

- Confidence thresholds for each heuristic
- Ordering of heuristic application
- Cleanup report structure and detail level
- Whether to include a --dry-run flag
- Edge case handling (e.g., page with 2 IDs where one is repeated-digit)

## Deferred Ideas

None — discussion stayed within phase scope
