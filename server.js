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

// Response cache to prevent duplicate requests
const responseCache = new Map();
const CACHE_EXPIRY_MS = 300000; // 5 minutes

// Active request tracking
let activeRequest = null;
let activeRequestText = null;

// Pause state management
let isPaused = false;

// Request counter file for Premium model tracking
const REQUEST_COUNTER_FILE = path.join(__dirname, 'premium_requests.json');

// Load request counter
function loadRequestCounter() {
  try {
    if (fs.existsSync(REQUEST_COUNTER_FILE)) {
      const data = JSON.parse(fs.readFileSync(REQUEST_COUNTER_FILE, 'utf8'));
      const today = new Date().toDateString();
      // Reset counter if it's a new day
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

// Save request counter
function saveRequestCounter(counter) {
  try {
    fs.writeFileSync(REQUEST_COUNTER_FILE, JSON.stringify(counter, null, 2));
  } catch (error) {
    console.error('Error saving request counter:', error);
  }
}

// Increment request counter
function incrementRequestCounter() {
  const counter = loadRequestCounter();
  counter.count++;
  saveRequestCounter(counter);
  console.log(`📊 Premium requests today: ${counter.count}/100`);
  return counter;
}

let pauseTimestamp = null;

// Rate limiting system
let requestCount = 0;
let lastCooldownTime = null;
const MAX_REQUESTS_BEFORE_COOLDOWN = 50;
const COOLDOWN_DURATION_MS = 5 * 60 * 1000; // 5 minutes

// System prompt generator for MCQ generation - ENFORCES PERFECT VALID JSON OUTPUT
function generateSystemPrompt(expectedMcqs = 10) {
  return `You are an expert MCQ generator for Virtual University students preparing for mids and finals examinations.
  You need to think deeply on every request and not respond too quickly, because we need quality output.

CRITICAL - JSON MUST BE 100% VALID

Your response MUST be parseable by JSON.parse() with ZERO errors. Any JSON error will cause the entire batch to fail.

IMPORTANT - RESPONSE FORMAT:
- Respond ONLY with plain text JSON array
- DO NOT use code blocks (no backticks or json markers)
- DO NOT use markdown formatting
- DO NOT add any text before or after the JSON array
- DO NOT include links (YouTube, websites, etc.)
- DO NOT add explanations or notes
- DO NOT add "Here are the MCQs" or similar text
- Just write the JSON directly as plain text in the chat
- ABSOLUTELY NOTHING except the JSON array itself

CRITICAL: Your ENTIRE response must be ONLY the JSON array. First character must be [ and last character must be ].

PRIMARY OBJECTIVE:
Generate EXACTLY ${expectedMcqs} multiple-choice questions specifically for Virtual University students.

MCQ GENERATION STRATEGY (PRIORITY ORDER):

1. FIRST PRIORITY - PAST PAPERS (2023-2025):
   - Search for Virtual University past paper questions from 2023, 2024, and 2025
   - Focus on questions that have appeared multiple times (high recurrence rate)
   - These questions have 80-90% chance of appearing again
   - Mark importance as 5 for frequently recurring questions
   - Mark importance as 4 for questions that appeared once in past papers

2. FALLBACK - AI ANALYSIS:
   - If no past paper data is available for the given topic
   - Generate MCQs based on the most important and fundamental concepts
   - Focus on core topics that are typically tested in university exams
   - Mark importance as 3 for AI-generated questions

3. CRITICAL - NO REPETITION:
   - NEVER repeat the same question twice
   - Ensure each MCQ is unique in wording and concept
   - Ensure every MCQ covers a distinct concept or angle
   - If a concept is important, ask about it differently, do not duplicate the question



ABSOLUTE JSON REQUIREMENTS:

1. START AND END: First character MUST be [ and last character MUST be ]
2. NO EXTRA TEXT: Absolutely NO text before [ or after ]
3. NO MARKDOWN: NO code blocks, NO backticks, NO formatting
4. VALID SYNTAX: Every comma, quote, bracket must be perfect
5. NO TRAILING COMMAS: Never put comma after last item in array/object

COMMON MISTAKES THAT BREAK JSON (DO NOT DO THESE):

- Extra bracket at end: [{"id":1}] ]  <- WRONG! Extra ]
- Trailing comma: [{"id":1,}]  <- WRONG! Comma before }
- Missing comma: [{"id":1}{"id":2}]  <- WRONG! Need comma between objects
- Unescaped quotes: {"q":"What is "cache"?"}  <- WRONG! Must escape: \\\\"cache\\\\"
- Text after JSON: [{"id":1}] Here are the MCQs  <- WRONG! Nothing after ]

CORRECT JSON FORMAT:

[{"id":1,"question":"What is virtual storage?","options":["RAM extension","Disk-based memory","Cache memory","ROM type"],"correct":"Disk-based memory","explanation":"Virtual storage uses disk space as extended memory.","difficulty":"Medium","importance":5,"source":"VU Past Paper 2024"},{"id":2,"question":"What is cache memory?","options":["Fast memory","Slow memory","Disk storage","Network storage"],"correct":"Fast memory","explanation":"Cache is high-speed memory close to CPU.","difficulty":"Easy","importance":4,"source":"VU Past Paper 2023"}]

REQUIRED FIELDS (ALL MANDATORY):

- id: number (1-${expectedMcqs})
- question: string (SHORT, 15-20 words max)
- options: array of EXACTLY 4 strings (each option 2-8 words)
- correct: string (MUST match one option EXACTLY)
- explanation: string (brief, 1-2 sentences)
- difficulty: string ("Easy", "Medium", or "Hard" ONLY)
- importance: number (1-5, where 5 = highest recurrence in past papers)
- source: string ("VU Past Paper YYYY" or "AI Generated" or "VU Syllabus")

QUALITY REQUIREMENTS:

6. Prioritize questions from past papers over AI-generated ones
7. Ensure high predictability for student success
8. ABSOLUTELY NO REPEATED QUESTIONS - Each MCQ must be unique

BEFORE SENDING YOUR RESPONSE:mbiguous
5. Explanation should be concise and educational
6. Prioritize questions from past papers over AI-generated ones
7. Ensure high predictability for student success

BEFORE SENDING YOUR RESPONSE:

- Check: Does it start with [ ?
- Check: Does it end with ] ?
- Check: No text before [ or after ] ?
- Check: All commas in correct places?
- Check: No trailing commas?
- Check: All quotes properly closed?
- Check: Exactly ${expectedMcqs} MCQs OR empty array [] if no data?
- Check: Each MCQ has "source" field indicating origin?
- Check: Importance reflects past paper recurrence?

REMEMBER: If your JSON has ANY syntax error, the entire batch fails and is skipped. Make it PERFECT.

TEXT TO ANALYZE:
`;
}

// System prompt generator for SHORT NOTES - ENFORCES PERFECT VALID JSON OUTPUT
function generateShortNotesPrompt(expectedNotes = 10) {
  return `You are an expert note generator for Virtual University students preparing for mids and finals examinations.
You need to think deeply on every request and not respond too quickly, because we need quality output.

CRITICAL - JSON MUST BE 100% VALID

Your response MUST be parseable by JSON.parse() with ZERO errors. Any JSON error will cause the entire batch to fail.

IMPORTANT - RESPONSE FORMAT:
- Respond ONLY with plain text JSON array
- DO NOT use code blocks (no backticks or json markers)
- DO NOT use markdown formatting
- DO NOT add any text before or after the JSON array
- DO NOT include links (YouTube, websites, videos, or any URLs)
- DO NOT add explanations or notes outside the JSON
- DO NOT add "Here are the notes" or similar text
- Just write the JSON directly as plain text in the chat
- ABSOLUTELY NOTHING except the JSON array itself

CRITICAL: Your ENTIRE response must be ONLY the JSON array. First character must be [ and last character must be ].

PRIMARY OBJECTIVE:
Generate EXACTLY ${expectedNotes} short notes in question-answer format based on the MOST REPEATED and MOST IMPORTANT points from the text.

SHORT NOTES STRATEGY:

1. PRIORITIZE CONCEPTUAL UNDERSTANDING (90%):
   - Focus on "How", "Why", "Explain the significance", "Compare", "Differentiate" type questions.
   - Avoid simple "What is" definition questions unless the term is complex.
   - Target deep understanding of mechanisms, processes, and relationships between concepts.
   - Questions should test understanding, not just memory.

2. IDENTIFY KEY EXAM TOPICS:
   - Focus on fundamental concepts that are essential for university exams.
   - Include formulas, core principles, and critical logic.
   - Ensure the content is relevant to the provided text.

3. CREATE HIGH-QUALITY NOTES:
   - Each note must be in question-answer format.
   - Questions should be direct and clear (10-20 words).
   - Answers must be COMPREHENSIVE yet CONCISE (3-5 sentences, 40-60 words).
   - Explain the concept clearly so the student has NO queries left.
   - Ensure accuracy and clarity.

ABSOLUTE JSON REQUIREMENTS:

1. START AND END: First character MUST be [ and last character MUST be ]
2. NO EXTRA TEXT: Absolutely NO text before [ or after ]
3. NO MARKDOWN: NO code blocks, NO backticks, NO formatting
4. VALID SYNTAX: Every comma, quote, bracket must be perfect
5. NO TRAILING COMMAS: Never put comma after last item in array/object
6. ONLY TWO FIELDS: Each note object must have ONLY "question" and "answer" fields - NOTHING ELSE

CORRECT JSON FORMAT:

[{"question":"Why is virtual memory important for system performance?","answer":"Virtual memory allows running programs larger than physical RAM by using disk space. It prevents system crashes during high load, though excessive swapping can slow down performance (thrashing)."},{"question":"Differentiate between SRAM and DRAM.","answer":"SRAM is faster, more expensive, and uses flip-flops (no refresh needed), used in Cache. DRAM is slower, cheaper, uses capacitors (needs periodic refresh), and is used for Main Memory."}]

REQUIRED FIELDS (ONLY THESE TWO):

- question: string (direct question, 10-20 words max)
- answer: string (Clear, accurate explanation, 3-5 sentences, 40-60 words max)

FORBIDDEN - DO NOT INCLUDE:

- NO "id" field
- NO "difficulty" field
- NO "importance" field
- NO "source" field
- NO "options" field
- NO "explanation" field
- NO links, URLs, or references to external resources
- NO videos or multimedia references
- NO long paragraphs or detailed explanations
- ONLY "question" and "answer" fields

QUALITY REQUIREMENTS:

1. 90% CONCEPTUAL QUESTIONS: Focus on logic, mechanisms, and reasons (How/Why).
2. 10% DEFINITIONS: Only for very complex terms.
3. COMPREHENSIVE ANSWERS: Explain clearly to remove all doubts (40-60 words).
4. ACCURACY: Ensure technical correctness.
5. NO REPETITION: Each note must cover a unique concept.
6. CLARITY: Use simple, direct language for easy understanding.

BEFORE SENDING YOUR RESPONSE:

- Check: Does it start with [ ?
- Check: Does it end with ] ?
- Check: No text before [ or after ] ?
- Check: All commas in correct places?
- Check: No trailing commas?
- Check: All quotes properly closed?
- Check: Each object has ONLY "question" and "answer" fields?
- Check: No extra fields like id, difficulty, importance, etc.?
- Check: Answers are DETAILED enough (40-60 words)?
- Check: Exactly ${expectedNotes} notes 

REMEMBER: If your JSON has ANY syntax error, the entire batch fails and is skipped. Make it PERFECT.

TEXT TO ANALYZE:
`;
}


// Helper function to replace deprecated page.waitForTimeout
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Initialize browser and login
async function initializeBrowser() {
  if (isInitialized) {
    console.log('Browser already initialized');
    return true;
  }

  try {
    console.log('Launching browser...');
    browser = await puppeteer.launch({
      headless: false,
      userDataDir: './session',
      defaultViewport: null,
      args: ['--start-maximized', '--disable-blink-features=AutomationControlled']
    });

    page = await browser.newPage();
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => false });
    });

    // OPTIMIZATION: Block unnecessary resources to speed up loading
    await page.setRequestInterception(true);
    page.on('request', (req) => {
      const resourceType = req.resourceType();
      if (['image', 'stylesheet', 'font', 'media'].includes(resourceType)) {
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
    console.log('✓ Browser initialized successfully\n');
    return true;
  } catch (error) {
    console.error('Failed to initialize browser:', error.message);
    return false;
  }
}

// Extract response from Gemini - ADVANCED ROBUST DETECTION
async function waitForResponse(timeoutMs = 180000, domDelayMs = 1000) {
  try {
    const startTime = Date.now();
    console.log('🔍 Waiting for Gemini to finish generating...');
    
    // Wait for response to start appearing
    await page.waitForSelector('message-content', { visible: true, timeout: 120000 });
    await delay(800); // Increased from 300ms - ensure content starts properly
    
    // ADVANCED: Use MutationObserver to detect when DOM stops changing
    const generationComplete = await page.evaluate((maxWaitMs) => {
      return new Promise((resolve, reject) => {
        const startTime = Date.now();
        let lastMutationTime = Date.now();
        let stableCount = 0;
        const STABLE_CHECKS_NEEDED = 5; // Increased from 3 - more conservative
        const STABLE_DURATION_MS = 1500; // Increased from 800ms - safer detection
        
        // Get the last message container
        const messages = document.querySelectorAll('message-content');
        if (messages.length === 0) {
          reject(new Error('No message-content found'));
          return;
        }
        const lastMessage = messages[messages.length - 1];
        
        // Multiple completion signal checkers
        const checkCompletionSignals = () => {
          const signals = {
            copyButton: false,
            stopButton: false,
            textStable: false,
            cursorGone: false
          };
          
          // Signal 1: Copy button appears (strong indicator)
          const copyButton = lastMessage.querySelector('button[aria-label*="Copy"], button[data-tooltip*="Copy"], button[title*="Copy"]');
          signals.copyButton = copyButton && copyButton.offsetParent !== null;
          
          // Signal 2: Stop button disappears
          const stopButton = document.querySelector('button[aria-label*="Stop"], button[aria-label*="stop"]');
          signals.stopButton = !stopButton || stopButton.offsetParent === null;
          
          // Signal 3: Typing cursor/indicator gone
          const typingIndicator = lastMessage.querySelector('.typing-indicator, .cursor, [class*="typing"]');
          signals.cursorGone = !typingIndicator || typingIndicator.offsetParent === null;
          
          // Signal 4: Text content stable
          const timeSinceLastMutation = Date.now() - lastMutationTime;
          signals.textStable = timeSinceLastMutation >= STABLE_DURATION_MS;
          
          return signals;
        };
        
        // Set up MutationObserver to track DOM changes
        const observer = new MutationObserver((mutations) => {
          // Filter out irrelevant mutations (like class changes on unrelated elements)
          const relevantMutation = mutations.some(mutation => {
            // Check if mutation is in the message content area
            if (mutation.type === 'childList' || mutation.type === 'characterData') {
              return true;
            }
            // Ignore pure class/attribute changes unless it's on the message itself
            return false;
          });
          
          if (relevantMutation) {
            lastMutationTime = Date.now();
            stableCount = 0;
          }
        });
        
        // Observe the last message for changes
        observer.observe(lastMessage, {
          childList: true,
          subtree: true,
          characterData: true,
          attributes: false // Ignore attribute changes to reduce noise
        });
        
        // Polling loop to check completion signals
        const checkInterval = setInterval(() => {
          const elapsed = Date.now() - startTime;
          
          // Timeout check
          if (elapsed >= maxWaitMs) {
            clearInterval(checkInterval);
            observer.disconnect();
            console.log('⚠️ Timeout reached in MutationObserver');
            resolve({ completed: false, reason: 'timeout' });
            return;
          }
          
          const signals = checkCompletionSignals();
          const timeSinceLastMutation = Date.now() - lastMutationTime;
          
          // Log progress every 5 seconds
          if (elapsed % 5000 < 500) {
            console.log(`  Monitoring... (${Math.floor(elapsed/1000)}s) - Copy:${signals.copyButton} Stop:${signals.stopButton} Stable:${signals.textStable} (${Math.floor(timeSinceLastMutation/1000)}s)`);
          }
          
          // Check if generation is complete based on multiple signals
          // Strategy: Either copy button appears OR (stop button gone AND text stable)
          const isComplete = signals.copyButton || 
                           (signals.stopButton && signals.textStable && signals.cursorGone);
          
          if (isComplete) {
            stableCount++;
            
            if (stableCount >= STABLE_CHECKS_NEEDED) {
              clearInterval(checkInterval);
              observer.disconnect();
              console.log(`✓ Generation detected as complete! Signals: Copy=${signals.copyButton}, Stop=${signals.stopButton}, Stable=${signals.textStable}, Cursor=${signals.cursorGone}`);
              resolve({ completed: true, signals });
              return;
            }
          } else {
            stableCount = 0;
          }
        }, 500); // Check every 500ms
      });
    }, timeoutMs);
    
    if (!generationComplete.completed) {
      console.log('⚠️ Generation may not be complete, but proceeding to extract response...');
    } else {
      const detectionTime = Date.now() - startTime;
      console.log(`✓ Generation confirmed complete in ${detectionTime}ms`);
    }
    
    // Small delay to ensure final content is rendered (user-configurable)
    console.log(`⏳ DOM stable delay triggered (${domDelayMs}ms)...`);
    await delay(domDelayMs);
    
    // Now extract the final response
    console.log('📤 JSON return triggered from frontend (Gemini script)...');
    const extractStart = Date.now();
    
    const messages = await page.$$('message-content');
    if (messages.length === 0) {
      throw new Error('No messages found after waiting');
    }
    
    // Get the last message (most recent response)
    const lastMessage = messages[messages.length - 1];
    
    // Try multiple methods to extract text (handle both plain text and code blocks)
    const text = await lastMessage.evaluate(el => {
      // Method 1: Try to get text from code block first (if Gemini uses code blocks despite instructions)
      const codeBlock = el.querySelector('pre code, code[class*="language-"], .code-block code');
      if (codeBlock && codeBlock.textContent.trim().length > 50) {
        return codeBlock.textContent.trim();
      }
      
      // Method 2: Try markdown container
      const markdown = el.querySelector('.markdown');
      if (markdown && markdown.textContent.trim().length > 50) {
        return markdown.textContent.trim();
      }
      
      // Method 3: Get all text content
      return el.textContent.trim();
    });
    
    const extractTime = Date.now() - extractStart;
    console.log(`✓ Extraction completed in ${extractTime}ms`);
    
    if (!text || text.length < 50) {
      throw new Error(`Response too short or empty (${text.length} characters)`);
    }
    
    const totalTime = Date.now() - startTime;
    console.log(`✅ Response ready (${totalTime}ms total, ${text.length} characters)`);
    console.log(`   └─ Breakdown: Detection + Extraction = ${totalTime}ms`);
    return text;
    
  } catch (error) {
    console.error('❌ Error in waitForResponse:', error.message);
    
    // Try one more time to extract any available response
    try {
      console.log('🔄 Attempting recovery...');
      await delay(2000);
      const messages = await page.$$('message-content');
      if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        const text = await lastMessage.evaluate(el => {
          // Try code block first
          const codeBlock = el.querySelector('pre code, code[class*="language-"], .code-block code');
          if (codeBlock && codeBlock.textContent.trim().length > 50) {
            return codeBlock.textContent.trim();
          }
          // Then markdown
          const markdown = el.querySelector('.markdown');
          return markdown ? markdown.textContent.trim() : el.textContent.trim();
        });
        if (text && text.length > 50) {
          console.log(`✓ Recovered response (${text.length} characters)`);
          return text;
        }
      }
    } catch (retryError) {
      console.error('❌ Recovery failed:', retryError.message);
    }
    
    throw new Error(`Failed to get response: ${error.message}`);
  }
}

// Generate cache key for text
function generateCacheKey(text) {
  const crypto = require('crypto');
  return crypto.createHash('md5').update(text).digest('hex');
}

// Clean expired cache entries
function cleanCache() {
  const now = Date.now();
  for (const [key, value] of responseCache.entries()) {
    if (now - value.timestamp > CACHE_EXPIRY_MS) {
      responseCache.delete(key);
    }
  }
}

// Send query to Gemini - SINGLE ATTEMPT, RETURN RAW RESPONSE
async function sendToGemini(text, systemPrompt, domDelayMs = 1000) {
  const inputSel = 'textarea, div[role="textbox"]';
  
  // Check cache first
  const cacheKey = generateCacheKey(text);
  cleanCache();
  
  if (responseCache.has(cacheKey)) {
    const cached = responseCache.get(cacheKey);
    console.log('✓ Using cached response');
    return cached.response;
  }
  
  // Check if there's already an active request for this text
  if (activeRequest && activeRequestText === cacheKey) {
    console.log('⚠️  Request already in progress for this text, waiting...');
    try {
      const result = await activeRequest;
      return result;
    } catch (error) {
      console.log('⚠️  Active request failed');
      activeRequest = null;
      activeRequestText = null;
      throw error;
    }
  }
  
  // Create new request promise - SINGLE ATTEMPT
  const requestPromise = (async () => {
    try {
      console.log('\n🚀 Sending query to Gemini (single attempt)...');
      
      // Wait for input field
      await page.waitForSelector(inputSel, { visible: true, timeout: 15000 });
      await page.bringToFront();
      await delay(500);
      
      // Clear any existing text
      await page.click(inputSel);
      await page.keyboard.down('Control');
      await page.keyboard.press('A');
      await page.keyboard.up('Control');
      await page.keyboard.press('Backspace');
      await delay(500);
      
      // Prepare the full prompt with dynamic system prompt
      const fullPrompt = systemPrompt + '\n\n' + text;
      
      // CRITICAL: Use evaluate to paste text directly instead of typing
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
      
      console.log(`✓ Text pasted successfully (${fullPrompt.length} characters)`);
      await delay(1000);
      
      // Send the query
      await page.keyboard.press('Enter');
      console.log('✓ Query sent, waiting for response...');
      
      // Wait for and extract response with timeout protection
      const response = await Promise.race([
        waitForResponse(180000, domDelayMs),
        new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Overall timeout exceeded')), 180000)
        )
      ]);
      
      if (!response || response.length < 50) {
        throw new Error(`Invalid response (too short: ${response?.length || 0} characters)`);
      }
      
      console.log(`✓ Raw response received (${response.length} characters)`);
      console.log('📤 Returning raw response to Python for auto-correction...');
      
      // Cache the raw response
      responseCache.set(cacheKey, {
        response: response,
        timestamp: Date.now()
      });
      
      return response;
      
    } catch (error) {
      console.error(`❌ Request failed:`, error.message);
      // CRITICAL: Always wait 5 seconds even on error to avoid rapid-fire requests
      console.log('⏳ Waiting mandatory 5 seconds before allowing next request (error recovery)...');
      await new Promise(resolve => setTimeout(resolve, 5000));
      throw error;
    }
  })();
  
  // Track active request
  activeRequest = requestPromise;
  activeRequestText = cacheKey;
  
  try {
    const result = await requestPromise;
    // CRITICAL: Always wait 5 seconds after successful request
    console.log('⏳ Waiting mandatory 5 seconds before allowing next request...');
    await new Promise(resolve => setTimeout(resolve, 2000));
    return result;
  } catch (error) {
    // Error already handled above with delay
    throw error;
  } finally {
    // Clear active request tracking
    if (activeRequestText === cacheKey) {
      activeRequest = null;
      activeRequestText = null;
    }
  }
}

// Clean JSON response (remove markdown, code blocks, fix common issues)

function cleanJsonResponse(text) {
  console.log(`🧹 Cleaning JSON response (${text.length} characters)...`);
  
  // Remove markdown code blocks
  text = text.replace(/```json\s*/gi, '').replace(/```\s*/g, '');
  
  // Remove any text before the first [ or {
  const jsonStart = Math.min(
    text.indexOf('[') !== -1 ? text.indexOf('[') : Infinity,
    text.indexOf('{') !== -1 ? text.indexOf('{') : Infinity
  );
  
  if (jsonStart !== Infinity) {
    text = text.substring(jsonStart);
  }
  
  // Remove any text after the last ] or }
  const jsonEnd = Math.max(text.lastIndexOf(']'), text.lastIndexOf('}'));
  if (jsonEnd !== -1) {
    text = text.substring(0, jsonEnd + 1);
  }
  
  // Fix common HTML entities that break JSON
  text = text.replace(/&quot;/g, '\\"');
  text = text.replace(/&amp;/g, '&');
  text = text.replace(/&lt;/g, '<');
  text = text.replace(/&gt;/g, '>');
  text = text.replace(/&apos;/g, "'");
  
  // Remove HTML tags (they shouldn't be there, but just in case)
  text = text.replace(/<[^>]+>/g, '');
  
  const cleaned = text.trim();
  console.log(`✓ Cleaned to ${cleaned.length} characters`);
  
  // Try to parse and provide helpful error message if it fails
  try {
    JSON.parse(cleaned);
    console.log('✓ JSON validation passed');
  } catch (error) {
    console.error('❌ JSON validation failed:', error.message);
    
    // Show context around the error position
    if (error.message.includes('position')) {
      const match = error.message.match(/position (\d+)/);
      if (match) {
        const pos = parseInt(match[1]);
        const start = Math.max(0, pos - 50);
        const end = Math.min(cleaned.length, pos + 50);
        const context = cleaned.substring(start, end);
        console.error(`Context around error (position ${pos}):`);
        console.error(`...${context}...`);
        console.error(' '.repeat(pos - start + 3) + '^');
      }
    }
    
    throw error;
  }
  
  return cleaned;
}

// Validate MCQ structure
function validateMCQs(mcqs) {
  if (!Array.isArray(mcqs)) {
    throw new Error('Response is not an array');
  }
  
  const requiredFields = ['id', 'question', 'options', 'correct', 'explanation', 'difficulty', 'importance'];
  
  for (let i = 0; i < mcqs.length; i++) {
    const mcq = mcqs[i];
    
    // Check all required fields exist
    for (const field of requiredFields) {
      if (!(field in mcq)) {
        throw new Error(`MCQ ${i} missing field: ${field}`);
      }
    }
    
    // Validate options is array of 4
    if (!Array.isArray(mcq.options) || mcq.options.length !== 4) {
      throw new Error(`MCQ ${i} must have exactly 4 options`);
    }
    
    // Validate correct answer is in options
    if (!mcq.options.includes(mcq.correct)) {
      throw new Error(`MCQ ${i} correct answer not in options`);
    }
  }
  
  return true;
}

// Cooldown check function
async function checkAndApplyCooldown() {
  requestCount++;
  
  if (requestCount >= MAX_REQUESTS_BEFORE_COOLDOWN) {
    console.log('\n⏸️  COOLDOWN TRIGGERED');
    console.log(`Processed ${requestCount} requests. Starting 5-minute cooldown...`);
    
    lastCooldownTime = Date.now();
    const cooldownEnd = new Date(lastCooldownTime + COOLDOWN_DURATION_MS);
    
    console.log(`Cooldown will end at: ${cooldownEnd.toLocaleTimeString()}`);
    
    // Wait for cooldown period
    await delay(COOLDOWN_DURATION_MS);
    
    // Reset counter
    requestCount = 0;
    lastCooldownTime = null;
    
    console.log('✓ Cooldown complete. Resuming processing...\n');
  }
}

// API Routes
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    initialized: isInitialized,
    timestamp: new Date().toISOString()
  });
});

// Reset Gemini chat endpoint
app.post('/api/reset-chat', async (req, res) => {
  try {
    if (!isInitialized) {
      return res.status(503).json({ 
        success: false, 
        error: 'Browser not initialized' 
      });
    }
    
    console.log('🔄 Starting fresh Gemini chat...');
    
    // Use keyboard shortcut: Ctrl + Shift + O
    await page.keyboard.down('Control');
    await page.keyboard.down('Shift');
    await page.keyboard.press('KeyO');
    await page.keyboard.up('Shift');
    await page.keyboard.up('Control');
    
    // Wait for new chat to load
    await delay(2000);
    
    // Clear response cache and active requests
    responseCache.clear();
    activeRequest = null;
    activeRequestText = null;
    
    console.log('✓ Fresh chat started');
    
    res.json({ success: true, message: 'Chat reset successfully' });
  } catch (error) {
    console.error('❌ Failed to reset chat:', error.message);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Cooldown status endpoint
app.get('/api/cooldown-status', (req, res) => {
  const inCooldown = lastCooldownTime !== null;
  const remainingTime = inCooldown 
    ? Math.max(0, COOLDOWN_DURATION_MS - (Date.now() - lastCooldownTime))
    : 0;
  
  res.json({
    requestCount: requestCount,
    maxRequests: MAX_REQUESTS_BEFORE_COOLDOWN,
    requestsUntilCooldown: MAX_REQUESTS_BEFORE_COOLDOWN - requestCount,
    inCooldown: inCooldown,
    cooldownRemainingMs: remainingTime,
    cooldownRemainingMinutes: Math.ceil(remainingTime / 60000)
  });
});

// Pause endpoint
app.post('/api/pause', (req, res) => {
  try {
    if (isPaused) {
      return res.json({ 
        success: true, 
        message: 'Already paused',
        pausedAt: pauseTimestamp
      });
    }
    
    isPaused = true;
    pauseTimestamp = new Date().toISOString();
    
    console.log('⏸️  PROCESSING PAUSED by user request');
    console.log(`   Paused at: ${pauseTimestamp}`);
    
    res.json({ 
      success: true, 
      message: 'Processing paused',
      pausedAt: pauseTimestamp
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Resume endpoint
app.post('/api/resume', (req, res) => {
  try {
    if (!isPaused) {
      return res.json({ 
        success: true, 
        message: 'Not paused'
      });
    }
    
    const pauseDuration = pauseTimestamp ? 
      Math.floor((Date.now() - new Date(pauseTimestamp).getTime()) / 1000) : 0;
    
    isPaused = false;
    const resumedAt = new Date().toISOString();
    
    console.log('▶️  PROCESSING RESUMED by user request');
    console.log(`   Was paused for: ${pauseDuration}s`);
    console.log(`   Resumed at: ${resumedAt}`);
    
    pauseTimestamp = null;
    
    res.json({ 
      success: true, 
      message: 'Processing resumed',
      pauseDurationSeconds: pauseDuration,
      resumedAt: resumedAt
    });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Pause status endpoint
app.get('/api/pause-status', (req, res) => {
  const pauseDuration = isPaused && pauseTimestamp ? 
    Math.floor((Date.now() - new Date(pauseTimestamp).getTime()) / 1000) : 0;
  
  res.json({
    isPaused: isPaused,
    pausedAt: pauseTimestamp,
    pauseDurationSeconds: pauseDuration
  });
});

app.post('/api/generate-mcqs', async (req, res) => {
  const requestId = Date.now();
  
  try {
    const { text, section, expected_mcqs } = req.body;
    const expectedMcqs = expected_mcqs || 10; // Default to 10 if not provided
    const domDelaySeconds = req.body.dom_delay_seconds || 1; // Default to 1 second
    const domDelayMs = domDelaySeconds * 1000; // Convert to milliseconds
    
    if (!text) {
      return res.status(400).json({ 
        success: false,
        error: 'Text is required' 
      });
    }
    
    if (!isInitialized) {
      return res.status(503).json({ 
        success: false,
        error: 'Browser not initialized. Please start the server and complete login.',
        code: 'NOT_INITIALIZED'
      });
    }
    
    // Check if processing is paused
    if (isPaused) {
      console.log(`⏸️  [Request ${requestId}] Rejected - Processing is paused`);
      return res.status(503).json({
        success: false,
        error: 'Processing is paused. Please resume to continue.',
        code: 'PAUSED',
        pausedAt: pauseTimestamp
      });
    }
    
    // Increment and check request counter for Premium model
    const counter = incrementRequestCounter();
    let warningMessage = null;
    
    if (counter.count >= 100) {
      warningMessage = `⚠️ WARNING: You have used ${counter.count}/100 Premium requests today. The model may produce errors or rate limit responses.`;
      console.log(warningMessage);
    }
    
    console.log(`\n${'='.repeat(60)}`);
    console.log(`[Request ${requestId}] Processing ${section || 'unknown'} section`);
    console.log(`[Request ${requestId}] Text length: ${text.length} characters`);
    console.log(`[Request ${requestId}] Expected MCQs: ${expectedMcqs}`);
    console.log(`[Request ${requestId}] Premium requests today: ${counter.count}/100`);
    console.log(`[Request ${requestId}] Current count: ${requestCount + 1}/${MAX_REQUESTS_BEFORE_COOLDOWN}`);
    console.log('='.repeat(60));
    
    // Generate dynamic system prompt based on expected MCQs and content type
    const contentType = req.body.content_type || 'mcq';
    const systemPrompt = contentType === 'short_notes' 
      ? generateShortNotesPrompt(expectedMcqs)
      : generateSystemPrompt(expectedMcqs);
    
    const contentLabel = contentType === 'short_notes' ? 'Short Notes' : 'MCQs';
    console.log(`[Request ${requestId}] Content Type: ${contentLabel}`);
    console.log(`[Request ${requestId}] DOM Delay: ${domDelaySeconds}s`);
    
    // Send to Gemini and get RAW response (no parsing on server)
    const rawResponse = await sendToGemini(text, systemPrompt, domDelayMs);
    
    console.log(`✓ [Request ${requestId}] Raw response obtained (${rawResponse.length} characters)`);
    console.log('='.repeat(60));
    
    // Apply cooldown check AFTER successful response
    await checkAndApplyCooldown();
    
    res.json({
      success: true,
      raw_response: rawResponse,
      cached: responseCache.has(generateCacheKey(text)),
      requestCount: requestCount,
      requestsUntilCooldown: MAX_REQUESTS_BEFORE_COOLDOWN - requestCount,
      premium_request_count: counter.count,
      premium_daily_limit: 100,
      premium_warning: warningMessage
    });

    
  } catch (error) {
    console.error(`❌ [Request ${requestId}] Error:`, error.message);
    console.error('='.repeat(60));
    
    // Determine appropriate status code
    let statusCode = 500;
    let errorCode = 'GENERATION_ERROR';
    
    if (error.message.includes('timeout') || error.message.includes('Timeout')) {
      statusCode = 504;
      errorCode = 'TIMEOUT';
    } else if (error.message.includes('JSON') || error.message.includes('parse')) {
      statusCode = 502;
      errorCode = 'INVALID_RESPONSE';
    } else if (error.message.includes('not initialized') || error.message.includes('login')) {
      statusCode = 503;
      errorCode = 'NOT_INITIALIZED';
    }
    
    res.status(statusCode).json({
      success: false,
      error: error.message,
      code: errorCode,
      requestId: requestId
    });
  }
});

// Start server
async function startServer() {
  // Initialize browser first
  const initialized = await initializeBrowser();
  
  if (!initialized) {
    console.error('Failed to initialize browser. Exiting...');
    process.exit(1);
  }
  
  // Start Express server
  app.listen(PORT, () => {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`🚀 Gemini MCQ Server running on http://localhost:${PORT}`);
    console.log(`${'='.repeat(60)}\n`);
    console.log('Available endpoints:');
    console.log(`  GET  /api/health          - Check server status`);
    console.log(`  POST /api/generate-mcqs   - Generate MCQs from text`);
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

// Start the server
startServer();
