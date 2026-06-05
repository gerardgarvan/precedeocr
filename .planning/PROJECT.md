# Precede OCR — PDF ID Scanner & Mapper

## What This Is

A batch OCR pipeline that scans ~30,429 multi-page PDF files containing scanned/photographed images, extracts 5-digit numeric "Precede" IDs from each page, and produces structured output (CSV + JSON) mapping every ID to its source file and page number. The IDs are typically rotated ~90 degrees on the page and appear below the word "Precede" in cursive.

## Core Value

Reliably extract every Precede ID from every page across 30K+ PDFs so the user can look up which file and page any given ID lives in.

## Requirements

### Validated

- [x] Convert each PDF page to a high-DPI image for OCR — Validated in Phase 1: Foundation
- [x] Extract 5-digit numeric IDs from OCR output via regex — Validated in Phase 1: Foundation
- [x] Map each ID to its source filename and page number — Validated in Phase 1: Foundation
- [x] Output results as CSV (`filename, id, page, rotation_detected`) — Validated in Phase 1: Foundation
- [x] Handle ~90-degree rotated text (multi-rotation OCR strategy) — Validated in Phase 2: Rotation Handling
- [x] Recursively discover all `.pdf` files in a target directory — Validated in Phase 3: Scale
- [x] Output results as JSON (`{filename: {page: [ids], ...}}`) — Validated in Phase 3: Scale
- [x] Flag pages where no ID is found (not silently dropped) — Validated in Phase 3: Scale
- [x] Handle multiple IDs per page if present — Validated in Phase 3: Scale
- [x] Parallelize processing to handle 30,429 files efficiently — Validated in Phase 3: Scale

### Active

- [ ] Preprocess low-quality scans (grayscale, threshold, denoise) as fallback
- [ ] Handle OCR near-misses (O/0, I/1, S/5 confusion) with normalization

### Out of Scope

- GUI or web interface — CLI/script only, output to files
- Search CLI tool — user will search CSV/JSON manually or via Excel
- Cloud OCR services — using local Tesseract
- Rewriting or modifying the source PDFs
- Real-time/streaming processing — this is a one-shot batch job

## Context

- PDFs are scanned or photographed documents (rasterized pages, no embedded text layer)
- Each page contains a "Precede" label in cursive font with a 5-digit numeric ID below it
- The IDs are oriented at approximately 90 degrees from upright reading position
- Total corpus: ~30,429 PDF files, each with multiple pages
- The "Precede" cursive text above the ID could serve as an anchor/landmark for locating the ID region
- Running on Windows 10 with Tesseract OCR and Poppler already installed

## Constraints

- **Platform**: Windows 10 — all tooling must work on Windows
- **Dependencies**: Tesseract OCR + Poppler already installed; Python 3.x ecosystem
- **Scale**: ~30,429 PDFs with multiple pages each — must parallelize; single-threaded would be impractical
- **OCR quality**: Scanned images vary in quality; preprocessing pipeline needed for degraded scans
- **No manual intervention**: Must run fully automated once pointed at a directory

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + pytesseract + pdf2image | User's stated preference, well-suited ecosystem for OCR batch work | -- Pending |
| Multi-rotation OCR (0/90/180/270) | IDs are rotated ~90 degrees; trying all rotations with regex validation catches orientation variations | -- Pending |
| CSV + JSON dual output | CSV for Excel/manual inspection, JSON for programmatic lookup | -- Pending |
| Local Tesseract (no cloud OCR) | Dependencies already installed, no API costs at scale, simpler pipeline | -- Pending |
| Multiprocessing parallelization | 30K+ files makes serial processing impractical | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-05 after Phase 3 completion*
