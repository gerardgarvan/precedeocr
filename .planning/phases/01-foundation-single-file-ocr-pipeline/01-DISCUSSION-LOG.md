# Phase 1: Foundation — Single-File OCR Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-04
**Phase:** 01-foundation-single-file-ocr-pipeline
**Areas discussed:** ID extraction strategy, Phase 1 rotation scope, Output granularity

---

## ID Extraction Strategy

### Q1: How should the pipeline identify Precede IDs in OCR text?

| Option | Description | Selected |
|--------|-------------|----------|
| Pure regex scan | Scan full OCR text for any 5-digit number. Simpler, more robust. The "Precede" cursive text may not OCR reliably. | ✓ |
| Anchor to "Precede" text | Look for "Precede" keyword first, then extract nearby 5-digit numbers. Reduces false positives but risks missing IDs. | |
| Try both (anchor first, regex fallback) | First try anchor approach; if no match, fall back to pure regex. Most thorough but adds complexity. | |
| You decide | Claude picks based on technical trade-offs. | |

**User's choice:** Pure regex scan (Recommended)
**Notes:** None

### Q2: When regex finds multiple 5-digit numbers on a single page, how should we handle it?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep all matches | Output every 5-digit number found. Maximizes recall. | |
| Keep first match only | Take the first 5-digit number found in OCR text. | |
| You decide | Claude picks based on PIPE-06 requirement. | |

**User's choice:** Free text — "there aren't multiple ids per page. there are multiple ids per PDF file"
**Notes:** Key clarification: one Precede ID per page, multiple IDs per PDF across its pages. This reframes the multi-match concern.

### Q3: If regex finds multiple 5-digit numbers on a single page (noise scenario), keep all or one?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep all matches per page | Output all 5-digit numbers. Safer — doesn't risk dropping real ID. | |
| Keep only one per page | Take the most likely match. Cleaner output. | ✓ |
| You decide | Claude picks safest approach. | |

**User's choice:** Keep only one per page
**Notes:** Since there's only one real ID per page, keeping one match and filtering noise is preferred.

---

## Phase 1 Rotation Scope

### Q1: Should Phase 1 handle rotation, or stay strictly at 0° orientation?

| Option | Description | Selected |
|--------|-------------|----------|
| Try all 4 rotations now | 0°, 90°, 180°, 270° with early exit. Phase 1 produces real results on actual PDFs. | ✓ |
| Try 0° and 90° only | Only the two most likely orientations. Faster but may miss edge cases. | |
| 0° only (strict boundary) | Phase 1 only tests default orientation. Real rotation waits for Phase 2. | |

**User's choice:** Try all 4 rotations now (Recommended)
**Notes:** This pulls core rotation logic into Phase 1, shifting Phase 2 scope to optimization/tracking.

---

## Output Granularity

### Q1: Should the CSV include rows for pages where no ID was found?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include no-match rows | Every page gets a row. Enables completeness auditing. | ✓ |
| No, only pages with IDs | Cleaner output but can't tell which pages were skipped. | |
| You decide | Claude picks based on PIPE-07 requirement. | |

**User's choice:** Yes, include no-match rows (Recommended)
**Notes:** None

### Q2: What CSV columns?

| Option | Description | Selected |
|--------|-------------|----------|
| Minimum + rotation | filename, page, id, rotation_detected. Matches OUT-01 and prepares for Phase 2. | ✓ |
| Minimum only | filename, page, id. Add rotation in Phase 2. | |
| You decide | Claude picks based on requirements. | |

**User's choice:** Minimum + rotation (Recommended)
**Notes:** None

---

## Claude's Discretion

- Project structure (single script vs. modular)
- PSM mode selection
- Memory management approach
- File handle cleanup patterns
- DPI setting (300+ per research)
- Match disambiguation logic for multiple 5-digit numbers on one page

## Deferred Ideas

None — discussion stayed within phase scope.
