# Phase 13: CLI Subcommand Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 13-cli-subcommand-foundation
**Areas discussed:** Backward compatibility, Stub behavior, Code organization, Help text design

---

## Backward Compatibility

### Q1: Should bare invocation still work?

| Option | Description | Selected |
|--------|-------------|----------|
| Require 'scan' subcommand | Clean break. `python precede_ocr.py scan <dir>` only. Simpler argparse. | ✓ |
| Auto-detect bare path as 'scan' | If first arg is a path, treat as scan. Backward compatible but complex. | |
| Show help if no subcommand | Bare invocation shows help. No silent fallback. | |

**User's choice:** Require 'scan' subcommand
**Notes:** Clean break appropriate for v1.3 milestone

### Q2: No-argument behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-show help | Running with no arguments prints help and exits. Standard pattern. | ✓ |
| Require --help | Bare invocation shows short error with hint to use --help. | |

**User's choice:** Auto-show help

### Q3: Flag scope

| Option | Description | Selected |
|--------|-------------|----------|
| Scan-specific | All existing flags become scan-specific. Each subcommand gets own flags. | ✓ |
| Mixed (global + scan) | Keep --workers/--debug global, move others to scan. | |

**User's choice:** Scan-specific

---

## Stub Behavior

### Q1: What should stubs do?

| Option | Description | Selected |
|--------|-------------|----------|
| "Not yet implemented" message | Print friendly message and exit with code 1. | ✓ |
| Raise NotImplementedError | Python error with traceback. Developer-facing. | |
| Show subcommand help only | Print help text but don't execute. Preview of what's coming. | |

**User's choice:** "Not yet implemented" message

### Q2: Define stub arguments now?

| Option | Description | Selected |
|--------|-------------|----------|
| Define arguments now | Help shows planned interface. Validates CLI design early. | ✓ |
| Empty stubs | Subcommands exist but take no args until implemented. | |

**User's choice:** Define arguments now

---

## Code Organization

### Q1: File structure

| Option | Description | Selected |
|--------|-------------|----------|
| Keep single file | All CLI stays in precede_ocr.py. Consistent with project architecture. | ✓ |
| Split CLI into cli.py | New cli.py for parsing. precede_ocr.py as library. | |
| Commands directory | commands/ package with scan.py, lookup.py, etc. | |

**User's choice:** Keep single file

### Q2: Function naming

| Option | Description | Selected |
|--------|-------------|----------|
| Keep main() as-is | Dispatcher calls existing main(). Zero test changes. | ✓ |
| Rename to cmd_scan() | Cleaner naming but breaks 236 tests. | |

**User's choice:** Keep main() as-is

---

## Help Text Design

### Q1: Help organization

| Option | Description | Selected |
|--------|-------------|----------|
| Standard argparse subparsers | Default output. No custom formatting. Simple and maintainable. | ✓ |
| Custom formatted help | Manually formatted with sections and examples. More polished. | |

**User's choice:** Standard argparse subparsers

### Q2: Version display

| Option | Description | Selected |
|--------|-------------|----------|
| No version display | Keep it simple. Add --version later if needed. | ✓ |
| Add --version flag | Global --version prints version string. | |

**User's choice:** No version display

---

## Claude's Discretion

- Exact one-line descriptions for each subcommand in help text
- Argument names and help strings for stub subcommand parameters
- Order of subcommand registration in argparse
- How to structure the dispatcher (dict mapping vs if/elif)

## Deferred Ideas

None — discussion stayed within phase scope
