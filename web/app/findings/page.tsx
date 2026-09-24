"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FindingStatusBadge } from "@/components/findings/finding-status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { listFindings, syncFindings } from "@/lib/api";
import type { Finding, FindingStatusValue } from "@/lib/types";

const STATUS_FILTERS: (FindingStatusValue | "ALL")[] = ["ALL", "OPEN", "ACKNOWLEDGED", "RETEST_REQUIRED", "RESOLVED"];

const SEVERITY_VARIANT: Record<string, "danger" | "warning" | "default" | "muted"> = {
  critical: "danger",
  high: "warning",
  medium: "default",
  low: "muted",
};

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [filter, setFilter] = useState<FindingStatusValue | "ALL">("ALL");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  async function load(status: FindingStatusValue | "ALL") {
    setLoading(true);
    const rows = await listFindings(status === "ALL" ? undefined : status);
    setFindings(rows);
    setLoading(false);
  }

  async function handleSync() {
    setSyncing(true);
    await syncFindings();
    setSyncing(false);
    await load(filter);
  }

  useEffect(() => {
    load(filter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Findings</h1>
          <p className="text-sm text-text-primary/60">
            Opened from security tests whose guardrail failed to block a known attack. Historical evidence is never deleted.
          </p>
        </div>
        <Button onClick={handleSync} disabled={syncing}>
          {syncing ? "Syncing..." : "Run tests & sync findings"}
        </Button>
      </div>

      <div className="flex gap-2">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`rounded-md border px-3 py-1 text-xs ${
              filter === s
                ? "border-accent-teal bg-accent-teal/10 text-accent-teal"
                : "border-bg-surface text-text-primary/60 hover:text-text-primary"
            }`}
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {!loading && findings.length === 0 && (
        <p className="text-text-primary/60">
          No findings{filter !== "ALL" ? ` with status ${filter}` : ""}. Run tests & sync to check for new ones.
        </p>
      )}

      {!loading && findings.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="bg-bg-surface/60 text-text-primary/60">
              <tr>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Title</th>
                <th className="px-3 py-2">Severity</th>
                <th className="px-3 py-2">Opened</th>
              </tr>
            </thead>
            <tbody>
              {findings.map((f) => (
                <tr key={f.id} className="border-t border-bg-surface/60">
                  <td className="px-3 py-2">
                    <FindingStatusBadge status={f.status} />
                  </td>
                  <td className="px-3 py-2 text-text-primary/80">{f.category}</td>
                  <td className="px-3 py-2">
                    <Link href={`/findings/${f.id}`} className="text-accent-teal underline underline-offset-2">
                      {f.title}
                    </Link>
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant={SEVERITY_VARIANT[f.severity] ?? "muted"}>{f.severity}</Badge>
                  </td>
                  <td className="px-3 py-2 text-text-primary/60">{new Date(f.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
