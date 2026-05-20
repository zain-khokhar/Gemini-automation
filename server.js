const express = require('express');
const puppeteer = require('puppeteer');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;

// Middleware
app.use(express.json({ limit: '50mb' }));
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
});

// Global browser instance
let browser = null;
let page = null;
let isInitialized = false;

// Chat session tracking
let chatSessionId = 0;
let isPageReady = false;

// Pause state
let isPaused = false;
let pauseTimestamp = null;

// Premium request counter file
const REQUEST_COUNTER_FILE = path.join(__dirname, 'premium_requests.json');

function loadRequestCounter() {
  try {
    if (fs.existsSync(REQUEST_COUNTER_FILE)) {
      const data = JSON.parse(fs.readFileSync(REQUEST_COUNTER_FILE, 'utf8'));
      const today = new Date().toDateString();
      if (data.date !== today) {
        return { date: today, count: 0 };
      }
      return data;
    }
  } catch (error) {
    console.error('Error loading request counter:', error);
  }
  return { date: new Date().toDateString(), count: 0 };
}

function saveRequestCounter(counter) {
  try {
    fs.writeFileSync(REQUEST_COUNTER_FILE, JSON.stringify(counter, null, 2));
  } catch (error) {
    console.error('Error saving request counter:', error);
  }
}

function incrementRequestCounter() {
  const counter = loadRequestCounter();
  counter.count++;
  saveRequestCounter(counter);
  console.log(`📊 Premium requests today: ${counter.count}/100`);
  return counter;
}

// Helper
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================================================
// SYSTEM PROMPTS
// ============================================================

function generateSystemPrompt(expectedMcqs = 10) {
  return `You are an expert MCQ generator for Virtual University students preparing for mids and finals exams.

Generate EXACTLY ${expectedMcqs} unique MCQs from the given text/topic.

PRIORITY:

Prefer VU past paper questions from 2023-2025
Focus on frequently repeated concepts
If past paper data is unavailable, generate important conceptual MCQs

RULES:

Response MUST be valid JSON parseable by JSON.parse()
Respond ONLY with a JSON array
No markdown, no code blocks, no explanations, no extra text
First character must be [ and last character must be ]
Never repeat questions or concepts
Each question must be short and clear
Each MCQ must contain exactly 4 options

CORRECT JSON FORMAT:

[{"question":"What is virtual storage?","options":["RAM extension","Disk-based memory","Cache memory","ROM type"],"correct":"Disk-based memory","explanation":"Virtual storage uses disk space as extended memory."},{"question":"What is cache memory?","options":["Fast memory","Slow memory","Disk storage","Network storage"],"correct":"Fast memory","explanation":"Cache is high-speed memory close to CPU."}]

REQUIRED FIELDS (ALL MANDATORY):

question: string (SHORT, 15-20 words max)
options: array of EXACTLY 4 strings (each option 2-8 words)
correct: string (MUST match one option EXACTLY)
explanation: string (brief, 1-2 sentences)

REMEMBER: If your JSON has ANY syntax error, the entire batch fails and is skipped. Make it PERFECT.

TEXT TO ANALYZE:
`;
}

function generateShortNotesPrompt(expectedNotes = 10) {
  return `You are an expert academic note generator for Virtual University students preparing for exams.

Generate EXACTLY ${expectedNotes} high-quality short notes from the provided text/topic.

OUTPUT RULES:

Respond ONLY with a valid JSON array
No markdown, no code blocks, no extra text before or after
Output must be directly parseable by JSON.parse()
First character must be [ and last character must be ]

CONTENT REQUIREMENTS:

Focus on important exam concepts, logic, processes, and relationships
Prefer “Why”, “How”, “Differentiate”, and “Explain significance” type questions
Avoid simple memorization questions unless concept is essential
Ensure strong conceptual depth and exam relevance
Explanations must feel like a top-level expert (genius-level clarity), making the concept fully intuitive and permanently understandable for a student

FORMAT:
Each item must follow this structure exactly:
{
"question": "Clear question (10 to 20 words)",
"answer": "Detailed explanation (40 to 60 words, 3 to 5 sentences)"
}

RULES:

Exactly ${expectedNotes} items
No repetition of ideas or questions
Questions must be clear and exam-oriented
Answers must be complete, highly clear, and conceptually deep
No extra fields (no id, no difficulty, no source, no importance)
No links, URLs, or references
Each object must contain ONLY "question" and "answer"

VALIDATION CHECK:

Must be valid JSON
Must start with [
Must end with ]
No trailing commas
Properly closed quotes and brackets
Exactly ${expectedNotes} entries

TEXT TO ANALYZE:
`;
}

// ============================================================
// BROWSER INITIALIZATION
// ============================================================

async function initializeBrowser() {
  if (isInitialized) {
    console.log('Browser already initialized');
    return true;
  }

  try {
    console.log('Launching browser...');
    const launchOpts = {
      headless: false,
      userDataDir: './session',
      defaultViewport: null,
      args: [
        '--start-maximized',
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--lang=en-US,en',
        '--disable-features=TranslateUI'
      ]
    };
    try {
      browser = await puppeteer.launch(launchOpts);
    } catch (launchErr) {
      console.warn('⚠️ Puppeteer launch failed:', launchErr.message);
      console.log('🔄 Deleting corrupt "./session" directory and retrying...');
      try {
        if (fs.existsSync('./session')) {
          fs.rmSync('./session', { recursive: true, force: true });
        }
        browser = await puppeteer.launch(launchOpts);
        console.log('✓ Recovered with fresh session');
      } catch (retryErr) {
        console.error('❌ Recovery failed:', retryErr.message);
        throw retryErr;
      }
    }

    page = await browser.newPage();
    await page.setExtraHTTPHeaders({
      'Accept-Language': 'en-US,en;q=0.9'
    });
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    // Block unnecessary resources
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      const resourceType = req.resourceType();
      if (['image', 'font', 'media'].includes(resourceType)) {
        req.abort();
      } else {
        req.continue();
      }
    });

    console.log('Navigating to Gemini...');
    await page.goto('https://gemini.google.com/app', { waitUntil: 'networkidle2' });

    // Check if logged in
    const isLoggedIn = await page.$('textarea, div[role="textbox"]') !== null;

    if (!isLoggedIn) {
      console.log('\n⚠️  NOT LOGGED IN - Please complete login manually in the browser window.');
      console.log('After login, press Enter here to continue...\n');
      await new Promise(resolve => {
        const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
        rl.question('', () => { rl.close(); resolve(); });
      });
      await delay(2000);
    } else {
      console.log('✓ Already logged in');
    }

    isInitialized = true;
    isPageReady = true;
    chatSessionId = 1;
    console.log('✓ Browser initialized successfully\n');
    return true;
  } catch (error) {
    console.error('Failed to initialize browser:', error.message);
    return false;
  }
}

// ============================================================
// PAGE READINESS CHECK
// ============================================================

async function verifyPageReady(maxWaitMs = 15000) {
  const inputSel = 'textarea, div[role="textbox"]';
  const startTime = Date.now();

  console.log('🔍 Verifying page readiness...');

  try {
    await page.waitForSelector(inputSel, { visible: true, timeout: maxWaitMs });

    const isInteractive = await page.evaluate((selector) => {
      const el = document.querySelector(selector);
      if (!el) return false;
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return (
        rect.width > 0 &&
        rect.height > 0 &&
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        style.pointerEvents !== 'none' &&
        !el.disabled
      );
    }, inputSel);

    if (!isInteractive) {
      await delay(2000);
      const retryInteractive = await page.evaluate((selector) => {
        const el = document.querySelector(selector);
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && !el.disabled;
      }, inputSel);

      if (!retryInteractive) {
        throw new Error('Input field found but not interactive after retry');
      }
    }

    const elapsed = Date.now() - startTime;
    console.log(`✓ Page ready in ${elapsed}ms`);
    isPageReady = true;
    return true;

  } catch (error) {
    const elapsed = Date.now() - startTime;
    console.error(`❌ Page readiness failed after ${elapsed}ms: ${error.message}`);
    isPageReady = false;
    return false;
  }
}

// ============================================================
// API ROUTES
// ============================================================

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    initialized: isInitialized,
    timestamp: new Date().toISOString()
  });
});

// ---- SEND PROMPT (fire-and-forget, no waiting for response) ----
app.post('/api/send-prompt', async (req, res) => {
  const requestId = Date.now();

  try {
    const { text, section, expected_mcqs, content_type } = req.body;
    const expectedMcqs = expected_mcqs || 10;

    if (!text) {
      return res.status(400).json({ success: false, error: 'Text is required' });
    }

    if (!isInitialized) {
      return res.status(503).json({
        success: false,
        error: 'Browser not initialized',
        code: 'NOT_INITIALIZED'
      });
    }

    if (isPaused) {
      return res.status(503).json({
        success: false,
        error: 'Processing is paused',
        code: 'PAUSED'
      });
    }

    // Verify page ready
    if (!isPageReady) {
      const ready = await verifyPageReady(10000);
      if (!ready) {
        return res.status(503).json({
          success: false,
          error: 'Page not ready to accept input',
          code: 'PAGE_NOT_READY'
        });
      }
    }

    // Increment premium counter
    const counter = incrementRequestCounter();

    // Generate system prompt
    const ct = content_type || 'mcq';
    const systemPrompt = ct === 'short_notes'
      ? generateShortNotesPrompt(expectedMcqs)
      : generateSystemPrompt(expectedMcqs);

    const fullPrompt = systemPrompt + '\n\n' + text;

    console.log(`\n${'='.repeat(60)}`);
    console.log(`[${requestId}] Sending prompt to Gemini`);
    console.log(`[${requestId}] Section: ${section || 'unknown'}, Type: ${ct}, Expected: ${expectedMcqs}`);
    console.log(`[${requestId}] Text: ${text.length} chars, Prompt: ${fullPrompt.length} chars`);
    console.log(`[${requestId}] Premium today: ${counter.count}/100`);
    console.log('='.repeat(60));

    // Paste text into input field
    const inputSel = 'textarea, div[role="textbox"]';
    await page.waitForSelector(inputSel, { visible: true, timeout: 15000 });
    await page.bringToFront();
    await delay(500);

    // Clear existing text
    await page.click(inputSel);
    await page.keyboard.down('Control');
    await page.keyboard.press('A');
    await page.keyboard.up('Control');
    await page.keyboard.press('Backspace');
    await delay(500);

    // Paste prompt directly
    await page.evaluate((selector, textContent) => {
      const element = document.querySelector(selector);
      if (element) {
        if (element.tagName === 'TEXTAREA') {
          element.value = textContent;
          element.dispatchEvent(new Event('input', { bubbles: true }));
        } else if (element.getAttribute('role') === 'textbox') {
          element.textContent = textContent;
          element.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }
    }, inputSel, fullPrompt);

    console.log(`✓ Text pasted (${fullPrompt.length} chars)`);
    await delay(1000);

    // Press Enter to send
    await page.keyboard.press('Enter');
    console.log('✓ Prompt sent to Gemini — waiting for user to extract response manually');

    res.json({
      success: true,
      message: 'Prompt sent to Gemini successfully',
      requestId: requestId,
      promptLength: fullPrompt.length,
      premium_count: counter.count
    });

  } catch (error) {
    console.error(`❌ [${requestId}] Send failed:`, error.message);
    res.status(500).json({
      success: false,
      error: error.message,
      code: 'SEND_FAILED'
    });
  }
});

// ---- SEND FIX JSON (ask Gemini to fix broken JSON) ----
app.post('/api/send-fix-json', async (req, res) => {
  const requestId = Date.now();

  try {
    const { broken_json } = req.body;

    if (!broken_json) {
      return res.status(400).json({ success: false, error: 'broken_json is required' });
    }

    if (!isInitialized) {
      return res.status(503).json({
        success: false,
        error: 'Browser not initialized',
        code: 'NOT_INITIALIZED'
      });
    }

    if (isPaused) {
      return res.status(503).json({
        success: false,
        error: 'Processing is paused',
        code: 'PAUSED'
      });
    }

    // Verify page ready
    if (!isPageReady) {
      const ready = await verifyPageReady(10000);
      if (!ready) {
        return res.status(503).json({
          success: false,
          error: 'Page not ready to accept input',
          code: 'PAGE_NOT_READY'
        });
      }
    }

    const fullPrompt = "The following JSON is invalid. Fix it and return ONLY valid JSON array. No explanation, no markdown, just the corrected JSON:\n\n" + broken_json;

    console.log(`\n${'='.repeat(60)}`);
    console.log(`[${requestId}] Sending fix JSON prompt to Gemini`);
    console.log(`[${requestId}] Prompt: ${fullPrompt.length} chars`);
    console.log('='.repeat(60));

    // Paste text into input field
    const inputSel = 'textarea, div[role="textbox"]';
    await page.waitForSelector(inputSel, { visible: true, timeout: 15000 });
    await page.bringToFront();
    await delay(500);

    // Clear existing text
    await page.click(inputSel);
    await page.keyboard.down('Control');
    await page.keyboard.press('A');
    await page.keyboard.up('Control');
    await page.keyboard.press('Backspace');
    await delay(500);

    // Paste prompt directly
    await page.evaluate((selector, textContent) => {
      const element = document.querySelector(selector);
      if (element) {
        if (element.tagName === 'TEXTAREA') {
          element.value = textContent;
          element.dispatchEvent(new Event('input', { bubbles: true }));
        } else if (element.getAttribute('role') === 'textbox') {
          element.textContent = textContent;
          element.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }
    }, inputSel, fullPrompt);

    console.log(`✓ Text pasted (${fullPrompt.length} chars)`);
    await delay(1000);

    // Press Enter to send
    await page.keyboard.press('Enter');
    console.log('✓ Fix Prompt sent to Gemini — waiting for user to extract response manually');

    res.json({
      success: true,
      message: 'Fix prompt sent to Gemini successfully',
      requestId: requestId
    });

  } catch (error) {
    console.error(`❌ [${requestId}] Send fix failed:`, error.message);
    res.status(500).json({
      success: false,
      error: error.message,
      code: 'SEND_FAILED'
    });
  }
});

// ---- EXTRACT RESPONSE (instant grab, no waiting) ----
app.post('/api/extract-response', async (req, res) => {
  try {
    if (!isInitialized) {
      return res.status(503).json({
        success: false,
        error: 'Browser not initialized',
        code: 'NOT_INITIALIZED'
      });
    }

    console.log('📋 Extracting current response from Gemini...');

    const messages = await page.$$('message-content');
    if (messages.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'No messages found on page',
        code: 'NO_MESSAGES'
      });
    }

    // Get the last message (most recent response)
    const lastMessage = messages[messages.length - 1];

    const text = await lastMessage.evaluate(el => {
      // Try code block first
      const codeBlock = el.querySelector('pre code, code[class*="language-"], .code-block code');
      if (codeBlock && codeBlock.textContent.trim().length > 50) {
        return codeBlock.textContent.trim();
      }

      // Try markdown container
      const markdown = el.querySelector('.markdown');
      if (markdown && markdown.textContent.trim().length > 50) {
        return markdown.textContent.trim();
      }

      // Get all text content
      return el.textContent.trim();
    });

    if (!text || text.length < 10) {
      return res.status(404).json({
        success: false,
        error: `Response too short or empty (${text?.length || 0} chars)`,
        code: 'EMPTY_RESPONSE'
      });
    }

    console.log(`✓ Extracted ${text.length} characters`);

    res.json({
      success: true,
      raw_response: text,
      length: text.length
    });

  } catch (error) {
    console.error('❌ Extract failed:', error.message);
    res.status(500).json({
      success: false,
      error: error.message,
      code: 'EXTRACT_FAILED'
    });
  }
});

// ---- RESET CHAT ----
app.post('/api/reset-chat', async (req, res) => {
  const resetStartTime = Date.now();

  try {
    if (!isInitialized) {
      return res.status(503).json({
        success: false,
        error: 'Browser not initialized',
        code: 'NOT_INITIALIZED'
      });
    }

    console.log('🔄 Starting fresh Gemini chat...');
    isPageReady = false;

    const oldSessionId = chatSessionId;
    chatSessionId++;
    console.log(`   Session: ${oldSessionId} → ${chatSessionId}`);

    // Navigate to fresh page
    try {
      await page.goto('https://gemini.google.com/app', {
        waitUntil: 'networkidle2',
        timeout: 30000
      });
    } catch (navError) {
      console.log(`⚠️ networkidle2 failed, retrying with domcontentloaded...`);
      try {
        await page.goto('https://gemini.google.com/app', {
          waitUntil: 'domcontentloaded',
          timeout: 20000
        });
        await delay(5000);
      } catch (navError2) {
        const elapsed = Date.now() - resetStartTime;
        return res.status(500).json({
          success: false,
          error: `Navigation failed: ${navError2.message}`,
          code: 'NAVIGATION_FAILED',
          elapsed_ms: elapsed
        });
      }
    }

    await delay(2000);

    // Verify readiness
    const pageReady = await verifyPageReady(15000);
    if (!pageReady) {
      await delay(3000);
      const retryReady = await verifyPageReady(10000);
      if (!retryReady) {
        const elapsed = Date.now() - resetStartTime;
        return res.status(500).json({
          success: false,
          error: 'Page not ready after reset',
          code: 'PAGE_NOT_READY',
          elapsed_ms: elapsed
        });
      }
    }

    const elapsed = Date.now() - resetStartTime;
    console.log(`✓ Fresh chat started (session ${chatSessionId}, ${elapsed}ms)`);

    res.json({
      success: true,
      message: 'Chat reset successfully',
      chatSessionId: chatSessionId,
      elapsed_ms: elapsed
    });

  } catch (error) {
    const elapsed = Date.now() - resetStartTime;
    console.error(`❌ Reset failed: ${error.message} (${elapsed}ms)`);
    isPageReady = false;
    res.status(500).json({
      success: false,
      error: error.message,
      code: 'RESET_FAILED',
      elapsed_ms: elapsed
    });
  }
});

// ---- PAUSE / RESUME / STATUS ----
app.post('/api/pause', (req, res) => {
  if (isPaused) {
    return res.json({ success: true, message: 'Already paused', pausedAt: pauseTimestamp });
  }
  isPaused = true;
  pauseTimestamp = new Date().toISOString();
  console.log(`⏸️ PAUSED at ${pauseTimestamp}`);
  res.json({ success: true, message: 'Processing paused', pausedAt: pauseTimestamp });
});

app.post('/api/resume', (req, res) => {
  if (!isPaused) {
    return res.json({ success: true, message: 'Not paused' });
  }
  const duration = pauseTimestamp
    ? Math.floor((Date.now() - new Date(pauseTimestamp).getTime()) / 1000)
    : 0;
  isPaused = false;
  pauseTimestamp = null;
  console.log(`▶️ RESUMED (was paused ${duration}s)`);
  res.json({ success: true, message: 'Processing resumed', pauseDurationSeconds: duration });
});

app.get('/api/pause-status', (req, res) => {
  const duration = isPaused && pauseTimestamp
    ? Math.floor((Date.now() - new Date(pauseTimestamp).getTime()) / 1000)
    : 0;
  res.json({ isPaused, pausedAt: pauseTimestamp, pauseDurationSeconds: duration });
});

// ============================================================
// SERVER STARTUP
// ============================================================

async function startServer() {
  const initialized = await initializeBrowser();
  if (!initialized) {
    console.error('Failed to initialize browser. Exiting...');
    process.exit(1);
  }

  app.listen(PORT, () => {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`🚀 Gemini Server running on http://localhost:${PORT}`);
    console.log(`${'='.repeat(60)}\n`);
    console.log('Endpoints:');
    console.log('  GET  /api/health           - Server status');
    console.log('  POST /api/send-prompt      - Send prompt to Gemini');
    console.log('  POST /api/extract-response - Extract current response');
    console.log('  POST /api/reset-chat       - Fresh chat session');
    console.log('  POST /api/pause            - Pause processing');
    console.log('  POST /api/resume           - Resume processing');
    console.log('');
  });
}

// Cleanup on exit
process.on('SIGINT', async () => {
  console.log('\n\nShutting down...');
  if (browser) {
    await browser.close();
  }
  process.exit(0);
});

startServer();
