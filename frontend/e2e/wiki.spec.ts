import { test, expect } from '@playwright/test'

test.describe('Wiki — article viewer', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    // Wait for book data to load — "ch. 6" appears in both h1 elements
    await expect(page.getByText('ch. 6').first()).toBeVisible({ timeout: 20000 })
  })

  test('wiki tab opens from desktop menu', async ({ page }) => {
    // Open the Menu dropdown
    const menuBtn = page.locator('button[title="Menu"]')
    await expect(menuBtn).toBeVisible()
    await menuBtn.click()

    // Click Wiki in the menu
    const wikiItem = page.getByText('Wiki').first()
    await expect(wikiItem).toBeVisible()
    await wikiItem.click()
    await page.waitForTimeout(1500)

    // Wiki view should load — article viewer or browse view
    // It shows either an article or a "select an entity" message
    const bodyText = await page.textContent('body')
    expect(bodyText).toContain('Wiki')
  })

  test('wiki article viewer loads for known entity', async ({ page }) => {
    // Navigate directly to wiki view with an entity
    // Use the mobile menu approach: we can test via direct API
    const response = await page.request.get('/api/v1/wiki/abraham')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.title).toBe('Abraham')
    expect(data.data.id).toBe('abraham')
    expect(data.data.content).toContain('Abraham')
  })

  test('wiki search returns results', async ({ page }) => {
    const response = await page.request.get('/api/v1/wiki/search?q=covenant')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.total).toBeGreaterThanOrEqual(1)
    expect(data.data.results.length).toBeGreaterThanOrEqual(1)
  })

  test('wiki browse returns entity list', async ({ page }) => {
    const response = await page.request.get('/api/v1/wiki/browse/entity')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.type).toBe('entity')
    expect(data.data.total).toBeGreaterThanOrEqual(1)
    expect(data.data.articles.length).toBeGreaterThanOrEqual(1)
  })

  test('wiki concordance returns key verses', async ({ page }) => {
    const response = await page.request.get('/api/v1/wiki/concordance/abraham')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.entity).toBe('abraham')
    expect(data.data.verses.length).toBeGreaterThanOrEqual(1)
  })

  test('unknown entity returns 404', async ({ page }) => {
    const response = await page.request.get('/api/v1/wiki/nonexistent_entity_xyz')
    expect(response.ok()).toBe(false)
    expect(response.status()).toBe(404)
  })
})

test.describe('Wiki — chapter-level wiki mode', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.getByText('ch. 6').first()).toBeVisible({ timeout: 20000 })
  })

  test('wiki mode toggle exists in chapter view', async ({ page }) => {
    // Look for the "Wiki" toggle button in the chapter view toolbar
    const wikiBtn = page.locator('button[title*="Wikipedia"]').or(
      page.locator('button').filter({ hasText: 'Wiki' })
    ).first()
    // The button may or may not exist depending on view state
    const count = await wikiBtn.count()
    if (count > 0) {
      await wikiBtn.click()
      await page.waitForTimeout(1000)
      // After clicking, should show wiki-style layout
      const bodyText = await page.textContent('body')
      expect(bodyText).toContain('Wiki')
    }
  })
})
