import { test, expect } from '@playwright/test'

test.use({ viewport: { width: 375, height: 667 }, hasTouch: true, isMobile: true })

// Restored long sessions must keep their opening message: the restore merge
// strips welcome content (it must never reach the LLM), so the greeting is
// prepended outside the merge — exactly one anchors the top above the
// windowed history.
test('chat greeting survives a long-session restore', async ({ page, context }) => {
  const msgs: Array<{ role: string; content: string }> = []
  for (let i = 0; i < 40; i++) {
    msgs.push({ role: i % 2 ? 'assistant' : 'user', content: `history message ${i}` })
  }
  await page.addInitScript(() => {
    localStorage.clear()
    localStorage.setItem('current_chat_session', 'long-session')
  })
  await context.route(/\/api\/v1\/conversations\/long-session/, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, data: { id: 'long-session', messages: msgs } }),
    }),
  )
  await page.goto('/')
  await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 30000 })
  await page.locator('nav button[aria-label="Chat"]').click()
  // The real greeting (not a stub marker) anchors the session…
  const greet = page.locator('p').filter({ hasText: "I'm connected to the scripture engine" })
  await expect(greet).toHaveCount(1, { timeout: 20000 })
  // …above the windowed history: 41 messages, 30 shown + greeting.
  await expect(page.locator('text=/Show earlier \\(10 more\\)/')).toHaveCount(1, { timeout: 10000 })
  await greet.scrollIntoViewIfNeeded()
  await expect(greet).toBeVisible({ timeout: 10000 })
})
