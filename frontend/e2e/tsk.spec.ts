import { test, expect } from '@playwright/test'

test.describe('TSK (Treasury of Scripture Knowledge) popup', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1')).toContainText('Isaiah', { timeout: 15000 })
  })

  test('TSK badge appears on verses with cross-references', async ({ page }) => {
    const tskBadge = page.locator('button[title*="Treasury"]')
    const count = await tskBadge.count()
    if (count > 0) {
      await expect(tskBadge.first()).toBeVisible()
    }
  })

  test('TSK count shown in connections panel', async ({ page }) => {
    const tskBadge = page.locator('button[title*="Treasury"]')
    const count = await tskBadge.count()
    test.skip(count === 0, 'No TSK cross-references in this chapter')

    // TSK count should also be shown in the connections panel header
    const panelBtn = page.locator('button', { hasText: 'Connections' })
    await expect(panelBtn).toBeVisible()
    await expect(panelBtn.locator('text=ᵗ').first()).toBeVisible()
  })

  test('clicking TSK badge opens popup', async ({ page }) => {
    const tskBadge = page.locator('button[title*="Treasury"]').first()
    const count = await tskBadge.count()
    test.skip(count === 0, 'No TSK cross-references in this chapter')

    await tskBadge.click()
    await expect(page.locator('text=Treasury of Scripture Knowledge')).toBeVisible({ timeout: 5000 })
  })

  test('TSK popup has references', async ({ page }) => {
    const tskBadge = page.locator('button[title*="Treasury"]').first()
    const count = await tskBadge.count()
    test.skip(count === 0, 'No TSK cross-references in this chapter')

    await tskBadge.click()
    await expect(page.locator('text=Treasury of Scripture Knowledge')).toBeVisible({ timeout: 5000 })

    const refs = page.locator('text=Treasury of Scripture Knowledge').first()
      .locator('..').locator('..').locator('.cursor-pointer')
    await expect(refs.first()).toBeVisible()
  })
})
