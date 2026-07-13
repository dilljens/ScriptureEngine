import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://127.0.0.1:5176',
    headless: true,
    viewport: { width: 1280, height: 800 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
  // Playwright manages the Vite dev server + Python API backend
  webServer: [
    {
      command: 'python3 -m uvicorn web.server:app --port 8000 --host 127.0.0.1',
      url: 'http://127.0.0.1:8000/api/v1/health',
      reuseExistingServer: true,
      timeout: 30000,
      cwd: '/home/dillon/_code/scriptureengine',
    },
    {
      command: 'npx vite --port 5176 --host 127.0.0.1',
      url: 'http://127.0.0.1:5176',
      reuseExistingServer: true,
      timeout: 30000,
      cwd: '/home/dillon/_code/scriptureengine/frontend',
    },
  ],
})
