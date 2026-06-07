# Phase 6: Enhanced Campaign State Schema - Research

**Researched:** 2026-06-05
**Domain:** Campaign state persistence with atomic writes and folder tracking
**Confidence:** HIGH

## Summary

Phase 6 establishes a campaign metadata layer that supplements the existing v1.0 `.checkpoint.json` with orchestration state needed for downstream features (menu, stats, shutdown tracking). The key architectural decision is **separation of concerns**: checkpoint stores granular per-file results; campaign state stores high-level metadata (ID, status, folder breakdowns, interruption log). Both use the proven atomic write pattern (tempfile + fsync + os.replace) validated in v1.0.

This is a **pure additive change** with zero risk to existing checkpoint/resume functionality. The `process_single_pdf_wrapper()` gains a single `folder_path` field, campaign state lives in a new JSON file, and path normalization via `Path.resolve()` prevents Windows case-sensitivity bugs. The phase enables all downstream features (graceful shutdown logs interruptions, menu shows per-folder stats, reports highlight problem areas) while keeping the OCR pipeline completely unchanged.

**Primary recommendation:** Extend existing atomic write utilities into a shared helper, leverage dataclasses for type safety, and add silent upgrade logic so v1.0 checkpoints auto-create campaign state on first v1.1 run.

## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Campaign ID uses auto-generated timestamp format: `campaign_20260605_143022` (ISO-ish, human-readable, sortable)

**D-02:** No input directory name in the campaign ID — input path stored as a separate field in state

**D-03:** Campaign state is "practical" level — stores: campaign ID, status (running/interrupted/completed), total/processed/failed counts, start time, last update time, interruption log, input path, CLI options snapshot

**D-04:** Interruption log entries include timestamp + progress snapshot (files_processed, files_remaining) — not just bare timestamps

**D-05:** Silent upgrade from v1.0 checkpoints — if `.checkpoint.json` exists but no `campaign_state.json`, auto-create campaign state from checkpoint metadata (derive campaign ID from checkpoint timestamp, set status to 'interrupted')

**D-06:** User sees a brief "Upgraded to campaign tracking" message on silent upgrade — no confirmation prompt required

**D-07:** `folder_path` field added to result dicts in `process_single_pdf_wrapper()` — stores path relative to the input directory (e.g., `subdir1/batch2`)

**D-08:** Files directly in the input directory (not in a subdirectory) get `folder_path: ''` (empty string) — Phase 9 can display as "(root)" or input dir name

**D-09:** Path normalization uses `Path.resolve()` before computing relative paths to handle Windows case-insensitivity

### Claude's Discretion

- Campaign state JSON schema field names and nesting structure
- Whether to use dataclasses or plain dicts for internal state representation
- Checkpoint frequency and state update timing (align with existing checkpoint_frequency=50 pattern)
- Error handling for edge cases (missing fields in upgraded state, concurrent access)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STATE-01 | Campaign persists state (ID, status, progress, options) to JSON file with atomic writes | Atomic write pattern already validated in v1.0 `save_checkpoint_atomic()` — tempfile + fsync + os.replace. Campaign state uses same pattern. dataclasses + dataclasses-json for clean serialization. |
| STATE-02 | Campaign tracks per-folder file paths in result data for downstream statistics | Add `folder_path` field to result dicts in `process_single_pdf_wrapper()`. Use `Path.resolve()` for normalization (prevents Windows case duplicates). Store relative to input_path for portability. |
| STATE-03 | Campaign logs interruption events with timestamps for debugging | Campaign state includes `interruptions` list. Each entry: `{timestamp, reason, files_processed_at_interrupt}`. Updated on SIGINT in Phase 7, but schema established now. |

## Standard Stack

All technologies are stdlib or already validated in v1.0 — zero new external dependencies for this phase.

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| json | Python 3.14 stdlib | JSON encoding/decoding | Standard for state files. Existing checkpoint uses json.dump/load. Human-readable for debugging. |
| dataclasses | Python 3.14 stdlib | Type-safe state structure | Clean state modeling with type hints. Built-in `asdict()` for serialization. Zero dependencies. |
| tempfile | Python 3.14 stdlib | Atomic write pattern (temp file creation) | Already used in `save_checkpoint_atomic()`. Creates temp file in same dir as target (same filesystem for atomic os.replace). |
| os.replace | Python 3.14 stdlib | Atomic file move | Atomic on Windows via MoveFileEx. Validated in v1.0. Crash-safe when combined with fsync. |
| pathlib.Path | Python 3.14 stdlib | Path manipulation and normalization | `Path.resolve()` returns absolute, normalized paths. Handles Windows case-insensitivity. Used throughout existing codebase. |
| datetime | Python 3.14 stdlib | Timestamp generation | ISO format timestamps for campaign ID and interruption log. Already used in checkpoint metadata. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| dataclasses-json | 0.6.7 (optional) | Serialize dataclasses to JSON | Optional enhancement if dataclass schema becomes complex. Use stdlib `dataclasses.asdict()` + json.dump as fallback. Not required for v1.1. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| json (stdlib) | dataclasses-json | dataclasses-json adds automatic type handling (nested dataclasses, datetime) but is pre-1.0.0 and not officially Python 3.13+ yet. Stdlib approach more robust. Use dataclasses-json only if nesting becomes complex. |
| Path.resolve() | Manual case normalization | Custom case-folding (`.lower()`) is Windows-specific and fragile. `Path.resolve()` handles it correctly across platforms. |
| Separate campaign_state.json | Extend .checkpoint.json | Merging into checkpoint couples orchestration metadata with result data. Separation allows independent evolution (e.g., campaign features without touching checkpoint schema). |

**Installation:**

No new packages required — all stdlib. Optional dataclasses-json if desired:
```bash
pip install dataclasses-json==0.6.7  # OPTIONAL
```

**Version verification:**

All stdlib modules ship with Python 3.14 — no version check needed.

## Architecture Patterns

### Recommended Project Structure

No new files or directories — Phase 6 adds functions to existing `precede_ocr.py` and a new `campaign_state.json` file in the output directory.

```
precede_ocr/
├── precede_ocr.py                    # Enhanced with campaign state functions
├── tests/
│   ├── test_precede_ocr.py           # Add campaign state tests
│   └── conftest.py                   # Existing fixtures
└── [output_dir]/
    ├── .checkpoint.json               # Existing granular results
    ├── campaign_state.json            # NEW: Campaign metadata
    ├── results.csv
    └── results.json
```

### Pattern 1: Campaign State Schema (Dataclass)

**What:** Type-safe Python dataclass representing campaign metadata.

**When to use:** Always — provides type hints, IDE autocomplete, and validation.

**Example:**
```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class CampaignState:
    """Campaign orchestration metadata (separate from checkpoint results)."""
    version: str = "1.1"
    campaign_id: str = ""
    input_path: str = ""
    status: str = "running"  # running | interrupted | completed | failed
    started_at: str = ""  # ISO timestamp
    last_updated: str = ""  # ISO timestamp
    completed_at: Optional[str] = None  # ISO timestamp or null

    # Progress counters (derived from checkpoint or updated incrementally)
    total_files_discovered: int = 0
    files_processed: int = 0
    files_failed: int = 0

    # Per-folder aggregates (populated by Phase 9, schema established now)
    folder_stats: dict = field(default_factory=dict)
    # Structure: {folder_path: {total_files, processed, ids_found, no_id_pages, errors}}

    # Interruption log (populated by Phase 7, schema established now)
    interruptions: list = field(default_factory=list)
    # Structure: [{timestamp, reason, files_processed_at_interrupt}]

    # CLI options snapshot for resume consistency
    options: dict = field(default_factory=dict)
    # Structure: {workers, checkpoint_frequency, output_csv, output_json}

    @classmethod
    def generate_campaign_id(cls) -> str:
        """Generate campaign ID per D-01."""
        now = datetime.now()
        return f"campaign_{now.strftime('%Y%m%d_%H%M%S')}"
```

**Source:** Dataclass pattern from Python 3.14 stdlib docs; schema fields from CONTEXT.md D-03.

### Pattern 2: Atomic Campaign State Write

**What:** Reuse v1.0 atomic write pattern for campaign state persistence.

**When to use:** Every time campaign state is updated (startup, periodic updates, shutdown).

**Example:**
```python
import os
import json
import tempfile
from pathlib import Path
from dataclasses import asdict

def save_campaign_state_atomic(state: CampaignState, output_dir: Path) -> None:
    """
    Atomically save campaign state JSON.

    Uses same pattern as save_checkpoint_atomic (tempfile + fsync + os.replace).
    Per D-01, D-03: state stored in campaign_state.json alongside .checkpoint.json.
    """
    state_path = Path(output_dir) / 'campaign_state.json'
    temp_dir = state_path.parent

    # Update last_updated timestamp
    state.last_updated = datetime.now().isoformat()

    # Serialize dataclass to dict
    state_dict = asdict(state)

    # Atomic write pattern (validated in v1.0)
    with tempfile.NamedTemporaryFile(
        mode='w',
        dir=temp_dir,
        delete=False,
        suffix='.tmp',
        prefix='.campaign_state_'
    ) as tmp_file:
        json.dump(state_dict, tmp_file, indent=2)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())  # Ensure data on disk before replace
        tmp_path = tmp_file.name

    os.replace(tmp_path, str(state_path))  # Atomic on Windows
```

**Source:** Existing `save_checkpoint_atomic()` in precede_ocr.py lines 555-579; tempfile + os.replace pattern from Python docs.

### Pattern 3: Silent Upgrade from v1.0 Checkpoint

**What:** Auto-create campaign state when v1.0 checkpoint exists but campaign state doesn't.

**When to use:** On startup, before processing begins.

**Example:**
```python
def load_or_create_campaign_state(
    output_dir: Path,
    input_path: str,
    cli_options: dict
) -> CampaignState:
    """
    Load existing campaign state or create new one.

    Per D-05, D-06: Silent upgrade from v1.0 checkpoints.
    If .checkpoint.json exists but campaign_state.json doesn't,
    derive campaign state from checkpoint metadata.
    """
    state_path = output_dir / 'campaign_state.json'
    checkpoint_path = output_dir / '.checkpoint.json'

    # Case 1: Campaign state already exists — load it
    if state_path.exists():
        try:
            with open(state_path) as f:
                state_dict = json.load(f)
            # Convert dict to dataclass (manual for stdlib approach)
            state = CampaignState(**state_dict)
            print(f"Resuming campaign: {state.campaign_id} ({state.status})")
            return state
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"WARNING: Corrupt campaign state, recreating: {e}")
            state_path.unlink(missing_ok=True)
            # Fall through to create fresh state

    # Case 2: v1.0 checkpoint exists but no campaign state — silent upgrade
    if checkpoint_path.exists():
        try:
            with open(checkpoint_path) as f:
                checkpoint = json.load(f)
            metadata = checkpoint['metadata']
            processed_files = set(checkpoint['processed_files'])

            # Derive campaign ID from checkpoint timestamp (D-05)
            checkpoint_ts = metadata.get('timestamp', datetime.now().isoformat())
            # Parse ISO timestamp to generate campaign ID format
            dt = datetime.fromisoformat(checkpoint_ts)
            campaign_id = f"campaign_{dt.strftime('%Y%m%d_%H%M%S')}"

            state = CampaignState(
                campaign_id=campaign_id,
                input_path=input_path,
                status='interrupted',  # Assume interrupted since resuming
                started_at=checkpoint_ts,
                last_updated=datetime.now().isoformat(),
                files_processed=len(processed_files),
                options=cli_options
            )

            print(f"Upgraded to campaign tracking: {campaign_id}")  # D-06
            save_campaign_state_atomic(state, output_dir)
            return state
        except (json.JSONDecodeError, KeyError) as e:
            print(f"WARNING: Corrupt checkpoint during upgrade, starting fresh: {e}")
            # Fall through to create fresh state

    # Case 3: Fresh start — create new campaign state
    state = CampaignState(
        campaign_id=CampaignState.generate_campaign_id(),
        input_path=input_path,
        started_at=datetime.now().isoformat(),
        last_updated=datetime.now().isoformat(),
        options=cli_options
    )

    print(f"Starting new campaign: {state.campaign_id}")
    save_campaign_state_atomic(state, output_dir)
    return state
```

**Source:** Existing `load_checkpoint_if_exists()` pattern in precede_ocr.py lines 582-602; upgrade logic from CONTEXT.md D-05, D-06.

### Pattern 4: Folder Path Injection (Result Enhancement)

**What:** Add `folder_path` field to result dicts returned by workers.

**When to use:** In `process_single_pdf_wrapper()` before returning results.

**Example:**
```python
def process_single_pdf_wrapper(pdf_path: Path, input_path_root: Path) -> list[dict]:
    """
    Enhanced wrapper with folder tracking per D-07, D-08, D-09.

    Computes folder_path relative to input_path_root with normalization.
    """
    # Process PDF with existing logic
    results = process_single_pdf(str(pdf_path), debug=False)

    # Compute normalized folder path (D-09)
    pdf_full_path = pdf_path.resolve()  # Absolute, normalized (handles case)
    input_root_resolved = input_path_root.resolve()

    # Compute relative folder path
    pdf_folder = pdf_full_path.parent
    try:
        rel_folder = pdf_folder.relative_to(input_root_resolved)
        folder_path = str(rel_folder)  # e.g., "subdir1/batch2"
    except ValueError:
        # PDF outside input directory (shouldn't happen, but handle gracefully)
        folder_path = str(pdf_folder)

    # Handle root directory case (D-08)
    if folder_path == '.':
        folder_path = ''  # Empty string for files directly in input_path

    # Inject folder_path into each result dict (additive, backward compatible)
    for result in results:
        result['folder_path'] = folder_path

    return results
```

**Source:** CONTEXT.md D-07, D-08, D-09; pathlib.Path.resolve() from Python stdlib docs.

### Anti-Patterns to Avoid

**Anti-pattern:** Storing full result lists in campaign state

**Why it's bad:** Results already in `.checkpoint.json`. Duplicating in `campaign_state.json` bloats file size (30K PDFs = GB), slows resume, risks inconsistency.

**Do this instead:** Campaign state stores only aggregates (total counts, folder stats). Full results live in checkpoint only.

---

**Anti-pattern:** Using `Path("folder1").lower()` for case normalization

**Why it's bad:** Fragile, Windows-specific, doesn't handle all edge cases (e.g., `Folder1` vs `FOLDER1` vs `folder1`).

**Do this instead:** Use `Path.resolve()` which returns the canonical path with OS-appropriate case handling.

---

**Anti-pattern:** Updating campaign state on every PDF completion

**Why it's bad:** Atomic writes have overhead (fsync). Writing every PDF (30K writes) is slow and unnecessary.

**Do this instead:** Update campaign state at same frequency as checkpoint (every 50 files, already established pattern). State updates are primarily for status changes (running → completed) and interruptions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom lock files + rename logic | tempfile + os.replace pattern (already in v1.0) | Edge cases: crash during write, cross-volume moves, fsync requirements. Existing pattern proven crash-safe. |
| Path normalization | String manipulation (`path.lower()`, `path.replace('\\', '/')`) | `Path.resolve()` | Handles Windows case-insensitivity, UNC paths, symlinks, relative path resolution — all correctly. |
| Campaign ID generation | UUID or random strings | Timestamp-based ID per D-01 | Human-readable, sortable, no collision risk at 1-second granularity for single-user tool. |
| JSON schema validation | Manual field checks | Dataclasses with type hints | Type hints provide IDE autocomplete, validation, and self-documenting code. |

**Key insight:** v1.0 already solved atomic writes and path handling. Phase 6 extends existing patterns rather than reinventing them.

## Runtime State Inventory

> Skip — Phase 6 is greenfield (new campaign state feature, not rename/refactor). No existing runtime state to migrate.

## Common Pitfalls

### Pitfall 1: Path Case-Sensitivity on Windows

**What goes wrong:** Windows file paths are case-insensitive but case-preserving. String comparisons are case-sensitive, so `"C:\PDFs"` and `"C:\pdfs"` become different dict keys even though they're the same folder.

**Why it happens:** Workers may resolve paths differently based on how the OS returned the path. Example: user types `c:\pdfs`, OS returns `C:\pdfs`, different worker sees `C:\PDFS` from glob.

**How to avoid:**
1. **Always use `Path.resolve()`** before storing as dict key — returns canonical absolute path
2. Store `folder_path` as **relative to input_path** to reduce absolute path variance
3. Test on Windows with mixed-case directory names to catch edge cases

**Warning signs:**
- Same folder appears multiple times in `folder_stats` with different counts
- Folder counts don't sum to total file count
- Stats show `subdir` and `SubDir` as separate folders

**Validation:** Write test that processes PDFs in `C:\Test\Folder1` and `C:\test\folder1` — verify single `folder_stats` key, not two.

### Pitfall 2: Checkpoint Corruption from Missing fsync

**What goes wrong:** Without `os.fsync()` before `os.replace()`, data may still be in kernel buffers when the checkpoint file is moved. A crash or power loss results in incomplete JSON (e.g., `{}` or truncated content).

**Why it happens:** `file.flush()` only flushes to the OS buffer, not to physical disk. On Windows, `os.replace()` (MoveFileEx) doesn't guarantee the source file is fully written. Crash between flush and replace = data loss.

**How to avoid:**
1. **Always call `os.fsync(file.fileno())`** after `file.flush()` in tempfile
2. Reuse existing `save_checkpoint_atomic()` pattern (already includes fsync)
3. Test by killing process mid-write (Task Manager forceful terminate) and verifying state file still valid

**Warning signs:**
- Campaign state file has `{}` or partial JSON after crash
- Resume fails with `JSONDecodeError`
- `campaign_state.json` exists but is 0 bytes

**Validation:** Write test that forcefully terminates process during `save_campaign_state_atomic()` — verify previous state still intact (not corrupted by partial write).

### Pitfall 3: Silent Upgrade Mismatches Input Path

**What goes wrong:** User runs pipeline on `C:\pdfs`, creates checkpoint. Later runs on `C:\other_pdfs` but existing checkpoint from first run is still in output dir. Silent upgrade creates campaign state for first run's path, then processes second run's files — stats mismatch.

**Why it happens:** Output directory is persistent across runs. Checkpoint validation (existing code) warns about input path mismatch but allows resume. Campaign state needs same logic.

**How to avoid:**
1. **Validate `state.input_path == input_path`** on load
2. If mismatch: print warning, ask user to delete old state, or auto-create fresh state
3. Follow existing checkpoint pattern (lines 594-597) — warn but allow processing

**Warning signs:**
- Campaign state shows files from different directory than current run
- Folder stats include paths not in current input_path

**Validation:** Write test that loads campaign state with mismatched `input_path` — verify warning printed, processing continues or fails gracefully.

### Pitfall 4: Interruption Log Schema Premature Population

**What goes wrong:** Phase 6 establishes `interruptions` field schema but Phase 7 populates it. If Phase 6 tries to populate on Ctrl+C (before Phase 7 signal handling exists), it creates incomplete implementation.

**Why it happens:** Schema establishment vs. feature implementation confusion. Interruption logging requires SIGINT handler (Phase 7), but schema defined in Phase 6.

**How to avoid:**
1. **Phase 6:** Define `interruptions: list = field(default_factory=list)` schema only
2. **Phase 6:** Leave list empty in all created states
3. **Phase 7:** Implement actual interruption logging when SIGINT handler exists
4. Document clearly: "Schema established Phase 6, populated Phase 7"

**Warning signs:**
- Phase 6 tests try to simulate interruptions (not possible without signal handler)
- Code attempts to append to `interruptions` list before Phase 7

**Validation:** Phase 6 tests verify `interruptions` field exists and is empty list; Phase 7 tests verify entries are added.

## Code Examples

Verified patterns from stdlib docs and existing codebase:

### Campaign State Update (Periodic)

```python
# Source: Extend existing checkpoint pattern (precede_ocr.py lines 865-955)
def process_all_pdfs_with_campaign_state(
    pdf_paths: list[Path],
    campaign_state: CampaignState,
    output_dir: Path,
    workers: int,
    checkpoint_frequency: int
) -> list[dict]:
    """
    Enhanced process_all_pdfs with campaign state updates.

    Updates campaign state at same frequency as checkpoint (every N files).
    """
    all_results = []
    processed_files = set()

    with multiprocessing.Pool(processes=workers) as pool:
        pbar = tqdm(total=len(pdf_paths), desc="Processing PDFs", unit="file")

        for file_results in pool.imap_unordered(
            lambda p: process_single_pdf_wrapper(p, input_path_root=Path(campaign_state.input_path)),
            pdf_paths,
            chunksize=10
        ):
            all_results.extend(file_results)
            processed_files.add(file_results[0]['filename'])
            pbar.update(1)

            # Periodic update (same frequency as checkpoint)
            if len(processed_files) % checkpoint_frequency == 0:
                # Update campaign state counters
                campaign_state.files_processed = len(processed_files)
                campaign_state.files_failed = sum(
                    1 for r in all_results if 'error:' in r.get('notes', '')
                )
                save_campaign_state_atomic(campaign_state, output_dir)

        pbar.close()

    return all_results
```

### Folder Path Relative Computation

```python
# Source: pathlib.Path.resolve() + relative_to() from Python 3.14 stdlib docs
from pathlib import Path

input_path = Path("C:/Users/Owner/Documents/pdfs")
pdf_path = Path("C:/Users/Owner/Documents/pdfs/subfolder/batch1/file.pdf")

# Normalize both paths
input_resolved = input_path.resolve()  # C:\Users\Owner\Documents\pdfs
pdf_resolved = pdf_path.resolve()      # C:\Users\Owner\Documents\pdfs\subfolder\batch1\file.pdf

# Compute relative folder
pdf_folder = pdf_resolved.parent  # C:\Users\Owner\Documents\pdfs\subfolder\batch1
rel_folder = pdf_folder.relative_to(input_resolved)  # subfolder\batch1 (or subfolder/batch1 on POSIX)

folder_path = str(rel_folder)  # "subfolder/batch1" (pathlib uses forward slashes in str())

# Handle root case
if folder_path == '.':
    folder_path = ''  # Per D-08
```

## State of the Art

No paradigm shifts or deprecations for this phase — stdlib patterns are stable.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| shelve for state persistence | JSON with atomic writes | Python 3.3+ (os.replace) | shelve has corruption risks (macOS) and no concurrent read/write. JSON + atomic writes more robust. |
| Manual timestamp formatting | datetime.isoformat() | Always (stdlib) | ISO 8601 format is sortable, parseable, human-readable. Standard for timestamps. |

**Deprecated/outdated:**
- **shelve:** Per Python docs, "not suitable for concurrent access." Use JSON.
- **pickle for state:** Binary format, security risk. Use JSON for human-readable state.
- **os.rename:** Not atomic on Windows cross-volume. Use `os.replace` (Python 3.3+).

## Open Questions

**None.** All patterns validated in existing codebase or stdlib docs.

## Environment Availability

> Skip — Phase 6 has no external dependencies. All stdlib modules (json, dataclasses, tempfile, os, pathlib, datetime) ship with Python 3.14.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pytest.ini` |
| Quick run command | `pytest tests/test_precede_ocr.py::test_campaign_state -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STATE-01 | Campaign state persists ID/status/progress to JSON with atomic writes | unit | `pytest tests/test_precede_ocr.py::test_save_campaign_state_atomic -x` | ❌ Wave 0 |
| STATE-01 | Campaign state loads correctly on resume | unit | `pytest tests/test_precede_ocr.py::test_load_campaign_state -x` | ❌ Wave 0 |
| STATE-01 | Silent upgrade from v1.0 checkpoint creates campaign state | integration | `pytest tests/test_precede_ocr.py::test_silent_upgrade -x` | ❌ Wave 0 |
| STATE-02 | folder_path field added to result dicts, normalized correctly | unit | `pytest tests/test_precede_ocr.py::test_folder_path_injection -x` | ❌ Wave 0 |
| STATE-02 | folder_path handles root directory (empty string) | unit | `pytest tests/test_precede_ocr.py::test_folder_path_root -x` | ❌ Wave 0 |
| STATE-02 | folder_path normalizes Windows case-sensitivity | unit | `pytest tests/test_precede_ocr.py::test_folder_path_windows_case -x` | ❌ Wave 0 |
| STATE-03 | Interruption log schema exists and is empty list | unit | `pytest tests/test_precede_ocr.py::test_interruption_log_schema -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_precede_ocr.py::test_campaign_state -x` (quick smoke test)
- **Per wave merge:** `pytest tests/` (full suite, ~2 minutes)
- **Phase gate:** Full suite green + manual Windows path case test before `/gsd:verify-work`

### Wave 0 Gaps

All tests are new for Phase 6:

- [ ] `tests/test_precede_ocr.py::test_save_campaign_state_atomic` — covers STATE-01 atomic writes
- [ ] `tests/test_precede_ocr.py::test_load_campaign_state` — covers STATE-01 load/resume
- [ ] `tests/test_precede_ocr.py::test_silent_upgrade` — covers STATE-01 v1.0 upgrade (D-05, D-06)
- [ ] `tests/test_precede_ocr.py::test_folder_path_injection` — covers STATE-02 folder tracking (D-07)
- [ ] `tests/test_precede_ocr.py::test_folder_path_root` — covers STATE-02 root case (D-08)
- [ ] `tests/test_precede_ocr.py::test_folder_path_windows_case` — covers STATE-02 normalization (D-09)
- [ ] `tests/test_precede_ocr.py::test_interruption_log_schema` — covers STATE-03 schema (populated in Phase 7)

Existing test infrastructure (pytest 9.0.2, conftest.py fixtures) covers all phase requirements — no framework additions needed.

## Sources

### Primary (HIGH confidence)

**Python stdlib documentation:**
- [dataclasses — Python 3.14 Documentation](https://docs.python.org/3/library/dataclasses.html) — dataclass pattern, asdict() for serialization
- [json — Python 3.14 Documentation](https://docs.python.org/3/library/json.html) — JSON encoding/decoding
- [tempfile — Python 3.14 Documentation](https://docs.python.org/3/library/tempfile.html) — NamedTemporaryFile for atomic writes
- [os — Python 3.14 Documentation](https://docs.python.org/3/library/os.html) — os.replace (atomic), os.fsync (flush to disk)
- [pathlib — Python 3.14 Documentation](https://docs.python.org/3/library/pathlib.html) — Path.resolve() for normalization
- [datetime — Python 3.14 Documentation](https://docs.python.org/3/library/datetime.html) — isoformat() for timestamps

**Existing codebase (v1.0 patterns):**
- `precede_ocr.py` lines 555-579 — `save_checkpoint_atomic()` pattern with tempfile + fsync + os.replace
- `precede_ocr.py` lines 582-602 — `load_checkpoint_if_exists()` validation and error handling
- `precede_ocr.py` lines 840-862 — `process_single_pdf_wrapper()` result dict structure

**CONTEXT.md decisions:**
- D-01 through D-09 — locked implementation decisions for campaign state schema

### Secondary (MEDIUM confidence)

**Atomic file operations:**
- [Crash-safe JSON at scale: atomic writes + recovery without a DB](https://dev.to/constanta/crash-safe-json-at-scale-atomic-writes-recovery-without-a-db-3aic) — validates tempfile + fsync + os.replace pattern
- [How to Implement Atomic File Writing in Python (No Partial Writes) | BSWEN](https://docs.bswen.com/blog/2026-04-04-atomic-file-writing-python/) — confirms fsync requirement

**Path normalization:**
- [pathlib vs os.path Best Practices](https://medium.com/codeelevation/pathlib-vs-os-in-python-which-one-should-you-use-ed40a432673c) — 2025 best practice: use pathlib for path manipulation

### Tertiary (LOW confidence)

None — all patterns validated via official docs or existing codebase.

## Metadata

**Confidence breakdown:**
- Atomic write pattern: HIGH — already validated in v1.0 `save_checkpoint_atomic()`
- Path normalization: HIGH — `Path.resolve()` documented in stdlib, Windows behavior confirmed
- Campaign state schema: HIGH — simple dataclass with stdlib serialization
- Silent upgrade: MEDIUM — logic is straightforward but needs testing with real v1.0 checkpoints

**Research date:** 2026-06-05
**Valid until:** 90 days (stable stdlib patterns, no fast-moving dependencies)
