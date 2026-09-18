import { explainWeakness } from "@/lib/weakness-heuristics";
import { Card, CardContent, CardTitle } from "@/components/ui/card";

export function WeaknessCoach({ promptText }: { promptText: string }) {
  const tips = explainWeakness(promptText);

  return (
    <Card className="mt-3 border-amber-500/30" data-testid="weakness-coach">
      <CardTitle className="mb-2 text-amber-400">Weakness coach</CardTitle>
      <CardContent className="space-y-3">
        {tips.map((tip) => (
          <div key={tip.pattern} className="border-l-2 border-amber-500/50 pl-3">
            <p className="font-medium text-text-primary">{tip.headline}</p>
            <p className="text-slate-300">{tip.detail}</p>
            <p className="mt-1 text-xs italic text-slate-500">{tip.disclaimer}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
