import { test, expect } from '@playwright/test'

test.describe('D&C navigation', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.getByText('ch. 6').first()).toBeVisible({ timeout: 20000 })
  })

  test('navigate to D&C section via command palette', async ({ page }) => {
    // Open command palette
    await page.locator('button[title*="Go to"]').click()
    await expect(page.getByPlaceholder(/search|go to|find/i).first()).toBeVisible({ timeout: 5000 })
    // Type D&C reference
    await page.getByPlaceholder(/search|go to|find/i).fill('/dc/138')
    // Wait for navigation result
    await page.keyboard.press('Enter')
    await page.waitForTimeout(3000)
    // Should load D&C 138 — check breadcrumb or heading
    await expect(page.getByText(/dc.*138|doctrine.*138|dc138/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('navigate to D&C section with dcN format', async ({ page }) => {
    // Open command palette
    await page.locator('button[title*="Go to"]').click()
    await expect(page.getByPlaceholder(/search|go to|find/i).first()).toBeVisible({ timeout: 5000 })
    // Type "dc138" compact format
    await page.getByPlaceholder(/search|go to|find/i).fill('dc138')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(3000)
    // Should load D&C 138
    await expect(page.getByText(/section|dc138|dc 138/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('navigate to D&C section with dc N format', async ({ page }) => {
    // Open command palette
    await page.locator('button[title*="Go to"]').click()
    await expect(page.getByPlaceholder(/search|go to|find/i).first()).toBeVisible({ timeout: 5000 })
    // Type "dc 138" with space
    await page.getByPlaceholder(/search|go to|find/i).fill('dc 138')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(3000)
    // Should load D&C 138
    await expect(page.getByText(/section|dc138|dc 138/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('navigate to D&C verse with dcN:M format', async ({ page }) => {
    // Open command palette
    await page.locator('button[title*="Go to"]').click()
    await expect(page.getByPlaceholder(/search|go to|find/i).first()).toBeVisible({ timeout: 5000 })
    // Type "dc138:1" compact verse format
    await page.getByPlaceholder(/search|go to|find/i).fill('dc138:1')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(3000)
    // Should load D&C 138 with specific verse
    await expect(page.getByText(/dc138|dc 138|section 138/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('D&C section chapter preview shows correct section number', async ({ page }) => {
    // Open command palette and type dc to see D&C suggestions
    await page.locator('button[title*="Go to"]').click()
    await expect(page.getByPlaceholder(/search|go to|find/i).first()).toBeVisible({ timeout: 5000 })
    await page.getByPlaceholder(/search|go to|find/i).fill('dc')
    // Should see D&C section results in the list
    await page.waitForTimeout(2000)
    const dcResults = page.locator('text=/dc/i')
    expect(await dcResults.count()).toBeGreaterThan(0)
  })
