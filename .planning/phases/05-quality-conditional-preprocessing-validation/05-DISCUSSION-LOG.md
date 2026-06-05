# Phase 5: Quality — Conditional Preprocessing & Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 05-quality-conditional-preprocessing-validation
**Areas discussed:** Preprocessing Pipeline, Preprocessing Trigger, Output Tracking, Normalization Strategy, Sequential ID Validation

---

## Preprocessing Pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Single pass (Recommended) | One preprocessing combo: grayscale + Otsu threshold + light denoise. Simple, fast, handles most degraded scans. | Yes |
| Escalating pipeline | Try mild preprocessing first, then aggressive if still no match. More complex but catches more edge cases. Slower per page. | |
| You decide | Claude picks the best preprocessing approach based on the codebase and OCR best practices. | |

**User's choice:** Single pass
**Notes:** None

### Follow-up: Retry Rotation Scope

| Option | Description | Selected |
|--------|-------------|----------|
| All 4 rotations (Recommended) | Re-run the full [90, 270, 0, 180] rotation loop on the preprocessed image. | Yes |
| 90-degree only | Only retry at 90 degrees since that's where most valid IDs are. Faster, but misses edge cases. | |
| You decide | Claude picks based on performance vs accuracy tradeoff. | |

**User's choice:** All 4 rotations
**Notes:** None

---

## Preprocessing Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| All failures (Recommended) | Retry preprocessing on all three failure types: no_text_detected, only_noise_matches, and no_match_any_rotation. | Yes |
| no_text only | Only preprocess when OCR returned nothing at all. | |
| no_text + no_match | Preprocess on blank pages and pages with text but no 5-digit numbers. Skip noise-match pages. | |

**User's choice:** All failures
**Notes:** None

---

## Output Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Notes field (Recommended) | Add 'preprocessed' to the existing notes column. No schema change, keeps CSV simple. | Yes |
| New column | Add a 'preprocessed' boolean column to CSV. Cleaner filtering but changes schema. | |
| Both | New boolean column AND details in notes. Most informative but adds complexity. | |

**User's choice:** Notes field
**Notes:** None

---

## Normalization Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Keep whitelist (Recommended) | Keep digit whitelist for both passes. Tesseract forces digit output — normalization stays as safety net. QUAL-02 satisfied by whitelist. | Yes |
| Remove whitelist on retry | Drop the digit whitelist for the preprocessed retry pass. normalize_digits() becomes active. | |
| You decide | Claude picks the approach based on OCR best practices. | |

**User's choice:** Keep whitelist
**Notes:** User acknowledged that digit whitelist effectively covers QUAL-02.

---

## Sequential ID Validation (User-Initiated Scope Addition)

**Context:** User observed that IDs within a file are generally sequential, and 270-degree rotations frequently produce incorrect numbers that break the sequence. This is a strong post-hoc test for false positives.

### Scope Decision

| Option | Description | Selected |
|--------|-------------|----------|
| Fold into Phase 5 | Add sequential validation as a post-processing step in this phase. | Yes |
| Defer to future phase | Note it as a deferred idea. Phase 5 stays focused on preprocessing + normalization. | |

**User's choice:** Fold into Phase 5

### Action on Out-of-Sequence IDs

| Option | Description | Selected |
|--------|-------------|----------|
| Flag + confidence score | Keep the ID but add confidence indicator based on sequence deviation. | Yes |
| Flag in notes | Mark out-of-sequence ID in notes but no score. | |
| Drop and re-extract | Discard and retry with preprocessing or alternate rotation. | |

**User's choice:** Flag + confidence score

### Sequence Tolerance

| Option | Description | Selected |
|--------|-------------|----------|
| Trend-based (Recommended) | Check if IDs generally increase/decrease. Flag wild deviations from trend. | Yes |
| Strict consecutive | Expect IDs within +/-N of previous page. Tight tolerance. | |
| You decide | Claude picks appropriate tolerance. | |

**User's choice:** Trend-based

---

## Claude's Discretion

- OpenCV preprocessing parameters (kernel sizes, blur strength)
- Confidence score formula and thresholds for sequence deviation
- Handling of files with too few IDs to establish a reliable trend

## Deferred Ideas

None — discussion stayed within phase scope.
