# Phase 8: Interactive Campaign Menu - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-06
**Phase:** 08-interactive-campaign-menu
**Areas discussed:** Menu display, Re-run failures, Menu trigger logic, Export partial

---

## Menu Display

### Q1: Campaign status info level

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal | Campaign ID, status (interrupted/completed), files done/total, failed count. Enough to decide without clutter. | ✓ |
| Detailed | Add last run timestamp, interruption count, elapsed time, and top error types. More context for informed decisions. | |
| You decide | Claude picks the right level of detail based on what CampaignState already tracks. | |

**User's choice:** Minimal
**Notes:** None

### Q2: Menu option format

| Option | Description | Selected |
|--------|-------------|----------|
| Numbered list | "[1] Continue  [2] Re-run failures  [3] ..." — user types a number. Simple, Windows-safe. | ✓ |
| Letter shortcuts | "[C] Continue  [R] Re-run  [S] Stats  [E] Export  [F] Fresh  [Q] Quit" — user types a letter. | |
| You decide | Claude picks the format based on what works best with input(). | |

**User's choice:** Numbered list
**Notes:** None

### Q3: Input validation

| Option | Description | Selected |
|--------|-------------|----------|
| Re-prompt with hint | Show "Invalid choice. Enter 1-6:" and loop until valid. Forgiving, no crash on typos. | ✓ |
| Strict, exit on invalid | Print error and exit. User re-runs the command. Simpler code, but worse UX. | |

**User's choice:** Re-prompt with hint
**Notes:** None

### Q4: View stats action

| Option | Description | Selected |
|--------|-------------|----------|
| Print summary, return to menu | Show files done/total, failed count, IDs found so far. Then re-display the menu. | ✓ |
| Print summary and exit | Show stats and quit. User re-runs to take another action. | |

**User's choice:** Print summary, return to menu
**Notes:** None

---

## Re-run Failures

### Q1: Failure definition

| Option | Description | Selected |
|--------|-------------|----------|
| Error entries only | Files with notes starting with 'error:' — actual exceptions during processing. | ✓ |
| Errors + no-ID pages | Also include files where every page returned no IDs. Broader — catches quality failures too. | |
| You decide | Claude determines the right failure criteria. | |

**User's choice:** Error entries only
**Notes:** None

### Q2: Checkpoint merge strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Replace old entries | Remove the error entries for those files from checkpoint, process fresh. New results replace old errors. | ✓ |
| Keep both, mark superseded | Keep old error entries but flag them as superseded. More audit trail, adds complexity. | |

**User's choice:** Replace old entries
**Notes:** None

### Q3: Post re-run behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Write output automatically | After re-run completes, generate updated CSV/JSON with merged results. Same as normal completion. | ✓ |
| Return to menu | Go back to menu so user can inspect stats or export manually before committing. | |

**User's choice:** Write output automatically
**Notes:** None

---

## Menu Trigger Logic

### Q1: When menu appears

| Option | Description | Selected |
|--------|-------------|----------|
| Checkpoint exists | Show menu when .checkpoint.json exists for this input path. No checkpoint = straight to processing. | ✓ |
| Campaign state exists | Show menu when campaign_state.json exists, even if no checkpoint. Broader trigger. | |
| You decide | Claude picks the right trigger. | |

**User's choice:** Checkpoint exists
**Notes:** None

### Q2: --fresh flag interaction

| Option | Description | Selected |
|--------|-------------|----------|
| Skip menu entirely | --fresh deletes checkpoint/state first, menu never appears. Consistent with current behavior. | ✓ |
| Show menu but pre-select Fresh | Show menu with Fresh Start highlighted. Gives user chance to change mind. | |

**User's choice:** Skip menu entirely
**Notes:** None

### Q3: 100% complete campaign

| Option | Description | Selected |
|--------|-------------|----------|
| Show menu with adjusted options | Show menu but 'Continue' is unavailable or says 'All files processed'. Re-run, stats, export, fresh still available. | ✓ |
| Skip menu, just report completion | Print 'All files already processed. Use --fresh to reprocess.' and exit. Current behavior. | |
| You decide | Claude determines the right behavior. | |

**User's choice:** Show menu with adjusted options
**Notes:** None

---

## Export Partial

### Q1: Export destination

| Option | Description | Selected |
|--------|-------------|----------|
| Same output paths | Write to --output-csv and --output-json locations. Final run overwrites with complete data. | ✓ |
| Separate 'partial' paths | Write to output/results_partial.csv and .json. Keeps partial and final separate. | |
| You decide | Claude picks based on existing output path handling. | |

**User's choice:** Same output paths
**Notes:** None

### Q2: Post-export behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Return to menu | Print confirmation and re-display menu. User can continue, quit, etc. | ✓ |
| Exit after export | Export and quit. User re-runs for further action. | |

**User's choice:** Return to menu
**Notes:** None

### Q3: Sequence validation on partial data

| Option | Description | Selected |
|--------|-------------|----------|
| Skip validation | Just export raw results from checkpoint. Partial data may trigger false warnings. | ✓ |
| Run validation | Apply Theil-Sen sequence validation to partial data. Gives early warning but may be noisy. | |

**User's choice:** Skip validation
**Notes:** None

---

## Claude's Discretion

- Exact wording of menu header and status lines
- How "Continue unavailable" is displayed when 100% complete
- Whether to show failed file count next to "Re-run failures" option
- Stats detail level in "View stats" beyond core metrics

## Deferred Ideas

None — discussion stayed within phase scope
