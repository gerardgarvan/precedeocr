"""
Phase 10 Benchmark Script — DPI, Worker Count, Whitelist, and Accuracy Validation.

Usage:
    python benchmark.py <corpus_dir> [--baseline-csv <path>] [--sample-size 100] [--seed 42]

This script benchmarks the Precede OCR pipeline across different configurations
to find optimal DPI and worker count settings. Results are printed as comparison
tables and optionally saved to CSV.

Per D-06: Standalone script, not integrated into main pipeline.
Per D-07: Uses 100-PDF random sample for iteration speed.
Per D-08: Accuracy validated by comparing IDs page-by-page against v1.1 baseline.
"""

import argparse
import random
import time
import multiprocessing as mp
from pathlib import Path
from collections import defaultdict
import fitz  # PyMuPDF
from PIL import Image
import pandas as pd
import pytesseract

# Import from main pipeline
from precede_ocr import extract_id_with_rotation, process_all_pdfs


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
            baseline_ids[key].add(str(row['id']))

    # Group sample results by (filename, page) -> set of IDs
    sample_ids = defaultdict(set)
    for result in sample_results:
        if result['page'] > 0:  # Skip error entries
            key = (result['filename'], result['page'])
            for id_val in result['ids']:
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

    # Validate accuracy if baseline provided
    if args.baseline_csv:
        # Run at DPI 300 for accuracy validation
        print("\nRunning DPI 300 for accuracy validation...")
        validation_results = []
        for pdf_path in sample_pdfs:
            validation_results.extend(run_single_pdf_at_dpi(pdf_path, 300))

        accuracy = validate_accuracy(validation_results, args.baseline_csv)

    # Print summary
    print("\n=== Benchmark Complete ===")
    print("Review the results above to determine optimal settings.")
    print()


if __name__ == '__main__':
    main()
