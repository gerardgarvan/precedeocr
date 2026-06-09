# Technology Stack — v1.3 Results Cleanup & ID Lookup

**Project:** Precede OCR — PDF ID Scanner & Mapper
**Milestone:** v1.3 Results Cleanup & ID Lookup
**Last Updated:** 2026-06-09
**Target Platform:** Windows 10
**Focus:** Post-processing pipeline results, deduplication, error investigation, quality reporting

---

## Executive Summary

**Recommendation: NO NEW DEPENDENCIES NEEDED.**

The existing v1.2 stack (pandas 3.0.3 + Python stdlib) is fully sufficient for all v1.3 requirements:
- ID lookup generation: pandas `sort_values()`, `groupby()`, basic CSV I/O
- Deduplication/noise filtering: pandas `duplicated()`, `drop_duplicates()`, custom logic
- Error investigation: pandas filtering, `value_counts()`, `groupby()` aggregation
- Quality reporting: Python stdlib f-strings, markdown templates (existing pattern from v1.1)

**Optional libraries evaluated and REJECTED** for this milestone:
- **ydata-profiling**: Overkill for targeted error analysis (generates full EDA reports, 52K rows manageable without)
- **openpyxl/xlsxwriter**: Not needed for "Excel-friendly" CSV (Excel reads CSV natively, no styling required)
- **pandera**: Data validation library not needed for post-processing analysis (no schema enforcement needed)

---

## v1.3 Requirements Mapping

| Requirement | Technique | Library | Already Available? |
|-------------|-----------|---------|-------------------|
| **Generate ID lookup CSV sorted by ID** | `df.sort_values('id')`, `df.to_csv()` | pandas 3.0.3 | ✓ YES (v1.0) |
| **Add Folder column to lookup** | `Path(filename).parent`, `df['folder'] = ...` | pathlib (stdlib) + pandas | ✓ YES (v1.0) |
| **Investigate failed files (49 FileNotFoundError)** | Filter campaign_state.json failures, filesystem checks | json (stdlib), pathlib | ✓ YES (v1.0) |
| **Investigate no-match pages (59 pages)** | `df[df['notes'] == 'no_match']`, manual inspection | pandas | ✓ YES (v1.0) |
| **Investigate multi-ID pages (5,141 pages)** | `df.groupby(['filename', 'page']).size()`, deduplication logic | pandas | ✓ YES (v1.0) |
| **Deduplicate false positives** | `df.duplicated(subset=['filename','page','id'])`, custom validation | pandas | ✓ YES (v1.0) |
| **Error/quality report** | f-string templates, markdown output (same as campaign_report.md v1.1) | stdlib | ✓ YES (v1.1) |
| **Frequency analysis (rotation, errors)** | `df['rotation_detected'].value_counts()`, Counter | pandas + collections.Counter | ✓ YES (v1.0) |
| **Excel-friendly output** | CSV with UTF-8 BOM: `df.to_csv(encoding='utf-8-sig')` | pandas | ✓ YES (v1.0) |

**Verdict:** Existing stack covers 100% of requirements.

---

## Existing Stack (Validated, No Changes)

### Data Manipulation & Analysis

| Technology | Version | Purpose | Why Sufficient |
|------------|---------|---------|----------------|
| **pandas** | 3.0.3 | Post-processing scan.csv (52K rows), deduplication, aggregation, sorting, CSV I/O | Handles millions of rows efficiently. `drop_duplicates()` uses hash-based O(N) detection. `groupby()` optimized for aggregation. `to_csv()` produces Excel-compatible output. **Confidence: HIGH** |
| **pathlib** | stdlib | Extract folder from filename paths | `Path(filename).parent` extracts directory. Already used in v1.0 for file discovery. **Confidence: HIGH** |
| **collections.Counter** | stdlib | Error frequency analysis, rotation distribution | Already used in v1.1 for campaign statistics. Lightweight, fast. **Confidence: HIGH** |
| **collections.defaultdict** | stdlib | Nested aggregation (e.g., per-folder stats) | Already used in v1.1 for folder_stats. **Confidence: HIGH** |

### Output & Reporting

| Technology | Version | Purpose | Why Sufficient |
|------------|---------|---------|----------------|
| **f-string templates** | stdlib (Python 3.6+) | Quality report generation (markdown, text) | v1.1 campaign_report.md already uses this pattern. Clean, no dependencies. **Confidence: HIGH** |
| **json** | stdlib | Load campaign_state.json for failure investigation | Already used in v1.0/v1.1 for checkpoint/campaign state. **Confidence: HIGH** |

---

## What's Already in the Stack

**From v1.0:**
- pandas 3.0.3 — CSV/JSON I/O, DataFrame manipulation
- pathlib (stdlib) — Path operations
- json (stdlib) — JSON I/O
- collections (stdlib) — Counter, defaultdict

**From v1.1:**
- f-string markdown templates — campaign_report.md generation pattern

**From v1.2:**
- PyMuPDF 1.27.2.3 — Not needed for v1.3 (no PDF processing)
- pytesseract 0.3.13 — Not needed for v1.3 (no OCR processing)

**v1.3 reuses:** pandas + stdlib only. No new libraries required.

---

## pandas Capabilities for v1.3 (2026 Best Practices)

### 1. Duplicate Detection & Deduplication

**Use Case:** Identify multi-ID pages (5,141 pages where multiple IDs detected), distinguish real vs OCR noise.

**pandas Methods (v3.0.3):**

```python
# Detect duplicate rows (same filename, page, ID)
df['is_duplicate'] = df.duplicated(subset=['filename', 'page', 'id'], keep=False)

# Find pages with multiple IDs
multi_id_pages = df.groupby(['filename', 'page']).size()
multi_id_pages = multi_id_pages[multi_id_pages > 1]

# Remove exact duplicates
df_clean = df.drop_duplicates(subset=['filename', 'page', 'id'], keep='first')

# Inspect before removing
duplicates_df = df[df.duplicated(subset=['filename', 'page', 'id'], keep=False)]
```

**Performance:** O(N) hash-based detection. For 52K rows: <100ms. **Confidence: HIGH** (pandas 3.0.3 official docs, 2026 best practices articles).

**Best Practices (2026):**
- **Inspect before removal:** Use `duplicated(keep=False)` to see all duplicates (not just subsequent ones) before calling `drop_duplicates()`
- **Avoid inplace=True:** Returns new DataFrame for method chaining, doesn't actually save memory
- **Normalize first:** For string columns, normalize case/whitespace before dedup if semantic matching needed
- **Document rationale:** Comment why duplicates removed (reproducibility)

**Sources:**
- [pandas.DataFrame.drop_duplicates — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html)
- [Mastering drop_duplicates() in Pandas: Comprehensive Guide](https://www.sparkcodehub.com/pandas/data-cleaning/remove-duplicates)
- [Pandas Drop Duplicates: How to Remove Duplicate Rows in Python — Kanaries](https://docs.kanaries.net/topics/Pandas/pandas-drop-duplicates)

### 2. Sorting & ID Lookup Generation

**Use Case:** Generate ID lookup CSV sorted by ID (columns: ID, Filename, Page, Folder).

**pandas Methods (v3.0.3):**

```python
# Sort by ID (ascending)
df_sorted = df.sort_values('id')

# Add Folder column
df_sorted['folder'] = df_sorted['filename'].apply(lambda x: str(Path(x).parent))

# Select and reorder columns
lookup = df_sorted[['id', 'filename', 'page', 'folder']]

# Export to Excel-friendly CSV (UTF-8 with BOM for Excel compatibility)
lookup.to_csv('id_lookup.csv', index=False, encoding='utf-8-sig')
```

**Performance:** For 52K rows: sorting O(N log N) ≈ 10ms, `to_csv()` ≈ 100ms. Total <150ms. **Confidence: HIGH** (pandas 3.0.3 official docs).

**Excel Compatibility:**
- **UTF-8 with BOM (`encoding='utf-8-sig'`)**: Excel on Windows recognizes UTF-8 automatically when BOM present
- **No special libraries needed**: Excel reads CSV natively, no openpyxl/xlsxwriter required unless advanced formatting needed (conditional coloring, formulas, charts)
- **Alternative if BOM issues**: Use `encoding='cp1252'` (Windows Latin-1), but UTF-8-sig preferred for international characters

**Sources:**
- [pandas.DataFrame.sort_values — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html)
- [pandas.DataFrame.to_csv — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html)

### 3. Filtering & Aggregation for Error Analysis

**Use Case:** Investigate no-match pages, failed files, rotation distribution, multi-ID frequency.

**pandas Methods (v3.0.3):**

```python
# Filter no-match pages
no_match_pages = df[df['notes'] == 'no_match']

# Rotation distribution
rotation_counts = df['rotation_detected'].value_counts()

# Pages with multiple IDs
multi_id_counts = df.groupby(['filename', 'page']).size()
multi_id_summary = multi_id_counts.value_counts().sort_index()

# Files with most no-matches
no_match_by_file = no_match_pages.groupby('filename').size().sort_values(ascending=False)
```

**Performance:** Filtering O(N), `groupby()` O(N), `value_counts()` O(N). For 52K rows: each <50ms. **Confidence: HIGH** (pandas 3.0.3 official docs).

**Best Practices (2026):**
- **Boolean indexing over query():** `df[df['col'] == value]` faster than `df.query()` for simple filters
- **Avoid unnecessary sorting:** `groupby(sort=False)` improves performance when group order doesn't matter
- **Use categoricals for repeated strings:** Convert folder/filename columns to categorical dtype if many repeated values (reduces memory, speeds up groupby)

**Sources:**
- [pandas.DataFrame.groupby — pandas 3.0.3 documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html)
- [Pandas GroupBy at Speed: Pitfalls and Power Moves | by Codastra | Medium](https://medium.com/@2nick2patel2/pandas-groupby-at-speed-pitfalls-and-power-moves-8b27ca7ccc5a)

### 4. Data Quality Checks (Stdlib, No External Libraries)

**Use Case:** Validate scan.csv integrity, detect anomalies, report statistics.

**Techniques (stdlib + pandas):**

```python
# Check for missing values
missing_summary = df.isnull().sum()

# Detect duplicate rows (exact duplicates)
exact_duplicates = df.duplicated().sum()

# Validate ID format (5 digits)
invalid_ids = df[~df['id'].astype(str).str.match(r'^\d{5}$')]

# Outlier detection (e.g., unexpected rotation values)
valid_rotations = [0.0, 90.0, 180.0, 270.0]
invalid_rotations = df[~df['rotation_detected'].isin(valid_rotations)]

# Summary statistics
id_stats = df['id'].describe()
```

**Why Not Use External Libraries:**
- **pandera:** Data validation library with schema enforcement. **Overkill** for one-time post-processing analysis. Useful for ongoing data pipelines with strict schemas. Not needed here.
- **ydata-profiling (pandas-profiling):** Generates full EDA HTML reports with univariate/multivariate/correlation analysis. **Overkill** for targeted error investigation. 52K rows manageable with manual pandas analysis. Report generation overhead (minutes for large datasets) not justified.
- **pandas_dq:** Auto-generates data quality reports. **Not needed** — v1.3 requires custom error analysis (no-match pages, multi-ID investigation), not generic profiling.

**Recommendation:** Stick with pandas + stdlib for v1.3. If future milestones need automated profiling for 30K PDFs (e.g., folder-level quality dashboards), revisit ydata-profiling. **Confidence: HIGH**

**Sources:**
- [7 Essential Data Quality Checks with Pandas - KDnuggets](https://www.kdnuggets.com/7-essential-data-quality-checks-with-pandas)
- [Comprehensive Data Quality Checks with Python Pandas | by Gen. Devin DL. | Medium](https://medium.com/@tubelwj/comprehensive-data-quality-checks-with-python-pandas-aafc080e2a76)

---

## Libraries Evaluated and REJECTED for v1.3

| Library | Version | Evaluated For | Why Rejected |
|---------|---------|---------------|--------------|
| **ydata-profiling** | 7.0.0+ (April 2026) | Automated data quality reports, EDA | **Overkill.** Generates full HTML reports with correlations, distributions, missing data analysis. 52K rows manageable with targeted pandas analysis. Report generation overhead (minutes for large datasets) not justified for one-time post-processing. Useful for ongoing pipelines or massive datasets, not this use case. **Confidence: MEDIUM** |
| **openpyxl** | Latest | Excel styling (conditional formatting, charts) | **Not needed.** CSV output is Excel-friendly with UTF-8 BOM (`encoding='utf-8-sig'`). Excel reads CSV natively. No advanced styling required (no conditional formatting, charts, formulas requested). If future milestone needs styled Excel reports, revisit. **Confidence: HIGH** |
| **xlsxwriter** | Latest | Excel export with formatting | **Not needed.** Same rationale as openpyxl. CSV sufficient for v1.3. **Confidence: HIGH** |
| **pandera** | Latest | Schema validation, data quality checks | **Overkill.** Enforces schemas on DataFrames (type checking, constraints). Useful for production pipelines with strict validation. v1.3 is one-time post-processing analysis, not ongoing validation. Custom pandas checks sufficient. **Confidence: MEDIUM** |
| **pandas_dq** | Latest | Auto-generated data quality reports | **Not needed.** Generic profiling tool. v1.3 requires custom error analysis (no-match investigation, multi-ID filtering). Manual pandas analysis more targeted. **Confidence: MEDIUM** |

**All evaluations based on 2026 documentation and best practices articles.**

**Sources:**
- [ydata-profiling · PyPI](https://pypi.org/project/ydata-profiling/) — Latest version April 22, 2026
- [Pandas Profiling for Exploratory Data Analysis in Python 2026](https://johal.in/pandas-profiling-for-exploratory-data-analysis-in-python-2026/)
- [Data Validation in Python with Pandera: A Practical Introduction](https://www.statology.org/data-validation-in-python-with-pandera-a-practical-introduction/)
- [pandas.io.formats.style.Styler.to_excel — pandas 3.0.2 documentation](https://pandas.pydata.org/docs/reference/api/pandas.io.formats.style.Styler.to_excel.html)
- [Example: Pandas Excel output with column formatting — XlsxWriter](https://xlsxwriter.readthedocs.io/example_pandas_column_formats.html)

---

## Integration Notes

### Reusing Existing Patterns from v1.1

**campaign_report.md generation pattern:**

v1.1 already established f-string markdown template pattern for quality reporting:

```python
# v1.1 pattern (from campaign runner)
report = f"""# Campaign Report

## Summary
- Total files: {total_files}
- Success: {success_count}
- Failed: {failed_count}

## Problem Folders
{folder_table}
"""

with open('campaign_report.md', 'w', encoding='utf-8') as f:
    f.write(report)
```

**v1.3 reuses this pattern** for error/quality report:

```python
# v1.3 error/quality report
report = f"""# v1.3 Results Analysis

## Summary
- Total IDs extracted: {len(df)}
- No-match pages: {no_match_count}
- Multi-ID pages: {multi_id_count}
- Failed files: {failed_count}

## Findings
{findings_text}
"""
```

**No new libraries needed.** Markdown output readable in GitHub, VSCode, or convert to HTML/PDF with external tools if needed.

### Data Flow for v1.3

```
Input:
  - results.csv (52K rows, from v1.2 production run)
  - campaign_state.json (failure metadata from v1.1)

Processing (pandas + stdlib):
  1. Load results.csv → pandas DataFrame
  2. Filter no-match pages → investigate
  3. Detect multi-ID pages → deduplicate false positives
  4. Sort by ID, add Folder column → id_lookup.csv
  5. Aggregate error statistics → error_report.md
  6. Load campaign_state.json → investigate failed files (FileNotFoundError)

Output:
  - id_lookup.csv (sorted by ID, columns: ID, Filename, Page, Folder)
  - error_report.md (findings, statistics, recommendations)
  - Optional: cleaned_results.csv (after deduplication)
```

**All steps use existing libraries.** No new dependencies.

---

## Performance Considerations

### Dataset Scale

- **Current:** 52K rows (v1.2 production run)
- **pandas 3.0.3 performance:** Handles millions of rows efficiently on typical hardware
- **Operations on 52K rows:**
  - `read_csv()`: <200ms
  - `sort_values()`: <10ms (O(N log N))
  - `groupby()` + aggregation: <50ms (O(N))
  - `drop_duplicates()`: <100ms (O(N) hash-based)
  - `to_csv()`: <150ms

**Total processing time estimate:** <1 second for all v1.3 operations combined.

**Memory footprint:** ~5-10 MB for 52K rows with 5 columns (filename, page, id, rotation, notes).

**Conclusion:** pandas 3.0.3 is overkill for this scale, but already in stack. No performance concerns. **Confidence: HIGH**

### When to Consider Alternatives

**If future milestones scale to:**
- **500K+ rows:** Still pandas (tested to 10M+ rows)
- **10M+ rows:** Consider chunked processing (`pd.read_csv(chunksize=10000)`) or Dask for out-of-core processing
- **100M+ rows:** Consider PySpark, Polars (faster than pandas for large-scale operations)

**For v1.3:** pandas 3.0.3 sufficient. No changes needed.

**Sources:**
- [Streaming groupbys in pandas for big datasets • Max Halford](https://maxhalford.github.io/blog/pandas-streaming-groupby/)
- [Pandas GroupBy at Speed: Pitfalls and Power Moves | by Codastra | Medium](https://medium.com/@2nick2patel2/pandas-groupby-at-speed-pitfalls-and-power-moves-8b27ca7ccc5a)

---

## What NOT to Add for v1.3

| Library | Why Avoid for v1.3 | When to Reconsider |
|---------|---------------------|-------------------|
| **ydata-profiling** | Overkill for targeted error analysis. Generates full EDA reports (correlations, distributions). Overhead not justified for 52K rows. | If future milestone needs automated profiling dashboards for 30K PDFs (folder-level quality metrics), or if analyzing millions of rows. |
| **openpyxl / xlsxwriter** | CSV is Excel-friendly with UTF-8 BOM. No advanced styling needed (no conditional formatting, charts, formulas requested). | If future milestone requires styled Excel reports (highlighted errors, charts, formulas). |
| **pandera** | Schema validation overkill for one-time post-processing. Useful for production pipelines with strict validation. | If future milestone builds ongoing validation pipeline (e.g., validating new batch results against schema). |
| **pandas_dq** | Generic profiling not aligned with custom error investigation (no-match, multi-ID analysis). | If future milestone needs standardized quality checks across multiple datasets. |
| **PySpark / Dask** | 52K rows too small for distributed processing. Single-machine pandas sufficient. Adds complexity and dependencies. | If scaling to 10M+ rows or processing too large for RAM. |
| **Polars** | Faster than pandas for large datasets (Rust-based), but 52K rows insignificant. pandas already in stack. | If bottleneck emerges on large-scale aggregations (unlikely for this project). |

**Stick with pandas 3.0.3 + stdlib for v1.3.** Clean, simple, sufficient.

---

## Installation Summary

**v1.3 requires NO new installations.**

**Existing stack (from v1.0/v1.1/v1.2):**
```bash
# Already installed (requirements.txt)
pip install pandas==3.0.3
```

**Everything else is Python stdlib:**
- pathlib
- json
- collections (Counter, defaultdict)
- f-strings (Python 3.6+)

**Libraries NOT needed:**
```bash
# DO NOT INSTALL for v1.3 (not needed)
# pip install ydata-profiling
# pip install openpyxl
# pip install xlsxwriter
# pip install pandera
# pip install pandas_dq
```

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| pandas sufficiency | HIGH | Official pandas 3.0.3 docs (2026), performance tested to millions of rows, 52K rows trivial scale |
| Deduplication methods | HIGH | pandas `duplicated()` / `drop_duplicates()` documented, O(N) hash-based, established 2026 best practices |
| Sorting & groupby | HIGH | pandas core operations, well-documented, performance benchmarks available |
| Excel compatibility | HIGH | UTF-8 BOM (`encoding='utf-8-sig'`) standard for Excel CSV import, verified in pandas docs |
| No new libraries needed | HIGH | All v1.3 requirements map to existing pandas + stdlib capabilities |
| ydata-profiling rejection | MEDIUM | Library well-documented (April 2026 release), but "overkill" assessment based on feature comparison, not empirical testing for this use case |
| openpyxl rejection | HIGH | CSV sufficient per v1.3 requirements (no advanced Excel styling requested) |
| pandera rejection | MEDIUM | Library well-documented, but "overkill for one-time analysis" based on use case fit, not empirical testing |

**Overall Confidence: HIGH** — Recommendation to use existing stack without additions is well-supported.

---

## Sources

### pandas 3.0.3 Official Documentation (2026)
- [pandas 3.0.3 documentation](https://pandas.pydata.org/docs/)
- [pandas.DataFrame.drop_duplicates](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.drop_duplicates.html)
- [pandas.DataFrame.sort_values](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.sort_values.html)
- [pandas.DataFrame.groupby](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html)
- [pandas.DataFrame.to_csv](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html)
- [pandas.io.formats.style.Styler.to_excel](https://pandas.pydata.org/docs/reference/api/pandas.io.formats.style.Styler.to_excel.html)

### Deduplication Best Practices (2026)
- [Mastering drop_duplicates() in Pandas: Comprehensive Guide](https://www.sparkcodehub.com/pandas/data-cleaning/remove-duplicates)
- [Pandas Drop Duplicates: How to Remove Duplicate Rows in Python — Kanaries](https://docs.kanaries.net/topics/Pandas/pandas-drop-duplicates)
- [Mastering Deduplication: Smarter Data Cleaning for Massive Datasets | by Sagar Iyer | Medium](https://medium.com/@sagarsiyer/mastering-deduplication-smarter-data-cleaning-for-massive-datasets-93708d22c16c)
- [pandas remove duplicate columns (2026): Master Data Cleaning](https://codegive.com/blog/pandas_remove_duplicate_columns.php)

### Data Quality & Error Analysis (2026)
- [7 Essential Data Quality Checks with Pandas - KDnuggets](https://www.kdnuggets.com/7-essential-data-quality-checks-with-pandas)
- [Comprehensive Data Quality Checks with Python Pandas | by Gen. Devin DL. | Medium](https://medium.com/@tubelwj/comprehensive-data-quality-checks-with-python-pandas-aafc080e2a76)
- [Using Pandas for quality error reduction in data repositories | datos.gob.es](https://datos.gob.es/en/blog/using-pandas-quality-error-reduction-data-repositories)
- [4 Basic Data Quality Checks You Can Perform with Python and Pandas | by Balu Rama Chandra | Dev Genius](https://blog.devgenius.io/5-essential-data-quality-checks-you-can-perform-with-python-18fc87655950)

### Sorting & Aggregation Performance (2026)
- [Pandas GroupBy at Speed: Pitfalls and Power Moves | by Codastra | Medium](https://medium.com/@2nick2patel2/pandas-groupby-at-speed-pitfalls-and-power-moves-8b27ca7ccc5a)
- [Streaming groupbys in pandas for big datasets • Max Halford](https://maxhalford.github.io/blog/pandas-streaming-groupby/)
- [Mastering Pandas GroupBy and Sort-Pandas Dataframe](https://pandasdataframe.com/pandas-groupby-sort.html)
- [Pandas: Sort within groups | by Akshay Chavan | Medium](https://arccoder.medium.com/pandas-sort-within-groups-e1f3b6a10a3f)

### Excel Export & Formatting (2026)
- [Pandas DataFrame to Styled Excel with Python openpyxl | PyTutorial](https://pytutorial.com/pandas-dataframe-to-styled-excel-with-python-openpyxl/)
- [Example: Pandas Excel output with column formatting — XlsxWriter](https://xlsxwriter.readthedocs.io/example_pandas_column_formats.html)
- [GitHub - WZBSocialScienceCenter/pandas-excel-styler](https://github.com/WZBSocialScienceCenter/pandas-excel-styler)

### Data Profiling Libraries (Evaluated, Rejected)
- [ydata-profiling · PyPI](https://pypi.org/project/ydata-profiling/) — Latest version April 22, 2026
- [Pandas Profiling for Exploratory Data Analysis in Python 2026](https://johal.in/pandas-profiling-for-exploratory-data-analysis-in-python-2026/)
- [Automate Python Data Analysis With YData Profiling – Real Python](https://realpython.com/ydata-profiling-eda/)
- [Pandas Profiling (ydata-profiling) in Python: A Guide for Beginners | DataCamp](https://www.datacamp.com/tutorial/pandas-profiling-ydata-profiling-in-python-guide)
- [GitHub - Data-Centric-AI-Community/ydata-profiling](https://github.com/ydataai/ydata-profiling)
- [Data Validation in Python with Pandera: A Practical Introduction](https://www.statology.org/data-validation-in-python-with-pandera-a-practical-introduction/)
- [GitHub - AutoViML/pandas_dq](https://github.com/AutoViML/pandas_dq)

---

**Stack complete for v1.3.** NO new dependencies needed. All requirements covered by pandas 3.0.3 + Python stdlib. Recommendation is prescriptive and actionable for roadmap creation.
