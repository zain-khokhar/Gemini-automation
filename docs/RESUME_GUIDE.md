# Resume from Position Feature - User Guide

## 🎯 Problem Solved

**Before:** Processing 67 PDFs with ~55 batches each. If laptop shuts down at PDF 6, batch 45 → all progress lost, must restart from PDF 1, batch 1.

**After:** Resume from ANY position! Start from PDF 6, batch 45 and continue exactly where you left off.

---

## 📍 How to Use

### Step 1: Select Folder
Click "📁 Browse" and select your folder with PDFs.

### Step 2: Choose Resume Mode

**Option A: Start from Beginning**
- Select "○ Start from beginning"
- Processes all PDFs from the start

**Option B: Resume from Position**
- Select "● Resume from position"
- Enter your resume position

### Step 3: Set Resume Position

**PDF Index:**
```
Start from PDF: [__6__] / 67
```

**Section Selection:**
- **Mids Only**: Shows "Start from Mids batch: [___]"
- **Finals Only**: Shows "Start from Finals batch: [___]"
- **Both**: Shows BOTH batch inputs

**Example (Both sections):**
```
Start from Mids batch:   [__45__]
Start from Finals batch: [__1__]
```

### Step 4: Start Processing
Click "▶️ Start Processing"

---

## 💡 Examples

### Example 1: Resume Mids Processing
```
Scenario: Was at PDF 6/67, Mids batch 45/55
Solution:
  ● Resume from position
  Start from PDF: 6
  Section: ● Mids Only
  Start from Mids batch: 45
  
Result: Skips PDFs 1-5, skips mids batches 1-44, continues from batch 45
```

### Example 2: Resume Both Sections
```
Scenario: Completed all mids, was at Finals batch 15
Solution:
  ● Resume from position
  Start from PDF: 10
  Section: ● Both (Mids + Finals)
  Start from Mids batch: 999 (skip all mids)
  Start from Finals batch: 15
  
Result: Skips PDFs 1-9, skips all mids, starts finals from batch 15
```

### Example 3: Start Fresh on PDF 20
```
Scenario: Want to skip first 19 PDFs
Solution:
  ● Resume from position
  Start from PDF: 20
  Section: ● Both
  Start from Mids batch: 1
  Start from Finals batch: 1
  
Result: Skips PDFs 1-19, processes PDF 20 onwards from beginning
```

---

## 🔍 Console Output

### When Resuming:
```
📍 Resuming from PDF 6/67
   Mids: Starting from batch 45
   Finals: Starting from batch 1

⏭️  Skipping PDF 1/67 (resuming from 6)
⏭️  Skipping PDF 2/67 (resuming from 6)
...
⏭️  Skipping PDF 5/67 (resuming from 6)

📄 Processing PDF 6/67: handout_06.pdf
📚 Processing MIDS Section
⏭️  Skipping mids batch 1/55
⏭️  Skipping mids batch 2/55
...
⏭️  Skipping mids batch 44/55
📦 Batch 45/55 (Pages 441-450)
  → Sending request to server...
  ✓ Successfully processed 10 MCQs in 32.5s
```

---

## ⚙️ How It Works

### Skip Logic:

**PDF Level:**
- If `current_pdf < start_pdf_index` → Skip entire PDF

**Batch Level:**
- Only applies to the resume PDF (`current_pdf == start_pdf_index`)
- If `current_batch < start_batch` → Skip batch
- Different start batch for mids vs finals

**After Resume PDF:**
- All subsequent PDFs process normally from batch 1

---

## 🎯 Pro Tips

1. **Write Down Your Position**
   - Before shutting down, note: PDF X, Section Y, Batch Z
   - Makes resuming easy

2. **Use High Batch Numbers to Skip Sections**
   - Want to skip all mids? Set mids batch to 999
   - System will skip all mids batches

3. **Test Resume First**
   - Try resuming from PDF 2, batch 1
   - Verify it skips PDF 1 correctly

4. **Combine with Pause**
   - Use pause for short breaks
   - Use resume for laptop shutdown/restart

---

## ✅ Benefits

✅ **No Lost Progress** - Resume from exact position  
✅ **Flexible** - Skip any number of PDFs/batches  
✅ **Smart** - UI adapts to section selection  
✅ **Safe** - Clear skip messages in logs  
✅ **Efficient** - No reprocessing of completed work  

---

**Status: ✅ READY TO USE**

Resume from any position and never lose progress again!
