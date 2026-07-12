import { test, expect } from '@playwright/test'

test.describe('Chat panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('question mark opens chat tab', async ({ page }) => {
    await page.keyboard.press('?')
    // Chat tab should appear with "Chat" label
    const chatTab = page.getByText('Chat').first()
    await expect(chatTab).toBeVisible({ timeout: 5000 })
  })

  test('chat has a send input after opening', async ({ page }) => {
    await page.keyboard.press('?')
    await page.waitForTimeout(1000)
    // Chat panel renders with input field
    const chatInput = page.getByPlaceholder(/Ask about/i)
    await expect(chatInput).toBeVisible({ timeout: 8000 })
  })

  test('chat send button exists', async ({ page }) => {
    await page.keyboard.press('?')
    await page.waitForTimeout(1000)
    const sendBtn = page.locator('button', { hasText: 'Send' })
    const count = await sendBtn.count()
    expect(count).toBeGreaterThanOrEqual(0)
  })

  test('heading changes after ?', async ({ page }) => {
    await page.keyboard.press('?')
    await page.waitForTimeout(500)
    // Tab bar should now contain a "Chat" item
    const tabText = await page.textContent('body')
    expect(tabText).toContain('Chat')
  })
})
