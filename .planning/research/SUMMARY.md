# Project Research Summary

**Project:** Precede OCR — PDF ID Scanner & Mapper (v1.1 Campaign Management)
**Domain:** Campaign management layer for batch OCR pipeline
**Researched:** 2026-06-05
**Confidence:** HIGH

## Executive Summary

This research synthesizes findings for adding campaign management features to the existing v1.0 batch OCR pipeline that processes ~30,429 multi-page PDFs on Windows 10. The v1.1 milestone adds production-grade UX for long-running campaigns: interactive menus for resume/re-run/stats, graceful Ctrl+C shutdown with checkpoint preservation, per-folder quality breakdowns, and statistics reporting. The recommended approach wraps the existing OCR pipeline without modifying its core logic, keeping risk low while adding critical operational features.

The key architectural insight is **separation of concerns**: campaign orchestration lives in a wrapper layer that manages state, presents menus, and handles signals, while the proven v1.0 OCR pipeline (Tesseract + multiprocessing + atomic checkpoints) remains unchanged. This minimizes integration risk and allows incremental delivery across 4 phases: (1) enhanced state schema, (2) graceful shutdown infrastructure, (3) interactive menu system, and (4) per-folder statistics.

Critical risks center on Windows-specific multiprocessing and signal handling limitations. Signal handlers execute only in the main thread, making blocking calls dangerous; workers inherit SIGINT and may terminate prematurely without protection; and Pool cleanup order is strict (drain → close → join → terminate) to avoid deadlocks. Research validates stdlib-only mitigations: use `multiprocessing.Event()` for cross-process shutdown coordination, set `signal.SIG_IGN` in worker initializers, replace blocking `pool.map()` with non-blocking `pool.imap_unordered()`, and ensure tqdm closes before Pool cleanup. All patterns validated from official Python docs, bug tracker issues, and production experience reports (HIGH confidence).

## Key Findings

### Recommended Stack

The v1.1 stack adds minimal dependencies to the proven v1.0 baseline (Tesseract, pytesseract, pdf2image, Pillow, OpenCV, pandas, tqdm, multiprocessing stdlib). Campaign features require only stdlib modules plus two optional libraries for UX polish.

**Core technologies for campaign management:**
- **signal (stdlib):** SIGINT handler for Ctrl+C on Windows. Only SIGINT and SIGBREAK available (not SIGTERM/SIGUSR1). Handlers execute in main thread only, requiring non-blocking patterns.
- **multiprocessing.Event (stdlib):** Cross-platform shutdown coordination. More reliable than signals for Windows 'spawn' mode. Workers check Event before starting new files.
- **questionary 2.1.1:** Interactive CLI menus via prompt_toolkit (cross-platform). Modern API: `questionary.select(message, choices).ask()`. Fallback: stdlib `input()` sufficient for simple number-select menus.
- **dataclasses-json 0.6.7:** Serialize/deserialize campaign state to JSON. Auto-handles nested dataclasses. Alternative: stdlib `json` + `dataclasses.asdict()` if compatibility issues.
- **tempfile + os.replace (stdlib):** Already validated in v1.0. Atomic state file writes prevent corruption on crash. Pattern: `NamedTemporaryFile()` → write → fsync → `os.replace()`.
- **collections.defaultdict/Counter (stdlib):** Per-folder statistics aggregation. Lightweight, fast, zero dependencies. Avoid `multiprocessing.Manager()` (10-100x overhead).

**Critical architectural decisions:**
- **Campaign state separate from checkpoint:** `campaign_state.json` stores metadata (status, folder stats, interruption log); `.checkpoint.json` stores granular results. Both updated atomically.
- **Stdlib-only menu:** Use `input()` for menus, not external libraries like simple-term-menu (Linux-only). Menu shown only when workers idle (input() blocks signals).
- **Event-based shutdown, not signal-only:** Signals don't propagate reliably to child processes on Windows. Event is cross-platform IPC mechanism.
- **Local stats aggregation, not Manager:** Workers return results to main process, main aggregates. Avoids IPC bottleneck for per-PDF stats.

**Version confidence:** HIGH — signal/Event/tempfile/collections from Python 3.14 stdlib docs; questionary 2.1.1 and dataclasses-json 0.6.7 from official PyPI (latest 2025-2026 releases); atomic write pattern validated in existing v1.0 codebase.

### Expected Features

Research identifies clear table stakes (users expect in any long-running batch job) vs. differentiators (set this tool apart) for campaign management.

**Must have (table stakes):**
- **Continue from checkpoint** — Resume after Ctrl+C or crash without reprocessing completed files. Already have v1.0 checkpoint; enhance with campaign metadata.
- **Graceful Ctrl+C handling** — Industry standard: stop accepting work → drain in-flight tasks → save state → exit cleanly. Requires signal handling + Event coordination.
- **Completion progress tracking** — Real-time "X of Y files (Z%)" with files/min rate and ETA. tqdm provides this out-of-box; enhance to show success/failure counts.
- **Success/failure counts** — Basic accountability: "Completed: 28,500 | Failures: 150 | Remaining: 1,779". Aggregate from checkpoint data.
- **View partial results** — Export CSV/JSON from checkpoint mid-run for spot-checking quality without waiting for completion.
- **Re-run failed files only** — Standard failure recovery: after fixing environment issues, retry only failed items. Filter checkpoint to create failure-only file list.
- **Real-time processing rate** — Files/min or pages/sec to estimate completion time. tqdm provides iteration rate; enhance to track separately for multi-page PDFs.
- **Error summary on exit** — Show "X files failed" with top failure reasons. List top 5 error types for debugging.

**Should have (differentiators):**
- **Interactive campaign menu** — Better UX than CLI flags: Continue / Re-run failures / View stats / Export partial / Fresh start. Use stdlib `input()` for simplicity.
- **Per-folder quality breakdown** — Unique insight: "Folder A: 99% success, Folder B: 85%" helps identify problem directories (e.g., older scans, different scanner quality).
- **Preprocessing fallback statistics** — Show how often fallback triggered: "Primary OCR: 92% | Fallback preprocessing: 8%". Already have fallback logic, just add counter.
- **Rotation heuristic reporting** — Track which rotations succeeded: "90°: 70% | 270°: 20%". Insight into document orientation patterns. Multi-rotation strategy already tracks successful angle.

**Defer (v2+):**
- **OCR confidence scores** — Tesseract provides per-character confidence; aggregating to page-level adds processing overhead (MEDIUM complexity, useful but not critical).
- **Smart ETA with historical data** — Regression models for per-folder rate prediction (HIGH complexity, linear ETA sufficient for v1.1).
- **Anomaly detection flags** — Statistical outlier flagging: "Folder X has 10x more failures than average" (HIGH complexity, requires Z-score modeling).
- **Batch comparison reports** — Compare multiple campaign runs for optimization experiments (requires campaign ID tracking, historical database — out of scope).

**Anti-features (explicitly avoid):**
- **Real-time dashboard web UI** — Out of scope per constraints (CLI-only). Stick to terminal UI; users can export results for analysis.
- **Automatic failure retry logic** — Dangerous without root cause understanding. Provide manual "Re-run failures" option instead.
- **Database-backed checkpoint** — JSON sufficient per constraints. No database dependencies.
- **Parallel campaign execution** — Confusing UX. One active campaign at a time. Users can run multiple terminal sessions manually if needed.
- **Interactive page-by-page review** — Not "no manual intervention" per constraints. Automated campaign only; manual review happens post-processing.
- **Cloud storage integration** — Local-only tool per constraints. Users can manually upload outputs if desired.
- **Adaptive parallelization** — Dynamic worker scaling adds complexity and unpredictability. Static worker count sufficient.

**Complexity estimate:** Priority 1+2 (table stakes + key differentiators): 20-30 hours across 4 phases.

### Architecture Approach

Campaign management adds three architectural layers atop the existing single-file OCR pipeline without modifying its core logic. The pattern: **campaign features wrap the pipeline, not interleave with it**. This preserves v1.0 stability while adding production UX.

**Major components:**
1. **Campaign State Manager** — Loads/saves `campaign_state.json` with campaign ID, status (running/interrupted/completed), folder-level stats, interruption log, and options snapshot. Supplements `.checkpoint.json` (doesn't replace it). Atomic writes with fsync for crash safety.

2. **Interactive Menu (stdlib only)** — Pre-run menu displays when checkpoint exists. Uses stdlib `input()` for action selection (Continue / Re-run failures / View stats / Export / Fresh). Menu only appears when workers idle (avoids input() blocking signals). No external dependencies.

3. **Signal Handler + Event Coordination** — Main process registers `signal.signal(SIGINT, handler)` to catch Ctrl+C. Handler sets `multiprocessing.Event()` flag. Workers initialized with `signal.SIG_IGN` to prevent premature termination, check Event before each PDF, finish in-flight work on shutdown. Strict Pool cleanup: close → join → terminate fallback.

4. **Folder Stats Aggregator** — Post-processes results to group by `Path.resolve()` normalized parent directory. Handles Windows case-insensitivity (`C:\PDFs` vs `C:\pdfs` → single key). Aggregates per-folder metrics: total files, IDs found, no-ID pages, errors. Uses `collections.defaultdict` for lightweight aggregation.

5. **Non-blocking Pool Iteration** — Replaces blocking `pool.map()` with `pool.imap_unordered()` to allow periodic signal checking. Drains iterator before Pool cleanup to prevent queue deadlock. Uses context manager (`with Pool() as pool`) for automatic cleanup.

**Data flow:**
```
CLI args → main_with_campaign()
  ↓
load_or_create_campaign_state() (campaign_state.json + .checkpoint.json)
  ↓
display_campaign_menu() if checkpoint exists
  ↓
setup_signal_handlers() (SIGINT → set Event)
  ↓
process_all_pdfs_with_shutdown() (existing pipeline with Event checks)
  ├─ multiprocessing.Pool(initializer=init_worker with signal.SIG_IGN)
  ├─ imap_unordered() with Event check in main loop
  ├─ Periodic checkpoint writes (every 50 files, unchanged)
  └─ On SIGINT: Event.set() → workers finish current file → pool.close() + join()
  ↓
aggregate_per_folder_stats(all_results)
  ↓
update_campaign_state(status='completed', stats=folder_stats)
  ↓
write_campaign_report() (Markdown summary)
```

**Key architectural patterns:**
- **Campaign layer wraps pipeline:** OCR core (`process_single_pdf()`, `extract_id_with_rotation()`) unchanged. Campaign logic in orchestration layer.
- **Separate state files:** Campaign metadata in `campaign_state.json`, granular results in `.checkpoint.json`. Both atomic writes, campaign state references checkpoint version.
- **Result dict enhancement (additive only):** Add `folder_path` field to result dicts in `process_single_pdf_wrapper()`. Backward compatible (v1.0 code ignores new field).
- **No changes to workers:** Workers still process one PDF end-to-end, return results. No campaign awareness except checking shutdown Event.

### Critical Pitfalls

Research identified 10 critical pitfalls specific to Windows multiprocessing + signal handling + campaign management. All HIGH confidence from official Python docs, bug tracker, and production reports.

1. **Signal handlers execute only in main thread (Windows spawn)** — Blocking calls like `pool.join()` or `pool.map()` prevent handler execution, making program unresponsive to Ctrl+C. **Prevention:** Use `pool.imap_unordered()` with timeout checks; replace blocking `join()` with timed polling; check shutdown Event in main loop with `break` on set.

2. **Workers inherit SIGINT and terminate prematurely** — Default SIGINT handler raises KeyboardInterrupt in workers, corrupting in-flight work and leaving incomplete checkpoint writes. **Prevention:** Set `signal.SIG_IGN` in Pool `initializer=init_worker`, let only main process handle Ctrl+C via signal handler + Event.

3. **Pool cleanup order causes deadlock or corruption** — Calling `terminate()` before draining iterators corrupts queues; calling `join()` without `close()` hangs indefinitely. **Prevention:** Strict sequence: drain `imap_unordered()` iterator → `pool.close()` → `pool.join(timeout=30)` → check workers finished → `pool.terminate()` only if timeout.

4. **Checkpoint corruption from concurrent writes or missing fsync** — `os.replace()` alone doesn't guarantee data on disk; crash during write leaves partial JSON. Multiple processes writing concurrently create race conditions. **Prevention:** Call `flush()` + `os.fsync()` before `os.replace()`; centralize checkpoint writes in main process only (workers return results, don't write).

5. **imap/imap_unordered deadlock on generator exceptions (Python <3.5)** — Fixed in 3.5+, but generator exceptions crash task handler thread causing indefinite hang. **Prevention:** Use Python 3.5+; wrap generators in exception handlers; or use pre-computed lists instead of generators.

6. **Shared Manager objects create performance bottleneck** — `multiprocessing.Manager()` proxies use IPC for every read/write, reducing performance 10-100x. **Prevention:** Use local counters in workers, aggregate in main process; never use Manager for high-frequency updates (per-PDF stats).

7. **tqdm progress bars leak or corrupt on Pool termination** — Abrupt termination (via `terminate()` or Ctrl+C) leaves terminal formatting corrupted (missing newlines, ANSI codes visible). **Prevention:** Always call `tqdm.close()` in finally block before Pool cleanup; use context manager `with tqdm() as pbar`.

8. **Windows signal limitations break cross-platform code** — Only SIGINT/SIGTERM/SIGBREAK available on Windows; SIGUSR1/SIGHUP crash with ValueError. **Prevention:** Use only SIGINT for cross-platform code; use `multiprocessing.Event()` for worker coordination (not signals).

9. **Interactive menu blocks signal handling during input()** — `input()` syscall doesn't return until Enter pressed; can't Ctrl+C during menu. **Prevention:** Show menu only when workers idle (not while Pool active); use non-blocking alternatives if workers must run during menu.

10. **Per-folder statistics require path normalization** — Windows paths case-insensitive but case-preserving; string keys create duplicates ("C:\\PDFs" vs "C:\\pdfs"). **Prevention:** Use `Path.resolve()` for absolute normalized paths; store as strings for dict keys; handle case-insensitive lookups on Windows.

## Implications for Roadmap

Based on research, campaign management should be built in 4 incremental phases that layer onto the existing v1.0 pipeline without modifying core OCR logic. Order dictated by dependency chain: state schema → shutdown infrastructure → menu UX → statistics. Each phase independently testable.

### Phase 1: Enhanced Campaign State Schema
**Rationale:** Foundation for all campaign features. Must establish state structure, atomic write patterns, and path normalization before adding menu or stats. Low risk since v1.0 checkpoint system already validates atomic writes.

**Delivers:**
- `campaign_state.json` schema (campaign ID, status, progress, folder stats, interruption log)
- `load_or_create_campaign_state()` / `update_campaign_state()` functions with atomic writes
- `folder_path` field added to result dicts in `process_single_pdf_wrapper()` (additive, backward compatible)
- Path normalization with `Path.resolve()` to avoid Windows case-sensitivity duplicates

**Addresses (table stakes):** Continue from checkpoint, per-folder statistics (differentiator)

**Avoids (critical pitfalls):** Pitfall #10 (path normalization), Pitfall #4 (checkpoint corruption via atomic writes)

**Uses (from stack):** tempfile + os.replace (already validated in v1.0), pathlib.Path, json stdlib, dataclasses + dataclasses-json

**Research flag:** No deeper research needed — extends existing checkpoint system with well-documented stdlib patterns. Standard file I/O.

---

### Phase 2: Graceful Shutdown Infrastructure
**Rationale:** Critical safety feature before adding interactive elements. Must establish signal handling, Event coordination, and Pool cleanup patterns to prevent data loss on Ctrl+C. Highest technical risk due to Windows multiprocessing quirks; research thoroughly validated mitigations.

**Delivers:**
- `signal.signal(SIGINT, handler)` registration in main process
- `multiprocessing.Event()` creation + passing via Pool initializer
- Worker initializer with `signal.SIG_IGN` to prevent premature termination
- Modified `process_all_pdfs()` → `process_all_pdfs_with_shutdown()` with Event checks in main loop
- Non-blocking `pool.imap_unordered()` replacing `pool.map()` to allow signal processing
- Strict cleanup sequence in finally block: drain iterator → close → join(timeout=30) → terminate fallback
- Campaign state marked `interrupted` on SIGINT with timestamp in interruption log
- tqdm.close() in finally block before Pool cleanup (prevent terminal corruption)

**Addresses (table stakes):** Graceful Ctrl+C handling, campaign resume after interrupt

**Avoids (critical pitfalls):** Pitfall #1 (main thread blocking), #2 (worker SIGINT), #3 (cleanup deadlock), #7 (tqdm leaks), #8 (Windows signals)

**Uses (from stack):** signal stdlib, multiprocessing.Event, Pool initializer, tqdm (existing)

**Research flag:** **Requires extensive manual testing on Windows** — automated tests can't fully validate Ctrl+C timing edge cases, second Ctrl+C force-quit, or zombie process cleanup. Budget 30-50% extra QA time. Test scenarios: Ctrl+C early/mid/late in batch, second Ctrl+C force-quit, verify Task Manager shows no zombie processes, checkpoint saved correctly on interrupt.

---

### Phase 3: Interactive Campaign Menu
**Rationale:** UX layer that surfaces campaign state to user. Depends on Phase 1 (state schema) for resume/stats display. Must follow Phase 2 (shutdown) to ensure menu doesn't block signal handling. Stdlib-only implementation (no external dependencies) reduces risk.

**Delivers:**
- `display_campaign_menu()` with stdlib `input()` — options: [1] Continue, [2] Re-run failures, [3] View stats, [4] Export partial, [5] Fresh start, [Q] Quit
- `display_folder_stats()` — table view of per-folder breakdown (uses campaign state from Phase 1)
- Menu action handlers:
  - Continue: calls existing `process_all_pdfs_with_shutdown()` with remaining PDFs
  - Re-run failures: filters to failed files from campaign state, creates new file list
  - View stats: displays folder table, returns to menu
  - Export partial: calls existing CSV/JSON writers with checkpoint data
  - Fresh start: deletes both `.checkpoint.json` and `campaign_state.json`, creates new campaign
- Menu flow: Load campaign state → Show menu (if checkpoint exists) → Dispatch action → Execute pipeline or loop to menu
- Menu only shown when workers idle (input() doesn't block active Pool)

**Addresses (table stakes):** Re-run failed files, view partial results; Interactive campaign menu (differentiator)

**Avoids (critical pitfalls):** Pitfall #9 (input() blocking signals — menu only when workers idle), Pitfall #5 (generator exceptions — pre-compute file lists before menu)

**Uses (from stack):** stdlib input() (primary), optional questionary 2.1.1 for better UX, pathlib for file operations

**Research flag:** No deeper research needed — simple menu pattern with stdlib. Manual testing required for UX validation (menu displays correctly, actions dispatch as expected, loop back to menu works).

---

### Phase 4: Per-Folder Statistics & Reporting
**Rationale:** Quality insights layer. Depends on Phase 1 (`folder_path` in results). Can be built in parallel with Phase 3 (menu) but reporting comes after pipeline completes. Lowest risk — pure post-processing of existing results.

**Delivers:**
- `aggregate_per_folder_stats()` — groups results by `folder_path`, calculates per-folder metrics:
  - total_files, processed, ids_found, no_id_pages, errors
  - preprocessing fallback trigger count (if fallback exists)
  - rotation distribution (90°/270°/0°/180°)
- Enhanced `campaign_state.json` with `folder_stats` dict populated after pipeline completes
- `write_campaign_report()` — Markdown report (`campaign_report.md`) with:
  - Campaign summary (ID, duration, total files, total IDs extracted)
  - Per-folder breakdown table
  - Problem area highlights (folders with high error rate)
  - Recommendations (e.g., "Re-run folder2 with --debug flag")
- Menu option [3] displays folder stats table from existing campaign state (doesn't re-run pipeline)

**Addresses (differentiators):** Per-folder quality breakdown, preprocessing fallback statistics, rotation heuristic reporting

**Avoids (critical pitfalls):** Pitfall #6 (Manager overhead — uses local aggregation in main process post-pipeline), Pitfall #10 (path normalization — established in Phase 1)

**Uses (from stack):** collections.defaultdict (lightweight aggregation), pathlib, Markdown string formatting

**Research flag:** No deeper research needed — straightforward aggregation with stdlib `collections.defaultdict`. Standard post-processing pattern.

---

### Phase Ordering Rationale

**Why this order:**
1. **Phase 1 before Phase 2:** Campaign state must exist before shutdown can mark it `interrupted`. Folder path tracking must be in place before workers start (can't retrofit after results collected).

2. **Phase 2 before Phase 3:** Graceful shutdown must work before menu appears, otherwise selecting "Continue" after Ctrl+C could encounter corrupt state or deadlocked Pool. Signal handling infrastructure is foundation for all interactive features.

3. **Phase 3 independent of Phase 4:** Menu and stats are orthogonal features; can be built in parallel. Menu doesn't require stats to function (shows "no stats available" if Phase 4 incomplete). Can defer Phase 4 if time-constrained without breaking menu.

4. **Phase 4 last:** Pure post-processing; no dependencies on it. Can be deferred if time-constrained without breaking core campaign functionality (continue/re-run/export still work).

**Dependency chain discovered in research:**
- Enhanced state schema (Phase 1) required by menu display (Phase 3) and stats reporting (Phase 4)
- Graceful shutdown (Phase 2) required before interactive menu (Phase 3) to prevent input() blocking Ctrl+C
- Folder path tracking (Phase 1) required by per-folder stats (Phase 4)
- No dependencies on Phase 4 (post-processing only)

**Architecture preserves v1.0 isolation:**
- All phases wrap existing `process_all_pdfs()` / `process_single_pdf()` without modifying OCR logic
- Worker functions unchanged except adding `folder_path` field to return dict (additive, backward compatible)
- Checkpoint writes remain atomic (tempfile + fsync + os.replace pattern validated in v1.0)
- Pool parallelization logic unchanged (coarse-grained per-PDF workers)

**Pitfall avoidance:**
- Phase 1 establishes atomic writes and path normalization before complexity added
- Phase 2 implements all shutdown safety patterns before interactive features (most dangerous phase — needs manual testing)
- Phase 3 builds menu only when shutdown patterns proven safe
- Phase 4 uses local aggregation patterns (not Manager) established from research

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 2 (Graceful Shutdown):** Windows multiprocessing has documented edge cases around SIGINT propagation, Pool zombie processes, and context manager cleanup. Research validates mitigations but **manual testing on Windows mandatory** — automated tests can't cover all Ctrl+C timing scenarios or force-quit (second Ctrl+C) behavior. Budget 30-50% more testing time than typical feature. Test checklist: Ctrl+C at various points (early/mid/late), second Ctrl+C force-quit, Task Manager zombie verification, checkpoint integrity after interrupt.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Campaign State):** Direct extension of existing v1.0 checkpoint system. Atomic write pattern already validated. Path normalization well-documented in pathlib docs. JSON schema design straightforward.
- **Phase 3 (Interactive Menu):** Stdlib `input()` pattern trivial. No complex integrations. UX testing required but no technical unknowns. Menu logic is simple dispatch.
- **Phase 4 (Folder Statistics):** Standard aggregation with `defaultdict`. No novel algorithms or libraries. Post-processing patterns well-documented.

**No phases need `/gsd:research-phase`** — all patterns sufficiently documented in this research synthesis and source files (STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md). Phase 2 needs validation/testing, not additional research.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | v1.0 technologies already validated in production per CLAUDE.md. v1.1 additions (questionary, dataclasses-json, signal/Event) from official PyPI + stdlib docs. All Windows-compatible. Tesseract 5.x + multiprocessing proven in existing codebase. |
| **Features** | HIGH | Table stakes derived from batch processing best practices (OneUpTime blog series 2026-01-30, graceful shutdown patterns). Differentiators align with campaign management use cases (per-folder stats, interactive menus). Anti-features clearly bounded by project constraints (CLI-only, local, no DB). Source quality high (official docs, industry best practices). |
| **Architecture** | HIGH | Campaign-wraps-pipeline pattern proven in similar batch systems. Signal handling + Event coordination documented in Python multiprocessing guides and production blog posts (The-Fonz, peterspython.com). Atomic checkpoint writes validated by v1.0 implementation. Windows-specific patterns verified via official Python docs (multiprocessing spawn, signal limitations), GitHub issues (SIGINT handling discussion #90064), and community reports. Separation of concerns reduces integration risk. |
| **Pitfalls** | HIGH | 10 critical pitfalls sourced from official Python bug tracker (issue #23051 imap deadlock, issue #38263 DupHandle race, issue #35629 Pool hang), stdlib signal docs (Windows limitations SIGINT/SIGBREAK only), multiprocessing docs (spawn vs fork), and production experience reports (tqdm terminal corruption, Manager IPC overhead, OSD unreliability). All have documented mitigations with code examples. Windows spawn behavior well-understood. |

**Overall confidence:** HIGH

Research is comprehensive with authoritative sources (official docs, PyPI, Python tracker, production experience). The v1.0 baseline already validates core patterns (Tesseract + multiprocessing + atomic checkpoints) in this codebase. v1.1 additions are well-trodden patterns (signal handling, interactive menus, stats aggregation) with stdlib-focused implementations that minimize external dependencies and Windows compatibility risks. Recommendations are prescriptive with specific code patterns and known pitfall mitigations.

### Gaps to Address

**Minor gaps requiring validation during implementation:**

1. **Windows-specific multiprocessing edge cases:** Research documents known pitfalls and mitigations, but Windows 'spawn' mode has subtle timing issues around Pool shutdown that can't be fully validated without manual testing. **Mitigation:** Phase 2 must include extensive manual QA on Windows 10 with large batches (1000+ PDFs), Ctrl+C at various points (early/mid/late), second Ctrl+C force-quit, and process cleanup verification in Task Manager. Create test checklist based on pitfalls research.

2. **questionary Windows compatibility:** Research indicates questionary 2.1.1 supports Windows via prompt_toolkit, but some users report terminal encoding issues on older Windows consoles. **Mitigation:** Include fallback to stdlib `input()` if questionary import fails or raises exceptions; test on Windows 10 cmd.exe and PowerShell terminals. If issues arise, use `input()` fallback (already designed). pick library with blessed backend is documented secondary fallback.

3. **dataclasses-json Python 3.14 support:** Library officially supports Python 3.7-3.12; no official 3.13+ release yet (as of June 2024 release). **Mitigation:** Test compatibility on Python 3.14 (project environment). If issues arise, use stdlib fallback: `json` + `dataclasses.asdict()` pattern (more manual but zero dependencies, already documented in research).

4. **Checkpoint file size growth:** With 30K+ PDFs, `campaign_state.json` folder stats could grow large if deeply nested directories. **Mitigation:** Monitor file size during Phase 4 testing; if > 10MB, consider storing only top-level folder aggregates or compressing with gzip. Research shows JSON sufficient but validate at scale.

5. **tqdm terminal corruption edge cases:** Research documents tqdm.close() in finally block prevents most corruption, but some Windows terminals (older cmd.exe) may still have issues. **Mitigation:** Test on target Windows 10 environment; if issues persist, consider tqdm-multiprocess library (documented in STACK.md) or fallback to simple print() progress (less UX but more robust).

**All gaps are validation questions, not research gaps.** Existing research provides proven mitigation strategies; implementation needs to validate on target hardware/OS and tune based on observed behavior (e.g., adjust Pool timeout values, choose questionary vs input() based on terminal compatibility).

## Sources

### Primary (HIGH confidence)

**Official Documentation:**
- Python stdlib documentation: signal, multiprocessing, pathlib, tempfile, collections, dataclasses — official Python 3.14 docs validate all core patterns
- PyPI official pages: pytesseract, pdf2image, Pillow, opencv-python, pandas, tqdm, questionary, dataclasses-json, pick — version info, dependencies, platform support
- Python bug tracker: Issue #23051 (imap deadlock), Issue #38263 (DupHandle race), Issue #35629 (Pool hang) — known multiprocessing pitfalls with documented workarounds
- Tesseract GitHub: Issue #4426 (OSD unreliability June 2025) — validates multi-rotation strategy over OSD

**Windows-specific:**
- Microsoft documentation: Windows signal handling (SIGINT/SIGBREAK only), file system operations (MoveFileEx atomicity)
- Python Windows multiprocessing: spawn method requirements, pickle overhead, process creation costs

### Secondary (MEDIUM confidence)

**Batch Processing Best Practices:**
- OneUpTime blog series (2026-01-30): batch statistics, monitoring, reporting, metrics — establishes table stakes features
- Campaign management patterns: Google Patents GB2364399A, GE Digital Campaign Manager Guide — validates campaign workflow patterns
- Checkpoint/resume workflows: fast.io AI agent checkpointing, Microsoft Learn workflows — confirms checkpoint-based resume patterns

**Graceful Shutdown Patterns:**
- Zylos.ai research (2026-02-25): graceful shutdown for long-lived services — validates Event-based coordination
- River docs: graceful shutdown patterns — confirms signal handling approach
- The-Fonz blog: graceful exit with Python multiprocessing — code examples for Pool cleanup
- peterspython.com (2026): multiprocessing graceful shutdown in proper order — validates close → join → terminate sequence
- DEV Community (2026): Go shutdown patterns (concepts applicable to Python) — general shutdown principles

**Interactive CLI Patterns:**
- InquirerPy GitHub + docs: interactive CLI prompts and menus — validates questionary choice
- ArjanCodes blog: Rich Python library for interactive CLI tools — confirms Rich + questionary integration
- The Green Report: interactive CLI automation with Python — validates prompt_toolkit approach

**Progress Tracking:**
- Rich documentation: progress display, multi-threading visualization — validates Rich Progress patterns
- Lei Mao's Log Book: Python tqdm multiprocessing — confirms tqdm.close() in finally block
- Redowan's Reflections: running tqdm with multiprocessing — validates process_map() approach

**Atomic File Operations:**
- Crash-safe JSON (2026 dev.to): atomic writes + recovery patterns — validates tempfile + fsync + os.replace
- BSWEN blog (2026-04-04): atomic file writing in Python — confirms no partial writes pattern

### Tertiary (LOW confidence)

**OCR Comparisons:**
- Codesota (2026), TTSforFree (2026): Tesseract vs EasyOCR comparisons — used for stack selection but not critical to campaign features
- DocSumo: OCR accuracy analysis — general benchmarks, not specific to this project

**Source aggregation:** 60+ sources reviewed across 4 research files (STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md); convergence across official docs, GitHub issues, Python tracker, and technical blogs provides HIGH confidence for campaign management recommendations. v1.0 baseline already validates OCR stack; v1.1 focuses on orchestration patterns which are well-documented in stdlib and community best practices.

---

**Research completed:** 2026-06-05
**Ready for roadmap:** Yes

**Next steps for orchestrator:**
1. Load SUMMARY.md as context for roadmap creation
2. Use suggested 4-phase structure as starting point
3. Apply research flags (all phases skip research-phase; Phase 2 needs extensive manual testing)
4. Reference STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md for detailed specifications during phase planning
5. Note: v1.0 baseline already complete per CLAUDE.md; roadmap should focus on v1.1 campaign management additions only
