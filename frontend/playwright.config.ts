import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "PYTHONPATH=../backend uv run --project ../backend python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000",
      url: "http://localhost:8000/docs",
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
  ],
  projects: [
    {
      name: "mobile",
      use: { ...devices["Pixel 5"], viewport: { width: 390, height: 844 } },
    },
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
    },
  ],
  expect: { timeout: 10000 },
});
