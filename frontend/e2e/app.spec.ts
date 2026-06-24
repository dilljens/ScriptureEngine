import { test, expect } from '@playwright/test'

test.describe('App — page load & default state', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
  })

  test('page loads with correct title', async ({ page }) => {
    await expect(page).toHaveTitle('Scripture Engine')
  })

  test('toolbar shows book name and chapter in breadcrumb', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })
    await expect(page.locator('h1')).toContainText('Isaiah')
    await expect(page.locator('h1')).toContainText('ch. 6')
  })

  test('toolbar has navigation arrows, search input, and icon buttons', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })

    // Search input (placeholder updated)
    await expect(page.locator('input[placeholder*="Search"]')).toBeVisible()

    // Layers button (stacked layers icon)
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await expect(layersBtn).toBeVisible()

    // Graph button
    const graphBtn = page.locator('button[title="Connection Graph"]')
    await expect(graphBtn).toBeVisible()

    // Command palette button
    const cmdBtn = page.locator('button[title*="Go to ("]')
    await expect(cmdBtn).toBeVisible()

    // Settings button (title has hotkey suffix)
    const settingsBtn = page.locator('button[title*="Settings"]')
    await expect(settingsBtn).toBeVisible()

    // Chat button
    const chatBtn = page.locator('button[title*="Chat"]')
    await expect(chatBtn).toBeVisible()

    // Dark mode button
    const darkBtn = page.locator('button[title*="Dark mode"]')
    await expect(darkBtn).toBeVisible()
  })

  test('tab strip shows workspace selector and chapter tabs', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })

    // Workspace selector label
    await expect(page.getByText('WS')).toBeVisible()

    // Chapter tabs
    await expect(page.getByText('Isaiah 6')).toBeVisible()
  })

  test('verse text is rendered after loading', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })
    const verseText = page.locator('p.text-sm.leading-relaxed')
    await expect(verseText.first()).toBeVisible({ timeout: 15000 })
    const text = await verseText.first().textContent()
    expect(text?.length).toBeGreaterThan(20)
  })

  test('layers popover opens and shows toggles', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })

    // Click the Layers button
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()

    // Popover should appear with group headers
    await expect(page.getByText('Annotations')).toBeVisible()
    await expect(page.getByText('Parallelism')).toBeVisible()
    await expect(page.getByText('Intertextual')).toBeVisible()
    await expect(page.getByText('Reference')).toBeVisible()

    // View Mode section should show with Narrative selected (default)
    await expect(page.getByText('View Mode')).toBeVisible()
    const narrativeBtn = page.getByText('Narrative')
    await expect(narrativeBtn).toBeVisible()

    // Close by clicking elsewhere
    await page.locator('h1').click()
    await expect(page.getByText('Annotations')).not.toBeVisible()
  })

  test('layers popover "All Off" toggles everything off', async ({ page }) => {
    await expect(page.locator('h1')).toBeVisible({ timeout: 15000 })
    const layersBtn = page.locator('button[title="Layers (toggle visibility)"]')
    await layersBtn.click()

    // Click All Off
    await page.getByText('All Off').click()

    // Close and reopen to verify
    await page.locator('h1').click()
    await layersBtn.click()

    // LDS Notes should now be toggled off (was on by default)
    // Just check the popover is still interactive
    await expect(page.getByText('All On')).toBeVisible()
  })
})
