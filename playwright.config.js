// @ts-check
const { defineConfig } = require('@playwright/test');

/**
 * Playwright configuration for kgiit E2E tests.
 *
 * Tests target the FastAPI GUI bridge server at http://127.0.0.1:8765.
 * The server is started automatically via `webServer` config below.
 */
module.exports = defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,       // Sequential — tests share a server
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'html' : 'list',
  timeout: 30_000,

  use: {
    baseURL: 'http://127.0.0.1:8765',
    trace: 'on-first-retry',
  },

  /* Start the FastAPI server before running tests */
  webServer: {
    command: 'python -m uvicorn kgiit.learn.server:app --host 127.0.0.1 --port 8765',
    url: 'http://127.0.0.1:8765/api/tracks',
    reuseExistingServer: !process.env.CI,
    timeout: 15_000,
  },

  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
});
