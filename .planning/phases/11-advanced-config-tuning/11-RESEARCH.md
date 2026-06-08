# Phase 11: Advanced Config Tuning - Research

**Researched:** 2026-06-08
**Domain:** Tesseract OCR configuration optimization for numeric digit extraction
**Confidence:** MEDIUM

## Summary

Phase 11 targets 1.5-2x incremental speedup through aggressive Tesseract configuration changes: OEM 1 (LSTM-only), PSM 7 (single-line), and dictionary disabling. These are configuration flag changes only — zero code complexity cost — making even minor speedups worthwhile to ship.

**Critical constraint:** The Phase 10 DPI-200 baseline (94.9% accuracy) is the new measuring stick. All config changes must maintain >=94% accuracy with soft margin (93-94% acceptable if speed gain substantial, below 93% is hard fail).

**Primary recommendation:** Test each config independently first (OEM 1, PSM 7, dict-off), then test winning combinations. Extend existing `benchmark.py` infrastructure rather than building new tooling. Ship any improvement regardless of magnitude since config changes have no complexity cost.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Testing Strategy:**
- **D-01:** Test each config change (OEM 1, PSM 7, dict-off) independently first, then test the winning combination. This catches interaction effects between configs.
- **D-02:** Extend existing `benchmark.py` with a new `benchmark_tesseract_config()` function. Reuse corpus selection, timing, and accuracy validation infrastructure from Phase 10.
- **D-03:** Accuracy baseline is Phase 10's DPI-200 results (the current pipeline state). Regressions measured from HERE, not from v1.1.

**PSM 7 Approach:**
- **D-04:** Try PSM 7 on full page images first (just swap the flag). If accuracy holds on full pages, no extra complexity. If it drops below threshold, keep PSM 6 — don't attempt region cropping.
- **D-05:** If PSM 7 fails accuracy, do NOT try PSM 13 or other PSM variants. Keep PSM 6 (proven at 94.9%) and move on to dictionary tuning.

**Revert Policy:**
- **D-06:** Apply any config that individually passes accuracy. Partial wins are shipped. E.g., if OEM 1 passes but PSM 7 fails, apply OEM 1 alone.
- **D-07:** Accuracy threshold has soft margin: 93-94% acceptable if the speed gain is substantial. Report the tradeoff and let user decide. Below 93% is a hard fail.

**Stop Condition:**
- **D-08:** Ship any improvement regardless of magnitude. Even 1.1x speedup is free speed since configs are just flag changes with zero code complexity cost. The 1.5x roadmap threshold is relaxed.
- **D-09:** Phase 12 gate: after Phase 11 benchmarks, estimate total 30K corpus runtime with Phases 10+11 combined. If under 24 hours, Phase 12 is unnecessary. Only proceed to Phase 12 if still too slow.

### Claude's Discretion

- Order of testing the three configs (which to try first)
- Benchmark output format and reporting details
- How to structure the combination testing (which combos to test)
- Whether to run the full 100-PDF sample or smaller subset for initial screening

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TESS-02 | OCR uses OEM 1 (LSTM-only) mode if accuracy maintains >=94% baseline | OEM modes research, benchmark methodology |
| TESS-03 | OCR uses PSM 7 (single-line) mode if accuracy maintains >=94% baseline | PSM modes comparison, single-line vs block text |
| TESS-04 | OCR disables dictionary loading if accuracy maintains >=94% baseline | Dictionary config research, numeric-only optimization |
| QUAL-01 | All optimizations maintain >=94% OCR accuracy on test corpus | Accuracy validation methodology, baseline comparison |
| QUAL-02 | Benchmark results documented (before/after speed comparison) | Benchmark infrastructure, reporting patterns |

</phase_requirements>

## Standard Stack

### Core (Existing — No New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **pytesseract** | 0.3.13 | Python wrapper for Tesseract | Already installed. Supports all config flags via `config` parameter. Verified working. |
| **Tesseract OCR** | 5.5.2 | OCR engine | Already installed per project constraints. Version 5.x defaults to LSTM (OEM 1). Supports all PSM modes and config variables. |
| **pytest** | 9.0.2 | Test framework | Already installed. Existing 230 passing tests. Config changes should not break tests unless OCR behavior changes. |

### Benchmark Infrastructure (Existing)

| Component | Location | Purpose |
|-----------|----------|---------|
| `benchmark.py` | Project root | DPI/worker benchmarking. Extend with `benchmark_tesseract_config()` function. |
| `select_benchmark_corpus()` | benchmark.py:31 | Random 100-PDF sample (seed=42). Reuse for config testing. |
| `run_single_pdf_at_dpi()` | benchmark.py:75 | Per-PDF processing with DPI parameter. Pattern to follow for config testing. |
| Phase 10 results | `.planning/phases/10-drop-in-performance-gains/benchmark_results.md` | DPI-200 baseline (94.9% accuracy). New accuracy target. |

### No Installation Required

Phase 11 changes configuration flags only. No new packages, no dependency updates, no environment changes.

## Architecture Patterns

### Recommended Benchmark Extension Pattern

```python
def benchmark_tesseract_config(corpus_dir, sample_size=100, seed=42):
    """
    Test Tesseract config variants (OEM, PSM, dictionary) independently,
    then test winning combinations.

    Per D-01: Independent testing first to isolate effects.
    Per D-02: Reuse Phase 10 infrastructure.

    Returns:
        DataFrame with columns: config_name, duration, pages, ids_found,
                                ms_per_page, speedup_vs_baseline
    """
    # Reuse select_benchmark_corpus() for reproducibility
    sample = select_benchmark_corpus(corpus_dir, sample_size, seed)

    # Define configs to test
    configs = {
        'baseline': '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
        'oem1': '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789',
        'psm7': '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789',
        'dict_off': '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789 -c load_system_dawg=false -c load_freq_dawg=false',
    }

    results = []
    for config_name, config_string in configs.items():
        # Run each PDF with this config
        # Time execution, collect IDs
        # Compare against Phase 10 baseline accuracy
        pass

    # Test winning combinations (D-01)
    # E.g., if OEM 1 and dict-off both pass, test OEM 1 + dict-off

    return pd.DataFrame(results)
```

### Config String Modification Points

Current config strings at two locations (must update both):

**Location 1:** `precede_ocr.py:397`
```python
# Current (Phase 10)
config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'
```

**Location 2:** `precede_ocr.py:432` (preprocessing fallback)
```python
# Current (Phase 10)
config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'
```

**Critical:** Both locations must use identical config. Pattern from Phase 10: hard-code winning config, no CLI flags.

### Accuracy Validation Pattern (from Phase 10)

```python
def validate_accuracy_against_baseline(test_results, baseline_csv):
    """
    Compare page-by-page ID extraction against baseline results.

    Per D-03: Baseline is Phase 10 DPI-200 results, not v1.1.
    Per D-07: >=94% required, 93-94% soft margin, <93% hard fail.

    Returns:
        accuracy_pct: float (0-100)
        regression_details: dict of pages with differences
    """
    # Load baseline CSV (from Phase 10 run)
    baseline = pd.read_csv(baseline_csv)

    # Compare each page: filename + page number
    # Match: both found same ID(s) or both found no ID
    # Mismatch: different IDs, or one found/one didn't

    accuracy = matches / total_pages * 100
    return accuracy, regression_details
```

### Independent Testing Strategy (D-01)

```
Test Order (suggested):
1. OEM 1 (LSTM-only) — likely fastest individual gain
2. Dictionary disabling — second most likely for numeric-only
3. PSM 7 (single-line) — riskiest for accuracy

For each:
- Run on 100-PDF sample
- Time execution
- Validate accuracy against Phase 10 baseline
- Report: speedup, accuracy delta, pass/fail

Then test combinations of winners:
- If OEM 1 + dict-off both pass → test OEM 1 + dict-off combined
- If all three pass → test OEM 1 + PSM 7 + dict-off combined
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Accuracy validation | Custom ID comparison logic | Extend Phase 10's page-by-page comparison | Phase 10 already validates IDs per page. Reuse tested code. |
| Corpus sampling | New random selection | `select_benchmark_corpus(seed=42)` | Reproducibility requires same sample. seed=42 is locked. |
| Timing methodology | Manual timing code | `time.perf_counter()` pattern from Phase 10 | Consistent with existing benchmarks. |
| Results reporting | Custom tables | pandas DataFrame + markdown tables | Phase 10 pattern. benchmark_results.md template exists. |
| Config combinations | Manual permutation logic | Explicit dict of configs to test | 3 configs = 8 permutations (2^3). Test baseline + 3 independent + winning combos only, not all permutations. |

**Key insight:** Phase 10 built comprehensive benchmark infrastructure. Phase 11 extends it with config testing, not new infrastructure.

## Tesseract Configuration Deep Dive

### OEM Modes (OCR Engine Mode)

| Mode | Description | Speed | Accuracy | Use Case |
|------|-------------|-------|----------|----------|
| **OEM 0** | Legacy engine only | Faster initialization | Lower accuracy | Pre-LSTM fonts, legacy compatibility |
| **OEM 1** | LSTM neural nets only | **Fastest runtime** | Highest accuracy | **Tesseract 5 default, recommended** |
| **OEM 2** | Legacy + LSTM combined | Slower (runs both) | Mixed | Fallback mode, not recommended |
| **OEM 3** | Default (based on available) | Depends on traineddata | Depends on traineddata | **Current pipeline setting** |

**Research findings:**
- OEM 1 is **2x faster than Tesseract 3.04 (legacy)** in wall time per official docs
- OEM 1 is Tesseract 5's default mode for new installations
- OEM 3 defaults to OEM 1 if only LSTM traineddata available (tessdata_fast, tessdata_best)
- **Critical:** Windows Tesseract 5.5.2 installation uses tessdata_fast (LSTM-only), so OEM 3 likely already runs OEM 1 internally

**Recommendation:** Test OEM 1 explicitly to confirm speedup vs OEM 3. Expected gain: 0-20% (may already be running LSTM-only, but explicit OEM 1 may skip detection overhead).

**Confidence:** MEDIUM — OEM 1 is faster than OEM 0/2, but OEM 3 may already be using LSTM on this system.

### PSM Modes (Page Segmentation Mode)

| Mode | Description | Use Case | Risk |
|------|-------------|----------|------|
| **PSM 6** | Uniform block of text | Multi-line paragraphs, pages | **Current pipeline (94.9% accuracy)** |
| **PSM 7** | Single text line | License plates, single-line headers | **D-04: Try on full pages first** |
| **PSM 3** | Fully automatic (default) | Unknown layouts | Slower, not relevant |
| **PSM 13** | Raw line (bypass segmentation) | Single-line, minimal processing | **D-05: Out of scope** |

**PSM 6 characteristics:**
- Assumes uniform block of text (consistent font/size)
- Handles line breaks naturally
- Proven on this corpus: 94.9% accuracy with DPI 200

**PSM 7 characteristics:**
- Treats image as single continuous line (no line breaks)
- Faster: skips multi-line segmentation
- **Risk:** If Tesseract sees multiple text regions, may fail or concatenate incorrectly

**Research findings:**
- PSM 7 succeeds on license plates (single line, isolated text)
- PSM 6 succeeds on book pages (multi-line uniform text)
- **This corpus:** Scanned images with "Precede" label + 5-digit ID, rotated 90°. Text is isolated but may appear as two "lines" (label + ID) to Tesseract.

**Recommendation (per D-04):** Try PSM 7 on full page images. If accuracy drops below threshold, revert to PSM 6 immediately. Do not attempt region cropping or PSM 13.

**Expected outcome:** PSM 7 may fail if Tesseract interprets "Precede" label and ID as separate lines. If it works, speedup estimated 10-30% from skipping segmentation.

**Confidence:** LOW — PSM 7 behavior depends on image characteristics. Must benchmark on actual corpus.

### Dictionary Configuration

| Parameter | Default | Disabled | Purpose |
|-----------|---------|----------|---------|
| `load_system_dawg` | true | false | System dictionary (common words) |
| `load_freq_dawg` | true | false | Frequency-weighted dictionary |

**Effect of disabling:**
- **Speed:** Faster initialization (no dictionary loading)
- **Speed:** Faster recognition (no dictionary lookups)
- **Accuracy:** Higher for non-dictionary text (numeric IDs, codes)
- **Accuracy:** Lower for natural language text (spell-checking disabled)

**This corpus:** 5-digit numeric IDs only. No natural language. Character whitelist already constrains to `0123456789`.

**Research findings:**
- Disabling dictionaries recommended when text is not dictionary words
- Combined with character whitelist, dictionaries provide no value for numeric-only text
- Expected speedup: 5-15% from skipping dictionary initialization and lookup

**Configuration syntax:**
```python
config = '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789 -c load_system_dawg=false -c load_freq_dawg=false'
```

**Recommendation:** High probability of speedup with no accuracy loss. Dictionaries are irrelevant for numeric extraction.

**Confidence:** HIGH — Well-documented feature, clear applicability to numeric-only use case.

## Common Pitfalls

### Pitfall 1: Assuming OEM 3 Uses Legacy Engine
**What goes wrong:** Benchmark shows no speedup from OEM 1, conclude "OEM modes don't matter."
**Why it happens:** Windows Tesseract 5.5.2 with tessdata_fast may already run LSTM-only internally when OEM 3 is set. OEM 3 means "use what's available" — if only LSTM traineddata exists, it uses OEM 1 automatically.
**How to avoid:** Check installed traineddata files. If tessdata_fast or tessdata_best, OEM 3 ≈ OEM 1. Speedup may be minimal (0-10%) from skipping detection overhead only.
**Warning signs:** OEM 1 benchmark shows <5% speedup over OEM 3 baseline.

### Pitfall 2: Testing PSM 7 Without Fallback Plan
**What goes wrong:** PSM 7 drops accuracy to 85%, but team already committed to shipping it because "roadmap says PSM 7."
**Why it happens:** D-04 is clear: try PSM 7, but if it fails, revert. PSM 6 is proven at 94.9%. No need to force PSM 7.
**How to avoid:** Per D-05, if PSM 7 fails accuracy threshold, immediately revert to PSM 6. Do not attempt PSM 13 or region cropping workarounds.
**Warning signs:** PSM 7 accuracy <93% on benchmark. Hard stop, revert to PSM 6.

### Pitfall 3: Testing Combinations Before Independent Tests
**What goes wrong:** Test OEM 1 + PSM 7 + dict-off immediately. It fails. Don't know which config caused failure.
**Why it happens:** Skipping D-01 independent testing to "save time."
**How to avoid:** Always test each config independently first. Know which configs pass individually before testing combinations.
**Warning signs:** Combination test fails, but no data on individual config performance.

### Pitfall 4: Ignoring Interaction Effects in Combinations
**What goes wrong:** OEM 1 passes (1.2x speedup, 94.5% accuracy). Dict-off passes (1.15x speedup, 94.2% accuracy). Combined test: 1.1x speedup, 91% accuracy.
**Why it happens:** Config parameters can interact. LSTM (OEM 1) may rely on dictionary in unexpected ways, even with character whitelist.
**How to avoid:** D-01 includes combination testing of winners. Expect non-additive speedups. Always validate accuracy of combinations separately.
**Warning signs:** Combination accuracy < min(individual accuracies). Indicates negative interaction.

### Pitfall 5: Mismatched Config Strings at Two Locations
**What goes wrong:** Update config at line 397, forget line 432 (preprocessing fallback). Preprocessing now uses different config than primary path. Results inconsistent.
**Why it happens:** Config string appears twice in `extract_id_with_rotation()` (lines 397 and 432). Easy to miss second location.
**How to avoid:** Always update both locations identically. Add comment `# CRITICAL: Keep in sync with line 432` at line 397.
**Warning signs:** Inconsistent results between primary OCR pass and preprocessing fallback.

### Pitfall 6: Using Outdated Baseline for Accuracy Validation
**What goes wrong:** Compare Phase 11 results to v1.1 accuracy (pre-Phase 10), report "OEM 1 maintains accuracy." But Phase 10 changed DPI to 200, which already affected accuracy profile.
**Why it happens:** D-03 is explicit: baseline is Phase 10 DPI-200 results, not v1.1.
**How to avoid:** Always compare against Phase 10 benchmark results. Baseline CSV must be from DPI-200 run.
**Warning signs:** Accuracy validation references v1.1 or pre-DPI-optimization results.

### Pitfall 7: Soft Margin Becomes Excuse for Low Accuracy
**What goes wrong:** OEM 1 scores 92.5% accuracy. Claim "soft margin allows 93-94%, and 92.5% is close, so ship it."
**Why it happens:** Misreading D-07. Soft margin is 93-94%, not "around 93%."
**How to avoid:** Hard fail <93%. Soft margin (93-94%) requires user decision with documented tradeoff. 92.5% is below threshold.
**Warning signs:** Accuracy between 91-93%. Requires re-test or revert, not shipping.

## Code Examples

### Example 1: Benchmark Config Variants

```python
# Source: Extended from benchmark.py pattern (Phase 10)
def benchmark_tesseract_config(corpus_dir, baseline_csv=None, sample_size=100, seed=42):
    """
    Test Tesseract config variants: OEM 1, PSM 7, dict-off.

    Per D-01: Independent tests first, then combinations.
    Per D-02: Reuse Phase 10 infrastructure.
    Per D-03: Compare against Phase 10 DPI-200 baseline.
    """
    import time
    import pandas as pd
    from pathlib import Path

    # Reuse corpus selection
    sample = select_benchmark_corpus(corpus_dir, sample_size, seed)

    # Define configs (D-01: independent variants)
    configs = {
        'baseline_phase10': '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
        'oem1_only': '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789',
        'psm7_only': '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789',
        'dict_off_only': '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789 -c load_system_dawg=false -c load_freq_dawg=false',
    }

    results = []
    for config_name, config_string in configs.items():
        print(f"\n=== Testing {config_name} ===")

        # Temporarily monkey-patch config in precede_ocr module
        # OR: Add config parameter to extract_id_with_rotation()

        start = time.perf_counter()

        # Process all PDFs in sample
        all_results = []
        for pdf_path in sample:
            # Use run_single_pdf_at_dpi() pattern with config override
            pdf_results = process_pdf_with_config(pdf_path, config_string)
            all_results.extend(pdf_results)

        duration = time.perf_counter() - start

        # Aggregate stats
        total_pages = len(all_results)
        total_ids = sum(len(r['ids']) for r in all_results)
        ms_per_page = (duration / total_pages * 1000) if total_pages > 0 else 0

        results.append({
            'config': config_name,
            'duration_sec': duration,
            'pages': total_pages,
            'ids_found': total_ids,
            'ms_per_page': ms_per_page,
        })

        # Accuracy validation (if baseline provided)
        if baseline_csv:
            accuracy = validate_accuracy_vs_baseline(all_results, baseline_csv)
            results[-1]['accuracy_pct'] = accuracy
            results[-1]['pass_fail'] = 'PASS' if accuracy >= 94 else 'SOFT' if accuracy >= 93 else 'FAIL'

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Calculate speedup vs baseline
    baseline_ms = df[df['config'] == 'baseline_phase10']['ms_per_page'].values[0]
    df['speedup_vs_baseline'] = baseline_ms / df['ms_per_page']

    # Print comparison table
    print("\n=== Config Benchmark Results ===")
    print(df.to_string(index=False))

    # D-01: Test combinations of winners
    winners = df[(df['pass_fail'] == 'PASS') & (df['config'] != 'baseline_phase10')]
    if len(winners) >= 2:
        print("\n=== Testing Winning Combinations ===")
        # Build combined config from individual winners
        # E.g., if OEM 1 and dict-off pass, test OEM 1 + dict-off
        # (Implementation details omitted for brevity)

    return df
```

### Example 2: Process PDF with Custom Config

```python
# Source: Adapted from benchmark.py run_single_pdf_at_dpi()
def process_pdf_with_config(pdf_path, tesseract_config):
    """
    Process a single PDF with a specific Tesseract config string.

    Returns list of result dicts (one per page).
    """
    import fitz  # PyMuPDF
    from PIL import Image
    from precede_ocr import extract_id_with_rotation

    filename = Path(pdf_path).name
    results = []

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        return [{'filename': filename, 'page': 0, 'ids': [], 'notes': f'error: {e}'}]

    for page_num in range(len(doc)):
        page = doc[page_num]

        # Render at DPI 200 (Phase 10 winner)
        pix = page.get_pixmap(dpi=200)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))

        # Extract IDs with custom config
        # PROBLEM: extract_id_with_rotation() doesn't accept config parameter
        # SOLUTION: Temporarily monkey-patch or add config parameter

        # Monkey-patch approach (for benchmarking only):
        import precede_ocr
        original_config_line_397 = precede_ocr.TESSERACT_CONFIG  # if we refactor to constant
        precede_ocr.TESSERACT_CONFIG = tesseract_config

        ids, rotation, notes = extract_id_with_rotation(image, debug=False)

        precede_ocr.TESSERACT_CONFIG = original_config_line_397  # restore

        results.append({
            'filename': filename,
            'page': page_num + 1,
            'ids': ids,
            'rotation_detected': rotation,
            'notes': notes,
        })

    doc.close()
    return results
```

**Note:** The above example shows monkey-patching for benchmark purposes. Production implementation may refactor config into a module-level constant for cleaner testing.

### Example 3: Accuracy Validation Against Baseline

```python
# Source: Pattern from Phase 10 accuracy validation discussion
def validate_accuracy_vs_baseline(test_results, baseline_csv_path):
    """
    Compare page-by-page ID extraction against Phase 10 baseline.

    Per D-03: Baseline is Phase 10 DPI-200 results.
    Per D-07: >=94% pass, 93-94% soft margin, <93% fail.

    Args:
        test_results: List of dicts with keys: filename, page, ids
        baseline_csv_path: Path to Phase 10 baseline results CSV

    Returns:
        accuracy_pct: float (0-100)
    """
    import pandas as pd

    # Load baseline
    baseline_df = pd.read_csv(baseline_csv_path)

    # Convert test results to comparable format
    test_df = pd.DataFrame(test_results)

    # Create composite key: filename + page
    baseline_df['key'] = baseline_df['filename'] + '_' + baseline_df['page'].astype(str)
    test_df['key'] = test_df['filename'] + '_' + test_df['page'].astype(str)

    # Normalize IDs to sets for comparison (order doesn't matter)
    def ids_to_set(ids):
        if isinstance(ids, list):
            return set(ids)
        elif isinstance(ids, str):
            return set(ids.split(',')) if ids else set()
        else:
            return set()

    baseline_df['id_set'] = baseline_df['ids'].apply(ids_to_set)
    test_df['id_set'] = test_df['ids'].apply(ids_to_set)

    # Merge on key
    merged = baseline_df.merge(test_df, on='key', suffixes=('_baseline', '_test'))

    # Compare ID sets
    merged['match'] = merged.apply(
        lambda row: row['id_set_baseline'] == row['id_set_test'],
        axis=1
    )

    # Calculate accuracy
    matches = merged['match'].sum()
    total = len(merged)
    accuracy_pct = (matches / total * 100) if total > 0 else 0

    # Report mismatches
    mismatches = merged[~merged['match']]
    if len(mismatches) > 0:
        print(f"\nAccuracy: {accuracy_pct:.1f}% ({matches}/{total} pages match)")
        print(f"Mismatches: {len(mismatches)} pages")
        print("\nFirst 10 mismatches:")
        print(mismatches[['filename_baseline', 'page_baseline', 'id_set_baseline', 'id_set_test']].head(10))

    return accuracy_pct
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tesseract 3.x legacy engine | Tesseract 4+ LSTM neural nets | Tesseract 4.0 (2018) | 2x faster, higher accuracy on complex layouts |
| OEM 0 (legacy) default | OEM 1 (LSTM) default | Tesseract 5.0 (2021) | LSTM-only models (tessdata_fast/best) require OEM 1 |
| Manual PSM selection per image | PSM 6 for uniform blocks | Best practice evolution | PSM 6 handles most scanned documents well |
| Dictionary loading always enabled | Conditional dictionary disabling | Ongoing | Numeric-only use cases benefit from disabling dictionaries |

**Deprecated/outdated:**
- **OEM 0 (legacy engine):** Only recommended for pre-2018 fonts. LSTM (OEM 1) superior for modern use cases.
- **OEM 2 (legacy + LSTM combined):** Runs both engines, slower. No advantage over OEM 1 for most tasks.
- **PSM 3 (fully automatic):** Slower than targeted PSM modes. Use PSM 6 for uniform text blocks.
- **Training custom Tesseract models:** Tesseract 4/5 LSTM models trained on 400K+ lines, 4,500+ fonts. Custom training takes weeks and rarely beats pre-trained models for standard Latin text.

## Open Questions

### 1. Does OEM 3 Already Use LSTM on This System?

**What we know:** Windows Tesseract 5.5.2 installed. Likely uses tessdata_fast (LSTM-only models). OEM 3 defaults to "use what's available" — if only LSTM traineddata exists, uses OEM 1 internally.

**What's unclear:** Whether OEM 1 explicit setting skips detection overhead vs OEM 3 auto-detection. Speedup may be 0% (already running LSTM) or 5-15% (skips detection).

**Recommendation:** Benchmark to verify. If speedup <5%, document that OEM 3 ≈ OEM 1 on this system. Still ship OEM 1 explicitly for clarity and portability.

### 2. Will PSM 7 Interpret "Precede" Label and ID as Two Lines?

**What we know:** PSM 7 treats image as single text line. Corpus has "Precede" cursive label + 5-digit ID, rotated 90°.

**What's unclear:** Whether Tesseract sees this as one line or two separate text regions. If two, PSM 7 may fail or concatenate incorrectly.

**Recommendation:** Per D-04, try PSM 7 on full pages. If accuracy drops, immediately revert to PSM 6. Do not attempt workarounds.

### 3. Do Dictionary Configs Interact with Character Whitelist?

**What we know:** Character whitelist constrains to `0123456789`. Dictionaries provide word-level context (spell-checking).

**What's unclear:** Whether disabling dictionaries has any effect when character whitelist already restricts to digits. May be redundant, or may skip initialization overhead.

**Recommendation:** Benchmark dict-off independently. Expected speedup 5-15% from skipping initialization even if lookup is already bypassed by whitelist.

### 4. What Is the Speedup of Combined Winners?

**What we know:** Individual configs may provide 1.1-1.3x speedups each. Combined, they may be additive (1.1 × 1.2 × 1.15 ≈ 1.52x) or non-additive due to interaction effects.

**What's unclear:** Actual combined speedup and whether accuracy holds.

**Recommendation:** Per D-01, test combinations only after individual tests. Document combined results separately. Ship best-performing config that passes accuracy threshold.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pytest.ini` — defines testpaths, file patterns |
| Quick run command | `pytest tests/test_precede_ocr.py -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TESS-02 | OEM 1 config applied and accuracy >=94% | integration | `python benchmark.py <corpus> --baseline-csv <phase10.csv>` | ✅ benchmark.py exists, extend with config testing |
| TESS-03 | PSM 7 config applied and accuracy >=94% | integration | `python benchmark.py <corpus> --baseline-csv <phase10.csv>` | ✅ benchmark.py exists, extend with config testing |
| TESS-04 | Dictionary disabled and accuracy >=94% | integration | `python benchmark.py <corpus> --baseline-csv <phase10.csv>` | ✅ benchmark.py exists, extend with config testing |
| QUAL-01 | All configs maintain >=94% accuracy | integration | `python benchmark.py <corpus> --baseline-csv <phase10.csv>` | ✅ benchmark.py exists, extend with config testing |
| QUAL-02 | Benchmark results documented | manual | Human review of `benchmark_results.md` | ❌ Wave 0 creates Phase 11 benchmark_results.md |

### Sampling Rate

- **Per task commit:** `pytest tests/test_precede_ocr.py -x` — verify no breakage from config changes
- **Per wave merge:** `python benchmark.py <corpus>` — verify config changes on 100-PDF sample
- **Phase gate:** Full benchmark + accuracy validation before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `benchmark.py::benchmark_tesseract_config()` — function to test OEM/PSM/dict configs independently and in combination
- [ ] `benchmark.py::process_pdf_with_config()` — helper to run OCR with custom config string
- [ ] `benchmark.py::validate_accuracy_vs_baseline()` — page-by-page accuracy comparison against Phase 10 baseline CSV
- [ ] `.planning/phases/11-advanced-config-tuning/benchmark_results.md` — Phase 11 results documentation template

## Environment Availability

> Phase 11 has no external dependencies beyond those already verified in Phase 10. All changes are Tesseract configuration flags.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Tesseract OCR | All config testing | ✓ | 5.5.2 | — |
| pytesseract | Python interface | ✓ | 0.3.13 | — |
| Python | Runtime | ✓ | 3.14.2 | — |
| pytest | Test verification | ✓ | 9.0.2 | — |
| PyMuPDF (fitz) | PDF rendering (Phase 10) | ✓ | (installed Phase 10) | — |

**Missing dependencies with no fallback:** None

**Missing dependencies with fallback:** None

## Sources

### Primary (HIGH confidence)

- [Tesseract Improving Quality Documentation](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html) - Dictionary configuration, PSM modes overview
- [PyImageSearch: Tesseract PSM Modes Explained](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/) - PSM 6 vs PSM 7 detailed comparison, use cases, code examples
- [pytesseract PyPI](https://pypi.org/project/pytesseract/) - Config parameter documentation, version 0.3.13
- [Python OCR Tutorial: Tesseract, Pytesseract, and OpenCV - Nanonets](https://nanonets.com/blog/ocr-with-tesseract/) - OEM modes overview, LSTM performance
- [tessdoc: 4.0 Accuracy and Performance](https://tesseract-ocr.github.io/tessdoc/tess4/4.0-Accuracy-and-Performance.html) - LSTM 2x faster than Tesseract 3.04 benchmark

### Secondary (MEDIUM confidence)

- [OCR Engine Modes - DeepWiki](https://deepwiki.com/tesseract-ocr/tessdata/2.1-ocr-engine-modes) - OEM 0/1/2/3 descriptions
- [Tuning Tesseract PSM and OEM - sqlpey.com](https://sqlpey.com/python/tesseract-psm-oem-tuning/) - Combined configuration examples
- [OCR Accuracy Benchmarking - AIMultiple](https://aimultiple.com/ocr-accuracy) - Accuracy validation methodology
- [Measuring Pytesseract Performance - Glinteco](https://glinteco.com/en/post/measuring-time-and-accuracy-performance-of-pytesseract/) - Benchmark methodology, timing patterns
- [Tesseract Production Setup - Markaicode](https://markaicode.com/tutorial/tesseract-tutorial-production-setup-guide/) - Version pinning, preprocessing importance
- [Dedicated OCR Models vs Tesseract 2026 - Joshua8.AI](https://joshua8.ai/ocr-models-vs-vision-llms-vs-tesseract/) - Tesseract 5 baseline accuracy, preprocessing impact

### Tertiary (LOW confidence)

- [GitHub tesseract-ocr/tessdata](https://github.com/tesseract-ocr/tessdata) - tessdata_fast models (LSTM-only)
- [GitHub tesseract-ocr/tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) - Fast integer LSTM models
- [tessdoc: Benchmarks](https://tesseract-ocr.github.io/tessdoc/Benchmarks.html) - Official benchmarking guidance (limited detail)

## Metadata

**Confidence breakdown:**
- **OEM modes:** MEDIUM — OEM 1 faster than legacy (HIGH), but unclear if OEM 3 already uses LSTM on this system (requires benchmarking)
- **PSM modes:** LOW — PSM 7 applicability to this corpus unknown; must benchmark to verify accuracy
- **Dictionary disabling:** HIGH — Well-documented, clear applicability to numeric-only extraction
- **Benchmark methodology:** HIGH — Phase 10 infrastructure proven and reusable
- **Accuracy validation:** HIGH — Page-by-page comparison pattern established in Phase 10

**Research date:** 2026-06-08
**Valid until:** 2026-08-08 (60 days — Tesseract 5.x stable, configuration options unlikely to change)

---

*This research supports Phase 11 planning. Planner will create PLAN.md files based on these findings.*
