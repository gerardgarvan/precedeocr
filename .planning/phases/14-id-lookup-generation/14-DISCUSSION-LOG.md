# Phase 14: ID Lookup Generation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 14-id-lookup-generation
**Areas discussed:** Data filtering, Folder extraction, Completion summary

---

## Data Filtering

### No-match and Error Row Handling

| Option | Description | Selected |
|--------|-------------|----------|
| IDs only (Recommended) | Exclude rows with blank IDs and error rows. Lookup is purely for finding which file/page an ID is in. No-match and error analysis belongs in Phase 15. | Y |
| Include no-match rows | Keep blank-ID rows with a placeholder like 'NO_ID' so the lookup shows coverage gaps too. | |
| You decide | Claude picks the approach that best serves an ID lookup use case. | |

**User's choice:** IDs only (Recommended)
**Notes:** No additional clarification needed.

### Duplicate ID Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Keep all (Recommended) | Every occurrence of an ID is a valid lookup result. If ID 12345 appears in two files, both rows appear. Deduplication is Phase 16's job. | Y |
| Deduplicate by ID | Keep only the first occurrence of each ID. Simpler lookup but loses multi-file context. | |
| You decide | Claude picks based on the data characteristics. | |

**User's choice:** Keep all (Recommended)
**Notes:** No additional clarification needed.

---

## Folder Extraction

| Option | Description | Selected |
|--------|-------------|----------|
| Graceful fallback (Recommended) | Use folder_path column if present. If column is missing (older CSV), extract parent directory from the filename field. If filename has no path component, Folder is blank. | Y |
| Require folder_path | Error out if the source CSV doesn't have a folder_path column. User must re-run scan to get the new format. | |
| You decide | Claude picks the most robust approach. | |

**User's choice:** Graceful fallback (Recommended)
**Notes:** No additional clarification needed.

---

## Completion Summary

| Option | Description | Selected |
|--------|-------------|----------|
| Summary stats (Recommended) | Print total IDs, unique IDs, files covered, and output path. E.g.: 'Wrote 52,055 entries (48,901 unique IDs) from 30,316 files to output/lookup.csv' | Y |
| Minimal confirmation | Just print the output path: 'Lookup written to output/lookup.csv' | |
| You decide | Claude picks appropriate verbosity level. | |

**User's choice:** Summary stats (Recommended)
**Notes:** No additional clarification needed.

---

## Claude's Discretion

- Excel compatibility implementation details (BOM byte, quoting strategy)
- Exact error messages for invalid/missing input CSV
- Whether to use pandas or csv module for output
- Progress indication for large files (if needed)

## Deferred Ideas

None — discussion stayed within phase scope.
