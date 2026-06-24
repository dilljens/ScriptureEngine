import { test, expect } from '@playwright/test'

test.describe('Settings panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })
  })

  test('F1 opens settings panel', async ({ page }) => {
    await page.keyboard.press('F1')
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible({ timeout: 5000 })
  })

  test('settings panel has dark mode toggle', async ({ page }) => {
    await page.keyboard.press('F1')
    await expect(page.getByText('Dark mode').first()).toBeVisible({ timeout: 5000 })
  })

  test('settings panel has font size controls', async ({ page }) => {
    await page.keyboard.press('F1')
    await expect(page.getByText('Font size').first()).toBeVisible({ timeout: 5000 })
  })

  test('Escape closes settings panel', async ({ page }) => {
    await page.keyboard.press('F1')
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible({ timeout: 5000 })
    await page.keyboard.press('Escape')
    await page.waitForTimeout(500)
    await expect(page.getByRole('heading', { name: 'Settings' })).not.toBeVisible()
  })

  test('question mark key opens chat', async ({ page }) => {
    await page.keyboard.press('?')
    await page.waitForTimeout(1000)
    await expect(page.getByText('Chat').first()).toBeVisible({ timeout: 5000 })
  })
})
