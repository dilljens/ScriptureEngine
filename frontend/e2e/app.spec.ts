import { test, expect } from '@playwright/test'

test.describe('App — page load & default state', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
  })

  test('page loads with correct title', async ({ page }) => {
    await expect(page).toHaveTitle('Scripture Engine')
  })

  test('content loads with book name in header', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })
    await expect(page.locator('h1')).toContainText('Isaiah')
  })

  test('toggle bar is visible', async ({ page }) => {
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 })
    await expect(page.locator('button', { hasText: 'LDS Notes' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Gematria' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Direct' })).toBeVisible()
    await expect(page.locator('button', { hasText: 'Chiasmus' })).toBeVisible()
  })

  test('verse text is rendered after loading', async ({ page }) => {
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 })
    const verseText = page.locator('p.text-sm.leading-relaxed')
    await expect(verseText.first()).toBeVisible({ timeout: 15000 })
    const text = await verseText.first().textContent()
    expect(text?.length).toBeGreaterThan(20)
  })
})
