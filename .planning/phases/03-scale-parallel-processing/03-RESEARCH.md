# Phase 3: Scale — Parallel Processing - Research

**Researched:** 2026-06-05
**Domain:** Python multiprocessing for CPU-bound OCR batch processing on Windows
**Confidence:** HIGH

## Summary

Phase 3 implements parallel processing to scale from single-file to 30K+ PDFs efficiently, while also adding support for multiple IDs per page (PIPE-06), no-ID page flagging (PIPE-07), JSON output (OUT-02), and progress tracking (PROG-01). The phase modifies existing single-file processing to work in a parallel context and aggregates results across workers.

Python's `multiprocessing.Pool` with `imap_unordered()` is the standard approach for CPU-bound batch processing on Windows. The existing `process_single_pdf()` function is already a self-contained worker unit requiring minimal changes. Key challenges: Windows spawn requirements (`if __name__ == '__main__'`), memory leaks from Tesseract over 30K files (solved via process recycling), tqdm integration for progress visibility, and result aggregation from multiple workers.

**Primary recommendation:** Use `multiprocessing.Pool` with `imap_unordered()` for file-level parallelism, `maxtasksperchild=50` for process recycling, tqdm wrapping the iterator for progress bars, and nested dict JSON structure (`{"file.pdf": {"1": ["12345"], "2": []}}`) for easy file-based lookups.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Multiple IDs per page:**
- **D-01:** One row per ID in CSV output. Same page appears in multiple rows when it has multiple IDs. Easy to filter/sort in Excel.
- **D-02:** Keep early exit on first successful rotation. Return ALL valid 5-digit matches from that rotation, not just the first. Assumes all IDs on a page share the same orientation.
- **D-03:** Continue filtering trivial/repeating patterns (00000, 11111, etc.). These are OCR noise, not real Precede IDs.

**JSON output structure:**
- **D-04:** Nested by filename structure: `{"file.pdf": {"1": ["12345"], "2": ["67890", "11234"], "3": []}}`. Pages with no ID show as empty array. Natural for browsing by file.
- **D-05:** Always generate both CSV and JSON in every run. No flags needed — both are lightweight to produce.

**Worker configuration & memory:**
- **D-06:** Default worker count = cpu_count() - 1 (leave one core free). User can override with `--workers N` flag.
- **D-07:** Process recycling via maxtasksperchild=50. Workers are recycled after processing 50 PDFs to prevent memory growth from Tesseract leaks over 30K+ files.

**Progress display:**
- **D-08:** Per-file progress bar using tqdm. Tracks files completed out of total (not per-page). Shows ETA, rate.
- **D-09:** Inline stats in tqdm postfix showing running counts: IDs found, no-ID pages, errors. Gives confidence the pipeline is working throughout the run.

### Claude's Discretion
- Exact tqdm configuration (bar format, refresh interval)
- multiprocessing.Pool vs concurrent.futures.ProcessPoolExecutor choice
- How to aggregate results from workers (queue vs return values)
- Batch size for imap_unordered chunking
- Output file naming when input is a directory (output/results.csv, output/results.json)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-06 | Multiple IDs on a single page are all captured | Regex `findall()` returns all matches as list; modify `select_most_likely_id()` to filter and return all valid IDs instead of first only |
| PIPE-07 | Pages where no ID is found are flagged in output (not silently dropped) | Already partially implemented via notes column; ensure empty list `[]` appears in JSON for no-match pages |
| OUT-02 | Results are written as JSON mapping filename to pages to IDs | Nested dict structure using pandas groupby or manual aggregation; Decision D-04 specifies exact format |
| PROG-01 | Processing progress is displayed (file count and/or percentage complete) | tqdm wrapping `pool.imap_unordered()` with `total=len(pdf_paths)` provides file-level progress bar with ETA |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **multiprocessing** | stdlib | CPU-bound parallel processing | Python stdlib. Required for scaling OCR across 30K+ PDFs. Pool.imap_unordered() with tqdm for progress. Windows uses 'spawn' start method. **Confidence: HIGH** |
| **tqdm** | 4.67.3 (verified installed) | Progress bar visualization | De facto standard for progress bars. Works with multiprocessing via wrapping iterators. Low overhead (60ns/iter). Essential UX for batch jobs. **Confidence: HIGH** |
| **pandas** | 3.0.3 (verified installed) | CSV/JSON export and aggregation | Already used for CSV output. Supports nested JSON via `to_json(orient='records')` or custom dict construction with `groupby()`. **Confidence: HIGH** |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pathlib** | stdlib | Directory recursion, glob patterns | `Path.glob('**/*.pdf')` for recursive PDF discovery. Already used in existing code. **Confidence: HIGH** |
| **argparse** | stdlib | CLI argument parsing | Extend existing argparse to accept directory input and `--workers` flag. **Confidence: HIGH** |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| multiprocessing.Pool | concurrent.futures.ProcessPoolExecutor | ProcessPoolExecutor has simpler API and slightly lower memory overhead, but Pool has more direct control over chunking and worker lifecycle. Pool is more common in OCR pipelines. Both are viable. **Confidence: MEDIUM** |
| imap_unordered | map | `map()` blocks until all tasks complete before returning results; `imap_unordered()` yields results as they complete, enabling streaming to tqdm. imap_unordered required for progress visibility. **Confidence: HIGH** |
| Manual dict construction | pandas groupby + to_json | Both work. Manual dict construction gives precise control over nested structure per D-04. pandas groupby is cleaner but may need post-processing. Recommend manual for clarity. **Confidence: MEDIUM** |

**Installation:**
```bash
# tqdm already installed (verified: 4.67.3)
# multiprocessing, pathlib, argparse are stdlib (no install needed)
# pandas already installed (verified: 3.0.3)
```

**Version verification:**
```bash
# Already verified via environment checks:
# - Python 3.14.2
# - tqdm 4.67.3
# - pandas 3.0.3
# - multiprocessing stdlib (cpu_count: 24 cores)
```

## Architecture Patterns

### Recommended Project Structure
```
precedeocr/
├── precede_ocr.py           # Main script (extends to multiprocessing)
├── tests/
│   └── test_precede_ocr.py  # Unit tests (extend for parallel functions)
├── output/
│   ├── results.csv          # CSV output (one row per ID)
│   └── results.json         # JSON output (nested by filename)
└── requirements.txt         # Add tqdm if not present
```

### Pattern 1: File-Level Parallelism with Pool.imap_unordered
**What:** Each worker process handles one complete PDF file end-to-end. Results stream back as files complete.
**When to use:** When processing units (PDFs) are independent and order doesn't matter.
**Example:**
```python
# Source: Adapted from official Python multiprocessing docs + tqdm best practices
import multiprocessing as mp
from tqdm import tqdm
from pathlib import Path

def main(pdf_dir, output_csv, output_json, workers=None):
    # Discover all PDF files recursively
    pdf_paths = list(Path(pdf_dir).glob('**/*.pdf'))

    # Default workers: cpu_count() - 1 (per D-06)
    if workers is None:
        workers = max(1, mp.cpu_count() - 1)

    # Create process pool with recycling (per D-07)
    with mp.Pool(processes=workers, maxtasksperchild=50) as pool:
        # Process files with progress bar
        results_list = []
        stats = {'ids_found': 0, 'no_id_pages': 0, 'errors': 0}

        for result in tqdm(
            pool.imap_unordered(process_single_pdf_wrapper, pdf_paths),
            total=len(pdf_paths),
            desc="Processing PDFs",
            unit="file"
        ):
            # result is list[dict] from one PDF
            results_list.extend(result)

            # Update running stats (per D-09)
            stats['ids_found'] += sum(1 for r in result if r['id'])
            stats['no_id_pages'] += sum(1 for r in result if not r['id'])

            # Update tqdm postfix
            tqdm.write(f"IDs: {stats['ids_found']}, No-ID pages: {stats['no_id_pages']}")

        # Write outputs
        write_results_csv(results_list, output_csv)
        write_results_json(results_list, output_json)

if __name__ == '__main__':
    # Windows spawn requirement: protect entry point
    main()
```

### Pattern 2: Multiple IDs Per Page (PIPE-06)
**What:** Modify `select_most_likely_id()` to return list of all valid IDs instead of first match.
**When to use:** When a page can contain multiple Precede IDs.
**Example:**
```python
# Source: Adapted from existing select_most_likely_id() logic
def select_all_valid_ids(matches: list[str]) -> list[str]:
    """
    Filter and return ALL valid Precede IDs from matches.

    Per D-03: Filter out trivial/repeating patterns like 00000, 11111.
    Per D-02: Return all valid candidates from the successful rotation.

    Args:
        matches: List of 5-digit strings from regex matching

    Returns:
        List of valid ID strings (may be empty if no valid candidates)
    """
    trivial_patterns = {
        '00000', '11111', '22222', '33333', '44444',
        '55555', '66666', '77777', '88888', '99999'
    }

    # Filter out noise patterns, return all valid IDs
    filtered = [m for m in matches if m not in trivial_patterns]
    return filtered if filtered else []

# Update extract_id_with_rotation return type:
# OLD: return selected_id, angle, ''
# NEW: return selected_ids_list, angle, ''
```

### Pattern 3: Nested JSON Output Structure (OUT-02)
**What:** Build nested dict `{filename: {page_num: [ids]}}` from flat results list.
**When to use:** For file-based ID lookup (per D-04).
**Example:**
```python
# Source: Manual dict construction (clearer than pandas groupby for this structure)
def write_results_json(results: list[dict], output_path: str) -> None:
    """
    Write results to nested JSON per OUT-02 and D-04.

    Structure: {"file.pdf": {"1": ["12345"], "2": ["67890", "11234"], "3": []}}
    Pages with no ID show as empty array (per D-04, PIPE-07).

    Args:
        results: List of dicts from process_single_pdf()
                 (now with 'ids' as list instead of 'id' as single value)
        output_path: Path to output JSON file
    """
    from pathlib import Path
    import json
    from collections import defaultdict

    # Create output directory if needed
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Build nested structure
    nested = defaultdict(dict)
    for row in results:
        filename = row['filename']
        page = str(row['page'])
        ids = row['ids']  # Now a list, not a single value

        # Store list of IDs for this page (empty list if no IDs per D-04)
        nested[filename][page] = ids

    # Write JSON with indentation for readability
    with open(output_path, 'w') as f:
        json.dump(dict(nested), f, indent=2)

    print(f"JSON output written to {output_path}")
```

### Pattern 4: Progress Bar with Running Statistics (PROG-01, D-08, D-09)
**What:** Wrap `pool.imap_unordered()` with tqdm, update postfix with running stats.
**When to use:** Long-running batch jobs where user needs feedback.
**Example:**
```python
# Source: https://leimao.github.io/blog/Python-tqdm-Multiprocessing/
from tqdm import tqdm

# Initialize tqdm with total count (per D-08: per-file progress)
pbar = tqdm(total=len(pdf_paths), desc="Processing PDFs", unit="file")

for result in pool.imap_unordered(worker_func, pdf_paths):
    # Update progress bar
    pbar.update(1)

    # Update postfix with running stats (per D-09)
    pbar.set_postfix({
        'IDs': total_ids_found,
        'No-ID': total_no_id_pages,
        'Errors': total_errors
    })

pbar.close()
```

### Pattern 5: Windows Spawn Entry Point Protection
**What:** Wrap Pool creation in `if __name__ == '__main__':` guard.
**When to use:** Always on Windows when using multiprocessing.
**Example:**
```python
# Source: https://docs.python.org/3/library/multiprocessing.html
# CRITICAL: Windows uses spawn, requires entry point protection

# At module level: all imports and function definitions

def main():
    # Pool creation and usage here
    with mp.Pool(...) as pool:
        results = pool.imap_unordered(...)

if __name__ == '__main__':
    # Parse args
    args = parser.parse_args()

    # Call main function
    main(args.input_dir, args.output_csv, args.output_json, args.workers)
```

### Anti-Patterns to Avoid
- **Global state in workers:** Windows spawn creates fresh interpreter; shared state must use Manager/Queue, not globals. Existing code already avoids this.
- **Large return values:** Returning huge objects from workers causes IPC overhead. Current design returns list[dict] per file, which is fine.
- **Blocking map():** Using `pool.map()` blocks until all tasks complete, preventing progress updates. Use `imap_unordered()` instead.
- **No process recycling:** Tesseract leaks memory over time. Without `maxtasksperchild`, 30K files will OOM. D-07 specifies `maxtasksperchild=50`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress tracking | Custom print statements, manual counters | tqdm library | tqdm handles terminal width, ETA calculation, rate formatting, concurrent updates. Reinventing loses these features. **Confidence: HIGH** |
| Process pool management | Manual fork/spawn, worker lifecycle | multiprocessing.Pool | Pool handles worker creation, task distribution, result collection, cleanup. Spawn on Windows is complex (requires pickle support, entry point protection). **Confidence: HIGH** |
| Nested JSON from flat data | String concatenation, manual loops | collections.defaultdict + json.dump | defaultdict(dict) auto-creates nested structure. json.dump handles serialization, escaping, formatting. **Confidence: HIGH** |
| Recursive file discovery | os.walk loops, manual recursion | pathlib.Path.glob('**/*.pdf') | Path.glob with `**` is cleaner, cross-platform, and returns Path objects. **Confidence: HIGH** |
| Worker function wrapping | Lambda functions for Pool | Top-level def or functools.partial | Windows spawn requires picklable worker functions. Lambdas and nested defs fail. Use module-level functions. **Confidence: HIGH** |

**Key insight:** Parallel processing on Windows has subtle gotchas (spawn semantics, pickling requirements, process recycling for memory leaks). Using stdlib abstractions (Pool, pathlib) and battle-tested libraries (tqdm) avoids reinventing complex concurrency and progress tracking logic.

## Common Pitfalls

### Pitfall 1: Missing `if __name__ == '__main__':` Guard on Windows
**What goes wrong:** Script launches infinite recursive worker processes, exhausting memory.
**Why it happens:** Windows uses spawn start method, which re-imports the script in each worker. Without the guard, Pool creation happens in workers too, spawning more workers recursively.
**How to avoid:** Always wrap Pool creation and main execution in `if __name__ == '__main__':` block. Move all imports and function defs to module level (outside the guard).
**Warning signs:** Script hangs on Windows, task manager shows dozens of Python processes spawning continuously.
**Source:** [Python multiprocessing documentation](https://docs.python.org/3/library/multiprocessing.html), [SuperFastPython - Add if __name__ == '__main__' When Spawning Processes](https://superfastpython.com/multiprocessing-spawn-runtimeerror/)

### Pitfall 2: Unpicklable Worker Functions
**What goes wrong:** Pool.imap() raises `PickleError` or `AttributeError` when trying to distribute work.
**Why it happens:** Windows spawn serializes worker functions via pickle. Lambda functions, nested functions, and class methods without proper support fail to pickle.
**How to avoid:** Define worker functions at module level (top-level def). If using class methods, ensure class is importable and method is not nested. Use `functools.partial` for parameter binding instead of lambdas.
**Warning signs:** `PickleError: Can't pickle <lambda>`, `AttributeError: Can't get attribute 'worker_func'`.
**Source:** [SuperFastPython - Multiprocessing Pool vs ProcessPoolExecutor](https://superfastpython.com/multiprocessing-pool-vs-processpoolexecutor/), Windows spawn documentation

### Pitfall 3: Memory Leaks from Long-Running Workers
**What goes wrong:** Workers consume increasing memory over thousands of tasks, eventually causing OOM crashes.
**Why it happens:** Tesseract and pdf2image create temporary files and internal buffers. Even with cleanup, memory fragmentation and unreleased resources accumulate over 30K+ files.
**How to avoid:** Set `maxtasksperchild=50` (per D-07) to recycle workers after 50 PDFs. This forces fresh process start, releasing all memory. Trade-off: slight overhead from process creation, but prevents OOM.
**Warning signs:** Memory usage grows monotonically, crash after processing thousands of files, temp directory grows large.
**Source:** [Tesseract OCR mailing list - Python Multiprocessing slows down](https://groups.google.com/g/tesseract-ocr/c/kHJkPoxS8dY/m/xNcplFnMAQAJ), user decision D-07

### Pitfall 4: Blocking with pool.map() Prevents Progress Updates
**What goes wrong:** Progress bar doesn't update until all 30K files finish processing (appears frozen for hours).
**Why it happens:** `pool.map()` blocks until all tasks complete, returning results as a single list. tqdm can't update until map() returns.
**How to avoid:** Use `pool.imap_unordered()` which yields results as they complete. Wrap the iterator with tqdm: `tqdm(pool.imap_unordered(...), total=len(tasks))`.
**Warning signs:** Progress bar shows 0% for extended period, jumps to 100% all at once.
**Source:** [Lei Mao's Blog - Progress Bars for Python Multiprocessing](https://leimao.github.io/blog/Python-tqdm-Multiprocessing/), [Running tqdm with Python multiprocessing](https://rednafi.com/python/tqdm-with-multiprocessing/)

### Pitfall 5: Incorrect Chunksize Causes Performance Issues
**What goes wrong:** Workers sit idle while coordinator distributes tasks one-by-one (high IPC overhead), or all tasks assigned upfront causing imbalanced load.
**Why it happens:** Default `chunksize=1` for `imap_unordered()` means each task sent individually. For 30K files with ~1 second processing time, IPC overhead dominates. Conversely, chunksize too large (e.g., 1000) front-loads work, leaving some workers idle at the end.
**How to avoid:** Use formula `chunksize = max(1, len(tasks) // (4 * num_workers))` as starting point. For 30K files with 23 workers: `30000 // (4 * 23) ≈ 326`. Experiment based on task duration variance.
**Warning signs:** CPU usage fluctuates instead of staying high, tqdm shows erratic rate, workers finish at very different times.
**Source:** [SuperFastPython - Configure Pool.map() Chunksize](https://superfastpython.com/multiprocessing-pool-map-chunksize/), [Multiprocessing Pool.imap_unordered()](https://superfastpython.com/multiprocessing-pool-imap_unordered/)

### Pitfall 6: Shared State Between Workers Corrupts Results
**What goes wrong:** Results are missing, duplicated, or contain data from other files. Race conditions appear.
**Why it happens:** Multiple workers access shared data structures (global dicts, class attributes) without synchronization. Windows spawn creates fresh processes, so this is less common than on Unix, but still possible if using Manager objects incorrectly.
**How to avoid:** Keep workers stateless. Pass all inputs as function arguments, return all outputs as return values. Existing `process_single_pdf()` already follows this pattern (no shared state).
**Warning signs:** Inconsistent results between runs, missing or extra records in output, exceptions about concurrent access.
**Source:** [Python multiprocessing documentation - Programming guidelines](https://docs.python.org/3/library/multiprocessing.html#programming-guidelines)

## Code Examples

Verified patterns from official sources and existing implementation:

### Recursive PDF Discovery
```python
# Source: Python pathlib documentation
from pathlib import Path

def discover_pdfs(input_path: str) -> list[Path]:
    """
    Recursively discover all PDF files in directory, or return single file.

    Args:
        input_path: Path to PDF file or directory

    Returns:
        List of Path objects for PDF files
    """
    path = Path(input_path)

    if path.is_file():
        if path.suffix.lower() == '.pdf':
            return [path]
        else:
            raise ValueError(f"Not a PDF file: {input_path}")
    elif path.is_dir():
        # Recursive glob: ** matches all subdirectories
        return sorted(path.glob('**/*.pdf'))
    else:
        raise FileNotFoundError(f"Path not found: {input_path}")
```

### Worker Function for Multiprocessing
```python
# Source: Adapted from existing process_single_pdf()
def process_single_pdf_wrapper(pdf_path: Path) -> list[dict]:
    """
    Wrapper for multiprocessing: converts Path to str, handles errors.

    Must be top-level function for Windows spawn pickling.

    Args:
        pdf_path: Path object for PDF file

    Returns:
        List of result dicts (one per page), or error dict if processing fails
    """
    try:
        # Convert Path to str for existing function
        results = process_single_pdf(str(pdf_path), debug=False)
        return results
    except Exception as e:
        # Return error record instead of crashing worker
        return [{
            'filename': pdf_path.name,
            'page': 0,
            'ids': [],
            'rotation_detected': None,
            'notes': f'error: {type(e).__name__}: {str(e)}'
        }]
```

### Aggregating Results with Progress and Stats
```python
# Source: https://rednafi.com/python/tqdm-with-multiprocessing/
import multiprocessing as mp
from tqdm import tqdm

def process_all_pdfs(pdf_paths: list[Path], workers: int) -> list[dict]:
    """
    Process all PDFs in parallel with progress bar and running stats.

    Args:
        pdf_paths: List of PDF file paths
        workers: Number of worker processes

    Returns:
        Flat list of all result dicts from all files
    """
    all_results = []
    stats = {'ids': 0, 'no_id_pages': 0, 'errors': 0}

    # Create pool with process recycling (D-07)
    with mp.Pool(processes=workers, maxtasksperchild=50) as pool:
        # Calculate chunksize for efficient distribution
        chunksize = max(1, len(pdf_paths) // (4 * workers))

        # Process with progress bar (D-08)
        for file_results in tqdm(
            pool.imap_unordered(
                process_single_pdf_wrapper,
                pdf_paths,
                chunksize=chunksize
            ),
            total=len(pdf_paths),
            desc="Processing PDFs",
            unit="file"
        ):
            all_results.extend(file_results)

            # Update running stats (D-09)
            for r in file_results:
                if r['page'] == 0 and 'error' in r['notes']:
                    stats['errors'] += 1
                elif r['ids']:
                    stats['ids'] += len(r['ids'])
                else:
                    stats['no_id_pages'] += 1

            # Update progress bar postfix
            tqdm.write(
                f"IDs: {stats['ids']} | No-ID pages: {stats['no_id_pages']} | Errors: {stats['errors']}",
                end='\r'
            )

    return all_results
```

### CSV Output with Multiple IDs (PIPE-06, D-01)
```python
# Source: Existing write_results_csv() + D-01 (one row per ID)
def write_results_csv(results: list[dict], output_path: str) -> None:
    """
    Write results to CSV with one row per ID (per D-01).

    If a page has multiple IDs, it appears in multiple rows.
    If a page has no IDs, it appears once with blank id column.

    Args:
        results: List of dicts with 'ids' as list (not single 'id')
        output_path: Path to output CSV file
    """
    import pandas as pd
    from pathlib import Path

    # Create output directory
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Flatten: one row per ID (D-01)
    flattened = []
    for r in results:
        if r['ids']:
            # Multiple rows for multiple IDs
            for id_val in r['ids']:
                flattened.append({
                    'filename': r['filename'],
                    'page': r['page'],
                    'id': id_val,
                    'rotation_detected': r['rotation_detected'],
                    'notes': r['notes']
                })
        else:
            # Single row with blank id for no-match (PIPE-07)
            flattened.append({
                'filename': r['filename'],
                'page': r['page'],
                'id': '',
                'rotation_detected': r['rotation_detected'],
                'notes': r['notes']
            })

    # Create DataFrame and write
    df = pd.DataFrame(flattened)
    df = df[['filename', 'page', 'id', 'rotation_detected', 'notes']]
    df.to_csv(output_path, index=False)

    print(f"CSV written to {output_path}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| concurrent.futures new in 3.2 | multiprocessing since 2.6 | N/A - both current | For this use case, multiprocessing.Pool preferred for fine-grained control over chunking and worker lifecycle. ProcessPoolExecutor simpler but less flexible. |
| tqdm manual updating | tqdm wrapping iterators | ~2016 (tqdm 4.x) | Direct iterator wrapping (`tqdm(iterable)`) is now standard. Manual `update()` still works but less common. |
| os.path + os.walk | pathlib.Path.glob | Python 3.4+ (2014) | pathlib is now standard for path operations. `glob('**/*.pdf')` is cleaner than os.walk loops. |

**Deprecated/outdated:**
- **multiprocessing.Manager for simple aggregation:** Overkill for file-level parallelism where results are returned. Use Manager only for shared counters or complex coordination. Current design doesn't need it.
- **tqdm-multiprocess library:** Third-party wrapper for multiprocessing + tqdm. Adds dependency. Direct `tqdm(pool.imap_unordered(...))` pattern is simpler and sufficient.
- **Global multiprocessing.Queue for results:** Older pattern. Returning results from worker functions is cleaner and leverages Pool's result handling.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.8+ | pytesseract, multiprocessing spawn | ✓ | 3.14.2 | — |
| multiprocessing | Parallel processing | ✓ | stdlib (24 cores detected) | — |
| tqdm | Progress bars (PROG-01) | ✓ | 4.67.3 | — |
| pandas | CSV/JSON output | ✓ | 3.0.3 | — |
| Tesseract OCR | OCR engine | ✓ | Auto-detected via existing code | — |
| Poppler | PDF to image conversion | ✓ | Auto-detected via existing code | — |

**Missing dependencies with no fallback:**
None — all required dependencies are installed and detected.

**Missing dependencies with fallback:**
None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (detected via pytest.ini) |
| Config file | `pytest.ini` |
| Quick run command | `pytest tests/ -x` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PIPE-06 | Multiple IDs on same page all captured | unit | `pytest tests/test_precede_ocr.py::test_select_all_valid_ids -x` | ❌ Wave 0 |
| PIPE-06 | extract_id_with_rotation returns list of IDs | unit | `pytest tests/test_precede_ocr.py::test_extract_id_multiple_matches -x` | ❌ Wave 0 |
| PIPE-07 | No-ID pages flagged in CSV output | unit | `pytest tests/test_precede_ocr.py::test_csv_output_no_id_pages -x` | ❌ Wave 0 |
| PIPE-07 | No-ID pages show empty array in JSON | unit | `pytest tests/test_precede_ocr.py::test_json_output_no_id_pages -x` | ❌ Wave 0 |
| OUT-02 | JSON nested structure matches D-04 format | unit | `pytest tests/test_precede_ocr.py::test_write_results_json_structure -x` | ❌ Wave 0 |
| PROG-01 | Progress bar displays file count | integration | Manual verification (tqdm output to stderr, hard to unit test) | Manual only |
| Parallel | Multiprocessing processes multiple files | integration | `pytest tests/test_precede_ocr.py::test_parallel_processing -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_precede_ocr.py -x` (fast unit tests)
- **Per wave merge:** `pytest tests/ -v` (full suite)
- **Phase gate:** Full suite green + manual verification of progress bar output before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_precede_ocr.py::test_select_all_valid_ids` — tests returning all valid IDs (not just first)
- [ ] `tests/test_precede_ocr.py::test_extract_id_multiple_matches` — tests extract_id_with_rotation with multiple IDs on page
- [ ] `tests/test_precede_ocr.py::test_csv_output_no_id_pages` — verifies no-ID pages appear in CSV with blank id column
- [ ] `tests/test_precede_ocr.py::test_json_output_no_id_pages` — verifies no-ID pages show as empty array in JSON
- [ ] `tests/test_precede_ocr.py::test_write_results_json_structure` — validates nested dict structure per D-04
- [ ] `tests/test_precede_ocr.py::test_parallel_processing` — integration test with small batch (3-5 PDFs)

## Open Questions

1. **tqdm postfix vs separate print for running stats (D-09)**
   - What we know: tqdm supports `set_postfix()` for inline stats display
   - What's unclear: Whether postfix updates are visible with `imap_unordered()` or if manual print statements are clearer
   - Recommendation: Use `set_postfix()` for structured stats; test visibility with sample run. Fall back to `tqdm.write()` if postfix doesn't update properly.

2. **Optimal chunksize for 30K files with ~1-10 seconds per file**
   - What we know: Formula `len(tasks) // (4 * workers)` suggests ~326 for 30K files with 23 workers
   - What's unclear: Actual processing time variance (simple 1-page PDFs vs complex 20-page PDFs) affects optimal chunking
   - Recommendation: Start with calculated chunksize (~300). Make it configurable via hidden `--chunksize` flag for experimentation.

3. **JSON file size and memory for 30K files**
   - What we know: Nested JSON structure with ~30K files, ~5 pages/file, ~1-2 IDs/page = ~100KB-1MB JSON
   - What's unclear: pandas vs manual dict construction memory efficiency for this scale
   - Recommendation: Manual dict construction (defaultdict) for control. Write incrementally if JSON exceeds 10MB.

## Sources

### Primary (HIGH confidence)
- [Python multiprocessing documentation](https://docs.python.org/3/library/multiprocessing.html) - Official stdlib docs for Pool, imap_unordered, spawn behavior
- [Python pathlib documentation](https://docs.python.org/3/library/pathlib.html) - Path.glob recursive patterns
- [Python glob documentation](https://docs.python.org/3/library/glob.html) - Recursive pattern syntax
- [Python argparse documentation](https://docs.python.org/3/library/argparse.html) - CLI argument parsing
- [Python re documentation](https://docs.python.org/3/library/re.html) - re.findall returns all matches

### Secondary (MEDIUM confidence)
- [Lei Mao's Blog - Progress Bars for Python Multiprocessing](https://leimao.github.io/blog/Python-tqdm-Multiprocessing/) - tqdm + imap_unordered pattern (March 2026)
- [Running tqdm with Python multiprocessing](https://rednafi.com/python/tqdm-with-multiprocessing/) - Practical examples
- [SuperFastPython - Configure Pool.map() Chunksize](https://superfastpython.com/multiprocessing-pool-map-chunksize/) - Chunksize formula and trade-offs
- [SuperFastPython - Multiprocessing Pool vs ProcessPoolExecutor](https://superfastpython.com/multiprocessing-pool-vs-processpoolexecutor/) - Performance comparison
- [SuperFastPython - Add if __name__ == '__main__'](https://superfastpython.com/multiprocessing-spawn-runtimeerror/) - Windows spawn requirements
- [Tesseract OCR mailing list - Python Multiprocessing slows down](https://groups.google.com/g/tesseract-ocr/c/kHJkPoxS8dY/m/xNcplFnMAQAJ) - Memory leak discussion, maxtasksperchild solution
- [GeeksforGeeks - Python Pandas DataFrame to Nested JSON](https://www.geeksforgeeks.org/pandas/python-pandas-dataframe-to-nested-json/) - Nested JSON patterns
- [GeeksforGeeks - re.findall() in Python](https://www.geeksforgeeks.org/python/re-findall-in-python/) - Returns all matches as list

### Tertiary (LOW confidence)
None — all findings verified with official docs or authoritative sources.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - multiprocessing stdlib, tqdm verified installed, pandas verified installed
- Architecture: HIGH - Patterns verified from official docs and existing implementation
- Pitfalls: HIGH - Windows spawn requirements well-documented, Tesseract memory leaks confirmed by community
- Code examples: HIGH - Adapted from official docs and existing precede_ocr.py functions

**Research date:** 2026-06-05
**Valid until:** 2026-07-05 (30 days - stable ecosystem)
