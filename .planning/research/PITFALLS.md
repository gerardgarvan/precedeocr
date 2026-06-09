# Pitfalls Research

**Domain:** OCR Post-Processing and Result Cleanup
**Researched:** 2026-06-09
**Confidence:** MEDIUM

## Critical Pitfalls

### Pitfall 1: Overzealous Noise Filtering Silently Deletes Real IDs

**What goes wrong:**
Post-processing filters designed to remove OCR "noise" (malformed IDs, OCR artifacts) accidentally classify legitimate IDs as noise and delete them. The data loss is silent—no error raised, IDs simply vanish from final output. In this project's context: removing a real ID means that file/page becomes unsearchable, defeating core value.

**Why it happens:**
- **False positive trap**: Training on limited samples creates overly strict filters. For example, if sample data shows IDs follow sequential patterns (10001, 10002, 10003), the filter rejects "outlier" IDs (11000, 09500) as noise even when legitimate.
- **Confidence threshold miscalibration**: OCR confidence scores are often poorly calibrated—a 0.9 confidence might only be 70% accurate in practice. Setting a "conservative" threshold (e.g., reject <0.8 confidence) still removes real low-quality scans.
- **Pattern overfitting**: Regex or validation rules tuned on clean samples fail on real production variance (degraded scans, unusual document batches, handwritten annotations that confuse OCR into extracting spurious digits alongside real IDs).

Research shows: "The false positive rate—rejecting a correct OCR word in favor of its correction-candidate—is a significant concern, as most OCR words are correct and such rejections would significantly harm the reliability of the method" ([OCR Post-Processing Error Correction, arXiv](https://arxiv.org/pdf/1204.0191)). Systems prioritize "false positive rate diminution over false negative diminution" to avoid this trap.

**How to avoid:**
1. **Bias toward preservation**: Default to keeping questionable IDs unless strong evidence of noise (e.g., ID appears 50+ times on one page, clearly OCR hallucination).
2. **Separate flagging from deletion**: Create a "low_confidence" or "needs_review" category instead of deleting. Include in output with a flag column.
3. **Multi-signal validation**: Don't rely solely on confidence scores. Use: (a) Regex match strength (5-digit numeric), (b) OCR confidence, (c) Context (is word "Precede" nearby?), (d) Frequency (1-3 IDs per page normal, 50 IDs suspicious).
4. **Sampling validation**: Before applying filter to 52K IDs, manually validate filter decisions on random 200-ID sample. Check false negative rate.
5. **Preserve raw data**: Keep original OCR results in separate file/column. Filtered output can be regenerated if filter is wrong.

**Warning signs:**
- Output ID count significantly lower than OCR extraction count without corresponding increase in "no_match" pages
- Disproportionate filtering in specific folders (e.g., 20% of IDs removed from FolderA, <1% from FolderB) suggests filter is overfitting to one subset
- User reports "I know this ID exists but can't find it" after lookup file published
- Validation sample shows filter removing IDs that pass manual inspection

**Phase to address:**
Phase 1 (Multi-ID investigation) — validate filter logic on sample before applying to full dataset. Phase 2 (Lookup generation) — preserve raw OCR data alongside filtered output.

---

### Pitfall 2: Deduplication False Positives Lose Multi-ID Context

**What goes wrong:**
Deduplication logic treats multiple legitimate IDs on the same page as "duplicates" and keeps only one. Example: Page contains two specimens labeled 10001 and 10002. Dedup logic sees "multiple IDs extracted from page 5" and arbitrarily keeps 10001, discarding 10002. Now 10002 is unsearchable.

Variant: Same ID appears on consecutive pages (e.g., two-page spread for one specimen). Dedup sees "10001 on page 3, 10001 on page 4" and removes one, causing lookup to point to wrong page.

**Why it happens:**
- **OCR multi-match assumption**: Developers assume "multiple IDs from one page = OCR error" because training data had one ID per page. Production data (5,141 multi-ID pages = 11.2% of corpus) violates this assumption.
- **Fuzzy matching overapplication**: Dedup uses fuzzy matching to handle OCR variations (10001 vs 1O001). Fuzzy threshold set too loose causes distinct IDs to merge (10001 = 10002 if Levenshtein distance <2).
- **Page-level grouping logic**: Grouping by filename+page and keeping "first occurrence" discards legitimate secondary IDs.

Research context: "Extraction errors from OCR manifest themselves in the deduplication process and throw off any decision made based on such erroneous extractions" ([Noise-Robust De-Duplication at Scale, arXiv](https://arxiv.org/pdf/2210.04261)). "Setting a high threshold when using fuzzy matching makes sure you don't get too many false positives" ([Fuzzy Matching Guide 2026, DataLadder](https://dataladder.com/fuzzy-matching-101/)).

**How to avoid:**
1. **Preserve multi-ID pages**: If page has 2-5 IDs, keep all by default (suspicious threshold >5 IDs suggests OCR noise).
2. **Exact-match deduplication only**: Only deduplicate exact string matches within same page (removes true duplicates from 4-rotation OCR passes). Never fuzzy-deduplicate across pages or across files.
3. **Cross-page dedup with caution**: If same ID on consecutive pages, verify it's truly duplicate (same file, pages N and N+1) vs. separate occurrences (different files). Document decision in notes column.
4. **Sequential ID context**: If page has [10001, 10002], validate both IDs fit sequential pattern (likely real). If [10001, 83947], investigate further (might be noise + real ID).
5. **Audit trail**: Log every dedup decision ("Removed ID 10001 from page 4 because duplicate of page 3") for manual review.

**Warning signs:**
- Dedup removes >5% of extracted IDs (too aggressive)
- Sequential ID gaps in final output (have 10001, 10003 but missing 10002—likely dedup false positive)
- Multi-ID pages consistently reduced to single ID in specific folders
- User feedback: "File has two specimens but I can only find one ID"

**Phase to address:**
Phase 1 (Multi-ID investigation) — establish dedup rules through sampling. Phase 2 (Lookup generation) — implement conservative exact-match-only dedup.

---

### Pitfall 3: FileNotFoundError Misdiagnosis (Race Condition vs. Real Missing Files)

**What goes wrong:**
Error investigation finds 46 FileNotFoundError failures and assumes "files are missing/deleted." Root cause is actually: (a) Windows path encoding issues (Unicode filenames), (b) multiprocessing race condition (temp files cleaned up before worker accesses them), or (c) filesystem timing (network drive latency). Re-running same files succeeds, but investigation blames "file system corruption" and moves on. Real cause (multiprocessing bug, path handling) remains unfixed and randomly resurfaces.

**Why it happens:**
- **Windows multiprocessing 'spawn' semantics**: Windows uses 'spawn' (not 'fork'), requiring serialization of objects passed to workers. If a Path object references a temp file cleaned up before worker deserializes, FileNotFoundError occurs even though original file exists.
- **Unicode path handling**: Windows has two path APIs (ANSI, Unicode). If PDF filename contains non-ASCII characters (é, ñ, 中) and code uses incorrect API, file exists but appears "not found."
- **Network drive timing**: If PDFs on network share (SMB, NFS), filesystem metadata cache can lag. Worker checks file existence, gets stale "not found" result, then file appears milliseconds later.
- **Shared state cleanup**: If multiple workers write to shared output folder and one worker deletes temp files while another is reading, race condition FileNotFoundError.

Python multiprocessing research shows: "FileNotFoundError can occur when sharing concurrency primitive objects with child processes, because processes coordinate with each other via files on the hard drive. The error requires that the main process finishes before the child process has had time to start-up completely" ([Fix FileNotFoundError With Multiprocessing, Super Fast Python](https://superfastpython.com/filenotfounderror-multiprocessing-python/)).

**How to avoid:**
1. **Verify file existence first**: Before attributing to missing files, manually check if file exists on filesystem. If file exists, it's a code bug not data issue.
2. **Test with failing file paths**: Extract the 46 failing file paths, run isolated single-threaded test. If test passes, multiprocessing is culprit.
3. **Pathlib absolute paths**: Ensure all Path objects converted to absolute paths before passing to workers. Relative paths can resolve differently in worker processes.
4. **Retry logic with backoff**: Wrap file operations in retry decorator (max 3 attempts, 100ms backoff). Handles transient network/filesystem timing issues.
5. **Unicode path validation**: Test code with filenames containing non-ASCII characters. On Windows, use `open(path, encoding='utf-8')` explicitly.
6. **Logging with full context**: Log absolute file path, worker process ID, current working directory. Makes race conditions visible.

**Warning signs:**
- Same file fails in one run, succeeds in another run (non-deterministic = race condition)
- All failures in specific character set range (e.g., filenames with accented characters) = encoding issue
- Failures clustered at start/end of batch = process startup/shutdown timing
- Error message shows truncated/garbled filename = Unicode encoding problem

**Phase to address:**
Phase 3 (Failed file investigation) — reproduce failures in isolated environment, test Unicode paths, verify multiprocessing safety.

---

### Pitfall 4: Lookup CSV Corruption from Unescaped Special Characters

**What goes wrong:**
ID lookup CSV exported to Excel shows: (a) rows split across multiple Excel rows, (b) commas in filename break column alignment, (c) Unicode characters render as gibberish (é→ƒÂ©), (d) Excel interprets 5-digit IDs as dates (10001→Oct 1, 2001). CSV is technically valid but unusable, defeating "Excel-friendly lookup" goal.

**Why it happens:**
- **Delimiter collision**: If filename contains comma ("Report, Final.pdf") and CSV uses comma delimiter, Excel splits one row into multiple columns.
- **Newline in data**: If filename contains newline (unlikely but possible from malformed filesystem metadata), CSV row breaks into multiple Excel rows.
- **Encoding mismatch**: pandas `to_csv()` defaults to UTF-8, but Excel on Windows expects UTF-8-BOM or Windows-1252. Opening UTF-8 file in Excel shows mojibake for non-ASCII characters.
- **Excel auto-formatting**: Excel aggressively reformats data—leading zeros removed (01234→1234), 5-digit numbers interpreted as dates, long IDs shown in scientific notation (12345678901→1.23E+10).
- **Quoting inconsistency**: CSV standard requires quoting fields with special characters, but inconsistent quoting confuses Excel.

Research shows: "CSV files have no built-in mechanism to declare their character encoding, making CSV the format most prone to encoding corruption" ([How to Fix CSV Encoding Problems, CSV Viewer](https://csv-viewer-online.com/blog/fix-csv-encoding-problems)). "Windows applications often assume Windows-1252, macOS applications may assume UTF-8, causing this guessing game to corrupt accented characters, currency symbols, and any text outside basic ASCII range" ([Solving CSV Encoding Problems, ConvertToCSV](https://converttocsv.com/blog/csv-encoding-issues/)).

Pandas pitfall: "It's possible to write out a CSV file using default settings that can't be read back in using default settings, which arises when there's a text column that doesn't get quotes around it but has a carriage return" ([pandas newline defaults issue](https://github.com/pandas-dev/pandas/issues/10018)).

**How to avoid:**
1. **Excel-optimized CSV export**:
   ```python
   df.to_csv(
       'lookup.csv',
       index=False,              # No mystery index column
       encoding='utf-8-sig',     # BOM signals UTF-8 to Excel
       quoting=csv.QUOTE_NONNUMERIC,  # Quote all non-numeric fields
       lineterminator='\n'       # Consistent line endings
   )
   ```
2. **Prefix IDs with quote**: Add leading quote to ID column (`="10001"`) to prevent Excel date conversion. Or export as text type.
3. **Validate filename safety**: Before export, check for: commas, newlines, quotes in filename column. Escape or sanitize.
4. **Test Excel roundtrip**: Export CSV → Open in Excel → Verify appearance → Re-save → Verify data integrity. Catches issues before user sees them.
5. **Provide multiple formats**: Export CSV (Excel-compatible) AND TSV (tab-delimited, safer) AND JSON (no ambiguity). User picks format that works.
6. **Document Excel import**: README with "Open Excel → Data tab → From Text/CSV → UTF-8 encoding" steps. Default double-click opens incorrectly.

**Warning signs:**
- Test CSV in Excel shows garbled characters (not caught in pandas validation)
- Column count mismatch in Excel (data in wrong columns)
- IDs display as dates or scientific notation in Excel
- User reports "CSV looks broken" despite passing programmatic validation

**Phase to address:**
Phase 2 (Lookup generation) — implement Excel-safe CSV export, test in actual Excel, document import steps.

---

### Pitfall 5: No-Match Page Investigation Confirms Broken OCR, Ignores User-Facing Impact

**What goes wrong:**
Investigation into 59 no-match pages identifies root causes ("blank pages", "severely degraded scans", "IDs outside OCR region") and documents findings. But fails to produce actionable output for user—which files have no-match pages? What should user do about them? Report is technically complete but operationally useless.

Worse variant: Investigation finds "OCR working as designed" and closes issue, leaving user with 59 unsearchable pages and no recourse.

**Why it happens:**
- **Developer vs. user perspective**: Developers focus on "why did OCR fail" (technical). User needs "which files are affected and what do I do" (operational).
- **Success criteria mismatch**: Investigation defined success as "identify root cause" not "enable user to handle no-match pages."
- **Report format**: Technical document (`.planning/reports/error_analysis.md`) not user-facing output (additional CSV column, separate "unextracted_pages.csv").
- **No follow-up mechanism**: Investigation identifies 20 degraded scans, but no plan to re-scan, manually transcribe, or flag in lookup file.

OCR error research shows: "For batch processing, the pipeline creates an audit trail: a CSV with page-level status, combined text output, and preprocessed images for manual inspection when results look wrong. Having these artifacts separately made it much easier to iterate on the OCR process and diagnose problems" ([Common Errors in DeepSeek-OCR, Skywork AI](https://skywork.ai/blog/llm/common-errors-in-deepseek-ocr-and-how-to-fix-them/)).

**How to avoid:**
1. **User-facing output artifact**: Export `no_match_pages.csv` with columns: filename, page, reason (blank/degraded/ocr_failed), recommendation (rescan/manual_review/n/a).
2. **Integrate into lookup file**: Add "status" column to main lookup CSV: "extracted" (normal), "no_match" (OCR failed), "low_confidence" (flagged). User sees gaps in single file.
3. **Actionable recommendations**: For each no-match category, provide next step: (a) Blank pages → "Safe to ignore", (b) Degraded scans → "Files attached, recommend rescan", (c) OCR failed → "Manual review needed."
4. **Sample pages for review**: Attach preprocessed images for no-match subset (5-10 examples per category) so user can validate diagnosis.
5. **Quantify impact**: Report both count (59 pages) AND percentage of corpus (0.13%) so user can prioritize.

**Warning signs:**
- Error report reads like academic paper (root cause analysis) not operational guide (what to do next)
- No deliverable for user consumption (only internal documentation)
- User asks "which files have no IDs?" and answer is "check the report" not "here's the CSV"
- Investigation identifies problems but no mitigation strategy

**Phase to address:**
Phase 4 (No-match investigation) — produce user-facing deliverable alongside technical report. Phase 2 (Lookup generation) — integrate no-match status into main lookup file.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| **Filter by confidence threshold only** | Simple one-line filter | Loses real IDs from degraded but valid scans; threshold miscalibration causes silent data loss | Never for final output; acceptable for flagging candidates for review |
| **Hardcode 5-digit pattern without context** | Fast regex match | Fails on edge cases (IDs in margins, page numbers misinterpreted as IDs); no protection against false positives | Acceptable as first pass if followed by multi-signal validation |
| **Group by page, keep first ID** | Trivial dedup logic | Loses legitimate multi-ID pages; creates unsearchable IDs | Never; multi-ID is known production pattern (11.2% of pages) |
| **Re-run failures without investigating** | Clears error count quickly | Hides systemic issues (Unicode bugs, race conditions); errors resurface randomly | Acceptable as immediate mitigation if investigation runs in parallel |
| **Export CSV with default pandas settings** | One-line export | Breaks in Excel (encoding, date conversion, column misalignment); user can't consume output | Never for user-facing files; acceptable for internal checkpoints |
| **Assume sequential IDs are noise** | Filters obvious duplicates (10001, 10001, 10001) | Removes legitimate sequential specimens in same file; creates gaps in ID range | Acceptable if threshold is conservative (flag >3 same ID on one page) and reviewed manually |

---

## Integration Gotchas

Common mistakes when connecting to external tools.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Excel CSV import** | Export UTF-8 CSV, double-click in Windows | Excel defaults to ANSI, shows mojibake; numeric IDs become dates | Export `utf-8-sig` (UTF-8 with BOM); document "Data → From Text/CSV" import steps; prefix IDs with `=` to force text |
| **pandas to_csv()** | Use default settings for user-facing file | Defaults work for pandas roundtrip but break Excel (encoding, quoting, index column) | Set `encoding='utf-8-sig'`, `index=False`, `quoting=csv.QUOTE_NONNUMERIC`, `lineterminator='\n'` |
| **Path objects in multiprocessing** | Pass relative Path to worker | Worker's cwd differs; Path resolves incorrectly; FileNotFoundError on Windows spawn | Convert to absolute path: `Path(path).resolve()` before passing to worker |
| **OCR confidence scores** | Treat 0.8 confidence as "80% accurate" | Confidence poorly calibrated; 0.9 may be 70% accurate in practice | Use confidence as relative signal (compare within batch) not absolute threshold; validate on sample |
| **Fuzzy deduplication** | Use Levenshtein distance <2 for OCR error tolerance | Merges distinct IDs (10001≈10002); causes data loss | Exact match only for dedup; use fuzzy matching for typo correction with manual review |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **In-memory ID validation** | Load all 52K IDs into set for duplicate check | Memory scales linearly with ID count; 100K+ IDs = multi-GB RAM | Use database or streaming validation for >100K IDs; current scale (52K) acceptable for in-memory |
| **File-by-file error retry** | Re-process each failed file individually | 46 retries = 46 worker spawns = overhead dominates; slow for large failure sets | Batch retries into single run; parallelize retry processing |
| **Full CSV read for incremental updates** | Read 52K-row CSV, modify, rewrite | File I/O dominates for small updates; risk of corruption on partial write | For incremental updates, append to separate file then merge; or use SQLite for large datasets |
| **Synchronous validation API calls** | Validate each ID against external service | Network latency dominates (100ms/ID × 52K = 1.4 hours); sequential = slow | Use async batch validation (100 IDs/request); or cache validation results; for this project, no external validation needed |

Performance research shows: "Large batch runs sometimes hit memory limits or produce random misses. One approach is to limit batch size (say 50 pages per job), log failures, and re-queue only problematic ones with heavier settings" ([How to Debug OCR in C#, IronOCR](https://ironsoftware.com/csharp/ocr/how-to/debugging/)).

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **ID lookup CSV exported:** Verify opens correctly in Excel (encoding, no date conversion, columns aligned, Unicode characters render)
- [ ] **Multi-ID dedup implemented:** Verify preserves legitimate multi-ID pages (test on known examples from 5,141-page set)
- [ ] **Failed files investigated:** Verify root cause identified AND users know which files failed AND mitigation plan exists
- [ ] **No-match pages handled:** Verify user has actionable output (CSV with affected files, recommendations) not just internal report
- [ ] **Filters validated:** Verify filter decisions tested on random sample (>100 IDs) with manual review of false negatives
- [ ] **Error report published:** Verify user-facing format (what to do) not just technical analysis (why it happened)
- [ ] **Edge cases tested:** Verify CSV export tested with: filenames containing commas/quotes/newlines, Unicode filenames (é, ñ, 中), maximum-length paths, IDs with leading zeros
- [ ] **Sequential ID handling:** Verify consecutive IDs within file preserved (not flagged as duplicates), gaps documented
- [ ] **Confidence threshold calibrated:** Verify threshold tested on validation sample (not just theoretical), false negative rate measured
- [ ] **Lookup file usability:** Verify actual user workflow tested (user searches for ID, finds file/page, locates PDF, views correct page) end-to-end

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Overzealous filtering deleted real IDs** | LOW (if raw data preserved) | Restore from raw OCR results; re-apply less aggressive filter; publish correction notice with updated lookup file |
| **Dedup false positives lost multi-ID pages** | LOW (if raw data preserved) | Restore from raw OCR results; re-run dedup with exact-match-only logic; diff old/new lookup to identify lost IDs |
| **Lookup CSV corrupted in Excel** | LOW | Re-export with utf-8-sig encoding; document Excel import steps; provide alternate format (TSV/JSON) |
| **FileNotFoundError from multiprocessing bug** | MEDIUM | Fix Path serialization (absolute paths); add retry logic; re-run failed files; update error handling |
| **No-match pages investigation incomplete** | MEDIUM | Re-open investigation with user-facing deliverable goal; export no_match_pages.csv; integrate into lookup file |
| **Threshold miscalibration caused data loss** | HIGH (if raw data not preserved) | If raw data lost: re-run OCR on original PDFs (expensive); if preserved: restore and re-filter (cheap) |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| **Overzealous noise filtering** | Phase 1 (Multi-ID investigation) | Sample validation on 200 IDs before full run; false negative rate <1%; raw data preserved |
| **Deduplication false positives** | Phase 1 (Multi-ID investigation) | Test dedup on known multi-ID pages; verify sequential IDs preserved; exact-match-only logic |
| **FileNotFoundError misdiagnosis** | Phase 3 (Failed file investigation) | Reproduce failures in isolation; test Unicode paths; verify absolute paths in multiprocessing |
| **Lookup CSV corruption** | Phase 2 (Lookup generation) | Excel roundtrip test passes; UTF-8-BOM encoding; quoting configured; import steps documented |
| **No-match investigation without user impact** | Phase 4 (No-match investigation) | no_match_pages.csv delivered; recommendations actionable; sample images attached; status column in lookup |

---

## Sources

### OCR Post-Processing and Filtering
- [OCR POST-PROCESSING ERROR CORRECTION (arXiv)](https://arxiv.org/pdf/1204.0191) — False positive rate concerns in OCR correction
- [Unverified: What Practitioners Post About OCR, Agents, and Tables](https://idp-software.com/news/idp-accuracy-reckoning-2026/) — Confidence threshold production challenges
- [OCR best practices in 2026: How to Build a Production-Ready OCR Pipeline](https://preocr.io/blog/ocr-best-practices-in-2026-how-to-build-a-production-ready-ocr-pipeline) — DPI, preprocessing, validation layers
- [The Complete Guide to OCR Data Labeling: 2026 Update](https://kili-technology.com/blog/ocr-annotation) — Edge case coverage for production failures

### Deduplication and Multi-Match Handling
- [Noise-Robust De-Duplication at Scale (arXiv)](https://arxiv.org/pdf/2210.04261) — OCR extraction errors in deduplication
- [Fuzzy Matching 101: The Complete Guide to Accurate Data Matching [2026]](https://dataladder.com/fuzzy-matching-101/) — Threshold tuning to prevent false positives
- [Choosing Your OCR Tool: The 6 Essentials for 2026](https://www.koncile.ai/en/ressources/choosing-an-ocr-in-2025-the-checklist) — Multi-page document handling
- [Duplicate Page Detection - Simple Wiki](https://www.simpleindex.com/wiki/index.php?title=Duplicate_Page_Detection) — Fuzzy matching for OCR variations

### Error Investigation and Debugging
- [How to Debug OCR in C# — Logging & Error Handling | IronOCR](https://ironsoftware.com/csharp/ocr/how-to/debugging/) — Batch error handling patterns
- [Common Errors in DeepSeek-OCR and How to Fix Them - Skywork AI](https://skywork.ai/blog/llm/common-errors-in-deepseek-ocr-and-how-to-fix-them/) — Audit trail for batch processing
- [8 Common OCR Errors and How to Fix Them | Gennai Blog](https://www.gennai.io/blog/common-ocr-errors-fix-them) — Image quality and resolution checks
- [Fix Poor Retrieval in On-Prem OCR RAG Pipelines](https://www.technetexperts.com/fix-on-prem-ocr-rag-pipeline/) — Memory limits and batch size tuning

### Confidence Thresholds and Calibration
- [How to use confidence scores in machine learning models | Towards Data Science](https://towardsdatascience.com/how-to-use-confidence-scores-in-machine-learning-models-abe9773306fa/) — Threshold optimization tradeoffs
- [How Confident Are You in Your OCR Confidence Scores | Parascript](https://www.parascript.com/blog/your-ocr-confidence-scores/) — Calibration issues in OCR systems
- [Understanding confidence scores in Machine Learning: Practical guide](https://www.mindee.com/blog/how-use-confidence-scores-ml-models) — False negative impact of threshold increases

### CSV Export and Excel Compatibility
- [How to Fix CSV Encoding Problems: Complete Guide [2026]](https://csv-viewer-online.com/blog/fix-csv-encoding-problems) — CSV encoding corruption issues
- [Solving CSV Encoding Problems: BOM UTF-8 and Excel](https://converttocsv.com/blog/csv-encoding-issues/) — UTF-8-BOM for Excel compatibility
- [Why Excel's built-in CSV functionality corrupts your data | POWER CSV](https://powercsv.com/blog/why-excel-corrupts-your-csv-data/) — Excel auto-formatting pitfalls
- [pandas newline defaults issue #10018](https://github.com/pandas-dev/pandas/issues/10018) — Newline handling in CSV roundtrips

### Multiprocessing and FileNotFoundError
- [Fix FileNotFoundError With Multiprocessing in Python - Super Fast Python](https://superfastpython.com/filenotfounderror-multiprocessing-python/) — Race condition in process coordination
- [multiprocessing.Process generates FileNotFoundError · Issue #94765 · python/cpython](https://github.com/python/cpython/issues/94765) — Windows-specific Path serialization issues
- [pathlib.Path.mkdir() raises FileExistsError due to TOCTOU race condition · Issue #142916](https://github.com/python/cpython/issues/142916) — Multiprocessing filesystem race conditions

---
*Pitfalls research for: Precede OCR v1.3 Results Cleanup & ID Lookup*
*Researched: 2026-06-09*
