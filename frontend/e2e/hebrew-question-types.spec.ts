import { test, expect } from '@playwright/test'

/**
 * New first-class item types render end-to-end in the real HebrewQuiz UI.
 * API responses are stubbed at the network layer (deterministic — no
 * dependence on curriculum unlock state or FSRS history); what is
 * exercised is the production render + answer + feedback path, including
 * the type badges, Hebrew lang/dir markup, and corrective feedback.
 *
 * Runs on a mobile viewport: the bottom nav is the entry point to Hebrew
 * (desktop menu has no Hebrew item).
 */
test.use({ viewport: { width: 375, height: 667 }, hasTouch: true, isMobile: true })

const DISCOURSE_Q = {
  node_id: 'qal_perfect',
  question_id: 9001,
  type: 'discourse_function',
  question: 'בָּרָא אֱלֹהִים (Gen 1:1, qatal) — past, present, or gnomic?',
  options: [
    'Past — completed event in narrative',
    'Present — ongoing action',
    'Gnomic — timeless truth',
  ],
  answer_mode: 'choice_index',
  category: 'verb',
  difficulty: 0.5,
  node_title: 'Qal Perfect',
}

const SYNTAX_Q = {
  node_id: 'read_exo14',
  question_id: 9002,
  type: 'syntax_parse',
  question: 'Exo 14:14 יְהוָה יִלָּחֵם לָכֶם — which word is the finite verb?',
  options: ['יִלָּחֵם', 'יְהוָה', 'לָכֶם', 'אֵת'],
  answer_mode: 'choice_index',
  category: 'reading',
  difficulty: 0.5,
  node_title: 'Exodus 14 — The Red Sea Crossing',
}

async function openHebrewQuiz(page, context) {
  await page.addInitScript(() => localStorage.clear())
  await page.goto('/')
  await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  // Stub the cumulative quiz with one question of each new type.
  // NOTE: context.route, not page.route — the app's service worker
  // attributes fetches away from page-level handlers.
  await context.route(/\/api\/v1\/hebrew\/quiz/, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, data: { questions: [DISCOURSE_Q, SYNTAX_Q], card: null } }),
    }),
  )
  // Server-authoritative grading stub: correct + corrective feedback.
  await context.route(/\/api\/v1\/hebrew\/progress/, (route) => {
    const body = JSON.parse(route.request().postData() || '{}')
    const isSyntax = body.question_id === 9002
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        data: {
          is_correct: true,
          correct_answer: isSyntax ? 'יִלָּחֵם' : 'Past — completed event in narrative',
          explanation: isSyntax
            ? 'יִלָּחֵם (3ms niphal yiqtol) is the predicate.'
            : 'Qatal presents the event as complete; narrative fixes past reference.',
        },
      }),
    })
  })
  // Bottom-nav Hebrew tab → curriculum dashboard.
  await page.locator('nav button[aria-label="Hebrew"]').click()
  await expect(page.locator('text=/Biblical Hebrew/i').first()).toBeVisible({ timeout: 30000 })
  // Practice dropdown → Quiz entry mounts HebrewQuiz (general review).
  await page.locator('button:has-text("Practice")').first().click()
  await page.locator('button:has-text("Test your knowledge")').click()
}

test.describe('Hebrew question types — discourse_function + syntax_parse', () => {
  test.beforeEach(async ({ page, context }) => {
    await openHebrewQuiz(page, context)
  })

  test('discourse_function renders badge, grades, and shows corrective feedback', async ({ page }) => {
    await expect(page.locator('text=discourse function')).toBeVisible({ timeout: 15000 })
    await expect(page.locator('p[lang="he"]')).toContainText('בָּרָא')
    await page.locator('button:has-text("Past — completed event in narrative")').click()
    await expect(page.locator('text=✓ Correct!')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Correct answer:')).toBeVisible()
    await expect(page.locator('text=/narrative fixes past reference/')).toBeVisible()
  })

  test('syntax_parse follows with Hebrew prompt and choice grading', async ({ page }) => {
    await expect(page.locator('text=discourse function')).toBeVisible({ timeout: 15000 })
    await page.locator('button:has-text("Past — completed event in narrative")').click()
    await expect(page.locator('text=✓ Correct!')).toBeVisible({ timeout: 10000 })
    await page.locator('button:has-text("Next Question")').click()
    await expect(page.locator('text=syntax parse')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('p[lang="he"]')).toContainText('יִלָּחֵם')
    await page.locator('button:has-text("יִלָּחֵם")').first().click()
    await expect(page.locator('text=✓ Correct!')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=/is the predicate/')).toBeVisible()
    await expect(page.locator('button:has-text("See Results")')).toBeVisible()
  })
})
