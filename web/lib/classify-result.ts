import type { GenerateResponse } from "./types";

export type PlaygroundOutcome = "blocked" | "allowed" | "failed";

// Only a flagged injection is a "block". Any other non-200 (e.g. 400
// provider_credentials_missing, 502, 503) is a failure — never "Not blocked".
export function classifyResult(status: number, body: GenerateResponse): PlaygroundOutcome {
  if (body.guardrails?.injection?.flagged === true) return "blocked";
  if (status !== 200) return "failed";
  return "allowed";
}
