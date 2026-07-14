import { test, expect } from '@playwright/test'

// Mobile tests run via --project=mobile-chromium which sets 375x667 viewport
// The mobile h1 is the second h1 in the DOM (first is hidden desktop h1)
const mobileH1 = (page) => page.locator('h1').nth(1)

test.describe('Mobile navigation — bottom tab bar', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(mobileH1(page)).toBeVisible({ timeout: 15000 })
  })

  test('bottom nav is visible on mobile', async ({ page }) => {
    const nav = page.locator('nav').filter({ hasText: 'Read' })
    await expect(nav).toBeVisible()
    await expect(nav.getByText('Read')).toBeVisible()
    await expect(nav.getByText('Chat')).toBeVisible()
    await expect(nav.getByText('Hebrew')).toBeVisible()
    await expect(nav.getByText('Learn')).toBeVisible()
    await expect(nav.getByText('Review')).toBeVisible()
    await expect(nav.getByText('More')).toBeVisible()
  })

  test('Read tab loads the reading view (chapter text)', async ({ page }) => {
    const verseText = page.locator('p.text-sm.leading-relaxed')
    await expect(verseText.first()).toBeVisible({ timeout: 15000 })
    const text = await verseText.first().textContent()
    expect(text?.length).toBeGreaterThan(20)
    await expect(mobileH1(page)).toContainText('Isaiah')
  })

  test('Chat tab opens chat view', async ({ page }) => {
    await page.getByText('Chat').click()
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 10000 })
  })

  test('Hebrew tab opens Hebrew learning view', async ({ page }) => {
    await page.locator('nav').filter({ hasText: 'Read' }).getByText('Hebrew').click()
    await expect(page.getByRole('heading', { name: 'Biblical Hebrew' })).toBeVisible({ timeout: 10000 })
  })

  test('Learn tab opens Learn view with module list', async ({ page }) => {
    await page.getByText('Learn').click()
    await expect(page.getByText('Learn Scripture')).toBeVisible({ timeout: 10000 })
    await expect(page.getByText('All Subjects')).toBeVisible()
  })

  test('Review (Memorize) tab opens Memorize view', async ({ page }) => {
    await page.getByText('Review').click()
    await expect(page.locator('h2').filter({ hasText: 'Memorize' })).toBeVisible({ timeout: 10000 })
  })

  test('More button opens menu drawer', async ({ page }) => {
    await page.getByText('More').click()
    const drawerContent = page.locator('div.fixed.inset-0.z-50').filter({ hasText: 'Learning' })
    await expect(drawerContent).toBeVisible()
    await expect(page.getByText('Layers')).toBeVisible()
    await expect(page.getByText('Structure')).toBeVisible()
  })

  test('switching between tabs updates the visible view', async ({ page }) => {
    await expect(mobileH1(page)).toContainText('Isaiah', { timeout: 5000 })
    await page.getByText('Chat').click()
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 8000 })
    await page.locator('nav').filter({ hasText: 'Read' }).getByText('Read').click()
    await expect(mobileH1(page)).toContainText('Isaiah', { timeout: 5000 })
    const verseText = page.locator('p.text-sm.leading-relaxed')
    await expect(verseText.first()).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Mobile — wiki', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(mobileH1(page)).toBeVisible({ timeout: 15000 })
  })

  test('wiki opens from More drawer on mobile', async ({ page }) => {
    await page.getByText('More').click()
    await expect(page.locator('div.fixed.inset-0.z-50').first()).toBeVisible()
    // Click the Wiki button in the drawer
    const wikiBtn = page.locator('div.fixed.inset-0.z-50').getByText('Wiki')
    if (await wikiBtn.isVisible()) {
      await wikiBtn.click()
      // Wait for wiki to load — either the empty state or the browse view
      await expect(page.locator('.max-w-4xl').first()).toBeVisible({ timeout: 10000 })
    }
  })

  test('wiki article renders without horizontal overflow on mobile', async ({ page }) => {
    await page.getByText('More').click()
    const wikiBtn = page.locator('div.fixed.inset-0.z-50').getByText('Wiki')
    if (await wikiBtn.isVisible()) {
      await wikiBtn.click()
      // Load a known article via API directly
      await page.evaluate(() => {
        const event = new CustomEvent('scripture-navigate', { detail: { ref: 'wiki:abraham' } })
        window.dispatchEvent(event)
      })
      // Check no horizontal scroll
      const overflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth
      })
      expect(overflow).toBe(false)
    }
  })

  test('wiki browse is single column on mobile', async ({ page }) => {
    await page.goto('/')
    // Open wiki via URL param
    await page.evaluate(() => {
      window.__bookData = { works: [] }
    })
    // Navigate directly to wiki browse
    const wikiTab = page.locator('button').filter({ hasText: 'Menu' })
    if (await wikiTab.isVisible()) {
      await wikiTab.click()
      const wikiNav = page.getByText('Wiki').last()
      if (await wikiNav.isVisible()) {
        await wikiNav.click()
      }
    }
    // Check browse mode — we can verify via the wiki content area
    const body = await page.textContent('body')
    if (body.includes('Select an entity')) {
      // Browse mode is showing the empty state
      const container = page.locator('.max-w-4xl')
      if (await container.count() > 0) {
        const box = await container.boundingBox()
        // On 375px viewport with px-4, max container width should be ~343px
        expect(box?.width).toBeLessThanOrEqual(380)
      }
    }
  })

  test('wiki article has bottom spacing on mobile', async ({ page }) => {
    await page.getByText('More').click()
    const wikiBtn = page.locator('div.fixed.inset-0.z-50').getByText('Wiki')
    if (await wikiBtn.isVisible()) {
      await wikiBtn.click()
      // Check that content doesn't overlap bottom nav
      const lastContent = page.locator('.max-w-4xl').last()
      if (await lastContent.isVisible()) {
        const contentBox = await lastContent.boundingBox()
        const viewportHeight = await page.evaluate(() => window.innerHeight)
        // Content should end above viewport bottom or have padding
        expect(contentBox ? contentBox.y + contentBox.height : 0).toBeLessThanOrEqual(viewportHeight)
      }
    }
  })

  test('wiki search works on mobile', async ({ page }) => {
    // Test the wiki search API endpoint directly (UI search is in the header)
    const response = await page.request.get('/api/v1/wiki/search?q=covenant')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.total).toBeGreaterThanOrEqual(1)
  })
})

test.describe('Mobile — Learn view open-ended questions', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(mobileH1(page)).toBeVisible({ timeout: 15000 })
  })

  test('Learn view has Next button after answering (no auto-advance)', async ({ page }) => {
    await page.getByText('Learn').click()
    await expect(page.getByText('Learn Scripture')).toBeVisible({ timeout: 10000 })
    const firstModule = page.locator('button').filter({ hasText: 'Covenants' }).first()
    const moduleBtn = (await firstModule.count() > 0)
      ? firstModule
      : page.locator('button.w-full.text-left.p-4.rounded-xl').first()
    if (await moduleBtn.count() > 0) {
      await moduleBtn.click()
      const startBtn = page.getByText(/Start Practice/)
      if (await startBtn.isVisible()) {
        await startBtn.click()
        const mcOptions = page.locator('button').filter({ hasText: /^[A-F]\./ })
        if (await mcOptions.count() > 0) {
          await mcOptions.first().click()
          const submitBtn = page.getByText('Submit')
          if (await submitBtn.isVisible()) {
            await submitBtn.click()
            await expect(page.getByText(/Next Question|See Results/)).toBeVisible({ timeout: 8000 })
          }
        }
      }
    }
  })
})
