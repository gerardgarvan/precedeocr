# Phase 7: Graceful Shutdown Infrastructure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 07-graceful-shutdown-infrastructure
**Areas discussed:** Double Ctrl+C behavior, Worker drain scope, Shutdown feedback

---

## Double Ctrl+C Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Force-quit immediately | Second Ctrl+C terminates workers and exits right away. Common CLI convention. Checkpoint from before shutdown is still safe. | ✓ |
| Warn and keep waiting | Print 'Shutdown in progress, please wait...' and ignore the second press. Safest for data integrity but can frustrate users. | |
| You decide | Claude picks based on Windows multiprocessing constraints | |

**User's choice:** Force-quit immediately (Recommended)
**Notes:** Standard CLI convention — users expect second Ctrl+C to force-quit.

### Follow-up: Force-quit exit message

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, brief warning | Print something like 'Force-quit! In-flight files may not be saved. Checkpoint has all completed files.' | ✓ |
| No, just exit silently | Terminate immediately with no extra output. | |
| You decide | Claude picks based on what's practical during forced termination | |

**User's choice:** Yes, brief warning (Recommended)
**Notes:** Sets user expectations for next resume.

---

## Worker Drain Scope

| Option | Description | Selected |
|--------|-------------|----------|
| File-level drain | Workers always finish the entire current PDF. Simpler, keeps results clean. Aligns with SHUT-01. | ✓ |
| Page-level drain | Workers check shutdown Event between pages and stop early. Faster shutdown on big PDFs, but creates partial results. Complicates resume logic. | |
| You decide | Claude picks based on codebase architecture | |

**User's choice:** File-level drain (Recommended)
**Notes:** No partial-file entries in checkpoint — clean resume behavior.

### Follow-up: Queue submission on shutdown

| Option | Description | Selected |
|--------|-------------|----------|
| Stop submission immediately | Set flag so main loop breaks out of imap_unordered. Workers in-flight finish, no new files dispatched. Fastest clean shutdown. | ✓ |
| Let queue drain naturally | Keep iterating but workers check Event before starting new file. Pool's chunksize means extra files may be 'started'. | |
| You decide | Claude picks based on how imap_unordered chunking works | |

**User's choice:** Stop submission immediately (Recommended)
**Notes:** Fastest clean shutdown path — no wasted work.

---

## Shutdown Feedback

### First Ctrl+C message

| Option | Description | Selected |
|--------|-------------|----------|
| Brief status line | Print '\nCtrl+C received. Finishing N in-flight files... (press Ctrl+C again to force-quit)' | ✓ |
| Just 'Shutting down...' | Minimal message. No worker count, no force-quit hint. | |
| You decide | Claude picks the message style | |

**User's choice:** Brief status line (Recommended)
**Notes:** Tells user what's happening and how to bail if needed.

### Exit stats after graceful shutdown

| Option | Description | Selected |
|--------|-------------|----------|
| Brief summary | Print 'Interrupted: 1,234/30,429 files processed (456 IDs found). State saved. Resume with same command.' | ✓ |
| Full batch stats | Print the same detailed BATCH PROCESSING SUMMARY as normal completion. | |
| No stats, just 'Saved and exited' | Minimal. User checks campaign_state.json if they want numbers. | |
| You decide | Claude picks appropriate detail level | |

**User's choice:** Brief summary (Recommended)
**Notes:** Tells users where they stand without overwhelming output on an interrupted run.

---

## Claude's Discretion

- tqdm cleanup mechanics (ANSI corruption prevention)
- Signal handler installation location
- Worker SIGINT protection approach
- Pool termination sequence (deadlock prevention)

## Deferred Ideas

None — discussion stayed within phase scope.
