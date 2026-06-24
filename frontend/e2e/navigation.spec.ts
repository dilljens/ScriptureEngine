import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 })
  })

  test('keyboard ArrowRight navigates chapters', async ({ page }) => {
    // Get the first verse text before navigating
    const verseBefore = await page.locator('p.text-sm.leading-relaxed').first().textContent()

    // ArrowRight goes to next chapter
    await page.keyboard.press('ArrowRight')
    await page.waitForTimeout(2000)

    // Verse text should change
    const verseAfter = await page.locator('p.text-sm.leading-relaxed').first().textContent()
    expect(verseAfter).not.toBe(verseBefore)
  })

  test('zoom out to book view and back', async ({ page }) => {
    // ArrowUp to zoom out to book view
    await page.keyboard.press('ArrowUp')
    await expect(page.locator('h2', { hasText: 'Isaiah' })).toBeVisible({ timeout: 5000 })

    // Chapter grid should be visible
    await expect(page.getByRole('button', { name: '1', exact: true })).toBeVisible()

    // ArrowDown to go back to chapter view
    await page.keyboard.press('ArrowDown')
    await expect(page.locator('h1')).toContainText('Isaiah', { timeout: 5000 })
  })

  test('zoom out twice to work view', async ({ page }) => {
    await page.keyboard.press('ArrowUp')
    await page.keyboard.press('ArrowUp')
    // Work view shows the current work's books
    await expect(page.getByRole('heading', { name: 'Old Testament', exact: true })).toBeVisible({ timeout: 5000 })
    // Old Testament books should be visible
    await expect(page.getByText('Genesis').first()).toBeVisible()
    await expect(page.getByText('Exodus').first()).toBeVisible()
  })
})
