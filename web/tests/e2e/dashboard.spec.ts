import { test, expect } from "@playwright/test";

test("dashboard renders without error and refresh re-fetches", async ({ page }) => {
  let callCount = 0;
  await page.route("**/v1/calls*", (route) => {
    callCount += 1;
    route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.goto("/dashboard");

  await expect(page.getByText("Eval dashboard")).toBeVisible();
  // Empty state renders instead of crashing.
  await expect(page.getByText(/no calls recorded yet/i)).toBeVisible();

  const initialCount = callCount;
  await page.getByRole("button", { name: /refresh/i }).click();
  await expect.poll(() => callCount).toBeGreaterThan(initialCount);

  // No raw JSON object ever rendered as visible text.
  const bodyText = await page.locator("body").innerText();
  expect(bodyText).not.toMatch(/\{"/);
});
