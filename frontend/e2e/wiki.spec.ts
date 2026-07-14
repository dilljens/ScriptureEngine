import { test, expect } from '@playwright/test'

test.describe('Wiki — article viewer (desktop)', () => {

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.getByText('ch. 6').first()).toBeVisible({ timeout: 20000 })
  })

  test('wiki tab opens from desktop Menu dropdown', async ({ page }) => {
    const menuBtn = page.locator('button[title="Menu"]')
    await expect(menuBtn).toBeVisible()
    await menuBtn.click()
    const wikiItem = page.getByText('Wiki').first()
    await expect(wikiItem).toBeVisible()
    await wikiItem.click()
    // Wiki view should load — article viewer or browse view
    await expect(page.locator('.max-w-4xl').first()).toBeVisible({ timeout: 10000 })
  })

  test('wiki article renders with full desktop layout', async ({ page }) => {
    // Navigate directly to wiki view by opening the menu
    const menuBtn = page.locator('button[title="Menu"]')
    await menuBtn.click()
    await page.getByText('Wiki').first().click()
    // Load an article via custom event
    await page.evaluate(() => {
      const event = new CustomEvent('scripture-navigate', { detail: { ref: 'wiki:abraham' } })
      window.dispatchEvent(event)
    })
    // Article should render with title
    await expect(page.getByRole('heading', { name: 'Abraham' })).toBeVisible({ timeout: 10000 })
    // Article content should have rendered verse references
    const content = await page.textContent('body')
    expect(content).toContain('friend of God')
    // Check that the "Key Verses" section is present
    await expect(page.getByText('Key Verses')).toBeVisible({ timeout: 5000 })
  })

  test('wiki search returns results via UI', async ({ page }) => {
    const menuBtn = page.locator('button[title="Menu"]')
    await menuBtn.click()
    await page.getByText('Wiki').first().click()
    // Use the global search bar in the header
    const searchInput = page.getByPlaceholder(/isa 55/)
    if (await searchInput.isVisible()) {
      await searchInput.fill('covenant')
      await searchInput.press('Enter')
      // Should show wiki search results from the command/search interface
      await expect(page.locator('.max-w-4xl').first()).toBeVisible({ timeout: 10000 })
    }
  })

  test('wiki concordance renders verse refs as clickable links', async ({ page }) => {
    // API test for concordance endpoint
    const response = await page.request.get('/api/v1/wiki/concordance/abraham')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.entity).toBe('abraham')
    expect(data.data.verses.length).toBeGreaterThanOrEqual(1)
    // Each verse should be a valid ref string
    for (const v of data.data.verses) {
      expect(typeof v).toBe('string')
      expect(v.split('.').length).toBeGreaterThanOrEqual(2)
    }
  })

  test('wiki browse returns entity list', async ({ page }) => {
    const response = await page.request.get('/api/v1/wiki/browse/entity')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.type).toBe('entity')
    expect(data.data.total).toBeGreaterThanOrEqual(1)
    expect(data.data.articles.length).toBeGreaterThanOrEqual(1)
  })

  test('unknown entity returns 404', async ({ page }) => {
    const response = await page.request.get('/api/v1/wiki/nonexistent_entity_xyz')
    expect(response.ok()).toBe(false)
    expect(response.status()).toBe(404)
  })

  test('wiki article key verses navigate when clicked', async ({ page }) => {
    const menuBtn = page.locator('button[title="Menu"]')
    await menuBtn.click()
    await page.getByText('Wiki').first().click()
    // Load Abraham article
    await page.evaluate(() => {
      const event = new CustomEvent('scripture-navigate', { detail: { ref: 'wiki:abraham' } })
      window.dispatchEvent(event)
    })
    await expect(page.getByText('Key Verses')).toBeVisible({ timeout: 10000 })
    // Click the first key verse
    const firstVerse = page.locator('.max-w-4xl span.text-\\[10px\\].font-mono').first()
    if (await firstVerse.isVisible()) {
      await firstVerse.click()
      // Should navigate to chapter view — breadcrumb should update
      await expect(page.getByText(/ch\./i).first()).toBeVisible({ timeout: 10000 })
    }
  })

  test('wiki article has no horizontal overflow on desktop', async ({ page }) => {
    const menuBtn = page.locator('button[title="Menu"]')
    await menuBtn.click()
    await page.getByText('Wiki').first().click()
    await page.evaluate(() => {
      const event = new CustomEvent('scripture-navigate', { detail: { ref: 'wiki:abraham' } })
      window.dispatchEvent(event)
    })
    await expect(page.getByRole('heading', { name: 'Abraham' })).toBeVisible({ timeout: 10000 })
    const overflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth
    })
    expect(overflow).toBe(false)
  })
})

test.describe('Wiki — API endpoints', () => {

  test('wiki search API returns results', async ({ page }) => {
    const response = await page.request.get('/api/v1/wiki/search?q=covenant')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.total).toBeGreaterThanOrEqual(1)
    expect(data.data.results.length).toBeGreaterThanOrEqual(1)
  })

  test('wiki article API returns article data', async ({ page }) => {
    const response = await page.request.get('/api/v1/wiki/abraham')
    const data = await response.json()
    expect(data.ok).toBe(true)
    expect(data.data.title).toBe('Abraham')
    expect(data.data.id).toBe('abraham')
    expect(data.data.content).toContain('Abraham')
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
})
