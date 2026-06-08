---
phase: 11-advanced-config-tuning
plan: 01
subsystem: benchmark-infrastructure
tags: [tesseract-config, benchmarking, accuracy-validation]
dependency_graph:
  requires: [10-03-SUMMARY.md]
  provides: [tesseract-config-benchmark-tooling]
  affects: [benchmark.py]
tech_stack:
  added: []
  patterns: [independent-config-testing, combination-testing, soft-accuracy-margin]
key_files:
  created: []
  modified: [benchmark.py]
decisions:
  - "Per D-01: Independent testing first, then combination testing"
  - "Per D-02: Extend Phase 10 benchmark.py infrastructure"
  - "Per D-03: Compare against Phase 10 DPI-200 baseline"
  - "Per D-07: Accuracy thresholds - >=94% PASS, 93-94% SOFT, <93% FAIL"
metrics:
  duration_sec: 249
  completed_date: 2026-06-08T14:59:27Z
  tasks_completed: 2
  files_modified: 1
---

# Phase 11 Plan 01: Tesseract Config Benchmarking Tooling Summary

**One-liner:** Extend benchmark.py with independent testing of OEM 1, PSM 7, dict-off configs plus combination testing, using Phase 10 DPI-200 baseline for accuracy validation with PASS/SOFT/FAIL classification.

## Objective Achieved

Extended benchmark.py with Phase 11 Tesseract config benchmarking capability. Users can now:
1. Generate Phase 10 baseline CSV with `--generate-baseline`
2. Test each config independently (OEM 1, PSM 7, dict-off) with `--tesseract-config`
3. Automatically test winning combinations
4. Validate accuracy against Phase 10 baseline with PASS/SOFT/FAIL classification

## Tasks Completed

### Task 1: Add process_pdf_with_config() and generate_baseline_csv() to benchmark.py
**Commit:** `0eaac60`
**Files:** benchmark.py

Added two helper functions:
- `process_pdf_with_config(pdf_path, tesseract_config, dpi=200)` — Processes single PDF with custom Tesseract config string, reimplements rotation loop [90, 270, 0, 180] with preprocessing fallback for independent config testing
- `generate_baseline_csv(corpus_dir, output_path, sample_size=100, seed=42)` — Generates Phase 10 baseline CSV at DPI 200 for accuracy comparison

Added imports: `re`, `io`, `normalize_digits`, `select_all_valid_ids`, `preprocess_image` from precede_ocr.

All 230 tests passing, no regressions.

### Task 2: Add benchmark_tesseract_config() and CLI integration to benchmark.py
**Commit:** `36d560d`
**Files:** benchmark.py

Added main benchmarking function and CLI integration:
- `benchmark_tesseract_config(corpus_dir, baseline_csv, sample_size=100, seed=42)` — Benchmarks four configs independently (baseline_phase10, oem1_only, psm7_only, dict_off_only), then tests combinations of winners
- Phase 1: Independent testing with timing, accuracy validation, PASS/SOFT/FAIL classification
- Phase 2: Combination testing (pairs + triple if all 3 pass)
- Phase 3: Summary with recommendations

Updated CLI:
- Added `--tesseract-config` flag to run Phase 11 benchmark
- Added `--generate-baseline <path>` flag to create baseline CSV
- Updated script docstring with Phase 11 usage examples

Accuracy classification per D-07:
- >=94%: PASS
- 93-94%: SOFT (user decides)
- <93%: FAIL

Config strings tested:
- `baseline_phase10`: `--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789`
- `oem1_only`: `--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789`
- `psm7_only`: `--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789`
- `dict_off_only`: `--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789 -c load_system_dawg=false -c load_freq_dawg=false`

All 230 tests passing, no regressions.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None detected. All functions fully implemented.

## Verification Results

All automated verification passed:
- `python -c "from benchmark import benchmark_tesseract_config, generate_baseline_csv, process_pdf_with_config"` → OK
- `python benchmark.py --help` → Shows `--tesseract-config` and `--generate-baseline` flags
- `pytest tests/test_precede_ocr.py -x` → 230 tests passed in 11.40s

## Integration Points

**Upstream dependencies:**
- Phase 10 benchmark infrastructure (select_benchmark_corpus, run_single_pdf_at_dpi, validate_accuracy)
- precede_ocr.py functions (normalize_digits, select_all_valid_ids, preprocess_image)

**Downstream consumers:**
- Phase 11 Plan 02 (will use benchmark_tesseract_config to run actual benchmarks)
- User CLI (can now generate baseline and run config benchmarks)

## Key Decisions Made

1. **Independent testing first:** Per D-01, test each config variant independently before testing combinations to isolate effects
2. **Reuse Phase 10 patterns:** Per D-02, extended existing benchmark.py rather than building new tooling
3. **Phase 10 baseline:** Per D-03, accuracy validated against Phase 10 DPI-200 results (not v1.1)
4. **Soft accuracy margin:** Per D-07, 93-94% accuracy marked as SOFT (requires user decision), <93% is hard FAIL
5. **Config string structure:** Explicit dict with four configs (baseline + 3 variants), combination testing builds from winning flags

## Testing Notes

- All 230 existing tests pass — no regressions
- New functions are importable and CLI help shows new flags
- No unit tests added for benchmark functions (per Phase 10 pattern — benchmarks are integration tools, not production code)

## Performance Characteristics

Estimated benchmark runtime on 100-PDF sample:
- Each independent config: ~30-60 seconds (depends on corpus)
- Combination tests: ~30-60 seconds per combination
- Total for all configs: ~3-6 minutes for 4 independent + 0-4 combinations

## Next Steps

1. User generates Phase 10 baseline CSV: `python benchmark.py <corpus> --generate-baseline baseline_phase10.csv`
2. User runs Phase 11 config benchmark: `python benchmark.py <corpus> --tesseract-config --baseline-csv baseline_phase10.csv --skip-dpi --skip-workers --skip-whitelist`
3. User reviews results to select winning config
4. Phase 11 Plan 02 will apply winning config to precede_ocr.py

## Self-Check: PASSED

Verified all claims:
- ✓ benchmark.py exists and contains all three new functions
- ✓ Commit 0eaac60 exists: `git log --oneline --all | grep 0eaac60`
- ✓ Commit 36d560d exists: `git log --oneline --all | grep 36d560d`
- ✓ All Phase 11 functions importable
- ✓ CLI help shows --tesseract-config and --generate-baseline
- ✓ 230 tests pass with no failures

---

*Plan 11-01 execution complete. Tooling ready for Phase 11 benchmarking workflow.*
