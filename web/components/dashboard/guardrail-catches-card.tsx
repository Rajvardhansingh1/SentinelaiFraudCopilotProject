import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CallLogRow } from "@/lib/types";
import { guardrailCatchCounts } from "@/lib/dashboard-data";

// Small badge/count display — NOT a raw dict dump (the exact complaint this fixes).
export function GuardrailCatchesCard({ calls }: { calls: CallLogRow[] }) {
  const catches = guardrailCatchCounts(calls);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Guardrail catches</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <span>Injection attempts flagged</span>
          <Badge variant={catches.injection > 0 ? "danger" : "muted"}>{catches.injection}</Badge>
        </div>
        <div className="flex items-center justify-between">
          <span>PII detections</span>
          <Badge variant={catches.pii > 0 ? "warning" : "muted"}>{catches.pii}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}
