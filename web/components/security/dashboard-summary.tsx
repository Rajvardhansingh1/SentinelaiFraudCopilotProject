"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/security/status-badge";
import { getSecurityDashboard } from "@/lib/api";
import type { SecurityDashboardSummary } from "@/lib/types";

const SEVERITY_VARIANT: Record<string, "danger" | "warning" | "default" | "muted"> = {
  critical: "danger",
  high: "warning",
  medium: "default",
  low: "muted",
};

type LoadState = "loading" | "error" | "empty" | "ready";

export function DashboardSummary() {
  const [state, setState] = useState<LoadState>("loading");
  const [summary, setSummary] = useState<SecurityDashboardSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setState("loading");
      const result = await getSecurityDashboard();
      if (cancelled) return;
      if (result.status === "error") {
        setErrorMessage(result.message);
        setState("error");
        return;
      }
      setSummary(result.data);
      setState(result.data.total_tests === 0 && result.data.last_run_at === null ? "empty" : "ready");
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === "loading") {
    return <p className="text-text-primary/60">Loading dashboard...</p>;
  }

  if (state === "error") {
    return (
      <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        Could not reach SentinelAI to load the dashboard: {errorMessage}
      </div>
    );
  }

  if (state === "empty" || !summary) {
    return (
      <div className="rounded-md border border-bg-surface bg-bg-surface/40 px-4 py-3 text-sm text-text-primary/60">
        No security tests have been recorded yet. Use &quot;Run tests &amp; sync findings&quot; below (or on the
        Findings page) to populate this dashboard with real data.
      </div>
    );
  }

  const severityEntries = Object.entries(summary.severity_distribution);

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs text-text-primary/50">
        Last run: {summary.last_run_at ? new Date(summary.last_run_at).toLocaleString() : "never"}
      </p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Total tests</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold">{summary.total_tests}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Passed</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-emerald-400">{summary.passed}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Failed</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-red-400">{summary.failed}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Errors</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-amber-400">{summary.errors}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Inconclusive</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-text-primary/70">{summary.inconclusive}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Not run</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-text-primary/50">{summary.not_run}</CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Open findings</CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-bold text-accent-teal">{summary.open_findings}</CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Open findings by severity</CardTitle>
          </CardHeader>
          <CardContent>
            {severityEntries.length === 0 ? (
              <p className="text-text-primary/50">No open findings.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {severityEntries.map(([severity, count]) => (
                  <Badge key={severity} variant={SEVERITY_VARIANT[severity] ?? "muted"}>
                    {severity}: {count}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Affected models / providers</CardTitle>
          </CardHeader>
          <CardContent>
            {summary.affected_models.length === 0 ? (
              <p className="text-text-primary/50">No test activity recorded yet.</p>
            ) : (
              <ul className="space-y-1">
                {summary.affected_models.map((m) => (
                  <li key={`${m.provider}-${m.model}`}>
                    {m.provider} / {m.model}
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent security activity</CardTitle>
        </CardHeader>
        <CardContent>
          {summary.recent_activity.length === 0 ? (
            <p className="text-text-primary/50">No recent activity.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-text-primary/50">
                  <tr>
                    <th className="py-1 pr-3">Status</th>
                    <th className="py-1 pr-3">Category</th>
                    <th className="py-1 pr-3">Test</th>
                    <th className="py-1 pr-3">When</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.recent_activity.map((row) => (
                    <tr key={`${row.test_id}-${row.executed_at}`} className="border-t border-bg-surface/60">
                      <td className="py-1 pr-3">
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="py-1 pr-3">{row.category}</td>
                      <td className="py-1 pr-3">{row.test_id}</td>
                      <td className="py-1 pr-3 text-text-primary/50">{new Date(row.executed_at).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recommendations & reports</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4 text-sm">
          <Link href="/remediation" className="text-accent-teal underline underline-offset-2">
            {summary.open_findings > 0
              ? `View ${summary.open_findings} recommended solution${summary.open_findings === 1 ? "" : "s"} →`
              : "Remediation center →"}
          </Link>
          <Link href="/reports" className="text-accent-teal underline underline-offset-2">
            Generate a report →
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
