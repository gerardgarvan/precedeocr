# Domain Pitfalls: Batch PDF OCR ID Extraction

**Domain:** Batch OCR/PDF processing for ID extraction (30K+ PDFs, Windows environment)
**Researched:** 2026-06-04
**Confidence:** HIGH (official docs + multiple verified sources)

## Critical Pitfalls

Mistakes that cause rewrites, silent data loss, or project failure.

---

### Pitfall 1: Memory Exhaustion from pdf2image Without Output Folders

**What goes wrong:** Processing large PDFs or running batches without an output folder loads all converted images into RAM, causing the process to be killed by the OS when memory is exhausted. At 30K+ PDFs, this leads to crashes mid-batch with no results.

**Why it happens:** pdf2image's default behavior converts PDF pages to PIL Image objects held in memory. With multi-page PDFs, memory consumption compounds quickly. Each page at 300 DPI can consume 10-50MB in memory.

**Consequences:**
- Process killed by OS (out of memory)
- No partial results saved
- Must restart from beginning
- Silent failures if not monitored

**Prevention:**
```python
# WRONG: Default behavior loads all into RAM
images = convert_from_path('document.pdf')

# CORRECT: Use output folder to write to disk
images = convert_from_path(
    'document.pdf',
    output_folder='/tmp/pdf_pages',
    paths_only=True  # Returns paths, not Image objects
)
```

**Additional safeguards:**
- Use `paths_only=True` parameter to return file paths instead of Image objects
- Process PDFs in chunks if they have 200+ pages (memory error threshold)
- Clean up temporary files after processing each PDF
- Monitor memory usage and implement circuit breakers

**Detection:** Process memory growing unbounded, eventual crash with OS memory error, temp directory size exploding.

**Phase mapping:** Phase 1 (PDF to Image Conversion) must address this immediately.

**Sources:**
- [pdf2image GitHub - Memory Management](https://github.com/Belval/pdf2image)
- [pdf2image PyPI Documentation](https://pypi.org/project/pdf2image/)

---

### Pitfall 2: Windows Multiprocessing Spawn Overhead with Large Pickle Objects

**What goes wrong:** On Windows, multiprocessing uses "spawn" (not "fork"), requiring all data to be pickled and sent to child processes. Passing large objects (images, configuration dictionaries, Tesseract instances) creates massive performance bottlenecks - up to 10x slower when pickle size exceeds 64KB.

**Why it happens:** Windows doesn't support fork(), so Python creates entirely new processes and must serialize/deserialize all data via pickle over pipes. This overhead is hidden in Unix systems that use fork() with copy-on-write memory.

**Consequences:**
- Multiprocessing runs slower than single-threaded processing
- Memory usage multiplies across all worker processes
- "Parallelization" adds no speed benefit or makes things worse
- Wasted CPU resources waiting on pickle/unpickle

**Prevention:**
```python
# WRONG: Passing large objects to workers
def process_pdf(pdf_path, tesseract_config, preprocessing_params):
    # tesseract_config and preprocessing_params get pickled for EACH task
    pass

with Pool(4) as pool:
    pool.map(process_pdf, [(p, config, params) for p in pdf_paths])

# CORRECT: Use initializer to load heavy objects once per worker
def worker_init():
    global tesseract_config
    tesseract_config = load_tesseract_config()

def process_pdf(pdf_path):
    # Uses global tesseract_config loaded once per worker
    pass

with Pool(4, initializer=worker_init) as pool:
    pool.map(process_pdf, pdf_paths)
```

**Additional safeguards:**
- Pass file paths, not file contents or Image objects
- Use worker initialization for heavy configuration
- Set `os.environ["OMP_THREAD_LIMIT"] = "1"` for pytesseract to prevent thread multiplication
- Limit pool size to CPU count (not more) to avoid context switching

**Detection:** Multiprocessing slower than expected, high CPU usage during "idle" periods between tasks, large memory footprint per worker process.

**Phase mapping:** Phase 4 (Parallelization) must design around this constraint from the start.

**Sources:**
- [Python Multiprocessing Fork vs Spawn Performance](https://medium.com/@Nexumo_/python-multiprocessing-revisited-fork-vs-spawn-5b9216fd5710)
- [Python's Multiprocessing Performance Problem](https://pythonspeed.com/articles/faster-multiprocessing-pickle/)
- [POSIX multiprocessing spawn performance issue](https://github.com/python/cpython/issues/96953)

---

### Pitfall 3: File Handle Leaks Leading to Resource Exhaustion

**What goes wrong:** Opening PDFs, images, or output files without explicit closure causes file handles to accumulate. Windows has a per-process handle limit; exceeding it causes "Too many open files" errors, preventing new files from being opened or processed.

**Why it happens:** Python's garbage collector doesn't immediately close file handles. In tight loops processing 30K+ files, handles accumulate faster than GC runs. Libraries like pdf2image and PIL may not properly clean up temporary files.

**Consequences:**
- Batch processing stops mid-run with "Cannot open file" errors
- Gradual performance degradation as OS struggles with handle management
- Temp directory fills with orphaned files
- Requires process restart to clear handles

**Prevention:**
```python
# WRONG: Implicit file handling
image = Image.open('page.png')
result = pytesseract.image_to_string(image)
# File handle not explicitly closed

# CORRECT: Use context managers
with Image.open('page.png') as image:
    result = pytesseract.image_to_string(image)
# Handle closed automatically

# For batch processing:
for pdf_path in pdf_paths:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Process
            pass
    finally:
        # Ensure cleanup even on error
        gc.collect()  # Force GC periodically
```

**Additional safeguards:**
- Use context managers (`with` statements) for all file operations
- Call `gc.collect()` periodically in batch loops (every 100 files)
- Monitor open file handles using `psutil` or Windows Resource Monitor
- Clean up pdf2image output folders after each batch
- Set explicit file handle limits if possible

**Detection:** Increasing number of open handles in Task Manager, "Too many open files" exceptions, temp directory growing without cleanup.

**Phase mapping:** Phase 1 must establish file handling patterns; Phase 4 (parallelization) must audit all workers for handle leaks.

**Sources:**
- [Understanding File Descriptor Leaks](https://pradeesh-kumar.medium.com/you-must-be-aware-of-file-descriptor-leaking-600cee607dd6)
- [Windows Resource Leak Troubleshooting](https://informatix.systems/knowledgebase/windows-server/system-resource-leaks-e.g.-handle-leaks-./)

---

### Pitfall 4: Tesseract RAM Not Released on Windows

**What goes wrong:** Tesseract 4.x on Windows accumulates RAM usage across multiple OCR operations without releasing memory after each image is processed. Memory grows unbounded until the process crashes or system becomes unresponsive.

**Why it happens:** Documented memory management bug in Tesseract 4.x on Windows where allocated memory for processed images is not freed. Particularly severe with large images or when using certain language models.

**Consequences:**
- Process memory usage grows linearly with each OCR operation
- Eventually hits memory limits and crashes
- Cannot process full 30K+ file corpus in single process
- Requires process restarts mid-batch

**Prevention:**
```python
# WRONG: Single long-lived process
for pdf in all_30k_pdfs:
    ocr_result = pytesseract.image_to_string(image)
    # Memory never released

# CORRECT: Process in batches with process recycling
batch_size = 100
for batch in chunk_list(all_pdfs, batch_size):
    # Spawn new process for each batch
    with Pool(1) as pool:
        results = pool.map(process_single_pdf, batch)
    # Process terminates, releasing all memory
```

**Additional safeguards:**
- Process files in batches of 100-500, then restart worker processes
- Use process pools with `maxtasksperchild=100` to automatically recycle workers
- Downsize large images before OCR (keep 300 DPI but limit dimensions)
- Monitor process memory and force restart when threshold exceeded
- Use batch checkpointing to safely resume after restarts

**Detection:** Linearly growing process memory in Task Manager, slowdowns over time, eventual out-of-memory crashes.

**Phase mapping:** Phase 3 (OCR Processing) must implement batch processing with process recycling; Phase 4 (Parallelization) must configure worker recycling.

**Sources:**
- [Tesseract RAM Not Released on Windows Issue #2541](https://github.com/tesseract-ocr/tesseract/issues/2541)
- [Large Images Cause Excessive Memory Usage](https://github.com/naptha/tesseract.js/issues/900)

---

### Pitfall 5: Insufficient Image Resolution for 5-Digit IDs

**What goes wrong:** Converting PDFs to images at default or low DPI (72-150 DPI) makes 5-digit numbers too small for accurate OCR. Tesseract treats small digits as noise and removes them, or misrecognizes them entirely, leading to silent data loss.

**Why it happens:** Tesseract requires characters to have a minimum pixel height (x-height ~20 pixels for best results, ~10 pixels minimum). Below 300 DPI, typical document text drops below this threshold. At 8-10 pixel x-height, text is noise-filtered out.

**Consequences:**
- IDs not detected at all (returned as empty string)
- Digit confusion (0→8, 1→7, 5→6) due to insufficient detail
- Inconsistent results across similar pages
- Silent data loss - no error raised, just wrong/missing results

**Prevention:**
```python
# WRONG: Default DPI
images = convert_from_path('document.pdf')  # Often defaults to 72-150 DPI

# CORRECT: Explicit high DPI
images = convert_from_path(
    'document.pdf',
    dpi=300,  # Minimum for reliable digit recognition
    fmt='png'  # Lossless format preserves detail
)
```

**Additional safeguards:**
- Always specify DPI=300 explicitly (do not rely on defaults)
- Verify converted image dimensions (a 5-digit number should be >100 pixels wide)
- Test with sample images at different DPIs to validate recognition
- Consider DPI=400 for poor-quality scans

**Detection:** Empty OCR results on pages that visually contain IDs, inconsistent digit recognition rates, character height <10 pixels in converted images.

**Phase mapping:** Phase 1 (PDF to Image Conversion) must set DPI correctly immediately; Phase 5 (Quality Assurance) should validate resolution.

**Sources:**
- [Tesseract: Improving Quality Documentation](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [Why DPI Matters for OCR](https://ironsoftware.com/csharp/ocr/examples/ocr-image-dpi-for-tesseract/)

---

### Pitfall 6: Wrong PSM Mode for Isolated 5-Digit IDs

**What goes wrong:** Using Tesseract's default PSM 3 (automatic page segmentation) on images containing only a small isolated 5-digit number fails with "Empty page!!" or garbage output. Tesseract expects a full page of text and cannot handle sparse single-line numeric data.

**Why it happens:** PSM modes define how Tesseract expects text to be laid out. PSM 3 assumes a full page with paragraphs, columns, etc. Isolated numbers don't match this pattern, so Tesseract's segmentation algorithm fails to identify text regions.

**Consequences:**
- "Empty page!!" errors despite visible text
- Incomplete digit extraction (only 2-3 of 5 digits returned)
- High false negative rate
- Wasted processing time on failed attempts

**Prevention:**
```python
# WRONG: Default PSM for isolated numbers
text = pytesseract.image_to_string(image)  # PSM 3 default

# CORRECT: Use PSM appropriate for content
# For single line of digits:
text = pytesseract.image_to_string(
    image,
    config='--psm 7 --oem 3'  # PSM 7 = single line
)

# For single character/digit (if needed):
text = pytesseract.image_to_string(
    image,
    config='--psm 10 --oem 3'  # PSM 10 = single character
)

# Strategy: Try multiple PSM modes
for psm in [7, 6, 4, 13]:
    result = pytesseract.image_to_string(image, config=f'--psm {psm}')
    if validate_5_digit(result):
        break
```

**PSM mode quick reference:**
- PSM 3: Full page (default) - avoid for isolated IDs
- PSM 4: Single column of text - may work for IDs with context
- PSM 6: Uniform block of text - good for IDs with "Precede" label
- PSM 7: Single line - ideal for isolated ID lines
- PSM 10: Single character - for character-by-character fallback
- PSM 13: Raw line without segmentation - last resort

**Additional safeguards:**
- Start with PSM 7 (single line) for isolated 5-digit numbers
- Fall back to PSM 6 if IDs appear with "Precede" label above
- Use PSM 0 to test orientation detection before OCR
- Validate results with regex and retry with different PSM if invalid

**Detection:** "Empty page" errors, extremely low extraction success rate, OCR returning surrounding text but not the number.

**Phase mapping:** Phase 3 (OCR Processing) must implement PSM mode selection strategy; Phase 2 (Rotation Handling) may need PSM 0 for orientation detection.

**Sources:**
- [Tesseract PSM Modes Explained - PyImageSearch](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/)
- [Python OCR Tutorial with Tesseract](https://nanonets.com/blog/ocr-with-tesseract/)

---

### Pitfall 7: Unreliable Tesseract OSD for Rotation Detection

**What goes wrong:** Relying on Tesseract's OSD (Orientation and Script Detection via PSM 0) to detect image rotation produces unreliable results, especially with sparse text (like a single 5-digit ID). OSD reports incorrect orientations, low confidence scores, or fails entirely with "Too few characters" errors.

**Why it happens:** OSD requires sufficient text content to statistically determine orientation. Sparse content like a single 5-digit ID doesn't provide enough information. Additionally, OSD has known bugs where it reports wrong orientations even for correctly-oriented images.

**Consequences:**
- Images rotated incorrectly based on faulty OSD output
- Processing time wasted on unreliable detection step
- False confidence in automation leading to unchecked errors
- Complex fallback logic required to handle OSD failures

**Prevention:**
```python
# WRONG: Blindly trust OSD
osd = pytesseract.image_to_osd(image)
rotation = parse_rotation(osd)
rotated_image = image.rotate(rotation)
# May rotate correctly-oriented image incorrectly

# CORRECT: Multi-rotation brute force approach
def extract_with_all_rotations(image):
    best_result = None
    best_confidence = 0

    for angle in [0, 90, 180, 270]:
        rotated = image.rotate(angle, expand=True)
        result = pytesseract.image_to_data(
            rotated,
            config='--psm 7',
            output_type=pytesseract.Output.DICT
        )

        # Extract text and confidence
        text = ' '.join(result['text'])
        avg_confidence = sum(result['conf']) / len(result['conf'])

        # Validate with regex
        if re.match(r'^\d{5}$', text.strip()) and avg_confidence > best_confidence:
            best_result = text
            best_confidence = avg_confidence

    return best_result
```

**Additional safeguards:**
- Skip OSD entirely for this use case - directly try all 4 rotations
- Use regex validation to determine which rotation produced valid 5-digit ID
- Consider confidence scores from `image_to_data()` to pick best rotation
- Multi-rotation is fast (90/180/270 rotation is just data rearrangement, no interpolation)

**Detection:** OSD returning 180-degree rotations for correct images, "Too few characters" errors, inconsistent orientation detection on similar images.

**Phase mapping:** Phase 2 (Rotation Handling) should implement multi-rotation brute force instead of OSD; decision should be documented in Phase 1.

**Sources:**
- [OSD Not Working for Rotated Images Issue #1701](https://github.com/tesseract-ocr/tesseract/issues/1701)
- [Tesseract OSD Incorrect Results Issue #1926](https://github.com/tesseract-ocr/tesseract/issues/1926)
- [Correcting Text Orientation with Tesseract](https://pyimagesearch.com/2022/01/31/correcting-text-orientation-with-tesseract-and-python/)

---

### Pitfall 8: Digit Confusion Without Character Normalization

**What goes wrong:** OCR consistently misreads look-alike characters: 0/O, 1/I/l, 5/S, 8/B, etc. Without normalization, IDs like "12345" become "I2345" or "1234S", causing lookup failures and data corruption. Problem compounds across 30K+ PDFs, creating thousands of incorrect records.

**Why it happens:** Tesseract's character recognition models are trained on general text, not pure numeric data. Ambiguous glyphs get classified based on broader language patterns. Even with whitelist configs (`tessedit_char_whitelist=0123456789`), Tesseract 4.x LSTM engine sometimes ignores this constraint.

**Consequences:**
- Silent data corruption - IDs stored with letters instead of digits
- Failed lookups when users search for correct 5-digit IDs
- Inconsistent recognition of same ID across pages
- Manual correction required post-processing

**Prevention:**
```python
# Character confusion mapping
DIGIT_NORMALIZATION = {
    'O': '0', 'o': '0',
    'I': '1', 'l': '1', '|': '1',
    'S': '5', 's': '5',
    'B': '8', 'b': '8',
    'Z': '2', 'z': '2',
}

def normalize_to_digits(text):
    """Normalize common OCR confusions to digits."""
    normalized = text
    for char, digit in DIGIT_NORMALIZATION.items():
        normalized = normalized.replace(char, digit)
    return normalized

def extract_id(image):
    # Try with whitelist first
    text = pytesseract.image_to_string(
        image,
        config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
    ).strip()

    # Fallback: normalize confusion characters
    if not re.match(r'^\d{5}$', text):
        text = normalize_to_digits(text)

    # Validate final result
    if re.match(r'^\d{5}$', text):
        return text
    return None
```

**Additional safeguards:**
- Use Tesseract whitelist config but don't rely on it exclusively
- Apply normalization rules post-OCR
- Log original OCR output before normalization for debugging
- Consider training custom Tesseract model on numeric-only data if accuracy remains poor
- Flag low-confidence results for manual review

**Detection:** IDs with letters in output, failed regex validation, inconsistent recognition across similar images.

**Phase mapping:** Phase 3 (OCR Processing) must implement normalization; Phase 5 (Quality Assurance) should validate effectiveness.

**Sources:**
- [OCR Accuracy: Common Mistakes Guide](https://www.docsumo.com/blog/improving-ocr-accuracy)
- [OCR Digit Recognition Confusion](https://www.lido.app/blog/ocr-accuracy)
- [Common OCR Errors and How to Fix Them](https://imagetotexts.net/understanding-ocr-errors-and-how-to-fix-them/)

---

## Moderate Pitfalls

Mistakes that cause inefficiency, technical debt, or quality issues but are recoverable.

---

### Pitfall 9: Over-Aggressive Preprocessing Degrading Quality

**What goes wrong:** Applying standard preprocessing pipeline (grayscale → threshold → denoise) uniformly to all images actually degrades OCR accuracy for high-quality scans. Over-processing introduces artifacts, removes fine details, and creates new recognition errors.

**Why it happens:** Developers read that preprocessing "improves OCR" and apply it blindly. However, Tesseract 4.x already performs internal preprocessing, and high-quality scans don't need additional processing. Unnecessary thresholding can destroy color cues and anti-aliasing that help recognition.

**Prevention:**
```python
# WRONG: Always preprocess
def process_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    denoised = cv2.medianBlur(thresh, 3)
    return pytesseract.image_to_string(denoised)

# CORRECT: Try raw first, preprocess only if needed
def process_image_adaptive(image):
    # Try with raw image first
    result = pytesseract.image_to_string(image, config='--psm 7')

    if validate_result(result):
        return result

    # Only preprocess if initial attempt failed
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    result = pytesseract.image_to_string(gray, config='--psm 7')

    if validate_result(result):
        return result

    # More aggressive preprocessing as last resort
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    return pytesseract.image_to_string(thresh, config='--psm 7')
```

**When preprocessing helps:**
- Scanned images with uneven backgrounds
- Low contrast between text and background
- Heavy noise or speckles
- Skewed/rotated pages (deskewing)

**When preprocessing hurts:**
- Clean, high-quality scans at 300 DPI
- Born-digital PDFs converted to images
- Color cues help distinguish text from background

**Detection:** Preprocessing producing worse results than raw images, loss of fine details, introduction of artifacts.

**Phase mapping:** Phase 3 (OCR Processing) should implement tiered fallback approach; Phase 5 should A/B test preprocessing effectiveness.

**Sources:**
- [Tesseract: Improving Quality - When NOT to Preprocess](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [Image Preprocessing for OCR](https://autbor.com/preprocessingocr/)

---

### Pitfall 10: No Progress Tracking or Resume Capability

**What goes wrong:** Running 30K+ PDF batch without progress tracking or checkpointing means any interruption (crash, power loss, Ctrl+C) loses all progress. Must restart from file 1, wasting hours/days of processing.

**Why it happens:** Quick prototype code doesn't implement state persistence. "Just run it overnight" mentality until first failure teaches painful lesson.

**Prevention:**
```python
# Checkpoint system
def load_progress(checkpoint_file):
    """Load list of already-processed files."""
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'r') as f:
            return set(line.strip() for line in f)
    return set()

def save_progress(checkpoint_file, processed_file):
    """Append processed file to checkpoint."""
    with open(checkpoint_file, 'a') as f:
        f.write(f"{processed_file}\n")

def process_batch(pdf_paths, checkpoint_file='progress.txt'):
    processed = load_progress(checkpoint_file)
    remaining = [p for p in pdf_paths if p not in processed]

    print(f"Already processed: {len(processed)}")
    print(f"Remaining: {len(remaining)}")

    for i, pdf_path in enumerate(remaining):
        try:
            result = process_single_pdf(pdf_path)
            save_result(result)
            save_progress(checkpoint_file, pdf_path)

            if i % 100 == 0:
                print(f"Progress: {i}/{len(remaining)}")
        except Exception as e:
            log_error(pdf_path, e)
            # Continue with next file
            continue
```

**Additional safeguards:**
- Write results incrementally (after each file or every N files)
- Log errors separately for later review/retry
- Display progress percentage and ETA
- Implement graceful shutdown on signals (Ctrl+C)
- Provide resume command-line flag

**Detection:** Long-running jobs with no progress indication, restart from beginning after any interruption.

**Phase mapping:** Phase 4 (Parallelization) must implement checkpointing; Phase 5 should test resume functionality.

---

### Pitfall 11: Windows Path Length Limit (260 Characters)

**What goes wrong:** Deep directory structures combined with long PDF filenames exceed Windows' 260-character path limit (MAX_PATH). File operations fail with "FileNotFoundError" or "Path too long" errors despite files existing.

**Why it happens:** Legacy Win32 API limitation (not NTFS limit). Deeply nested folders + descriptive filenames quickly hit limit. Example: `C:\Users\Owner\Documents\Project\Archive\2023\Department\Scans\Long_Descriptive_Filename_With_Date_20230101.pdf` (150+ chars before actual filename).

**Prevention:**
```python
# Check if long paths enabled
import sys
sys.getwindowsversion()  # Windows 10 1607+ can enable long paths

# Enable in Group Policy or Registry (requires admin):
# HKLM\SYSTEM\CurrentControlSet\Control\FileSystem
# LongPathsEnabled = 1

# Code-level workaround: Use UNC paths
def to_long_path(path):
    """Convert path to UNC format to bypass MAX_PATH limit."""
    if sys.platform == 'win32' and not path.startswith('\\\\?\\'):
        if os.path.isabs(path):
            return '\\\\?\\' + path
    return path

# Usage
pdf_path = to_long_path(r'C:\very\deep\directory\structure\file.pdf')
with open(pdf_path, 'rb') as f:
    # Process file
    pass
```

**Additional safeguards:**
- Document system requirements (Windows 10 1607+ with long paths enabled)
- Use shorter output directory paths
- Flatten directory structure if possible
- Test with deepest path in corpus early
- Provide clear error messages if path too long

**Detection:** FileNotFoundError for files that exist when viewed in Explorer, path-related errors only on Windows, issues with nested directories.

**Phase mapping:** Phase 1 should validate path handling early; Phase 4 (Parallelization) must ensure all workers handle long paths.

**Sources:**
- [Remove Max Path Length Limit on Windows](https://woshub.com/max-path-length-limit-windows/)
- [Microsoft: Maximum Path Length Limitation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)

---

### Pitfall 12: Regex Over-Matching Producing False Positives

**What goes wrong:** Loose regex patterns (e.g., `\d{5}`) match 5-digit numbers anywhere in OCR output, catching page numbers, dates (01234 from "2024-01-23 4pm"), phone number fragments, or other numeric data unrelated to IDs. Results contain garbage data.

**Why it happens:** OCR output includes not just target IDs but also: page footers, date stamps, annotations, marginal notes, and background artifacts. Simple regex matches all 5-digit sequences indiscriminately.

**Prevention:**
```python
# WRONG: Over-broad regex
ids = re.findall(r'\d{5}', ocr_text)  # Matches EVERYTHING

# BETTER: Anchor pattern and use boundaries
id_match = re.search(r'\b\d{5}\b', ocr_text)

# BEST: Use contextual validation
def extract_precede_id(ocr_text):
    """Extract ID with context validation."""
    # Look for "Precede" keyword near the ID
    pattern = r'(?:Precede|PRECEDE)[\s\S]{0,50}?(\d{5})'
    match = re.search(pattern, ocr_text, re.IGNORECASE)

    if match:
        return match.group(1)

    # Fallback: isolated 5-digit on its own line
    lines = ocr_text.split('\n')
    for line in lines:
        line_clean = line.strip()
        if re.match(r'^\d{5}$', line_clean):
            return line_clean

    return None
```

**Additional safeguards:**
- Use anchor patterns (`^`, `$`, `\b`) to avoid substring matches
- Validate ID format (e.g., exclude 00000, 11111 if invalid)
- Check spatial location if using `image_to_data()` (IDs in specific regions)
- Implement confidence thresholds
- Log ambiguous matches for manual review

**Detection:** Results containing obvious non-IDs (00000, 12345 in footer, dates), multiple IDs per page when expecting one, user reports of incorrect lookups.

**Phase mapping:** Phase 3 (OCR Processing) must implement smart extraction; Phase 5 (Quality Assurance) should audit false positive rate.

**Sources:**
- [Enhancing OCR Accuracy with Regex Patterns](https://www.researchgate.net/publication/389374337_Enhancing_OCR_Accuracy_with_Regex_Patterns_Limitations_Strengths_and_Comparative_Analysis_-Oluwadamilare_I_Tobiloba)
- [OCR Engine Extract Information - Heuristics Rules](https://www.researchgate.net/publication/323640080_OCR_Engine_to_Extract_Food-Items_Prices_Quantity_Units_from_Receipt_Images_Heuristics_Rules_Based_Approach)

---

## Minor Pitfalls

Mistakes that cause annoyance or slight inefficiency but are easily fixed.

---

### Pitfall 13: pdf2image Threading I/O Bottleneck

**What goes wrong:** Using more than 4 threads with pdf2image for parallel PDF conversion creates I/O bottleneck, slowing performance instead of improving it.

**Prevention:** Limit pdf2image threading to 4 or fewer. Scale parallelism at the PDF level (process multiple PDFs in parallel), not at the page level within one PDF.

**Phase mapping:** Phase 4 (Parallelization).

**Sources:**
- [pdf2image GitHub - Threading Issues](https://github.com/Belval/pdf2image/issues/29)

---

### Pitfall 14: Tesseract `tessedit_char_whitelist` Not Honored in v4

**What goes wrong:** Setting `tessedit_char_whitelist=0123456789` has no effect in some Tesseract 4.x versions with LSTM engine (OEM 1). Letters still appear in output.

**Prevention:**
```python
# Use OEM 3 (combined legacy + LSTM) for better whitelist support
config = '--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789'
```

Also implement post-OCR normalization (Pitfall 8) as backup.

**Phase mapping:** Phase 3 (OCR Processing).

**Sources:**
- [Tesseract Digits Only Issue - Tesseract 4](https://tesseract-ocr.narkive.com/33xRUphY/digits-only-for-tesseract4)
- [Tesseract Whitelist Not Working Issue #4407](https://github.com/tesseract-ocr/tesseract/issues/4407)

---

### Pitfall 15: Ignoring Tesseract Confidence Scores

**What goes wrong:** Treating all OCR output as equally reliable without checking confidence scores. Low-confidence results (e.g., <50) are often wrong but get committed to final output.

**Prevention:**
```python
# Use image_to_data() to get confidence scores
data = pytesseract.image_to_data(
    image,
    config='--psm 7',
    output_type=pytesseract.Output.DICT
)

text = data['text'][0]
confidence = data['conf'][0]

if confidence < 60:
    # Flag for manual review or try preprocessing
    result = try_with_preprocessing(image)
else:
    result = text
```

**Phase mapping:** Phase 3 (OCR Processing), Phase 5 (Quality Assurance).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Phase 1: PDF to Image | Memory exhaustion (Pitfall 1), DPI too low (Pitfall 5), file handles (Pitfall 3) | Use output folders + paths_only, set DPI=300, context managers |
| Phase 2: Rotation Handling | OSD unreliability (Pitfall 7), wrong PSM (Pitfall 6) | Multi-rotation brute force, skip OSD, use PSM 7 |
| Phase 3: OCR Processing | Digit confusion (Pitfall 8), wrong PSM (Pitfall 6), over-preprocessing (Pitfall 9) | Normalization rules, adaptive preprocessing, confidence checks |
| Phase 4: Parallelization | Windows spawn overhead (Pitfall 2), memory leaks (Pitfall 4), no resume (Pitfall 10) | Worker initialization, process recycling, checkpointing |
| Phase 5: Quality Assurance | Regex false positives (Pitfall 12), low confidence ignored (Pitfall 15) | Contextual extraction, confidence thresholds, audit samples |

---

## Research Confidence Notes

| Area | Confidence | Rationale |
|------|------------|-----------|
| Memory issues (pdf2image, Tesseract) | HIGH | Official documentation + multiple GitHub issues with specific details |
| Windows multiprocessing | HIGH | Python official documentation + verified performance testing |
| File handle leaks | MEDIUM | General Windows documentation + batch processing best practices |
| PSM modes and OSD | HIGH | Official Tesseract documentation + PyImageSearch detailed tutorial |
| Digit confusion | MEDIUM | Multiple sources + practical experience reports, but not official docs |
| Path length limits | HIGH | Microsoft official documentation |
| Preprocessing pitfalls | HIGH | Official Tesseract documentation explicitly addresses this |

---

## Sources

### Official Documentation
- [Tesseract: Improving Quality](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)
- [pdf2image GitHub Repository](https://github.com/Belval/pdf2image)
- [Microsoft: Maximum Path Length Limitation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)

### Technical Issues
- [Tesseract RAM Not Released on Windows (Issue #2541)](https://github.com/tesseract-ocr/tesseract/issues/2541)
- [pdf2image Memory Leak (Issue #54)](https://github.com/yakovmeister/pdf2image/issues/54)
- [Python Multiprocessing Pickle Performance (Issue #96953)](https://github.com/python/cpython/issues/96953)
- [Tesseract OSD Issues (Issue #1701, #1926)](https://github.com/tesseract-ocr/tesseract/issues/1701)
- [Tesseract Whitelist Not Working (Issue #4407)](https://github.com/tesseract-ocr/tesseract/issues/4407)

### Tutorials and Guides
- [PyImageSearch: Tesseract PSM Modes Explained](https://pyimagesearch.com/2021/11/15/tesseract-page-segmentation-modes-psms-explained-how-to-improve-your-ocr-accuracy/)
- [Python Multiprocessing: Fork vs Spawn](https://medium.com/@Nexumo_/python-multiprocessing-revisited-fork-vs-spawn-5b9216fd5710)
- [Python's Multiprocessing Performance Problem](https://pythonspeed.com/articles/faster-multiprocessing-pickle/)
- [Correcting Text Orientation with Tesseract](https://pyimagesearch.com/2022/01/31/correcting-text-orientation-with-tesseract-and-python/)

### Best Practices
- [How to Use Image Preprocessing for OCR](https://www.freecodecamp.org/news/getting-started-with-tesseract-part-ii-f7f9a0899b3f/)
- [OCR Accuracy: How to Measure and Improve](https://www.lido.app/blog/ocr-accuracy)
- [Understanding File Descriptor Leaks](https://pradeesh-kumar.medium.com/you-must-be-aware-of-file-descriptor-leaking-600cee607dd6)
- [Batch OCR Processing Best Practices](https://dev.to/revisepdf/batch-ocr-processing-for-large-document-collections-4h30)

### Domain Knowledge
- [The 6 Biggest OCR Problems and How to Overcome Them](https://conexiom.com/blog/the-6-biggest-ocr-problems-and-how-to-overcome-them)
- [Common OCR Errors and How to Fix Them](https://imagetotexts.net/understanding-ocr-errors-and-how-to-fix-them/)
- [Improving OCR Accuracy Guide](https://www.docsumo.com/blog/improving-ocr-accuracy)
