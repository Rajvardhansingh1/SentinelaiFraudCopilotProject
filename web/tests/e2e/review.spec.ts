import { test, expect } from "@playwright/test";

test("genuine sample: verdict renders before evidence, approve records a decision", async ({ page }) => {
  await page.goto("/review");
  await page.getByTestId("sample-genuine").click();
  await page.getByTestId("run-analysis-button").click();

  await expect(page.getByTestId("verdict-card")).toBeVisible({ timeout: 30_000 });

  // Verdict card must precede the evidence section in DOM order.
  const verdictBox = await page.getByTestId("verdict-card").boundingBox();
  const evidenceTrigger = page.getByText("Show evidence");
  await expect(evidenceTrigger).toBeVisible();
  const evidenceBox = await evidenceTrigger.boundingBox();
  expect(verdictBox!.y).toBeLessThan(evidenceBox!.y);

  // No raw JSON anywhere on the page.
  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toMatch(/\{"?\w+"?:/);

  await page.getByTestId("approve-button").click();
  await expect(page.getByTestId("decision-toast")).toHaveText(/Recorded: approved/, { timeout: 15_000 });
});
