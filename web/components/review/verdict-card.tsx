import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ForensicsResult, Guardrails, PolicyVerdict } from "@/lib/types";

interface Props {
  policy: PolicyVerdict | null;
  forensics: ForensicsResult | null;
  extractionGuardrails: Guardrails | null;
  confidence: number;
  hallucinationPct: number;
  children?: React.ReactNode;
}

const TAMPER_VARIANT = { low: "success", medium: "warning", high: "danger" } as const;

export function VerdictCard({
  policy,
  forensics,
  extractionGuardrails,
  confidence,
  hallucinationPct,
  children,
}: Props) {
  const compliant = policy?.compliant ?? true;
  const injectionCaught = extractionGuardrails?.injection?.flagged === true;

  return (
    <Card className="border-2" data-testid="verdict-card">
      <CardTitle className="text-base">System verdict</CardTitle>
      <CardContent className="space-y-4">
        {injectionCaught && (
          <div
            className="rounded-md border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm text-red-300"
            data-testid="injection-caught-banner"
          >
            <p className="font-medium">
              SentinelAI&apos;s injection detector — the same engine protecting the Red-Team Playground —
              caught a prompt injection hidden in this receipt&apos;s scanned text before it reached the
              policy checker.
            </p>
            {extractionGuardrails!.injection.matched_patterns.length > 0 && (
              <p className="mt-1 text-red-400">
                Matched pattern:{" "}
                <code>{extractionGuardrails!.injection.matched_patterns.join(", ")}</code>
              </p>
            )}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <Badge variant={compliant ? "success" : "danger"} className="text-sm">
            {compliant ? "Compliant" : "Non-compliant"}
          </Badge>
          {forensics && (
            <Badge variant={TAMPER_VARIANT[forensics.tamper_likelihood]} className="text-sm">
              Tamper likelihood: {forensics.tamper_likelihood}
            </Badge>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-6 text-sm">
          <div>
            <span className="text-slate-500">Grounding-fidelity confidence: </span>
            <span className="font-semibold">{Math.round(confidence * 100)}%</span>
          </div>
          <div>
            <span className="text-slate-500">Hallucination score: </span>
            <span>{Math.round(hallucinationPct * 100)}%</span>
          </div>
        </div>

        {/* D-026: not a calibrated probability — MVP heuristic ceiling, labeled honestly. */}
        <p className="text-xs text-slate-500">
          Confidence is 1 minus the report&apos;s hallucination score — a grounding-fidelity heuristic, not a
          calibrated probability.
        </p>

        {/* D-004: system verdict stays visually distinct from the human decision below. */}
        <div className="border-t border-bg-surface pt-3">
          <p className="mb-2 text-xs font-medium text-amber-400">
            This is model output, not a final decision.
          </p>
          {children}
        </div>
      </CardContent>
    </Card>
  );
}
