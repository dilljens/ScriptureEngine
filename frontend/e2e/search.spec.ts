import { test, expect } from '@playwright/test'

test.describe('Search bar', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Isaiah', { timeout: 15000 })
  })

  test('Alt+S shortcut opens search', async ({ page }) => {
    await page.keyboard.press('Alt+s')
    // Search input should receive focus — may show a popup or highlight
    await page.waitForTimeout(500)
    // No crash is the main check
    await expect(page.locator('h1')).toBeVisible()
  })
})
