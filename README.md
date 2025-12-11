# 🎓 PDF to MCQ Generator
### *Powered by Gemini AI & Python*

**Turn your textbooks into interactive quizzes in seconds!** 🚀

This intelligent tool automates the process of extracting knowledge from PDF textbooks and converting it into structured Multiple Choice Questions (MCQs). Whether you're a student preparing for exams or a teacher creating course materials, this tool does the heavy lifting for you.

---

## ✨ Key Features

- **🤖 AI-Powered Generation**: Uses Google's Gemini AI to create high-quality, context-aware questions.
- **📄 Smart PDF Processing**: Automatically splits textbooks into **Mids** and **Finals** sections based on your curriculum needs.
- **🖥️ User-Friendly Interface**: Clean and modern PyQt5 GUI for easy operation.
- **💾 Structured JSON Output**: Exports data in a clean, ready-to-use JSON format.
- **🔄 Auto-Correction**: Includes a robust JSON fixer to ensure AI output is always valid code.
- **🌐 Browser Automation**: Uses a custom Node.js server to interface directly with Gemini Web, bypassing standard API limitations.

---

## 🛠️ How It Works

1. **The Brain (Node.js Server)**: A local server controls a browser instance that talks to Gemini.
2. **The Body (Python App)**: The main application reads your PDF, chunks the text, and sends it to the "Brain".
3. **The Result**: You get a perfectly formatted JSON file with questions, options, and answers.

---

## 🚀 Getting Started

### Prerequisites
- **Node.js** (for the server)
- **Python 3.x** (for the application)
- **Google Chrome** (for browser automation)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd gemini-json
   ```

2. **Install Server Dependencies**
   ```bash
   npm install
   ```

3. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🎮 Usage Guide

### Step 1: Wake up the AI 🤖
Start the local server. This will open a Chrome window.
```bash
npm start
```
> **IMPORTANT:** Log in to your Google Gemini account in the browser window that pops up. Once logged in, keep this terminal running!

### Step 2: Launch the App 📱
Open a **new terminal** and run the main interface:
```bash
python ui_main.py
```

### Step 3: Generate! ⚡
1. Click **Browse** to select your PDF textbook.
2. Adjust the **Mids/Finals split** if needed (default is calculated automatically).
3. Hit **Start Processing** and watch the magic happen!

---

## 📂 Project Structure

- `ui_main.py` - The dashboard of the operation.
- `server.js` - The bridge to Gemini AI.
- `pdf_processor.py` - The document surgeon (splits and reads PDFs).
- `json_fixer.py` - The quality control agent (fixes broken JSON).
- `docs/` - Detailed documentation and guides.

---

## 📝 Notes

- The tool uses your local browser session to interact with Gemini.
- Ensure you have a stable internet connection.
- Large PDFs are processed in batches to ensure high-quality results.

---

*Made with ❤️ for efficient learning.*
