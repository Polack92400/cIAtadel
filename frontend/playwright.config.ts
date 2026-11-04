import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests run against the full docker compose stack (real Django,
 * Postgres, MinIO, Celery and Ollama) with the seeded demo data:
 *
 *   docker compose up -d && cd frontend && npx playwright test
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 180_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
