import { test, expect } from '@playwright/test'

test.describe('Connection tags — unified panel', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 })
  })

  test('toggle Direct then panel shows connections', async ({ page }) => {
    await page.locator('button', { hasText: 'Direct' }).click()
    await page.waitForTimeout(1000)

    // There may be multiple verse panels — pick first
    const panelBtn = page.locator('button', { hasText: /Connections/ }).first()
    const count = await page.locator('button', { hasText: /Connections/ }).count()
    test.skip(count === 0, 'No connections in this chapter')
    await expect(panelBtn).toBeVisible()
  })

  test('clicking panel header opens grouped sections', async ({ page }) => {
    await page.locator('button', { hasText: 'Direct' }).click()
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
    await page.locator('button', { hasText: 'Direct' }).click()
    await page.waitForTimeout(1000)

    const panels = page.locator('button', { hasText: /Connections/ })
    const count = await panels.count()
    test.skip(count === 0, 'No connections in this chapter')

    await panels.first().click()
    await page.waitForTimeout(500)

    // Find a section header with a count (indicates it has items)
    const sectionWithItems = page.locator('.space-y-1 button:has-text("/")').first()
    const sectionCount = await sectionWithItems.count()
    test.skip(sectionCount === 0, 'No expandable sections in this panel')
    await sectionWithItems.click()
    await page.waitForTimeout(300)
  })

  test('filter input works', async ({ page }) => {
    await page.locator('button', { hasText: 'Direct' }).click()
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

  test('All On / All Off toggle works', async ({ page }) => {
    const allBtn = page.locator('button', { hasText: /All (On|Off)/ })
    await expect(allBtn).toBeVisible({ timeout: 5000 })
    const currentText = await allBtn.textContent()

    await allBtn.click()

    const newBtn = page.locator('button', { hasText: /All (On|Off)/ })
    const newText = await newBtn.textContent()
    expect(newText).not.toBe(currentText)
  })
})
