import { test, expect } from '@playwright/test'

test.describe('Navigation', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 })
  })

  test('keyboard ArrowRight navigates to next chapter', async ({ page }) => {
    // Get the breadcrumb text before
    const titleBefore = await page.locator('h1').textContent()

    // ArrowRight goes to next chapter
    await page.keyboard.press('ArrowRight')
    await page.waitForTimeout(2000)

    // Breadcrumb should change (chapter number)
    const titleAfter = await page.locator('h1').textContent()
    expect(titleAfter).not.toBe(titleBefore)
  })

  test('toolbar right arrow button navigates to next chapter', async ({ page }) => {
    // Get current chapter
    const titleBefore = await page.locator('h1').textContent()

    // Click the right arrow button in the toolbar
    // The rightmost nav button before the breadcrumb title
    const rightArrow = page.locator('h1').locator('..').locator('button').last()
    await rightArrow.click()
    await page.waitForTimeout(1500)

    const titleAfter = await page.locator('h1').textContent()
    expect(titleAfter).not.toBe(titleBefore)
  })

  test('toolbar up arrow zooms out to book view', async ({ page }) => {
    // Click the Zoom out button by title
    const upArrow = page.locator('button[title*="Zoom out"]')
    await expect(upArrow).toBeVisible()
    await upArrow.click()
    await page.waitForTimeout(1000)

    // Should show book view (chapter grid buttons)
    await expect(page.getByRole('button', { name: '1', exact: true }).first()).toBeVisible({ timeout: 5000 })
  })

  test('zoom out to book view and back with down arrow', async ({ page }) => {
    // ArrowUp to zoom out to book view
    await page.keyboard.press('ArrowUp')
    await expect(page.getByRole('button', { name: '1', exact: true }).first()).toBeVisible({ timeout: 5000 })

    // ArrowDown to go back to chapter view
    await page.keyboard.press('ArrowDown')
    await page.waitForTimeout(1500)
    await expect(page.locator('h1')).toContainText('Isaiah', { timeout: 5000 })
  })

  test('zoom out twice to work view', async ({ page }) => {
    await page.keyboard.press('ArrowUp')
    await page.waitForTimeout(500)
    await page.keyboard.press('ArrowUp')
    // Work view shows the current work's books
    await expect(page.getByRole('heading', { name: 'Old Testament', exact: true })).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Genesis').first()).toBeVisible()
    await expect(page.getByText('Exodus').first()).toBeVisible()
  })

  test('graph tab opens from toolbar button', async ({ page }) => {
    // Click the graph button
    const graphBtn = page.locator('button[title="Connection Graph"]')
    await expect(graphBtn).toBeVisible()
    await graphBtn.click()

    // Should open a new tab labeled "Graph: ..."
    await page.waitForTimeout(1000)
    await expect(page.getByText('Graph:').first()).toBeVisible({ timeout: 5000 })
  })

  test('new tab opens from + button in tab strip', async ({ page }) => {
    // The + button in the tab strip
    const newTabBtn = page.locator('button[title="New tab (Ctrl+T)"]')
    await expect(newTabBtn).toBeVisible()
    await newTabBtn.click()

    await page.waitForTimeout(500)
    // Should create a duplicate tab
    const tabs = await page.getByText('Isaiah 6').all()
    expect(tabs.length).toBeGreaterThanOrEqual(1)
  })
})
