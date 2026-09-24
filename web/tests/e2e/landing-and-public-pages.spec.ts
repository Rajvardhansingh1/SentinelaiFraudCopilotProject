import { test, expect } from "@playwright/test";

test.describe("Public marketing pages", () => {
  test("landing page loads with no console errors and shows the CTA", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") errors.push(msg.text());
    });

    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByRole("link", { name: /get started/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /log in/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /sign up/i })).toBeVisible();

    expect(errors, `console errors on landing page: ${errors.join(", ")}`).toHaveLength(0);
  });

  test("about page is reachable without login", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("heading", { name: /about/i })).toBeVisible();
  });

  test("install page shows real terminal commands", async ({ page }) => {
    await page.goto("/install");
    await expect(page.getByText(/pip install -r requirements.txt/)).toBeVisible();
  });

  test("landing page nav routes to login and signup", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /log in/i }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/");
    await page.getByRole("link", { name: /sign up/i }).click();
    await expect(page).toHaveURL(/\/signup/);
  });
});
