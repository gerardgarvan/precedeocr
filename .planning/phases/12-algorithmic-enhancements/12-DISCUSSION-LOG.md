# Phase 12: Algorithmic Enhancements - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-08
**Phase:** 12-algorithmic-enhancements
**Areas discussed:** Rotation statistics source, DPI fallback trigger, Batch rendering scope, Production validation

---

## Rotation Statistics Source

| Option | Description | Selected |
|--------|-------------|----------|
| Keep [90, 270, 0, 180] | Domain knowledge already puts 90 first. If benchmarks confirm 90 is dominant, current order is already optimal. | ✓ |
| Data-driven from checkpoint | Read checkpoint data at campaign start, compute distribution, reorder dynamically. | |
| Per-folder adaptive | Track rotation hits per folder, reorder for subsequent pages within each folder. | |

**User's choice:** Keep [90, 270, 0, 180] (Recommended)
**Notes:** Domain knowledge is strong. Validate via benchmark, and if data shows a different rotation is most common, reorder to match.

### Follow-up: Benchmark validation

| Option | Description | Selected |
|--------|-------------|----------|
| Benchmark confirms it | Add rotation distribution report to benchmark.py output. If 90 is >50%, document as validated. | ✓ |
| Skip validation | Accept domain knowledge as sufficient. | |

**User's choice:** Benchmark confirms it (Recommended)

### Follow-up: Reorder if data disagrees

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, reorder to match data | If data says 270 > 90, swap. Simple one-line change. Data-informed but still hard-coded. | ✓ |
| No, keep regardless | Current order designed to minimize false positives, not just speed. | |

**User's choice:** Yes, reorder to match data (Recommended)

---

## DPI Fallback Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| After all 8 OCR passes fail | DPI 300 retry only when both direct (4 rotations) and preprocessing (4 rotations) find no IDs. Last resort. | ✓ |
| After direct OCR fails | If 4 direct rotations fail at DPI 200, re-render at 300 before preprocessing. | |
| Skip DPI fallback entirely | DPI 200 already finds more IDs than 300. Keep fixed. | |

**User's choice:** After all 8 OCR passes fail (Recommended)

### Follow-up: Retry scope at DPI 300

| Option | Description | Selected |
|--------|-------------|----------|
| Full 8 passes at DPI 300 | Try everything at 300 since we're re-rendering anyway. | ✓ |
| 4 direct rotations only | Skip preprocessing at DPI 300 to save 4 OCR passes per failed page. | |

**User's choice:** Full 8 passes at DPI 300 (Recommended)

### Follow-up: 70% threshold validation

| Option | Description | Selected |
|--------|-------------|----------|
| Phase 10 benchmark is sufficient | 211/211 IDs at DPI 200 = 100%. Threshold easily exceeded. | ✓ |
| Formally re-validate on larger sample | Run check on 500+ PDFs to confirm at scale. | |

**User's choice:** Phase 10 benchmark is sufficient (Recommended)

### Follow-up: DPI fallback note flagging

| Option | Description | Selected |
|--------|-------------|----------|
| "dpi_fallback" note | Add to notes column. Consistent with "preprocessed" pattern. | ✓ |
| No special note | Don't track which DPI succeeded. | |

**User's choice:** "dpi_fallback" note (Recommended)

---

## Batch Rendering Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Render all, catch OOM | Render all pages upfront. On MemoryError, fall back to page-by-page for that PDF. | ✓ |
| Chunked rendering (10 pages) | Render 10 pages at a time. Bounds memory but adds chunking logic. | |
| Keep page-by-page | Don't batch-render. Current approach may already be fast enough. | |

**User's choice:** Render all, catch OOM (Recommended)

### Follow-up: OOM logging

| Option | Description | Selected |
|--------|-------------|----------|
| Log as warning | Print warning with filename and page count. | ✓ |
| Silent fallback | Just fall back quietly. | |

**User's choice:** Log as warning (Recommended)

### Follow-up: DPI 300 + batch interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Page-by-page for DPI 300 retry | Re-render just the individual failed page at 300 DPI. | ✓ |
| Re-batch whole PDF at 300 | Re-render all pages at DPI 300 if any page fails. | |

**User's choice:** Page-by-page for DPI 300 retry (Recommended)

---

## Production Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Haven't run yet, proceeding anyway | Skip production validation gate. Build Phase 12 first, then validate on full corpus. | ✓ |
| Ran it, still too slow | Full corpus took >7 days. Phase 12 needed. | |
| Ran it, but want more speed | Acceptable time but faster is better. | |

**User's choice:** Haven't run yet, proceeding anyway

### Follow-up: Benchmarking approach

| Option | Description | Selected |
|--------|-------------|----------|
| Benchmark first | Extend benchmark.py to test each enhancement independently. Follow Phases 10-11 pattern. | ✓ |
| Implement and measure combined | Build all enhancements, benchmark combined result. Faster but can't isolate impact. | |

**User's choice:** Benchmark first (Recommended)

### Follow-up: Stop gate policy

| Option | Description | Selected |
|--------|-------------|----------|
| Ship if any measurable improvement | Consistent with Phase 11 D-08. DPI fallback improves accuracy, not just speed. | ✓ |
| Revert if <1.2x combined | Follow roadmap stop condition strictly. | |

**User's choice:** Ship if any measurable improvement (Recommended)

---

## Claude's Discretion

- Order of benchmarking the three enhancements
- Benchmark output format and reporting details
- Batch rendering data structure (list vs generator)
- PyMuPDF Document lifecycle with batch rendering

## Deferred Ideas

None — discussion stayed within phase scope
