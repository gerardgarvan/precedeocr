# Phase 13: CLI Subcommand Foundation - Research

**Researched:** 2026-06-10
**Domain:** Python argparse subcommand architecture, CLI refactoring patterns
**Confidence:** HIGH

## Summary

Phase 13 refactors the existing flat argparse CLI into a subcommand architecture (scan, lookup, investigate, clean-multi-ids) while maintaining 100% backward compatibility for existing tests that import and call `main()` directly. The refactor is pure structure — zero functional changes to the scan operation.

**Key constraint:** All 236 existing tests must pass without modification. Tests import `main()` directly (`from precede_ocr import main`) and call it with positional arguments, not via CLI. The refactor must preserve this interface completely.

**Primary recommendation:** Use argparse's `add_subparsers()` with `set_defaults(func=...)` dispatch pattern. Keep `main()` unchanged as the scan handler. Add new stub handlers (`cmd_lookup()`, `cmd_investigate()`, `cmd_clean_multi_ids()`) that print "not yet implemented" messages. All parsing lives in the `if __name__ == '__main__'` block per Windows multiprocessing requirements.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Backward Compatibility:**
- **D-01:** Clean break — `python precede_ocr.py scan <dir>` is the only invocation form. Bare `python precede_ocr.py <dir>` (without `scan` keyword) no longer works.
- **D-02:** Running `python precede_ocr.py` with no arguments auto-shows help text and exits. No error message needed.
- **D-03:** All existing flags (`--output-csv`, `--output-json`, `--workers`, `--debug`, `--fresh`) become scan-specific. Each subcommand gets its own flags. No global flags shared across subcommands.

**Stub Behavior:**
- **D-04:** Unimplemented subcommands (`lookup`, `investigate`, `clean-multi-ids`) print a friendly "not yet implemented" message and exit with code 1. Example: `"lookup command not yet implemented. Coming in a future update."`
- **D-05:** Stub subcommands define their expected arguments now (positional args and flags from ROADMAP.md success criteria), so `--help` shows the planned interface. This validates the CLI design early and makes `--help` useful for discovery.

**Code Organization:**
- **D-06:** All CLI parsing stays in `precede_ocr.py`'s `if __name__ == '__main__'` block. Handler functions added to `precede_ocr.py`. Consistent with project's single-file architecture.
- **D-07:** Existing `main()` function keeps its name and signature unchanged. The dispatcher calls `main()` for the `scan` subcommand. Tests import `main()` directly and continue to work without modification.
- **D-08:** New handler functions for future subcommands follow naming convention: `cmd_lookup()`, `cmd_investigate()`, `cmd_clean_multi_ids()`.

**Help Text Design:**
- **D-09:** Standard argparse subparser help output. No custom HelpFormatter. Program description: "Precede OCR — PDF ID Scanner & Mapper". Each subcommand has a one-line description.
- **D-10:** No `--version` flag. Keep it simple. Add later if needed.

### Claude's Discretion
- Exact one-line descriptions for each subcommand in help text
- Argument names and help strings for stub subcommand parameters
- Order of subcommand registration in argparse
- How to structure the dispatcher (dict mapping vs if/elif)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOOK-03 | User can run `python precede_ocr.py lookup <scan.csv>` as a CLI subcommand | argparse subparser pattern with stub implementation (D-04, D-05) validates CLI interface early; actual lookup logic implemented in Phase 14 |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | stdlib (3.8+) | CLI parsing with subcommands | Python standard library. `add_subparsers()` method enables subcommand architecture (like git/svn). Mature, well-documented, zero dependencies. Already imported in `precede_ocr.py` line 12. |
| sys | stdlib | Exit codes for stub handlers | Standard library for `sys.exit(1)` in unimplemented subcommand stubs. |

### Supporting
None — this is a pure refactor using existing stdlib modules.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | click | Click offers decorators and cleaner syntax, but requires new dependency and full CLI rewrite. argparse sufficient for 4 subcommands. Overkill for this phase. |
| argparse | Typer | Typer uses type hints for modern CLI, but requires dependency and rewrite. No benefit over argparse for simple subcommands. |
| argparse | docopt | docopt parses help strings for CLI structure, but less flexible for programmatic subcommand addition. argparse more explicit. |

**Installation:**
None required — argparse and sys are Python stdlib.

## Architecture Patterns

### Recommended Project Structure
No file structure changes — single-file architecture preserved:
```
precede_ocr.py            # All code remains in this file
├── [imports]             # argparse already imported (line 12)
├── [existing functions]  # All preserved
├── main()                # UNCHANGED — scan handler (line 1903)
├── cmd_lookup()          # NEW — stub handler
├── cmd_investigate()     # NEW — stub handler
├── cmd_clean_multi_ids() # NEW — stub handler
└── if __name__ == '__main__':  # REFACTORED — subparser setup (line 2146)
```

### Pattern 1: Function Dispatch via set_defaults()
**What:** Attach handler functions to subparsers using `set_defaults(func=...)`, then dispatch with `args.func(args)`.

**When to use:** When each subcommand needs different logic. Standard argparse pattern for subcommands.

**Example:**
```python
# Source: https://docs.python.org/3/library/argparse.html (official)
def cmd_scan(args):
    """Handler for scan subcommand - calls existing main()."""
    main(args.input_path, args.output_csv, args.output_json,
         args.workers, args.debug, args.fresh)

def cmd_lookup(args):
    """Handler for lookup subcommand - stub for Phase 14."""
    print("lookup command not yet implemented. Coming in a future update.")
    sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Precede OCR — PDF ID Scanner & Mapper'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    # Scan subcommand
    scan_parser = subparsers.add_parser('scan', help='Extract IDs from PDFs')
    scan_parser.add_argument('input_path', help='Path to PDF or directory')
    scan_parser.add_argument('--output-csv', default='output/results.csv')
    scan_parser.add_argument('--workers', type=int, default=None)
    # ... other scan args ...
    scan_parser.set_defaults(func=cmd_scan)

    # Lookup subcommand (stub)
    lookup_parser = subparsers.add_parser('lookup', help='Generate ID lookup CSV')
    lookup_parser.add_argument('scan_csv', help='Path to scan results CSV')
    lookup_parser.set_defaults(func=cmd_lookup)

    args = parser.parse_args()
    args.func(args)  # Dispatch to handler
```

### Pattern 2: Wrapper Handlers for Existing Functions
**What:** Create thin wrapper functions that unpack argparse Namespace and call existing functions with their original signatures.

**When to use:** When you need to preserve an existing function's signature for backward compatibility (like `main()` for tests).

**Example:**
```python
# Source: Derived from project constraint D-07
def cmd_scan(args):
    """Wrapper that unpacks args and calls existing main()."""
    main(
        input_path=args.input_path,
        output_csv=args.output_csv,
        output_json=args.output_json,
        workers=args.workers,
        debug=args.debug,
        fresh=args.fresh
    )

# main() signature UNCHANGED — tests continue to import and call it directly
def main(input_path: str, output_csv: str, output_json: str | None = None,
         workers: int | None = None, debug: bool = False, fresh: bool = False) -> None:
    # Existing implementation untouched
    pass
```

### Pattern 3: Windows Multiprocessing Guard
**What:** Keep all argparse code inside `if __name__ == '__main__'` guard to prevent re-execution on Windows spawn.

**When to use:** Always, when using multiprocessing on Windows. Required by project (existing pattern at line 2146).

**Example:**
```python
# Source: precede_ocr.py line 2146 (existing pattern)
if __name__ == '__main__':
    # ALL argparse setup goes here
    parser = argparse.ArgumentParser(...)
    subparsers = parser.add_subparsers(...)
    # ... subcommand definitions ...
    args = parser.parse_args()
    args.func(args)

# NO argparse code at module level — would execute multiple times on Windows
```

### Pattern 4: Stub Implementation with Interface Definition
**What:** Define complete argument structure for unimplemented subcommands, but handler just prints "not implemented" message.

**When to use:** When building CLI incrementally — validates interface design early, makes `--help` useful for discovery.

**Example:**
```python
# Source: Derived from constraint D-05
def cmd_lookup(args):
    """Generate sorted ID lookup CSV from scan results."""
    print("lookup command not yet implemented. Coming in a future update.")
    sys.exit(1)

# In argparse setup:
lookup_parser = subparsers.add_parser(
    'lookup',
    help='Generate sorted ID lookup CSV from scan results'
)
lookup_parser.add_argument('scan_csv', help='Path to scan results CSV')
lookup_parser.add_argument('--output', default='output/lookup.csv',
                          help='Output path for lookup CSV (default: output/lookup.csv)')
lookup_parser.set_defaults(func=cmd_lookup)

# User can run: python precede_ocr.py lookup --help
# Shows full interface even though not implemented yet
```

### Anti-Patterns to Avoid
- **Modifying `main()` signature:** Tests import and call it directly — changing parameters breaks 236 tests (violates D-07)
- **Global argparse setup:** On Windows, module is re-imported for multiprocessing spawn — argparse at module level would parse args multiple times (violates Pattern 3)
- **Shared arguments across subcommands:** Each subcommand gets its own flags. No parent parser with shared args (violates D-03)
- **Custom dispatcher logic:** Use `set_defaults(func=...)` pattern, not manual if/elif chains — cleaner, more maintainable (best practice per official docs)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subcommand routing | Manual arg[0] checking + if/elif chain | `argparse.add_subparsers()` with `set_defaults(func=...)` | argparse handles help generation, validation, and routing automatically. Manual routing loses error messages, help text, and validation. |
| Argument validation | Manual type checking and path validation | argparse `type=int`, `choices=[...]` | argparse validates before your code runs. Manual validation duplicates work and creates inconsistent error messages. |
| Help text generation | Print statements + manual formatting | argparse auto-generated help via `--help` | argparse generates consistent help across all subcommands. Manual help text diverges over time. |
| Exit codes for stubs | Return values or exceptions | `sys.exit(1)` | POSIX standard: 0 = success, non-zero = failure. Shell scripts and CI systems check exit codes. |

**Key insight:** argparse's subparser system was designed for exactly this use case (git-style subcommands). Reinventing it creates maintenance burden and loses standard CLI conventions (--help, error messages, validation).

## Common Pitfalls

### Pitfall 1: Breaking Test Imports by Modifying main()
**What goes wrong:** Adding argparse parameters to `main()` signature, or renaming it to `cmd_scan()`, breaks all 236 tests.

**Why it happens:** Tests import `main()` directly: `from precede_ocr import main`. They don't go through argparse. Changing `main()`'s signature means tests won't pass correct arguments.

**How to avoid:**
1. Keep `main()` signature exactly as-is: `main(input_path: str, output_csv: str, output_json: str | None = None, workers: int | None = None, debug: bool = False, fresh: bool = False) -> None`
2. Create new `cmd_scan(args)` wrapper that unpacks argparse Namespace and calls `main()`
3. Constraint D-07 mandates this approach

**Warning signs:** Test failures like `TypeError: main() got an unexpected keyword argument 'command'`

### Pitfall 2: Windows Multiprocessing Re-executes Module-Level Code
**What goes wrong:** Argparse setup at module level (outside `if __name__ == '__main__'`) runs multiple times when multiprocessing spawns workers on Windows. Causes errors like "SystemExit: 2" from argparse failing on second parse.

**Why it happens:** Windows multiprocessing uses 'spawn' method (not 'fork'), which re-imports the module. Module-level code executes again in child processes.

**How to avoid:**
1. Keep ALL argparse code inside `if __name__ == '__main__'` guard (existing pattern at line 2146)
2. Only imports at module level, no argparse setup
3. Project already follows this pattern — preserve it

**Warning signs:** Multiprocessing jobs hang or fail with argparse errors on Windows

### Pitfall 3: Forgetting required=True for Subparsers
**What goes wrong:** Without `required=True`, user can run `python precede_ocr.py` with no subcommand. argparse succeeds but `args.func` doesn't exist, causing `AttributeError: 'Namespace' object has no attribute 'func'`.

**Why it happens:** Prior to Python 3.7, subcommands were optional by default. Many tutorials show older pattern without `required=True`.

**How to avoid:**
1. Use `subparsers = parser.add_subparsers(dest='command', required=True)`
2. Python 3.8+ project (per CLAUDE.md) supports this parameter
3. Constraint D-02 says no subcommand should show help and exit — `required=True` achieves this

**Warning signs:** Running script with no args causes AttributeError instead of showing help

### Pitfall 4: Stub Handlers That Don't Exit Non-Zero
**What goes wrong:** Stub handlers print "not implemented" but return 0 (success). CI systems and scripts think the command succeeded.

**Why it happens:** Python functions implicitly return None, which becomes exit code 0.

**How to avoid:**
1. Explicitly call `sys.exit(1)` after printing message
2. Constraint D-04 specifies exit code 1 for unimplemented commands
3. Standard POSIX convention: 0=success, 1+=failure

**Warning signs:** Scripts continue after "not implemented" message instead of stopping

### Pitfall 5: Argument Collisions Between Subcommands
**What goes wrong:** Two subcommands use same argument name (e.g., both scan and lookup have `--output`) but need different defaults or help text. One clobbers the other.

**Why it happens:** Misunderstanding of subparser namespace isolation — each subparser is independent.

**How to avoid:**
1. Each subcommand has its own parser — no sharing
2. Constraint D-03 mandates scan-specific flags
3. Don't use parent parser with shared arguments (violates D-03)

**Warning signs:** Help text shows wrong default for a subcommand

## Code Examples

Verified patterns from official sources and project constraints:

### Complete Subparser Setup (Main Structure)
```python
# Source: Derived from https://docs.python.org/3/library/argparse.html
# and project constraints D-01 through D-10
if __name__ == '__main__':
    # Main parser
    parser = argparse.ArgumentParser(
        description='Precede OCR — PDF ID Scanner & Mapper'
    )

    # Subparser manager — required=True forces user to pick a subcommand
    subparsers = parser.add_subparsers(dest='command', required=True)

    # ========== SCAN SUBCOMMAND (existing functionality) ==========
    scan_parser = subparsers.add_parser(
        'scan',
        help='Extract Precede IDs from PDF files'
    )
    scan_parser.add_argument(
        'input_path',
        help='Path to PDF file or directory of PDFs'
    )
    scan_parser.add_argument(
        '--output-csv',
        default='output/results.csv',
        help='Path to output CSV (default: output/results.csv)'
    )
    scan_parser.add_argument(
        '--output-json',
        default=None,
        help='Path to output JSON (default: same dir as CSV with .json extension)'
    )
    scan_parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: cpu_count()-1)'
    )
    scan_parser.add_argument(
        '--debug',
        action='store_true',
        help='Print raw OCR text for each rotation to stderr (single file only)'
    )
    scan_parser.add_argument(
        '--fresh',
        action='store_true',
        help='Delete existing checkpoint and start from scratch'
    )
    scan_parser.set_defaults(func=cmd_scan)

    # ========== LOOKUP SUBCOMMAND (stub for Phase 14) ==========
    lookup_parser = subparsers.add_parser(
        'lookup',
        help='Generate sorted ID lookup CSV from scan results'
    )
    lookup_parser.add_argument(
        'scan_csv',
        help='Path to scan results CSV'
    )
    lookup_parser.add_argument(
        '--output',
        default='output/lookup.csv',
        help='Output path for lookup CSV (default: output/lookup.csv)'
    )
    lookup_parser.set_defaults(func=cmd_lookup)

    # ========== INVESTIGATE SUBCOMMAND (stub for Phase 15) ==========
    investigate_parser = subparsers.add_parser(
        'investigate',
        help='Investigate failed files and no-match pages'
    )
    investigate_parser.add_argument(
        '--report',
        default='output/quality_report.md',
        help='Output path for quality report (default: output/quality_report.md)'
    )
    investigate_parser.set_defaults(func=cmd_investigate)

    # ========== CLEAN-MULTI-IDS SUBCOMMAND (stub for Phase 16) ==========
    clean_parser = subparsers.add_parser(
        'clean-multi-ids',
        help='Clean multi-ID pages with conservative deduplication'
    )
    clean_parser.add_argument(
        'scan_csv',
        help='Path to scan results CSV'
    )
    clean_parser.add_argument(
        '--output',
        default='output/results_cleaned.csv',
        help='Output path for cleaned CSV (default: output/results_cleaned.csv)'
    )
    clean_parser.add_argument(
        '--sample-size',
        type=int,
        default=200,
        help='Sample size for validation (default: 200)'
    )
    clean_parser.set_defaults(func=cmd_clean_multi_ids)

    # Parse and dispatch
    args = parser.parse_args()
    args.func(args)
```

### Handler Functions (Wrapper + Stubs)
```python
# Source: Derived from constraint D-07, D-08, D-04
def cmd_scan(args):
    """
    Handler for scan subcommand.
    Unpacks argparse Namespace and calls existing main() with original signature.
    """
    main(
        input_path=args.input_path,
        output_csv=args.output_csv,
        output_json=args.output_json,
        workers=args.workers,
        debug=args.debug,
        fresh=args.fresh
    )

def cmd_lookup(args):
    """
    Handler for lookup subcommand.
    Stub for Phase 14 implementation.
    """
    print("lookup command not yet implemented. Coming in a future update.")
    sys.exit(1)

def cmd_investigate(args):
    """
    Handler for investigate subcommand.
    Stub for Phase 15 implementation.
    """
    print("investigate command not yet implemented. Coming in a future update.")
    sys.exit(1)

def cmd_clean_multi_ids(args):
    """
    Handler for clean-multi-ids subcommand.
    Stub for Phase 16 implementation.
    """
    print("clean-multi-ids command not yet implemented. Coming in a future update.")
    sys.exit(1)

# main() remains COMPLETELY UNCHANGED
def main(input_path: str, output_csv: str, output_json: str | None = None,
         workers: int | None = None, debug: bool = False, fresh: bool = False) -> None:
    """
    Main entry point: discover PDFs, handle checkpoint/resume, process, write outputs + stats.

    [Existing docstring and implementation UNCHANGED]
    """
    # Existing implementation at line 1903 stays exactly as-is
    pass
```

### Test Compatibility Verification
```python
# Source: tests/test_precede_ocr.py line 13, 32
# Tests import and call main() directly — refactor must not break this

# Test imports (UNCHANGED)
from precede_ocr import main

# Test calls main() with positional args (UNCHANGED)
def test_main_writes_batch_stats_json(tmp_path):
    output_csv = tmp_path / 'results.csv'
    main(str(tmp_path), str(output_csv))  # Still works after refactor
    # ... assertions ...
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pytest.ini (testpaths=tests, python_files=test_*.py) |
| Quick run command | `pytest tests/test_precede_ocr.py -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOOK-03 | CLI accepts `lookup` subcommand | integration | `python precede_ocr.py lookup --help` (manual — check exit 0) | ✅ precede_ocr.py |
| N/A (refactor) | All existing tests pass | unit + integration | `pytest tests/ -v` | ✅ tests/test_precede_ocr.py |
| N/A (refactor) | main() signature unchanged | unit | `pytest tests/test_precede_ocr.py::TestEndToEndIntegration::test_main_writes_batch_stats_json -v` | ✅ tests/test_precede_ocr.py |

**Note:** Phase 13 is pure refactor with no new business logic. Existing test suite (236 tests) validates correctness — if all pass, refactor is correct. No new tests needed.

### Sampling Rate
- **Per task commit:** `pytest tests/ -x` (stop on first failure)
- **Per wave merge:** `pytest tests/ -v` (full suite verbose)
- **Phase gate:** Full suite green + manual CLI verification: `python precede_ocr.py --help`, `python precede_ocr.py scan --help`, `python precede_ocr.py lookup --help`

### Wave 0 Gaps
None — existing test infrastructure covers all phase requirements. 236 existing tests validate that `main()` remains functional and importable.

## Open Questions

None — argparse subparser pattern is mature and well-documented. All project constraints are explicit in CONTEXT.md.

## Sources

### Primary (HIGH confidence)
- [argparse — Parser for command-line options, arguments and subcommands](https://docs.python.org/3/library/argparse.html) - Official Python 3 documentation, authoritative source for add_subparsers() API
- precede_ocr.py lines 1903-1914, 2146-2161 - Existing main() signature and argparse structure (project source)
- tests/test_precede_ocr.py lines 13-39, 1262-1311 - Test imports and main() invocation patterns (project source)
- .planning/phases/13-cli-subcommand-foundation/13-CONTEXT.md - User decisions D-01 through D-10 (project constraints)

### Secondary (MEDIUM confidence)
- [mike.depalatis.net - Simplifying argparse usage with subcommands](https://mike.depalatis.net/blog/simplifying-argparse.html) - Best practices for set_defaults(func=...) pattern
- [Example of argparse with subparsers for python · GitHub](https://gist.github.com/amarao/36327a6f77b86b90c2bca72ba03c9d3a) - Community example of subparser setup
- [Multiprocessing behaviour of Python in Windows vs non-Windows](https://www.adrian.idv.hk/2018-11-16-pyfork/) - Windows spawn vs Unix fork behavior with multiprocessing

### Tertiary (LOW confidence)
None — all findings verified with official docs or project source code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - argparse is stdlib, official docs authoritative
- Architecture patterns: HIGH - Official Python docs + verified against project constraints
- Pitfalls: HIGH - Derived from official docs and project's existing multiprocessing usage
- Test compatibility: HIGH - Verified by reading existing test suite

**Research date:** 2026-06-10
**Valid until:** 90 days (argparse is stable stdlib, unlikely to change)
