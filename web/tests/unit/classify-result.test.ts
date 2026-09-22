import { describe, expect, it } from "vitest";
import { classifyResult } from "@/lib/classify-result";
import { SAMPLE_ATTACKS } from "@/lib/sample-attacks";
import type { GenerateResponse } from "@/lib/types";

function body(flagged: boolean, code: string | null = null): GenerateResponse {
  return {
    output: null,
    guardrails: {
      injection: { flagged, matched_patterns: flagged ? ["ignore_instructions"] : [] },
      pii: { found: false, redacted: false, types: [] },
      schema_valid: true,
      retried: false,
      hallucination: null,
    },
    error: code ? { code, message: code } : null,
  };
}

describe("classifyResult", () => {
  it("flagged injection is blocked", () => {
    expect(classifyResult(400, body(true, "injection_detected"))).toBe("blocked");
  });

  it("200 unflagged is allowed", () => {
    expect(classifyResult(200, body(false))).toBe("allowed");
  });

  it("400 that is not an injection block is a failure, not 'Not blocked'", () => {
    // Regression: provider_credentials_missing (D-041) is also a 400.
    expect(classifyResult(400, body(false, "provider_credentials_missing"))).toBe("failed");
  });

  it("502/503/429 are failures", () => {
    expect(classifyResult(502, body(false, "provider_failed"))).toBe("failed");
    expect(classifyResult(503, body(false, "proxy_unreachable"))).toBe("failed");
    expect(classifyResult(429, body(false, "rate_limit_exceeded"))).toBe("failed");
  });

  it("every preset's cached fallback still renders as blocked", () => {
    for (const attack of SAMPLE_ATTACKS) {
      expect(classifyResult(attack.cachedResponse.status_code, attack.cachedResponse)).toBe("blocked");
    }
  });
});
