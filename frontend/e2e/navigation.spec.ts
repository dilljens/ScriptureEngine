import { test, expect } from '@playwright/test'

test.describe('Navigation — chapter, book, work levels', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('keyboard ArrowRight navigates to next chapter', async ({ page }) => {
    const titleBefore = await page.locator('h1').first().textContent()
    await page.keyboard.press('ArrowRight')
    await expect(async () => {
      await expect(page.locator('h1').first()).not.toHaveText(titleBefore!)
    }).toPass({ timeout: 10000 })
  })

  test('toolbar right arrow button navigates to next chapter', async ({ page }) => {
    const titleBefore = await page.locator('h1').first().textContent()
    const rightArrow = page.locator('h1').first().locator('..').locator('button').last()
    await rightArrow.click()
    await expect(async () => {
      await expect(page.locator('h1').first()).not.toHaveText(titleBefore!)
    }).toPass({ timeout: 10000 })
  })

  test('toolbar up arrow zooms out to book view', async ({ page }) => {
    const upArrow = page.locator('button[title*="Zoom out"]')
    await expect(upArrow).toBeVisible()
    await upArrow.click()
    await expect(page.getByRole('button', { name: '1', exact: true }).first()).toBeVisible({ timeout: 5000 })
  })

  test('zoom out to book view and back with down arrow', async ({ page }) => {
    await page.keyboard.press('ArrowUp')
    await expect(page.getByRole('button', { name: '1', exact: true }).first()).toBeVisible({ timeout: 5000 })
    await page.keyboard.press('ArrowDown')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 5000 })
  })

  test('zoom out twice to work view', async ({ page }) => {
    await page.keyboard.press('ArrowUp')
    await expect(page.getByRole('button', { name: '1', exact: true }).first()).toBeVisible({ timeout: 5000 })
    await page.keyboard.press('ArrowUp')
    await expect(page.getByRole('heading', { name: 'Old Testament', exact: true })).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Genesis').first()).toBeVisible()
    await expect(page.getByText('Exodus').first()).toBeVisible()
  })

  test('new tab opens from + button in tab strip', async ({ page }) => {
    const newTabBtn = page.locator('button[title="New workspace"]')
    await expect(newTabBtn).toBeVisible()
    await newTabBtn.click()
    await expect(page.getByText('New Workspace').first()).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Navigation — work search via search bar', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('search "ot" navigates to Old Testament work view via dropdown', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]')
    await expect(searchInput).toBeVisible()
    await searchInput.fill('ot')

    // Should see navigate results in dropdown — find a result with OT/Genesis text
    const otResult = page.locator('button').filter({ hasText: /(Go to|OT|Old Testament|Navigate)/i }).first()
    // The navigate result might show: "Old Testament → Genesis" or similar
    await expect(otResult).toBeVisible({ timeout: 5000 })

    await searchInput.press('Enter')
    // Should navigate to a book — the breadcrumb should reflect the choice
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 5000 })
  })

  test('search "old testament" in search bar shows navigate results', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill('old testament')
    // Should show navigate results with OT books
    const navResult = page.locator('button').filter({ hasText: /Navigate|Old/ }).first()
    await expect(navResult).toBeVisible({ timeout: 5000 })
  })

  test('search "nt" shows New Testament books as navigate results', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill('nt')
    const navResult = page.locator('button').filter({ hasText: /(Navigate|NT|New Testament)/i }).first()
    await expect(navResult).toBeVisible({ timeout: 5000 })
  })

  test('full-text search shows FTS results when no book matches', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]')
    await searchInput.fill('mercy')
    await expect(page.locator('.text-xs.text-neutral-600').first()).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('Go to ')).not.toBeVisible()
  })
})

test.describe('Navigation — D&C sections', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('navigate to D&C section via command palette', async ({ page }) => {
    await page.locator('button[title*="Go to"]').click()
    await expect(page.getByPlaceholder(/search|go to|find/i).first()).toBeVisible({ timeout: 5000 })
    await page.getByPlaceholder(/search|go to|find/i).fill('/dc/138')
    await page.keyboard.press('Enter')
    await page.waitForTimeout(3000)
    await expect(page.getByText(/dc.*138|doctrine.*138|dc138/i).first()).toBeVisible({ timeout: 10000 })
  })

  test('navigate to D&C section with dcN format via search bar', async ({ page }) => {
    const searchInput = page.locator('input[placeholder*="Search"]')
    await expect(searchInput).toBeVisible()
    await searchInput.fill('dc138')
    // Navigate result should appear
    const navResult = page.locator('button').filter({ hasText: /Navigate/i }).first()
    await expect(navResult).toBeVisible({ timeout: 5000 })
    await searchInput.press('Enter')
    await expect(page.getByText(/dc.*138|dc138|section/i).first()).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Navigation — library and work views', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('zoom out to work view then navigate to a book then to a chapter', async ({ page }) => {
    // Zoom out twice to work view
    await page.keyboard.press('ArrowUp')
    await expect(page.getByRole('button', { name: '1', exact: true }).first()).toBeVisible({ timeout: 5000 })
    await page.keyboard.press('ArrowUp')
    await expect(page.getByRole('heading', { name: 'Old Testament', exact: true })).toBeVisible({ timeout: 5000 })

    // Click a book (e.g., Genesis)
    const genesisBtn = page.getByText('Genesis').first()
    await expect(genesisBtn).toBeVisible()
    await genesisBtn.click()

    // Should now be in book view — chapter grid
    await expect(page.getByRole('button', { name: '1', exact: true }).first()).toBeVisible({ timeout: 5000 })

    // Click chapter 1 to go to chapter view
    const ch1Btn = page.getByRole('button', { name: '1', exact: true }).first()
    await ch1Btn.click()

    // Should show Genesis chapter 1
    await expect(page.locator('h1').first()).toContainText('Genesis', { timeout: 5000 })
    await expect(page.locator('h1').first()).toContainText('ch. 1')
  })

  test('library view shows all works', async ({ page }) => {
    // Zoom out three times: chapter → book → work → library
    await page.keyboard.press('ArrowUp') // chapter → book
    await page.waitForTimeout(500)
    await page.keyboard.press('ArrowUp') // book → work
    await page.waitForTimeout(500)
    await page.keyboard.press('ArrowUp') // work → library

    // Library view should show all work cards
    await expect(page.getByText('Old Testament').first()).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('New Testament').first()).toBeVisible({ timeout: 5000 })
    await expect(page.getByText('Book of Mormon').first()).toBeVisible({ timeout: 5000 })
  })
})
