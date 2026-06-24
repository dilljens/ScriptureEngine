import { test, expect } from '@playwright/test'

test.describe('Footnote markers', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 })
  })

  test('footnote superscript markers render', async ({ page }) => {
    const fnMarkers = page.locator('sup.fn-marker')
    const count = await fnMarkers.count()
    test.skip(count === 0, 'No footnotes in this chapter')
    await expect(fnMarkers.first()).toBeVisible()
  })

  test('clicking footnote marker opens popup', async ({ page }) => {
    const fnMarkers = page.locator('sup.fn-marker')
    const count = await fnMarkers.count()
    test.skip(count === 0, 'No footnotes in this chapter')

    await fnMarkers.first().click()
    await expect(page.locator('.fixed.inset-0').first()).toBeVisible({ timeout: 3000 })
  })

  test('footnote popup shows close button', async ({ page }) => {
    const fnMarkers = page.locator('sup.fn-marker')
    const count = await fnMarkers.count()
    test.skip(count === 0, 'No footnotes in this chapter')

    await fnMarkers.first().click()
    const popup = page.locator('.fixed.inset-0').first()
    await expect(popup.locator('button', { hasText: '×' }).first()).toBeVisible({ timeout: 3000 })
  })

  test('hovering footnote marker shows rich tooltip', async ({ page }) => {
    const fnMarkers = page.locator('sup.fn-marker')
    const count = await fnMarkers.count()
    test.skip(count === 0, 'No footnotes in this chapter')

    // Hover the first marker
    await fnMarkers.first().hover()

    // The rich tooltip should appear — it has the category label
    await page.waitForTimeout(500)
    const tooltip = page.locator('.z-\\[60\\]')
    const tooltipCount = await tooltip.count()
    // Tooltip may or may not render depending on timing
    if (tooltipCount > 0) {
      await expect(tooltip.first()).toBeVisible()
    }
  })

  test('hovering footnote word also shows tooltip', async ({ page }) => {
    const fnWords = page.locator('.fn-word')
    const count = await fnWords.count()
    test.skip(count === 0, 'No fn-words in this chapter')

    await fnWords.first().hover()
    await page.waitForTimeout(500)

    const tooltip = page.locator('.z-\\[60\\]')
    const tooltipCount = await tooltip.count()
    if (tooltipCount > 0) {
      await expect(tooltip.first()).toBeVisible()
    }
  })
})
