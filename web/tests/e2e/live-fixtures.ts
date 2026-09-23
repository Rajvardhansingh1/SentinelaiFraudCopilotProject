import { test as base, expect, request as pwRequest } from "@playwright/test";

/** For specs that exercise the real SentinelAI proxy end to end (not mocked
 * API responses) — e.g. asserting a real attack prompt gets really blocked.
 * These need a live proxy at NEXT_PUBLIC_PROXY_BASE_URL (default
 * http://localhost:8000). Each test signs up a fresh throwaway user +
 * project directly against that proxy (same pattern as
 * scripts/sentinel_ci.py's _bootstrap_auth) and injects the real token +
 * project id into localStorage before the page loads, so the UI is already
 * authenticated. Skips (not fails) when the proxy isn't reachable — this
 * mirrors how the rest of this repo treats "needs a live service" tests. */

const PROXY_BASE_URL = process.env.NEXT_PUBLIC_PROXY_BASE_URL ?? "http://localhost:8000";

export const test = base.extend<{ liveAuth: { token: string; projectId: number } }>({
  liveAuth: async ({}, use, testInfo) => {
    const api = await pwRequest.newContext();
    let reachable = true;
    try {
      const health = await api.get(`${PROXY_BASE_URL}/health`, { timeout: 3_000 });
      reachable = health.ok();
    } catch {
      reachable = false;
    }
    if (!reachable) {
      testInfo.skip(true, `SentinelAI proxy not reachable at ${PROXY_BASE_URL} — start it to run this spec.`);
    }

    const email = `e2e-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
    const signup = await api.post(`${PROXY_BASE_URL}/v1/auth/signup`, {
      data: { email, password: "e2e-password-123" },
    });
    const { access_token: token } = await signup.json();
    const project = await api.post(`${PROXY_BASE_URL}/v1/projects`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { name: "E2E Live Project", target_type: "model" },
    });
    const { id: projectId } = await project.json();
    await api.dispose();

    await use({ token, projectId });
  },
  page: async ({ page, liveAuth }, use) => {
    await page.addInitScript(
      ({ token, projectId }) => {
        window.localStorage.setItem("sentinelai_auth_token", token);
        window.localStorage.setItem("sentinelai_auth_user", JSON.stringify({ id: 0, email: "e2e@example.com" }));
        window.localStorage.setItem("sentinelai_active_project_id", String(projectId));
      },
      { token: liveAuth.token, projectId: liveAuth.projectId }
    );
    await use(page);
  },
});

export { expect };
