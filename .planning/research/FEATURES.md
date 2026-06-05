# Feature Landscape: Campaign Management for Batch OCR

**Domain:** Interactive campaign runner for long-running batch OCR processing
**Researched:** 2026-06-05
**Context:** Adding campaign management to existing OCR pipeline (v1.1 milestone)

**Note:** This document focuses on NEW campaign management features for v1.1. Base OCR pipeline features (recursive discovery, multi-page PDF handling, multi-rotation OCR, parallel processing, checkpoint/resume, preprocessing) are already built in v1.0.

---

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Continue from checkpoint** | Standard batch job UX. Users expect resume after Ctrl+C or crash without reprocessing completed files. | Low | Already have checkpoint system in place. Menu just needs to detect existing state and offer "Continue" option. **Confidence: HIGH** |
| **Graceful Ctrl+C handling** | Industry standard for long-running CLI jobs. Canonical pattern: stop accepting → drain → save state → exit. | Medium | Requires signal handling (SIGINT/SIGTERM), finishing current files in flight, flushing checkpoint atomically. Windows uses different signal model than Linux. **Confidence: HIGH** |
| **Completion progress tracking** | Users need to know "X of Y files processed (Z%)". Standard for any batch job. | Low | Already have tqdm progress bars. Enhancement: show files completed vs total, ETA based on processing rate. **Confidence: HIGH** |
| **Success/failure counts** | Users expect to see how many files succeeded vs failed. Basic accountability for batch processing quality. | Low | Aggregate from checkpoint data. Display: "Completed: 28,500 \| Failures: 150 \| Remaining: 1,779". **Confidence: HIGH** |
| **View partial results** | Users need to see progress before completion. Extract partial CSV/JSON from checkpoint without waiting for full campaign to finish. | Low | Read checkpoint state file, export what's been processed so far. Useful for spot-checking quality mid-run. **Confidence: HIGH** |
| **Re-run failed files only** | Standard failure recovery pattern. After fixing environment issues (e.g., Tesseract path), users expect to retry only failed items, not reprocess successes. | Medium | Requires filtering checkpoint to identify failures, creating new campaign targeting only those files. Depends on checkpoint schema tracking success/failure status. **Confidence: HIGH** |
| **Real-time processing rate** | Users expect "files/minute" or "pages/second" to estimate completion time and detect slowdowns. | Low | tqdm provides iteration rate out-of-box. Enhancement: track files/min and pages/min separately since multi-page PDFs vary. **Confidence: HIGH** |
| **Error summary on exit** | When campaign finishes or is interrupted, show summary: "X files failed. See failures in [output file]". | Low | Print summary from checkpoint aggregation. List top failure reasons if patterns detected (e.g., "75 files: PDF corrupted, 20 files: No ID found"). **Confidence: MEDIUM** |

**Source confidence:** HIGH - Based on [graceful shutdown patterns](https://zylos.ai/research/2026-02-25-graceful-shutdown-long-lived-services/), [batch job monitoring best practices](https://oneuptime.com/blog/post/2026-01-30-batch-processing-monitoring/view), [checkpoint/resume workflows](https://fast.io/resources/ai-agent-checkpointing-resume/), and [batch processing metrics](https://oneuptime.com/blog/post/2026-01-30-batch-processing-metrics/view).

---

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Per-folder quality breakdown** | Unique insight: "Folder A: 99% success, Folder B: 85% success". Helps users identify problem directories (e.g., older scans, different scanner). | Medium | Track statistics hierarchically during processing. Aggregate by directory path. Display tree-style breakdown or table sorted by error rate. **Confidence: MEDIUM** |
| **Interactive campaign menu** | Better UX than command-line flags for resume scenarios. On detecting existing checkpoint: "1) Continue, 2) Re-run failures, 3) View stats, 4) Export partial results, 5) Start fresh". | Medium | Use InquirerPy or Rich prompts. Requires designing menu flow and validation logic. More polish than functional necessity. **Confidence: HIGH** |
| **Smart ETA with historical data** | Better than linear projection. Track processing rate per folder, adjust ETA based on folder characteristics (e.g., older scans slower). | High | Requires tracking per-folder historical rate, building regression model. Complex for v1.1. Defer unless simple moving average sufficient. **Confidence: LOW** |
| **Preprocessing fallback statistics** | Show how often fallback was triggered: "Primary OCR: 92% \| Fallback preprocessing: 8%". Helps users understand quality distribution and preprocessing cost. | Low | Already have fallback logic. Add counter for when fallback path executes. Display in final summary. **Confidence: HIGH** |
| **OCR confidence scores** | Tesseract provides per-character confidence. Aggregate to page-level: "High confidence: 85% \| Medium: 10% \| Low: 5%". Flags pages needing manual review. | Medium | pytesseract.image_to_data() returns confidence scores. Aggregate by page. Threshold: >90% = high, 70-90% = medium, <70% = low. Adds processing overhead. **Confidence: MEDIUM** |
| **Rotation heuristic reporting** | Track which rotations succeeded: "90°: 70% \| 270°: 20% \| 0°: 8% \| 180°: 2%". Insight into document orientation patterns. | Low | Multi-rotation strategy already tracks which angle succeeded. Aggregate counts across campaign. Display in summary. **Confidence: HIGH** |
| **Anomaly detection flags** | Flag unusual patterns: "Folder X has 10x more failures than average" or "Last 100 files processing slower than first 1000". Proactive alerting. | High | Requires statistical modeling (Z-score, moving averages). Complex for v1.1. Valuable but non-critical. **Confidence: LOW** |
| **Batch comparison reports** | Compare multiple campaign runs: "Run 1 vs Run 2: +5% accuracy after preprocessing tuning". Useful for optimization experiments. | High | Out of scope for single campaign runner. Requires campaign ID tracking, historical database. Defer to future version. **Confidence: LOW** |

**Source confidence:** MEDIUM-HIGH - Based on [batch statistics implementation](https://oneuptime.com/blog/post/2026-01-30-batch-processing-statistics/view), [OCR accuracy metrics](https://www.docsumo.com/blogs/ocr/accuracy), [interactive CLI patterns with InquirerPy](https://github.com/kazhala/InquirerPy), and [Rich progress tracking](https://rich.readthedocs.io/en/stable/progress.html).

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time dashboard web UI** | Out of scope per PROJECT.md. Adds web server, frontend complexity. CLI-only requirement. | Stick to terminal UI with Rich. Users can export partial results and analyze in Excel/Pandas if needed. **Confidence: HIGH** |
| **Automatic failure retry logic** | Dangerous without root cause understanding. Re-running corrupted PDFs wastes time. User should investigate failures first. | Provide "Re-run failures" menu option that requires explicit user choice. Show failure reasons so user can fix environment before retry. **Confidence: HIGH** |
| **Database-backed checkpoint** | PROJECT.md specifies no database. JSON checkpoint files sufficient. DB adds dependency, deployment complexity. | Continue with atomic JSON checkpoint writes. Portable, human-readable, crash-safe with tempfile+os.replace pattern. **Confidence: HIGH** |
| **Parallel campaign execution** | Confusing UX. Users don't need to run multiple campaigns simultaneously. Single campaign with parallelization within is sufficient. | One active campaign at a time. Users can run multiple terminal sessions manually if needed, but don't build orchestration for it. **Confidence: HIGH** |
| **Interactive page-by-page review** | Not "no manual intervention" per constraints. Campaign runs fully automated. Manual review happens after completion using exported CSV/JSON. | Provide high-quality reports (confidence scores, failure summaries) so users know what to review manually post-processing. **Confidence: HIGH** |
| **Cloud storage integration** | Local-only tool per constraints. No AWS S3, Azure Blob, etc. Adds network dependencies, auth complexity. | Users can manually upload CSV/JSON outputs if they want cloud storage. Keep tool file-system only. **Confidence: HIGH** |
| **Email/Slack notifications** | Over-engineering for local CLI tool. Users will monitor terminal or check later. Notifications require configuration, auth, network. | Print clear terminal summaries. Users can wrap script with their own notification logic if desired (e.g., `python precede_ocr.py && curl slack-webhook`). **Confidence: MEDIUM** |
| **Adaptive parallelization** | Complexity not worth benefit. Dynamic worker scaling based on CPU/memory adds overhead, unpredictable behavior. | Stick with static worker count (--workers N). Let users tune based on their system. Simple, predictable, sufficient. **Confidence: HIGH** |

**Source confidence:** HIGH - Based on project requirements (CLI-only, local, no manual intervention, no database per PROJECT.md) and [batch processing anti-patterns](https://www.linkedin.com/advice/0/what-common-challenges-pitfalls-batch-processing).

---

## Feature Dependencies

```
Interactive campaign menu → Checkpoint detection (ALREADY EXISTS)
Re-run failures → Checkpoint failure tracking (ALREADY EXISTS: notes field)
Per-folder statistics → Checkpoint schema enhancement (ADD: folder_path tracking)
Graceful Ctrl+C → Signal handling + atomic checkpoint save (ALREADY ATOMIC)
Export partial results → Checkpoint read + CSV/JSON generation (REUSE: existing export logic)
OCR confidence scores → pytesseract.image_to_data() instead of image_to_string() (CHANGE: OCR call)
Preprocessing fallback stats → Counter in preprocessing path (ADD: simple counter)
Rotation heuristic reporting → Track successful rotation angle (ALREADY TRACKED: rotation_detected field)
```

**Key insight:** Most campaign features leverage existing checkpoint infrastructure. Minimal new dependencies. Clean incremental enhancement.

---

## MVP Recommendation

### Priority 1: Core Campaign UX (Table Stakes)

1. **Graceful Ctrl+C handling** — Register signal handler, finish in-flight files, save checkpoint, exit cleanly
2. **Interactive campaign menu** — Detect checkpoint, offer: Continue | Re-run failures | View stats | Export partial | Start fresh
3. **Completion progress tracking** — Enhanced tqdm/Rich: "Completed: X/Y (Z%) | Rate: A files/min | ETA: B"
4. **Success/failure summary** — On exit: "Completed: X | Failures: Y | Success rate: Z%"

### Priority 2: Quality Insights (Differentiators)

5. **Per-folder statistics** — Track and display error rate by directory: helps identify problem areas
6. **Preprocessing fallback statistics** — Show how often fallback triggered: "Primary: 92% | Fallback: 8%"
7. **Rotation heuristic reporting** — Aggregate rotation angles: "90°: 70% | 270°: 20% | 0°: 8% | 180°: 2%"

### Priority 3: Advanced Quality (Defer if Time-Constrained)

8. **OCR confidence scores** — Page-level confidence aggregation from Tesseract. Useful but adds overhead.
9. **Smart ETA with historical data** — Complexity not justified for v1.1. Linear ETA sufficient.
10. **Anomaly detection flags** — Valuable but complex. Defer to future version.

### Defer to Future Versions

- **Batch comparison reports** — Requires historical database, out of scope
- **Adaptive parallelization** — Over-engineering, static workers sufficient
- **All anti-features** — Explicitly avoid per rationale above

**Rationale:** Focus on table stakes that make long-running campaigns manageable (graceful stop, resume menu, progress visibility). Add quality insights (per-folder stats, fallback tracking) to help users understand results. Defer complex features requiring statistical modeling or historical tracking.

---

## Implementation Notes

### Existing Checkpoint Schema (Assumed)

```json
{
  "version": "1.0",
  "started_at": "2026-06-05T10:30:00",
  "last_updated": "2026-06-05T12:45:00",
  "completed": ["file1.pdf", "file2.pdf"],
  "failed": {
    "file3.pdf": "Corrupted PDF",
    "file4.pdf": "No ID found"
  },
  "results": {
    "file1.pdf": {"page_1": ["12345"], "page_2": ["67890"]},
    "file2.pdf": {"page_1": ["11111"]}
  }
}
```

### Enhancements Needed for Campaign Features

**Add to checkpoint:**
- `folder_statistics`: Map of folder paths to {total, succeeded, failed, fallback_count, rotation_distribution}
- `global_statistics`: {total_files, total_pages, total_ids, fallback_triggered_count}
- `processing_rate_history`: List of {timestamp, files_completed, rate} for ETA calculation

**No schema break:** Add fields, keep backward compatibility. Old checkpoints work, just lack new statistics.

### Libraries for Interactive Menu

| Library | Pros | Cons | Recommendation |
|---------|------|------|----------------|
| **InquirerPy** | Most feature-rich. Fuzzy search, validation, customization. Modern prompt_toolkit 3.0+ based. | Heavier dependency. | **RECOMMENDED** for best UX |
| **questionary** | Simpler than InquirerPy. Well-established, stable. prompt_toolkit based. | Less customization than InquirerPy. | Fallback if InquirerPy issues |
| **Rich prompts** | Already using Rich for progress bars. Integrated styling. | Less mature prompt features than InquirerPy. | Use for simple yes/no, not full menu |
| **python-inquirer** | Uses blessed instead of prompt_toolkit. | Different ecosystem, less cross-platform testing. | **AVOID** - prompt_toolkit better |

**Verdict:** InquirerPy for interactive menu. Already planning to use Rich for progress/statistics display. Complementary libraries.

**Source:** [InquirerPy GitHub](https://github.com/kazhala/InquirerPy), [InquirerPy vs questionary comparison](https://inquirerpy.readthedocs.io/), [Rich interactive CLI](https://arjancodes.com/blog/rich-python-library-for-interactive-cli-tools/).

### Statistics Display with Rich

Use **Rich Tables** and **Rich Layout** for campaign summary:

```python
from rich.console import Console
from rich.table import Table
from rich.layout import Layout

console = Console()

# Overall statistics table
stats_table = Table(title="Campaign Statistics")
stats_table.add_column("Metric", style="cyan")
stats_table.add_column("Value", style="magenta")
stats_table.add_row("Total Files", "30,429")
stats_table.add_row("Completed", "28,500 (93.7%)")
stats_table.add_row("Failed", "150 (0.5%)")
stats_table.add_row("Remaining", "1,779 (5.8%)")
stats_table.add_row("Processing Rate", "45 files/min")

# Per-folder breakdown table
folder_table = Table(title="Per-Folder Quality")
folder_table.add_column("Folder", style="cyan")
folder_table.add_column("Total", justify="right")
folder_table.add_column("Success Rate", justify="right", style="green")
folder_table.add_column("Failures", justify="right", style="red")
folder_table.add_row("scans/2020", "5000", "99.2%", "40")
folder_table.add_row("scans/2019", "4500", "85.3%", "661")

console.print(stats_table)
console.print(folder_table)
```

**Source:** [Rich Progress Display](https://rich.readthedocs.io/en/stable/progress.html), [Rich Tables documentation](https://github.com/Textualize/rich), [Multi-threading Progress with Rich](https://liumaoli.me/notes/notes-about-rich/).

### Graceful Shutdown Pattern (Windows)

Python signal handling on Windows is limited but functional:

```python
import signal
import sys
from multiprocessing import Pool, Event

shutdown_event = Event()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n⚠️  Shutdown requested. Finishing current files...")
    shutdown_event.set()
    # Don't call sys.exit() — let main loop finish naturally

def process_with_shutdown_check(pdf_path):
    """Worker function that checks shutdown event"""
    if shutdown_event.is_set():
        return None  # Skip processing if shutdown requested
    return process_pdf(pdf_path)  # Existing function

def main():
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Kill command

    # Process with periodic shutdown checks
    # ... existing multiprocessing logic ...

    # After loop, save checkpoint and exit gracefully
    if shutdown_event.is_set():
        save_checkpoint_atomically(state)
        print("✓ Checkpoint saved. Run again to resume.")
        sys.exit(0)
```

**Windows caveats:**
- SIGTERM not sent by Ctrl+C (only SIGINT)
- Process pool workers ignore signals (only main process receives)
- Use `shutdown_event` (multiprocessing.Event) to communicate to workers
- Workers check event periodically (e.g., before each PDF)

**Source:** [Graceful Shutdown Patterns](https://zylos.ai/research/2026-02-25-graceful-shutdown-long-lived-services/), [River graceful shutdown docs](https://riverqueue.com/docs/graceful-shutdown), [Graceful shutdown in Go patterns (applicable concepts)](https://dev.to/young_gao/graceful-shutdown-in-go-patterns-every-production-service-needs-3l9c).

### Progress Tracking with Rich

Existing code likely uses `tqdm` for basic progress. Campaign runner enhancements:

**Rich Progress (recommended for campaign dashboard)**

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TextColumn("({task.completed}/{task.total})"),
    TextColumn("•"),
    TextColumn("[cyan]{task.fields[rate]:.1f} files/min"),
    TimeRemainingColumn(),
    TimeElapsedColumn(),
) as progress:
    task = progress.add_task(
        "[green]Processing PDFs...",
        total=total_files,
        rate=0.0  # Custom field
    )

    for pdf in pdf_list:
        result = process_pdf(pdf)
        progress.update(task, advance=1, rate=calculate_rate())
```

**Recommendation:** Switch to Rich Progress for campaign runner. Better integration with Rich tables/layout for statistics display. More modern styling. tqdm sufficient for simple scripts, but campaign runner benefits from richer UI.

**Source:** [Rich Progress documentation](https://rich.readthedocs.io/en/stable/progress.html), [Richer progress bars tutorial](https://timothygebhard.de/posts/richer-progress-bars-for-rich/), [Progress bars with Rich](https://www.willmcgugan.com/blog/tech/post/progress-bars-with-rich/).

---

## Complexity Assessment by Feature

| Feature | Complexity | Estimated Effort | Rationale |
|---------|------------|------------------|-----------|
| Interactive campaign menu | Medium | 4-6 hours | InquirerPy integration, menu logic, state detection |
| Graceful Ctrl+C | Medium | 3-5 hours | Signal handling, shutdown coordination, testing edge cases |
| Per-folder statistics | Medium | 4-6 hours | Checkpoint schema enhancement, aggregation logic, display |
| Completion progress (enhanced) | Low | 2-3 hours | Rich Progress integration, rate calculation |
| Success/failure summary | Low | 1-2 hours | Aggregate from checkpoint, format display |
| Export partial results | Low | 2-3 hours | Read checkpoint, reuse existing CSV/JSON export |
| Re-run failures | Medium | 3-4 hours | Filter checkpoint, create failure-only file list |
| Preprocessing fallback stats | Low | 1-2 hours | Add counter, display in summary |
| Rotation heuristic reporting | Low | 1-2 hours | Aggregate rotation_detected field, display distribution |
| OCR confidence scores | Medium | 5-8 hours | Change OCR call, aggregate scores, threshold logic, testing |

**Total estimated effort for Priority 1+2 (MVP):** ~20-30 hours

**Source confidence:** MEDIUM - Based on implementation patterns from [batch processing best practices](https://oneuptime.com/blog/post/2026-01-30-batch-processing-metrics/view), [Python multiprocessing challenges](https://www.linkedin.com/advice/0/what-common-challenges-pitfalls-batch-processing), and experience estimates from similar CLI tools.

---

## Quality Metrics for Campaign Management

**Success rate threshold:** 99% or higher for production batch jobs. 95%+ acceptable for initial validation runs.

**Throughput targets:** Based on hardware:
- 4 cores: 15-25 files/min (0.25-0.4 files/sec)
- 8 cores: 30-50 files/min (0.5-0.8 files/sec)
- 16 cores: 60-100 files/min (1.0-1.7 files/sec)

**Time-to-completion for 30K corpus:**
- Serial: 30-50 hours (unacceptable)
- 4 cores: 20-35 hours
- 8 cores: 10-17 hours
- 16 cores: 5-8 hours (target)

**Error handling SLA:** Isolated failures should not crash batch. <0.6% error rate (6 per mille) is industry standard for batch jobs.

**Confidence score thresholds (if implemented):**
- High: >90% confidence — likely accurate
- Medium: 70-90% confidence — review recommended
- Low: <70% confidence — manual verification required

**Source:** [Batch processing metrics](https://oneuptime.com/blog/post/2026-01-30-batch-processing-metrics/view), [OCR accuracy benchmarks](https://medium.com/@sanjeeva.bora/the-definitive-guide-to-ocr-accuracy-benchmarks-and-best-practices-for-2025-8116609655da), [Task completion metrics](https://fastercapital.com/content/Task-Completion--Completion-Metrics--Measuring-Success-with-Completion-Metrics.html).

---

## Research Confidence Assessment

| Feature Category | Confidence | Notes |
|------------------|------------|-------|
| **Table stakes** | HIGH | Well-established patterns in batch processing systems; multiple sources confirm |
| **Differentiators** | MEDIUM-HIGH | Per-folder stats and rotation reporting straightforward; OCR confidence and anomaly detection more complex |
| **Anti-features** | HIGH | Based on explicit project requirements (CLI-only, local, no database, no manual intervention) |
| **Complexity estimates** | MEDIUM | Dependent on actual implementation and edge cases; estimates from similar CLI tools |
| **Library choices** | HIGH | InquirerPy and Rich are well-documented, actively maintained (2026) |
| **Graceful shutdown on Windows** | MEDIUM | Python signal handling on Windows is functional but limited; requires testing |

---

## Sources

### Campaign Management and Batch Processing
- [Campaign management for batch processes - Google Patents](https://patents.google.com/patent/GB2364399A/en)
- [Batch Execution - Campaign Manager Guide (GE Digital)](https://www.ge.com/digital/documentation/batch/Campaign_Manager.pdf)
- [How to Create Batch Statistics (OneUpTime Blog)](https://oneuptime.com/blog/post/2026-01-30-batch-processing-statistics/view)
- [How to Implement Batch Reporting (OneUpTime Blog)](https://oneuptime.com/blog/post/2026-01-30-batch-processing-reporting/view)

### Graceful Shutdown Patterns
- [Long-Running Tasks in ASP.NET Core: 2026 Best Practices](https://boldsign.com/blogs/long-running-tasks-asp-net-core-best-practices/)
- [How to Use Graceful Shutdown Handlers for Long-Running Kubernetes Processes (OneUpTime)](https://oneuptime.com/blog/post/2026-02-09-graceful-shutdown-handlers/view)
- [Graceful Shutdown Patterns for Long-Lived Services (Zylos Research)](https://zylos.ai/research/2026-02-25-graceful-shutdown-long-lived-services/)
- [Graceful Shutdown in Go: Patterns Every Production Service Needs (DEV Community)](https://dev.to/young_gao/graceful-shutdown-in-go-patterns-every-production-service-needs-3l9c)
- [Graceful shutdown (River Docs)](https://riverqueue.com/docs/graceful-shutdown)

### Batch Monitoring and Statistics
- [How to Create Batch Monitoring (OneUpTime Blog)](https://oneuptime.com/blog/post/2026-01-30-batch-processing-monitoring/view)
- [Best Batch Document Processing Software in 2026 (CompareOCRTools)](https://www.compareocrtools.com/best-batch-document-processing-software)
- [How to Monitor AWS Batch Jobs with CloudWatch (OneUpTime)](https://oneuptime.com/blog/post/2026-02-12-monitor-aws-batch-jobs-with-cloudwatch/view)
- [Batch job statistics (IBM Documentation)](https://www.ibm.com/docs/en/imdm/11.6.0?topic=overview-batch-job-statistics)

### Interactive CLI Libraries
- [InquirerPy (GitHub)](https://github.com/kazhala/InquirerPy)
- [InquirerPy Documentation](https://inquirerpy.readthedocs.io/)
- [inquirerpy · PyPI](https://pypi.org/project/inquirerpy/)
- [The Green Report | Interactive CLI Automation with Python](https://www.thegreenreport.blog/articles/interactive-cli-automation-with-python/interactive-cli-automation-with-python.html)
- [Rich Python Library for Advanced CLI Design (ArjanCodes)](https://arjancodes.com/blog/rich-python-library-for-interactive-cli-tools/)

### Progress Tracking and Display
- [Progress Display — Rich Documentation](https://rich.readthedocs.io/en/stable/progress.html)
- [Multi-threading and Multi-processing Progress Visualization with Python's rich Library](https://liumaoli.me/notes/notes-about-rich/)
- [tqdm GitHub Repository](https://github.com/tqdm/tqdm)
- [Progress Bars in Python: A Complete Guide with Examples (DataCamp)](https://www.datacamp.com/tutorial/progress-bars-in-python)
- [alive-progress · PyPI](https://pypi.org/project/alive-progress/)

### Checkpoint and Resume Patterns
- [AI Agent Checkpointing: Save State and Resume Guide (Fastio)](https://fast.io/resources/ai-agent-checkpointing-resume/)
- [Checkpointing and Resuming Workflows (Microsoft Learn)](https://learn.microsoft.com/en-us/agent-framework/tutorials/workflows/checkpointing-and-resuming)
- [Resume a run (Weights & Biases Documentation)](https://docs.wandb.ai/models/runs/resuming)
- [Partial Batch Export (Tungsten Automation)](https://docshield.tungstenautomation.com/kc/en_us/11.1.0-40hy9nfk91/help/main/KC_administration/batchclasses/c_partialbatchexport.html)
- [BatchOps GitHub Agentic Workflows](https://github.github.com/gh-aw/patterns/batch-ops/)

### OCR Accuracy Metrics and Quality
- [Analysis and Benchmarking of OCR Accuracy for Data Extraction Models (Docsumo)](https://www.docsumo.com/blogs/ocr/accuracy)
- [The Definitive Guide to OCR Accuracy: Benchmarks and Best Practices for 2025](https://medium.com/@sanjeeva.bora/the-definitive-guide-to-ocr-accuracy-benchmarks-and-best-practices-for-2025-8116609655da)
- [Evaluate OCR Output Quality with Character Error Rate (CER) and Word Error Rate (WER)](https://towardsdatascience.com/evaluating-ocr-output-quality-with-character-error-rate-cer-and-word-error-rate-wer-853175297510/)
- [OCR accuracy metrics: How to calculate and improve them](https://charted.com/blog/understanding-ocr-accuracy-how-its-measured-and-why-it-matters/)

### Batch Processing Metrics and Performance
- [How to Implement Batch Metrics (OneUpTime Blog)](https://oneuptime.com/blog/post/2026-01-30-batch-processing-metrics/view)
- [How to Measure Batch Processing Performance (LinkedIn)](https://www.linkedin.com/advice/0/what-common-challenges-pitfalls-batch-processing)
- [What is Batch processing? Meaning, Examples, Use Cases (TheDataOps)](https://www.thedataops.org/batch-processing/)
- [Task Completion: Completion Metrics (FasterCapital)](https://fastercapital.com/content/Task-Completion--Completion-Metrics--Measuring-Success-with-Completion-Metrics.html)
