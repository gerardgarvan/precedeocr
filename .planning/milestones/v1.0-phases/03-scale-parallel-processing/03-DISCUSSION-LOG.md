# Phase 3: Scale — Parallel Processing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 03-scale-parallel-processing
**Areas discussed:** Multiple IDs per page, JSON output structure, Worker config & memory, Progress display

---

## Multiple IDs per page

### CSV representation

| Option | Description | Selected |
|--------|-------------|----------|
| One row per ID | Same page appears in multiple rows, each with a different ID. Easy to filter/sort in Excel. | Yes |
| One row per page | Single row per page with IDs in a delimited list column. Compact but harder to query. | |

**User's choice:** One row per ID
**Notes:** None

### Multi-rotation behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Keep early exit | Stop at first rotation that yields matches, return ALL matches from that rotation. Assumes all IDs on a page share orientation. | Yes |
| Try all rotations | Run all 4 rotations and collect unique IDs across all of them. Catches IDs at different orientations but 4x slower. | |
| You decide | Claude picks the approach. | |

**User's choice:** Keep early exit
**Notes:** None

### ID filtering

| Option | Description | Selected |
|--------|-------------|----------|
| Keep filtering | Continue filtering repeating patterns (00000, 11111, etc.). These are noise from blank regions. | Yes |
| Capture everything | Return all 5-digit matches unfiltered. Let user decide what's noise. | |

**User's choice:** Keep filtering
**Notes:** None

---

## JSON output structure

### JSON format

| Option | Description | Selected |
|--------|-------------|----------|
| Nested by filename | {"file.pdf": {"1": ["12345"], "2": ["67890", "11234"], "3": []}}. Natural for browsing by file. | Yes |
| Flat list of records | [{filename, page, id, rotation}, ...]. Same shape as CSV. | |
| ID-indexed lookup | {"12345": {filename, page}}. Optimized for ID lookup but loses multi-ID and no-ID info. | |

**User's choice:** Nested by filename
**Notes:** None

### Output mode

| Option | Description | Selected |
|--------|-------------|----------|
| Always both | Every run produces results.csv AND results.json. No flags needed. | Yes |
| Flag-controlled | --csv and --json flags to select output format. More control but more complexity. | |
| You decide | Claude picks the approach. | |

**User's choice:** Always both
**Notes:** None

---

## Worker config & memory

### Worker count

| Option | Description | Selected |
|--------|-------------|----------|
| Auto with override | Default cpu_count() - 1. User can override with --workers N. | Yes |
| Fully automatic | Always cpu_count() - 1. No flag. Simpler but no escape hatch. | |
| You decide | Claude picks. | |

**User's choice:** Auto with override
**Notes:** None

### Process recycling

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, maxtasksperchild | Set maxtasksperchild=50. Prevents memory growth over 30K files. | Yes |
| No recycling | Keep workers alive for whole run. Simpler but risky at 30K+ files. | |
| You decide | Claude picks a value. | |

**User's choice:** Yes, maxtasksperchild
**Notes:** None

---

## Progress display

### Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Per-file | Progress bar tracks files completed. Per-page would be noisy. | Yes |
| Per-file + page sub-bar | Main bar for files, secondary for pages. More detail but cluttered. | |
| You decide | Claude picks. | |

**User's choice:** Per-file
**Notes:** None

### Inline stats

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, inline stats | Running counts in tqdm postfix: IDs found, no-ID count, errors. | Yes |
| Bar only, summary at end | Clean bar during run, full stats after completion. | |
| You decide | Claude picks. | |

**User's choice:** Yes, inline stats
**Notes:** None

## Claude's Discretion

- Exact tqdm configuration (bar format, refresh interval)
- multiprocessing.Pool vs concurrent.futures.ProcessPoolExecutor choice
- Result aggregation strategy (queue vs return values)
- Batch size for imap_unordered chunking
- Output file naming for directory input mode

## Deferred Ideas

None — discussion stayed within phase scope.
