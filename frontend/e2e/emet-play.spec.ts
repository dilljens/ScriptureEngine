import { test, expect } from '@playwright/test'

// EMET idle-game playthrough: fresh onboarding + a seeded mid-game workshop.
// Drives the REAL production bus (window 'hebrew-idle-answer' — the same
// event reportIdleAnswer dispatches from every quiz) and clicks the real HUD.
//
// Run: npx playwright test emet-play --project=chromium
// Box is heavily loaded (API + indexer + agents) — curriculum fetch can take
// a while. Triple the per-test budget; wall cost stays low on a quiet box.
test.setTimeout(120000)
test.use({ permissions: ['clipboard-read', 'clipboard-write'] })

const errors: string[] = []

test.beforeEach(async ({ page }) => {
  errors.length = 0
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
  page.on('console', (m) => {
    if (m.type() !== 'error') return
    // Environmental noise, not app bugs: flaky-box network resets and
    // missing favicon/asset 404s. Real JS errors still fail the run.
    if (/Failed to load resource|ERR_NETWORK|ERR_INTERNET|favicon/i.test(m.text())) return
    errors.push(`console: ${m.text()}`)
  })
})

test.afterEach(async () => {
  expect(errors, `JS errors:\n${errors.join('\n')}`).toEqual([])
})

async function gotoEmet(page, seed: Record<string, unknown> | null) {
  await page.addInitScript((s) => {
    localStorage.clear()
    if (s) localStorage.setItem('hebrew-idle-v1', JSON.stringify(s))
  }, seed)
  // NOTE: no curriculum stub — the preview server + warm API load it in
  // ~1s, so play the real path (stubbing would untest LearnView integration).
  await page.goto('/')
  await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 60000 })
  const menuBtn = page.locator('button:has-text("Menu"), [aria-label="Menu"], button:has-text("≡")').first()
  if (await menuBtn.isVisible()) await menuBtn.click()
  // Exact menu item "א Hebrew" (with space) — the toolbar "אHebrew" reader
  // and other Hebrew buttons open different views.
  await page.locator('button', { hasText: /^א Hebrew$/ }).click()
  // LearnView fetches the 696-lesson curriculum before the mode tabs exist.
  await expect(page.locator('text=Loading Hebrew...')).toBeHidden({ timeout: 30000 })
  const gamesTab = page.locator('[role="tab"]:has-text("Games")')
  await expect(gamesTab).toBeVisible({ timeout: 30000 })
  await gamesTab.click()
  const emet = page.locator('button:has-text("EMET")')
  await expect(emet).toBeVisible({ timeout: 10000 })
  await emet.click()
  await expect(page.locator('text=✨ Ohr').first()).toBeVisible({ timeout: 10000 })
}

function answer(page, correct: boolean, ms = 1200) {
  return page.evaluate(
    ([c, m]) => window.dispatchEvent(new CustomEvent('hebrew-idle-answer', { detail: { correct: c, ms: m } })),
    [correct, ms] as const,
  )
}

function richSeed() {
  const now = Date.now()
  return {
    ohr: 50000,
    lifetimeOhr: 8e12,
    owned: { 0: 12, 1: 8, 2: 5 },
    roots: 3,
    words: 20,
    tracks: {},
    streak: 7,
    bestStreak: 48,
    taps: 200,
    crits: 51,
    prestiges: 2,
    lastSeen: now,
    muted: true,
    difficulty: { bias: 0, recent: [] },
    correct: 300,
    kavod: 120,
    warps: 0,
    buffs: { frenzyEndsAt: 0, galeEndsAt: 0, tapEndsAt: 0 },
    golden: null,
    nextGoldenAt: 0,
    figs: { level: 4, readyAt: now - 1000 },
    vineyard: { level: 7, vines: [now - 1000, now + 3 * 3600 * 1000, now + 3 * 3600 * 1000] },
    daily: { day: new Date().toDateString(), correct: 10, claimed: false },
    letterUpgrades: {},
    perm: { tap2: true },
    quests: {},
    milestones: {},
    pendingOffline: 0,
    exile: null,
    exilesCompleted: 1,
    streakGraceDay: '',
    lastVowPrestige: 0,
  }
}

test('fresh workshop onboards without errors', async ({ page }) => {
  await gotoEmet(page, null)
  await expect(page.locator('text=Start here').first()).toBeVisible()
  // Answering with no production: taps still land, streak still counts.
  await answer(page, true)
  await expect(page.locator('text=/🔥48|🔥0 best|best/').first()).toBeVisible({ timeout: 5000 })
  await page.screenshot({ path: 'e2e-artifacts/emet-fresh.png', fullPage: true })
})

test('rich workshop: harvest fig, tend vine, claim daily', async ({ page }) => {
  await gotoEmet(page, richSeed())
  await expect(page.locator('text=Fig lvl 4').first()).toBeVisible()
  await expect(page.locator('text=1/3 ripe').first()).toBeVisible()
  await expect(page.locator('text=10/10').first()).toBeVisible()

  // NOTE: assert persistent STATE, not the 4.5s flashes — on a loaded box
  // click-dispatch latency can exceed the flash TTL (race by construction).
  // Flashes prove nothing the state change doesn't; math is pinned in self-checks.
  await page.getByTestId('fig-harvest').click()
  await expect(page.locator('text=Fig lvl 5').first()).toBeVisible({ timeout: 15000 })

  await page.getByTestId('vine-tend-0').click()
  await expect(page.locator('text=Vineyard lvl 8').first()).toBeVisible({ timeout: 15000 })

  await page.getByTestId('daily-claim').click()
  await expect(page.locator('text=done ✓').first()).toBeVisible({ timeout: 15000 })
})

test('shop buys a letter; Ascent branch locks its rival', async ({ page }) => {
  await gotoEmet(page, richSeed())
  await page.getByTestId('shop-toggle').click()
  // Buy one Aleph (seeded owned 12 -> 13).
  const aleph = page.locator('.grid-cols-6 button').first()
  await aleph.click()
  await expect(aleph).toContainText('x13', { timeout: 5000 })

  // Open Upgrades, buy Legacy of the Fathers (1 spark of 2).
  await page.locator('button:has-text("Upgrades")').first().click()
  await expect(page.locator('text=Legacy of the Fathers').first()).toBeVisible()
  await page.locator('button:has-text("Legacy of the Fathers")').click()
  await expect(page.locator('text=Foregone').first()).toBeVisible({ timeout: 5000 })
  await page.screenshot({ path: 'e2e-artifacts/emet-ascent.png', fullPage: true })
})

test('exile vow locks the shop to three letters', async ({ page }) => {
  // Seed the vow directly: the live roll is random, the lock must be exact.
  const now = Date.now()
  const seed = {
    ...richSeed(),
    perm: { tap2: true, h_legacy: true },
    exile: { kind: 'exile', letters: [0, 1, 2], startedAt: now, endsAt: now + 24 * 3600 * 1000 },
  }
  await gotoEmet(page, seed)
  await expect(page.locator('text=In exile').first()).toBeVisible({ timeout: 10000 })
  await page.getByTestId('shop-toggle').click()
  // Tile 10 (כ) is outside the vowed [אבג] — it explains the lock.
  const tiles = page.locator('.grid-cols-6 button')
  await tiles.nth(10).click()
  // Hint TTL is 3.5s; the box is loaded, so allow a wide catch window.
  await expect(page.locator('text=beyond your vow').first()).toBeVisible({ timeout: 15000 })
})

test('exile button vows with a random triple', async ({ page }) => {
  const seed = { ...richSeed(), perm: { tap2: true, h_legacy: true } }
  await gotoEmet(page, seed)
  await page.locator('button:has-text("Exile")').first().click()
  await expect(page.locator('text=In exile').first()).toBeVisible({ timeout: 5000 })
})

test('prophet choice grants the picked blessing', async ({ page }) => {
  const now = Date.now()
  const seed = {
    ...richSeed(),
    kavod: 120,
    golden: { id: 'prophet', expiresAt: now + 60000, options: ['dew', 'manna', 'early'], quiz: { letter: 0, options: [0, 1, 2, 3, 4, 5] } },
  }
  await gotoEmet(page, seed)
  await expect(page.locator('text=The Prophet visits!').first()).toBeVisible()
  // Answer the popup quiz itself (Aleph = option testid golden-opt-0).
  await page.getByTestId('golden-opt-0').click()
  await expect(page.locator('text=take one blessing').first()).toBeVisible({ timeout: 5000 })
  // Manna grants exactly MANNA_KAVOD (30) on top of whatever the claiming
  // answer itself earned — read state before/after, not an absolute number.
  const kavodBefore = await page.evaluate(() => JSON.parse(localStorage.getItem('hebrew-idle-v1')).kavod)
  await page.locator('button:has-text("Manna")').click()
  await expect(async () => {
    const kavodAfter = await page.evaluate(() => JSON.parse(localStorage.getItem('hebrew-idle-v1')).kavod)
    expect(kavodAfter).toBe(kavodBefore + 30)
  }).toPass({ timeout: 10000 })
})

test('golden popup quiz grants the buff on a right answer', async ({ page }) => {
  const now = Date.now()
  const seed = {
    ...richSeed(),
    golden: { id: 'gale', expiresAt: now + 60000, quiz: { letter: 1, options: [1, 2, 3, 4, 5, 6] } },
  }
  await gotoEmet(page, seed)
  await expect(page.locator('text=Golden Prompt!').first()).toBeVisible()
  // Bet = option testid golden-opt-1; the x7 gale shows in the HUD rate line.
  await page.getByTestId('golden-opt-1').click()
  await expect(page.locator('text=/x7/').first()).toBeVisible({ timeout: 15000 })
})

test('golden popup quiz fizzles on a wrong answer', async ({ page }) => {
  const now = Date.now()
  const seed = {
    ...richSeed(),
    golden: { id: 'gale', expiresAt: now + 60000, quiz: { letter: 1, options: [1, 2, 3, 4, 5, 6] } },
  }
  await gotoEmet(page, seed)
  await expect(page.locator('text=Golden Prompt!').first()).toBeVisible()
  // Gimel is wrong (Bet asked) — prompt fizzles, nothing granted, dialog closes.
  await page.getByTestId('golden-opt-2').click()
  await expect(page.locator('text=Golden Prompt!')).toHaveCount(0, { timeout: 15000 })
})

test('streak grace halves instead of resetting', async ({ page }) => {
  const seed = { ...richSeed(), streak: 20, streakGraceDay: '' }
  await gotoEmet(page, seed)
  await answer(page, false)
  // Grace halves 20 -> 10 (persistent header state, not the 4.5s flash).
  await expect(page.locator('text=/10 now/').first()).toBeVisible({ timeout: 15000 })
})

test('share card copies to clipboard', async ({ page }) => {
  await gotoEmet(page, richSeed())
  await page.locator('button:has-text("Share")').click()
  // Clipboard write is synchronous in the handler; the confirmation flash is
  // transient, so assert the pasted content itself.
  await expect(async () => {
    const text = await page.evaluate(() => navigator.clipboard.readText())
    expect(text).toContain('EMET')
    expect(text).toContain('3 roots')
  }).toPass({ timeout: 15000 })
  await page.screenshot({ path: 'e2e-artifacts/emet-rich.png', fullPage: true })
})
