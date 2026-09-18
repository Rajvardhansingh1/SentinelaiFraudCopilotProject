// Ported near-verbatim from frontend/lib/dashboard_data.py's 5 aggregation
// functions (same math, same field names). Operates client-side on the raw
// rows GET /v1/calls returns — the endpoint stays dumb per REACT_FRONTEND_PLAN.md §10.
import type { CallLogRow } from "./types";

export function trafficByOperation(calls: CallLogRow[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const c of calls) {
    counts[c.operation] = (counts[c.operation] ?? 0) + 1;
  }
  return counts;
}

export function guardrailCatchCounts(calls: CallLogRow[]): { injection: number; pii: number } {
  let injection = 0;
  let pii = 0;
  for (const c of calls) {
    const g: Partial<CallLogRow["guardrails"]> & object =
      c.guardrails ?? { injection: { flagged: false, matched_patterns: [] }, pii: { found: false, redacted: false, types: [] } };
    if (g.injection?.flagged) injection += 1;
    if (g.pii?.found) pii += 1;
  }
  return { injection, pii };
}

export function hallucinationScores(calls: CallLogRow[]): number[] {
  const scores: number[] = [];
  for (const c of calls) {
    const h = c.guardrails?.hallucination;
    if (h) scores.push(h.score);
  }
  return scores;
}

export function costSummary(calls: CallLogRow[]): { total_usd: number; avg_usd: number } {
  if (calls.length === 0) return { total_usd: 0, avg_usd: 0 };
  const total = calls.reduce((sum, c) => sum + c.cost_estimate_usd, 0);
  return { total_usd: total, avg_usd: total / calls.length };
}

export function latencySummary(calls: CallLogRow[]): { avg_ms: number; p95_ms: number } {
  const latencies = calls.map((c) => c.latency_ms).sort((a, b) => a - b);
  if (latencies.length === 0) return { avg_ms: 0, p95_ms: 0 };
  const avg = latencies.reduce((sum, v) => sum + v, 0) / latencies.length;
  const p95 = latencies.length > 1 ? latencies[Math.floor(latencies.length * 0.95)] : latencies[0];
  return { avg_ms: avg, p95_ms: p95 };
}
