# Quick Reference - PDF MCQ Extraction Tool

## 🚀 Quick Start (2 Steps)

### Step 1: Start Gemini Server
```bash
npm start
```
- Complete login if needed
- Press Enter after login
- **Keep this terminal running**

### Step 2: Launch UI
```bash
python ui_main.py
```

---

## 📋 File Structure

```
testing/
├── server.js              # Gemini API server
├── pdf_processor.py       # PDF extraction
├── gemini_client.py       # API client
├── json_manager.py        # File management
├── processing_thread.py   # Background worker
├── ui_main.py            # Main UI (run this)
├── config.json           # Settings
├── requirements.txt      # Python deps
├── package.json          # Node deps
└── README.md             # Full documentation
```

---

## ⚙️ Configuration (config.json)

```json
{
  "pages_per_batch": 5,      // Adjust for speed vs quality
  "mids_percentage": 45,     // Mids section size
  "retry_attempts": 3,       // Retries on failure
  "mcqs_per_batch": 10       // MCQs per batch
}
```

---

## 📊 Output

```
{pdf_name}_JSON/
├── {pdf_name}_mids_mcqs.json
└── {pdf_name}_finals_mcqs.json
```

Each MCQ has:
- id, question, options (4), correct, explanation, difficulty, importance

---

## 🔧 Common Issues

| Problem | Solution |
|---------|----------|
| "Server not initialized" | Run `npm start` first |
| "Cannot connect" | Check server is running on port 3000 |
| Slow processing | Normal - 30-60s per batch |
| PDF won't open | Check file isn't corrupted |

---

## 💡 Tips

- Test with small PDFs first (10-20 pages)
- Watch the color-coded logs
- Keep server terminal open
- Review generated MCQs for accuracy

---

**For full documentation, see README.md**
