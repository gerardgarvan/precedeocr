# Phase 15: Error Investigation & Reporting - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 15-error-investigation-reporting
**Areas discussed:** Investigation depth, Fix vs Report scope, Input data source, Output deliverables

---

## Investigation Depth

### No-match page diagnosis approach

| Option | Description | Selected |
|--------|-------------|----------|
| Re-render & re-OCR | Re-open each no-match PDF, re-render the specific page, run OCR again with debug output to capture exactly what Tesseract sees. Gives definitive diagnosis. | ✓ |
| Metadata-only analysis | Analyze existing result data + check file properties. No re-rendering. Faster, simpler, but less definitive categorization. | |
| You decide | Claude picks the approach that best satisfies ERR-02 requirements. | |

**User's choice:** Re-render & re-OCR
**Notes:** User wants definitive diagnosis, not inference from metadata.

### Failed file re-verification

| Option | Description | Selected |
|--------|-------------|----------|
| Re-verify each file | Check if files exist, try to open with PyMuPDF, report current status. | |
| Report from existing data | Just categorize from the stored error messages. No re-processing. | |
| You decide | Claude picks based on what makes the report most useful. | ✓ |

**User's choice:** You decide
**Notes:** Claude discretion — recommended to re-verify since it's cheap and useful.

### Page image saving

| Option | Description | Selected |
|--------|-------------|----------|
| Save images | Save each no-match page as PNG in output subfolder for manual inspection. | |
| No images | Just report OCR text and diagnosis in markdown. No image files. | |
| You decide | Claude picks based on what's most useful for investigation. | ✓ |

**User's choice:** You decide
**Notes:** Claude discretion.

### Diagnosis thoroughness

| Option | Description | Selected |
|--------|-------------|----------|
| Full debug OCR | Run all 8 OCR passes with raw text capture per page. Most diagnostic but slower. | |
| Quick scan | Render page, check if blank, then run single OCR pass to capture raw text. Faster, good enough for categorization. | ✓ |
| You decide | Claude picks the depth that satisfies ERR-02. | |

**User's choice:** Quick scan
**Notes:** User prefers speed over exhaustive diagnosis for 59 pages.

---

## Fix vs Report Scope

### Apply fixes or report only

| Option | Description | Selected |
|--------|-------------|----------|
| Report only | Produces reports and diagnostics but does NOT apply fixes. Results.csv untouched. Safest approach. | ✓ |
| Report + fix fixable | Applies easy fixes, writes updated results alongside originals. More ambitious. | |
| You decide | Claude picks based on ERR-03 requirements and conservation principle. | |

**User's choice:** Report only
**Notes:** Consistent with project's conservative/preservation approach.

### Actionable recommendations

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include commands | Report includes copy-paste CLI commands for each fixable category. Actionable immediately. | ✓ |
| Just describe fixes | Describes what could be fixed and why, but no runnable commands. | |
| You decide | Claude picks. | |

**User's choice:** Yes, include commands
**Notes:** User wants actionable output they can immediately run.

---

## Input Data Source

### Primary data source

| Option | Description | Selected |
|--------|-------------|----------|
| Scan results CSV | Read from results.csv. Add scan_csv positional arg like cmd_lookup. Consistent pattern. | ✓ |
| Checkpoint JSON | Read from .checkpoint.json directly. Richer data but may not exist after completion. | |
| Both (CSV + PDF dir) | Take results CSV for analysis AND PDF directory for re-rendering. Two inputs. | |

**User's choice:** Scan results CSV
**Notes:** Consistent with cmd_lookup pattern from Phase 14.

### PDF path resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Infer from CSV | Resolve paths from CSV filename column. No extra arg needed if paths valid. | |
| Add --pdf-dir arg | Optional argument to specify root directory of source PDFs. Explicit. | |
| You decide | Claude picks approach that works with existing CSV data. | ✓ |

**User's choice:** You decide
**Notes:** Claude discretion — will examine CSV data format to pick best approach.

---

## Output Deliverables

### Output files beyond report

| Option | Description | Selected |
|--------|-------------|----------|
| Report + no_match CSV | quality_report.md plus no_match_pages.csv. Two files. | |
| Report + multiple CSVs | Report plus no_match_pages.csv and failed_files.csv. Three files. | |
| You decide | Claude picks based on success criteria and usefulness. | ✓ |

**User's choice:** You decide
**Notes:** Claude discretion — no_match_pages.csv is mandatory per SC-4, additional CSVs at Claude's judgment.

### Report detail level

| Option | Description | Selected |
|--------|-------------|----------|
| Summary + tables | Category counts, findings, and table of every failed/no-match item. Scannable. | |
| Full narrative | Same tables plus narrative explaining patterns and root cause hypotheses. Forensic style. | |
| You decide | Claude picks appropriate level of detail. | ✓ |

**User's choice:** You decide
**Notes:** Claude discretion on report verbosity.

---

## Claude's Discretion

- Failed file re-verification approach
- Page image saving (yes/no)
- PDF path resolution strategy
- Additional CSV exports beyond no_match_pages.csv
- Report detail level

## Deferred Ideas

None — discussion stayed within phase scope.
