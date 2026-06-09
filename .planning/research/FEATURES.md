# Feature Research

**Domain:** OCR Result Post-Processing and ID Lookup Generation
**Researched:** 2026-06-09
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **ID Lookup CSV (sorted by ID)** | Primary deliverable — enables quick "which file has ID 12345?" queries in Excel | LOW | Standard pandas sort_values() + to_csv(). Columns: ID, Filename, Page, Folder. Already built in v1.2 (csv output exists), just needs re-sorting. |
| **Failed File Investigation** | Production run has 49 failures (46 FileNotFoundError, 3 EmptyFileError) — must understand why | MEDIUM | Categorize errors by type, investigate root causes (missing files? path issues?), document findings. Standard batch processing error categorization. |
| **No-Match Page Investigation** | 59 pages returned no ID — must determine if real blanks or OCR failures | MEDIUM | Re-process with debug mode, visual inspection of sample pages, categorize reasons (truly blank, degraded scan, ID outside expected regions). |
| **Multi-ID Deduplication** | 5,141 pages with multiple IDs detected — need to separate real multi-page documents from OCR noise | HIGH | Core challenge: distinguish true duplicates (same form scanned twice) from OCR artifacts (one ID read at multiple rotations). Requires bounding box analysis or confidence filtering. |
| **Error/Quality Report** | Document findings and remaining issues for production run | LOW | Markdown report with error categories, counts, root causes, recommendations. Standard data quality audit structure: executive summary, error breakdown, root cause analysis, recommendations. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Confidence-Based Duplicate Filtering** | Use Tesseract confidence scores to filter low-quality OCR artifacts from real IDs | MEDIUM | pytesseract.image_to_data returns confidence per word. Industry standard: accept >90%, review 70-90%, reject <70%. Eliminates OCR noise without manual review. |
| **Bounding Box Overlap Detection** | Detect same ID read multiple times at different rotations via spatial overlap (IoU) | HIGH | Non-Maximum Suppression (NMS) with Intersection over Union (IoU). If two 5-digit IDs overlap >50%, likely same ID at different rotations. More reliable than confidence alone. |
| **Statistical Outlier Detection** | Flag anomalous results using IQR or Modified Z-Score (e.g., pages with 10+ IDs) | LOW | Modified Z-Score more robust than standard Z-score. IQR method: flag values >Q3 + 1.5×IQR. Surfaces edge cases for manual review. |
| **Automated Re-Processing Pipeline** | Re-run failed files with diagnostic logging to capture detailed error context | MEDIUM | Wrap existing pipeline with enhanced error capture (full traceback, file metadata, OCR intermediate results). Enables root cause analysis without manual re-runs. |
| **Multi-ID Categorization Report** | Classify multi-ID pages into buckets: likely OCR noise, likely real duplicates, uncertain/review | MEDIUM | Combine confidence + bounding box + statistical outlier signals. Reduces 5,141 pages to manageable review list (~100-200 uncertain cases). |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Interactive GUI for Manual Review** | "Let's visually review all 5,141 multi-ID pages" | 5,141 pages × 30 seconds/page = 43 hours of manual labor. Doesn't scale, error-prone, boring. | Automated filtering via confidence + bounding box analysis. Flag only uncertain cases (~100-200) for manual review. |
| **Perfect Deduplication (Zero False Positives)** | "Remove ALL OCR noise, keep ALL real IDs" | Impossible without ground truth. Precision vs recall tradeoff. Conservative filtering (keep borderline cases) risks keeping noise; aggressive filtering risks dropping real IDs. | Provide confidence levels (high/medium/low certainty) for each ID. Let user set threshold based on use case (recall-focused: keep borderline; precision-focused: drop borderline). |
| **Re-OCR Everything at Higher DPI** | "Maybe DPI 300 will fix multi-ID noise" | v1.2 benchmarked DPI 200 vs 300: DPI 200 found MORE IDs (211 vs 186 on 100-PDF sample) and was 43% faster. Higher DPI adds noise, not accuracy. | Trust existing benchmark. Investigate multi-ID noise via filtering, not re-scanning. |
| **Database Backend for Lookups** | "Store results in SQLite/PostgreSQL for querying" | Overhead for one-shot batch job. CSV + Excel filtering is sufficient for 52K records. Database adds complexity without value. | CSV sorted by ID enables instant Excel filtering. JSON provides programmatic lookup. Both already generated. |

## Feature Dependencies

```
Error/Quality Report
    └──requires──> Failed File Investigation
    └──requires──> No-Match Page Investigation
    └──requires──> Multi-ID Deduplication

Multi-ID Deduplication
    └──requires──> Confidence-Based Filtering OR Bounding Box Overlap Detection
                       └──optional──> Statistical Outlier Detection (enhances filtering)

ID Lookup CSV
    └──independent──> (no dependencies, pure transformation of existing results)

Automated Re-Processing Pipeline
    └──enhances──> Failed File Investigation
    └──enhances──> No-Match Page Investigation
```

### Dependency Notes

- **Error/Quality Report requires all investigations:** Report synthesizes findings from failed files, no-match pages, and multi-ID analysis. Can't write report without completing investigations.
- **Multi-ID Deduplication requires Confidence-Based Filtering OR Bounding Box Overlap:** Need at least one filtering mechanism. Confidence is simpler (LOW complexity), bounding box is more accurate (MEDIUM complexity). Can implement both for highest accuracy.
- **Statistical Outlier Detection enhances Multi-ID Deduplication:** Independent feature, but synergistic. Flags pages with 10+ IDs for manual review, reducing filtering workload.
- **Automated Re-Processing Pipeline enhances investigations:** Optional but valuable. Captures detailed error context for failed files and no-match pages, accelerating root cause analysis.
- **ID Lookup CSV is independent:** Pure pandas transformation of existing results.csv. No dependencies on other features.

## MVP Definition

### Launch With (v1.3)

Minimum viable product — what's needed to validate the concept.

- [x] **ID Lookup CSV (sorted by ID)** — Primary deliverable, enables Excel-based ID lookups
- [x] **Failed File Investigation** — 49 failures must be understood and documented
- [x] **No-Match Page Investigation** — 59 no-match pages must be categorized (real blanks vs OCR failures)
- [ ] **Multi-ID Deduplication (Confidence-Based)** — 5,141 pages need filtering; start with simple confidence threshold approach
- [ ] **Error/Quality Report** — Document all findings in structured markdown report

### Add After Validation (v1.3+)

Features to add once core is working.

- [ ] **Bounding Box Overlap Detection** — If confidence-based filtering insufficient, add spatial overlap detection for higher accuracy
- [ ] **Statistical Outlier Detection** — If manual review list still too large (>200 pages), add outlier flagging to surface edge cases
- [ ] **Multi-ID Categorization Report** — If stakeholders need granular breakdown (likely noise / likely real / uncertain), generate classification report

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Automated Re-Processing Pipeline** — Nice-to-have diagnostic tool, not critical for v1.3 deliverables
- [ ] **Visual Inspection UI** — Only if automated filtering fails to reduce manual review workload to <50 pages

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| ID Lookup CSV (sorted by ID) | HIGH | LOW | P1 |
| Failed File Investigation | HIGH | MEDIUM | P1 |
| No-Match Page Investigation | HIGH | MEDIUM | P1 |
| Multi-ID Deduplication (Confidence-Based) | HIGH | MEDIUM | P1 |
| Error/Quality Report | HIGH | LOW | P1 |
| Bounding Box Overlap Detection | MEDIUM | HIGH | P2 |
| Statistical Outlier Detection | MEDIUM | LOW | P2 |
| Multi-ID Categorization Report | LOW | MEDIUM | P3 |
| Automated Re-Processing Pipeline | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for v1.3 launch
- P2: Should have, add if P1 filtering insufficient
- P3: Nice to have, future consideration

## Post-Processing Feature Patterns (2026)

### Confidence Thresholding (Industry Standard)

**What:** Tesseract returns per-word confidence scores (0-100). Filter results below threshold.

**Thresholds:**
- **>90%:** Auto-accept (HIGH confidence)
- **70-90%:** Flag for review (MEDIUM confidence)
- **<70%:** Auto-reject or reprocess (LOW confidence)

**Implementation:** `pytesseract.image_to_data(img, output_type=Output.DICT)` returns `conf` key with confidence scores. Filter DataFrame: `df[df['conf'] > 70]`.

**Source confidence:** HIGH — Industry standard per [C# OCR Confidence Levels](https://ironsoftware.com/csharp/ocr/how-to/tesseract-result-confidence/), [Confidence Score Explained](https://faq.veryfi.com/en/articles/5571597-confidence-score-explained), [OCR Accuracy Benchmarks 2026](https://medium.com/@info_59976/ocr-accuracy-benchmarks-the-2026-digital-transformation-revolution-2f7095c2696f)

### Bounding Box Deduplication (Spatial Overlap)

**What:** Detect duplicate text recognized at multiple rotations via Intersection over Union (IoU).

**Method:** Non-Maximum Suppression (NMS). For each pair of detected IDs:
1. Calculate IoU = (overlap area) / (union area)
2. If IoU > 0.5 (50% overlap), likely duplicate
3. Keep ID with higher confidence, discard lower

**Implementation:** `image_to_data` returns `left, top, width, height` for bounding boxes. Calculate overlap:
```python
def calculate_iou(box1, box2):
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2

    xi1, yi1 = max(x1, x2), max(y1, y2)
    xi2, yi2 = min(x1+w1, x2+w2), min(y1+h1, y2+h2)

    inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
    box1_area = w1 * h1
    box2_area = w2 * h2
    union_area = box1_area + box2_area - inter_area

    return inter_area / union_area if union_area > 0 else 0
```

**Source confidence:** HIGH — Standard computer vision technique per [Intersection over Union (IoU)](https://www.ultralytics.com/glossary/intersection-over-union-iou), [Confidence-Aware Document OCR Error Detection](https://arxiv.org/pdf/2409.04117)

### Statistical Outlier Detection (Anomaly Flagging)

**What:** Flag pages with abnormally high ID counts using Modified Z-Score or IQR method.

**IQR Method:**
1. Calculate Q1 (25th percentile), Q3 (75th percentile) of IDs per page
2. IQR = Q3 - Q1
3. Flag pages where ID_count > Q3 + 1.5×IQR

**Modified Z-Score:** More robust than standard Z-score for skewed distributions.
```python
median = np.median(id_counts)
mad = np.median(np.abs(id_counts - median))  # Median Absolute Deviation
modified_z = 0.6745 * (id_counts - median) / mad
outliers = modified_z > 3.5  # Flag values with |modified_z| > 3.5
```

**Source confidence:** HIGH — Standard statistical methods per [IQR Method Outlier Detection](https://plotnerd.com/blog/complete-guide-to-iqr-method-outlier-detection/), [Outlier Detection: IQR vs Z-Score](https://vrcacademy.com/tutorials/outliers/), [Performance Evaluation of Robust Scale Estimators](https://www.researchgate.net/publication/405042816)

### Error Categorization (Batch Processing Pattern)

**What:** Group failures by error type (FileNotFoundError, EmptyFileError, OCRTimeout, etc.) for root cause analysis.

**Categories:**
- **File I/O Errors:** FileNotFoundError, PermissionError, EmptyFileError
- **OCR Failures:** No text detected after all rotations
- **Format Errors:** Invalid PDF, corrupted file, unsupported encoding
- **Timeout/Resource:** MemoryError, timeout exceeded

**Implementation:** Try-except blocks with error type logging. Aggregate counts by category.

**Source confidence:** MEDIUM — Common pattern per [Batch Status and Error Codes](https://learn.microsoft.com/en-us/rest/api/batchservice/batch-status-and-error-codes), [Error handling in Azure Batch](https://learn.microsoft.com/en-us/azure/batch/error-handling), [BioDSA-1K Benchmarking](https://arxiv.org/pdf/2505.16100)

### Data Quality Report Structure (Audit Pattern)

**What:** Structured report documenting errors, root causes, remediation recommendations.

**Standard Sections:**
1. **Executive Summary:** High-level findings, key metrics, major issues
2. **Error Breakdown:** Counts by category, percentages, severity levels
3. **Root Cause Analysis:** Why errors occurred, contributing factors
4. **Validation Results:** Success rate, coverage, accuracy metrics
5. **Recommendations:** Fixes to implement, process improvements, future monitoring

**Source confidence:** HIGH — Industry standard per [Data Quality Audit Guide 2026](https://improvado.io/blog/guide-to-data-quality-audits), [9 Common Data Quality Problems 2026](https://www.ovaledge.com/blog/data-quality-problems), [Data Quality Guidelines](https://op.europa.eu/webpub/op/data-quality-guidelines/en/)

## Sources

### OCR Post-Processing and Filtering
- [Post-processing of OCR results for automatic indexing](https://ieeexplore.ieee.org/document/601966/)
- [Survey of Post-OCR Processing Approaches](https://dl.acm.org/doi/10.1145/3453476)
- [OCR Best Practices in 2026: Production-Ready Pipeline](https://preocr.io/blog/ocr-best-practices-in-2026-how-to-build-a-production-ready-ocr-pipeline)
- [Technical Analysis of Modern Non-LLM OCR Engines](https://intuitionlabs.ai/articles/non-llm-ocr-technologies)

### Confidence Scoring and Validation
- [C# OCR Confidence Levels: Text Recognition Accuracy](https://ironsoftware.com/csharp/ocr/how-to/tesseract-result-confidence/)
- [Confidence Score Explained | Veryfi Help Center](https://faq.veryfi.com/en/articles/5571597-confidence-score-explained)
- [OCR Accuracy Benchmarks: 2026 Digital Transformation Revolution](https://medium.com/@info_59976/ocr-accuracy-benchmarks-the-2026-digital-transformation-revolution-2f7095c2696f)
- [Understanding confidence scores in Machine Learning](https://www.mindee.com/blog/how-use-confidence-scores-ml-models)
- [Triage of OCR Results Using Confidence Scores (PDF)](https://www.researchgate.net/publication/2855972_Triage_of_OCR_Results_Using_Confidence'_Scores)

### Tesseract-Specific Features
- [Tesseract Review 2026: Features, Pros & Cons](https://research.com/software/reviews/tesseract)
- [Adjusting confidence thresholds in Tesseract.js](https://app.studyraid.com/en/read/15018/519349/adjusting-confidence-thresholds-in-tesseractjs)
- [Tesseract OCR: Text localization and detection](https://pyimagesearch.com/2020/05/25/tesseract-ocr-text-localization-and-detection/)
- [Python OCR Tutorial: Tesseract, Pytesseract, and OpenCV](https://nanonets.com/blog/ocr-with-tesseract/)
- [Text Localization using Pytesseract - GeeksforGeeks](https://www.geeksforgeeks.org/python/text-localization-detection-and-recognition-using-pytesseract/)

### Duplicate Detection and Deduplication
- [Noise-Robust De-Duplication at Scale](https://arxiv.org/pdf/2210.04261)
- [Fuzzy Matching 101: Accurate Data Matching 2026](https://dataladder.com/fuzzy-matching-101/)
- [Detection Masking for Improved OCR on Noisy Documents](https://ar5iv.labs.arxiv.org/html/2205.08257)
- [ReviewGenX Smart Deduplication for Accurate Record Review](https://www.mosmedicalrecordreview.com/blog/how-reviewgenx-smart-deduplication-improves-accuracy/)

### Bounding Box Overlap Detection
- [Intersection over Union (IoU) | Ultralytics](https://www.ultralytics.com/glossary/intersection-over-union-iou)
- [Confidence-Aware Document OCR Error Detection](https://arxiv.org/pdf/2409.04117)
- [Overlapping Box Suppression and Merging Algorithms (PDF)](https://www.researchgate.net/publication/394827947_Overlapping_Box_Suppression_and_Merging_Algorithms_for_Window-Based_Object_Detection)

### Statistical Outlier Detection
- [Complete Guide to IQR Method Outlier Detection](https://plotnerd.com/blog/complete-guide-to-iqr-method-outlier-detection/)
- [Outlier Detection: IQR vs Z-Score vs Modified Z-Score](https://vrcacademy.com/tutorials/outliers/)
- [3 Simple Statistical Methods for Outlier Detection](https://towardsdatascience.com/3-simple-statistical-methods-for-outlier-detection-db762e86cd9d/)
- [Outlier Detection Methods — IQR, Z-Score & Statistical Tests](https://statsolvepro.com/outlier-detection-methods/)
- [Performance Evaluation of Robust Scale Estimators for Modified Z-Score](https://www.researchgate.net/publication/405042816)

### Batch Processing Error Handling
- [Batch Status and Error Codes | Microsoft Learn](https://learn.microsoft.com/en-us/rest/api/batchservice/batch-status-and-error-codes)
- [Error handling in Azure Batch | Microsoft Learn](https://learn.microsoft.com/en-us/azure/batch/error-handling)
- [BioDSA-1K: Benchmarking Data Science Agents for Biomedical Research](https://arxiv.org/pdf/2505.16100)
- [Batch Document Processing OCR Guide](https://klearstack.com/blogs/batch-document-processing-ocr)

### Data Quality Auditing
- [Data Quality Audit: Complete Guide 2026](https://improvado.io/blog/guide-to-data-quality-audits)
- [9 Common Data Quality Problems 2026](https://www.ovaledge.com/blog/data-quality-problems)
- [Complete Guide to Data Quality: Frameworks, Tools, Best Practices](https://soda.io/blog/guide-data-quality-frameworks-tools-best-practices)
- [12 Data Quality Metrics to Measure in 2026](https://lakefs.io/data-quality/data-quality-metrics/)
- [Data Quality Guidelines](https://op.europa.eu/webpub/op/data-quality-guidelines/en/)

### Data Validation Pipelines
- [Recommended 8 Anomaly Detection Pipelines for CSV Quality 2026](https://www.topetl.com/blog/recommended-8-anomaly-detection-pipelines-for-csv-quality)
- [Real-Time Data Validation: Catching Bad Data Before It Lands](https://streamkap.com/resources-and-guides/stream-data-validation)

### CSV Export and Sorting
- [How to sort CSV by multiple columns with pandas](https://www.usepandas.com/csv/sort-csv-data-by-column)
- [Pandas Sort Values: Complete Guide](https://docs.kanaries.net/topics/Pandas/pandas-sort-values)
- [pandas Sort: Guide to Sorting Data in Python](https://realpython.com/pandas-sort-python/)
- [5 Best Ways to Sort CSV by Multiple Columns in Python](https://blog.finxter.com/5-best-ways-to-sort-csv-by-multiple-columns-in-python/)

---
*Feature research for: OCR Result Post-Processing and ID Lookup Generation*
*Researched: 2026-06-09*
