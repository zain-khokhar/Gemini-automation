# 🎓 The Ultimate PDF to MCQ Converter
### *Turn Static Textbooks into Interactive Goldmines*

![Python](https://img.shields.io/badge/Python-3.x-blue.svg) ![Node.js](https://img.shields.io/badge/Node.js-Automated-green.svg) ![Gemini](https://img.shields.io/badge/AI-Powered-purple.svg)

---

## 👋 Welcome to Smarter Studying

We've all been there: staring at a 500-page PDF textbook, knowing you need to prepare for exams, but dreading the endless reading. What if you could just feed that book into a machine and get a perfect practice test out the other side?

**That's exactly what this tool does.**

It takes your course materials—whether they're for "Mids" or "Finals"—feeds them to Google's advanced **Gemini AI**, and hands you back structured, ready-to-use Multiple Choice Questions. No API keys, no expensive subscriptions, just smart automation.

---

## 🌟 What Makes This Special?

This isn't just a script; it's a full-fledged desktop application designed to be resilient and intelligent.

### 🧠 The "Brain" (Node.js + Puppeteer)
Instead of paying for expensive API credits, we built a custom Node.js server that launches a real browser instance. It logs into Gemini just like you would, creating a persistent, conversational session. This allows for:
- **Human-like Interaction**: It talks to the AI naturally.
- **Smart Retries**: If the AI stutters, the system pauses and retries.
- **Context Awareness**: It keeps track of what you've already processed.

### 🦾 The "Body" (Python + PyQt5)
The interface is built with PyQt5, offering a clean, modern dashboard. It handles the heavy lifting:
- **Intelligent Splitting**: It knows your curriculum isn't just 50/50. It automatically calculates the split between Mids and Finals coverage (defaulting to a smart 95% of the first half for Mids).
- **Chunking Engine**: It breaks down massive PDFs into bite-sized chunks that the AI can digest easily without hallucinating.
- **Self-Healing Data**: AI isn't perfect. Sometimes it returns broken JSON. Our **`JSON Fixer`** catches these syntax errors and repairs them instantly, ensuring your output file is always valid code.

---

## 🚀 Features at a Glance

- **🤖 Automated AI Conversations**: Leveraging the power of Google Gemini (1.5 Pro/Flash models).
- **📄 Smart PDF Parsing**: Handles huge textbooks with ease.
- **⚡ Two-Thread System**: A non-blocking UI that stays responsive while the backend crunches data.
- **🛡️ Auto-Correction**: A dedicated module that actively monitors and fixes broken data formats.
- **📊 Real-time Progress**: Visual bars and logs keep you updated on every generated question.
- **💾 Clean Exports**: Get your data in pristine JSON format, ready for any quiz app or LMS.

---

## 🛠️ How to Set It Up

Getting your personal quiz factory running is easy. You need two main components: the **Brain** (Server) and the **Body** (App).

### Prerequisites
1.  **Node.js**: [Download here](https://nodejs.org/) (LTS recommended).
2.  **Python 3.x**: [Download here](https://www.python.org/).
3.  **Google Chrome**: You probably already have this!

### Installation

1.  **Clone the Magic**
    ```bash
    git clone https://github.com/yourusername/gemini-mcq-tool.git
    cd gemini-mcq-tool
    ```

2.  **Awaken the Brain (Node.js Dependencies)**
    ```bash
    npm install
    ```

3.  **Build the Body (Python Dependencies)**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🎮 Let's Generate Some Questions!

### Step 1: Start the Engine
Open a terminal in the project folder and run:
```bash
npm start
```
> **👀 Crucial Step:** A Chrome window will open. **Log in to your Google Gemini account** in this window. Once you're logged in, leave the window open and the terminal running. This is your gateway to the AI.

### Step 2: Launch the Dashboard
Open a **new** terminal window and run:
```bash
python ui_main.py
```

### Step 3: Create!
1.  Click **"Browse"** to select your textbook PDF.
2.  The app will auto-detect the page count and suggest a split for Mids/Finals.
3.  Hit **"Start Processing"**.
4.  Sit back and watch the questions pour in. ☕

---

## 📂 Inside the Codebase

For the curious developers, here's how we structured the magic:

- `ui_main.py`: The command center. Handles the GUI and user interactions.
- `server.js`: The puppeteer controller. It manages the browser session and dom manipulation to talk to Gemini.
- `pdf_processor.py`: The surgeon. Safely slices PDFs into text chunks.
- `json_fixer.py`: The medic. Scans output for syntax errors and patches them on the fly.
- `premium_requests.json`: Tracks your usage to ensure we stay within safe limits.

---

## 📝 A Note on Usage
This tool uses browser automation to interact with a web service. Please use it responsibly and adhere to Google's terms of service. It is designed for educational and personal use to facilitate learning.

---

*Built with ❤️ for students, by students. Happy studying!* 🎓
