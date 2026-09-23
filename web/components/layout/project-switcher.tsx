"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export function ProjectSwitcher() {
  const { user, projects, activeProjectId, setActiveProject, logout } = useAuth();

  if (!user) return null;

  return (
    <div className="mb-4 space-y-2 border-b border-bg-surface pb-4">
      <div className="text-xs text-text-primary/50">{user.email}</div>
      {projects.length > 0 ? (
        <select
          value={activeProjectId ?? ""}
          onChange={(e) => setActiveProject(Number(e.target.value))}
          className="w-full rounded-md border border-slate-600 bg-bg-surface px-2 py-1 text-sm text-text-primary"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      ) : (
        <Link href="/projects/new" className="block text-sm text-accent-teal underline underline-offset-2">
          Create a project
        </Link>
      )}
      <div className="flex items-center justify-between text-xs">
        <Link href="/projects/new" className="text-text-primary/60 hover:text-accent-teal">
          + New project
        </Link>
        <button onClick={logout} className="text-text-primary/60 hover:text-accent-teal">
          Log out
        </button>
      </div>
    </div>
  );
}
