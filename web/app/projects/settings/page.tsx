"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";
import { updateProject } from "@/lib/auth";

export default function ProjectSettingsPage() {
  const { activeProjectId, projects, refreshProjects } = useAuth();
  const project = projects.find((p) => p.id === activeProjectId) ?? null;

  const [name, setName] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (project) {
      setName(project.name);
      setRepoUrl(project.repo_url ?? "");
      setDescription(project.description ?? "");
    }
  }, [project]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (activeProjectId === null) return;
    setSubmitting(true);
    setError(null);
    setSaved(false);
    const result = await updateProject(activeProjectId, { name, repo_url: repoUrl, description });
    setSubmitting(false);
    if (result.status === "error") {
      setError(result.message);
      return;
    }
    await refreshProjects();
    setSaved(true);
  }

  if (!project) {
    return <p className="text-text-primary/60">No active project selected.</p>;
  }

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Project settings</h1>
        <p className="text-sm text-text-primary/60">
          Repository and notes are used only to make remediation guidance more specific — Sentinel never guesses
          them, only restates what you provide here.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>{project.name}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm text-text-primary/80" htmlFor="name">Name</label>
              <input
                id="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border border-slate-600 bg-bg-surface px-3 py-2 text-sm text-text-primary"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-text-primary/80" htmlFor="repo_url">Repository URL</label>
              <input
                id="repo_url"
                placeholder="https://github.com/you/project"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="w-full rounded-md border border-slate-600 bg-bg-surface px-3 py-2 text-sm text-text-primary"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-text-primary/80" htmlFor="description">Notes</label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="w-full rounded-md border border-slate-600 bg-bg-surface px-3 py-2 text-sm text-text-primary"
              />
            </div>
            {error && (
              <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                {error}
              </div>
            )}
            {saved && <p className="text-sm text-emerald-400">Saved.</p>}
            <Button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : "Save"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
