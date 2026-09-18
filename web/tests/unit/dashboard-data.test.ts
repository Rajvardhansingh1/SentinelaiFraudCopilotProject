import { describe, it, expect } from "vitest";
import {
  costSummary,
  guardrailCatchCounts,
  hallucinationScores,
  latencySummary,
  trafficByOperation,
} from "@/lib/dashboard-data";
import type { CallLogRow } from "@/lib/types";

// Mirrors tests/test_eval_dashboard.py's fixtures/cases so the TS port has real parity.
function fakeCall(overrides: Partial<CallLogRow> = {}): CallLogRow {
  return {
    id: 1,
    session_id: "s1",
    operation: "x",
    provider: "p",
    model: "m",
    latency_ms: 10,
    tokens_in: 0,
    tokens_out: 0,
    cost_estimate_usd: 0,
    guardrails: {} as CallLogRow["guardrails"],
    error_code: null,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("trafficByOperation", () => {
  it("counts calls per operation", () => {
    const calls = [
      fakeCall({ operation: "playground" }),
      fakeCall({ operation: "playground" }),
      fakeCall({ operation: "extract" }),
    ];
    expect(trafficByOperation(calls)).toEqual({ playground: 2, extract: 1 });
  });
});

describe("guardrailCatchCounts", () => {
  it("counts injection and pii flags", () => {
    const calls = [
      fakeCall({ guardrails: { injection: { flagged: true }, pii: { found: false } } as never }),
      fakeCall({ guardrails: { injection: { flagged: false }, pii: { found: true } } as never }),
    ];
    expect(guardrailCatchCounts(calls)).toEqual({ injection: 1, pii: 1 });
  });
});

describe("hallucinationScores", () => {
  it("skips calls with no hallucination guardrail", () => {
    const calls = [
      fakeCall({ guardrails: { hallucination: { score: 0.3 } } as never }),
      fakeCall({ guardrails: {} as never }),
    ];
    expect(hallucinationScores(calls)).toEqual([0.3]);
  });
});

describe("costSummary", () => {
  it("sums total and averages per call", () => {
    const calls = [fakeCall({ cost_estimate_usd: 0.01 }), fakeCall({ cost_estimate_usd: 0.03 })];
    const summary = costSummary(calls);
    expect(summary.total_usd).toBeCloseTo(0.04);
    expect(summary.avg_usd).toBeCloseTo(0.02);
  });

  it("returns zeros for an empty list", () => {
    expect(costSummary([])).toEqual({ total_usd: 0, avg_usd: 0 });
  });
});

describe("latencySummary", () => {
  it("averages latency across calls", () => {
    const calls = [fakeCall({ latency_ms: 100 }), fakeCall({ latency_ms: 200 })];
    expect(latencySummary(calls).avg_ms).toBe(150);
  });

  it("returns zeros for an empty list", () => {
    expect(latencySummary([])).toEqual({ avg_ms: 0, p95_ms: 0 });
  });
});
