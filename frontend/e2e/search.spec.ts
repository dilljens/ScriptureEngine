import { test, expect } from '@playwright/test'

test.describe('Search bar', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1')).toBeVisible({ timeout: 20000 })
  })

  test('reference search: "isa 3" navigates to Isaiah 3', async ({ page }) => {
    // Type "isa 3" in the search input
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill('isa 3')

    // Dropdown should appear with "Go to" result (label uses full book title now)
    const refResult = page.locator('button').filter({ hasText: 'Go to Isaiah' })
    await expect(refResult).toBeVisible({ timeout: 5000 })

    await searchInput.press('Enter')
    await expect(page.locator('h1')).toContainText('ch. 3', { timeout: 10000 })
  })

  test('reference search: "gen 1:1" navigates to Genesis 1', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill('gen 1:1')

    // Label now shows full book title "Genesis 1:1"
    const refResult = page.getByText(/Go to .*Genesis/)
    await expect(refResult).toBeVisible({ timeout: 5000 })

    await searchInput.press('Enter')
    await expect(page.locator('h1')).toContainText('ch. 1', { timeout: 10000 })
  })

  test('full-text search shows FTS results when no book matches', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]')
    // Use a distinctive word that should match text but is not a book name
    await searchInput.fill('mercy')

    // Should see text results (verse text snippets)
    await expect(page.locator('.text-xs.text-neutral-600').first()).toBeVisible({ timeout: 10000 })
    // Should NOT see a ref result (mercy is not a book)
    await expect(page.getByText('Go to ')).not.toBeVisible()
  })

  test('mouse click on ref result navigates', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill('exo 20')

    // Uses full book title now (e.g. "Exodus 20" instead of "exo 20")
    const refResult = page.locator('button').filter({ hasText: 'Go to' }).first()
    await expect(refResult).toBeVisible({ timeout: 5000 })

    await refResult.click()
    await expect(page.locator('h1')).toContainText('ch. 20', { timeout: 10000 })
  })

  test('Alt+S shortcut focuses search input', async ({ page }) => {
    await page.keyboard.press('Alt+s')
    await expect(page.locator('h1')).toBeVisible()
  })
})
