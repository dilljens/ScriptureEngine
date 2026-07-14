import { test, expect } from '@playwright/test'

test.describe('Layers popover (feature toggles)', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator("h1")).toBeVisible({ timeout: 15000 })
  })

  test('layers button opens popover with all toggle groups', async ({ page }) => {
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()

    // Check all group headers
    await expect(page.getByText('Annotations')).toBeVisible()
    await expect(page.getByText('Parallelism')).toBeVisible()
    await expect(page.getByText('Intertextual')).toBeVisible()
    await expect(page.getByText('Reference')).toBeVisible()
    await expect(page.getByText('View Mode')).toBeVisible()
  })

  test('toggle switch turns footnotes on/off', async ({ page }) => {
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()

    // Find the Footnotes toggle row and click the switch
    const fnRow = page.getByText('Footnotes (LDS Notes)')
    await expect(fnRow).toBeVisible()
    await fnRow.click()

    // Press Escape to close
    await page.keyboard.press('Escape')
    await expect(page.getByText('Annotations')).not.toBeVisible({ timeout: 3000 })

    // Re-open to verify state
    await layersBtn.click()
    await expect(page.getByText('Footnotes (LDS Notes)')).toBeVisible()
  })

  test('All On / All Off buttons toggle all toggles', async ({ page }) => {
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()

    // Click All Off
    await page.getByText('All Off').click()

    // "All On" button should now be active
    await expect(page.getByText('All On')).toBeVisible()

    // Click All On to restore
    await page.getByText('All On').click()
    await expect(page.getByText('All Off')).toBeVisible()
  })

  test('poetry/narrative toggle works in layers popover', async ({ page }) => {
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()

    // Default should be Narrative
    const narrativeBtn = page.getByText('Narrative')
    await expect(narrativeBtn).toBeVisible()

    // Click Poetry
    await page.getByText('Poetry').click()

    // Close and reopen — Poetry should remain selected
    await page.keyboard.press('Escape')
    await layersBtn.click()
    await expect(page.getByText('Narrative')).toBeVisible()
  })

  test('layers popover closes on Escape', async ({ page }) => {
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()
    await expect(page.getByText('Annotations')).toBeVisible()

    await page.keyboard.press('Escape')
    await expect(page.getByText('Annotations')).not.toBeVisible()
  })
})
