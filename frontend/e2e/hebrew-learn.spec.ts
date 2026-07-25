import { test, expect } from '@playwright/test'

test.describe('Hebrew Learn — curriculum & action bar', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('open Hebrew curriculum from menu', async ({ page }) => {
    // Click the menu button (≡ or similar) to open the main menu
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"], button:has-text("≡")').first()
    if (await menuBtn.isVisible()) {
      await menuBtn.click()
    }
    // Look for the Hebrew button
    const hebrewBtn = page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first()
    await expect(hebrewBtn).toBeVisible({ timeout: 8000 })
    await hebrewBtn.click()
    // Should show the Hebrew curriculum
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })
  })

  test('action bar has dropdown menus', async ({ page }) => {
    // Open Hebrew learn
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"]').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first().click()
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })

    // Check for dropdown buttons
    const practice = page.locator('button:has-text("Practice")').first()
    const reading = page.locator('button:has-text("Reading")').first()
    const tools = page.locator('button:has-text("Tools")').first()
    const mapBtn = page.locator('button:has-text("Map"), button:has-text("List")').first()

    await expect(practice).toBeVisible({ timeout: 5000 })
    await expect(reading).toBeVisible({ timeout: 5000 })
    await expect(tools).toBeVisible({ timeout: 5000 })
    await expect(mapBtn).toBeVisible({ timeout: 5000 })
  })

  test('practice dropdown opens with items', async ({ page }) => {
    // Open Hebrew learn
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"]').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first().click()
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })

    // Open Practice dropdown
    const practice = page.locator('button:has-text("Practice")').first()
    await practice.click()

    // Should show dropdown items
    await expect(page.locator('text=/5-min Quick|Quick/i').first()).toBeVisible({ timeout: 3000 })
    await expect(page.locator('text=/Quiz/i').first()).toBeVisible({ timeout: 3000 })
    await expect(page.locator('text=/Review/i').first()).toBeVisible({ timeout: 3000 })
  })

  test('reading dropdown opens with items', async ({ page }) => {
    // Open Hebrew learn
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"]').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first().click()
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })

    // Open Reading dropdown
    const reading = page.locator('button:has-text("Reading")').first()
    await reading.click()

    await expect(page.locator('text=/Verse of Day/i').first()).toBeVisible({ timeout: 3000 })
    await expect(page.locator('text=/Read Passage/i').first()).toBeVisible({ timeout: 3000 })
  })

  test('tools dropdown opens with items', async ({ page }) => {
    // Open Hebrew learn
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"]').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first().click()
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })

    // Open Tools dropdown
    const tools = page.locator('button:has-text("Tools")').first()
    await tools.click()

    await expect(page.locator('text=/Verb Drills/i').first()).toBeVisible({ timeout: 3000 })
    await expect(page.locator('text=/Top Vocab/i').first()).toBeVisible({ timeout: 3000 })
    await expect(page.locator('text=/Audio Review/i').first()).toBeVisible({ timeout: 3000 })
  })

  test('curriculum shows lesson cards', async ({ page }) => {
    // Open Hebrew learn
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"]').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first().click()
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })

    // Should see lessons listed (Level 1, consonants, etc.)
    await expect(page.locator('text=/Aleph/i').first()).toBeVisible({ timeout: 8000 })
    await expect(page.locator('text=/Bet/i').first()).toBeVisible({ timeout: 8000 })
  })

  test('mastery stats bar is visible', async ({ page }) => {
    // Open Hebrew learn
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"]').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first().click()
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })

    // Should show mastery stats
    await expect(page.locator('text=/mastered/i').first()).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=/locked/i').first()).toBeVisible({ timeout: 5000 })
  })

  test('filter tabs are visible and clickable', async ({ page }) => {
    // Open Hebrew learn
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"]').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first().click()
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })

    // Category filter tabs should be present
    const allTab = page.locator('button:has-text("All")').first()
    await expect(allTab).toBeVisible({ timeout: 5000 })

    // Click a filter tab
    const lettersTab = page.locator('button:has-text("Letters")').first()
    if (await lettersTab.isVisible()) {
      await lettersTab.click()
      // After clicking, the tab should be active (highlighted)
      await expect(lettersTab).toBeVisible()
    }
  })

  test('mastery map toggle works', async ({ page }) => {
    // Open Hebrew learn
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"]').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button:has-text("Hebrew"), button:has-text("א Hebrew")').first().click()
    await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 10000 })

    // Click Map toggle
    const mapBtn = page.locator('button:has-text("Map")').first()
    await expect(mapBtn).toBeVisible({ timeout: 5000 })
    await mapBtn.click()

    // Should show the mastery map grid
    await expect(page.locator('text=/Mastery Map/i').first()).toBeVisible({ timeout: 5000 })

    // Click List to go back
    const listBtn = page.locator('button:has-text("List")').first()
    await expect(listBtn).toBeVisible({ timeout: 3000 })
    await listBtn.click()
  })
})
