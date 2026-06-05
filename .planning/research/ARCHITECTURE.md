# Architecture Research: Campaign Management Integration

**Domain:** Campaign management layer for batch OCR pipeline
**Context:** Adding interactive menu, graceful shutdown, per-folder stats to existing single-file multiprocessing architecture
**Researched:** 2026-06-05
**Confidence:** HIGH

## Executive Summary

Campaign management for long-running batch jobs requires **three architectural layers**: (1) **State tracking** — persistent campaign state with per-folder breakdowns, (2) **Interactive control** — menu system for resume/re-run/stats, and (3) **Graceful shutdown** — Windows-compatible Ctrl+C handling for multiprocessing.Pool cleanup. The key insight: **campaign features wrap the existing pipeline, not interleave with it**. The OCR pipeline remains unchanged; campaign logic lives in a new orchestration layer that manages checkpoints, presents menus, and handles signals.

**Integration with existing architecture:**
- Existing: `precede_ocr.py` (1,101 LOC) — single-file pipeline with `multiprocessing.Pool`, atomic checkpoint writes, tqdm progress
- New: Campaign orchestration layer — pre-run menu, signal handlers, enhanced checkpoint schema, per-folder aggregation
- Build order: (1) Enhanced state schema → (2) Menu system → (3) Signal handling → (4) Per-folder stats

---

## Existing Architecture (v1.0 Baseline)

### Current System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                     precede_ocr.py (Single File)                      │
├──────────────────────────────────────────────────────────────────────┤
│  main()                                                               │
│    ├─ discover_pdfs() → List[Path]                                   │
│    ├─ load_checkpoint_if_exists() → (results, processed_files)       │
│    ├─ filter_remaining_pdfs() → remaining PDFs                       │
│    └─ process_all_pdfs() ────────────────────────────────────────┐   │
│         ├─ multiprocessing.Pool(workers) ───────────────────────┐│   │
│         │   └─ pool.imap_unordered(process_single_pdf_wrapper) ││   │
│         │        └─ Worker: process_single_pdf() ───────────────┘│   │
│         │             ├─ pdf2image.convert_from_path()           │   │
│         │             ├─ For each page:                          │   │
│         │             │    └─ extract_id_with_rotation()         │   │
│         │             │         ├─ pytesseract OCR (4 rotations) │   │
│         │             │         └─ preprocess_image() fallback   │   │
│         │             └─ Return: [{filename, page, ids, ...}]    │   │
│         ├─ tqdm progress bar with running stats                  │   │
│         ├─ Periodic checkpoint: save_checkpoint_atomic()         │   │
│         └─ Final checkpoint + validate_sequence()                    │
│    ├─ write_results_csv()                                            │
│    ├─ write_results_json()                                           │
│    └─ calculate_batch_stats() → batch_stats.json                     │
└──────────────────────────────────────────────────────────────────────┘
```

### Existing Components (DO NOT MODIFY)

| Component | Responsibility | Entry Point | Output |
|-----------|---------------|-------------|---------|
| **File Discovery** | Recursive `.pdf` scan via `pathlib.Path.glob('**/*.pdf')` | `discover_pdfs(input_path)` | `List[Path]` |
| **Worker Pool** | Parallel PDF processing with `multiprocessing.Pool.imap_unordered()` | `process_all_pdfs(pdf_paths, workers, ...)` | `List[dict]` (flat results) |
| **Single PDF Processor** | End-to-end: PDF→images→OCR→IDs | `process_single_pdf(pdf_path)` | `[{filename, page, ids, rotation, notes}]` |
| **OCR Pipeline** | Multi-rotation OCR + preprocessing fallback | `extract_id_with_rotation(image)` | `(ids, rotation, notes)` |
| **Checkpoint Writer** | Atomic writes via `tempfile + os.replace` | `save_checkpoint_atomic(results, ...)` | `.checkpoint.json` |
| **Checkpoint Loader** | Resume from `.checkpoint.json` | `load_checkpoint_if_exists(output_dir, input_path)` | `(results, processed_files)` or `None` |
| **Sequence Validator** | Theil-Sen robust regression outlier detection | `validate_sequence(results)` | Updated results with flags |
| **Output Writers** | CSV + JSON with pandas | `write_results_csv()`, `write_results_json()` | `results.csv`, `results.json` |
| **Stats Calculator** | Summary metrics + performance | `calculate_batch_stats()` | `batch_stats.json` |

### Existing Checkpoint Schema (v1.0)

```json
{
  "metadata": {
    "version": "1.0",
    "input_path": "C:/path/to/pdfs",
    "processed_count": 1234,
    "timestamp": "2026-06-05T14:32:10.123456",
    "checkpoint_frequency": 50
  },
  "results": [
    {"filename": "file1.pdf", "page": 1, "ids": ["12345"], "rotation_detected": 90, "notes": ""},
    ...
  ],
  "processed_files": ["file1.pdf", "file2.pdf", ...]
}
```

### Existing Data Flow

```
CLI args → main()
    ↓
discover_pdfs(input_path) → List[Path]
    ↓
load_checkpoint_if_exists() → (checkpointed_results, processed_files) or None
    ↓
filter_remaining_pdfs(all_pdfs, processed_files) → remaining_pdfs
    ↓
process_all_pdfs(remaining_pdfs) ──────────────────────────────┐
    ├─ multiprocessing.Pool(workers=N) ───────────────────────┐│
    │   ├─ For each PDF: process_single_pdf_wrapper()       ││
    │   │    └─ Worker: process_single_pdf(pdf_path)        ││
    │   │         └─ Returns: [{filename, page, ids, ...}] ││
    │   └─ collect results via imap_unordered              ││
    ├─ tqdm progress bar (files_processed, IDs, errors)     ││
    ├─ Every 50 files: save_checkpoint_atomic()             ││
    └─ Final checkpoint ────────────────────────────────────┘│
    ↓                                                         │
validate_sequence(all_results) → results with outlier flags  │
    ↓                                                         │
write_results_csv(results) ────────────────────────────────────┘
write_results_json(results)
calculate_batch_stats() → batch_stats.json
```

**Key characteristics:**
- **Single-file architecture:** All code in `precede_ocr.py` (1,101 LOC)
- **Atomic checkpoint writes:** `tempfile.NamedTemporaryFile() + os.replace()` prevents corruption
- **Worker isolation:** Each worker process handles one PDF end-to-end, no shared state
- **Resume capability:** `--fresh` flag deletes checkpoint; otherwise auto-resumes from `.checkpoint.json`
- **Error handling:** Per-file try/except, errors logged to `errors.log`, failed files get `page=0` sentinel

---

## Campaign Management Layer (v1.1 Addition)

### System Overview with Campaign Features

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Campaign Orchestrator (NEW)                          │
├──────────────────────────────────────────────────────────────────────────────┤
│  main_with_campaign() ────────────────────────────────────────────────────┐  │
│    ├─ campaign = load_or_create_campaign_state() ────────────────────────┐│  │
│    │    └─ campaign_state.json: {status, started, progress, folders, ...}││  │
│    ├─ display_campaign_menu(campaign) ────────────────────────────────────┘│  │
│    │    ├─ [1] Continue campaign                                           │  │
│    │    ├─ [2] Re-run failures                                             │  │
│    │    ├─ [3] View statistics (per-folder breakdown)                      │  │
│    │    ├─ [4] Export partial results                                      │  │
│    │    └─ [5] Fresh start (delete checkpoint)                             │  │
│    ├─ setup_signal_handlers() ────────────────────────────────────────────┐│  │
│    │    └─ signal.signal(SIGINT, graceful_shutdown_handler)              ││  │
│    └─ run_campaign_with_shutdown(campaign) ──────────────────────────────┘│  │
│         ├─ update_campaign_state(status='running')                         │  │
│         ├─ process_all_pdfs() ──────────────────────── (existing pipeline) │  │
│         │    └─ Pool shutdown: close() + join() on SIGINT                  │  │
│         ├─ aggregate_per_folder_stats(results) ────────────────────────────┐  │
│         │    └─ {folder_path: {total_files, ids_found, ...}}              │  │
│         ├─ update_campaign_state(status='completed', stats=folder_stats) ─┘  │
│         └─ write_campaign_report() → campaign_report.md                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓ (delegates to)
┌──────────────────────────────────────────────────────────────────────────────┐
│                      Existing OCR Pipeline (UNCHANGED)                        │
│                            precede_ocr.py core                                │
│  process_all_pdfs() → multiprocessing.Pool → workers → results               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### New Components

| Component | Responsibility | Integration Point | Implementation |
|-----------|---------------|-------------------|----------------|
| **Campaign State Manager** | Load/save campaign state with folder-level progress | Wraps `load_checkpoint_if_exists()` | New functions in `precede_ocr.py` |
| **Interactive Menu** | Display resume/re-run/stats options, handle user input | Entry point before `process_all_pdfs()` | New `display_campaign_menu()` function (stdlib `input()` only) |
| **Signal Handler** | Catch SIGINT (Ctrl+C), set shutdown event, cleanup Pool | Installed before Pool creation | `signal.signal(SIGINT, handler)` + shared `Event()` |
| **Folder Stats Aggregator** | Group results by parent directory, calculate per-folder metrics | Post-processes `all_results` after pipeline completes | New `aggregate_per_folder_stats()` function |
| **Campaign Report Writer** | Markdown summary with folder breakdown | Final step after stats aggregation | New `write_campaign_report()` function |

---

## Campaign State Schema (Enhanced Checkpoint)

### campaign_state.json (NEW file, supplements .checkpoint.json)

```json
{
  "version": "1.1",
  "campaign_id": "campaign_20260605_143210",
  "input_path": "C:/path/to/pdfs",
  "status": "running",
  "started_at": "2026-06-05T14:32:10.123456",
  "last_updated": "2026-06-05T15:45:32.987654",
  "completed_at": null,
  "progress": {
    "total_files_discovered": 30429,
    "files_processed": 1234,
    "files_remaining": 29195,
    "files_failed": 5,
    "percent_complete": 4.05
  },
  "folder_stats": {
    "C:/path/to/pdfs/folder1": {
      "total_files": 150,
      "processed": 150,
      "ids_found": 1423,
      "no_id_pages": 8,
      "errors": 0
    },
    "C:/path/to/pdfs/folder2": {
      "total_files": 300,
      "processed": 120,
      "ids_found": 567,
      "no_id_pages": 23,
      "errors": 2
    }
  },
  "interruptions": [
    {"timestamp": "2026-06-05T15:00:00", "reason": "SIGINT", "files_processed_at_interrupt": 500}
  ],
  "options": {
    "workers": 7,
    "checkpoint_frequency": 50,
    "output_csv": "output/results.csv",
    "output_json": "output/results.json"
  }
}
```

**Key additions vs. v1.0 checkpoint:**
- **Campaign ID:** Unique identifier for this run (timestamp-based)
- **Status tracking:** `running` / `interrupted` / `completed` / `failed`
- **Folder-level stats:** Per-directory aggregation (new feature)
- **Interruption log:** Track Ctrl+C events with timestamps
- **Options snapshot:** Preserve CLI args for resume consistency

**Relationship to .checkpoint.json:**
- `.checkpoint.json` — **granular state** (list of all processed files, full results)
- `campaign_state.json` — **campaign metadata** (folder stats, interruptions, progress summary)
- Both updated atomically; campaign state references checkpoint version

---

## Interactive Menu Pattern (Stdlib Only)

### Menu Implementation (No External Dependencies)

```python
def display_campaign_menu(campaign_state: dict) -> str:
    """
    Display interactive menu for campaign actions.
    Returns selected action: 'continue' / 're-run' / 'stats' / 'export' / 'fresh'
    """
    print("\n" + "="*60)
    print("CAMPAIGN MENU")
    print("="*60)
    print(f"Campaign ID: {campaign_state['campaign_id']}")
    print(f"Status: {campaign_state['status']}")
    print(f"Progress: {campaign_state['progress']['percent_complete']:.1f}%")
    print(f"  Files: {campaign_state['progress']['files_processed']} / "
          f"{campaign_state['progress']['total_files_discovered']}")
    print(f"  Errors: {campaign_state['progress']['files_failed']}")
    print("\nOptions:")
    print("  [1] Continue campaign")
    print("  [2] Re-run failed files only")
    print("  [3] View per-folder statistics")
    print("  [4] Export partial results (CSV + JSON)")
    print("  [5] Fresh start (delete checkpoint)")
    print("  [Q] Quit")
    print("="*60)

    while True:
        choice = input("\nSelect option [1-5, Q]: ").strip().upper()
        if choice == '1':
            return 'continue'
        elif choice == '2':
            return 're-run-failures'
        elif choice == '3':
            display_folder_stats(campaign_state)
            # Loop back to menu after displaying stats
        elif choice == '4':
            return 'export'
        elif choice == '5':
            confirm = input("Delete checkpoint and start fresh? [y/N]: ").strip().lower()
            if confirm == 'y':
                return 'fresh'
            else:
                print("Cancelled.")
        elif choice == 'Q':
            return 'quit'
        else:
            print("Invalid option. Please enter 1-5 or Q.")

def display_folder_stats(campaign_state: dict) -> None:
    """Print per-folder statistics table."""
    print("\n" + "="*80)
    print("PER-FOLDER STATISTICS")
    print("="*80)
    print(f"{'Folder':<50} {'Files':<8} {'IDs':<8} {'No-ID':<8} {'Errors':<8}")
    print("-"*80)

    folder_stats = campaign_state.get('folder_stats', {})
    for folder, stats in sorted(folder_stats.items()):
        folder_name = Path(folder).name or folder  # Show basename only
        print(f"{folder_name:<50} {stats['processed']:<8} {stats['ids_found']:<8} "
              f"{stats['no_id_pages']:<8} {stats['errors']:<8}")

    print("="*80)
    input("\nPress Enter to return to menu...")
```

**Why stdlib only:**
- **No new dependencies:** Avoids adding libraries like `simple-term-menu` or `console-menu`
- **Windows compatibility:** `input()` works universally; curses-based menus fail on Windows without `windows-curses`
- **Simplicity:** Menu is pre-run only, not real-time during processing (tqdm handles progress)
- **Low complexity:** ~50 LOC for menu logic, easy to maintain

---

## Graceful Shutdown Architecture (Windows-Compatible)

### Signal Handling Strategy

**Key constraint:** Windows doesn't support Unix signals fully. `SIGTERM` doesn't exist; only `SIGINT` (Ctrl+C) and `SIGBREAK` (Ctrl+Break) are available.

**Recommended pattern:** Use `signal.signal(SIGINT, handler)` + `multiprocessing.Event()` for cross-platform graceful shutdown.

### Implementation Pattern

```python
import signal
import multiprocessing as mp
from typing import Optional

# Module-level shutdown event (shared with workers via Pool initializer)
_shutdown_event: Optional[mp.Event] = None
_pool: Optional[mp.Pool] = None

def init_worker(shutdown_event: mp.Event):
    """
    Worker initializer: set global shutdown event.
    Called once per worker process when Pool is created.
    """
    global _shutdown_event
    _shutdown_event = shutdown_event

def signal_handler(signum, frame):
    """
    SIGINT handler: set shutdown event and initiate graceful pool shutdown.
    """
    print("\n\nReceived interrupt signal (Ctrl+C). Finishing current files...")
    print("Press Ctrl+C again to force quit (may lose checkpoint integrity).\n")

    if _shutdown_event:
        _shutdown_event.set()  # Signal workers to stop accepting new work

    if _pool:
        _pool.close()  # Prevent new task submission
        # Pool.join() will be called in main after loop exits

def process_all_pdfs_with_shutdown(
    pdf_paths: list[Path],
    workers: int,
    shutdown_event: mp.Event,
    **kwargs
) -> list[dict]:
    """
    Enhanced process_all_pdfs with graceful shutdown support.
    """
    global _pool

    all_results = []
    processed_files = set()

    with mp.Pool(
        processes=workers,
        initializer=init_worker,
        initargs=(shutdown_event,),
        maxtasksperchild=50
    ) as pool:
        _pool = pool  # Store for signal handler access

        pbar = tqdm(total=len(pdf_paths), desc="Processing PDFs", unit="file")

        try:
            for file_results in pool.imap_unordered(
                process_single_pdf_wrapper,
                pdf_paths,
                chunksize=10
            ):
                all_results.extend(file_results)
                processed_files.add(file_results[0]['filename'])
                pbar.update(1)

                # Check shutdown event
                if shutdown_event.is_set():
                    print("Shutdown event detected. Stopping after current batch...")
                    break  # Exit loop, Pool.close() + join() happens via context manager

                # Periodic checkpoint (unchanged)
                if len(processed_files) % 50 == 0:
                    save_checkpoint_atomic(all_results, processed_files, ...)

        except KeyboardInterrupt:
            # Second Ctrl+C: forceful shutdown
            print("\nForced shutdown. Saving checkpoint...")
            save_checkpoint_atomic(all_results, processed_files, ...)
            raise

        finally:
            pbar.close()
            _pool = None

    # Context manager handles pool.close() + pool.join()
    return all_results

def main_with_campaign(input_path: str, **kwargs):
    """
    Campaign-aware main entry point.
    """
    shutdown_event = mp.Event()

    # Install signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Load or create campaign state
    campaign_state = load_or_create_campaign_state(input_path, kwargs)

    # Display menu
    action = display_campaign_menu(campaign_state)

    if action == 'quit':
        return
    elif action == 'fresh':
        delete_checkpoint()
        campaign_state = create_fresh_campaign_state(input_path, kwargs)

    # Run pipeline with shutdown support
    try:
        all_results = process_all_pdfs_with_shutdown(
            pdf_paths,
            workers=kwargs.get('workers', mp.cpu_count() - 1),
            shutdown_event=shutdown_event,
            **kwargs
        )

        # Post-processing
        folder_stats = aggregate_per_folder_stats(all_results)
        update_campaign_state(campaign_state, status='completed', stats=folder_stats)
        write_campaign_report(campaign_state, folder_stats)

    except KeyboardInterrupt:
        update_campaign_state(campaign_state, status='interrupted')
        print("Campaign interrupted. Resume with same command to continue.")
        sys.exit(130)  # Standard Unix exit code for SIGINT
```

### Shutdown Sequence

```
User presses Ctrl+C
    ↓
SIGINT signal → signal_handler()
    ├─ Print "Finishing current files..." message
    ├─ shutdown_event.set() (notify workers)
    ├─ pool.close() (prevent new task submission)
    └─ (pool.join() deferred to context manager)
    ↓
Main loop checks shutdown_event.is_set()
    ├─ If True: break loop (exit imap_unordered iteration)
    └─ Else: continue processing
    ↓
Context manager __exit__()
    ├─ pool.close() (already called by handler, idempotent)
    ├─ pool.join() (wait for in-flight tasks to complete)
    └─ pool.terminate() only if join() times out (emergency)
    ↓
save_checkpoint_atomic(all_results, ...) (final state)
update_campaign_state(status='interrupted')
    ↓
Exit with code 130
```

**Windows-specific notes:**
- **No SIGTERM:** Only handle SIGINT (Ctrl+C). Don't register SIGTERM handlers (not available on Windows).
- **No SIGKILL:** `pool.terminate()` uses `TerminateProcess()` API on Windows, not SIGKILL.
- **Second Ctrl+C:** Raises `KeyboardInterrupt` exception, caught in `except` block for forceful shutdown.

### Why This Pattern Works

| Requirement | How Pattern Addresses It |
|-------------|--------------------------|
| **Graceful shutdown** | `pool.close()` stops accepting new tasks; workers finish current PDF before exiting |
| **No data loss** | `save_checkpoint_atomic()` in `finally` block ensures state persisted even on interrupt |
| **Windows compatibility** | Uses `Event()` for IPC, not Unix-only signals like SIGTERM |
| **User feedback** | Clear message: "Finishing current files... Press Ctrl+C again to force quit" |
| **Resume capability** | Campaign state marked `interrupted`, next run auto-resumes from menu |

---

## Per-Folder Statistics Architecture

### Folder Aggregation Strategy

**Challenge:** Results are flat list of `{filename, page, ids, ...}` dicts. Need to group by parent directory and calculate folder-level metrics.

**Solution:** Post-process results after pipeline completes, group by `Path(filename).parent`, aggregate stats.

### Implementation

```python
from pathlib import Path
from collections import defaultdict

def aggregate_per_folder_stats(all_results: list[dict], input_path: str) -> dict:
    """
    Aggregate results into per-folder statistics.

    Args:
        all_results: Flat list of result dicts from process_all_pdfs()
        input_path: Root directory path (to calculate relative folder paths)

    Returns:
        Dict mapping folder path to {total_files, processed, ids_found, ...}
    """
    input_root = Path(input_path).resolve()

    # Group results by filename first
    by_file = defaultdict(list)
    for r in all_results:
        by_file[r['filename']].append(r)

    # Then group files by parent folder
    folder_stats = defaultdict(lambda: {
        'total_files': 0,
        'processed': 0,
        'ids_found': 0,
        'no_id_pages': 0,
        'errors': 0
    })

    for filename, file_results in by_file.items():
        # Find parent folder relative to input_path
        # Note: filename is basename only, need to discover full path from original PDF list
        # For now, use flat structure assumption; for nested dirs, store full paths in results
        folder_path = str(input_root)  # Simplified; enhance to track actual parent dirs

        folder_stats[folder_path]['total_files'] += 1
        folder_stats[folder_path]['processed'] += 1

        # Count IDs and no-ID pages
        for r in file_results:
            if 'error:' in r.get('notes', ''):
                folder_stats[folder_path]['errors'] += 1
            elif r['ids']:
                folder_stats[folder_path]['ids_found'] += len(r['ids'])
            else:
                folder_stats[folder_path]['no_id_pages'] += 1

    return dict(folder_stats)
```

**Enhancement for nested directories:**
Currently, `process_single_pdf()` returns `filename: Path(pdf_path).name` (basename only). To enable per-folder stats:

**Option 1 (Minimal change):** Add `folder_path` field to result dicts in `process_single_pdf_wrapper()`:

```python
def process_single_pdf_wrapper(pdf_path: Path) -> list[dict]:
    """Enhanced wrapper with folder tracking."""
    results = process_single_pdf(str(pdf_path), debug=False)

    # Inject folder path into each result dict
    folder_path = str(pdf_path.parent)
    for r in results:
        r['folder_path'] = folder_path

    return results
```

**Option 2 (Post-process with discovery):** Rebuild folder mapping from original `pdf_paths` list using filename lookups. More complex but avoids changing result schema.

**Recommendation:** Use Option 1. Small change to wrapper, clean folder tracking.

### Folder Stats Output

**Console display:**
```
================================================================================
PER-FOLDER STATISTICS
================================================================================
Folder                                             Files    IDs      No-ID    Errors
--------------------------------------------------------------------------------
folder1                                            150      1423     8        0
folder2                                            300      567      23       2
subfolder/nested                                   50       234      1        0
================================================================================
```

**campaign_report.md:**
```markdown
# Campaign Report

**Campaign ID:** campaign_20260605_143210
**Status:** Completed
**Duration:** 2 hours 15 minutes
**Total Files:** 30,429
**Total IDs Extracted:** 287,543

## Per-Folder Breakdown

| Folder | Files | IDs Found | No-ID Pages | Errors |
|--------|-------|-----------|-------------|--------|
| folder1 | 150 | 1,423 | 8 | 0 |
| folder2 | 300 | 567 | 23 | 2 |
| subfolder/nested | 50 | 234 | 1 | 0 |

## Problem Areas

- **folder2:** 2 errors, 23 no-ID pages (7.7% failure rate) — investigate low-quality scans
- **subfolder/nested:** 2% no-ID rate — acceptable

## Recommendations

- Re-run folder2 with `--debug` flag to diagnose errors
- Check folder2 scan quality (possible scanner issue)
```

---

## Build Order and Integration Points

### Phase 1: Enhanced Campaign State Schema

**Goal:** Extend checkpoint with campaign metadata and folder stats.

**Changes:**
1. Create `campaign_state.json` schema (separate from `.checkpoint.json`)
2. Add `load_or_create_campaign_state()` function
3. Add `update_campaign_state()` for atomic updates
4. Add `folder_path` field to result dicts in `process_single_pdf_wrapper()`

**Integration points:**
- Wraps existing `load_checkpoint_if_exists()` — no changes to checkpoint logic
- New file alongside `.checkpoint.json` in output directory
- Result dict schema change is **additive** (adds `folder_path`, doesn't remove fields)

**Success criteria:**
- `campaign_state.json` created on first run
- Folder stats populated correctly for nested directories
- Backward compatible: v1.0 code can still read v1.1 checkpoints (ignores new fields)

---

### Phase 2: Interactive Menu System

**Goal:** Pre-run menu for continue/re-run/stats/fresh actions.

**Changes:**
1. Add `display_campaign_menu()` function (stdlib `input()` only)
2. Add `display_folder_stats()` helper for stats view
3. Wrap `main()` with `main_with_campaign()` entry point
4. Add menu action handlers: continue, re-run failures, export, fresh

**Integration points:**
- Calls existing `load_checkpoint_if_exists()` to populate menu state
- Menu action 'continue' → calls existing `process_all_pdfs()` unchanged
- Menu action 'fresh' → calls existing `delete_checkpoint()` logic (enhance for campaign_state.json)
- Menu action 're-run' → filters `pdf_paths` to failed files only from campaign state

**Success criteria:**
- Menu displays on startup if checkpoint exists
- Fresh start deletes both `.checkpoint.json` and `campaign_state.json`
- Re-run failures filters to error files only
- Stats view shows per-folder breakdown without running pipeline

**No changes to:** OCR pipeline, multiprocessing logic, checkpoint writes

---

### Phase 3: Graceful Shutdown (Signal Handling)

**Goal:** Ctrl+C stops pipeline gracefully, saves state, allows resume.

**Changes:**
1. Add `signal.signal(SIGINT, signal_handler)` in `main_with_campaign()`
2. Create `multiprocessing.Event()` for shutdown coordination
3. Modify `process_all_pdfs()` → `process_all_pdfs_with_shutdown()`:
   - Pass `shutdown_event` to Pool initializer
   - Check `shutdown_event.is_set()` in main loop
   - Break loop if event is set
4. Update campaign state to `status='interrupted'` on SIGINT
5. Add second Ctrl+C handling (forceful shutdown with warning)

**Integration points:**
- **Minimal changes to core loop:** Only adds `if shutdown_event.is_set(): break`
- **Pool management:** Uses context manager (`with Pool() as pool`) for automatic cleanup
- **Checkpoint writes:** Final checkpoint in `finally` block (already exists, unchanged)
- **Campaign state:** New `update_campaign_state()` call in exception handler

**Windows-specific considerations:**
- Only handle SIGINT (Ctrl+C), not SIGTERM (doesn't exist on Windows)
- Use `Event()` for IPC, not signals, for cross-platform compatibility
- Test on Windows: `pool.close()` + `pool.join()` sequence works correctly

**Success criteria:**
- First Ctrl+C: Prints "Finishing current files...", waits for in-flight tasks, saves checkpoint
- Second Ctrl+C: Immediate exit, checkpoint saved in `except KeyboardInterrupt` block
- Campaign state marked `interrupted`, next run shows resume option in menu
- No zombie processes on Windows after shutdown

**No changes to:** Worker function logic, OCR pipeline, checkpoint format (campaign state adds interruption log)

---

### Phase 4: Per-Folder Statistics & Reporting

**Goal:** Aggregate results by folder, display in menu and generate campaign report.

**Changes:**
1. Add `aggregate_per_folder_stats()` function (post-processes `all_results`)
2. Enhance `display_folder_stats()` to show per-folder table
3. Add `write_campaign_report()` for Markdown summary
4. Update `campaign_state.json` with folder stats after pipeline completes

**Integration points:**
- Runs **after** `process_all_pdfs()` completes (post-processing step)
- Uses `folder_path` field added in Phase 1
- No changes to pipeline or checkpoint logic
- Campaign report written alongside `results.csv` and `batch_stats.json`

**Success criteria:**
- Folder stats calculated correctly for nested directory structures
- Menu option [3] displays per-folder table
- `campaign_report.md` generated with folder breakdown and problem area highlights
- Campaign state includes folder stats for resume scenarios

**No changes to:** OCR pipeline, multiprocessing, checkpoint writes (only adds post-processing)

---

## Data Flow with Campaign Features

### Startup Flow (New)

```
CLI invocation: python precede_ocr.py <input_path> [options]
    ↓
main_with_campaign() (NEW)
    ├─ load_or_create_campaign_state()
    │    ├─ Check campaign_state.json exists?
    │    │    YES: Load campaign metadata
    │    │    NO: Create fresh campaign state
    │    └─ Check .checkpoint.json exists?
    │         YES: Load processed_files, results
    │         NO: Empty checkpoint state
    ↓
display_campaign_menu(campaign_state)
    ├─ Show: Campaign ID, status, progress %, folder stats
    ├─ Options: [1] Continue, [2] Re-run failures, [3] Stats, [4] Export, [5] Fresh
    └─ User selects action
    ↓
Action dispatcher:
    ├─ [1] Continue → process_all_pdfs_with_shutdown(remaining_pdfs)
    ├─ [2] Re-run → filter failed files → process_all_pdfs_with_shutdown(failed_pdfs)
    ├─ [3] Stats → display_folder_stats() → loop back to menu
    ├─ [4] Export → write_results_csv/json from checkpoint → exit
    └─ [5] Fresh → delete checkpoints → create_fresh_campaign_state() → continue
    ↓
setup_signal_handlers()
    └─ signal.signal(SIGINT, signal_handler)
    ↓
process_all_pdfs_with_shutdown() (ENHANCED existing function)
```

### Processing Flow with Shutdown Support (Enhanced)

```
process_all_pdfs_with_shutdown(pdf_paths, shutdown_event)
    ↓
Create multiprocessing.Pool(initializer=init_worker, initargs=(shutdown_event,))
    ↓
Main loop: for results in pool.imap_unordered(process_single_pdf_wrapper, pdf_paths):
    ├─ Collect results
    ├─ Update tqdm progress bar
    ├─ Check shutdown_event.is_set()?
    │    YES: break loop (graceful exit)
    │    NO: continue
    ├─ Every 50 files: save_checkpoint_atomic() (UNCHANGED)
    └─ Append to all_results
    ↓
Pool.__exit__() via context manager:
    ├─ pool.close() (if not already closed by signal handler)
    ├─ pool.join() (wait for workers)
    └─ Cleanup
    ↓
Final checkpoint save (UNCHANGED)
    ↓
Post-processing (NEW):
    ├─ aggregate_per_folder_stats(all_results) → folder_stats
    ├─ update_campaign_state(status='completed', stats=folder_stats)
    └─ write_campaign_report(campaign_state, folder_stats)
```

### Interrupt Flow (New)

```
User presses Ctrl+C during processing
    ↓
SIGINT → signal_handler()
    ├─ Print "Finishing current files..." message
    ├─ shutdown_event.set()
    ├─ pool.close() (prevent new tasks)
    └─ Return from handler
    ↓
Main loop iteration:
    ├─ Check shutdown_event.is_set() → True
    ├─ break loop
    └─ Pool context manager __exit__() calls pool.join()
    ↓
finally block:
    ├─ save_checkpoint_atomic() (UNCHANGED)
    └─ update_campaign_state(status='interrupted', interruptions=[...])
    ↓
Exit with code 130
    ↓
Next invocation:
    ├─ load_campaign_state() sees status='interrupted'
    ├─ Menu shows "Resume interrupted campaign?"
    └─ User selects [1] Continue → resumes from checkpoint
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Interleaving Campaign Logic with OCR Pipeline

**What people might do:** Add campaign state checks and menu logic inside `process_all_pdfs()` or worker functions.

**Why it's wrong:**
- Couples campaign management to core OCR logic (breaks separation of concerns)
- Makes testing harder (can't test pipeline without campaign layer)
- Worker processes shouldn't know about campaign state (only shutdown event)

**Do this instead:** **Campaign layer wraps pipeline, doesn't modify it.** Menu and state management happen **before** and **after** `process_all_pdfs()`, not during. Workers only check shutdown event.

---

### Anti-Pattern 2: Relying on SIGTERM for Windows Compatibility

**What people might do:** Register `signal.signal(SIGTERM, handler)` for graceful shutdown.

**Why it's wrong:**
- SIGTERM doesn't exist on Windows (raises `AttributeError`)
- Windows only supports SIGINT (Ctrl+C) and SIGBREAK (Ctrl+Break)
- Code becomes platform-specific, breaks on Windows

**Do this instead:** **Only handle SIGINT** (Ctrl+C), which works on both Windows and Unix. Use `multiprocessing.Event()` for cross-platform IPC instead of relying on signals.

---

### Anti-Pattern 3: Modifying Result Schema for Campaign Features

**What people might do:** Add campaign-specific fields like `campaign_id`, `status` to individual result dicts.

**Why it's wrong:**
- Result dicts represent **page-level data** (filename, page, ids, rotation)
- Campaign metadata belongs in **campaign state**, not page results
- Pollutes result schema with orchestration concerns
- Breaks backward compatibility with v1.0 checkpoints

**Do this instead:** **Keep result schema unchanged.** Add `folder_path` field only (Phase 1) for per-folder stats. Campaign metadata lives in `campaign_state.json`, separate from `.checkpoint.json`.

---

### Anti-Pattern 4: Using External Menu Libraries

**What people might do:** Add dependencies like `simple-term-menu`, `console-menu`, `pick` for interactive menus.

**Why it's wrong:**
- Adds new dependencies (project currently has minimal deps)
- Some libraries don't work on Windows without extra setup (`curses` requires `windows-curses`)
- Menu is pre-run only (not real-time), doesn't need fancy features
- Over-engineering for simple "select 1-5" use case

**Do this instead:** **Use stdlib `input()` only.** Simple text menu with number selection. Works on all platforms, zero dependencies, easy to maintain.

---

### Anti-Pattern 5: Blocking Shutdown Until All Files Complete

**What people might do:** Ignore shutdown event in main loop, always process all remaining PDFs before exiting.

**Why it's wrong:**
- User expects Ctrl+C to stop "soon", not after potentially hours of remaining work
- Poor UX: "Why isn't it stopping?"
- Defeats purpose of graceful shutdown (should finish current file, not all files)

**Do this instead:** **Check shutdown event in main loop, break immediately.** Finish only in-flight tasks (files already submitted to workers), not entire queue. Message: "Finishing current files..." (plural refers to ~N workers, not all 30K files).

---

### Anti-Pattern 6: Storing Full Results in Campaign State

**What people might do:** Duplicate `all_results` list in `campaign_state.json` for quick access.

**Why it's wrong:**
- Results already stored in `.checkpoint.json` (single source of truth)
- Campaign state file becomes massive (30K PDFs × pages × result dicts = GB)
- Slow to load on resume
- Risk of inconsistency (two copies of results)

**Do this instead:** **Campaign state stores only aggregates and metadata.** Full results live in `.checkpoint.json` only. Campaign state references checkpoint version, stores folder stats (aggregated), not raw results.

---

## Technology Stack Summary

| Component | Technology | Version | Purpose | Notes |
|-----------|-----------|---------|---------|-------|
| **Signal Handling** | `signal` module | stdlib | SIGINT handler for graceful shutdown | Windows: SIGINT only, no SIGTERM |
| **IPC for Shutdown** | `multiprocessing.Event` | stdlib | Cross-platform shutdown coordination | Shared between parent and workers |
| **Interactive Menu** | `input()` | stdlib | Simple text-based menu (no curses) | Platform-agnostic, zero dependencies |
| **Campaign State** | JSON (stdlib `json`) | stdlib | Persistent campaign metadata | Separate from `.checkpoint.json` |
| **Folder Stats** | `collections.defaultdict` | stdlib | Aggregate results by folder | Post-processing step |
| **Report Generation** | Markdown (string formatting) | stdlib | Human-readable campaign summary | `campaign_report.md` |

**Key decisions:**
- **No new dependencies:** All campaign features use stdlib only
- **Minimal pipeline changes:** Core OCR logic unchanged, campaign wraps it
- **Cross-platform:** Windows-compatible signal handling and menu system

---

## Testing Strategy by Phase

### Phase 1: Enhanced Campaign State

**Unit tests:**
- `test_load_or_create_campaign_state()`: New campaign vs. resume
- `test_update_campaign_state()`: Atomic updates, folder stats persistence
- `test_folder_path_injection()`: Verify `process_single_pdf_wrapper()` adds folder field

**Integration test:**
- Run pipeline with nested directories, verify `campaign_state.json` includes correct folder paths

**Success metric:** Campaign state loads correctly on resume, folder paths accurate

---

### Phase 2: Interactive Menu

**Manual testing required** (menu is interactive):
- Checkpoint exists: Menu displays with resume option
- No checkpoint: Menu offers fresh start only
- Stats view: Displays per-folder table correctly
- Re-run failures: Filters to error files only

**Unit tests:**
- `test_display_campaign_menu()`: Mock `input()`, verify action returns
- `test_display_folder_stats()`: Verify output formatting

**Success metric:** Menu works end-to-end, actions dispatch correctly

---

### Phase 3: Graceful Shutdown

**Manual testing required:**
- Start large batch (1000+ files), press Ctrl+C after ~100 files processed
- Verify: "Finishing current files..." message appears
- Verify: Pipeline stops within ~10 seconds (time to finish in-flight files)
- Verify: Checkpoint saved with correct `processed_files` count
- Verify: Campaign state marked `interrupted`
- Resume: Next run shows menu with continue option

**Stress test:**
- Press Ctrl+C twice quickly (forceful shutdown)
- Verify: Checkpoint still saved (exception handler)
- Verify: No zombie processes on Windows

**Unit tests:**
- `test_signal_handler()`: Mock shutdown event, verify event.set() called
- `test_shutdown_event_check()`: Verify loop breaks when event is set

**Success metric:** Ctrl+C stops gracefully, checkpoints preserved, resume works

---

### Phase 4: Per-Folder Statistics

**Unit tests:**
- `test_aggregate_per_folder_stats()`: Verify grouping and aggregation logic
- `test_write_campaign_report()`: Verify Markdown formatting

**Integration test:**
- Run pipeline on nested directory structure (3+ levels)
- Verify folder stats in `campaign_state.json` match actual results
- Verify `campaign_report.md` highlights problem areas correctly

**Success metric:** Folder stats accurate, report identifies low-performing folders

---

## Sources

### Signal Handling and Graceful Shutdown
- [Handling SIGINT in multiprocessing on Windows - Python Help](https://discuss.python.org/t/handling-sigint-in-multiprocessing-on-windows/90064)
- [Graceful exit with Python multiprocessing | The-Fonz blog](https://the-fonz.gitlab.io/posts/python-multiprocessing/)
- [Signal handling with async multiprocesses in Python — how to gracefully shut down | by Cziegler | Medium](https://medium.com/@cziegler_99189/gracefully-shutting-down-async-multiprocesses-in-python-2223be384510)
- [GitHub - wbenny/python-graceful-shutdown](https://github.com/wbenny/python-graceful-shutdown)
- [Shutdown the Multiprocessing Pool in Python – SuperFastPython](https://superfastpython.com/shutdown-the-multiprocessing-pool-in-python/)
- [Graceful vs. Forceful: Mastering Python's Pool Termination](https://runebook.dev/en/docs/python/library/multiprocessing/multiprocessing.pool.Pool.terminate)
- [Python Multiprocessing graceful shutdown in the proper order | peterspython.com](https://www.peterspython.com/en/blog/python-multiprocessing-graceful-shutdown-in-the-proper-order)

### Interactive CLI Menus
- [pymenu-cli · PyPI](https://pypi.org/project/pymenu-cli/)
- [Interactive CLI select menu in Python · GitHub](https://gist.github.com/henryefranks/885b95503c519f70f5b701681eb8d97f)
- [GitHub - mtik00/pyclimenu: Menu system for Python interactive command-line scripts](https://github.com/mtik00/pyclimenu)

### Checkpoint State and Progress Tracking
- [Agent State Checkpointing and Resumption · Issue #2172 · openai/openai-agents-python](https://github.com/openai/openai-agents-python/issues/2172)
- [Persistence - Docs by LangChain](https://docs.langchain.com/oss/python/langgraph/persistence)
- [State Management and Resumability | gemini-cli-extensions/conductor](https://deepwiki.com/gemini-cli-extensions/conductor/8.2-state-management-and-resumability)
- [GitHub - a-rahimi/python-checkpointing: Checkpoint python data processing pipelines](https://github.com/a-rahimi/python-checkpointing)

### Directory Statistics and Folder Analysis
- [Analyzing Your File System and Folder Structures with Python - njanakiev](https://janakiev.com/blog/python-filesystem-analysis/)
- [GitHub - njanakiev/folderstats: Python module that collects detailed statistics from a folder structure](https://github.com/njanakiev/folderstats)
- [Build a Python Directory Tree Generator for the Command Line – Real Python](https://realpython.com/directory-tree-generator-python/)

### Batch Processing Patterns
- [mcp-cli · PyPI](https://pypi.org/project/mcp-cli/) — Parallel batch execution with checkpointing and resume
- [Efficient Data Processing in Python: Batch vs Streaming Pipelines Explained](https://www.freecodecamp.org/news/efficient-data-processing-in-python-batch-vs-streaming-pipelines/)

---

*Architecture research for: Campaign management integration with existing OCR pipeline*
*Researched: 2026-06-05*
*Confidence: HIGH (signal handling, menu patterns, folder stats) — all based on stdlib features and documented multiprocessing patterns*
