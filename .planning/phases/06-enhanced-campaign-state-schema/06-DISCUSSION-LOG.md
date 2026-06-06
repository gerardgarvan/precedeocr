# Phase 6: Enhanced Campaign State Schema - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 06-enhanced-campaign-state-schema
**Areas discussed:** Campaign identity, State detail level, Backward compat, Folder tracking

---

## Campaign Identity

| Option | Description | Selected |
|--------|-------------|----------|
| Auto timestamp (Recommended) | campaign_20260605_143022 format. Human-readable, sortable, unique per run. No user input needed. | ✓ |
| UUID | Random UUID (e.g., a3f8c...). Guaranteed unique, but not human-readable. | |
| User-provided name | Prompt user for a campaign name at start. Most descriptive, but adds friction. | |

**User's choice:** Auto timestamp
**Notes:** None — straightforward decision.

### Follow-up: Include directory name in ID?

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp only (Recommended) | campaign_20260605_143022 — cleaner, shorter. Input path stored as separate field. | ✓ |
| Include dir name | campaign_PDFs_20260605_143022 — more context but could get long. | |

**User's choice:** Timestamp only

---

## State Detail Level

| Option | Description | Selected |
|--------|-------------|----------|
| Practical (Recommended) | Campaign ID, status, counts, timing, interruption log, input path, CLI options snapshot. | ✓ |
| Minimal | Campaign ID, status, processed count. Bare minimum for resume detection. | |
| Verbose | Everything in Practical plus per-file timing, per-page OCR confidence, worker assignment log. | |

**User's choice:** Practical
**Notes:** None.

### Follow-up: Interruption log detail per event

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp + progress (Recommended) | Each entry: {timestamp, files_processed, files_remaining}. | ✓ |
| Timestamp only | Just the ISO timestamp. | |
| You decide | Claude picks the right level of detail. | |

**User's choice:** Timestamp + progress

---

## Backward Compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| Silent upgrade (Recommended) | Auto-create campaign_state.json from checkpoint metadata, user sees upgrade message. | ✓ |
| Require --fresh | Old checkpoints treated as incompatible. User must pass --fresh. | |
| Notify and ask | Detect old checkpoint, print migration message, ask user to confirm. | |

**User's choice:** Silent upgrade
**Notes:** None.

---

## Folder Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Relative to input dir (Recommended) | Store folder_path as relative path from input directory. Portable. | ✓ |
| Full absolute path | Complete resolved path. Unambiguous but tied to machine. | |
| Parent folder only | Immediate parent directory name only. Simplest but collision risk. | |

**User's choice:** Relative to input dir
**Notes:** None.

### Follow-up: Root-level file folder_path value

| Option | Description | Selected |
|--------|-------------|----------|
| Empty string (Recommended) | folder_path: '' for root-level files. Phase 9 can display as '(root)'. | ✓ |
| Dot notation | folder_path: '.' for root-level files. Standard relative path convention. | |
| You decide | Claude picks whichever convention works best downstream. | |

**User's choice:** Empty string

---

## Claude's Discretion

- Campaign state JSON schema field names and nesting structure
- Whether to use dataclasses or plain dicts for internal state representation
- Checkpoint frequency and state update timing
- Error handling for edge cases

## Deferred Ideas

None — discussion stayed within phase scope
