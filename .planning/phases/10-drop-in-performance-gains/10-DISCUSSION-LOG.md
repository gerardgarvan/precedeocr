# Phase 10: Drop-in Performance Gains - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 10-drop-in-performance-gains
**Areas discussed:** PyMuPDF swap strategy, Benchmarking setup, Output configurability, Dependency transition

---

## PyMuPDF Swap Strategy

### Rendering Mode

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory pixmaps (Recommended) | page.get_pixmap() -> PIL Image directly. Fastest option since no disk I/O. Safe because workers process one page at a time. | ✓ |
| Disk-backed (like current) | Render pixmap -> save PNG to temp dir -> load as PIL Image. Safer for huge pages but loses speed. | |
| You decide | Claude picks based on benchmarking results and memory constraints. | |

**User's choice:** In-memory pixmaps
**Notes:** Maximizes PyMuPDF speed advantage. Memory bounded by one-page-at-a-time per worker.

### Fallback Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Error + skip (Recommended) | Log error, record as failed, move on. No fallback to pdf2image. Keeps codebase clean. | ✓ |
| Fallback to pdf2image | If PyMuPDF throws exception, retry with pdf2image/Poppler. Maximizes coverage but keeps two rendering paths. | |
| You decide | Claude picks based on how many PDFs fail during benchmark testing. | |

**User's choice:** Error + skip
**Notes:** Clean single rendering path. No dual-path complexity.

---

## Benchmarking Setup

### Corpus Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Random sample from real corpus (Recommended) | Pick PDFs randomly from actual 30K+ corpus. Most representative. | ✓ |
| First 1000 files found | Take first PDFs by directory order. Simpler but may not represent diversity. | |
| You decide | Claude selects sampling strategy. | |

**User's choice:** Random sample from real corpus
**Notes:** None

### Benchmark Script Location

| Option | Description | Selected |
|--------|-------------|----------|
| Separate script (Recommended) | Standalone benchmark.py that imports pipeline functions. Keeps main pipeline clean. | ✓ |
| Integrated --benchmark flag | Add benchmark mode to precede_ocr.py. Single entry point but adds complexity. | |
| You decide | Claude picks based on code organization. | |

**User's choice:** Separate script
**Notes:** None

### Accuracy Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Compare against v1.1 results (Recommended) | Run v1.1 baseline on sample, then optimized version. Compare IDs page-by-page. | |
| Manual spot-check | Visually inspect subset against actual PDFs. | |
| You decide | Claude designs validation approach. | |

**User's choice:** Free text — "change it to a 100 PDFS for a sample that's more time effective"
**Notes:** User reduced benchmark sample from 1000 to 100 PDFs for faster iteration. Compare-against-baseline approach confirmed (v1.1 results as ground truth).

---

## Output Configurability

### CLI Flags After Benchmarking

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-code winners (Recommended) | Set benchmarked-optimal DPI and worker count as defaults. Existing --workers flag stays. | ✓ |
| Add --dpi flag only | Hard-code worker count but add --dpi flag for experimentation. | |
| Add both --dpi and update --workers default | Expose both as CLI flags with benchmarked defaults. Maximum flexibility. | |

**User's choice:** Hard-code winners
**Notes:** Simplest approach. --workers flag already exists as escape hatch.

---

## Dependency Transition

### pdf2image / Poppler Removal

| Option | Description | Selected |
|--------|-------------|----------|
| Fully remove (Recommended) | Remove pdf2image from imports and requirements. Poppler no longer needed. Cleaner dependencies. | ✓ |
| Keep but unused | Leave pdf2image in requirements as optional dependency. Safety net for revert. | |
| You decide | Claude decides based on swap smoothness. | |

**User's choice:** Fully remove
**Notes:** None

### Poppler Concerns

| Option | Description | Selected |
|--------|-------------|----------|
| No concerns, remove it | PyMuPDF bundles MuPDF. No separate binary install needed. Simplifies setup. | ✓ |
| Keep Poppler docs | Remove from code but note replacement in README. | |

**User's choice:** No concerns, remove it
**Notes:** PyMuPDF simplifies installation compared to Poppler.

---

## Claude's Discretion

- PyMuPDF API details (matrix scaling, colorspace)
- Benchmark output format
- Random sampling implementation
- Test suite updates for rendering swap

## Deferred Ideas

None — discussion stayed within phase scope
