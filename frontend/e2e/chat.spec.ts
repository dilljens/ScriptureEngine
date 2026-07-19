import { test, expect } from '@playwright/test'

test.describe('Chat panel — verse links', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('question mark opens chat tab', async ({ page }) => {
    await page.keyboard.press('?')
    const chatTab = page.getByText('Chat').first()
    await expect(chatTab).toBeVisible({ timeout: 5000 })
  })

  test('chat has a send input after opening', async ({ page }) => {
    await page.keyboard.press('?')
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 8000 })
  })

  test('welcome message has text about verse refs', async ({ page }) => {
    await page.keyboard.press('?')
    // Verify the chat content area contains verse reference text
    const chatContent = page.locator('text=/verse references/i').first()
    await expect(chatContent).toBeVisible({ timeout: 10000 })
  })

  test('chat tab title shows heading', async ({ page }) => {
    await page.keyboard.press('?')
    // Wait for chat content to render
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 8000 })
    // Check the heading via text content (more reliable than role selector)
    await expect(page.locator('h2:has-text("Chat")').first()).toBeVisible({ timeout: 5000 })
  })
})
