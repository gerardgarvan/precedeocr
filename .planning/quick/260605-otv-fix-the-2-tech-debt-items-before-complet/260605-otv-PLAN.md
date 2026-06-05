---
phase: quick
plan: 260605-otv
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements.txt
  - tests/test_precede_ocr.py
autonomous: true
must_haves:
  truths:
    - "pip install -r requirements.txt installs scipy along with all other dependencies"
    - "tests/test_precede_ocr.py uses no deprecated Pillow APIs"
    - "All 141 tests pass without deprecation warnings"
  artifacts:
    - path: "requirements.txt"
      provides: "Complete dependency list including scipy"
      contains: "scipy"
    - path: "tests/test_precede_ocr.py"
      provides: "Test suite using current Pillow API"
      contains: "get_flattened_data"
  key_links: []
---

<objective>
Fix 2 tech debt items identified in v1.0 milestone audit before closing the milestone.

Purpose: Ensure requirements.txt is complete for fresh installs and eliminate Pillow deprecation warning before it becomes a breaking change.
Output: Updated requirements.txt with scipy, updated test file using non-deprecated Pillow API.
</objective>

<execution_context>
@.planning/v1.0-MILESTONE-AUDIT.md
</execution_context>

<context>
@requirements.txt
@tests/test_precede_ocr.py (line 1250)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add scipy to requirements.txt and fix Pillow deprecation</name>
  <files>requirements.txt, tests/test_precede_ocr.py</files>
  <action>
    1. In requirements.txt, add `scipy` as a dependency. Place it after `opencv-python` (alphabetical within the "processing" group). Do NOT pin to a specific version since the project uses whatever is currently installed. Use just `scipy` with no version constraint.

    Final requirements.txt should be:
    ```
    pytesseract==0.3.13
    pdf2image==1.17.0
    Pillow==12.2.0
    opencv-python==4.13.0.92
    scipy
    pandas==3.0.3
    tqdm>=4.60.0
    ```

    2. In tests/test_precede_ocr.py line 1250, replace the deprecated `Image.getdata()` call with the new `get_flattened_data()` method (available in Pillow 12.x, required in Pillow 14+).

    Change line 1250 from:
    ```python
        pixels = list(result.getdata())
    ```
    to:
    ```python
        pixels = list(result.get_flattened_data())
    ```

    This is the ONLY instance of getdata() in the codebase (confirmed by grep). No other files need changes.
  </action>
  <verify>
    <automated>cd C:\Users\Owner\Documents\precedeocr && python -m pytest tests/test_precede_ocr.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <done>
    - requirements.txt contains `scipy` as a dependency (7 total dependencies listed)
    - tests/test_precede_ocr.py line 1250 uses `get_flattened_data()` instead of `getdata()`
    - All 141 tests pass
  </done>
</task>

</tasks>

<verification>
1. `grep scipy requirements.txt` returns a match
2. `grep getdata tests/test_precede_ocr.py` returns NO matches (deprecated call removed)
3. `grep get_flattened_data tests/test_precede_ocr.py` returns a match (replacement in place)
4. `python -m pytest tests/test_precede_ocr.py -x -q` shows all 141 tests passing
</verification>

<success_criteria>
- requirements.txt includes scipy so fresh `pip install -r requirements.txt` installs all dependencies
- Zero instances of deprecated `Image.getdata()` in test code
- All 141 existing tests pass with no regressions
</success_criteria>

<output>
After completion, create `.planning/quick/260605-otv-fix-the-2-tech-debt-items-before-complet/260605-otv-SUMMARY.md`
</output>
