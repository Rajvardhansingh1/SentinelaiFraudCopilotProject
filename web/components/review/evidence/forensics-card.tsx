import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ForensicsResult } from "@/lib/types";

interface Props {
  forensics: ForensicsResult | null;
}

const TAMPER_VARIANT = { low: "success", medium: "warning", high: "danger" } as const;

export function ForensicsCard({ forensics }: Props) {
  return (
    <Card data-testid="forensics-card">
      <CardTitle>Forensics</CardTitle>
      <CardContent className="space-y-3">
        {!forensics ? (
          <p className="text-slate-500">No forensics data available.</p>
        ) : (
          <>
            <Badge variant={TAMPER_VARIANT[forensics.tamper_likelihood]}>
              Tamper likelihood: {forensics.tamper_likelihood}
            </Badge>

            {/* Simple CSS arc gauge — no chart library needed for one value. */}
            <div className="flex items-center gap-3">
              <span className="text-slate-500">ELA score</span>
              <div className="h-2 w-40 overflow-hidden rounded-full bg-bg-base">
                <div
                  className="h-full rounded-full bg-accent-teal"
                  style={{ width: `${Math.min(100, Math.round(forensics.ela_score * 100))}%` }}
                />
              </div>
              <span>{forensics.ela_score.toFixed(3)}</span>
            </div>

            {forensics.exif_flags.length === 0 ? (
              <p className="text-slate-500">No EXIF inconsistencies found.</p>
            ) : (
              <ul className="list-disc pl-5">
                {forensics.exif_flags.map((flag) => (
                  <li key={flag}>{flag}</li>
                ))}
              </ul>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
