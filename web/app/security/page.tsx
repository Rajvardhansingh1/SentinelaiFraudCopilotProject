"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/security/status-badge";
import { DashboardSummary } from "@/components/security/dashboard-summary";
import { Skeleton } from "@/components/ui/skeleton";
import { runSecurityTests } from "@/lib/api";
import type { SecurityTestResult } from "@/lib/types";

const SEVERITY_VARIANT: Record<string, "danger" | "warning" | "default" | "muted"> = {
  critical: "danger",
  high: "warning",
  medium: "default",
  low: "muted",
};

export default function SecurityTestsPage() {
  const [results, setResults] = useState<SecurityTestResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [ranOnce, setRanOnce] = useState(false);

  async function run() {
    setLoading(true);
    const rows = await runSecurityTests();
    setResults(rows);
    setLoading(false);
    setRanOnce(true);
  }

  useEffect(() => {
    run();
  }, []);

  const counts = results.reduce<Record<string, number>>((acc, r) => {
    acc[r.status] = (acc[r.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Security dashboard</h1>
        <p className="text-sm text-text-primary/60">
          Real counts from SentinelAI&apos;s recorded test runs and open findings — nothing here is fabricated.
        </p>
      </div>

      <DashboardSummary />

      <div className="flex items-center justify-between border-t border-bg-surface pt-6">
        <div>
          <h2 className="text-xl font-semibold text-text-primary">Live test run</h2>
          <p className="text-sm text-text-primary/60">
            Runs SentinelAI&apos;s built-in attack library (proxy/engine) against the live detector/scanner. This does
            not record history — use Findings&apos; &quot;Run tests &amp; sync findings&quot; for that.
          </p>
        </div>
        <Button onClick={run} disabled={loading}>
          {loading ? "Running..." : "Run all"}
        </Button>
      </div>

      {loading && (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      )}

      {ranOnce && !loading && results.length === 0 && (
        <p className="text-text-primary/60">No tests returned — is the SentinelAI proxy running?</p>
      )}

      {results.length > 0 && (
        <div className="flex gap-2 text-sm">
          {Object.entries(counts).map(([status, count]) => (
            <span key={status} className="text-text-primary/60">
              {status}: {count}
            </span>
          ))}
        </div>
      )}

      <div className="overflow-x-auto rounded-md border border-bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="bg-bg-surface/60 text-text-primary/60">
            <tr>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Category</th>
              <th className="px-3 py-2">Test</th>
              <th className="px-3 py-2">Severity</th>
              <th className="px-3 py-2">Detail</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.test_id} className="border-t border-bg-surface/60">
                <td className="px-3 py-2">
                  <StatusBadge status={r.status} />
                </td>
                <td className="px-3 py-2 text-text-primary/80">{r.category}</td>
                <td className="px-3 py-2 text-text-primary">{r.name}</td>
                <td className="px-3 py-2">
                  <Badge variant={SEVERITY_VARIANT[r.severity] ?? "muted"}>{r.severity}</Badge>
                </td>
                <td className="px-3 py-2 text-text-primary/70">{r.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
