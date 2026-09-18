// TypeScript mirror of proxy/schemas.py — keep in sync manually (D-015 contract).

export type Role = "system" | "user" | "assistant";

export interface Message {
  role: Role;
  content: string;
}

export type Operation = "extract" | "policy_check" | "report" | "playground";

export interface GenerateRequest {
  session_id: string;
  operation: Operation;
  messages: Message[];
  schema_name?: string | null;
  grounding_context?: string | null;
}

export interface InjectionResult {
  flagged: boolean;
  matched_patterns: string[];
}

export interface PIIResult {
  found: boolean;
  redacted: boolean;
  types: string[];
}

export interface HallucinationResult {
  score: number;
  mode: "grounded" | "ungrounded";
}

export interface Guardrails {
  injection: InjectionResult;
  pii: PIIResult;
  schema_valid: boolean;
  retried: boolean;
  hallucination: HallucinationResult | null;
}

export interface Usage {
  provider: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
  cost_estimate_usd: number;
}

export interface ErrorDetail {
  code: string;
  message: string;
}

export interface GenerateResponse {
  output: unknown;
  guardrails: Guardrails;
  usage?: Usage;
  error?: ErrorDetail | null;
}

// Envelope api.ts always returns — never throws (D-031/D-019).
export interface ProxyResult {
  status: number;
  body: GenerateResponse;
}

// Mirrors agents/api.py GET /v1/calls row shape (raw CallLog rows).
export interface CallLogRow {
  id: number;
  session_id: string;
  operation: string;
  provider: string;
  model: string;
  latency_ms: number;
  tokens_in: number;
  tokens_out: number;
  cost_estimate_usd: number;
  guardrails: Guardrails | null;
  error_code: string | null;
  created_at: string;
}

// --- Review page / agents/api.py mirrors ---

export interface ExtractedFields {
  vendor: string | null;
  date: string | null;
  line_items: string[];
  total: number | null;
}

export interface ForensicsResult {
  ela_score: number;
  exif_consistent: boolean | null;
  exif_flags: string[];
  tamper_likelihood: "low" | "medium" | "high";
}

export interface PolicyVerdict {
  triggered_rules: string[];
  compliant: boolean;
}

export interface PipelineError {
  node: string;
  code: string;
  message: string;
}

export interface AnalyzeReceiptResponse {
  extracted_fields: ExtractedFields | null;
  // Populated when the proxy's injection detector blocks the extraction call
  // (e.g. adversarial text embedded in the scanned receipt) — same Guardrails
  // shape /v1/generate returns, same detector the Playground page exercises.
  extraction_guardrails: Guardrails | null;
  forensics_result: ForensicsResult | null;
  policy_verdict: PolicyVerdict | null;
  report_text: string | null;
  report_guardrails: Guardrails | null;
  errors: PipelineError[];
}

// Never-throw envelope for analyzeReceipt (same D-031 pattern as ProxyResult).
export interface AnalyzeResult {
  status: number;
  body: AnalyzeReceiptResponse;
}

export interface ReviewDecisionPayload {
  session_id: string;
  receipt_ref: string;
  system_verdict: string;
  confidence: number;
  hallucination_pct: number;
  human_decision: "approved" | "rejected";
  reviewer_notes: string;
}

export interface ReviewDecision extends ReviewDecisionPayload {
  id: number;
  decided_at: string;
}

// Never-throw envelope for recordReviewDecision.
export interface ReviewDecisionResult {
  status: number;
  body: ReviewDecision | { error: { code: string; message: string } };
}
