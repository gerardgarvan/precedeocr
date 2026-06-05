# Phase 4: Resilience — Error Handling & Checkpointing - Research

**Researched:** 2026-06-05
**Domain:** Batch processing resilience patterns (checkpointing, error handling, retry logic, progress recovery)
**Confidence:** HIGH

## Summary

Phase 4 adds resilience to the 30K+ PDF batch processing pipeline through four integrated mechanisms: (1) JSON-based checkpoint persistence with atomic writes to prevent corruption, (2) per-file error handling with single-retry logic to handle transient failures, (3) structured error logging for post-batch investigation, and (4) batch statistics reporting for process observability. The standard Python ecosystem provides all necessary tools through stdlib (json, tempfile, os.replace) and existing dependencies (pandas for stats). The core challenge is integrating these patterns with the existing multiprocessing.Pool architecture without disrupting Phase 3's parallel processing patterns.

**Primary recommendation:** Use JSON checkpoint files with atomic write pattern (tempfile + os.replace), retry-once decorator at worker level, plain-text error log (not JSON), and batch stats as both console output and JSON file. Checkpoint every 50 files to balance crash safety with I/O overhead.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Checkpoint Format:**
- **D-01:** JSON file (`.checkpoint.json`) stored in the output directory alongside CSV/JSON results
- **D-02:** Checkpoint stores full results (extracted IDs, page data, rotation info) for completed files — not just filenames
- **D-03:** Checkpoint saved periodically every N files (not after every file) — balances crash safety with I/O overhead
- **D-04:** On resume, previously-checkpointed results merge with newly-processed results for final output

**Resume Behavior:**
- **D-05:** Auto-detect checkpoint — if `.checkpoint.json` exists in output directory, automatically resume from it on re-run (no explicit flag needed)
- **D-06:** Print resume status at startup: "Resuming: X/Y files already processed"
- **D-07:** `--fresh` CLI flag deletes existing checkpoint and starts from scratch
- **D-08:** Validate input path — checkpoint stores the input path used; on resume, if input path doesn't match, warn the user. New files in directory are processed; removed files are skipped from results

**Error Logging:**
- **D-09:** Separate error log file (`errors.log`) in output directory with one entry per failed file: filename, error type, message, timestamp
- **D-10:** Keep existing brief error in CSV notes column (e.g., `error: TypeError: ...`) alongside the separate detailed error log
- **D-11:** Retry each failed file once before marking as permanently failed — handles transient issues (file locks, temp disk full)

**Batch Statistics:**
- **D-12:** Print summary on screen at end of run AND write `batch_stats.json` to output directory
- **D-13:** Standard metrics: total files, successful, failed, total pages, IDs found, no-ID pages, error count, wall-clock duration, files/second rate
- **D-14:** Resume-aware stats: distinguish between previously-checkpointed results and newly-processed results in current session

### Claude's Discretion

- Exact checkpoint save frequency (N value — e.g., every 50 or 100 files)
- Internal checkpoint JSON structure/schema
- Error log format details (plain text vs structured)
- Exact warning message wording for stale checkpoint detection
- How to handle edge case of checkpoint file corruption

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUAL-03 | Per-file error handling ensures a single failed file does not crash the entire batch | Existing error dict pattern in process_single_pdf_wrapper provides foundation; retry-once decorator wraps this; multiprocessing error callback pattern handles silent failures |
| RESL-01 | Processing can resume from a checkpoint file after a crash or interruption | JSON checkpoint with atomic write pattern (tempfile + os.replace); auto-detect on startup; filter already-processed files from pool.imap_unordered input; merge checkpointed + new results before final output |

</phase_requirements>

## Standard Stack

### Core (Already Installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **json** | stdlib | Checkpoint serialization/deserialization | Python standard library. Simple API (`json.dump`, `json.load`). Lightweight for checkpoint data (list of result dicts). Human-readable for debugging. Already used for results.json output. **Confidence: HIGH** |
| **tempfile** | stdlib | Atomic checkpoint writes | Python standard library. `NamedTemporaryFile` creates temp file in same directory (required for atomic rename). Ensures temp and target on same filesystem. **Confidence: HIGH** |
| **os** | stdlib | Atomic file operations | `os.replace()` provides atomic rename on all platforms (POSIX and Windows). Safer than `os.rename()` on Windows. Python 3.3+ feature. **Confidence: HIGH** |
| **pathlib** | stdlib | Path manipulation | Already used throughout codebase. Cross-platform path handling. `Path.unlink(missing_ok=True)` for --fresh flag. **Confidence: HIGH** |
| **time** | stdlib | Timestamps and duration tracking | `time.time()` for wall-clock duration in batch stats. `datetime.now().isoformat()` for error log timestamps. **Confidence: HIGH** |
| **pandas** | 3.0.3 | Batch statistics calculation | Already installed and used for CSV output. Clean API for aggregating stats from results list. No new dependency. **Confidence: HIGH** |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pytest** | 9.0.2 | Testing checkpoint/resume logic | Already installed. Fixtures for temp directories, mock checkpoints, simulated crashes. Use `tmp_path` fixture for isolated test environments. **Confidence: HIGH** |
| **functools** | stdlib | Retry decorator | `@functools.wraps` for proper decorator metadata. Standard pattern for retry decorators. **Confidence: HIGH** |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **JSON checkpoint** | SQLite database | SQLite provides ACID guarantees but adds complexity for simple checkpoint use case. JSON is human-readable for debugging, sufficient for crash recovery. JSON with atomic write pattern is crash-safe enough. **Confidence: HIGH** |
| **Plain-text error log** | JSON structured logging (python-json-logger) | Structured JSON logs better for machine parsing (Loki, Elasticsearch) but overkill for batch script run manually. Plain text easier for human inspection in text editor. For 30K batch job, human readability > query performance. **Confidence: MEDIUM** |
| **Retry-once decorator** | tenacity library | tenacity provides exponential backoff, circuit breakers, advanced retry logic. Overkill for simple "retry once on any error" requirement. Custom decorator avoids new dependency. **Confidence: HIGH** |
| **os.replace** | shutil.move | shutil.move is higher-level but uses os.rename (not atomic on Windows). os.replace guarantees atomic behavior on all platforms. For checkpoint corruption prevention, use os.replace directly. **Confidence: HIGH** |

**Installation:**

No new dependencies required — all stdlib + existing packages (pandas, pytest).

**Version verification:**

All stdlib modules ship with Python 3.10+. Existing dependencies verified in requirements.txt:
- pandas==3.0.3 (latest, released May 2026)
- pytest==9.0.2 (current installation)

## Architecture Patterns

### Recommended Integration Points

The phase integrates with existing `precede_ocr.py` structure at four points:

```
main()
├── Load checkpoint if exists (D-05: auto-detect)
├── Filter already-processed PDFs from pdf_paths list
├── Pass checkpointed results + remaining PDFs to process_all_pdfs()
└── Merge checkpointed + new results → write outputs + stats

process_all_pdfs()
├── Track files processed since last checkpoint save
├── Periodically save checkpoint (D-03: every N files)
└── Accumulate stats (distinguish checkpointed vs new)

process_single_pdf_wrapper()
├── Add retry-once logic (D-11)
└── Log to errors.log on final failure (D-09)

argparse block
└── Add --fresh flag (D-07)
```

### Pattern 1: Atomic Checkpoint Write

**What:** Write-to-temp-then-rename pattern prevents corruption from mid-write crashes.

**When to use:** Every checkpoint save (periodic during batch processing, final save at end).

**Example:**
```python
# Source: https://docs.bswen.com/blog/2026-04-04-atomic-file-writing-python/
# Source: https://gist.github.com/therightstuff/cbdcbef4010c20acc70d2175a91a321f

import json
import tempfile
import os
from pathlib import Path

def save_checkpoint_atomic(checkpoint_data: dict, checkpoint_path: Path) -> None:
    """
    Atomically write checkpoint JSON to prevent corruption.

    Uses tempfile in same directory + os.replace for atomic rename.
    Ensures checkpoint file is always consistent (fully written or unchanged).
    """
    checkpoint_path = Path(checkpoint_path)
    temp_dir = checkpoint_path.parent

    # Write to temp file in same directory (required for atomic rename)
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=temp_dir,
        delete=False,
        suffix='.tmp'
    ) as tmp_file:
        json.dump(checkpoint_data, tmp_file, indent=2)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())  # Force write to disk before rename
        tmp_path = tmp_file.name

    # Atomic rename (overwrites existing checkpoint)
    os.replace(tmp_path, checkpoint_path)
```

**Why atomic:** Python's `open('file', 'w')` truncates file immediately, then writes incrementally. If process crashes mid-write, file is corrupted (partial content). Atomic write ensures destination file is either fully written or unchanged.

**Windows safety:** `os.replace()` is atomic on Windows (unlike `os.rename()`). Per Python 3.3+ docs, `os.replace()` works consistently across all platforms.

### Pattern 2: Checkpoint Schema Design

**What:** Checkpoint stores three pieces of data: (1) processing metadata, (2) full results for completed files, (3) validation hash.

**When to use:** Every checkpoint save and load operation.

**Example:**
```python
# Checkpoint structure per D-02, D-04, D-08
checkpoint_schema = {
    "metadata": {
        "version": "1.0",              # Schema version for future compatibility
        "input_path": "/path/to/pdfs", # D-08: Validate on resume
        "total_files": 30429,          # Total files discovered at start
        "processed_count": 1500,       # Files completed so far
        "timestamp": "2026-06-05T10:30:00Z",  # Last checkpoint time
        "checkpoint_frequency": 50     # How often checkpoint is saved
    },
    "results": [                       # D-02: Full results, not just filenames
        {
            "filename": "file001.pdf",
            "page": 1,
            "ids": ["12345"],
            "rotation_detected": 90,
            "notes": ""
        },
        # ... all pages from all completed files
    ],
    "processed_files": [               # Quick lookup: which files are done
        "file001.pdf",
        "file002.pdf",
        # ... 1500 filenames
    ]
}
```

**Design rationale:**
- `metadata` section: Input path validation (D-08), resume status message (D-06), stats calculation (D-14)
- `results` list: Full page-level data per D-02, ready to merge with new results
- `processed_files` list: Quick set lookup for filtering already-processed PDFs from work queue

**Corruption handling (Claude's discretion):** If `json.load()` raises `JSONDecodeError`, log warning, delete corrupt checkpoint, start fresh. Corruption rare with atomic write pattern but possible if disk fails during fsync.

### Pattern 3: Resume with Auto-Detect

**What:** On startup, check for checkpoint file in output directory. If exists, load and filter work queue. No explicit `--resume` flag needed (per D-05).

**When to use:** At start of `main()`, before processing begins.

**Example:**
```python
def load_checkpoint_if_exists(output_dir: Path) -> tuple[list[dict], set[str]] | None:
    """
    Load checkpoint if exists, return (results, processed_files_set).

    Returns None if no checkpoint or checkpoint is corrupt.
    D-05: Auto-detect — no explicit flag needed.
    """
    checkpoint_path = output_dir / '.checkpoint.json'

    if not checkpoint_path.exists():
        return None  # No checkpoint — fresh run

    try:
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)

        results = checkpoint['results']
        processed_files = set(checkpoint['processed_files'])

        print(f"Resuming: {len(processed_files)} files already processed")  # D-06
        return results, processed_files

    except (json.JSONDecodeError, KeyError) as e:
        print(f"WARNING: Corrupt checkpoint file, starting fresh: {e}")
        checkpoint_path.unlink(missing_ok=True)
        return None

def filter_remaining_pdfs(pdf_paths: list[Path], processed_files: set[str]) -> list[Path]:
    """
    Remove already-processed files from work queue.

    D-08: New files in directory are processed; removed files skipped from results.
    """
    return [p for p in pdf_paths if p.name not in processed_files]

# In main():
checkpoint_data = load_checkpoint_if_exists(Path(output_csv).parent)
if checkpoint_data:
    checkpointed_results, processed_files = checkpoint_data
    pdf_paths = filter_remaining_pdfs(pdf_paths, processed_files)
else:
    checkpointed_results = []
    processed_files = set()

# After processing:
all_results = checkpointed_results + new_results
```

**Input path validation (D-08):** Compare `checkpoint['metadata']['input_path']` with current `input_path` argument. If mismatch, warn user but continue (new files processed, removed files skipped).

### Pattern 4: Periodic Checkpoint Saves

**What:** Save checkpoint every N files (not after every file) to balance crash safety with I/O overhead (per D-03).

**When to use:** Inside `process_all_pdfs()` loop, after accumulating N new files.

**Example:**
```python
def process_all_pdfs(pdf_paths: list[Path], workers: int,
                     checkpointed_results: list[dict],
                     checkpoint_path: Path,
                     input_path: str,
                     checkpoint_frequency: int = 50) -> list[dict]:
    """
    Process PDFs with periodic checkpointing.

    D-03: Save every N files (default 50).
    """
    all_results = checkpointed_results.copy()
    processed_files = {r['filename'] for r in checkpointed_results}
    files_since_checkpoint = 0

    with mp.Pool(processes=workers, maxtasksperchild=50) as pool:
        pbar = tqdm(total=len(pdf_paths), desc="Processing PDFs", unit="file")

        for file_results in pool.imap_unordered(
            process_single_pdf_wrapper,
            pdf_paths,
            chunksize=max(1, len(pdf_paths) // (4 * workers))
        ):
            all_results.extend(file_results)
            processed_files.add(file_results[0]['filename'])
            files_since_checkpoint += 1

            # Periodic checkpoint save (D-03)
            if files_since_checkpoint >= checkpoint_frequency:
                checkpoint_data = {
                    "metadata": {
                        "version": "1.0",
                        "input_path": input_path,
                        "total_files": len(pdf_paths) + len(checkpointed_results),
                        "processed_count": len(processed_files),
                        "timestamp": datetime.now().isoformat(),
                        "checkpoint_frequency": checkpoint_frequency
                    },
                    "results": all_results,
                    "processed_files": list(processed_files)
                }
                save_checkpoint_atomic(checkpoint_data, checkpoint_path)
                files_since_checkpoint = 0

            pbar.update(1)

        pbar.close()

    # Final checkpoint save
    # ... (same structure as periodic save)

    return all_results
```

**Checkpoint frequency (Claude's discretion):** Start with N=50. Tradeoffs:
- Lower N (e.g., 10): More crash safety, more I/O overhead
- Higher N (e.g., 100): Less crash safety, less I/O overhead
- At 30K files with N=50: ~600 checkpoint saves, ~60MB total I/O (assuming 100KB per checkpoint)

### Pattern 5: Retry-Once Decorator

**What:** Wrap worker function with retry logic. Catch all exceptions, retry once, log on final failure (per D-11).

**When to use:** In `process_single_pdf_wrapper`, before returning error dict.

**Example:**
```python
# Source: https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide
# Source: https://z2d.io/posts/production-ready-python-decorators-retry/

import time
from functools import wraps

def retry_once(func):
    """
    Retry function once on any exception.

    D-11: Handles transient issues (file locks, temp disk full).
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # First failure — retry after brief delay
            time.sleep(0.5)  # 500ms delay for transient issues to clear
            try:
                return func(*args, **kwargs)
            except Exception as retry_error:
                # Second failure — propagate for error logging
                raise retry_error
    return wrapper

@retry_once
def process_single_pdf_inner(pdf_path: str, debug: bool = False) -> list[dict]:
    """
    Core processing logic (existing process_single_pdf function).
    """
    # ... existing implementation
    pass

def process_single_pdf_wrapper(pdf_path: Path) -> list[dict]:
    """
    Multiprocessing wrapper with retry and error logging.
    """
    try:
        results = process_single_pdf_inner(str(pdf_path), debug=False)
        return results
    except Exception as e:
        # Log to errors.log (D-09)
        log_error_to_file(pdf_path.name, e)

        # Return error dict for CSV notes column (D-10)
        return [{
            'filename': pdf_path.name,
            'page': 0,
            'ids': [],
            'rotation_detected': None,
            'notes': f'error: {type(e).__name__}: {str(e)}'
        }]
```

**Why retry once:** D-11 specifies single retry for transient issues. Transient errors (file locks, temp disk full) often resolve within seconds. Two attempts (original + retry) sufficient for these cases. Persistent errors (corrupt PDF, missing Tesseract) won't be fixed by retry, so avoid retry loops.

**Delay rationale:** 500ms delay gives time for file locks to release, temp disk space to free. Not too long to significantly slow batch processing (30K files * 500ms = 4 hours if all retried — unlikely).

### Pattern 6: Structured Error Logging

**What:** Write one log entry per failed file to `errors.log` in output directory. Plain text format for human readability (per Claude's discretion, avoiding JSON overkill for manual batch job).

**When to use:** In `process_single_pdf_wrapper` after final retry failure.

**Example:**
```python
# Source: https://oneuptime.com/blog/post/2026-01-24-handle-exceptions-properly-python/view

from datetime import datetime
from pathlib import Path

def log_error_to_file(filename: str, error: Exception, error_log_path: Path) -> None:
    """
    Append error entry to errors.log.

    D-09: One entry per failed file with filename, error type, message, timestamp.
    Plain text format (not JSON) for manual inspection.
    """
    timestamp = datetime.now().isoformat()
    error_type = type(error).__name__
    error_msg = str(error)

    # Format: [timestamp] filename | ErrorType: message
    log_entry = f"[{timestamp}] {filename} | {error_type}: {error_msg}\n"

    with open(error_log_path, 'a') as f:
        f.write(log_entry)

# In process_single_pdf_wrapper:
except Exception as e:
    error_log_path = Path(output_dir) / 'errors.log'  # Passed via closure or global
    log_error_to_file(pdf_path.name, e, error_log_path)
```

**Format choice (Claude's discretion):** Plain text chosen over JSON for:
- Human readability: User will inspect errors.log in text editor after batch run
- Simplicity: No need for log parsing tools (jq, Loki) for one-time batch job
- Grep-friendly: `grep "PermissionError" errors.log` works naturally

If project scales to production logging infrastructure (ELK, Loki), can migrate to JSON format with python-json-logger in future phase.

### Pattern 7: Batch Statistics Reporting

**What:** Collect metrics during processing, print summary to console, write JSON file (per D-12, D-13, D-14).

**When to use:** At end of `main()` after all processing complete.

**Example:**
```python
import time
from datetime import datetime

def calculate_batch_stats(all_results: list[dict],
                          checkpointed_count: int,
                          newly_processed_count: int,
                          start_time: float) -> dict:
    """
    Calculate batch statistics per D-13.

    D-14: Distinguish checkpointed vs newly-processed results.
    """
    duration = time.time() - start_time

    # Aggregate from results
    total_pages = len(all_results)
    ids_found = sum(len(r['ids']) for r in all_results)
    no_id_pages = sum(1 for r in all_results if not r['ids'])
    error_count = sum(1 for r in all_results if 'error:' in r.get('notes', ''))
    successful_files = len(set(r['filename'] for r in all_results if 'error:' not in r.get('notes', '')))
    total_files = len(set(r['filename'] for r in all_results))

    # Files per second rate (D-13)
    files_per_sec = newly_processed_count / duration if duration > 0 else 0

    return {
        "summary": {
            "total_files": total_files,
            "successful": successful_files,
            "failed": error_count,
            "total_pages": total_pages,
            "ids_found": ids_found,
            "no_id_pages": no_id_pages,
            "error_count": error_count
        },
        "performance": {
            "wall_clock_duration_sec": round(duration, 2),
            "files_per_second": round(files_per_sec, 2)
        },
        "resume_context": {  # D-14: Resume-aware stats
            "previously_checkpointed": checkpointed_count,
            "newly_processed": newly_processed_count
        },
        "timestamp": datetime.now().isoformat()
    }

def print_batch_stats(stats: dict) -> None:
    """Print summary to console per D-12."""
    print("\n" + "="*50)
    print("BATCH PROCESSING SUMMARY")
    print("="*50)
    s = stats['summary']
    print(f"Total files: {s['total_files']}")
    print(f"Successful: {s['successful']}")
    print(f"Failed: {s['failed']}")
    print(f"Total pages scanned: {s['total_pages']}")
    print(f"IDs found: {s['ids_found']}")
    print(f"Pages with no ID: {s['no_id_pages']}")

    p = stats['performance']
    print(f"\nDuration: {p['wall_clock_duration_sec']}s")
    print(f"Processing rate: {p['files_per_second']} files/sec")

    r = stats['resume_context']
    if r['previously_checkpointed'] > 0:
        print(f"\nResumed from checkpoint: {r['previously_checkpointed']} files")
        print(f"Newly processed: {r['newly_processed']} files")

    print("="*50)

# In main():
start_time = time.time()
# ... processing ...
stats = calculate_batch_stats(all_results, len(checkpointed_results),
                               len(pdf_paths), start_time)
print_batch_stats(stats)

# Write batch_stats.json (D-12)
stats_path = Path(output_csv).parent / 'batch_stats.json'
with open(stats_path, 'w') as f:
    json.dump(stats, f, indent=2)
print(f"\nBatch statistics written to {stats_path}")
```

### Pattern 8: --fresh Flag Implementation

**What:** Delete existing checkpoint and start from scratch (per D-07).

**When to use:** When user wants to reprocess entire batch (e.g., after fixing OCR config, testing).

**Example:**
```python
# In argparse block:
parser.add_argument('--fresh', action='store_true',
                    help='Delete existing checkpoint and start from scratch')

# In main():
if args.fresh:
    checkpoint_path = Path(args.output_csv).parent / '.checkpoint.json'
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print("Deleted existing checkpoint (--fresh mode)")
```

### Anti-Patterns to Avoid

- **Checkpoint after every file:** D-03 explicitly specifies periodic saves (every N files). Per-file checkpointing adds excessive I/O overhead (30K writes) without meaningful benefit. Most crashes don't lose more than N files of work.

- **Non-atomic checkpoint writes:** Using `open('checkpoint.json', 'w')` without temp-then-rename creates corruption risk. Mid-write crash leaves partial JSON that fails to parse on resume.

- **Retry with exponential backoff:** D-11 specifies retry-once. Exponential backoff (1s, 2s, 4s, 8s...) is for rate-limited APIs, not local file processing. Adds unnecessary complexity and delays batch completion.

- **Storing only filenames in checkpoint:** D-02 requires full results (page data, IDs, rotation). Filename-only checkpoint would require reprocessing on resume, defeating purpose.

- **Synchronous checkpoint saves in multiprocessing loop:** Atomic file writes are fast (<10ms for 100KB JSON) but blocking. For 30K files with N=50, 600 checkpoint saves = ~6 seconds overhead. Acceptable for reliability gain. Async saves add complexity without meaningful benefit.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| **Atomic file writes** | Custom lock files or PID files | tempfile + os.replace | Lock files have race conditions, PID files don't prevent corruption. os.replace is atomic primitive guaranteed by OS kernel. Stdlib solution is bulletproof. |
| **JSON schema validation** | Custom validators for checkpoint structure | Try/except with KeyError | For internal checkpoint format (not external API), KeyError on missing keys is sufficient. If validation needed later, use pydantic. But for Phase 4, simple error handling sufficient. |
| **Retry logic** | Custom while loops with counters | Decorator pattern (or tenacity if complex) | Retry-once is simple enough for custom decorator. For more complex retry (exponential backoff, circuit breakers), tenacity library is battle-tested. Don't reimplement retry state machines. |
| **Distributed locking** | File-based locks for multi-machine resume | N/A — out of scope | User runs on single Windows machine. No multi-machine coordination needed. If scaling to cluster (Dask, Ray), use their checkpoint mechanisms. |
| **Progress persistence across reboots** | Custom daemon or Windows service | Checkpoint file is sufficient | Checkpoint file survives reboots, crashes, power loss (with fsync). No need for separate persistence layer. |

**Key insight:** Python's stdlib provides all primitives for crash-safe checkpointing (tempfile, os.replace, json). The "hard part" is integration with multiprocessing architecture, not the checkpoint mechanics themselves. Focus research on integration patterns, not reimplementing atomic writes.

## Runtime State Inventory

> Skipped — Phase 4 is not a rename/refactor/migration phase. No stored data, live service config, OS-registered state, secrets, or build artifacts are affected. This is purely feature addition (error handling + checkpointing).

## Common Pitfalls

### Pitfall 1: Checkpoint File Corruption from Non-Atomic Writes

**What goes wrong:** Using `open('.checkpoint.json', 'w')` directly. Process crashes mid-write, leaving partial JSON. On resume, `json.load()` raises `JSONDecodeError`, user loses all checkpoint progress.

**Why it happens:** Python's `open(..., 'w')` truncates file immediately, then writes content incrementally (via kernel buffer). Crash between truncation and completion leaves corrupt file.

**How to avoid:**
1. Always use tempfile + os.replace pattern (see Pattern 1)
2. Call `os.fsync(fd)` after `flush()` to force kernel → disk write
3. Handle `JSONDecodeError` gracefully: warn user, delete corrupt checkpoint, start fresh

**Warning signs:**
- Checkpoint file has non-zero size but fails to parse
- Checkpoint file size varies wildly between runs (should be consistent for same number of files)
- Users report "lost progress" after crash

**Example of problem:**
```python
# BAD: Non-atomic write
with open('.checkpoint.json', 'w') as f:
    json.dump(checkpoint_data, f)  # <-- Crash here = corrupt file
```

**Example of solution:**
```python
# GOOD: Atomic write (from Pattern 1)
with tempfile.NamedTemporaryFile(mode='w', dir=checkpoint_path.parent, delete=False) as tmp:
    json.dump(checkpoint_data, tmp)
    tmp.flush()
    os.fsync(tmp.fileno())
os.replace(tmp.name, checkpoint_path)  # Atomic rename
```

### Pitfall 2: Checkpoint in Different Directory than Output

**What goes wrong:** Saving checkpoint to temp directory (`/tmp/.checkpoint.json`) while output goes to `output/`. User resumes with different output directory, doesn't find checkpoint, starts from scratch.

**Why it happens:** Misunderstanding of checkpoint auto-detect logic (D-05). Checkpoint must be co-located with output files to be discovered automatically.

**How to avoid:**
1. Always derive checkpoint path from output CSV path: `Path(output_csv).parent / '.checkpoint.json'`
2. Use same parent directory as other output artifacts (CSV, JSON, errors.log, batch_stats.json)
3. Test: Run with `--output-csv foo/results.csv`, verify checkpoint appears at `foo/.checkpoint.json`

**Warning signs:**
- User reports "checkpoint not found" even though they see `.checkpoint.json` file
- Checkpoint appears in wrong directory (e.g., current working directory instead of output dir)

### Pitfall 3: Retry Loop Without Limit

**What goes wrong:** Implementing retry logic without max attempts. Single corrupt PDF triggers infinite retry loop, batch job hangs forever.

**Why it happens:** Misunderstanding D-11 ("retry each failed file once"). Implementing generic retry decorator with `while True:` loop.

**How to avoid:**
1. D-11 explicitly specifies retry-once (total 2 attempts)
2. Use decorator with hardcoded `max_attempts=2`
3. After 2 failures, propagate exception for error logging

**Warning signs:**
- Progress bar hangs on single file for minutes
- CPU usage stays high but no progress
- Error log shows same file repeated many times

**Example of problem:**
```python
# BAD: Unbounded retry
while True:
    try:
        return process_pdf(path)
    except Exception:
        time.sleep(1)  # <-- Infinite loop on persistent error
```

**Example of solution:**
```python
# GOOD: Retry-once per D-11
for attempt in range(2):
    try:
        return process_pdf(path)
    except Exception as e:
        if attempt == 0:  # First failure
            time.sleep(0.5)
        else:  # Second failure
            raise e  # Propagate for error logging
```

### Pitfall 4: Merging Checkpointed Results After Filtering

**What goes wrong:** Loading checkpoint, filtering already-processed files from work queue, then re-filtering checkpointed results based on current input directory. Files removed from directory get dropped from final output, violating D-08 ("removed files are skipped from results" means keep them in output, just don't try to re-process).

**Why it happens:** Confusion about D-08's "removed files" clause. User interprets as "remove from output" but actually means "don't re-process, but keep previous results."

**How to avoid:**
1. Load checkpointed_results once from checkpoint file
2. Filter work queue: `remaining_pdfs = [p for p in pdf_paths if p.name not in processed_files]`
3. Merge at end: `all_results = checkpointed_results + new_results` (NO filtering of checkpointed_results)
4. Final output includes results for files that no longer exist in directory

**Warning signs:**
- User removes 10 files from directory, re-runs, final CSV has 10 fewer files than checkpoint
- User adds 5 files to directory, re-runs, final CSV has only 5 files (lost checkpointed results)

**Example of problem:**
```python
# BAD: Re-filtering checkpointed results
current_files = {p.name for p in pdf_paths}
checkpointed_results = [r for r in checkpointed_results if r['filename'] in current_files]  # WRONG
```

**Example of solution:**
```python
# GOOD: Keep all checkpointed results, only filter work queue
checkpointed_results = checkpoint['results']  # Keep all previous results
processed_files = set(checkpoint['processed_files'])
remaining_pdfs = [p for p in pdf_paths if p.name not in processed_files]  # Only filter work
all_results = checkpointed_results + new_results  # Merge without filtering
```

### Pitfall 5: Input Path Validation as Error

**What goes wrong:** D-08 specifies "warn the user" if input path doesn't match checkpoint. Implementing as hard error (raise ValueError), blocking resume.

**Why it happens:** Over-strict interpretation of validation. Trying to prevent user mistakes but blocking legitimate use cases (e.g., directory renamed, network path changed).

**How to avoid:**
1. Compare input paths, print warning if mismatch, but continue processing
2. Warning format: "WARNING: Checkpoint was created for '{old_path}', now processing '{new_path}'. New files will be processed, removed files will be skipped from re-processing."
3. Only block if fundamental incompatibility (e.g., checkpoint for file mode, now processing directory)

**Warning signs:**
- User reports "can't resume after renaming directory"
- Resume fails when moving project to different machine (path changes)

### Pitfall 6: Stats Calculation Before Checkpoint Merge

**What goes wrong:** Calculating batch stats from new_results only, ignoring checkpointed_results. D-14 requires distinguishing but including both in totals.

**Why it happens:** Calculating stats before merging checkpointed + new results.

**How to avoid:**
1. Merge first: `all_results = checkpointed_results + new_results`
2. Calculate stats from `all_results` for totals (total_files, total_pages, ids_found)
3. Track `newly_processed_count = len(new_results)` and `checkpointed_count = len(checkpointed_results)` separately for D-14

**Warning signs:**
- Batch stats show "Total files: 50" when checkpoint had 1000 files + 50 new files
- Stats don't account for previously-processed files

### Pitfall 7: Checkpoint Frequency as Files Per Worker

**What goes wrong:** Interpreting "every N files" as "every N files per worker" in multiprocessing. With 4 workers and N=50, checkpoint saves after 50 files per worker = 200 total files processed.

**Why it happens:** Misunderstanding multiprocessing architecture. Each worker processes files independently, but checkpoint tracking happens in main process (pool consumer).

**How to avoid:**
1. Track `files_since_checkpoint` in main process (not worker)
2. Increment by 1 for each `pool.imap_unordered` result consumed (regardless of which worker processed it)
3. Save checkpoint when `files_since_checkpoint >= N` (global counter, not per-worker)

**Warning signs:**
- With N=50 and 4 workers, checkpoints saved every 200 files instead of 50
- Checkpoint frequency varies based on worker count

## Code Examples

Verified patterns from research and existing codebase.

### Atomic Checkpoint Save (Full Implementation)

```python
# Source: https://docs.bswen.com/blog/2026-04-04-atomic-file-writing-python/
# Adapted for precede_ocr.py checkpoint use case

import json
import tempfile
import os
from pathlib import Path
from datetime import datetime

def save_checkpoint_atomic(
    results: list[dict],
    processed_files: set[str],
    input_path: str,
    checkpoint_path: Path,
    checkpoint_frequency: int
) -> None:
    """
    Atomically save checkpoint to prevent corruption.

    Uses tempfile + os.replace pattern for atomic write.
    Per D-01, D-02, D-03.

    Args:
        results: Full results list (all pages from all completed files)
        processed_files: Set of completed filenames
        input_path: Original input path (for D-08 validation on resume)
        checkpoint_path: Path to .checkpoint.json file
        checkpoint_frequency: How often checkpoint is saved (for metadata)
    """
    checkpoint_data = {
        "metadata": {
            "version": "1.0",
            "input_path": input_path,
            "total_files": len(processed_files),
            "processed_count": len(processed_files),
            "timestamp": datetime.now().isoformat(),
            "checkpoint_frequency": checkpoint_frequency
        },
        "results": results,
        "processed_files": list(processed_files)
    }

    # Write to temp file in same directory
    temp_dir = checkpoint_path.parent
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=temp_dir,
        delete=False,
        suffix='.tmp',
        prefix='.checkpoint_'
    ) as tmp_file:
        json.dump(checkpoint_data, tmp_file, indent=2)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())  # Force write to disk
        tmp_path = tmp_file.name

    # Atomic rename (overwrites existing checkpoint)
    os.replace(tmp_path, checkpoint_path)
```

### Load Checkpoint with Validation

```python
# Source: Integration of D-05 (auto-detect), D-06 (resume status), D-08 (path validation)

def load_checkpoint_if_exists(
    output_dir: Path,
    input_path: str
) -> tuple[list[dict], set[str]] | None:
    """
    Load checkpoint if exists, validate, return results and processed files.

    D-05: Auto-detect — no explicit flag needed.
    D-06: Print resume status.
    D-08: Validate input path, warn if mismatch.

    Returns:
        (results, processed_files_set) if checkpoint exists and valid, else None
    """
    checkpoint_path = output_dir / '.checkpoint.json'

    if not checkpoint_path.exists():
        return None  # No checkpoint — fresh run

    try:
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)

        # Extract data
        results = checkpoint['results']
        processed_files = set(checkpoint['processed_files'])
        metadata = checkpoint['metadata']

        # D-06: Print resume status
        print(f"Resuming from checkpoint: {len(processed_files)} files already processed")

        # D-08: Validate input path
        if metadata.get('input_path') != input_path:
            print(f"WARNING: Checkpoint was created for '{metadata.get('input_path')}'")
            print(f"         Now processing '{input_path}'")
            print(f"         New files will be processed; removed files skipped from re-processing.")

        return results, processed_files

    except (json.JSONDecodeError, KeyError) as e:
        print(f"WARNING: Corrupt checkpoint file, starting fresh: {e}")
        checkpoint_path.unlink(missing_ok=True)
        return None
```

### Retry-Once Decorator

```python
# Source: https://z2d.io/posts/production-ready-python-decorators-retry/
# Simplified to retry-once per D-11

import time
from functools import wraps

def retry_once(func):
    """
    Retry function once on any exception.

    D-11: Handles transient issues (file locks, temp disk full).
    Total 2 attempts: original + retry.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as first_error:
            # First failure — retry after brief delay
            time.sleep(0.5)  # 500ms for transient issues to clear
            try:
                return func(*args, **kwargs)
            except Exception as second_error:
                # Second failure — propagate for error logging
                raise second_error
    return wrapper
```

### Error Logging

```python
# Source: https://oneuptime.com/blog/post/2026-01-24-handle-exceptions-properly-python/view
# Plain text format per Claude's discretion

from datetime import datetime
from pathlib import Path

def log_error_to_file(filename: str, error: Exception, error_log_path: Path) -> None:
    """
    Append error entry to errors.log.

    D-09: One entry per failed file with filename, error type, message, timestamp.
    Plain text format (not JSON) for manual inspection.

    Args:
        filename: PDF filename that failed
        error: Exception object from final retry failure
        error_log_path: Path to errors.log file
    """
    timestamp = datetime.now().isoformat()
    error_type = type(error).__name__
    error_msg = str(error)

    # Format: [timestamp] filename | ErrorType: message
    log_entry = f"[{timestamp}] {filename} | {error_type}: {error_msg}\n"

    # Append to error log (create if doesn't exist)
    error_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(error_log_path, 'a') as f:
        f.write(log_entry)
```

### Integration into process_single_pdf_wrapper

```python
# Updated wrapper with retry and error logging

# At module level (outside wrapper, for pickling)
def process_single_pdf_with_retry(pdf_path: str, debug: bool = False) -> list[dict]:
    """Core processing with retry decorator."""
    return process_single_pdf(pdf_path, debug=debug)

process_single_pdf_with_retry = retry_once(process_single_pdf_with_retry)

def process_single_pdf_wrapper(pdf_path: Path, error_log_path: Path) -> list[dict]:
    """
    Wrapper for multiprocessing: handles retry and error logging.

    Must be top-level function for Windows spawn pickling.

    Args:
        pdf_path: Path object for PDF file
        error_log_path: Path to errors.log file (passed from main process)

    Returns:
        List of result dicts (one per page), or error dict if processing fails
    """
    try:
        results = process_single_pdf_with_retry(str(pdf_path), debug=False)
        return results
    except Exception as e:
        # Log to errors.log (D-09)
        log_error_to_file(pdf_path.name, e, error_log_path)

        # Return error dict for CSV notes column (D-10)
        return [{
            'filename': pdf_path.name,
            'page': 0,
            'ids': [],
            'rotation_detected': None,
            'notes': f'error: {type(e).__name__}: {str(e)}'
        }]
```

### Batch Stats Calculation and Reporting

```python
# Source: D-12, D-13, D-14 from CONTEXT.md

import time
from datetime import datetime

def calculate_batch_stats(
    all_results: list[dict],
    checkpointed_count: int,
    newly_processed_count: int,
    start_time: float
) -> dict:
    """
    Calculate batch statistics per D-13.

    D-14: Distinguish checkpointed vs newly-processed results.

    Args:
        all_results: Merged results (checkpointed + new)
        checkpointed_count: Number of files from checkpoint
        newly_processed_count: Number of files processed in current run
        start_time: time.time() at start of processing

    Returns:
        Stats dict for JSON output and console printing
    """
    duration = time.time() - start_time

    # Aggregate from results
    total_pages = len(all_results)
    ids_found = sum(len(r['ids']) for r in all_results)
    no_id_pages = sum(1 for r in all_results if not r['ids'] and 'error:' not in r.get('notes', ''))
    error_count = sum(1 for r in all_results if r['page'] == 0 and 'error:' in r.get('notes', ''))

    # Count unique files (successful and failed)
    all_filenames = set(r['filename'] for r in all_results)
    error_filenames = set(r['filename'] for r in all_results if 'error:' in r.get('notes', ''))
    successful_files = len(all_filenames - error_filenames)
    total_files = len(all_filenames)

    # Files per second rate (D-13) — only for newly processed files
    files_per_sec = newly_processed_count / duration if duration > 0 else 0

    return {
        "summary": {
            "total_files": total_files,
            "successful": successful_files,
            "failed": error_count,
            "total_pages": total_pages,
            "ids_found": ids_found,
            "no_id_pages": no_id_pages,
            "error_count": error_count
        },
        "performance": {
            "wall_clock_duration_sec": round(duration, 2),
            "files_per_second": round(files_per_sec, 2)
        },
        "resume_context": {  # D-14: Resume-aware stats
            "previously_checkpointed": checkpointed_count,
            "newly_processed": newly_processed_count
        },
        "timestamp": datetime.now().isoformat()
    }

def print_batch_stats(stats: dict) -> None:
    """Print summary to console per D-12."""
    print("\n" + "="*60)
    print("BATCH PROCESSING SUMMARY")
    print("="*60)

    s = stats['summary']
    print(f"Total files:        {s['total_files']}")
    print(f"  Successful:       {s['successful']}")
    print(f"  Failed:           {s['failed']}")
    print(f"Total pages:        {s['total_pages']}")
    print(f"  IDs found:        {s['ids_found']}")
    print(f"  No-ID pages:      {s['no_id_pages']}")

    p = stats['performance']
    print(f"\nDuration:           {p['wall_clock_duration_sec']}s")
    print(f"Processing rate:    {p['files_per_second']:.2f} files/sec")

    r = stats['resume_context']
    if r['previously_checkpointed'] > 0:
        print(f"\nResumed from checkpoint:")
        print(f"  Previously done:  {r['previously_checkpointed']} files")
        print(f"  Newly processed:  {r['newly_processed']} files")

    print("="*60)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual retry loops with `while True:` | Decorator pattern with explicit max attempts | 2024-2025 | Cleaner code, prevents infinite loops. Decorators centralize retry logic. Tenacity library (2019+) popularized pattern, now standard in production Python. |
| `os.rename()` for atomic writes | `os.replace()` | Python 3.3 (2012) | `os.replace()` works consistently on Windows and POSIX. `os.rename()` fails on Windows if target exists. Modern code should always use `os.replace()`. |
| Structured logging with JSON for all cases | Plain text for human-inspected batch logs | Ongoing nuance | JSON logging (python-json-logger, structlog) is essential for machine-aggregated logs (Kubernetes, ELK). For one-time batch scripts inspected manually, plain text is simpler. Context matters. |
| Database-backed checkpoints (SQLite, PostgreSQL) | JSON files with atomic writes | 2020+ for lightweight batch jobs | JSON sufficient for single-machine batch processing. Databases add setup complexity without benefit unless multi-machine coordination needed. Modern pattern: JSON for local, Redis/database for distributed. |
| Checkpoint after every item | Event-based periodic checkpointing | 2024-2026 best practices | Periodic checkpointing balances crash safety with I/O overhead. For large batches (1K+ items), checkpointing every N items (50-100) is standard. Databricks, Apache Spark use this pattern. |

**Deprecated/outdated:**
- **os.rename() for Windows compatibility:** Use `os.replace()` (atomic on all platforms, Python 3.3+)
- **Unbounded retry loops:** Use explicit max_attempts or tenacity library with `stop=stop_after_attempt(N)`
- **Global checkpoint frequency:** Should be configurable (CLI argument or config file) for tuning by user
- **Ignoring fsync after write:** Modern guidance emphasizes `os.fsync()` before rename for true crash safety

## Open Questions

1. **Should checkpoint frequency be configurable via CLI argument?**
   - What we know: D-03 specifies "every N files" but doesn't mandate fixed value. Claude's discretion on exact N value (50 or 100).
   - What's unclear: Whether user needs tuning capability (e.g., `--checkpoint-every 100` for faster processing vs. `--checkpoint-every 10` for more crash safety).
   - Recommendation: Start with hardcoded N=50 in Phase 4. Add CLI argument in future phase if users request tuning. Avoid premature generalization.

2. **How to handle checkpoint file larger than available disk space?**
   - What we know: Checkpoint stores full results (D-02). At 30K files with ~10 pages each = 300K result dicts. Estimated checkpoint size: ~50-100MB JSON (depending on IDs per page).
   - What's unclear: Should code check available disk space before writing checkpoint? Or rely on tempfile.NamedTemporaryFile raising OSError if disk full?
   - Recommendation: Let OSError propagate naturally. User's responsibility to ensure sufficient disk space for output. If disk full during checkpoint save, error will be caught in main() exception handler, user sees clear error message.

3. **Should errors.log be rotated or appended across multiple runs?**
   - What we know: D-09 specifies errors.log in output directory. Format is append-mode (`open(path, 'a')`).
   - What's unclear: If user runs batch job multiple times (with --fresh or resuming), should errors.log accumulate across runs or be cleared on fresh start?
   - Recommendation: Clear errors.log on fresh start (`--fresh` flag deletes it along with checkpoint). On resume, append to existing errors.log (preserves error history from previous sessions). Aligns with checkpoint behavior.

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified)

Phase 4 adds no new external dependencies. All functionality uses Python stdlib (json, tempfile, os, pathlib, time, datetime, functools) and existing project dependencies (pandas 3.0.3, pytest 9.0.2). No CLI tools, databases, or external services required.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | none — implicit discovery via tests/ directory |
| Quick run command | `pytest tests/test_precede_ocr.py -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-03 | Per-file error handling: single failed file does not crash batch | unit | `pytest tests/test_precede_ocr.py::test_wrapper_handles_exception -x` | ❌ Wave 0 |
| QUAL-03 | Retry-once logic: transient errors retried, persistent errors logged | unit | `pytest tests/test_precede_ocr.py::test_retry_once_decorator -x` | ❌ Wave 0 |
| QUAL-03 | Error logging: failed files written to errors.log with timestamp | unit | `pytest tests/test_precede_ocr.py::test_error_logging -x` | ❌ Wave 0 |
| RESL-01 | Checkpoint save: periodic checkpoint written with atomic pattern | unit | `pytest tests/test_precede_ocr.py::test_checkpoint_save_atomic -x` | ❌ Wave 0 |
| RESL-01 | Checkpoint load: existing checkpoint auto-detected and loaded | unit | `pytest tests/test_precede_ocr.py::test_checkpoint_load -x` | ❌ Wave 0 |
| RESL-01 | Resume filtering: already-processed files skipped from work queue | unit | `pytest tests/test_precede_ocr.py::test_filter_remaining_pdfs -x` | ❌ Wave 0 |
| RESL-01 | Result merging: checkpointed + new results merged correctly | unit | `pytest tests/test_precede_ocr.py::test_merge_results -x` | ❌ Wave 0 |
| RESL-01 | --fresh flag: deletes existing checkpoint and starts from scratch | integration | `pytest tests/test_precede_ocr.py::test_fresh_flag -x` | ❌ Wave 0 |
| RESL-01 | Input path validation: warns if checkpoint path doesn't match current | unit | `pytest tests/test_precede_ocr.py::test_checkpoint_path_validation -x` | ❌ Wave 0 |
| RESL-01 | Corrupt checkpoint handling: gracefully handles JSONDecodeError | unit | `pytest tests/test_precede_ocr.py::test_corrupt_checkpoint -x` | ❌ Wave 0 |
| D-12/D-13/D-14 | Batch stats: calculates and writes stats JSON and console output | unit | `pytest tests/test_precede_ocr.py::test_batch_stats_calculation -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_precede_ocr.py -x` (fast subset — exit on first failure)
- **Per wave merge:** `pytest tests/` (full suite)
- **Phase gate:** Full suite green + manual smoke test (interrupt batch job, verify resume works) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_precede_ocr.py` — 11 new test functions covering checkpoint save/load, retry logic, error logging, stats calculation, --fresh flag, corrupt checkpoint handling
- [ ] `tests/conftest.py` — shared fixtures for temp checkpoint files, mock error log paths, simulated crashes (if not already present from Phase 3)
- [ ] Manual smoke test procedure: "Run batch job on 100 files, interrupt (Ctrl+C) after 50 files, verify checkpoint exists, re-run, verify only remaining 50 files processed"

Framework already installed (pytest 9.0.2), no installation needed. Existing test file (tests/test_precede_ocr.py) has 70+ tests for Phases 1-3, will extend with Phase 4 tests.

## Sources

### Primary (HIGH confidence)
- [Python os.replace() for Safe, Atomic File Updates in Real Systems – TheLinuxCode](https://thelinuxcode.com/python-osreplace-for-safe-atomic-file-updates-in-real-systems/) - Atomic file operations on Windows and POSIX
- [How to Implement Atomic File Writing in Python (No Partial Writes) | BSWEN](https://docs.bswen.com/blog/2026-04-04-atomic-file-writing-python/) - Tempfile + os.replace pattern
- [Python multiprocessing — Process-based parallelism](https://docs.python.org/3/library/multiprocessing.html) - Official stdlib docs for multiprocessing error handling
- [Pytest Best Practices 2026: Fixtures, Markers, Config](https://qaskills.sh/blog/pytest-best-practices-2026) - Current testing patterns for 2026
- [How to Implement Job Checkpointing for Long-Running Batch Processes](https://oneuptime.com/blog/post/2026-02-09-job-checkpointing-long-running-batch/view) - Checkpoint patterns for batch jobs (2026)

### Secondary (MEDIUM confidence)
- [API Error Handling & Retry Strategies: Python Guide 2026](https://easyparser.com/blog/api-error-handling-retry-strategies-python-guide) - Retry decorator patterns, exponential backoff
- [Retry — Production-Ready Python Decorators | ZERO TO DATA](https://z2d.io/posts/production-ready-python-decorators-retry/) - Decorator implementation best practices
- [How to Use Structured JSON Logging for Python Applications Running in Kubernetes](https://oneuptime.com/blog/post/2026-02-09-structured-json-logging-python-kubernetes/view) - When to use JSON vs plain text logging
- [How to Process Datasets with Parallel Jobs in Python](https://oneuptime.com/blog/post/2026-01-23-parallel-dataset-processing-python/view) - Multiprocessing error handling patterns (2026)
- [Exception Handling in Methods of the Multiprocessing Pool Class in Python | Towards Data Science](https://towardsdatascience.com/exception-handling-in-methods-of-the-multiprocessing-pool-class-in-python-7fbb73746c26/) - Pool error callback patterns

### Tertiary (LOW confidence — context only)
- [Crash-safe JSON at scale: atomic writes + recovery without a DB - DEV Community](https://dev.to/constanta/crash-safe-json-at-scale-atomic-writes-recovery-without-a-db-3aic) - Recovery patterns (no specific Python version verification)
- [Batch Processing | Hermes Agent - nous research](https://hermes-agent.nousresearch.com/docs/user-guide/features/batch-processing) - General batch processing concepts (not Python-specific)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All stdlib modules with official docs, pandas already installed
- Architecture patterns: HIGH - Atomic write pattern well-documented across multiple 2026 sources, multiprocessing integration follows Phase 3 established patterns
- Retry logic: HIGH - Retry-once is simpler than exponential backoff (well-understood pattern), decorator pattern is standard Python
- Checkpoint schema: MEDIUM - Custom schema design (no standard library for this), but structure is straightforward (metadata + results + processed_files)
- Error logging: MEDIUM - Plain text vs JSON is judgment call (context-dependent), but format itself is simple
- Pitfalls: HIGH - Verified by reading atomic write pitfalls across multiple sources, non-atomic write corruption is well-documented problem

**Research date:** 2026-06-05
**Valid until:** 2026-07-05 (30 days — checkpoint patterns stable, Python stdlib unchanged, retry patterns established)
