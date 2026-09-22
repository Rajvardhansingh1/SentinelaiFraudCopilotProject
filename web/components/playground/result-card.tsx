import { Card, CardContent, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { WeaknessCoach } from "./weakness-coach";
import { classifyResult } from "@/lib/classify-result";
import type { GenerateResponse } from "@/lib/types";

interface Props {
  status: number;
  body: GenerateResponse;
  promptText: string;
  cachedBanner?: string | null;
  isOwnPrompt: boolean;
}

export function ResultCard({ status, body, promptText, cachedBanner, isOwnPrompt }: Props) {
  const injection = body.guardrails?.injection;
  const outcome = classifyResult(status, body);
  const blocked = outcome === "blocked";
  const failed = outcome === "failed";

  return (
    <div data-testid="result-card">
      {cachedBanner && (
        <div className="mb-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">
          {cachedBanner}
        </div>
      )}

      {blocked && (
        <Card className="border-red-500/40">
          <CardTitle>
            <Badge variant="danger" data-testid="blocked-badge">
              Blocked
            </Badge>
          </CardTitle>
          <CardContent>
            <p className="mb-1">Caught by known attack pattern(s):</p>
            <ul className="list-disc pl-5">
              {injection?.matched_patterns.map((p) => (
                <li key={p}>
                  <code className="text-accent-teal">{p}</code>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {!blocked && !failed && (
        <>
          <Card className="border-emerald-500/40">
            <CardTitle>
              <Badge variant="success">Not blocked</Badge>
            </CardTitle>
            <CardContent>
              <p className="whitespace-pre-wrap">{String(body.output ?? "(no output)")}</p>
            </CardContent>
          </Card>
          {isOwnPrompt && <WeaknessCoach promptText={promptText} />}
        </>
      )}

      {failed && (
        <Card className="border-slate-500/40">
          <CardTitle>
            <Badge variant="muted">Request failed</Badge>
          </CardTitle>
          <CardContent>{body.error?.message ?? "Request failed."}</CardContent>
        </Card>
      )}
    </div>
  );
}
