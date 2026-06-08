"""
Benchmark Script — DPI, Worker Count, Whitelist, and Tesseract Config Optimization.

Usage:
    # Phase 10 benchmarks (DPI, workers, whitelist)
    python benchmark.py <corpus_dir> [--baseline-csv <path>]

    # Phase 11: Generate baseline CSV first
    python benchmark.py <corpus_dir> --generate-baseline baseline_phase10.csv

    # Phase 11: Run Tesseract config benchmark
    python benchmark.py <corpus_dir> --tesseract-config --baseline-csv baseline_phase10.csv

    # Combined: generate baseline and benchmark in one run
    python benchmark.py <corpus_dir> --generate-baseline baseline_phase10.csv --tesseract-config --baseline-csv baseline_phase10.csv --skip-dpi --skip-workers --skip-whitelist

This script benchmarks the Precede OCR pipeline across different configurations
to find optimal settings. Results are printed as comparison tables.

Per D-06: Standalone script, not integrated into main pipeline.
Per D-07: Uses 100-PDF random sample for iteration speed.
Per D-08: Accuracy validated by comparing IDs page-by-page against baseline.
"""

import argparse
import random
import time
import multiprocessing as mp
from pathlib import Path
from collections import defaultdict
import re
import io
import fitz  # PyMuPDF
from PIL import Image
import pandas as pd
import pytesseract

# Import from main pipeline
from precede_ocr import (extract_id_with_rotation, process_all_pdfs,
                          normalize_digits, select_all_valid_ids, preprocess_image)


def select_benchmark_corpus(corpus_dir, sample_size=100, seed=42):
    """
    Select a random sample of PDFs from the corpus for benchmarking.

    Per D-07: 100-PDF random sample from real corpus for iteration speed.
    Uses random.seed() for reproducibility.

    Args:
        corpus_dir: Path to PDF corpus directory
        sample_size: Number of PDFs to sample (default 100)
        seed: Random seed for reproducibility (default 42)

    Returns:
        List of Path objects representing sampled PDFs
    """
    corpus_path = Path(corpus_dir)

    # Collect all PDFs
    all_pdfs = list(corpus_path.rglob('*.pdf'))

    if not all_pdfs:
        print(f"ERROR: No PDF files found in {corpus_dir}")
        return []

    # Sample with reproducible seed
    random.seed(seed)
    sample = random.sample(all_pdfs, min(sample_size, len(all_pdfs)))

    # Calculate statistics
    folders_represented = len(set(pdf.parent for pdf in sample))
    file_sizes = [pdf.stat().st_size for pdf in sample if pdf.exists()]
    size_range = (min(file_sizes) / 1024, max(file_sizes) / 1024) if file_sizes else (0, 0)

    # Print stats
    print(f"\n=== Benchmark Corpus Selected ===")
    print(f"Total PDFs found: {len(all_pdfs)}")
    print(f"Sample size: {len(sample)}")
    print(f"Folders represented: {folders_represented}")
    print(f"File size range: {size_range[0]:.1f} KB - {size_range[1]:.1f} KB")
    print()

    return sample


def run_single_pdf_at_dpi(pdf_path, dpi):
    """
    Process a single PDF at a specific DPI, returning results list.

    This function renders each page at the given DPI and runs OCR extraction.
    Avoids modifying the main pipeline's process_single_pdf function.

    Args:
        pdf_path: Path to PDF file
        dpi: DPI setting for rendering (200, 250, or 300)

    Returns:
        List of result dicts with keys: filename, page, ids, rotation_detected, notes
    """
    filename = Path(pdf_path).name

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        return [{
            'filename': filename,
            'page': 0,
            'ids': [],
            'rotation_detected': None,
            'notes': f'error: {type(e).__name__}: {e}'
        }]

    try:
        results = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            # Render at specified DPI
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Run OCR extraction
            ids_found, rotation, notes = extract_id_with_rotation(img, debug=False)

            results.append({
                'filename': filename,
                'page': page_idx + 1,
                'ids': ids_found,
                'rotation_detected': rotation if ids_found else None,
                'notes': notes
            })

        return results
    finally:
        doc.close()


def benchmark_dpi(pdf_paths, dpi_values=[200, 250, 300]):
    """
    Benchmark different DPI settings on the sample corpus.

    Per D-03: Test 200, 250, and 300 DPI on the sample.
    Tests each DPI value sequentially and measures total processing time.

    Args:
        pdf_paths: List of Path objects to process
        dpi_values: List of DPI values to test (default [200, 250, 300])

    Returns:
        pandas DataFrame with columns: dpi, total_time_sec, pages_processed, ids_found, pages_per_second
    """
    print("\n=== DPI Benchmark ===")
    print("Testing DPI values:", dpi_values)
    print()

    results = []
    dpi_results_cache = {}  # Cache results for accuracy comparison

    for dpi in dpi_values:
        print(f"Testing DPI {dpi}...")

        start_time = time.perf_counter()
        total_pages = 0
        total_ids = 0
        all_results = []

        # Process all PDFs at this DPI
        for pdf_path in pdf_paths:
            pdf_results = run_single_pdf_at_dpi(pdf_path, dpi)
            all_results.extend(pdf_results)

            for result in pdf_results:
                if result['page'] > 0:  # Skip error entries (page 0)
                    total_pages += 1
                    total_ids += len(result['ids'])

        elapsed = time.perf_counter() - start_time
        pages_per_sec = total_pages / elapsed if elapsed > 0 else 0

        # Store results
        results.append({
            'dpi': dpi,
            'total_time_sec': elapsed,
            'pages_processed': total_pages,
            'ids_found': total_ids,
            'pages_per_second': pages_per_sec
        })

        # Cache for accuracy comparison
        dpi_results_cache[dpi] = all_results

        print(f"  Completed in {elapsed:.1f}s ({pages_per_sec:.2f} pages/sec, {total_ids} IDs found)")

    # Create DataFrame
    df = pd.DataFrame(results)

    # Print formatted table
    print("\n=== DPI Benchmark Results ===")
    print(f"{'DPI':<6} | {'Time (s)':<10} | {'Pages':<7} | {'IDs Found':<10} | {'Pages/sec':<10}")
    print("-" * 60)
    for _, row in df.iterrows():
        print(f"{int(row['dpi']):<6} | {row['total_time_sec']:10.1f} | {int(row['pages_processed']):7} | {int(row['ids_found']):10} | {row['pages_per_second']:10.2f}")

    # Identify winner (fastest)
    winner_idx = df['pages_per_second'].idxmax()
    winner = df.iloc[winner_idx]
    print(f"\nWinner: DPI {int(winner['dpi'])} (fastest at {winner['pages_per_second']:.2f} pages/sec)")

    # Compare accuracy between fastest and baseline (300 DPI)
    if 300 in dpi_results_cache and int(winner['dpi']) != 300:
        baseline_ids = dpi_results_cache[300]
        winner_ids = dpi_results_cache[int(winner['dpi'])]

        # Count matching IDs
        baseline_count = sum(len(r['ids']) for r in baseline_ids if r['page'] > 0)
        winner_count = sum(len(r['ids']) for r in winner_ids if r['page'] > 0)

        if baseline_count > 0:
            accuracy = (winner_count / baseline_count) * 100
            print(f"Accuracy check: DPI {int(winner['dpi'])} found {winner_count}/{baseline_count} IDs vs DPI 300 baseline ({accuracy:.1f}%)")

    print()
    return df


def benchmark_workers(pdf_paths, worker_counts=[16, 17, 18, 19, 20]):
    """
    Benchmark different worker counts on the sample corpus.

    Per D-04: Test worker counts 16-20 on 20-core hybrid CPU.
    Uses multiprocessing.Pool with the main pipeline's process_all_pdfs function.

    Args:
        pdf_paths: List of Path objects to process
        worker_counts: List of worker counts to test (default [16, 17, 18, 19, 20])

    Returns:
        pandas DataFrame with columns: workers, total_time_sec, pdfs_processed, pdfs_per_second
    """
    print("\n=== Worker Count Benchmark ===")
    print("Testing worker counts:", worker_counts)
    print()

    results = []

    for workers in worker_counts:
        print(f"Testing {workers} workers...")

        start_time = time.perf_counter()

        # Use the main pipeline's process_all_pdfs function
        # Pass minimal args (no checkpointing, no campaign state)
        try:
            pdf_results = process_all_pdfs(
                pdf_paths=pdf_paths,
                workers=workers,
                checkpointed_results=None,
                checkpoint_path=None,
                input_path='',
                checkpoint_frequency=999999,  # Effectively disable checkpointing
                campaign_state=None,
                output_dir=None
            )
        except KeyboardInterrupt:
            print("  Benchmark interrupted by user.")
            break

        elapsed = time.perf_counter() - start_time
        pdfs_per_sec = len(pdf_paths) / elapsed if elapsed > 0 else 0

        # Store results
        results.append({
            'workers': workers,
            'total_time_sec': elapsed,
            'pdfs_processed': len(pdf_paths),
            'pdfs_per_second': pdfs_per_sec
        })

        print(f"  Completed in {elapsed:.1f}s ({pdfs_per_sec:.3f} PDFs/sec)")

    # Create DataFrame
    df = pd.DataFrame(results)

    # Print formatted table
    print("\n=== Worker Count Benchmark Results ===")
    print(f"{'Workers':<8} | {'Time (s)':<10} | {'PDFs':<7} | {'PDFs/sec':<10}")
    print("-" * 45)
    for _, row in df.iterrows():
        print(f"{int(row['workers']):<8} | {row['total_time_sec']:10.1f} | {int(row['pdfs_processed']):7} | {row['pdfs_per_second']:10.3f}")

    # Identify winner (fastest)
    if not df.empty:
        winner_idx = df['pdfs_per_second'].idxmax()
        winner = df.iloc[winner_idx]
        print(f"\nWinner: {int(winner['workers'])} workers (fastest at {winner['pdfs_per_second']:.3f} PDFs/sec)")

    print()
    return df


def benchmark_whitelist(pdf_paths, sample_count=20):
    """
    Benchmark whitelist impact on OCR speed.

    Per D-05: Compare speed with vs without character whitelist.
    Tests on a smaller subset (20 PDFs) since this is a per-page OCR config test.

    Args:
        pdf_paths: List of Path objects to process
        sample_count: Number of PDFs to test (default 20)

    Returns:
        pandas DataFrame with columns: config, total_time_sec, pages_processed, time_per_page_ms
    """
    print("\n=== Whitelist Benchmark ===")
    print(f"Testing on {sample_count} PDFs...")
    print()

    # Take a smaller sample for this test
    test_pdfs = pdf_paths[:sample_count]

    configs = [
        ('With whitelist', '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789'),
        ('Without whitelist', '--psm 6 --oem 3')
    ]

    results = []

    for config_name, config_string in configs:
        print(f"Testing: {config_name}")

        start_time = time.perf_counter()
        total_pages = 0

        # Process each PDF page-by-page
        for pdf_path in test_pdfs:
            try:
                doc = fitz.open(str(pdf_path))
            except Exception:
                continue

            try:
                for page_idx in range(len(doc)):
                    page = doc[page_idx]
                    pix = page.get_pixmap(dpi=300, alpha=False)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    # Run OCR with this config for all 4 rotations
                    for angle in [90, 270, 0, 180]:
                        if angle == 0:
                            rotated_image = img
                        else:
                            rotated_image = img.rotate(angle, expand=True)

                        # Direct OCR call with specific config
                        _ = pytesseract.image_to_string(rotated_image, config=config_string).strip()

                    total_pages += 1
            finally:
                doc.close()

        elapsed = time.perf_counter() - start_time
        time_per_page = (elapsed / total_pages * 1000) if total_pages > 0 else 0

        results.append({
            'config': config_name,
            'total_time_sec': elapsed,
            'pages_processed': total_pages,
            'time_per_page_ms': time_per_page
        })

        print(f"  Completed in {elapsed:.1f}s ({time_per_page:.1f} ms/page)")

    # Create DataFrame
    df = pd.DataFrame(results)

    # Print formatted table
    print("\n=== Whitelist Benchmark Results ===")
    print(f"{'Config':<20} | {'Time (s)':<10} | {'Pages':<7} | {'ms/page':<10}")
    print("-" * 55)
    for _, row in df.iterrows():
        print(f"{row['config']:<20} | {row['total_time_sec']:10.1f} | {int(row['pages_processed']):7} | {row['time_per_page_ms']:10.1f}")

    # Calculate speedup
    if len(results) == 2:
        with_whitelist = results[0]['time_per_page_ms']
        without_whitelist = results[1]['time_per_page_ms']
        if without_whitelist > 0:
            speedup = ((without_whitelist - with_whitelist) / without_whitelist) * 100
            if speedup > 0:
                print(f"\nSpeedup: Whitelist is {speedup:.1f}% faster")
            else:
                print(f"\nSlowdown: Whitelist is {abs(speedup):.1f}% slower")

    print()
    return df


def validate_accuracy(sample_results, baseline_csv_path):
    """
    Validate accuracy by comparing against v1.1 baseline results.

    Per D-08: Page-by-page ID comparison against v1.1 baseline.
    Accuracy = percentage of matching ID extractions.

    Args:
        sample_results: List of result dicts from benchmark run
        baseline_csv_path: Path to v1.1 baseline CSV file

    Returns:
        Accuracy percentage (float)
    """
    print("\n=== Accuracy Validation ===")
    print(f"Loading baseline from: {baseline_csv_path}")

    # Load baseline CSV
    try:
        baseline_df = pd.read_csv(baseline_csv_path)
    except Exception as e:
        print(f"ERROR: Could not load baseline CSV: {e}")
        return 0.0

    # Group baseline by (filename, page) -> set of IDs
    baseline_ids = defaultdict(set)
    for _, row in baseline_df.iterrows():
        if pd.notna(row.get('id')):
            key = (row['filename'], int(row['page']))
            baseline_ids[key].add(str(int(row['id'])))

    # Group sample results by (filename, page) -> set of IDs
    # Normalize to int to strip leading zeros (e.g., "00688" -> "688")
    sample_ids = defaultdict(set)
    for result in sample_results:
        if result['page'] > 0:  # Skip error entries
            key = (result['filename'], result['page'])
            for id_val in result['ids']:
                try:
                    sample_ids[key].add(str(int(id_val)))
                except (ValueError, TypeError):
                    sample_ids[key].add(str(id_val))

    # Compare pages present in BOTH
    common_keys = set(baseline_ids.keys()) & set(sample_ids.keys())

    if not common_keys:
        print("WARNING: No common pages found between baseline and sample.")
        return 0.0

    matches = 0
    mismatches = []

    for key in common_keys:
        baseline_set = baseline_ids[key]
        sample_set = sample_ids[key]

        if baseline_set == sample_set:
            matches += 1
        else:
            mismatches.append((key, baseline_set, sample_set))

    # Calculate accuracy
    total_compared = len(common_keys)
    accuracy = (matches / total_compared * 100) if total_compared > 0 else 0.0

    print(f"Pages compared: {total_compared}")
    print(f"Matches: {matches}")
    print(f"Mismatches: {len(mismatches)}")
    print(f"Accuracy: {accuracy:.2f}%")

    # Print mismatches (first 10)
    if mismatches:
        print("\nFirst 10 mismatches:")
        print(f"{'Filename':<30} | {'Page':<5} | {'Baseline IDs':<20} | {'Sample IDs':<20}")
        print("-" * 85)
        for (filename, page), baseline_set, sample_set in mismatches[:10]:
            baseline_str = ','.join(sorted(baseline_set)) if baseline_set else '(none)'
            sample_str = ','.join(sorted(sample_set)) if sample_set else '(none)'
            print(f"{filename:<30} | {page:<5} | {baseline_str:<20} | {sample_str:<20}")

    # Assert against 94% threshold
    print()
    if accuracy >= 94.0:
        print(f"PASS: Accuracy {accuracy:.2f}% >= 94% baseline threshold")
    else:
        print(f"FAIL: Accuracy {accuracy:.2f}% < 94% baseline threshold")

    print()
    return accuracy


def process_pdf_with_config(pdf_path, tesseract_config, dpi=200):
    """
    Process a single PDF with a specific Tesseract config string.

    Reimplements the rotation loop from extract_id_with_rotation() to allow
    config injection for benchmarking. Does NOT modify the main pipeline.

    Per D-01: Enables independent testing of each config variant.
    Per D-02: Reuses Phase 10 benchmark infrastructure patterns.

    Args:
        pdf_path: Path to PDF file
        tesseract_config: Full Tesseract config string (e.g., '--psm 6 --oem 1 ...')
        dpi: Rendering DPI (default 200, Phase 10 winner)

    Returns:
        List of result dicts with keys: filename, page, ids, rotation_detected, notes
    """
    filename = Path(pdf_path).name

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        return [{
            'filename': filename,
            'page': 0,
            'ids': [],
            'rotation_detected': None,
            'notes': f'error: {type(e).__name__}: {e}'
        }]

    try:
        results = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            # Render at specified DPI
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # === Direct OCR attempt with custom config ===
            ids_found = []
            rotation_found = None
            notes = ''

            for angle in [90, 270, 0, 180]:  # Same order as main pipeline
                if angle == 0:
                    rotated_image = img
                else:
                    rotated_image = img.rotate(angle, expand=True)

                # Run OCR with custom config
                text = pytesseract.image_to_string(rotated_image, config=tesseract_config).strip()

                # Normalize digit confusion characters
                normalized_text = normalize_digits(text)

                # Find 5-digit numbers with word boundaries
                matches = re.findall(r'\b\d{5}\b', normalized_text)

                if matches:
                    # Select all valid IDs from this rotation
                    selected_ids = select_all_valid_ids(matches)
                    if selected_ids:
                        ids_found = selected_ids
                        rotation_found = angle
                        notes = ''
                        break  # Early exit on match

            # === Preprocessing fallback (if no direct match) ===
            if not ids_found:
                preprocessed = preprocess_image(img)

                for angle in [90, 270, 0, 180]:
                    if angle == 0:
                        rotated_image = preprocessed
                    else:
                        rotated_image = preprocessed.rotate(angle, expand=True)

                    text = pytesseract.image_to_string(rotated_image, config=tesseract_config).strip()
                    normalized_text = normalize_digits(text)
                    matches = re.findall(r'\b\d{5}\b', normalized_text)

                    if matches:
                        selected_ids = select_all_valid_ids(matches)
                        if selected_ids:
                            ids_found = selected_ids
                            rotation_found = angle
                            notes = 'preprocessed'
                            break

            # If still no match, classify as failure
            if not ids_found:
                notes = 'no_match'

            results.append({
                'filename': filename,
                'page': page_idx + 1,
                'ids': ids_found,
                'rotation_detected': rotation_found if ids_found else None,
                'notes': notes
            })

        return results
    finally:
        doc.close()


def generate_baseline_csv(corpus_dir, output_path, sample_size=100, seed=42):
    """
    Generate Phase 10 baseline CSV for accuracy comparison.

    Runs current pipeline config (PSM 6, OEM 3, whitelist, DPI 200) on
    the benchmark sample and saves results for later comparison.

    Per D-03: This captures the Phase 10 DPI-200 baseline state.

    Args:
        corpus_dir: Path to PDF corpus directory
        output_path: Path to save baseline CSV
        sample_size: Number of PDFs to sample (default 100)
        seed: Random seed (default 42)

    Returns:
        Path to generated CSV file
    """
    print("\n=== Generating Phase 10 Baseline CSV ===")

    # Select sample corpus
    sample_pdfs = select_benchmark_corpus(corpus_dir, sample_size, seed)

    if not sample_pdfs:
        print("ERROR: No PDFs to process.")
        return None

    # Process all PDFs at DPI 200 (Phase 10 winner)
    print("Processing PDFs at DPI 200 (Phase 10 baseline)...")
    all_results = []
    for pdf_path in sample_pdfs:
        pdf_results = run_single_pdf_at_dpi(pdf_path, 200)
        all_results.extend(pdf_results)

    # Flatten results into rows: one row per ID (or one row per page if no IDs)
    rows = []
    for result in all_results:
        if result['page'] == 0:  # Skip error entries
            continue

        if result['ids']:
            # One row per ID found
            for id_val in result['ids']:
                rows.append({
                    'filename': result['filename'],
                    'page': result['page'],
                    'id': id_val,
                    'rotation_detected': result['rotation_detected'],
                    'notes': result['notes']
                })
        else:
            # One row with empty ID for pages with no match
            rows.append({
                'filename': result['filename'],
                'page': result['page'],
                'id': '',
                'rotation_detected': result['rotation_detected'],
                'notes': result['notes']
            })

    # Create DataFrame and save
    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)

    # Print summary
    total_pdfs = len(sample_pdfs)
    total_pages = len([r for r in all_results if r['page'] > 0])
    total_ids = sum(len(r['ids']) for r in all_results if r['page'] > 0)

    print(f"\n=== Baseline CSV Generated ===")
    print(f"Total PDFs: {total_pdfs}")
    print(f"Total pages: {total_pages}")
    print(f"Total IDs: {total_ids}")
    print(f"Output: {output_path}")
    print()

    return output_path


def benchmark_tesseract_config(corpus_dir, baseline_csv=None, sample_size=100, seed=42):
    """
    Benchmark Tesseract config variants: OEM 1, PSM 7, dict-off.

    Per D-01: Test each config independently first, then test winning combinations.
    Per D-02: Reuse Phase 10 benchmark infrastructure.
    Per D-03: Compare against Phase 10 DPI-200 baseline.
    Per D-07: >=94% PASS, 93-94% SOFT (user decides), <93% FAIL.

    Args:
        corpus_dir: Path to PDF corpus directory
        baseline_csv: Path to Phase 10 baseline CSV for accuracy comparison (optional)
        sample_size: Number of PDFs to sample (default 100)
        seed: Random seed (default 42)

    Returns:
        pandas DataFrame with results for all tested configs
    """
    print("\n=== Phase 11: Tesseract Config Benchmark ===")

    # Select benchmark corpus (reuse Phase 10 infrastructure)
    sample_pdfs = select_benchmark_corpus(corpus_dir, sample_size, seed)

    if not sample_pdfs:
        print("ERROR: No PDFs to process.")
        return pd.DataFrame()

    # Define config variants (D-01: independent testing)
    configs = {
        'baseline_phase10': '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789',
        'oem1_only': '--psm 6 --oem 1 -c tessedit_char_whitelist=0123456789',
        'psm7_only': '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789',
        'dict_off_only': '--psm 6 --oem 3 -c tessedit_char_whitelist=0123456789 -c load_system_dawg=false -c load_freq_dawg=false',
    }

    results = []
    all_config_results = {}  # Store detailed results for accuracy validation

    print("\n=== Phase 1: Independent Config Testing ===\n")

    for config_name, config_string in configs.items():
        print(f"Testing: {config_name}")

        start_time = time.perf_counter()
        all_results = []

        # Process all PDFs in sample with this config
        for pdf_path in sample_pdfs:
            pdf_results = process_pdf_with_config(pdf_path, config_string, dpi=200)
            all_results.extend(pdf_results)

        elapsed = time.perf_counter() - start_time

        # Calculate stats
        total_pages = len([r for r in all_results if r['page'] > 0])
        total_ids = sum(len(r['ids']) for r in all_results if r['page'] > 0)
        ms_per_page = (elapsed / total_pages * 1000) if total_pages > 0 else 0

        # Store results for this config
        result = {
            'config': config_name,
            'duration_sec': elapsed,
            'pages': total_pages,
            'ids_found': total_ids,
            'ms_per_page': ms_per_page,
            'accuracy_pct': None,
            'pass_fail': 'N/A'
        }

        # Accuracy validation if baseline provided
        if baseline_csv:
            accuracy = validate_accuracy(all_results, baseline_csv)
            result['accuracy_pct'] = accuracy

            # Per D-07: classify result
            if accuracy >= 94.0:
                result['pass_fail'] = 'PASS'
            elif accuracy >= 93.0:
                result['pass_fail'] = 'SOFT'
            else:
                result['pass_fail'] = 'FAIL'

        results.append(result)
        all_config_results[config_name] = all_results

        print(f"  Completed: {elapsed:.1f}s, {ms_per_page:.1f} ms/page, {total_ids} IDs")
        if baseline_csv:
            print(f"  Accuracy: {result['accuracy_pct']:.2f}% ({result['pass_fail']})")
        print()

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Calculate speedup vs baseline
    baseline_row = df[df['config'] == 'baseline_phase10']
    if not baseline_row.empty:
        baseline_ms = baseline_row['ms_per_page'].values[0]
        df['speedup_vs_baseline'] = baseline_ms / df['ms_per_page']
    else:
        df['speedup_vs_baseline'] = 1.0

    # Print formatted comparison table
    print("\n=== Independent Config Results ===")
    print(f"{'Config':<20} | {'Duration (s)':<12} | {'Pages':<7} | {'IDs':<6} | {'ms/page':<8} | {'Speedup':<8} | {'Accuracy':<10} | {'Pass/Fail':<10}")
    print("-" * 115)
    for _, row in df.iterrows():
        accuracy_str = f"{row['accuracy_pct']:.2f}%" if row['accuracy_pct'] is not None else "N/A"
        print(f"{row['config']:<20} | {row['duration_sec']:12.1f} | {int(row['pages']):7} | {int(row['ids_found']):6} | {row['ms_per_page']:8.1f} | {row['speedup_vs_baseline']:8.2f}x | {accuracy_str:<10} | {row['pass_fail']:<10}")

    # === Phase 2: Combination Testing (D-01) ===
    winners = df[(df['pass_fail'].isin(['PASS', 'SOFT'])) & (df['config'] != 'baseline_phase10')]

    if len(winners) >= 2:
        print("\n=== Phase 2: Combination Testing ===\n")

        winner_names = winners['config'].tolist()

        # Build combination configs from winning individual flags
        oem_flag = '--oem 1' if 'oem1_only' in winner_names else '--oem 3'
        psm_flag = '--psm 7' if 'psm7_only' in winner_names else '--psm 6'
        dict_flags = ' -c load_system_dawg=false -c load_freq_dawg=false' if 'dict_off_only' in winner_names else ''

        combo_configs = {}

        if len(winner_names) == 2:
            # One combination: both winners
            combo_name = '+'.join(w.replace('_only', '') for w in winner_names)
            combo_config = f'{psm_flag} {oem_flag} -c tessedit_char_whitelist=0123456789{dict_flags}'
            combo_configs[combo_name] = combo_config

        elif len(winner_names) == 3:
            # Test all three pairs + the triple
            pairs = [
                ('oem1_only', 'psm7_only'),
                ('oem1_only', 'dict_off_only'),
                ('psm7_only', 'dict_off_only')
            ]

            for pair in pairs:
                if pair[0] in winner_names and pair[1] in winner_names:
                    pair_oem = '--oem 1' if 'oem1' in pair[0] else '--oem 3'
                    pair_psm = '--psm 7' if 'psm7' in pair[0] or 'psm7' in pair[1] else '--psm 6'
                    pair_dict = ' -c load_system_dawg=false -c load_freq_dawg=false' if 'dict_off' in pair[0] or 'dict_off' in pair[1] else ''

                    pair_name = '+'.join(p.replace('_only', '') for p in pair)
                    pair_config = f'{pair_psm} {pair_oem} -c tessedit_char_whitelist=0123456789{pair_dict}'
                    combo_configs[pair_name] = pair_config

            # Triple combination
            combo_configs['all_three'] = f'{psm_flag} {oem_flag} -c tessedit_char_whitelist=0123456789{dict_flags}'

        # Test each combination
        for combo_name, combo_config in combo_configs.items():
            print(f"Testing combination: {combo_name}")

            start_time = time.perf_counter()
            all_results = []

            for pdf_path in sample_pdfs:
                pdf_results = process_pdf_with_config(pdf_path, combo_config, dpi=200)
                all_results.extend(pdf_results)

            elapsed = time.perf_counter() - start_time

            total_pages = len([r for r in all_results if r['page'] > 0])
            total_ids = sum(len(r['ids']) for r in all_results if r['page'] > 0)
            ms_per_page = (elapsed / total_pages * 1000) if total_pages > 0 else 0

            result = {
                'config': combo_name,
                'duration_sec': elapsed,
                'pages': total_pages,
                'ids_found': total_ids,
                'ms_per_page': ms_per_page,
                'accuracy_pct': None,
                'pass_fail': 'N/A',
                'speedup_vs_baseline': baseline_ms / ms_per_page if baseline_ms > 0 else 1.0
            }

            if baseline_csv:
                accuracy = validate_accuracy(all_results, baseline_csv)
                result['accuracy_pct'] = accuracy

                if accuracy >= 94.0:
                    result['pass_fail'] = 'PASS'
                elif accuracy >= 93.0:
                    result['pass_fail'] = 'SOFT'
                else:
                    result['pass_fail'] = 'FAIL'

            results.append(result)

            print(f"  Completed: {elapsed:.1f}s, {ms_per_page:.1f} ms/page, {total_ids} IDs")
            if baseline_csv:
                print(f"  Accuracy: {result['accuracy_pct']:.2f}% ({result['pass_fail']})")
            print()

        # Update DataFrame with combination results
        df = pd.DataFrame(results)

        # Recalculate speedup for all rows (individual results lack it after DataFrame rebuild)
        if baseline_ms > 0:
            df['speedup_vs_baseline'] = baseline_ms / df['ms_per_page']

    # === Phase 3: Summary ===
    print("\n=== Phase 11 Tesseract Config Benchmark Summary ===")

    # Find best individual config (excluding baseline)
    individual_configs = df[~df['config'].str.contains(r'\+|all_three', regex=True) & (df['config'] != 'baseline_phase10')]
    if not individual_configs.empty:
        best_individual = individual_configs.loc[individual_configs['speedup_vs_baseline'].idxmax()]
        print(f"Best individual config: {best_individual['config']} ({best_individual['speedup_vs_baseline']:.2f}x speedup, {best_individual['accuracy_pct']:.2f}% accuracy, {best_individual['pass_fail']})")

    # Find best combination (if any)
    combination_configs = df[df['config'].str.contains(r'\+|all_three', regex=True)]
    if not combination_configs.empty:
        best_combo = combination_configs.loc[combination_configs['speedup_vs_baseline'].idxmax()]
        print(f"Best combination: {best_combo['config']} ({best_combo['speedup_vs_baseline']:.2f}x speedup, {best_combo['accuracy_pct']:.2f}% accuracy, {best_combo['pass_fail']})")

    # Recommend best passing config overall
    passing_configs = df[df['pass_fail'].isin(['PASS', 'SOFT']) & (df['config'] != 'baseline_phase10')]
    if not passing_configs.empty:
        recommended = passing_configs.loc[passing_configs['speedup_vs_baseline'].idxmax()]
        print(f"\nRecommended config: {recommended['config']} ({recommended['speedup_vs_baseline']:.2f}x speedup, {recommended['accuracy_pct']:.2f}% accuracy)")
    else:
        print("\nNo configs passed accuracy threshold. Recommend keeping baseline_phase10.")

    print("\nPer D-08: Ship any improvement regardless of magnitude.")
    print("Per D-07: Configs marked SOFT require user decision.")
    print()

    return df


def main():
    """
    Main entry point for benchmark script.

    Runs DPI, worker count, and whitelist benchmarks on a sample corpus.
    Optionally validates accuracy against v1.1 baseline.
    """
    parser = argparse.ArgumentParser(
        description="Phase 10 Benchmark Script — DPI, Worker Count, Whitelist, and Accuracy Validation"
    )
    parser.add_argument('corpus_dir', help="Path to PDF corpus directory")
    parser.add_argument('--baseline-csv', help="Path to v1.1 baseline CSV for accuracy comparison")
    parser.add_argument('--sample-size', type=int, default=100, help="Number of PDFs to sample (default: 100)")
    parser.add_argument('--seed', type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument('--skip-dpi', action='store_true', help="Skip DPI benchmark")
    parser.add_argument('--skip-workers', action='store_true', help="Skip worker count benchmark")
    parser.add_argument('--skip-whitelist', action='store_true', help="Skip whitelist benchmark")
    parser.add_argument('--tesseract-config', action='store_true',
        help="Run Phase 11 Tesseract config benchmark (OEM/PSM/dict)")
    parser.add_argument('--generate-baseline', type=str, default=None,
        help="Generate Phase 10 baseline CSV at specified path")

    args = parser.parse_args()

    # Select sample corpus
    sample_pdfs = select_benchmark_corpus(args.corpus_dir, args.sample_size, args.seed)

    if not sample_pdfs:
        print("No PDFs to process. Exiting.")
        return

    dpi_results_300 = None  # Store DPI 300 results for accuracy validation

    # Run DPI benchmark
    if not args.skip_dpi:
        dpi_df = benchmark_dpi(sample_pdfs, dpi_values=[200, 250, 300])

    # Run worker benchmark
    if not args.skip_workers:
        worker_df = benchmark_workers(sample_pdfs, worker_counts=[16, 17, 18, 19, 20])

    # Run whitelist benchmark
    if not args.skip_whitelist:
        whitelist_df = benchmark_whitelist(sample_pdfs, sample_count=20)

    # Validate accuracy if baseline provided (Phase 10 validation)
    if args.baseline_csv and not args.tesseract_config:
        # Run at DPI 300 for accuracy validation
        print("\nRunning DPI 300 for accuracy validation...")
        validation_results = []
        for pdf_path in sample_pdfs:
            validation_results.extend(run_single_pdf_at_dpi(pdf_path, 300))

        accuracy = validate_accuracy(validation_results, args.baseline_csv)

    # Generate baseline CSV if requested (Phase 11)
    if args.generate_baseline:
        generate_baseline_csv(args.corpus_dir, args.generate_baseline,
                             args.sample_size, args.seed)

    # Run Tesseract config benchmark (Phase 11)
    if args.tesseract_config:
        config_df = benchmark_tesseract_config(
            args.corpus_dir,
            baseline_csv=args.baseline_csv,
            sample_size=args.sample_size,
            seed=args.seed
        )

    # Print summary
    print("\n=== Benchmark Complete ===")
    print("Review the results above to determine optimal settings.")
    print()


if __name__ == '__main__':
    main()
