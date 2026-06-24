import { test, expect } from '@playwright/test'

test.describe('Feature toggles', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })
  })

  test('toggle bar has the expected toggle buttons', async ({ page }) => {
    const toggles = ['LDS Notes', 'Gematria', 'Lexicon', 'Synonymous', 'Antithetic', 'Synthetic', 'Chiasmus']
    for (const label of toggles) {
      await expect(page.locator('button', { hasText: label }).first()).toBeVisible({ timeout: 5000 })
    }
  })

  test('LDS Notes toggle is active by default', async ({ page }) => {
    const fnToggle = page.locator('button', { hasText: 'LDS Notes' }).first()
    // Active toggles have blue background
    await expect(fnToggle).toHaveClass(/bg-blue-100/)
  })

  test('Gematria toggle becomes active on click', async ({ page }) => {
    const gemToggle = page.locator('button', { hasText: 'Gematria' }).first()
    await expect(gemToggle).not.toHaveClass(/bg-blue-100/)
    await gemToggle.click()
    await expect(gemToggle).toHaveClass(/bg-blue-100/)
  })

  test('All On / All Off toggle works', async ({ page }) => {
    // Default state: some on, some off → shows "All On"
    const allToggle = page.locator('button', { hasText: /^All (On|Off)$/ })
    await expect(allToggle).toBeVisible()
    const text1 = await allToggle.textContent()
    await allToggle.click()
    await page.waitForTimeout(300)
    // After click, should show the opposite
    const text2 = await allToggle.textContent()
    expect(text2).not.toBe(text1)
  })

  test('toggling a feature does not break the page', async ({ page }) => {
    // Click a few toggles
    await page.locator('button', { hasText: 'Gematria' }).first().click()
    await page.locator('button', { hasText: 'Chiasmus' }).first().click()
    await page.locator('button', { hasText: 'Direct' }).first().click()
    await page.waitForTimeout(500)
    // h1 should still be visible
    await expect(page.locator('h1')).toContainText('isa', { timeout: 5000 })
  })
})
