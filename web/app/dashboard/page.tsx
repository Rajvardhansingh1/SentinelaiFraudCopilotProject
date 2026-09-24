"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { CostLatencyCards } from "@/components/dashboard/cost-latency-cards";
import { GuardrailCatchesCard } from "@/components/dashboard/guardrail-catches-card";
import { HallucinationChart } from "@/components/dashboard/hallucination-chart";
import { MetricsRow } from "@/components/dashboard/metrics-row";
import { TrafficChart } from "@/components/dashboard/traffic-chart";
import { Skeleton } from "@/components/ui/skeleton";
import { getCalls } from "@/lib/api";
import type { CallLogRow } from "@/lib/types";

export default function DashboardPage() {
  const [calls, setCalls] = useState<CallLogRow[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    const rows = await getCalls(100);
    setCalls(rows);
    setLoading(false);
  }

  // Fetch once on mount only — D-028: manual refresh, no polling loop.
  useEffect(() => {
    load();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Eval dashboard</h1>
          <p className="text-sm text-text-primary/60">Recent proxy call traffic and guardrail activity.</p>
        </div>
        <Button onClick={load} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </div>

      {loading && calls.length === 0 ? (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
          <Skeleton className="h-48 w-full" />
        </div>
      ) : (
        <>
          <MetricsRow calls={calls} />

          {!loading && calls.length === 0 && (
            <p className="text-text-primary/60">No calls recorded yet. Use the playground or review pages, then refresh.</p>
          )}

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <TrafficChart calls={calls} />
            <GuardrailCatchesCard calls={calls} />
          </div>

          <HallucinationChart calls={calls} />

          <CostLatencyCards calls={calls} />
        </>
      )}
    </div>
  );
}
