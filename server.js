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

function generateSystemPrompt(expectedMcqs = 20, reviewTopics = []) {
  // Build the review topics section ONLY if reviews are provided
  let reviewSection = '';
  if (reviewTopics && reviewTopics.length > 0) {
    const topicsList = reviewTopics.map((t, i) => `  ${i + 1}. ${t}`).join('\n');
    reviewSection = `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  MANDATORY REVIEW TOPICS — YOU MUST READ AND USE THESE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The following ${reviewTopics.length} topics are REAL past paper topics from actual VU exams, submitted by students.
These are NOT suggestions — they are MANDATORY exam intelligence that you MUST use.

YOUR INSTRUCTIONS:
1. READ every single topic below carefully
2. ANALYZE which topics relate to the content in this batch
3. For EACH matching topic, generate exactly 2 MCQs covering that exact concept from different angles.
4. Focus on definitions, comparisons, applications, and conceptual depth for each matching topic.
5. The REMAINING MCQs (to reach your minimum target) should come from other important and conceptual areas in the text that are NOT covered in the reviews.
6. These review-based MCQs are CRITICAL for exam prediction — do NOT skip any matching topic.

REVIEW TOPICS:
${topicsList}

CALCULATION FOR TOTAL MCQS:
- Generate 2 MCQs for each matching review topic.
- If the total MCQs from review topics is LESS than ${expectedMcqs}, generate additional MCQs from other conceptual areas to reach exactly ${expectedMcqs} total MCQs.
- If the total MCQs from review topics is EQUAL TO or GREATER than ${expectedMcqs}, you do NOT need to generate MCQs from other areas. Just output the review-based MCQs.
- If NO topics match the batch content → still generate exactly ${expectedMcqs} MCQs from other conceptual areas.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
  }

  return `You are an expert MCQ generator for Virtual University students preparing for mids and finals exams.

TOTAL REQUIREMENT: You MUST generate AT LEAST ${expectedMcqs} MCQs in total. It should work in a balanced way: generate 2 MCQs per matching review topic, and the remaining MCQs (if any needed to reach ${expectedMcqs}) should come from other important and conceptual areas not covered in the reviews.

PRIORITY ORDER:
1. Prefer VU past paper questions from 2023-2025
2. Focus on frequently repeated and conceptually important topics
3. Always cover the most exam-relevant content from the provided text
${reviewSection}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Response MUST be valid JSON parseable by JSON.parse()
Respond with your JSON inside a JSON code block like:
\`\`\`json
[...your JSON array here...]
\`\`\`
No explanations or extra text outside the code block
Never repeat questions or concepts
Each question must be short and clear
Each MCQ must contain exactly 4 options

CORRECT JSON FORMAT:
\`\`\`json
[{"question":"What is virtual storage?","options":["RAM extension","Disk-based memory","Cache memory","ROM type"],"correct":"Disk-based memory","explanation":"Virtual storage uses disk space as extended memory."},{"question":"What is cache memory?","options":["Fast memory","Slow memory","Disk storage","Network storage"],"correct":"Fast memory","explanation":"Cache is high-speed memory close to CPU."}]
\`\`\`

REQUIRED FIELDS (ALL MANDATORY):
question: string (SHORT, 15-20 words max)
options: array of EXACTLY 4 strings (each option 2-8 words)
correct: string (MUST match one option EXACTLY)
explanation: string (brief, 1-2 sentences)

REMEMBER: If your JSON has ANY syntax error, the entire batch fails. Make it PERFECT.
REMEMBER: MINIMUM ${expectedMcqs} MCQs is NON-NEGOTIABLE. Always deliver at least ${expectedMcqs}.

TEXT TO ANALYZE:
`;
}

function generateShortNotesPrompt(expectedNotes = 20, reviewTopics = []) {
  let reviewSection = '';

  if (reviewTopics && reviewTopics.length > 0) {
    const topicsList = reviewTopics.map((t, i) => `  ${i + 1}. ${t}`).join('\n');

    reviewSection = `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ MANDATORY REVIEW TOPICS (EXAM INTELLIGENCE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REVIEW TOPICS:
${topicsList}

STRICT REVIEW MATCHING RULES:
1. First, identify ONLY the review topics that are a direct/strong match with the PDF content.
2. If a review topic is not clearly supported by the PDF, ignore it completely.
3. For EACH matched review topic, generate EXACTLY 2 short notes.
4. Review-based notes must come first in the output.
5. After review notes, generate ONLY important conceptual notes from the PDF.
6. Conceptual notes must be high-probability, exam-relevant, and non-repetitive.
7. If review topics match, generate at most 5 conceptual notes.
8. If no review topics match, generate at most ${expectedNotes} total notes.

COUNT CONTROL:
- Matched review topic = exactly 2 notes each
- Conceptual notes = 0 to 5 only when review matches exist
- HARD CAP:
  - If no review matches → MAX ${expectedNotes} total notes
  - If review matches exist → MAX (matchedReviewTopics × 2) + 5 total notes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
  }

  return `You are an expert academic short-note generator for Virtual University students.

CORE RULE:
- If no review topics match the PDF, generate at most ${expectedNotes} short notes total.
- If review topics match the PDF, generate exactly 2 short notes per matched review topic, then add at most 5 conceptual notes.

PRIORITY ORDER:
1. Review topics (only if they match the PDF)
2. High-probability exam concepts
3. Important conceptual explanations (Why / How / Differences)

${reviewSection}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON:

\`\`\`json
[
  {
    "question": "string (short and clear)",
    "answer": "string (concise explanation)"
  }
]
\`\`\`

STRICT RULES:
- No duplicates
- No rewording same idea
- No forced review usage
- Do not invent topics outside the PDF
- Keep answers concise and exam-focused
- Respect the hard cap exactly

TEXT TO ANALYZE:
`;
}

function generateReviewStructuringPrompt() {
  return `You are an expert data structuring assistant for Virtual University course reviews.

Your task is to extract and structure student reviews from the raw, unstructured text provided below.

The input text may contain:
- Reviews in multiple languages (Urdu, Roman Urdu, English, etc.)
- Unrelated text mixed in with the reviews
- Multiple reviews for different subjects
- Duplicate reviews

RULES:

1. Extract ONLY actual student reviews about courses/subjects
2. Ignore any unrelated text that is not a review
3. Translate ALL reviews into clear, natural English
4. Extract the subject/course code (e.g., MGT501, CS101, ENG201) from each review's context
5. Extract the review date if mentioned in the text, otherwise set to null
6. If the current batch contains 100% duplicate reviews, ignore duplicates and keep only ONE unique structured review
7. Return the result inside a JSON code block

OUTPUT FORMAT:

Respond with your JSON inside a JSON code block like:
\`\`\`json
[
  {
    "subject_code": "MGT501",
    "review": "The exact review text translated to English",
    "review_date": "2024-03-15"
  },
  {
    "subject_code": "CS101",
    "review": "Another review translated to English",
    "review_date": null
  }
]
\`\`\`

REQUIRED FIELDS (ALL MANDATORY):

subject_code: string (e.g., "MGT501", "CS101", "ENG201")
review: string (the review translated to English, preserve original meaning)
review_date: string or null (date in YYYY-MM-DD format if available, null otherwise)

IMPORTANT:
- Do NOT add any extra fields
- Do NOT include reviews that are just greetings or unrelated messages
- Keep the translation accurate and natural
- If you cannot determine the subject code, use "UNKNOWN"

RAW TEXT TO PROCESS:
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
    const { text, section, expected_mcqs, content_type, review_topics } = req.body;
    const expectedMcqs = expected_mcqs || 10;
    const reviews = Array.isArray(review_topics) ? review_topics : [];

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

    // Generate system prompt — reviews are embedded DIRECTLY into the system prompt
    const ct = content_type || 'mcq';
    let systemPrompt;
    if (ct === 'reviews') {
      systemPrompt = generateReviewStructuringPrompt();
    } else if (ct === 'short_notes') {
      systemPrompt = generateShortNotesPrompt(expectedMcqs, reviews);
    } else {
      systemPrompt = generateSystemPrompt(expectedMcqs, reviews);
    }

    const fullPrompt = systemPrompt + '\n\n' + text;

    console.log(`\n${'='.repeat(60)}`);
    console.log(`[${requestId}] Sending prompt to Gemini`);
    console.log(`[${requestId}] Section: ${section || 'unknown'}, Type: ${ct}, Expected: ${expectedMcqs}`);
    console.log(`[${requestId}] Text: ${text.length} chars, Prompt: ${fullPrompt.length} chars`);
    console.log(`[${requestId}] Review topics embedded: ${reviews.length}`);
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
