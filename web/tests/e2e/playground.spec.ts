import { test, expect } from "./live-fixtures";

test("selecting a prewritten attack and submitting shows Blocked", async ({ page }) => {
  await page.goto("/playground");
  await page.getByTestId("attack-select").selectOption("instruction_override");
  await page.getByTestId("submit-button").click();
  await expect(page.getByTestId("blocked-badge")).toBeVisible({ timeout: 15_000 });
});

test("submitting a benign free-text prompt shows a WeaknessCoach tip", async ({ page }) => {
  await page.goto("/playground");
  await page.getByTestId("attack-select").selectOption("__free_text__");
  await page.getByTestId("prompt-textarea").fill("What is the capital of France?");
  await page.getByTestId("submit-button").click();
  await expect(page.getByTestId("weakness-coach")).toBeVisible({ timeout: 15_000 });
});
