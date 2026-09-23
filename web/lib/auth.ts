/**
 * Phase 2 (D-055) frontend: token + active-project storage and the auth
 * endpoints. Plain functions (not a React hook) so api.ts's request helpers
 * can read the current token/project synchronously on every call.
 *
 * ponytail: the JWT lives in localStorage, not an httpOnly cookie — simplest
 * thing that works for a same-origin SPA talking to its own API. Upgrade to
 * httpOnly cookies (with CSRF handling) if this ever needs to resist XSS
 * from third-party script injection.
 */

const TOKEN_KEY = "sentinelai_auth_token";
const USER_KEY = "sentinelai_auth_user";
const PROJECT_KEY = "sentinelai_active_project_id";

export interface AuthUser {
  id: number;
  email: string;
}

const PROXY_BASE_URL = process.env.NEXT_PUBLIC_PROXY_BASE_URL ?? "http://localhost:8000";

function safeLocalStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  return safeLocalStorage()?.getItem(TOKEN_KEY) ?? null;
}

export function getStoredUser(): AuthUser | null {
  const raw = safeLocalStorage()?.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function getActiveProjectId(): number | null {
  const raw = safeLocalStorage()?.getItem(PROJECT_KEY);
  if (!raw) return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

export function setActiveProjectId(id: number | null): void {
  const storage = safeLocalStorage();
  if (!storage) return;
  if (id === null) storage.removeItem(PROJECT_KEY);
  else storage.setItem(PROJECT_KEY, String(id));
}

function storeAuth(token: string, user: AuthUser): void {
  const storage = safeLocalStorage();
  if (!storage) return;
  storage.setItem(TOKEN_KEY, token);
  storage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  const storage = safeLocalStorage();
  if (!storage) return;
  storage.removeItem(TOKEN_KEY);
  storage.removeItem(USER_KEY);
  storage.removeItem(PROJECT_KEY);
}

/** Authorization header, or {} when signed out — spread into fetch headers. */
export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface AuthResult {
  status: "ok" | "error";
  code?: string;
  message?: string;
}

async function authRequest(path: string, email: string, password: string): Promise<AuthResult> {
  try {
    const resp = await fetch(`${PROXY_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const body = await resp.json();
    if (!resp.ok) {
      return { status: "error", code: body?.detail?.code ?? "unknown", message: body?.detail?.message ?? "Request failed." };
    }
    storeAuth(body.access_token, { id: body.user_id, email: body.email });
    return { status: "ok" };
  } catch (err) {
    return { status: "error", code: "network_error", message: err instanceof Error ? err.message : String(err) };
  }
}

export function signup(email: string, password: string): Promise<AuthResult> {
  return authRequest("/v1/auth/signup", email, password);
}

export function login(email: string, password: string): Promise<AuthResult> {
  return authRequest("/v1/auth/login", email, password);
}

export function logout(): void {
  clearAuth();
}

export interface Project {
  id: number;
  workspace_id: number;
  name: string;
  target_type: string;
  repo_url: string | null;
  description: string | null;
  created_at: string;
}

export async function listProjects(): Promise<Project[]> {
  try {
    const resp = await fetch(`${PROXY_BASE_URL}/v1/projects`, { headers: authHeaders() });
    if (!resp.ok) return [];
    return (await resp.json()) as Project[];
  } catch {
    return [];
  }
}

export async function createProject(
  name: string,
  targetType = "model",
  repoUrl?: string,
  description?: string
): Promise<{ status: "ok"; data: Project } | { status: "error"; message: string }> {
  try {
    const resp = await fetch(`${PROXY_BASE_URL}/v1/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ name, target_type: targetType, repo_url: repoUrl || null, description: description || null }),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return { status: "error", message: body?.detail?.message ?? `Failed (${resp.status})` };
    }
    return { status: "ok", data: (await resp.json()) as Project };
  } catch (err) {
    return { status: "error", message: err instanceof Error ? err.message : String(err) };
  }
}

export async function updateProject(
  projectId: number,
  fields: { name?: string; repo_url?: string; description?: string }
): Promise<{ status: "ok"; data: Project } | { status: "error"; message: string }> {
  try {
    const resp = await fetch(`${PROXY_BASE_URL}/v1/projects/${projectId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(fields),
    });
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}));
      return { status: "error", message: body?.detail?.message ?? `Failed (${resp.status})` };
    }
    return { status: "ok", data: (await resp.json()) as Project };
  } catch (err) {
    return { status: "error", message: err instanceof Error ? err.message : String(err) };
  }
}
