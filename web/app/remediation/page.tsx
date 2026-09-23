"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FindingStatusBadge } from "@/components/findings/finding-status-badge";
import { listFindings, syncFindings } from "@/lib/api";
import type { Finding } from "@/lib/types";

const OPEN_LIKE = new Set(["OPEN", "ACKNOWLEDGED", "RETEST_REQUIRED"]);

const SEVERITY_VARIANT: Record<string, "danger" | "warning" | "default" | "muted"> = {
  critical: "danger",
  high: "warning",
  medium: "default",
  low: "muted",
};

const SEVERITY_RANK: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 };

const CONFIDENCE_VARIANT: Record<string, "danger" | "warning" | "default" | "muted"> = {
  "HIGH CONFIDENCE": "default",
  LIKELY: "default",
  "REQUIRES INVESTIGATION": "warning",
  "INSUFFICIENT EVIDENCE": "muted",
};

/** Phase 6 (spec_V3.md §29): "Finding -> Evidence -> Recommended Solution ->
 * Retest" without leaving the dashboard. The Findings page lists every
 * finding one row at a time; this page is the aggregated remediation view —
 * every open finding's recommendation visible at once, worst severity first,
 * with retest and per-finding drill-down from the same screen. */
export default function RemediationCenterPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    const rows = await listFindings();
    setFindings(rows);
    setLoading(false);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRetest() {
    setSyncing(true);
    await syncFindings();
    setSyncing(false);
    await load();
  }

  const openFindings = useMemo(
    () =>
      findings
        .filter((f) => OPEN_LIKE.has(f.status))
        .sort((a, b) => (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0)),
    [findings]
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Remediation center</h1>
          <p className="text-sm text-text-primary/60">
            Every open finding&apos;s recommended solution, worst severity first. Sentinel never modifies your code —
            fix it, then retest to confirm.
          </p>
        </div>
        <Button onClick={handleRetest} disabled={syncing}>
          {syncing ? "Retesting..." : "Retest all"}
        </Button>
      </div>

      {loading && <p className="text-text-primary/60">Loading...</p>}

      {!loading && openFindings.length === 0 && (
        <div className="rounded-md border border-bg-surface bg-bg-surface/40 px-4 py-3 text-sm text-text-primary/60">
          No open findings. Either nothing has run yet, or everything is currently passing — use &quot;Retest
          all&quot; above to check for new gaps.
        </div>
      )}

      <div className="flex flex-col gap-3">
        {openFindings.map((f) => {
          const isOpen = expanded === f.id;
          return (
            <Card key={f.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{f.title}</CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant={SEVERITY_VARIANT[f.severity] ?? "muted"}>{f.severity}</Badge>
                    <FindingStatusBadge status={f.status} />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="text-text-primary/80">{f.remediation.expected_fix}</p>
                <div className="flex items-center gap-2">
                  <Badge variant={CONFIDENCE_VARIANT[f.remediation.confidence] ?? "muted"}>
                    {f.remediation.confidence}
                  </Badge>
                  <button
                    onClick={() => setExpanded(isOpen ? null : f.id)}
                    className="text-xs text-accent-teal underline underline-offset-2"
                  >
                    {isOpen ? "Hide details" : "Show evidence & analysis"}
                  </button>
                  <Link href={`/findings/${f.id}`} className="text-xs text-accent-teal underline underline-offset-2">
                    Full finding
                  </Link>
                </div>
                {isOpen && (
                  <div className="space-y-2 border-t border-bg-surface/60 pt-2">
                    <p><span className="font-medium text-text-primary">Observed:</span> {f.remediation.observed}</p>
                    <p><span className="font-medium text-text-primary">Analysis:</span> {f.remediation.analysis}</p>
                    <p><span className="font-medium text-text-primary">Impact:</span> {f.remediation.security_impact}</p>
                    <p><span className="font-medium text-text-primary">Why this fixes it:</span> {f.remediation.why_it_addresses}</p>
                    {f.remediation.components_to_review.length > 0 && (
                      <p>
                        <span className="font-medium text-text-primary">Review:</span>{" "}
                        {f.remediation.components_to_review.map((c) => <code key={c} className="mr-2">{c}</code>)}
                      </p>
                    )}
                    {f.remediation.project_context.length > 0 && (
                      <p className="text-text-primary/60">{f.remediation.project_context.join(" ")}</p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
