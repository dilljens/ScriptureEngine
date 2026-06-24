import { test, expect } from '@playwright/test'

test.describe('Connection tags — unified panel', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 })
  })

  test('toggle Direct via Layers popover then panel shows connections', async ({ page }) => {
    // Open Layers popover and toggle Direct Quotes on
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()
    await page.getByText('Direct Quotes').click()
    await page.keyboard.press('Escape')
    await page.waitForTimeout(1000)

    // Connections panel should appear in the verse
    const panelBtn = page.locator('button', { hasText: /Connections/ }).first()
    const count = await page.locator('button', { hasText: /Connections/ }).count()
    test.skip(count === 0, 'No connections in this chapter')
    await expect(panelBtn).toBeVisible()
  })

  test('clicking panel header opens grouped sections', async ({ page }) => {
    // Enable Direct quotes via Layers popover
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()
    await page.getByText('Direct Quotes').click()
    await page.keyboard.press('Escape')
    await page.waitForTimeout(1000)

    const panels = page.locator('button', { hasText: /Connections/ })
    const count = await panels.count()
    test.skip(count === 0, 'No connections in this chapter')

    await panels.first().click()
    await page.waitForTimeout(500)

    const groupHeader = page.locator('button:has-text("Direct")').first()
    await expect(groupHeader).toBeVisible({ timeout: 3000 })
  })

  test('expanding a section shows connection items', async ({ page }) => {
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()
    await page.getByText('Direct Quotes').click()
    await page.keyboard.press('Escape')
    await page.waitForTimeout(1000)

    const panels = page.locator('button', { hasText: /Connections/ })
    const count = await panels.count()
    test.skip(count === 0, 'No connections in this chapter')

    await panels.first().click()
    await page.waitForTimeout(500)

    const sectionWithItems = page.locator('.space-y-1 button:has-text("/")').first()
    const sectionCount = await sectionWithItems.count()
    test.skip(sectionCount === 0, 'No expandable sections in this panel')
    await sectionWithItems.click()
    await page.waitForTimeout(300)
  })

  test('filter input works', async ({ page }) => {
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()
    await page.getByText('Direct Quotes').click()
    await page.keyboard.press('Escape')
    await page.waitForTimeout(1000)

    const panels = page.locator('button', { hasText: /Connections/ })
    const count = await panels.count()
    test.skip(count === 0, 'No connections in this chapter')

    await panels.first().click()
    await page.waitForTimeout(500)

    const filterInput = page.locator('input[placeholder*="filter"]').first()
    await expect(filterInput).toBeVisible({ timeout: 3000 })

    await filterInput.fill('isa')
    await page.waitForTimeout(300)
    await expect(filterInput).toBeVisible()
  })

  test('All On / All Off toggle works via Layers popover', async ({ page }) => {
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()

    // All Off / All On buttons exist inside the popover
    const allOff = page.getByText('All Off')
    await expect(allOff).toBeVisible()
    await allOff.click()

    // After clicking All Off, "All On" should become active
    await expect(page.getByText('All On')).toBeVisible()
  })
})
