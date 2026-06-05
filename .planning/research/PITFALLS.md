# Pitfalls Research

**Domain:** Adding Campaign Management to Multiprocessing OCR Pipeline (Windows 10)
**Researched:** 2026-06-05
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Signal Handlers Execute Only in Main Thread (Windows spawn Method)

**What goes wrong:**
When using multiprocessing on Windows (which uses the `spawn` start method), signal handlers registered with `signal.signal(signal.SIGINT, handler)` execute ONLY in the main thread of the main process. If the main thread is blocked waiting on `pool.join()` or a blocking iterator like `pool.imap()`, the handler won't execute until that blocking call completes, making the program unresponsive to Ctrl+C.

**Why it happens:**
Python's signal handling design restricts handler execution to the main thread of the main interpreter. On Windows, processes are spawned fresh (not forked), creating process isolation that prevents workers from receiving signals directly. Additionally, blocking calls like `pool.join()` prevent the main thread from processing signals until the call returns.

**How to avoid:**
1. **Use non-blocking iteration with timeout checks**: Replace `pool.map()` with `pool.imap_unordered()` and iterate with small timeouts to allow signal processing:
   ```python
   it = pool.imap_unordered(process_pdf, pdf_files, chunksize=1)
   while True:
       try:
           result = it.next(timeout=0.5)  # Check every 0.5s
           # process result
       except StopIteration:
           break
       except multiprocessing.TimeoutError:
           continue  # Allow signal handler to run
   ```

2. **Replace blocking pool.join() with timed polling**:
   ```python
   pool.close()
   while not shutdown_event.is_set():
       pool.join(timeout=0.5)
       if not pool._pool:  # Workers finished
           break
   ```

3. **Use apply_async with get(timeout)** instead of blocking map:
   ```python
   results = [pool.apply_async(func, (item,)) for item in items]
   for result in results:
       try:
           value = result.get(timeout=0.5)
       except multiprocessing.TimeoutError:
           continue
   ```

**Warning signs:**
- Program ignores Ctrl+C completely during `pool.join()` or `pool.map()` calls
- Signal handler sets a flag but nothing responds until entire batch completes
- Progress bars continue updating but program won't terminate

**Phase to address:**
Phase 1 (Signal Handler Infrastructure) — establish non-blocking patterns before building campaign menu

---

### Pitfall 2: Workers Inherit SIGINT and Terminate Prematurely

**What goes wrong:**
By default, worker processes in the same process group receive the SIGINT signal when Ctrl+C is pressed. If workers don't ignore the signal, they terminate immediately with `KeyboardInterrupt`, corrupting in-flight work, leaving incomplete checkpoint writes, and potentially causing the main process to hang waiting for results that will never arrive.

**Why it happens:**
Child processes are part of the same process group as the main process on Windows, so they receive Ctrl+C signals directly from the console. Python's default SIGINT handler raises `KeyboardInterrupt`, which terminates the worker before it can finish processing the current PDF or report back to the pool.

**How to avoid:**
1. **Ignore SIGINT in worker initialization**:
   ```python
   import signal

   def init_worker():
       signal.signal(signal.SIGINT, signal.SIG_IGN)

   pool = multiprocessing.Pool(
       processes=cpu_count() - 1,
       initializer=init_worker
   )
   ```

2. **Let only the main process handle Ctrl+C**: With workers ignoring SIGINT, the main process signal handler sets a flag, workers check the flag periodically, and cleanup happens in controlled shutdown sequence.

3. **Use multiprocessing.Event for shutdown coordination**:
   ```python
   shutdown_event = multiprocessing.Event()

   def worker(pdf_path, shutdown_event):
       if shutdown_event.is_set():
           return None  # Skip this work
       # ... process PDF ...

   def signal_handler(sig, frame):
       shutdown_event.set()
       print("\nShutdown requested, finishing current files...")
   ```

**Warning signs:**
- Workers terminate mid-PDF leaving partial results
- Checkpoint file contains only half the expected data
- `BrokenProcessPool` or `TerminatedWorkerError` exceptions
- Main process hangs after Ctrl+C because workers died without reporting

**Phase to address:**
Phase 1 (Signal Handler Infrastructure) — must be implemented before any Ctrl+C handling

---

### Pitfall 3: Pool Cleanup Order Causes Deadlock or Corruption

**What goes wrong:**
Calling `pool.terminate()` before draining result iterators (from `imap()`, `imap_unordered()`, or pending `apply_async` results) can cause deadlock or queue corruption. Workers may be killed while holding locks or writing to queues, leaving the main process blocked trying to read results that will never arrive. Conversely, calling `pool.join()` without first calling `pool.close()` hangs indefinitely if workers are still accepting new tasks.

**Why it happens:**
The multiprocessing documentation warns: "If this method is used when the associated process is using a pipe or queue then the pipe or queue is liable to become corrupted and may become unusable by other process." Abrupt termination with `terminate()` doesn't allow workers to flush buffers, release locks, or signal completion. The result queue can fill up, blocking workers from returning, while the main thread waits on `terminate()` to complete.

**How to avoid:**
1. **Follow strict cleanup sequence**:
   ```python
   # CORRECT ORDER:
   pool.close()              # 1. Prevent new tasks
   pool.join(timeout=30)     # 2. Wait for workers (with timeout)
   if pool._pool:            # 3. Check if workers finished
       pool.terminate()      # 4. Force kill if timeout
       pool.join()           # 5. Wait for termination
   ```

2. **Always drain iterators before cleanup**:
   ```python
   results = []
   try:
       for result in pool.imap_unordered(func, items):
           results.append(result)
   except KeyboardInterrupt:
       pass  # Allow iterator to exit cleanly
   finally:
       pool.close()
       pool.join(timeout=10)
       if pool._pool:
           pool.terminate()
           pool.join()
   ```

3. **Use context manager for automatic cleanup**:
   ```python
   with multiprocessing.Pool(processes=N, initializer=init_worker) as pool:
       results = list(pool.imap_unordered(func, items))
   # close() and join() called automatically
   ```

**Warning signs:**
- Program hangs indefinitely on exit after Ctrl+C
- `RuntimeError: Queue objects should only be shared between processes through inheritance` messages
- Workers show as "zombie" processes in Task Manager
- tqdm progress bar freezes but processes still running

**Phase to address:**
Phase 1 (Signal Handler Infrastructure) — establish proper cleanup patterns from the start

---

### Pitfall 4: Checkpoint Corruption from Concurrent Writes or Missing fsync

**What goes wrong:**
On Windows, `os.replace()` is "usually" atomic but can silently fall back to non-atomic `CopyFile` in some cases. Without `flush()` + `fsync()` before calling `os.replace()`, data may still be in kernel buffers when the checkpoint file is moved, resulting in incomplete or corrupted checkpoint data after a crash. Additionally, if multiple workers or the main thread try to update the checkpoint concurrently, race conditions can corrupt the state file.

**Why it happens:**
Windows' `MoveFileEx` operation (used by `os.replace()`) guarantees atomicity only when source and destination are on the same volume and meet other conditions. Python's `flush()` only flushes to the OS buffer, not to physical disk. Multiprocessing with the `spawn` method creates truly separate processes that can simultaneously attempt checkpoint writes if not coordinated.

**How to avoid:**
1. **Ensure atomic writes with fsync on Windows**:
   ```python
   import os
   import tempfile
   from pathlib import Path

   def atomic_write_checkpoint(checkpoint_path, data):
       checkpoint_dir = checkpoint_path.parent
       with tempfile.NamedTemporaryFile(
           mode='w',
           dir=checkpoint_dir,  # Same filesystem as target
           delete=False,
           suffix='.tmp'
       ) as tmp_file:
           json.dump(data, tmp_file, indent=2)
           tmp_file.flush()
           os.fsync(tmp_file.fileno())  # CRITICAL on Windows
           tmp_path = Path(tmp_file.name)

       # Atomic replace (mostly atomic on Windows)
       os.replace(tmp_path, checkpoint_path)

       # Sync directory metadata (POSIX only, no-op on Windows)
       try:
           dir_fd = os.open(checkpoint_dir, os.O_RDONLY)
           os.fsync(dir_fd)
           os.close(dir_fd)
       except (OSError, AttributeError):
           pass  # Windows doesn't support directory fsync
   ```

2. **Centralize checkpoint writes in main process only**:
   ```python
   # GOOD: Workers return results, main process updates checkpoint
   def main():
       for result in pool.imap_unordered(process_pdf, pdfs):
           state['processed'].append(result['filename'])
           atomic_write_checkpoint(checkpoint_path, state)

   # BAD: Workers directly write to checkpoint (race condition)
   def worker(pdf_path, checkpoint_path):  # DANGEROUS
       result = process_pdf(pdf_path)
       update_checkpoint(checkpoint_path, result)  # RACE!
   ```

3. **Use file locks if workers must write**:
   ```python
   from filelock import FileLock

   lock_path = checkpoint_path.with_suffix('.lock')
   with FileLock(lock_path, timeout=10):
       state = load_checkpoint(checkpoint_path)
       state['processed'].append(pdf_filename)
       atomic_write_checkpoint(checkpoint_path, state)
   ```

**Warning signs:**
- Checkpoint file has `{}` or partial JSON after crash
- Resume skips files or processes duplicates
- `PermissionError` or `FileNotFoundError` on checkpoint reads
- Checkpoint file exists but `json.load()` raises `JSONDecodeError`

**Phase to address:**
Phase 1 (Signal Handler Infrastructure) — verify checkpoint atomicity before adding campaign state complexity

---

### Pitfall 5: imap/imap_unordered Deadlock on Generator Exceptions (Python <3.5)

**What goes wrong:**
When `pool.imap()` or `pool.imap_unordered()` receive a generator that raises an exception during iteration, the `_task_handler` thread dies without notifying worker threads or the main thread. This causes the application to hang indefinitely, with workers waiting for tasks and the main thread waiting for results that will never arrive.

**Why it happens:**
Prior to Python 3.5, exceptions from the iterator passed to `imap()` weren't properly handled. The `_task_handler` thread would crash without cleanup, leaving workers blocked on empty queues and the main thread blocked on result iteration.

**How to avoid:**
1. **Upgrade to Python 3.5+**: The issue was fixed in March 2015. If running Python 3.4 or earlier, upgrade immediately.

2. **Wrap generator in exception handler**:
   ```python
   def safe_pdf_generator(pdf_dir):
       try:
           for pdf_path in Path(pdf_dir).rglob("*.pdf"):
               yield pdf_path
       except Exception as e:
           logging.error(f"Generator failed: {e}")
           return  # Clean exit instead of exception

   # Use with imap_unordered
   for result in pool.imap_unordered(process_pdf, safe_pdf_generator(pdf_dir)):
       ...
   ```

3. **Use list instead of generator if uncertain**:
   ```python
   # SAFE: Pre-compute list before passing to pool
   pdf_files = list(Path(pdf_dir).rglob("*.pdf"))
   for result in pool.imap_unordered(process_pdf, pdf_files):
       ...
   ```

4. **Add timeout to detect hangs**:
   ```python
   it = pool.imap_unordered(process_pdf, pdf_generator())
   while True:
       try:
           result = it.next(timeout=60)  # 60s timeout
       except StopIteration:
           break
       except multiprocessing.TimeoutError:
           logging.error("Pool appears hung, no results in 60s")
           break
   ```

**Warning signs:**
- Progress bar stops updating mid-batch
- Workers show CPU usage but no results produced
- `pool.join()` never returns
- No exceptions raised but program doesn't terminate

**Phase to address:**
Phase 2 (Interactive Campaign Menu) — ensure generator safety before adding resume-from-failure logic that relies on robust iteration

---

### Pitfall 6: Shared Manager Objects Create Performance Bottleneck

**What goes wrong:**
Using `multiprocessing.Manager()` to share dictionaries, counters, or statistics across workers introduces massive overhead because every read and write requires inter-process communication (IPC) with the manager process. This serializes access and can reduce parallel performance by 10-100x compared to local aggregation patterns.

**Why it happens:**
Manager proxies don't share memory directly; they send messages to a separate manager process that holds the actual data. Each `stats['processed'] += 1` involves: (1) serialize request, (2) IPC to manager, (3) manager updates, (4) IPC back to worker, (5) deserialize response. High-frequency updates create an IPC storm.

**How to avoid:**
1. **Use local counters, aggregate at end**:
   ```python
   def process_pdf_batch(pdf_paths):
       """Each worker maintains local stats"""
       local_stats = {'processed': 0, 'failed': 0, 'ids_found': 0}
       results = []

       for pdf_path in pdf_paths:
           result = process_single_pdf(pdf_path)
           results.append(result)
           local_stats['processed'] += 1
           if result['success']:
               local_stats['ids_found'] += len(result['ids'])
           else:
               local_stats['failed'] += 1

       return {'results': results, 'stats': local_stats}

   # Main process aggregates
   total_stats = {'processed': 0, 'failed': 0, 'ids_found': 0}
   for batch_result in pool.imap_unordered(process_pdf_batch, batches):
       for key in total_stats:
           total_stats[key] += batch_result['stats'][key]
   ```

2. **Use Queue for periodic updates instead of Manager**:
   ```python
   stats_queue = multiprocessing.Queue()

   def worker(pdf_path, stats_queue):
       result = process_pdf(pdf_path)
       stats_queue.put({
           'type': 'completion',
           'success': result['success'],
           'ids_found': len(result['ids'])
       })
       return result

   # Main process aggregates from queue
   def update_stats_from_queue(stats_queue, total_stats):
       while not stats_queue.empty():
           try:
               update = stats_queue.get_nowait()
               total_stats['processed'] += 1
               if update['success']:
                   total_stats['ids_found'] += update['ids_found']
               else:
                   total_stats['failed'] += 1
           except queue.Empty:
               break
   ```

3. **Avoid Manager unless truly needed**:
   ```python
   # BAD: High overhead for simple counter
   manager = multiprocessing.Manager()
   shared_stats = manager.dict({'processed': 0})

   def worker(pdf):
       result = process_pdf(pdf)
       shared_stats['processed'] += 1  # IPC on every PDF!
       return result

   # GOOD: Return stats with result
   def worker(pdf):
       result = process_pdf(pdf)
       return {'pdf': pdf, 'result': result, 'stats': 1}
   ```

**Warning signs:**
- Pool performance degrades as worker count increases (should improve)
- High CPU usage in main process or manager process, low in workers
- `htop` shows workers blocked on IPC calls
- Processing 30K PDFs takes hours instead of minutes

**Phase to address:**
Phase 3 (Statistics Tracking) — design stats collection architecture to avoid Manager antipattern

---

### Pitfall 7: tqdm Progress Bars Leak or Corrupt on Pool Termination

**What goes wrong:**
When a multiprocessing Pool is terminated abruptly (via `terminate()` or Ctrl+C without proper cleanup), tqdm progress bars may not close cleanly, leaving terminal formatting corrupted (missing newlines, cursor in wrong position, ANSI codes visible). Additionally, using tqdm with `pool.imap()` without proper cleanup can leak file descriptors or leave progress bar processes running as zombies.

**Why it happens:**
tqdm's multiprocessing support relies on proper cleanup sequences. Calling `pool.terminate()` kills worker processes before they can call `tqdm.close()`, leaving terminal state dirty. The tqdm-multiprocess library spawns additional processes for progress bars that must be explicitly closed.

**How to avoid:**
1. **Always close tqdm before pool termination**:
   ```python
   from tqdm import tqdm

   pbar = None
   try:
       pbar = tqdm(total=len(pdf_files), desc="Processing PDFs")
       for result in pool.imap_unordered(process_pdf, pdf_files):
           pbar.update(1)
   finally:
       if pbar:
           pbar.close()  # CRITICAL: Close before pool cleanup
       pool.close()
       pool.join(timeout=10)
   ```

2. **Use tqdm context manager**:
   ```python
   with tqdm(total=len(pdf_files)) as pbar:
       for result in pool.imap_unordered(process_pdf, pdf_files):
           pbar.update(1)
   # tqdm.close() called automatically
   ```

3. **Handle Ctrl+C in tqdm loop**:
   ```python
   pbar = tqdm(total=len(pdf_files))
   try:
       for result in pool.imap_unordered(process_pdf, pdf_files):
           pbar.update(1)
   except KeyboardInterrupt:
       pbar.write("\nShutdown requested, cleaning up...")
   finally:
       pbar.close()
       # ... pool cleanup ...
   ```

4. **If using tqdm-multiprocess, call shutdown explicitly**:
   ```python
   from tqdm_multiprocess import TqdmMultiProcessPool

   pool = TqdmMultiProcessPool()
   try:
       # ... work ...
   finally:
       pool.shutdown()  # Cleans up progress bar processes
   ```

**Warning signs:**
- Terminal shows `^C` characters or ANSI codes after Ctrl+C
- Cursor positioned in middle of screen after program exits
- Progress bar remains visible after program terminates
- Need to run `reset` command to fix terminal
- Zombie processes with `tqdm` in command name

**Phase to address:**
Phase 2 (Interactive Campaign Menu) — ensure tqdm cleanup works before adding more interactive elements

---

### Pitfall 8: Windows Signal Limitations Break Cross-Platform Code

**What goes wrong:**
Code that works on Linux with signals like `SIGUSR1`, `SIGTERM`, `SIGHUP` fails on Windows with `ValueError: signal number out of range`. Windows only supports `SIGABRT`, `SIGFPE`, `SIGILL`, `SIGINT`, `SIGSEGV`, `SIGTERM`, and `SIGBREAK`. Additionally, on Windows, processes receive `SIGBREAK` (Ctrl+Break) instead of POSIX signals for console control events.

**Why it happens:**
Windows is not POSIX-compliant and implements only a subset of signals. Most POSIX signals (SIGUSR1, SIGHUP, SIGPIPE, etc.) don't exist on Windows. Signal delivery mechanisms differ fundamentally between Windows console control events and POSIX signals.

**How to avoid:**
1. **Stick to cross-platform signals**:
   ```python
   import signal
   import sys

   def setup_signal_handlers():
       signal.signal(signal.SIGINT, handle_shutdown)
       signal.signal(signal.SIGTERM, handle_shutdown)

       # Windows-specific: SIGBREAK (Ctrl+Break)
       if sys.platform == 'win32':
           signal.signal(signal.SIGBREAK, handle_shutdown)

       # DON'T: SIGUSR1 doesn't exist on Windows
       # signal.signal(signal.SIGUSR1, handle_reload)  # ValueError on Windows!
   ```

2. **Use multiprocessing.Event instead of signals for worker coordination**:
   ```python
   # GOOD: Cross-platform shutdown coordination
   shutdown_event = multiprocessing.Event()

   def worker(pdf_path, shutdown_event):
       if shutdown_event.is_set():
           return None
       # ... process ...

   def handle_ctrl_c(sig, frame):
       shutdown_event.set()
   ```

3. **Document platform-specific behavior**:
   ```python
   def graceful_shutdown():
       """
       Initiate graceful shutdown.

       On Windows: Triggered by Ctrl+C (SIGINT) or Ctrl+Break (SIGBREAK)
       On POSIX: Triggered by SIGINT or SIGTERM
       """
       shutdown_event.set()
   ```

**Warning signs:**
- Code works on Linux/Mac but crashes on Windows with signal errors
- `ValueError: signal number out of range` exceptions
- Signal handlers registered but never called on Windows
- Ctrl+Break behaves differently than Ctrl+C

**Phase to address:**
Phase 1 (Signal Handler Infrastructure) — verify Windows compatibility immediately

---

### Pitfall 9: Interactive Menu Blocks Signal Handling During input()

**What goes wrong:**
When the main thread is blocked on `input("Select option: ")`, it cannot process signals, making the program unresponsive to Ctrl+C. Users pressing Ctrl+C during the menu prompt see no response, leading to force-kill via Task Manager. This is especially problematic if workers are running in the background during menu display.

**Why it happens:**
Python's `input()` is a blocking syscall that doesn't return until Enter is pressed. Signal handlers execute in the main thread, but only when the thread is executing Python bytecode or at specific interruption points. The `input()` syscall doesn't provide these interruption points on Windows.

**How to avoid:**
1. **Don't run interactive menu while workers are active**:
   ```python
   # GOOD: Menu appears only when pool is idle
   def main():
       while True:
           # Show menu
           choice = input("Select: [1] Start [2] Stats [3] Quit: ")

           if choice == '1':
               run_campaign()  # Blocks until complete or Ctrl+C
           elif choice == '2':
               show_stats()
           elif choice == '3':
               break

   # BAD: Menu while workers running
   def main():
       pool.map_async(process_pdf, pdfs)  # Workers running!
       choice = input("Select option: ")  # Can't Ctrl+C here
   ```

2. **Use timeout-based input alternative for active campaigns**:
   ```python
   import sys
   import select

   def input_with_timeout(prompt, timeout=1.0):
       """
       Input with timeout - allows periodic signal checking.
       Note: select.select doesn't work with stdin on Windows.
       Windows alternative uses msvcrt.
       """
       if sys.platform == 'win32':
           import msvcrt
           print(prompt, end='', flush=True)
           chars = []
           while True:
               if msvcrt.kbhit():
                   char = msvcrt.getwche()
                   if char == '\r':  # Enter
                       print()
                       return ''.join(chars)
                   chars.append(char)
               time.sleep(0.1)  # Allow signal processing
       else:
           print(prompt, end='', flush=True)
           ready, _, _ = select.select([sys.stdin], [], [], timeout)
           if ready:
               return sys.stdin.readline().strip()
           return None
   ```

3. **Show live status instead of blocking menu during processing**:
   ```python
   # GOOD: Status updates + Ctrl+C to interrupt
   def run_campaign(pdf_files):
       print("Processing PDFs... Press Ctrl+C to stop")
       print("Current progress: [shown via tqdm]")

       for result in pool.imap_unordered(process_pdf, pdf_files):
           # ... updates ...
           # Ctrl+C caught in signal handler, sets shutdown_event

       print("\nCampaign complete. Returning to menu...")
   ```

**Warning signs:**
- Ctrl+C during menu does nothing
- Users report program "freezes" at menu
- Need Task Manager to kill program
- Workers running but can't interrupt from menu

**Phase to address:**
Phase 2 (Interactive Campaign Menu) — design menu flow to avoid blocking during active work

---

### Pitfall 10: Per-Folder Statistics Require Directory Handle Management

**What goes wrong:**
Tracking statistics per directory requires mapping results back to their source folders, which breaks if PDF paths are stored as strings (path separators differ on Windows), if relative paths are used (breaks when current directory changes), or if path normalization is inconsistent (e.g., `C:\Folder` vs `C:\folder` vs `C:\FOLDER` treated as different on case-insensitive Windows).

**Why it happens:**
Windows file paths are case-insensitive but case-preserving. String comparisons are case-sensitive, so `Path("C:\\PDFs")` and `Path("C:\\pdfs")` create different dictionary keys even though they refer to the same directory. Workers may resolve paths differently based on their working directory.

**How to avoid:**
1. **Use pathlib.Path with resolved absolute paths**:
   ```python
   from pathlib import Path

   def normalize_path(path):
       """Consistent path representation for Windows."""
       return Path(path).resolve()  # Absolute + normalized

   # Track by normalized path
   folder_stats = {}
   pdf_path = normalize_path(pdf_filename)
   folder_key = str(pdf_path.parent)  # Use string of normalized path

   if folder_key not in folder_stats:
       folder_stats[folder_key] = {'processed': 0, 'failed': 0}
   folder_stats[folder_key]['processed'] += 1
   ```

2. **Normalize paths at data collection boundary**:
   ```python
   def process_pdf(pdf_path):
       """Worker returns normalized paths."""
       pdf_path = Path(pdf_path).resolve()
       result = {
           'pdf': str(pdf_path),  # Full absolute path
           'folder': str(pdf_path.parent),  # Normalized folder
           'success': True,
           # ... other fields ...
       }
       return result

   # Main process aggregates by folder
   for result in pool.imap_unordered(process_pdf, pdf_files):
       folder = result['folder']
       folder_stats[folder]['processed'] += 1
   ```

3. **Handle case-insensitive lookups on Windows**:
   ```python
   from collections import defaultdict
   import sys

   class CaseInsensitiveDict(dict):
       """Dictionary with case-insensitive keys on Windows."""
       def __init__(self):
           super().__init__()
           self._case_map = {}  # lowercase -> original case

       def __setitem__(self, key, value):
           key_lower = key.lower() if sys.platform == 'win32' else key
           self._case_map[key_lower] = key
           super().__setitem__(self._case_map[key_lower], value)

       def __getitem__(self, key):
           key_lower = key.lower() if sys.platform == 'win32' else key
           canonical_key = self._case_map.get(key_lower, key)
           return super().__getitem__(canonical_key)

   folder_stats = CaseInsensitiveDict()
   ```

4. **Store relative paths from campaign root for portability**:
   ```python
   campaign_root = Path(pdf_directory).resolve()

   def get_relative_folder(pdf_path, campaign_root):
       """Get folder relative to campaign root."""
       pdf_path = Path(pdf_path).resolve()
       folder = pdf_path.parent
       try:
           rel_folder = folder.relative_to(campaign_root)
           return str(rel_folder)
       except ValueError:
           # PDF outside campaign root
           return str(folder)
   ```

**Warning signs:**
- Same folder appears multiple times in stats with different counts
- Stats show `C:\PDFs` and `C:\pdfs` as separate folders
- Relative path stats break after resume from checkpoint
- Folder counts don't sum to total file count

**Phase to address:**
Phase 3 (Statistics Tracking) — establish path normalization before collecting per-folder stats

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip `fsync()` in checkpoint writes | Slightly faster writes | Checkpoint corruption after crash/power loss | NEVER — data loss unacceptable at 30K+ file scale |
| Use `pool.terminate()` on Ctrl+C | Immediate shutdown | Queue corruption, zombie processes, checkpoint loss | NEVER — use `close()` + `join(timeout)` + `terminate()` fallback |
| Use Manager for shared statistics | Simpler code | 10-100x performance penalty | Only if stats updated < 100 times total |
| Block on `input()` during processing | Standard Python pattern | Program unresponsive to Ctrl+C | Only when workers fully idle |
| Store paths as strings | Works initially | Case-sensitivity bugs on Windows | Only for display, never for dictionary keys |
| Use `signal.SIGUSR1` for reload | Common POSIX pattern | Crashes on Windows | NEVER on cross-platform code |
| Skip worker signal ignoring | Works on Linux | Workers terminate prematurely on Ctrl+C (Windows) | NEVER on Windows |
| Pass generators to `imap()` in Python 3.4 | Memory efficient | Deadlock on exception | NEVER — upgrade to 3.5+ or use lists |

## Integration Gotchas

Common mistakes when integrating components.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **tqdm + multiprocessing** | Use `pool.map()` and update tqdm in workers | Use `pool.imap_unordered()` in main thread, update tqdm on each result |
| **Signal handlers + Pool** | Register handler before creating pool | Create pool first, then register handlers (pool workers inherit handlers) |
| **Checkpoints + multiprocessing** | Workers write checkpoint concurrently | Only main process writes checkpoint; workers return results |
| **Event + Pool workers** | Pass Event as function argument | Pass Event in Pool initializer or use global + init |
| **pathlib + Windows** | Use string concatenation `"C:\\" + folder` | Use `Path("C:\\") / folder` for cross-platform safety |
| **Ctrl+C + input()** | Assume input() is interruptible | Use non-blocking alternatives or ensure workers idle during input |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Manager for per-PDF stats** | Processing slows to crawl as PDF count grows | Use local stats + aggregation | > 1000 PDFs with stats updates |
| **Synchronous checkpoint writes** | Each result write blocks for 10-50ms | Batch checkpoint writes (every 100 PDFs or 30s) | > 10K PDFs |
| **Blocking `pool.map()`** | Can't interrupt, no progress visibility | Use `imap_unordered()` with tqdm | Always (lack of interactivity) |
| **Single-threaded resume validation** | Resume startup slow on large checkpoints | Validate checkpoint schema only, not every path | > 5K PDFs in checkpoint |
| **Print to stdout in workers** | Corrupts tqdm output, slows pool | Use `tqdm.write()` or logging to file | > 10 workers |
| **Creating new Pool per campaign action** | 5-10s startup per action (spawn overhead on Windows) | Reuse pool across actions when possible | > 4 workers on Windows |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **No feedback during Ctrl+C cleanup** | User thinks program frozen, force-kills | Print "Finishing current files, please wait..." immediately on SIGINT |
| **tqdm bar corruption after Ctrl+C** | Terminal unusable without `reset` command | Always call `tqdm.close()` in finally block |
| **Menu appears before workers fully stopped** | Selecting option while workers running causes errors | Wait for `pool.join()` completion before showing menu |
| **No ETA for graceful shutdown** | User doesn't know if waiting seconds or hours | Show "N files remaining, ~MM:SS left" during shutdown |
| **Statistics update only at end** | No progress indication for hours-long runs | Update stats every 100 PDFs or 30s |
| **Checkpoint resume doesn't show what's skipped** | User unsure if resume worked | Print "Resuming: X/Y PDFs already processed" on startup |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Graceful Shutdown:** Works with Ctrl+C, but tested with Ctrl+Break on Windows? (SIGBREAK may behave differently)
- [ ] **Checkpoint Atomicity:** Uses `tempfile` + `os.replace()`, but calls `fsync()` before replace? (Prevents corruption)
- [ ] **Signal Handler:** Registered handler, but workers ignore SIGINT with `signal.SIG_IGN`? (Prevents premature termination)
- [ ] **Pool Cleanup:** Calls `pool.close()` and `pool.join()`, but drains iterators first? (Prevents deadlock)
- [ ] **tqdm Progress:** Shows progress bar, but closes it in finally block? (Prevents terminal corruption)
- [ ] **Per-Folder Stats:** Tracks by folder, but normalizes paths with `Path.resolve()`? (Prevents duplicate entries on Windows)
- [ ] **Interactive Menu:** Shows menu, but only when workers fully idle? (Prevents input() blocking Ctrl+C)
- [ ] **Campaign Resume:** Loads checkpoint, but validates schema version? (Prevents crashes on checkpoint format changes)
- [ ] **Statistics Aggregation:** Collects stats, but uses local counters not Manager? (Prevents performance degradation)
- [ ] **Error Handling:** Catches exceptions, but logs to file not stdout? (Prevents tqdm corruption)

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **Corrupted Checkpoint** | MEDIUM | Delete checkpoint file, re-run campaign from start (or last known good checkpoint backup) |
| **Zombie Worker Processes** | LOW | Kill zombies: `taskkill /F /IM python.exe` (Windows) or `pkill -9 python` (POSIX) |
| **Terminal Corruption from tqdm** | LOW | Run `reset` command (POSIX) or close/reopen terminal (Windows) |
| **Pool Deadlock** | LOW | Force quit with Ctrl+Break (Windows) or Ctrl+\\ (POSIX), check for iterator draining |
| **Manager Performance Bottleneck** | HIGH | Refactor to local stats + aggregation pattern (code changes required) |
| **Signal Handler Not Responding** | MEDIUM | Refactor to use `imap_unordered()` with timeout instead of blocking `map()` |
| **Workers Not Ignoring SIGINT** | MEDIUM | Add `initializer=init_worker` to Pool constructor with `signal.SIG_IGN` |
| **Case-Sensitive Folder Stats** | MEDIUM | Normalize existing stats by converting keys to lowercase, merge duplicates |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Signal handlers main-thread only | Phase 1: Signal Handler Infrastructure | Manual test: Start pool.map(), press Ctrl+C during processing, verify responds within 1s |
| Workers inherit SIGINT | Phase 1: Signal Handler Infrastructure | Manual test: Ctrl+C during processing, verify workers finish current file before stopping |
| Pool cleanup order deadlock | Phase 1: Signal Handler Infrastructure | Automated test: Ctrl+C during imap_unordered, verify no zombie processes afterward |
| Checkpoint corruption | Phase 1: Signal Handler Infrastructure | Automated test: Kill process mid-write, verify checkpoint still valid JSON |
| imap generator deadlock | Phase 2: Interactive Campaign Menu | Automated test: Pass failing generator to imap_unordered, verify timeout detection |
| Manager performance bottleneck | Phase 3: Statistics Tracking | Performance test: Process 1000 PDFs, verify throughput > 10 PDFs/sec/worker |
| tqdm progress bar leaks | Phase 2: Interactive Campaign Menu | Manual test: Ctrl+C during progress, verify terminal formatting clean afterward |
| Windows signal limitations | Phase 1: Signal Handler Infrastructure | Automated test: Run on Windows, verify no ValueError on signal registration |
| input() blocks signals | Phase 2: Interactive Campaign Menu | Manual test: Show menu with workers running, verify Ctrl+C works |
| Per-folder stats path issues | Phase 3: Statistics Tracking | Automated test: Process PDFs in `C:\Test` and `C:\test`, verify single folder key |

## Sources

### Official Documentation
- [Python multiprocessing — Process-based parallelism](https://docs.python.org/3/library/multiprocessing.html)
- [Python signal — Set handlers for asynchronous events](https://docs.python.org/3/library/signal.html)

### Signal Handling with Multiprocessing
- [Python Keyboard Interrupt Handling with Multiprocessing – Maxence BOBIN](https://bobin.iiens.net/python-keyboard-interrupt-handling-with-multiprocessing/)
- [Handling SIGINT in multiprocessing on Windows - Python Help - Discussions](https://discuss.python.org/t/handling-sigint-in-multiprocessing-on-windows/90064)
- [Handling SIGTERM in python on Windows - Marc-Antoine Ruel](https://maruel.ca/post/python_windows_signal/)
- [Python Multiprocessing graceful shutdown in the proper order | peterspython.com](https://www.peterspython.com/en/blog/python-multiprocessing-graceful-shutdown-in-the-proper-order)
- [Python Multiprocessing and KeyboardInterrupt - Bryce Boe](https://bryceboe.com/2010/08/26/python-multiprocessing-and-keyboardinterrupt/)
- [Python: Using KeyboardInterrupt with a Multiprocessing Pool - Amethyst Reese](https://noswap.com/blog/python-multiprocessing-keyboardinterrupt)

### Pool Cleanup and Shutdown
- [Graceful exit with Python multiprocessing | The-Fonz blog](https://the-fonz.gitlab.io/posts/python-multiprocessing/)
- [Graceful vs. Forceful: Mastering Python's Pool Termination](https://runebook.dev/en/docs/python/library/multiprocessing/multiprocessing.pool.Pool.terminate)
- [Shutdown the Multiprocessing Pool in Python – SuperFastPython](https://superfastpython.com/shutdown-the-multiprocessing-pool-in-python/)
- [Python Multiprocessing Pool: How to Handle KeyboardInterrupt](https://www.pythontutorials.net/blog/keyboard-interrupts-with-python-s-multiprocessing-pool/)

### Checkpoint and File Corruption
- [Safely and atomically write to a file « Python recipes « ActiveState Code](https://code.activestate.com/recipes/579097-safely-and-atomically-write-to-a-file/)
- [PSA: Avoid Data Corruption by Syncing to the Disk - ELL Blog](https://blog.elijahlopez.ca/posts/data-corruption-atomic-writing/)
- [Python os.replace Function - Complete Guide](https://zetcode.com/python/os-replace/)
- [Avoiding File Conflicts in Multithreaded Python Programs | by Aman Deep | Medium](https://medium.com/@aman.deep291098/avoiding-file-conflicts-in-multithreaded-python-programs-34f2888f4521)

### Known Issues and Bugs
- [Issue 23051: multiprocessing.pool methods imap()/imap_unordered() deadlock - Python tracker](https://bugs.python.org/issue23051)
- [Issue 38263: [Windows] multiprocessing: DupHandle.detach() race condition - Python tracker](https://bugs.python.org/issue38263)
- [Issue 35629: hang and/or leaked processes with multiprocessing.Pool().imap() - Python tracker](https://bugs.python.org/issue35629)

### Progress Bars and tqdm
- [Progress Bars for Python Multiprocessing Tasks - Lei Mao's Log Book](https://leimao.github.io/blog/Python-tqdm-Multiprocessing/)
- [tqdm-multiprocess · PyPI](https://pypi.org/project/tqdm-multiprocess/)
- [Running tqdm with Python multiprocessing | Redowan's Reflections](https://rednafi.com/python/tqdm-with-multiprocessing/)

### Shared State and Statistics
- [Advanced Shared State Management in Python Multiprocessing](https://hevalhazalkurt.com/blog/advanced-shared-state-management-in-python-multiprocessing/)
- [Shared counter implementation in Python multiprocessing](https://copyprogramming.com/howto/python-multiprocessing-and-a-shared-counter)
- [Python Multiprocessing Queue: A Comprehensive Guide - CodeRivers](https://coderivers.org/blog/python-multiprocessing-queue/)
- [Multiprocessing Queue in Python – SuperFastPython](https://superfastpython.com/multiprocessing-queue-in-python/)

---
*Pitfalls research for: Campaign Management + Multiprocessing OCR Pipeline (Windows 10)*
*Researched: 2026-06-05*
*Confidence: HIGH — Verified with official documentation, known bug reports, and community best practices*
