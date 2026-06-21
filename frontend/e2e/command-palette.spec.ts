import { test, expect } from '@playwright/test'

test.describe('Command palette', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Isaiah', { timeout: 15000 })
  })

  test('pressing / opens the command palette', async ({ page }) => {
    await page.keyboard.press('/')
    await expect(page.getByPlaceholder('isa 55:6')).toBeVisible({ timeout: 3000 })
  })

  test('typing shows suggestions', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await expect(input).toBeVisible({ timeout: 3000 })

    await input.fill('isa 55')
    await page.waitForTimeout(500)

    const suggestions = page.locator('.fixed.inset-0').last().locator('button')
    expect(await suggestions.count()).toBeGreaterThan(0)
  })

  test('pressing Enter navigates', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await expect(input).toBeVisible({ timeout: 3000 })

    await input.fill('isa 55')
    await page.waitForTimeout(500)

    await page.keyboard.press('Enter')
    await page.waitForTimeout(2000)
    await expect(page.locator('h1')).toBeVisible({ timeout: 10000 })
  })

  test('pressing Escape closes the palette', async ({ page }) => {
    await page.keyboard.press('/')
    await expect(page.getByPlaceholder('isa 55:6')).toBeVisible({ timeout: 3000 })

    await page.keyboard.press('Escape')
    await expect(page.getByPlaceholder('isa 55:6')).not.toBeVisible()
  })
})
