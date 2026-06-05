# Phase 2: Rotation Handling — Multi-Angle OCR - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 02-rotation-handling-multi-angle-ocr
**Areas discussed:** Early exit vs. best match, Rotation order, Wrong/missing ID diagnosis, Rotation statistics, Failure info in CSV

---

## Early Exit vs. Best Match

| Option | Description | Selected |
|--------|-------------|----------|
| Best match | Try all 4 rotations, collect all matches, pick the best candidate. Fixes wrong IDs at cost of ~2-3x slower per page. | |
| Smart early exit | Try preferred rotation first (90), then others. Exit early only if match comes from preferred angle. | ✓ |
| Keep early exit | Current behavior. Fast but keeps false positive problem. | |

**User's choice:** Smart early exit — "every correct match is at 90, the wrong ones have a zero degree match"
**Notes:** This key insight drove the entire rotation strategy. 0-degree false positives are the root cause of wrong IDs.

---

## Rotation Order

Merged into the early exit discussion. User confirmed 90 degrees is where all correct matches occur. Order decided: [90, 270, 0, 180].

---

## Wrong/Missing ID Diagnosis

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add debug output | Add --debug flag that prints raw OCR text at each rotation. | ✓ |
| No, just fix rotation order | Fix order and re-test. Investigate in Phase 5 if still failing. | |

**User's choice:** Yes, add debug output
**Notes:** Low effort, high diagnostic value. Helps determine if missed pages are rotation issues (Phase 2) or quality issues (Phase 5).

---

## Missing Pages Investigation

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, IDs exist but OCR missed them | Pages have valid Precede IDs that pipeline failed to extract. | ✓ |
| No, blank/cover pages | Pages genuinely have no ID. | |
| Not sure | Haven't checked. | |

**User's choice:** Yes, IDs exist but OCR missed them
**Notes:** 2 of 39 pages have real IDs that the current pipeline misses entirely.

---

## Rotation Statistics

| Option | Description | Selected |
|--------|-------------|----------|
| Summary at end | Print rotation distribution after processing. | ✓ |
| Per-page in CSV only | Already have rotation_detected in CSV. | |
| Both console and CSV | Summary + CSV column. | |

**User's choice:** Summary at end
**Notes:** Simple console summary for validation.

---

## Failure Info in CSV

| Option | Description | Selected |
|--------|-------------|----------|
| Failure reason column | Add 'notes' column with concise failure reasons. | ✓ |
| Raw OCR text column | Full raw text in CSV. | |
| Both reason and raw text | Most complete but messiest. | |

**User's choice:** Failure reason column
**Notes:** User wants to analyze failures across large datasets (30K+ PDFs) without re-running debug mode. Concise filterable reasons are preferred.

---

## Claude's Discretion

- Debug output format
- PSM mode tuning if investigation reveals issues
- Failure reason classification expansion

## Deferred Ideas

- Raw OCR text column in CSV — too messy for large datasets
