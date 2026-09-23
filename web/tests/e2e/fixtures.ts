import { test as base, expect } from "@playwright/test";

/** Phase 2 (D-055) broke every existing e2e spec that assumed no auth — every
 * protected route now redirects to /login without a token. These specs test
 * page behavior against mocked API responses, not real auth, so the fixture
 * injects a fake token/user into localStorage before the app's AuthProvider
 * ever reads it, and mocks GET /v1/projects so the project switcher has
 * something to show. No real proxy is required to run these. */

const FAKE_TOKEN = "e2e-fake-token";
const FAKE_USER = { id: 1, email: "e2e@example.com" };
export const FAKE_PROJECT = {
  id: 1,
  workspace_id: 1,
  name: "E2E Project",
  target_type: "model",
  created_at: new Date().toISOString(),
};

export const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript(
      ({ token, user }) => {
        window.localStorage.setItem("sentinelai_auth_token", token);
        window.localStorage.setItem("sentinelai_auth_user", JSON.stringify(user));
      },
      { token: FAKE_TOKEN, user: FAKE_USER }
    );
    await page.route("**/v1/projects", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([FAKE_PROJECT]) });
      } else {
        await route.continue();
      }
    });
    await use(page);
  },
});

export { expect };
