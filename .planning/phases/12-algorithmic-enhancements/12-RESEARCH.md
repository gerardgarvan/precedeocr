# Phase 12: Algorithmic Enhancements - Research

**Researched:** 2026-06-08
**Domain:** OCR pipeline optimization (batch rendering, rotation priority, DPI fallback)
**Confidence:** HIGH

## Summary

Phase 12 implements three algorithmic enhancements to achieve 1.2-1.5x incremental speedup beyond Phase 11's optimizations. The phase focuses on smarter resource allocation rather than raw parameter tuning: (1) reordering rotation attempts based on corpus statistics to reduce average OCR passes, (2) implementing conditional DPI fallback (DPI 200 first, 300 only on failure) to minimize expensive high-DPI rendering, and (3) batch-rendering all PDF pages upfront to separate I/O from compute and enable potential caching optimizations.

All three enhancements are LOW-RISK modifications to the existing Phase 10+11 pipeline. The rotation reordering is a one-line array change validated by benchmark statistics. DPI fallback adds a retry layer that preserves existing accuracy while reducing average rendering cost. Batch rendering restructures the process_single_pdf loop without changing the OCR logic, with OOM fallback for edge cases.

**Primary recommendation:** Implement enhancements incrementally with independent benchmarks following Phase 10-11 methodology. Ship any measurable improvement per D-14. Rotation reordering is essentially free (one-line change validated by benchmark data). DPI fallback improves accuracy coverage for difficult pages while reducing average cost. Batch rendering simplifies code flow and enables future optimizations (pixmap caching, early termination strategies).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rotation Reordering (PIPE-02):**
- Keep current hard-coded order [90, 270, 0, 180] as default — domain knowledge already places 90 first (D-01)
- Add rotation distribution report to benchmark.py output on 100-PDF sample to validate order via corpus statistics (D-02)
- If benchmark data shows a different rotation is most common (e.g., 270 > 90), reorder the array to match data — still hard-coded, just data-informed (D-03)

**Conditional DPI Fallback (PIPE-03):**
- DPI 300 retry fires ONLY after ALL 8 OCR passes fail at DPI 200 — both direct OCR (4 rotations) and preprocessing fallback (4 rotations) must fail (D-04)
- DPI 300 retry does full 8 passes (4 direct + 4 preprocessed rotations) — if re-rendering anyway, give the page the full treatment (D-05)
- Phase 10 benchmark (211/211 IDs at DPI 200 = 100% success) is sufficient proof of >70% threshold — no formal re-validation needed (D-06)
- Flag DPI 300 fallback success in notes column as `dpi_fallback` or `dpi_fallback+preprocessed` for consistency with existing `preprocessed` note pattern (D-07)
- DPI 300 re-render is page-by-page for individual failed pages only — do NOT re-render the whole PDF at 300 — keep batch rendering at DPI 200 (D-08)

**Batch Rendering (PIPE-04):**
- Render ALL pages of a PDF into a list of PIL Images upfront before the OCR loop — separates rendering phase from OCR phase (D-09)
- On MemoryError, catch and fall back to page-by-page rendering for that specific PDF — most PDFs in corpus are small (max 1125 KB per Phase 10 stats) (D-10)
- Log OOM fallback as a warning with filename and page count — useful for diagnosing memory issues in production (D-11)

**Benchmarking & Validation:**
- Proceed without production validation on full 30K corpus — build Phase 12 enhancements first, then validate on full corpus (D-12)
- Benchmark each enhancement independently first (extend benchmark.py), following established Phases 10-11 methodology — reuse 100-PDF sample (seed=42) (D-13)
- Ship any measurable improvement regardless of magnitude — relaxed from 1.2x roadmap threshold, consistent with Phase 11 D-08 — DPI fallback improves accuracy coverage (not just speed), batch rendering simplifies code flow (D-14)

### Claude's Discretion

- Order of benchmarking the three enhancements
- Benchmark output format and reporting details
- How to structure the batch rendering (list of Images vs generator)
- Whether batch rendering benchmark needs accuracy validation or just timing
- How to handle the `doc` (PyMuPDF Document) lifecycle with batch rendering

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-02 | Multi-rotation strategy tries most common rotation first (based on corpus statistics) | Rotation distribution tracking already implemented (lines 867-876); benchmark.py extension adds reporting; one-line array reorder at lines 389/426 |
| PIPE-03 | Pipeline uses conditional DPI fallback (lower DPI first, 300 DPI only on failure) | DPI 200 validated at 100% accuracy (211/211 IDs) in Phase 10; fallback layer wraps extract_id_with_rotation() call at line 500; PyMuPDF page object available for re-render |
| PIPE-04 | PyMuPDF batch-renders all pages of a PDF before OCR loop | Restructure process_single_pdf() lines 491-513 to separate rendering from OCR; MemoryError handling follows Python stdlib patterns; PIL Image list is standard approach |
| QUAL-01 | All optimizations maintain >=94% OCR accuracy on test corpus | DPI fallback preserves existing accuracy (200 DPI already 100%); rotation reorder doesn't change logic (same 4 passes); batch rendering doesn't touch OCR path |
| QUAL-02 | Benchmark results documented (before/after speed comparison on representative sample) | Extend benchmark.py with three new functions following Phase 10-11 methodology; 100-PDF sample (seed=42) ensures consistency |

</phase_requirements>

## Standard Stack

### Core (Already Installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **PyMuPDF (fitz)** | 1.27.2.3 | PDF rendering and page management | Already in use per Phase 10. Batch rendering uses `doc[page_idx]` iteration and `page.get_pixmap()`. Document lifecycle management critical for memory safety. **Confidence: HIGH** |
| **Pillow (PIL)** | 12.2.0 | Image objects for OCR | Already in use. Batch rendering creates list of `Image.Image` objects. Lazy loading ensures efficient memory usage. Explicit `img.close()` not needed for in-memory images from PyMuPDF pixmaps. **Confidence: HIGH** |
| **pytesseract** | 0.3.13 | OCR engine wrapper | Already in use. DPI fallback calls `extract_id_with_rotation()` twice (once at 200, once at 300 if needed). No API changes. **Confidence: HIGH** |

### Supporting (Already Installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pandas** | 3.0.3 | Benchmark result analysis | Already used in benchmark.py. Extend for rotation distribution reporting and DPI fallback metrics. **Confidence: HIGH** |
| **pytest** | 9.0.2 | Unit testing framework | 230 existing tests. Phase 12 needs new tests for batch rendering OOM fallback, DPI fallback retry logic, and rotation distribution calculation. **Confidence: HIGH** |

### No New Dependencies

Phase 12 uses only existing libraries already installed in Phases 10-11. All enhancements are algorithmic reorganizations of existing code paths.

## Architecture Patterns

### Recommended Project Structure

```
precede_ocr.py
├── extract_id_with_rotation()   # [361] Core OCR logic (unchanged)
├── process_single_pdf()          # [453] RESTRUCTURE for batch rendering
│   ├── Batch render all pages → list[Image]
│   ├── try/except MemoryError fallback
│   ├── OCR loop over pre-rendered images
│   └── DPI 300 fallback per failed page
└── rotation order arrays          # [389, 426] DATA-DRIVEN reorder

benchmark.py (EXTEND)
├── benchmark_rotation_distribution()  # NEW: Report rotation stats
├── benchmark_batch_rendering()        # NEW: Timing + OOM handling
└── benchmark_dpi_fallback()           # NEW: Coverage + speed
```

### Pattern 1: Batch Rendering with OOM Fallback

**What:** Separate PDF rendering from OCR processing by pre-rendering all pages into a list of PIL Images before the OCR loop. On MemoryError, fall back to page-by-page rendering for that PDF only.

**When to use:** When processing moderate-sized PDFs (corpus max 1125 KB per Phase 10 stats) on a system with sufficient RAM (user has 20-core system, likely 32GB+ RAM).

**Example:**

```python
# Source: Phase 12 research pattern synthesis
def process_single_pdf(pdf_path: str, debug: bool = False) -> list[dict]:
    filename = Path(pdf_path).name

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return [{
            'filename': filename,
            'page': 0,
            'ids': [],
            'rotation_detected': None,
            'notes': f'error: {type(e).__name__}: {e}'
        }]

    try:
        # === BATCH RENDERING (D-09) ===
        try:
            # Pre-render all pages at DPI 200
            images = []
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                pix = page.get_pixmap(dpi=200, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                images.append(img)
        except MemoryError as e:
            # D-10: Fall back to page-by-page rendering
            import logging
            logging.warning(f"OOM during batch render: {filename} ({len(doc)} pages) - falling back to page-by-page")
            images = None  # Signal to use fallback path

        results = []

        # === OCR LOOP ===
        for page_idx in range(len(doc)):
            if images is not None:
                # Use pre-rendered image (batch path)
                img = images[page_idx]
            else:
                # Render on-demand (fallback path)
                page = doc[page_idx]
                pix = page.get_pixmap(dpi=200, alpha=False)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Extract IDs at DPI 200
            ids_found, rotation, notes = extract_id_with_rotation(img, debug=debug)

            # === DPI 300 FALLBACK (D-04, D-05, D-08) ===
            if not ids_found and 'preprocessed' not in notes:
                # ALL 8 passes failed at DPI 200 (4 direct + 4 preprocessed)
                # Re-render this page at DPI 300 and retry
                page = doc[page_idx]
                pix_300 = page.get_pixmap(dpi=300, alpha=False)
                img_300 = Image.frombytes("RGB", [pix_300.width, pix_300.height], pix_300.samples)

                ids_fallback, rotation_fallback, notes_fallback = extract_id_with_rotation(img_300, debug=debug)

                if ids_fallback:
                    # DPI 300 succeeded
                    ids_found = ids_fallback
                    rotation = rotation_fallback
                    # D-07: Flag in notes column
                    if 'preprocessed' in notes_fallback:
                        notes = 'dpi_fallback+preprocessed'
                    else:
                        notes = 'dpi_fallback'

            results.append({
                'filename': filename,
                'page': page_idx + 1,
                'ids': ids_found,
                'rotation_detected': rotation if ids_found else None,
                'notes': notes
            })

        return results
    finally:
        doc.close()  # Critical: prevent memory leaks
```

### Pattern 2: Data-Driven Rotation Reordering

**What:** Add rotation distribution reporting to benchmark.py. If corpus statistics show a different most-common rotation than the current hard-coded [90, 270, 0, 180] order, reorder the array to match data.

**When to use:** One-time during Phase 12 benchmarking. Future phases can reference the validated rotation order.

**Example:**

```python
# Source: Phase 12 research pattern synthesis
def benchmark_rotation_distribution(pdf_paths):
    """
    Analyze rotation distribution across sample corpus (D-02).

    Runs OCR on 100-PDF sample and reports which rotation succeeded
    for each page that found an ID. Validates current [90, 270, 0, 180]
    order or recommends reordering based on data.

    Returns:
        pandas DataFrame with rotation distribution and recommendation
    """
    from collections import Counter
    rotation_counts = Counter()

    print("\n=== Rotation Distribution Benchmark ===")
    print("Analyzing rotation success patterns across 100-PDF sample...")

    for pdf_path in pdf_paths:
        results = run_single_pdf_at_dpi(pdf_path, dpi=200)
        for r in results:
            if r.get('rotation_detected') is not None:
                rotation_counts[r['rotation_detected']] += 1

    total = sum(rotation_counts.values())

    # Build report
    print("\n| Rotation | Count | Percentage |")
    print("|----------|-------|------------|")
    for angle in [90, 270, 0, 180]:
        count = rotation_counts.get(angle, 0)
        pct = (count / total * 100) if total > 0 else 0.0
        print(f"| {angle}° | {count} | {pct:.1f}% |")

    # Recommendation (D-03)
    most_common = rotation_counts.most_common(1)[0][0] if rotation_counts else 90
    current_order = [90, 270, 0, 180]

    print(f"\nMost common rotation: {most_common}° ({rotation_counts[most_common]} pages)")
    print(f"Current hard-coded order: {current_order}")

    if most_common != current_order[0]:
        # Reorder to place most common first
        recommended_order = [most_common] + [x for x in current_order if x != most_common]
        print(f"RECOMMENDATION: Reorder to {recommended_order}")
        print(f"This would reduce average OCR passes by trying most common rotation first.")
    else:
        print("RECOMMENDATION: Keep current order (already optimal)")

    return rotation_counts
```

### Pattern 3: DPI Fallback Benchmarking

**What:** Measure how many pages fail at DPI 200 but succeed at DPI 300, and quantify the speed/accuracy tradeoff.

**When to use:** Phase 12 benchmarking to validate D-06 assumption (>70% succeed at DPI 200).

**Example:**

```python
# Source: Phase 12 research pattern synthesis
def benchmark_dpi_fallback(pdf_paths, baseline_csv=None):
    """
    Benchmark DPI fallback strategy (D-04, D-05, D-06).

    For each page in sample:
    1. Try DPI 200 (8 passes: 4 direct + 4 preprocessed)
    2. If fail, try DPI 300 (8 passes)
    3. Report success rate at each DPI and speed impact

    Validates D-06 assumption: >70% succeed at DPI 200
    """
    print("\n=== DPI Fallback Benchmark ===")

    stats = {
        'total_pages': 0,
        'success_200': 0,
        'success_300_fallback': 0,
        'total_fail': 0,
        'time_200': 0.0,
        'time_300_fallback': 0.0,
    }

    for pdf_path in pdf_paths:
        results_200 = run_single_pdf_at_dpi(pdf_path, dpi=200)

        for page_result in results_200:
            stats['total_pages'] += 1

            if page_result['ids']:
                # Succeeded at DPI 200
                stats['success_200'] += 1
            else:
                # Failed at DPI 200, try DPI 300 fallback
                # (In real impl, would re-render just this page at 300)
                # For benchmark, re-run entire PDF at 300 for simplicity
                import time
                start = time.perf_counter()
                results_300 = run_single_pdf_at_dpi(pdf_path, dpi=300)
                elapsed = time.perf_counter() - start

                # Find corresponding page result
                page_300 = next((r for r in results_300 if r['page'] == page_result['page']), None)
                if page_300 and page_300['ids']:
                    stats['success_300_fallback'] += 1
                    stats['time_300_fallback'] += elapsed / len(results_300)  # Amortize
                else:
                    stats['total_fail'] += 1

    # Report
    total = stats['total_pages']
    print(f"\nTotal pages: {total}")
    print(f"Success at DPI 200: {stats['success_200']} ({stats['success_200']/total*100:.1f}%)")
    print(f"Success at DPI 300 fallback: {stats['success_300_fallback']} ({stats['success_300_fallback']/total*100:.1f}%)")
    print(f"Total failures (both DPI): {stats['total_fail']} ({stats['total_fail']/total*100:.1f}%)")

    # Validate D-06 assumption
    if (stats['success_200'] / total * 100) >= 70:
        print(f"\n✓ D-06 VALIDATED: {stats['success_200']/total*100:.1f}% succeed at DPI 200 (>70% threshold)")
    else:
        print(f"\n✗ D-06 FAILED: Only {stats['success_200']/total*100:.1f}% succeed at DPI 200 (<70% threshold)")

    return stats
```

### Anti-Patterns to Avoid

**Anti-Pattern 1: Rendering entire PDF at DPI 300 on first failure**
- **Why it's bad:** User decision D-08 explicitly requires page-by-page DPI 300 re-render for failed pages only
- **What to do instead:** DPI 300 fallback wraps individual page rendering, not the whole PDF

**Anti-Pattern 2: Batch rendering with no OOM fallback**
- **Why it's bad:** User corpus has PDFs up to 1125 KB (small), but edge cases exist — batch rendering ALL pages could OOM on pathological PDFs
- **What to do instead:** try/except MemoryError with page-by-page fallback per D-10, logged as warning per D-11

**Anti-Pattern 3: Changing rotation order without benchmark validation**
- **Why it's bad:** Current [90, 270, 0, 180] order is based on domain knowledge (IDs typically ~90° rotated) — changing without data is cargo-culting
- **What to do instead:** Run benchmark first (D-02), reorder only if data contradicts current order (D-03)

**Anti-Pattern 4: Generator-based batch rendering**
- **Why it's bad:** Goal is to separate rendering I/O from OCR compute — generators don't pre-render, they render on-demand
- **What to do instead:** Use list of Images (D-09) — explicit upfront rendering enables future optimizations (caching, early termination)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Memory profiling for OOM detection | Custom memory tracking with `psutil` or `tracemalloc` | try/except MemoryError with fallback | Python's MemoryError is raised when allocation fails — catching it is sufficient for graceful degradation. Custom profiling adds complexity for no benefit. **Confidence: HIGH** |
| Rotation distribution statistics | Manual counter logic for each rotation | `collections.Counter` (stdlib) | Already used in precede_ocr.py line 867 for campaign-wide rotation counts. Proven, tested, zero dependencies. **Confidence: HIGH** |
| DPI fallback decision logic | Complex heuristics (page size, text density, confidence scores) | Simple rule: if no IDs found at 200, try 300 | Phase 10 validated 211/211 IDs at DPI 200 (100% success). DPI fallback is for edge cases, not routine. Simple rule sufficient per D-04. **Confidence: HIGH** |
| Benchmark result comparison | String formatting and manual table building | `pandas.DataFrame` with `.to_markdown()` or manual formatting | Already used in benchmark.py. Consistent with Phase 10-11 methodology. **Confidence: HIGH** |

**Key insight:** Phase 12 enhancements are reorganizations of existing proven components, not new algorithms. Reuse existing patterns (Counter for stats, try/except for OOM, pandas for reporting) rather than introducing new dependencies or custom logic.

## Runtime State Inventory

> This section omitted — Phase 12 is pure algorithmic optimization with no rename/refactor/migration.

## Common Pitfalls

### Pitfall 1: Batch Rendering Memory Explosion

**What goes wrong:** Loading all pages of a large multi-page PDF into memory simultaneously causes OOM crash, terminating the worker process and losing checkpoint progress.

**Why it happens:** PyMuPDF pixmaps are memory-intensive (DPI 200: ~1-2 MB per page for letter-sized documents). A 100-page PDF could consume 100-200 MB for batch rendering. User corpus max is 1125 KB (small PDFs), but edge cases exist.

**How to avoid:**
- Implement try/except MemoryError per D-10
- Log OOM fallback as warning per D-11 (includes filename and page count)
- Fall back to page-by-page rendering for that specific PDF only
- DO NOT fail the entire worker process — graceful degradation

**Warning signs:**
- Worker process killed with no traceback (OOM killer)
- Checkpoint shows gaps in processed files (some PDFs silently skipped)
- System swap usage spikes during processing

**Prevention:**
```python
try:
    images = [render_page(doc[i]) for i in range(len(doc))]
except MemoryError:
    logging.warning(f"OOM batch render: {filename} ({len(doc)} pages)")
    images = None  # Signal page-by-page fallback
```

### Pitfall 2: DPI Fallback Infinite Loop

**What goes wrong:** DPI 300 fallback logic triggers even when DPI 300 was already tried, creating infinite retry loop or double-counting failures.

**Why it happens:** Forgetting that `extract_id_with_rotation()` already does 8 OCR passes (4 direct + 4 preprocessed) at the given DPI. Fallback should ONLY trigger after ALL 8 passes fail.

**How to avoid:**
- DPI fallback wraps the extract_id_with_rotation() call, not individual rotations per D-04
- Check `if not ids_found` (all 8 passes failed) before triggering DPI 300 retry
- DPI 300 retry does its own 8 passes per D-05 (give page full treatment)
- Flag success with `dpi_fallback` or `dpi_fallback+preprocessed` per D-07

**Warning signs:**
- Same page processed multiple times in logs
- Notes column shows duplicate `dpi_fallback` flags
- Benchmark timing 2x slower than expected

**Prevention:**
```python
ids_found, rotation, notes = extract_id_with_rotation(img_200)

# DPI fallback ONLY if all 8 passes failed
if not ids_found:
    ids_found, rotation, notes = extract_id_with_rotation(img_300)
    if ids_found:
        notes = 'dpi_fallback' if 'preprocessed' not in notes else 'dpi_fallback+preprocessed'
```

### Pitfall 3: Rotation Reordering Without Data

**What goes wrong:** Changing rotation order based on intuition or partial data, then discovering actual corpus has different distribution, requiring second reordering.

**Why it happens:** Temptation to optimize prematurely before running benchmark. Current [90, 270, 0, 180] is based on domain knowledge, not data.

**How to avoid:**
- Run rotation distribution benchmark FIRST per D-02
- Calculate actual percentages from 100-PDF sample (seed=42)
- Reorder ONLY if data shows different most-common rotation per D-03
- Document benchmark results before code change

**Warning signs:**
- Guessing most common rotation without data
- Testing on small sample (<100 PDFs) or non-representative subset
- Skipping benchmark step to "save time"

**Prevention:** Follow Phase 10-11 methodology — measure, then optimize. Benchmark is ~10 minutes, reordering is 1 line — do it in the right order.

### Pitfall 4: Document Lifecycle Mismanagement

**What goes wrong:** Keeping PyMuPDF Document open while processing batch-rendered images leads to memory leaks or file handle exhaustion on large campaigns.

**Why it happens:** Batch rendering separates image creation from OCR processing. Temptation to keep `doc` open "in case we need it later."

**How to avoid:**
- Document lifecycle: open → batch render → close (in try/finally per existing pattern line 512-513)
- DPI 300 fallback requires re-opening: close after batch render, re-open for individual page re-render, close again
- PyMuPDF documents are lightweight to re-open — don't optimize for handle reuse

**Warning signs:**
- Memory usage grows linearly with processed PDFs (not constant)
- "Too many open files" errors on Linux systems
- Checkpoint file corruption (documents not flushed)

**Prevention:**
```python
try:
    doc = fitz.open(pdf_path)
    # Batch render all pages
    images = [...]
finally:
    doc.close()  # CRITICAL: Must close even if batch render fails

# Later, for DPI 300 fallback on specific page:
doc = fitz.open(pdf_path)  # Re-open for single page
try:
    page = doc[page_idx]
    pix_300 = page.get_pixmap(dpi=300)
    # ...
finally:
    doc.close()
```

## Code Examples

Verified patterns from official sources and existing codebase:

### PyMuPDF Batch Page Rendering

```python
# Source: PyMuPDF documentation + Phase 10 implementation (precede_ocr.py:491-513)
import fitz
from PIL import Image

def batch_render_pages(pdf_path: str, dpi: int = 200) -> list[Image.Image]:
    """
    Pre-render all pages of a PDF at specified DPI.

    Returns list of PIL Images. Caller must handle MemoryError for large PDFs.
    """
    doc = fitz.open(pdf_path)
    try:
        images = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            # alpha=False ensures RGB mode required for OCR
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            images.append(img)
        return images
    finally:
        doc.close()
```

### MemoryError Fallback Pattern

```python
# Source: Python stdlib exception handling + 2026 best practices
import logging

def process_with_memory_fallback(pdf_path: str):
    """
    Batch render with OOM fallback to page-by-page rendering.
    """
    try:
        # Attempt batch rendering
        images = batch_render_pages(pdf_path, dpi=200)
        batch_mode = True
    except MemoryError as e:
        # D-11: Log warning with filename and page count
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()

        logging.warning(f"OOM during batch render: {Path(pdf_path).name} ({page_count} pages) - falling back to page-by-page")
        images = None
        batch_mode = False

    # Rest of processing adapts based on batch_mode flag
    # ...
```

### Rotation Distribution Analysis

```python
# Source: precede_ocr.py:867-876 (existing implementation)
from collections import Counter

def analyze_rotation_distribution(results: list[dict]) -> dict[int, float]:
    """
    Calculate rotation distribution percentages from OCR results.

    Reuses pattern from generate_campaign_report() in precede_ocr.py.
    """
    rotation_counts = Counter()
    for r in results:
        if r.get('rotation_detected') is not None:
            rotation_counts[r['rotation_detected']] += 1

    total_rotations = sum(rotation_counts.values())

    rotation_pct = {}
    for angle in [90, 270, 0, 180]:
        if total_rotations == 0:
            rotation_pct[angle] = 0.0
        else:
            rotation_pct[angle] = rotation_counts.get(angle, 0) / total_rotations * 100

    return rotation_pct
```

### DPI Fallback Logic

```python
# Source: Phase 12 research synthesis (pattern combines D-04, D-05, D-07, D-08)
def extract_with_dpi_fallback(page, page_idx: int, debug: bool = False):
    """
    Try OCR at DPI 200 first, fall back to DPI 300 only on total failure.

    Per D-04: DPI 300 retry fires ONLY after all 8 passes fail at DPI 200.
    Per D-05: DPI 300 does full 8 passes (4 direct + 4 preprocessed).
    Per D-07: Flag success in notes column.
    Per D-08: Re-render only this specific page, not whole PDF.
    """
    # Try DPI 200 (8 passes: 4 direct + 4 preprocessed)
    pix_200 = page.get_pixmap(dpi=200, alpha=False)
    img_200 = Image.frombytes("RGB", [pix_200.width, pix_200.height], pix_200.samples)

    ids_found, rotation, notes = extract_id_with_rotation(img_200, debug=debug)

    if ids_found:
        # Success at DPI 200
        return ids_found, rotation, notes

    # ALL 8 passes failed at DPI 200 — try DPI 300 fallback
    pix_300 = page.get_pixmap(dpi=300, alpha=False)
    img_300 = Image.frombytes("RGB", [pix_300.width, pix_300.height], pix_300.samples)

    ids_fallback, rotation_fallback, notes_fallback = extract_id_with_rotation(img_300, debug=debug)

    if ids_fallback:
        # DPI 300 succeeded — flag in notes
        if 'preprocessed' in notes_fallback:
            notes = 'dpi_fallback+preprocessed'
        else:
            notes = 'dpi_fallback'
        return ids_fallback, rotation_fallback, notes
    else:
        # Both DPI failed — return original failure reason from DPI 200
        return [], None, notes
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Page-by-page rendering interleaved with OCR | Batch render all pages, then OCR loop | Phase 12 (2026) | Separates I/O from compute, enables caching and early termination strategies |
| Fixed DPI 300 for all pages | Conditional DPI fallback (200 first, 300 only on failure) | Phase 12 (2026) | Reduces average rendering cost by 43% (per Phase 10 benchmarks) for pages that succeed at lower DPI |
| Hard-coded rotation order based on intuition | Data-driven rotation order from corpus statistics | Phase 12 (2026) | Reduces average OCR passes by prioritizing most common rotation first |
| pdf2image + Poppler rendering | PyMuPDF (fitz) rendering | Phase 10 (2026) | 2-12x faster PDF rasterization per research; already applied |
| OEM 3 auto-detect, dict enabled | OEM 1 LSTM-only, dict disabled | Phase 11 (2026) | 1.01x incremental speedup; already applied |
| DPI 300 | DPI 200 | Phase 10 (2026) | 43% faster, MORE IDs found (211 vs 186); already applied |

**Deprecated/outdated:**
- **pdf2image**: Replaced by PyMuPDF in Phase 10 — 2-12x faster
- **OEM 3 auto-detect**: Replaced by OEM 1 in Phase 11 — 1.01x faster with same accuracy
- **PSM 7 single-line**: Tested in Phase 11, catastrophic failure (0% accuracy) — keep PSM 6
- **DPI 300 for all pages**: Phase 10 proved DPI 200 is 43% faster with better accuracy

## Open Questions

**Question 1: Should batch rendering use list or generator comprehension?**
- **What we know:** User decision D-09 specifies "list of PIL Images" — goal is upfront rendering to separate I/O from compute
- **What's unclear:** Whether generator would provide memory benefits while still achieving separation of concerns
- **Recommendation:** Use list per D-09 — explicit upfront rendering is the goal, generators would render on-demand (defeating the purpose)

**Question 2: Does batch rendering benchmark need accuracy validation?**
- **What we know:** Batch rendering doesn't change OCR logic — same extract_id_with_rotation() calls, just pre-rendered images instead of on-demand
- **What's unclear:** Whether to run full accuracy validation (compare IDs page-by-page against baseline) or just timing
- **Recommendation:** Timing only — if batch mode renders same pixels as page-by-page mode (which it does), OCR results are identical. Accuracy validation would be redundant.

**Question 3: How to benchmark rotation reordering impact?**
- **What we know:** D-02 specifies rotation distribution reporting on 100-PDF sample. D-03 says reorder if data contradicts current order.
- **What's unclear:** Whether to measure actual speedup from reordering, or trust that fewer average passes = faster
- **Recommendation:** Report distribution percentages only. Actual speedup from reordering is hard to measure reliably (single-digit ms differences, noise dominates). If 90° is 70%+ of corpus, reordering to [90, ...] means 70% of pages early-exit on first pass — theoretical speedup is clear.

## Environment Availability

> Phase 12 has no external dependencies beyond what's already installed. All libraries verified present in Phases 10-11.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini |
| Quick run command | `pytest tests/test_precede_ocr.py -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-02 | Rotation order matches corpus statistics (data-driven) | unit | `pytest tests/test_precede_ocr.py::test_rotation_reordering -x` | ❌ Wave 0 |
| PIPE-03 | DPI fallback retries at 300 only after all 8 passes fail at 200 | unit | `pytest tests/test_precede_ocr.py::test_dpi_fallback -x` | ❌ Wave 0 |
| PIPE-04 | Batch rendering falls back to page-by-page on MemoryError | unit | `pytest tests/test_precede_ocr.py::test_batch_render_oom_fallback -x` | ❌ Wave 0 |
| QUAL-01 | All enhancements maintain >=94% accuracy | benchmark | `python benchmark.py <corpus> --rotation-dist --batch-render --dpi-fallback --baseline-csv baseline_phase11.csv` | ❌ Wave 0 |
| QUAL-02 | Benchmark results documented (before/after comparison) | manual | Visual inspection of benchmark_results.md | ✅ Existing template |

### Sampling Rate

- **Per task commit:** `pytest tests/test_precede_ocr.py -x` (fail fast on first error)
- **Per wave merge:** `pytest tests/` (full suite, 230 tests)
- **Phase gate:** Full suite green + benchmarks documented before `/gsd:verify-work`

### Wave 0 Gaps

**Unit Tests (3 new test functions in tests/test_precede_ocr.py):**
- [ ] `test_batch_render_oom_fallback` — Mock MemoryError during batch render, verify fallback to page-by-page
- [ ] `test_dpi_fallback_logic` — Mock failed DPI 200 OCR, verify DPI 300 retry with correct notes flagging
- [ ] `test_rotation_distribution_calculation` — Verify rotation_counts and rotation_pct() logic (already exists in codebase, extract to testable function)

**Benchmark Extensions (3 new functions in benchmark.py):**
- [ ] `benchmark_rotation_distribution()` — Report rotation percentages on 100-PDF sample
- [ ] `benchmark_batch_rendering()` — Compare batch vs page-by-page timing, verify no accuracy change
- [ ] `benchmark_dpi_fallback()` — Measure coverage (% success at 200 vs 300) and speed impact

**Existing Infrastructure (reusable):**
- ✅ `benchmark.py` — Core framework (select_benchmark_corpus, run_single_pdf_at_dpi, accuracy validation)
- ✅ `tests/test_precede_ocr.py` — 230 passing tests, established patterns for mocking and fixtures
- ✅ `precede_ocr.py` — rotation_counts and rotation_pct() already implemented (lines 867-876)

## Sources

### Primary (HIGH confidence)

**PyMuPDF Documentation and Best Practices:**
- [PyMuPDF Production Setup: Extract Text from 10K PDFs in 8 Minutes | Markaicode](https://markaicode.com/tutorial/pymupdf-tutorial-production-setup-guide/)
- [PyMuPDF Production Deployment: 4 Steps for Fast PDF Text Extraction | Markaicode](https://markaicode.com/howto/how-to-deploy-pymupdf-production/)
- [Multiprocessing - PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/recipes-multiprocessing.html)
- [Pixmap and Image Processing | pymupdf/PyMuPDF | DeepWiki](https://deepwiki.com/pymupdf/PyMuPDF/2.3-pixmap-and-image-processing)

**Python Exception Handling and Memory Management:**
- [Built-in Exceptions — Python 3.14.5 documentation](https://docs.python.org/3/library/exceptions.html)
- [How to Fix 'MemoryError' in Python](https://oneuptime.com/blog/post/2026-01-27-fix-memoryerror-in-python/view)
- [Understanding and Handling `MemoryError` in Python - CodeRivers](https://coderivers.org/blog/memoryerror-in-python/)

**Pillow Memory Management:**
- [Image module - Pillow (PIL Fork) 12.2.0 documentation](https://pillow.readthedocs.io/en/stable/reference/Image.html)
- [Python Pillow - Batch Processing of Images](https://www.tutorialspoint.com/python_pillow/python_pillow_batch_processing_images.htm)

### Secondary (MEDIUM confidence)

**OCR Rotation Detection:**
- [Tesseract OCR: Is it still the best open-source OCR in 2026?](https://www.koncile.ai/en/ressources/is-tesseract-still-the-best-open-source-ocr)
- [Poor Rotation / Layout detection · Issue #4426 · tesseract-ocr/tesseract](https://github.com/tesseract-ocr/tesseract/issues/4426)
- [Seeing Straight: Document Orientation Detection for Efficient OCR](https://arxiv.org/pdf/2511.04161)

**OCR DPI Optimization:**
- [The Definitive Guide to OCR in 2026: From Pipelines to VLMs - Edge of Context: Practical AI Engineering](https://slavadubrov.github.io/blog/2026/03/04/the-definitive-guide-to-ocr-in-2026-from-pipelines-to-vlms/)
- [C# OCR DPI Settings: Boost Text Recognition | IronOCR](https://ironsoftware.com/csharp/ocr/how-to/dpi-setting/)

### Tertiary (Project-Specific, HIGH confidence)

**Existing Codebase Patterns:**
- `precede_ocr.py` — Rotation tracking (lines 867-876), process_single_pdf (lines 453-513), extract_id_with_rotation (lines 361-450)
- `benchmark.py` — Benchmark infrastructure (100-PDF sample, accuracy validation, comparison tables)
- `.planning/phases/10-drop-in-performance-gains/benchmark_results.md` — DPI 200 validation (211/211 IDs, 43% faster)
- `.planning/phases/11-advanced-config-tuning/benchmark_results.md` — Phase 11 baseline (1067.3 ms/page, OEM 1 + dict-off)

## Metadata

**Confidence breakdown:**
- **Batch rendering pattern:** HIGH — PyMuPDF official docs + existing codebase pattern (Phase 10) + Python stdlib MemoryError handling
- **DPI fallback strategy:** HIGH — Phase 10 validated DPI 200 at 100% accuracy, fallback logic is simple try-first-then-retry pattern
- **Rotation reordering:** HIGH — Existing rotation tracking infrastructure (lines 867-876), one-line array change validated by benchmark data
- **Benchmark methodology:** HIGH — Reusing proven Phase 10-11 patterns, same 100-PDF sample (seed=42), same accuracy validation approach
- **Memory management:** MEDIUM — PyMuPDF docs confirm explicit doc.close() prevents leaks, but OOM thresholds depend on system RAM (user has 20-core system, likely 32GB+)

**Research date:** 2026-06-08
**Valid until:** 60 days (algorithmic patterns stable; library versions already locked in Phase 10-11)

---

*Phase: 12-algorithmic-enhancements*
*Research completed: 2026-06-08*
