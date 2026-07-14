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
    const suggestions = page.locator('div.fixed.inset-0').last().locator('button')
    await expect(suggestions.first()).toBeVisible({ timeout: 5000 })
  })

  test('pressing Enter navigates', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await expect(input).toBeVisible({ timeout: 3000 })
    await input.fill('isa 55')
    const suggestions = page.locator('div.fixed.inset-0').last().locator('button')
    await expect(suggestions.first()).toBeVisible({ timeout: 5000 })
    await page.keyboard.press('Enter')
    await expect(page.locator('h1')).toContainText('ch. 55', { timeout: 10000 })
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
    await expect(page.locator('body')).toContainText('Genesis', { timeout: 5000 })
  })

  test('colon format works', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await input.fill('isa:34')
    const suggestions = page.locator('div.fixed.inset-0').last().locator('button')
    await expect(suggestions.first()).toBeVisible({ timeout: 5000 })
    await page.keyboard.press('Enter')
    await expect(page.locator('h1')).toContainText('ch. 34', { timeout: 10000 })
  })

  test('/chat command shows chat result', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await input.fill('/chat hello')
    const result = page.locator('text=💬 Chat: hello')
    await expect(result).toBeVisible({ timeout: 3000 })
  })

  test('/dark command shows dark mode result', async ({ page }) => {
    await page.keyboard.press('/')
    const input = page.getByPlaceholder('isa 55:6')
    await input.fill('/dark')
    await expect(page.locator('text=Toggle dark mode')).toBeVisible({ timeout: 3000 })
  })
})
