
const puppeteer = require('puppeteer');
const readline = require('readline');

(async () => {
  const browser = await puppeteer.launch({
    headless: false,
    // executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    userDataDir: './session',
    defaultViewport: null,
    args: ['--start-maximized', '--disable-blink-features=AutomationControlled']
  });

  const page = await browser.newPage();
  await page.evaluateOnNewDocument(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
  });

  await page.goto('https://gemini.google.com/app', { waitUntil: 'networkidle2' });

  // Simple check: if app textarea (logged-in UI) exists, skip login
  const isLoggedIn = await page.$('textarea, div[role="textbox"], .text-input-field_textarea-wrapper') !== null;

  if (!isLoggedIn) {
    console.log('Not logged in. Please complete login (manually if 2FA). After login, press Enter here to continue...');
    await new Promise(resolve => {
      const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
      rl.question('', () => { rl.close(); resolve(); });
    });
    // give page time to update after manual login
    await page.waitForTimeout(2000);
  } else {
    console.log('Already logged in — skipping login flow.');
  }

  // Now type query (example)
  try{
  const inputSel = 'textarea, div[role="textbox"], .text-input-field_textarea-wrapper';
  await page.waitForSelector(inputSel, { visible: true, timeout: 15000 });
  await page.bringToFront();
  await page.type(inputSel, 'Hello Gemini!', { delay: 80 });
  await page.keyboard.press('Enter');

  // answer content extraction (example)
const host = await page.waitForSelector('message-content', { visible: true, timeout: 30000 });
const text = await host.evaluate(el => {
  const inner = el.querySelector('.markdown');
  return inner ? inner.textContent.trim() : '';
});
await page.bringToFront();
await page.type(inputSel, text, { delay: 80 });

// switch model
await page.click('.logo-pill-label-container.input-area-switch-label', { delay: 100 });
await page.waitForSelector('.mat-mdc-menu-item.bard-mode-list-button', { visible: true, timeout: 5000 });
await page.waitForTimeout(500); // wait for menu animation
const modelButtons = await page.$$('.mat-mdc-menu-item.bard-mode-list-button');
if (modelButtons.length > 0) {
  await modelButtons[0].click(); // click first model option
  console.log('Model switched successfully');
} else {
  console.log('No model buttons found');
}

  }catch(e){
    console.log('Error during query/response:', e.message || e);
  }

  // keep browser open for inspection
})();
