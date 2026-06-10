# Phase 13: CLI Subcommand Foundation - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Refactor the flat argparse CLI in `precede_ocr.py` into an argparse subparser architecture supporting four subcommands: `scan`, `lookup`, `investigate`, and `clean-multi-ids`. The `scan` subcommand wraps the existing `main()` function with identical behavior. Other subcommands are stubs with pre-defined argument interfaces, implemented in Phases 14-16.

Requirements in scope: LOOK-03

</domain>

<decisions>
## Implementation Decisions

### Backward Compatibility
- **D-01:** Clean break — `python precede_ocr.py scan <dir>` is the only invocation form. Bare `python precede_ocr.py <dir>` (without `scan` keyword) no longer works.
- **D-02:** Running `python precede_ocr.py` with no arguments auto-shows help text and exits. No error message needed.
- **D-03:** All existing flags (`--output-csv`, `--output-json`, `--workers`, `--debug`, `--fresh`) become scan-specific. Each subcommand gets its own flags. No global flags shared across subcommands.

### Stub Behavior
- **D-04:** Unimplemented subcommands (`lookup`, `investigate`, `clean-multi-ids`) print a friendly "not yet implemented" message and exit with code 1. Example: `"lookup command not yet implemented. Coming in a future update."`
- **D-05:** Stub subcommands define their expected arguments now (positional args and flags from ROADMAP.md success criteria), so `--help` shows the planned interface. This validates the CLI design early and makes `--help` useful for discovery.

### Code Organization
- **D-06:** All CLI parsing stays in `precede_ocr.py`'s `if __name__ == '__main__'` block. Handler functions added to `precede_ocr.py`. Consistent with project's single-file architecture.
- **D-07:** Existing `main()` function keeps its name and signature unchanged. The dispatcher calls `main()` for the `scan` subcommand. Tests import `main()` directly and continue to work without modification.
- **D-08:** New handler functions for future subcommands follow naming convention: `cmd_lookup()`, `cmd_investigate()`, `cmd_clean_multi_ids()`.

### Help Text Design
- **D-09:** Standard argparse subparser help output. No custom HelpFormatter. Program description: "Precede OCR — PDF ID Scanner & Mapper". Each subcommand has a one-line description.
- **D-10:** No `--version` flag. Keep it simple. Add later if needed.

### Claude's Discretion
- Exact one-line descriptions for each subcommand in help text
- Argument names and help strings for stub subcommand parameters
- Order of subcommand registration in argparse
- How to structure the dispatcher (dict mapping vs if/elif)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline Source
- `precede_ocr.py` — Main pipeline. Current argparse at lines 2146-2161 (flat ArgumentParser). `main()` at line 1903 (entry point for scan behavior). All existing flags defined here.

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` — LOOK-03 definition ("User can run `python precede_ocr.py lookup <scan.csv>` as a CLI subcommand")
- `.planning/ROADMAP.md` — Phase 13 success criteria (4 items), Phase 14-16 CLI interfaces (defines what arguments each stub subcommand needs)

### Test Suite
- `tests/test_precede_ocr.py` — 236 passing tests. Tests call `main()` directly (not through CLI). Must pass without modification.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `main()` at `precede_ocr.py:1903` — Complete scan implementation. Dispatcher just calls this with parsed args. Signature: `main(input_path, output_csv, output_json=None, workers=None, debug=False, fresh=False)`
- `argparse` already imported (line 12)

### Established Patterns
- **Single-file architecture:** `precede_ocr.py` is ~2160 lines. All functionality in one file. No package structure.
- **`if __name__ == '__main__'` guard:** Required for multiprocessing on Windows (spawn method). Currently at line 2146.
- **Hard-coded defaults:** Config values hard-coded, not parameterized. `--workers` is the only override flag.

### Integration Points
- `if __name__ == '__main__'` block (lines 2146-2161) — Replace flat argparse with subparser setup
- `main()` function (line 1903) — Called by scan dispatcher, signature unchanged
- New stub handler functions — Added above the `__main__` block
- Tests reference `from precede_ocr import main` — Must continue to resolve

</code_context>

<specifics>
## Specific Ideas

- Success criterion #3 ("All 236 existing tests pass without modification") is the hardest constraint — drives the decision to keep `main()` unchanged
- Stub argument definitions should match what ROADMAP.md Phase 14-16 success criteria describe (e.g., `lookup` takes `scan_csv` positional arg)
- The "not yet implemented" message pattern is common in CLIs being built incrementally

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-cli-subcommand-foundation*
*Context gathered: 2026-06-10*
