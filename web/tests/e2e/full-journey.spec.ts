import { test, expect } from "@playwright/test";

/** Phase 13 (spec_V3.md §67): a clean end-to-end user journey against a
 * real, live proxy — Sign Up -> Login -> Create Project -> Run Assessment ->
 * Findings -> Recommended Solutions -> Generate Report. No mocked API
 * routes: every step is a real request to the SentinelAI proxy. Skips (not
 * fails) if the proxy isn't reachable, same convention as live-fixtures.ts. */

const PROXY_BASE_URL = process.env.NEXT_PUBLIC_PROXY_BASE_URL ?? "http://localhost:8000";

test.beforeEach(async ({ request }, testInfo) => {
  let reachable = true;
  try {
    const health = await request.get(`${PROXY_BASE_URL}/health`, { timeout: 3_000 });
    reachable = health.ok();
  } catch {
    reachable = false;
  }
  testInfo.skip(!reachable, `SentinelAI proxy not reachable at ${PROXY_BASE_URL} — start it to run this spec.`);
});

test("new user: signup -> create project -> run assessment -> findings -> report", async ({ page }) => {
  const email = `journey-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;

  // Sign Up
  await page.goto("/signup");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("journey-password-123");
  await page.getByRole("button", { name: /sign up/i }).click();

  // -> Create Project (redirected here automatically after signup)
  await expect(page).toHaveURL(/\/projects\/new/, { timeout: 15_000 });
  await page.getByLabel("Project name").fill("Journey Test Project");
  await page.getByRole("button", { name: /create project/i }).click();

  // -> lands on the dashboard, authenticated, with a real project active
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
  await expect(page).not.toHaveURL(/\/login/);

  // Run Assessment (security engine suite) and sync Findings
  await page.goto("/findings");
  await page.getByRole("button", { name: /run tests & sync findings/i }).click();
  await expect(page.getByRole("button", { name: /run tests & sync findings/i })).toBeEnabled({ timeout: 30_000 });
  // Never silently bounced back to login — proves the whole auth+project chain worked.
  await expect(page).not.toHaveURL(/\/login/);

  // View Findings -> Recommended Solutions, if the run produced any open finding.
  const firstFindingLink = page.locator("table a").first();
  const hasFinding = await firstFindingLink.isVisible().catch(() => false);
  if (hasFinding) {
    await firstFindingLink.click();
    await expect(page.getByText("Remediation guidance")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Observed")).toBeVisible();
    await expect(page.getByText("Recommendation")).toBeVisible();
  }

  // Remediation center (Phase 6): the same recommendation, aggregated.
  await page.goto("/remediation");
  await expect(page).not.toHaveURL(/\/login/);
  if (hasFinding) {
    await expect(page.getByRole("button", { name: /show evidence & analysis/i }).first()).toBeVisible({ timeout: 10_000 });
  }

  // Project settings: declare repo/notes, confirm it round-trips.
  await page.goto("/projects/settings");
  await page.getByLabel("Repository URL").fill("https://github.com/example/journey-project");
  await page.getByLabel("Notes").fill("Created by the Phase 13 e2e journey test.");
  await page.getByRole("button", { name: /^save$/i }).click();
  await expect(page.getByText("Saved.")).toBeVisible({ timeout: 10_000 });

  // Generate Report
  await page.goto("/reports");
  await page.getByRole("button", { name: /^generate$/i }).first().click();
  await expect(page.getByText(/SentinelAI Security Report/)).toBeVisible({ timeout: 15_000 });
});
