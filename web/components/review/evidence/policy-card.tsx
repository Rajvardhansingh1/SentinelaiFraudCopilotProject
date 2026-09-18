import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { PolicyVerdict } from "@/lib/types";

interface Props {
  policy: PolicyVerdict | null;
}

export function PolicyCard({ policy }: Props) {
  return (
    <Card data-testid="policy-card">
      <CardTitle>Policy check</CardTitle>
      <CardContent className="space-y-3">
        {!policy ? (
          <p className="text-slate-500">No policy data available.</p>
        ) : (
          <>
            <Badge variant={policy.compliant ? "success" : "danger"}>
              {policy.compliant ? "Compliant" : "Non-compliant"}
            </Badge>
            {policy.triggered_rules.length === 0 ? (
              <p className="text-slate-500">No policy rules triggered.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {policy.triggered_rules.map((rule) => (
                  <Badge key={rule} variant="warning">
                    {rule}
                  </Badge>
                ))}
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
