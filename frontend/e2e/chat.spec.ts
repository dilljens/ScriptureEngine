import { test, expect } from '@playwright/test'

test.describe('Chat panel — verse links', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.clear())
    await page.goto('/')
    await expect(page.locator('h1').first()).toContainText('Isaiah', { timeout: 20000 })
  })

  test('question mark opens chat tab', async ({ page }) => {
    await page.keyboard.press('?')
    const chatTab = page.getByText('Chat').first()
    await expect(chatTab).toBeVisible({ timeout: 5000 })
  })

  test('chat has a send input after opening', async ({ page }) => {
    await page.keyboard.press('?')
    await expect(page.getByPlaceholder(/Ask about/i)).toBeVisible({ timeout: 8000 })
  })

  test('welcome message contains clickable verse ref', async ({ page }) => {
    await page.keyboard.press('?')
    // The welcome message has "gen.1.1" which should be converted to a clickable verse span
    const verseSpan = page.locator('span[data-type="verse"]').first()
    await expect(verseSpan).toBeVisible({ timeout: 10000 })
    // Should show the formatted ref like "Genesis 1:1"
    await expect(verseSpan).toContainText(/Genesis|gen/i)
  })

  test('clicking verse span opens VersePopup', async ({ page }) => {
    await page.keyboard.press('?')
    const verseSpan = page.locator('span[data-type="verse"]').first()
    await expect(verseSpan).toBeVisible({ timeout: 10000 })
    await verseSpan.click()
    // VersePopup should appear with chapter content
    const popupContent = page.locator('text=/Loading|Genesis|gen/i').first()
    await expect(popupContent).toBeVisible({ timeout: 10000 })
  })

  test('VersePopup Open button navigates to chapter', async ({ page }) => {
    await page.keyboard.press('?')
    const verseSpan = page.locator('span[data-type="verse"]').first()
    await expect(verseSpan).toBeVisible({ timeout: 10000 })

    // Get the verse ref before clicking
    const ref = await verseSpan.getAttribute('data-ref')
    await verseSpan.click()

    // Click the "Open" button in the VersePopup
    const openBtn = page.locator('button', { hasText: 'Open' })
    await expect(openBtn).toBeVisible({ timeout: 5000 })
    await openBtn.click()

    // Should navigate to the chapter — breadcrumb should update
    if (ref) {
      const parts = ref.split('.')
      if (parts.length >= 2) {
        const ch = parts[1]
        await expect(page.locator('h1').first()).toContainText(`ch. ${ch}`, { timeout: 10000 })
      }
    }
  })

  test('suggestion buttons appear in welcome message', async ({ page }) => {
    await page.keyboard.press('?')
    // Suggestion buttons are rendered from %%%CLICK:...%%% markers
    const suggestionBtns = page.locator('button', { hasText: 'Trace the Angel' })
    await expect(suggestionBtns.first()).toBeVisible({ timeout: 10000 })
  })

  test('clicking a suggestion shows prebuilt response with verse links', async ({ page }) => {
    await page.keyboard.press('?')
    // Click the first suggestion
    const suggestionBtn = page.locator('button', { hasText: 'Trace the Angel' }).first()
    await expect(suggestionBtn).toBeVisible({ timeout: 10000 })
    await suggestionBtn.click()

    // Prebuilt response should contain verse links (multiple spans)
    const verseSpans = page.locator('span[data-type="verse"]')
    await expect(verseSpans.first()).toBeVisible({ timeout: 10000 })
    const count = await verseSpans.count()
    expect(count).toBeGreaterThanOrEqual(2) // prebuilt response has many verse refs
  })
})
