"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import {
  type AuthUser,
  type Project,
  clearAuth,
  createProject as createProjectRequest,
  getActiveProjectId,
  getStoredUser,
  getToken,
  listProjects,
  login as loginRequest,
  setActiveProjectId as persistActiveProjectId,
  signup as signupRequest,
} from "./auth";

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  projects: Project[];
  activeProjectId: number | null;
  login: (email: string, password: string) => Promise<{ status: "ok" } | { status: "error"; message: string }>;
  signup: (email: string, password: string) => Promise<{ status: "ok" } | { status: "error"; message: string }>;
  logout: () => void;
  refreshProjects: () => Promise<void>;
  createProject: (name: string, targetType?: string) => Promise<{ status: "ok" } | { status: "error"; message: string }>;
  setActiveProject: (id: number) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectIdState] = useState<number | null>(null);

  const refreshProjects = useCallback(async () => {
    const list = await listProjects();
    setProjects(list);
    // Auto-pick a project if none is active yet — the dashboard/findings/etc.
    // pages all require one, so a fresh login shouldn't leave every page 400ing.
    const stored = getActiveProjectId();
    const stillValid = stored !== null && list.some((p) => p.id === stored);
    if (stillValid) {
      setActiveProjectIdState(stored);
    } else if (list.length > 0) {
      persistActiveProjectId(list[0].id);
      setActiveProjectIdState(list[0].id);
    } else {
      setActiveProjectIdState(null);
    }
  }, []);

  useEffect(() => {
    const token = getToken();
    const storedUser = getStoredUser();
    if (token && storedUser) {
      setUser(storedUser);
      refreshProjects().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(email: string, password: string) {
    const result = await loginRequest(email, password);
    if (result.status === "error") return { status: "error" as const, message: result.message ?? "Login failed." };
    setUser(getStoredUser());
    await refreshProjects();
    return { status: "ok" as const };
  }

  async function signup(email: string, password: string) {
    const result = await signupRequest(email, password);
    if (result.status === "error") return { status: "error" as const, message: result.message ?? "Signup failed." };
    setUser(getStoredUser());
    await refreshProjects();
    return { status: "ok" as const };
  }

  function logout() {
    clearAuth();
    setUser(null);
    setProjects([]);
    setActiveProjectIdState(null);
  }

  function setActiveProject(id: number) {
    persistActiveProjectId(id);
    setActiveProjectIdState(id);
  }

  async function createProject(name: string, targetType = "model") {
    const result = await createProjectRequest(name, targetType);
    if (result.status === "error") return result;
    await refreshProjects();
    setActiveProject(result.data.id);
    return { status: "ok" as const };
  }

  return (
    <AuthContext.Provider
      value={{ user, loading, projects, activeProjectId, login, signup, logout, refreshProjects, createProject, setActiveProject }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
