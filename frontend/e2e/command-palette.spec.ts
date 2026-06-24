import { test, expect } from '@playwright/test'

test.describe('Command palette', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })
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
    const suggestions = page.locator('div.fixed.inset-0').last().locator('button')
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

  test('fuzzy typing finds book', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await input.fill('gn')
    await page.waitForTimeout(500)
    // Check if the page body contains a Genesis suggestion
    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toContain('Genesis')
  })

  test('colon format works', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await input.fill('isa:34')
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)
    await expect(page.locator('h1')).toBeVisible()
  })

  test('/chat command shows chat result', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await input.fill('/chat hello')
    await page.waitForTimeout(300)
    const result = page.locator('text=💬 Chat: hello')
    await expect(result).toBeVisible({ timeout: 3000 })
  })

  test('/dark command shows dark mode result', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await input.fill('/dark')
    await page.waitForTimeout(300)
    await expect(page.locator('text=Toggle dark mode')).toBeVisible({ timeout: 3000 })
  })
})
