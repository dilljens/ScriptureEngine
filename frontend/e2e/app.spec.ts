import { test, expect } from '@playwright/test'

// Desktop breadcrumb h1 is the first h1 in the DOM (visible at desktop viewport)
function desktopH1(page) { return page.locator('h1').first() }

test.describe('App — page load & default state', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
  })

  test('page loads with correct title', async ({ page }) => {
    await expect(page).toHaveTitle('Scripture Engine')
  })

  test('toolbar shows book name and chapter in breadcrumb', async ({ page }) => {
    // Wait for book data to load — desktop breadcrumb shows "Isaiah"
    await expect(desktopH1(page)).toContainText('Isaiah', { timeout: 20000 })
    await expect(desktopH1(page)).toContainText('ch. 6')
  })

  test('toolbar has search input and controls', async ({ page }) => {
    await expect(desktopH1(page)).toBeVisible({ timeout: 15000 })

    // Search input
    await expect(page.locator('input[placeholder*="Search"]')).toBeVisible()

    // Command palette button
    const cmdBtn = page.locator('button[title*="Go to ("]')
    await expect(cmdBtn).toBeVisible()

    // Settings button
    const settingsBtn = page.locator('button[title*="Settings"]')
    await expect(settingsBtn).toBeVisible()

    // Dark mode button
    const darkBtn = page.locator('button[title*="Dark mode"]')
    await expect(darkBtn).toBeVisible()
  })

  test('tab strip shows workspace selector and chapter tabs', async ({ page }) => {
    await expect(desktopH1(page)).toBeVisible({ timeout: 15000 })

    // Workspace selector or subject tab bar
    const wsEl = page.getByText('WS').or(page.getByText('My Study'))
    await expect(wsEl.first()).toBeVisible()

    // Chapter tabs
    await expect(page.getByText('Isaiah 6')).toBeVisible()
  })

  test('verse text is rendered after loading', async ({ page }) => {
    // Wait for book data to load
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
    const verseText = page.locator('p.text-sm.leading-relaxed')
    await expect(verseText.first()).toBeVisible({ timeout: 15000 })
    const text = await verseText.first().textContent()
    expect(text?.length).toBeGreaterThan(20)
  })

  test('main menu dropdown opens and shows tools', async ({ page }) => {
    await expect(desktopH1(page)).toBeVisible({ timeout: 15000 })

    // Click the main Menu button
    const menuBtn = page.locator('button[title="Menu"]')
    await expect(menuBtn).toBeVisible()
    await menuBtn.click()

    // Menu should show Study options
    await expect(page.getByText('Learn').first()).toBeVisible()
    await expect(page.getByText('Hebrew').first()).toBeVisible()
    await expect(page.getByText('Memorize').first()).toBeVisible()
    await expect(page.getByText('Study Paths').first()).toBeVisible()
    await expect(page.getByText('Wiki').first()).toBeVisible()

    // Tools section
    await expect(page.getByText('Chat').first()).toBeVisible()
    await expect(page.getByText('History').first()).toBeVisible()
    await expect(page.getByText('Structure').first()).toBeVisible()
    await expect(page.getByText('Layers').first()).toBeVisible()
  })
})
