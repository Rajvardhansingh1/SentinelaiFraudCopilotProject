import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatMs, formatUsd } from "@/lib/format";
import type { CallLogRow } from "@/lib/types";
import { costSummary, guardrailCatchCounts, latencySummary } from "@/lib/dashboard-data";

// 4 large stat tiles, biggest numbers first — same verdict-first principle as
// the Review page's verdict card (REACT_FRONTEND_PLAN.md §4.3).
export function MetricsRow({ calls }: { calls: CallLogRow[] }) {
  const catches = guardrailCatchCounts(calls);
  const cost = costSummary(calls);
  const latency = latencySummary(calls);

  const tiles = [
    { label: "Total calls", value: calls.length.toLocaleString() },
    { label: "Guardrail catches", value: (catches.injection + catches.pii).toLocaleString() },
    { label: "Total cost", value: formatUsd(cost.total_usd) },
    { label: "Avg latency", value: formatMs(latency.avg_ms) },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {tiles.map((tile) => (
        <Card key={tile.label}>
          <CardHeader>
            <CardTitle>{tile.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold text-text-primary">{tile.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
