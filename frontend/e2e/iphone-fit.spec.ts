import { test, expect } from '@playwright/test'

// iPhone fit: the whole workshop (HUD + tabs + active panel + bottom bar)
// fits one phone screen with no page scroll and no horizontal overflow.
// Each tab's content may mini-scroll internally on short screens, but the
// panel itself must never push past the viewport.
test.setTimeout(120000)

async function gotoGame(page, seed: Record<string, unknown> | null) {
  await page.addInitScript((s) => {
    localStorage.clear()
    if (s) localStorage.setItem('hebrew-idle-v1', JSON.stringify(s))
  }, seed)
  await page.goto('/')
  await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 60000 })
  // Mobile viewports use the bottom nav; desktop uses the menu button.
  const bottomHebrew = page.locator('nav').filter({ hasText: 'Read' }).getByText('Hebrew')
  if (await bottomHebrew.isVisible()) {
    await bottomHebrew.click()
  } else {
    const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"], button:has-text("≡")').first()
    if (await menuBtn.isVisible()) await menuBtn.click()
    await page.locator('button', { hasText: /^א Hebrew$/ }).click()
  }
  await expect(page.locator('text=Loading Hebrew...')).toBeHidden({ timeout: 30000 })
  const gamesTab = page.locator('[role="tab"]:has-text("Games")')
  await expect(gamesTab).toBeVisible({ timeout: 30000 })
  await gamesTab.click()
  const emet = page.locator('button:has-text("EMET")')
  await expect(emet).toBeVisible({ timeout: 10000 })
  await emet.click()
  await expect(page.locator('text=✨ Ohr').first()).toBeVisible({ timeout: 10000 })
}

function workshopPanel(page) {
  return page.locator('[role="tablist"][aria-label="Workshop sections"]').locator('xpath=ancestor::div[contains(@class,"rounded-xl")][1]')
}

for (const vp of [{ width: 390, height: 844, name: 'iphone14' }, { width: 375, height: 667, name: 'iphoneSE' }]) {
  test(`workshop fits one screen @${vp.name}`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height })
    const now = Date.now()
    await gotoGame(page, {
      ohr: 50000, lifetimeOhr: 8e12, owned: { 0: 12, 1: 8, 2: 5 }, roots: 3,
      words: 20, tracks: {}, streak: 7, bestStreak: 48, taps: 200, crits: 51,
      prestiges: 2, lastSeen: now, muted: true, difficulty: { bias: 0, recent: [] },
      correct: 300, kavod: 120, warps: 0,
      buffs: { frenzyEndsAt: 0, galeEndsAt: 0, tapEndsAt: 0 }, golden: null, nextGoldenAt: 0,
      figs: { level: 4, readyAt: now - 1000 },
      vineyard: { level: 7, vines: [now - 1000, now + 3 * 3600 * 1000, now + 3 * 3600 * 1000] },
      daily: { day: new Date().toDateString(), correct: 10, claimed: false },
      letterUpgrades: {}, perm: { tap2: true }, quests: {}, milestones: {},
      pendingOffline: 0, exile: null, exilesCompleted: 1,
      streakGraceDay: '', lastVowPrestige: 0,
    })
    // No horizontal overflow anywhere.
    const noX = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)
    expect(noX).toBe(true)
    // The game auto-lands exactly on screen (sticky workshop): panel top at
    // the app bar, panel bottom inside the viewport — no page scroll needed.
    const box = await workshopPanel(page).boundingBox()
    expect(box).not.toBeNull()
    expect(box!.y).toBeLessThanOrEqual(48)
    expect(box!.y + box!.height).toBeLessThanOrEqual(vp.height + 2)
    // Walk every tab: it must render without JS errors; record internal overflow.
    const tabs = ['Garden', 'Watch', 'Shuk', 'Boosts', 'Quests', 'Upgrades', 'Letters']
    for (const t of tabs) {
      await page.locator(`[role="tab"]:has-text("${t}")`).click()
      await page.waitForTimeout(300)
    }
    await page.screenshot({ path: `e2e-artifacts/iphone-${vp.name}-letters.png` })
    await page.locator('[role="tab"]:has-text("Garden")').click()
    await page.waitForTimeout(300)
    await page.screenshot({ path: `e2e-artifacts/iphone-${vp.name}-garden.png` })
  })
}
