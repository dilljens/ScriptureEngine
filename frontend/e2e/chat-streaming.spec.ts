import { test, expect } from '@playwright/test'

test.describe('Chat streaming — real-time responses', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('open chat tab via ? key', async ({ page }) => {
    await page.keyboard.press('?')
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 8000 })
  })

  test('chat has response mode selector', async ({ page }) => {
    await page.keyboard.press('?')
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 8000 })
    // Response mode button should be visible (Auto/S/M/D)
    const modeBtn = page.locator('button[aria-label^="Response mode:"]').first()
    await expect(modeBtn).toBeVisible({ timeout: 5000 })
  })

  test('verse preview appears when typing a reference', async ({ page }) => {
    await page.keyboard.press('?')
    const input = page.getByPlaceholder(/Ask about/i)
    await expect(input).toBeVisible({ timeout: 8000 })
    await input.fill('gen.1.1')
    // Verse preview card should appear
    const preview = page.locator('text=/Genesis 1:1|gen 1|gen.1.1/i').first()
    await expect(preview).toBeVisible({ timeout: 5000 })
  })

  test('suggestion buttons appear in welcome message', async ({ page }) => {
    await page.keyboard.press('?')
    // Wait for welcome message to render
    await page.waitForTimeout(2000)
    // Look for suggestion-style buttons (%%CLICK markers → buttons with text)
    const suggestionBtn = page.locator('button:has-text("Angel of YHWH"), button:has-text("temple"), button:has-text("Yom Kippur")').first()
    await expect(suggestionBtn).toBeVisible({ timeout: 10000 })
  })

  test('clicking suggestion shows prebuilt response instantly', async ({ page }) => {
    await page.keyboard.press('?')
    await page.waitForTimeout(2000)
    // Click a suggestion button
    const suggestion = page.locator('button:has-text("Yom Kippur")').first()
    await expect(suggestion).toBeVisible({ timeout: 10000 })
    await suggestion.click()
    // Prebuilt response should appear (no API call needed)
    await expect(page.locator('text=/Yom Kippur|Day of Atonement/i').first()).toBeVisible({ timeout: 8000 })
  })

  test('response mode menu opens and can change mode', async ({ page }) => {
    await page.keyboard.press('?')
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 8000 })
    // Click the mode button
    const modeBtn = page.locator('button[aria-label^="Response mode:"]').first()
    await expect(modeBtn).toBeVisible({ timeout: 5000 })
    await modeBtn.click()
    // Dropdown should show mode options
    await expect(page.locator('text=/Deep|Short|Medium/i').first()).toBeVisible({ timeout: 5000 })
  })

  test('recent conversations button is visible', async ({ page }) => {
    await page.keyboard.press('?')
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 8000 })
    const recentBtn = page.locator('button:has-text("Recent")').first()
    await expect(recentBtn).toBeVisible({ timeout: 5000 })
  })

  test('completed streamed response remains visible after done event', async ({ page }) => {
    await page.route('**/api/v1/chat/stream', async route => {
      const body = [
        `data: ${JSON.stringify({ type: 'thinking', content: 'checking' })}\n\n`,
        `data: ${JSON.stringify({ type: 'text', content: 'The response stays visible after done.' })}\n\n`,
        `data: ${JSON.stringify({
          type: 'done',
          final_content: 'The response stays visible after done.',
          final_reasoning: 'checking',
          usage: {}, cost: {}, model: 'test-model', tool_results: [],
        })}\n\n`,
      ].join('')
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
        body,
      })
    })

    await page.keyboard.press('?')
    const input = page.getByPlaceholder(/Ask about/i)
    await expect(input).toBeVisible({ timeout: 8000 })
    await input.fill('test streamed answer')
    await input.press('Enter')

    const answer = page.getByText('The response stays visible after done.', { exact: false }).last()
    await expect(answer).toBeVisible({ timeout: 10000 })
    // A second assertion after React's terminal cleanup catches the original
    // bug: content appeared during streaming, then vanished on done.
    await page.waitForTimeout(250)
    await expect(answer).toBeVisible()
  })
})
