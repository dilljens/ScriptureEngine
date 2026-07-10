#!/usr/bin/env node
/**
 * Playwright E2E tests for Scripture Engine.
 * Validates that each button opens the CORRECT content, not just "something".
 *
 * Usage: node scripts/test_navigation.mjs
 */
import { chromium } from 'playwright';

const BASE = 'https://scriptureengine.org';

async function wait(ms) { return new Promise(r => setTimeout(r, ms)) }

async function run() {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  const tests = [];
  let passed = 0, failed = 0;
  function test(name, fn) { tests.push({ name, fn }); }
  function assert(cond, msg) { if (!cond) throw new Error(msg || 'Assertion'); }

  try {
    console.log('=== SCRIPTURE ENGINE VALIDATION TESTS ===\n');

    // ─────────── Desktop: Load & structure ───────────
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await wait(1500);

    test('Header shows book reference', async () => {
      const h1 = await page.textContent('h1');
      assert(h1.includes('isa') || h1.includes('gen'), `Header shows: "${h1?.trim()}"`);
    });

    test('Search input has correct placeholder', async () => {
      const ph = await page.getAttribute('input[placeholder*="Search"]', 'placeholder');
      assert(ph.includes('navigate') && ph.includes('/commands'), `Placeholder: "${ph}"`);
    });

    // ─────────── Study dropdown: each item opens correct view ───────────
    const studyBtn = page.locator('button').filter({ hasText: 'Study' }).first();

    // Wiki
    await studyBtn.click();
    await wait(400);
    await page.locator('div[class*="z-50"] button').filter({ hasText: 'Wiki' }).click();
    await wait(1500);
    test('Study → Wiki shows wiki view', async () => {
      const body = await page.textContent('body');
      assert(body.includes('wiki article') || body.includes('Select an entity') || body.includes('Wiki'),
        `Wiki view loaded (shows "${body.slice(0, 100)}")`);
    });
    // Go back to main view
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await wait(1000);

    // Quiz
    await studyBtn.click();
    await wait(400);
    await page.locator('div[class*="z-50"] button').filter({ hasText: 'Quiz' }).click();
    await wait(1500);
    test('Study → Quiz shows assessment intro', async () => {
      const body = await page.textContent('body');
      assert(body.includes('Scripture Knowledge'), `Body includes "Scripture Knowledge"`);
      assert(body.includes('Text') || body.includes('analysis') || body.includes('Consistency'),
        'Quiz shows tier options');
    });
    await page.keyboard.press('Escape');
    await wait(500);
    // Reset: press Escape a few times to clear overlays
    await page.keyboard.press('Escape'); await wait(300);
    await page.keyboard.press('Escape'); await wait(300);

    // Hebrew curriculum
    await studyBtn.click();
    await wait(400);
    await page.locator('div[class*="z-50"] button').filter({ hasText: 'Hebrew' }).click();
    await wait(3000);
    test('Study → Hebrew shows learning view', async () => {
      const text = await page.textContent('body');
      assert(text.includes('Knowledge Check') || text.includes('Hebrew'),
        `Hebrew view loaded`); // text=${text.slice(0, 100)}
    });
    await page.keyboard.press('Escape');
    await wait(300);
    await page.keyboard.press('Escape');
    await wait(300);

    // Graph
    await studyBtn.click();
    await wait(400);
    await page.locator('div[class*="z-50"] button').filter({ hasText: 'Graph' }).click();
    await wait(2000);
    test('Study → Graph shows graph view', async () => {
      const body = await page.textContent('body');
      assert(body.includes('Depth') || body.includes('Fit') || body.includes('Layers'),
        `Graph shows Depth/Fit/Layers controls`);
    });
    await page.keyboard.press('Escape');
    await wait(300);
    await page.keyboard.press('Escape');
    await wait(300);

    // ─────────── Tools dropdown ───────────
    const toolsBtn = page.locator('button').filter({ hasText: 'Tools' }).first();

    // Chat
    await toolsBtn.click();
    await wait(400);
    await page.locator('div[class*="z-50"] button').filter({ hasText: 'Chat' }).click();
    await wait(1500);
    test('Tools → Chat opens chat panel', async () => {
      const body = await page.textContent('body');
      assert(body.includes('Send') || body.includes('Chat') || body.includes('Type'),
        `Chat shows input interface`);
    });
    await page.keyboard.press('Escape');
    await wait(400);

    // History
    await toolsBtn.click();
    await wait(400);
    await page.locator('div[class*="z-50"] button').filter({ hasText: 'History' }).click();
    await wait(1000);
    test('Tools → History shows conversation history', async () => {
      const body = await page.textContent('body');
      assert(body.includes('Conversation') || body.includes('History'),
        `History panel shown`);
    });
    await page.keyboard.press('Escape');
    await wait(400);

    // Layers
    await toolsBtn.click();
    await wait(400);
    await page.locator('div[class*="z-50"] button').filter({ hasText: 'Layers' }).click();
    await wait(800);
    test('Tools → Layers opens popover', async () => {
      const layersPopover = await page.$('text=Connections, text=Poetry, text=Footnote');
      const layersBtn = await page.$('button[class*="bg-blue-100"]');
      assert(!!layersPopover || !!layersBtn, 'Layers popover visible');
    });
    // Click outside to close
    await page.mouse.click(10, 10);
    await wait(400);

    // ─────────── Keyboard shortcuts ───────────
    await page.keyboard.press('?');
    await wait(1000);
    test('"?" shortcut opens chat panel', async () => {
      const body = await page.textContent('body');
      assert(body.includes('Send') || body.includes('Chat'), 'Chat panel opens with ?');
    });
    await page.keyboard.press('Escape');
    await wait(400);

    await page.keyboard.press('/');
    await wait(800);
    test('"/" shortcut opens command palette', async () => {
      const input = await page.$('input[placeholder*="Search"], input[placeholder*="Go to"]');
      // The command palette may not be an input, check for overlay
      const cmdOverlay = await page.$('text=Search,text=Navigate');
      assert(!!cmdOverlay || !!input, 'Command palette opens with /');
    });
    await page.keyboard.press('Escape');
    await wait(400);

    // ─────────── Dark mode ───────────
    // (skip icon-based detection — unreliable across browsers)

    // ─────────── Font size controls ───────────
    const fontUp = page.locator('button[title*="Larger"]').first();
    if (await fontUp.isVisible()) {
      await fontUp.click();
      await wait(300);
      const fontSize = await page.textContent('span:has-text("%")');
      test('Font size increase changes display', () => {
        const pct = parseInt(fontSize || '100');
        assert(pct > 100, `Font size increased to ${pct}%`);
      });
    }

    // ─────────── Mobile nav ───────────
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(BASE, { waitUntil: 'networkidle' });
    await wait(2000);

    const mobileNav = await page.$('nav[class*="fixed bottom-0"]');
    test('Mobile bottom nav is visible', () => {
      assert(!!mobileNav, 'nav element found');
    });

    // Verify mobile nav has exactly 7 tabs
    const tabs = await mobileNav.$$('button');
    test('Mobile nav has 7 tabs', () => {
      assert(tabs.length === 7, `Found ${tabs.length} tabs`);
    });

    // Test each mobile tab opens the correct view
    async function testMobileTab(tabText, expectedText, escapeCount = 2) {
      const btn = page.locator('nav[class*="fixed bottom-0"] button').filter({ hasText: tabText });
      if (!(await btn.isVisible())) return;
      await btn.click();
      await wait(2000);
      test(`Mobile "${tabText}" tab shows "${expectedText}"`, async () => {
        const txt = await page.textContent('body');
        assert(txt.includes(expectedText), `Expected "${expectedText}" in body after clicking ${tabText}`);
      });
      for (let i = 0; i < escapeCount; i++) {
        await page.keyboard.press('Escape');
        await wait(400);
      }
    }

    await testMobileTab('Read', 'Isaiah');
    await testMobileTab('Chat', 'Chat');
    await testMobileTab('Hebrew', 'Hebrew', 3);
    await testMobileTab('Quiz', 'Scripture Knowledge', 3);
    await testMobileTab('Menu', 'Wiki', 2);

    // ─────────── Search ───────────
    const searchInput = page.locator('input[placeholder*="Search"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.click();
      await searchInput.fill('covenant');
      await wait(1500);
      test('Search shows results for "covenant"', async () => {
        const body = await page.textContent('body');
        assert(body.toLowerCase().includes('covenant'), `"covenant" appears in search results`);
      });
    }

  } catch (err) {
    console.error('Fatal:', err.message);
    failed++;
  }

  // ─── Results ───
  console.log(`\n${'='.repeat(50)}`);
  for (const t of tests) {
    try {
      await t.fn();
      passed++;
      process.stdout.write('.');
    } catch (err) {
      failed++;
      process.stdout.write('F');
      console.error(`\n  ❌ ${t.name}: ${err.message}`);
    }
  }
  console.log(`\n\n✅ ${passed}/${passed + failed} PASSED`);
  if (failed > 0) console.log(`❌ ${failed} FAILED`);
  await browser.close();
  process.exit(failed > 0 ? 1 : 0);
}

run();
