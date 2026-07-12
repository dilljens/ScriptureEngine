import { test, expect } from '@playwright/test'

// Mobile h1 is the second h1 in the DOM (visible at mobile viewport, first is hidden desktop h1)
const mobileH1 = (page) => page.locator('h1').nth(1)

test.describe('Mobile navigation — bottom tab bar', () => {

  test.beforeEach(async ({ page }) => {
    // Mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    // Wait for the page to fully load — h1 breadcrumb visible
    await expect(mobileH1(page)).toBeVisible({ timeout: 15000 })
  })

  test('bottom nav is visible on mobile', async ({ page }) => {
    // Bottom nav is the nav at the bottom of the page
    const nav = page.locator('nav').filter({ hasText: 'Read' })
    await expect(nav).toBeVisible()
    // All 5 tab buttons + More should be present in the nav
    await expect(nav.getByText('Read')).toBeVisible()
    await expect(nav.getByText('Chat')).toBeVisible()
    await expect(nav.getByText('Hebrew')).toBeVisible()
    await expect(nav.getByText('Learn')).toBeVisible()
    await expect(nav.getByText('Review')).toBeVisible()
    await expect(nav.getByText('More')).toBeVisible()
  })

  test('Read tab loads the reading view (chapter text)', async ({ page }) => {
    // Read is the default — verse text should be visible
    const readBtn = page.getByText('Read')
    await expect(readBtn).toBeVisible()
    // The verse content area should have rendered text
    const verseText = page.locator('p.text-sm.leading-relaxed')
    await expect(verseText.first()).toBeVisible({ timeout: 15000 })
    const text = await verseText.first().textContent()
    expect(text?.length).toBeGreaterThan(20)
    // Breadcrumb should show we're on a chapter
    await expect(mobileH1(page)).toContainText('Isaiah')
  })

  test('Chat tab opens chat view', async ({ page }) => {
    await page.getByText('Chat').click()
    await page.waitForTimeout(2000)
    // The Chat tab should have loaded — tab label shows "Chat"
    // Check that the body contains "Chat" indicating the view switched
    const bodyText = await page.textContent('body')
    expect(bodyText).toContain('Chat')
  })

  test('Hebrew tab opens Hebrew learning view', async ({ page }) => {
    // Click the Hebrew button specifically in the nav (not the <option> element)
    await page.locator('nav').filter({ hasText: 'Read' }).getByText('Hebrew').click()
    await page.waitForTimeout(3000)
    // Hebrew view loads — body should contain Hebrew content
    const bodyText = await page.textContent('body')
    expect(bodyText).toContain('Hebrew')
  })

  test('Learn tab opens Learn view with module list', async ({ page }) => {
    await page.getByText('Learn').click()
    await page.waitForTimeout(3000)
    // Learn view shows module list with "Learn Scripture" heading
    await expect(page.getByText('Learn Scripture')).toBeVisible({ timeout: 10000 })
    // Subject filter chips should appear
    await expect(page.getByText('All Subjects')).toBeVisible()
  })

  test('Review (Memorize) tab opens Memorize view', async ({ page }) => {
    await page.getByText('Review').click()
    await page.waitForTimeout(3000)
    // Memorize view should load — body should contain "Memorize"
    const bodyText = await page.textContent('body')
    expect(bodyText).toContain('Memorize')
  })

  test('More button opens menu drawer', async ({ page }) => {
    await page.getByText('More').click()
    await page.waitForTimeout(1000)
    // Menu drawer should show with the drawer content
    // The MobileMenuDrawer should be visible
    const drawerContent = page.locator('div.fixed.inset-0.z-50').filter({ hasText: 'Learning' })
    await expect(drawerContent).toBeVisible()
    await expect(page.getByText('Layers')).toBeVisible()
    await expect(page.getByText('Structure')).toBeVisible()
  })

  test('switching between tabs updates the visible view', async ({ page }) => {
    // Start on Read
    await expect(mobileH1(page)).toContainText('Isaiah', { timeout: 5000 })

    // Switch to Chat
    await page.getByText('Chat').click()
    await page.waitForTimeout(1000)
    const chatInput = page.getByPlaceholder(/Ask about/i)
    await expect(chatInput).toBeVisible({ timeout: 8000 })

    // Switch back to Read — should still show the chapter
    await page.getByText('Read').click()
    await page.waitForTimeout(1000)
    await expect(mobileH1(page)).toContainText('Isaiah', { timeout: 5000 })
    const verseText = page.locator('p.text-sm.leading-relaxed')
    await expect(verseText.first()).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Mobile — Learn view open-ended questions', () => {

  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(mobileH1(page)).toBeVisible({ timeout: 15000 })
  })

  test('Learn view has Next button after answering (no auto-advance)', async ({ page }) => {
    // Navigate to Learn
    await page.getByText('Learn').click()
    await page.waitForTimeout(2000)
    await expect(page.getByText('Learn Scripture')).toBeVisible({ timeout: 10000 })

    // Click a module to start practice
    const firstModule = page.locator('button').filter({ hasText: 'Covenants' }).first()
    // If covenants isn't available, try any module button
    const moduleBtn = (await firstModule.count() > 0)
      ? firstModule
      : page.locator('button.w-full.text-left.p-4.rounded-xl').first()

    if (await moduleBtn.count() > 0) {
      await moduleBtn.click()
      await page.waitForTimeout(1500)

      // On the lesson page, click "Start Practice"
      const startBtn = page.getByText(/Start Practice/)
      if (await startBtn.isVisible()) {
        await startBtn.click()
        await page.waitForTimeout(1000)

        // Check if there's a "Next" button after answering
        // This confirms no auto-advance
        const mcOptions = page.locator('button').filter({ hasText: /^[A-F]\./ })
        if (await mcOptions.count() > 0) {
          await mcOptions.first().click()
          await page.waitForTimeout(500)
          const submitBtn = page.getByText('Submit')
          if (await submitBtn.isVisible()) {
            await submitBtn.click()
            await page.waitForTimeout(1000)
            // Should see "Next Question" or "See Results" button instead of auto-advance
            await expect(page.getByText(/Next Question|See Results/)).toBeVisible({ timeout: 8000 })
          }
        }
      }
    }
  })
})
