"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CallLogRow } from "@/lib/types";
import { hallucinationScores } from "@/lib/dashboard-data";

export function HallucinationChart({ calls }: { calls: CallLogRow[] }) {
  const scores = hallucinationScores(calls);
  const data = scores.map((score, index) => ({ index: index + 1, score }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Hallucination scores</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-text-primary/60">No hallucination scores recorded yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="index" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 1]} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
              <Line type="monotone" dataKey="score" stroke="#2dd4bf" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
