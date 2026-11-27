import { test, expect } from '@playwright/test'

test.use({ viewport: { width: 375, height: 667 }, hasTouch: true, isMobile: true })

// Regression: opening Hebrew must land on the dashboard, never auto-open a
// lesson persisted from the last session (e.g. Zayin).
test('stale hebrew lesson does not auto-open', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.clear()
    const tabs = {
      workspaces: [{
        id: 'ws1', name: 'My Study',
        tabs: [
          { id: 't1', book: 'isa', chapter: 6, label: 'Isaiah 6', view: 'chapter', viewRef: null, highlights: [], companion: null },
          { id: 't2', book: 'gen', chapter: 1, label: 'Hebrew: zayin', view: 'hebrew', viewRef: 'zayin', highlights: [], companion: null },
        ],
      }],
      activeWorkspace: 'ws1',
      activeTab: 't2',
    }
    localStorage.setItem('scripture_tabs', JSON.stringify(tabs))
  })
  await page.goto('/')
  await expect(page.locator('body')).toContainText('Biblical Hebrew', { timeout: 30000 })
  const body = await page.locator('body').innerText()
  console.log('DASHBOARD=' + /Biblical Hebrew/i.test(body))
  // Must be the dashboard, not the Zayin lesson auto-opened.
  expect(body).toMatch(/Biblical Hebrew/i)
  expect(body).not.toMatch(/Zayin \(ז\)/)
})
