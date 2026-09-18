import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMs, formatUsd } from "@/lib/format";
import type { CallLogRow } from "@/lib/types";
import { costSummary, latencySummary } from "@/lib/dashboard-data";

// Formatted currency/ms display — never JSON.stringify({total_usd: ...}).
export function CostLatencyCards({ calls }: { calls: CallLogRow[] }) {
  const cost = costSummary(calls);
  const latency = latencySummary(calls);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Cost</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span>Total</span>
            <span className="font-semibold">{formatUsd(cost.total_usd)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Average per call</span>
            <span className="font-semibold">{formatUsd(cost.avg_usd)}</span>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Latency</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          <div className="flex items-center justify-between">
            <span>Average</span>
            <span className="font-semibold">{formatMs(latency.avg_ms)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>p95</span>
            <span className="font-semibold">{formatMs(latency.p95_ms)}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
