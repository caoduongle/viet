import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 45000,
  workers: 2,
  use: {
    baseURL: "http://localhost:8000",
    headless: true,
  },
  webServer: {
    command: "node scripts/serve.mjs",
    url: "http://localhost:8000",
    reuseExistingServer: !process.env.CI,
    timeout: 15000,
  },
});
