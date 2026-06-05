---
phase: quick
plan: 260605-otv
status: complete
completed_at: "2026-06-05T21:55:21Z"
duration_seconds: 49
subsystem: dependencies, testing
tags: [tech-debt, deprecation-fix, requirements]
dependency_graph:
  requires: []
  provides: [complete-requirements-txt, pillow-14-ready]
  affects: [fresh-installs, test-suite]
tech_stack:
  added: [scipy]
  patterns: [deprecation-migration]
key_files:
  created: []
  modified:
    - requirements.txt
    - tests/test_precede_ocr.py
decisions: []
metrics:
  tasks_completed: 1
  tasks_total: 1
  files_modified: 2
  tests_run: 141
  tests_passed: 141
  commit_hash: 39383f0
---

# Quick Task 260605-otv: Fix Tech Debt Items

**One-liner:** Added scipy to requirements.txt and migrated test suite from deprecated Image.getdata() to get_flattened_data() for Pillow 14+ compatibility.

## Objective

Fix 2 tech debt items identified in v1.0 milestone audit before closing the milestone:
1. Missing scipy dependency in requirements.txt (required by validate_sequence function)
2. Deprecated Pillow API usage (Image.getdata() scheduled for removal in Pillow 14)

## What Was Built

### Dependency Management
- **requirements.txt updated**: Added `scipy` as unpinned dependency (placed after opencv-python in alphabetical order)
- **Fresh install support**: New installs via `pip install -r requirements.txt` now include all required dependencies
- **Existing behavior preserved**: Unpinned to match project pattern for libraries where version flexibility is acceptable

### Deprecation Fix
- **Pillow API migration**: Replaced deprecated `Image.getdata()` with `get_flattened_data()` in test_precede_ocr.py:1250
- **Single instance fix**: This was the only occurrence of the deprecated method in the codebase (confirmed via grep)
- **Forward compatibility**: Code now works with current Pillow 12.x and future Pillow 14+ releases

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All verification criteria passed:

1. `grep scipy requirements.txt` → Match found (scipy present)
2. `grep getdata tests/test_precede_ocr.py` → No matches (deprecated call removed)
3. `grep get_flattened_data tests/test_precede_ocr.py` → Match found at line 1250
4. `python -m pytest tests/test_precede_ocr.py -x -q` → 141 passed in 10.78s

No regressions. No deprecation warnings.

## Known Stubs

None. This was a tech debt cleanup task with no new feature work.

## Files Modified

| File | Changes | Commit |
|------|---------|--------|
| requirements.txt | Added `scipy` dependency | 39383f0 |
| tests/test_precede_ocr.py | Line 1250: `getdata()` → `get_flattened_data()` | 39383f0 |

## Impact

### Immediate Benefits
- **Fresh installs work**: New developers can install all dependencies via requirements.txt without manually discovering scipy is needed
- **No warnings**: Eliminated deprecation warning that appeared during test runs
- **Future-proof**: Code ready for Pillow 14+ where getdata() will be removed

### Risk Assessment
- **Risk level**: None
- **Changes**: Minimal (1 line added to requirements.txt, 1 method call renamed in tests)
- **Test coverage**: All 141 existing tests passing confirms no regressions
- **Backward compatibility**: get_flattened_data() available in Pillow 12.x (current project version)

## Commit

```
chore(quick-260605-otv): add scipy dependency and fix Pillow deprecation

- Add scipy to requirements.txt for fresh installs (used by validate_sequence)
- Replace deprecated Image.getdata() with get_flattened_data() in test_precede_ocr.py:1250
- All 141 tests passing with no deprecation warnings

Commit: 39383f0
```

## Self-Check: PASSED

### Files Verified
- [x] requirements.txt exists and contains scipy
- [x] tests/test_precede_ocr.py exists and uses get_flattened_data()

### Commit Verified
```bash
$ git log --oneline --all | grep 39383f0
39383f0 chore(quick-260605-otv): add scipy dependency and fix Pillow deprecation
```

All claimed files exist. Commit exists in git history.

---

**Status:** Tech debt items resolved. v1.0 milestone ready for closure.
