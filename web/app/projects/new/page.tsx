"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth-context";

const TARGET_TYPES: { value: string; label: string }[] = [
  { value: "model", label: "AI Model" },
  { value: "application", label: "AI Application" },
  { value: "agent", label: "AI Agent" },
  { value: "api", label: "API / Service" },
];

export default function NewProjectPage() {
  const router = useRouter();
  const { createProject } = useAuth();
  const [name, setName] = useState("");
  const [targetType, setTargetType] = useState("model");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [repoUrl, setRepoUrl] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const result = await createProject(name, targetType, repoUrl, description);
    setSubmitting(false);
    if (result.status === "error") {
      setError(result.message);
      return;
    }
    router.push("/dashboard");
  }

  return (
    <div className="mx-auto mt-16 max-w-sm">
      <Card>
        <CardHeader>
          <CardTitle>Create your first project</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm text-text-primary/80" htmlFor="name">Project name</label>
              <input
                id="name"
                required
                placeholder="Customer Support Agent"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border border-slate-600 bg-bg-surface px-3 py-2 text-sm text-text-primary"
              />
            </div>
            <div>
              <p className="mb-1 text-sm text-text-primary/80">What are you testing?</p>
              <div className="space-y-1">
                {TARGET_TYPES.map((t) => (
                  <label key={t.value} className="flex items-center gap-2 text-sm text-text-primary/80">
                    <input
                      type="radio"
                      name="target_type"
                      value={t.value}
                      checked={targetType === t.value}
                      onChange={() => setTargetType(t.value)}
                    />
                    {t.label}
                  </label>
                ))}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="text-xs text-text-primary/60 underline underline-offset-2 hover:text-accent-teal"
            >
              {showAdvanced ? "Hide" : "Show"} advanced (optional)
            </button>
            {showAdvanced && (
              <div className="space-y-3 rounded-md border border-bg-surface bg-bg-surface/30 p-3">
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
                    placeholder="What this project does, anything Sentinel should know."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full rounded-md border border-slate-600 bg-bg-surface px-3 py-2 text-sm text-text-primary"
                    rows={3}
                  />
                </div>
                <p className="text-xs text-text-primary/50">
                  Used only to make remediation guidance more specific — never guessed, only shown when you provide it.
                </p>
              </div>
            )}
            {error && (
              <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                {error}
              </div>
            )}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Creating..." : "Create project"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
