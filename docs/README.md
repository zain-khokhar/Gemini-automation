# PDF MCQ Extraction Tool - User Guide

## 📋 Overview

This tool automatically extracts text from PDF textbooks and generates high-quality Multiple Choice Questions (MCQs) using Gemini AI. The system intelligently splits content into **Mids** and **Finals** sections and saves them as structured JSON files.

---

## 🚀 Quick Start

### 1. Install Dependencies

**Node.js (for Gemini server):**
```bash
npm install
```

**Python (for UI and PDF processing):**
```bash
pip install -r requirements.txt
```

### 2. Start the Gemini Server

Open a terminal and run:
```bash
npm start
```

**Important:** 
- The browser will open automatically
- If not logged in to Gemini, complete the login manually
- Press Enter in the terminal after login
- Keep this terminal running while using the tool

### 3. Launch the UI Application

Open a **new terminal** and run:
```bash
python ui_main.py
```

---

## 📖 How to Use

### Step-by-Step Process

1. **Select PDF File**
   - Click the "📁 Browse" button
   - Choose your PDF textbook
   - The file path will appear in the input field

2. **Start Processing**
   - Click "▶️ Start Processing"
   - The system will:
     - Check Gemini server connection
     - Split PDF into Mids (45% of pages) and Finals (remaining)
     - Process 5 pages at a time
     - Generate 10 MCQs per batch
     - Save results automatically

3. **Monitor Progress**
   - **Current Section**: Shows whether processing Mids or Finals
   - **Current Batch**: Shows batch number (e.g., "3/12")
   - **Status**: Current operation (e.g., "Generating MCQs...")
   - **Progress Bar**: Visual progress indicator
   - **Logs**: Detailed color-coded process information
     - 🔵 Blue = Information
     - 🟢 Green = Success
     - 🟠 Orange = Warning
     - 🔴 Red = Error

4. **Stop if Needed**
   - Click "⏸️ Stop" to halt processing
   - Partial results will not be saved

5. **Reset**
   - Click "🔄 Reset" to clear the UI and start fresh

---

## 📁 Output Structure

After processing, you'll find a new folder in the same directory as your PDF:

```
{pdf_name}_JSON/
├── {pdf_name}_mids_mcqs.json
└── {pdf_name}_finals_mcqs.json
```

**Example:**
```
cs101_JSON/
├── cs101_mids_mcqs.json
└── cs101_finals_mcqs.json
```

---

## 📝 JSON Format

Each MCQ follows this structure:

```json
{
  "id": 1,
  "question": "What is the main focus of Computer Science?",
  "options": [
    "Software",
    "Hardware",
    "Algorithms",
    "Telecommunication"
  ],
  "correct": "Algorithms",
  "explanation": "Computer Science primarily focuses on algorithms and computational theory.",
  "difficulty": "Medium",
  "importance": 4
}
```

**Fields:**
- `id`: Unique sequential number
- `question`: The MCQ question
- `options`: Array of 4 possible answers
- `correct`: The correct answer (must match one option exactly)
- `explanation`: Brief explanation of the answer
- `difficulty`: Easy, Medium, or Hard
- `importance`: 1-5 scale (5 = most important)

---

## ⚙️ Configuration

Edit `config.json` to customize:

```json
{
  "gemini_server_url": "http://localhost:3000",
  "pages_per_batch": 5,           // Pages per Gemini request
  "mids_percentage": 45,           // Percentage for Mids section
  "retry_attempts": 3,             // Retries on failure
  "retry_delay_seconds": 5,        // Delay between retries
  "mcqs_per_batch": 10,            // MCQs to generate per batch
  "request_timeout_seconds": 60    // Request timeout
}
```

---

## 🔧 Troubleshooting

### "Server not initialized" Error
**Solution:** Make sure you started the Gemini server with `npm start` and completed login.

### "Cannot connect to server" Error
**Solution:** 
1. Check if the server is running
2. Verify the URL in `config.json` is correct
3. Ensure no firewall is blocking port 3000

### MCQ Generation Fails
**Solution:**
- Check your internet connection
- Verify Gemini is responding in the browser
- Try reducing `pages_per_batch` in config.json
- Check the logs for specific error messages

### PDF Cannot Be Opened
**Solution:**
- Ensure the PDF is not corrupted
- Check file permissions
- Try a different PDF

### Slow Processing
**Solution:**
- This is normal for large PDFs
- Each batch takes 30-60 seconds
- Consider reducing `pages_per_batch` for faster individual responses

---

## 💡 Tips

1. **Start Small**: Test with a small PDF (10-20 pages) first
2. **Monitor Logs**: Watch the color-coded logs for detailed progress
3. **Keep Server Running**: Don't close the terminal running `npm start`
4. **Check Output**: Verify JSON files after processing
5. **Backup PDFs**: Keep original PDFs safe

---

## 📊 How It Works

### Mids/Finals Splitting Logic

**Formula:** Mids = (Total Pages / 2) - 5%

**Example:**
- 100 pages total
- Half = 50 pages
- 50 - 5% = 45 pages for Mids
- Remaining 55 pages for Finals

### Processing Flow

1. **PDF Analysis**: Extract text from all pages
2. **Section Split**: Divide into Mids and Finals
3. **Batch Creation**: Group pages (5 per batch)
4. **AI Generation**: Send each batch to Gemini
5. **Validation**: Verify JSON structure
6. **ID Assignment**: Sequential numbering
7. **File Saving**: Create organized JSON files

---

## 🎯 Best Practices

1. **Quality PDFs**: Use clear, text-based PDFs (not scanned images)
2. **Reasonable Size**: 50-200 pages work best
3. **Stable Connection**: Ensure stable internet for Gemini
4. **Review Output**: Always review generated MCQs for accuracy
5. **Batch Size**: 5 pages per batch is optimal for quality

---

## 🆘 Support

If you encounter issues:

1. Check the logs in the UI (detailed error messages)
2. Verify all dependencies are installed
3. Ensure Gemini server is running and logged in
4. Check `config.json` settings
5. Try with a different PDF to isolate the issue

---

## 📄 System Requirements

- **Node.js**: v14 or higher
- **Python**: 3.7 or higher
- **Internet**: Required for Gemini AI
- **RAM**: 4GB minimum (8GB recommended)
- **Disk Space**: Depends on PDF size

---

**Enjoy automated MCQ generation! 🎉**
