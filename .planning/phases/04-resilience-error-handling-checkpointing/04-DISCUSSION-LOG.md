# Phase 4: Resilience — Error Handling & Checkpointing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-05
**Phase:** 04-resilience-error-handling-checkpointing
**Areas discussed:** Checkpoint format, Resume behavior, Error logging, Batch statistics

---

## Checkpoint Format

### Q1: What format should checkpoint data be stored in?

| Option | Description | Selected |
|--------|-------------|----------|
| JSON file | Simple, human-readable, easy to inspect/edit. Stores {processed_files, results}. Lightweight for 30K entries. Fits existing JSON output pattern. | Y |
| SQLite database | More robust for concurrent writes, but adds complexity. Better for multiple writers or very large datasets. | |
| You decide | Claude picks the simplest approach. | |

**User's choice:** JSON file
**Notes:** Fits existing pattern of JSON output in the project.

### Q2: Should the checkpoint save results incrementally or periodically?

| Option | Description | Selected |
|--------|-------------|----------|
| Every N files | Write checkpoint every 50-100 files. Balances crash safety with I/O overhead. | Y |
| After every file | Maximum crash safety, higher I/O overhead (30K writes). | |
| You decide | Claude picks based on performance tradeoffs. | |

**User's choice:** Every N files
**Notes:** None.

### Q3: Where should the checkpoint file live?

| Option | Description | Selected |
|--------|-------------|----------|
| Output directory | Same directory as results CSV/JSON. Keeps all run artifacts together. | Y |
| Next to input directory | Checkpoint lives alongside the PDF source directory. | |
| You decide | Claude picks the most practical location. | |

**User's choice:** Output directory
**Notes:** None.

### Q4: Should the checkpoint store full results or just filenames?

| Option | Description | Selected |
|--------|-------------|----------|
| Full results | Checkpoint includes extracted IDs/page data. On resume, these merge with new results. | Y |
| Filenames only | Just a set of processed filenames. Simpler but resume needs to re-extract results. | |

**User's choice:** Full results
**Notes:** None.

---

## Resume Behavior

### Q1: How should resume be triggered?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-detect | If checkpoint exists, automatically resume. No extra flag needed. | Y |
| Explicit --resume flag | User must pass --resume to use checkpoint. | |
| You decide | Claude picks the most user-friendly approach. | |

**User's choice:** Auto-detect
**Notes:** None.

### Q2: What should happen for a fresh start?

| Option | Description | Selected |
|--------|-------------|----------|
| --fresh flag | Add CLI flag that deletes existing checkpoint and starts over. | Y |
| Delete checkpoint manually | User deletes .checkpoint.json before re-running. | |
| You decide | Claude picks the approach. | |

**User's choice:** --fresh flag
**Notes:** None.

### Q3: How should stale checkpoints be handled?

| Option | Description | Selected |
|--------|-------------|----------|
| Validate input path | Checkpoint stores input path. On mismatch, warn. New files processed; removed files skipped. | Y |
| Always trust checkpoint | No validation. Just skip completed files. | |
| You decide | Claude picks a reasonable strategy. | |

**User's choice:** Validate input path
**Notes:** None.

---

## Error Logging

### Q1: Where should detailed error info be written?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate error log | Write output/errors.log with per-file entries. Keeps main CSV/JSON clean. | Y |
| Inline in CSV notes | Enhance existing notes column with more detail. | |
| Both | Errors in CSV (brief) AND separate log (detailed). | |

**User's choice:** Separate error log
**Notes:** None.

### Q2: Should failed files be retried?

| Option | Description | Selected |
|--------|-------------|----------|
| Retry once | Retry each failed file once before marking failed. Handles transient issues. | Y |
| No retry | Fail immediately and log. Fastest, simplest. | |
| Retry N times | Configurable retry count. More flexible but adds complexity. | |

**User's choice:** Retry once
**Notes:** None.

### Q3: Keep brief error in CSV notes column?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep brief error in CSV | CSV notes still shows error summary. Separate log has full detail. | Y |
| Remove from CSV | CSV only shows clean data. All errors move to separate log. | |

**User's choice:** Keep brief error in CSV
**Notes:** None.

---

## Batch Statistics

### Q1: Should stats be written to a file or just printed?

| Option | Description | Selected |
|--------|-------------|----------|
| Both | Print on screen AND write batch_stats.json. File useful for automation/auditing. | Y |
| Screen only | Just enhance existing print statements. No additional file. | |
| You decide | Claude picks based on usefulness for 30K batch. | |

**User's choice:** Both
**Notes:** None.

### Q2: What metrics to include?

| Option | Description | Selected |
|--------|-------------|----------|
| Standard set | Total files, successful, failed, total pages, IDs found, no-ID pages, errors, duration, rate. | Y |
| Minimal | Just total/success/fail counts and IDs found. | |
| You decide | Claude includes useful metrics. | |

**User's choice:** Standard set
**Notes:** None.

### Q3: Should stats include resume-aware metrics?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes | Stats distinguish checkpointed vs newly-processed results. | Y |
| No, just totals | Stats reflect final combined results regardless of resume. | |

**User's choice:** Yes
**Notes:** None.

---

## Claude's Discretion

- Exact checkpoint save frequency (N value)
- Internal checkpoint JSON structure/schema
- Error log format details
- Warning message wording for stale checkpoint
- Handling of corrupted checkpoint files

## Deferred Ideas

None — discussion stayed within phase scope.
