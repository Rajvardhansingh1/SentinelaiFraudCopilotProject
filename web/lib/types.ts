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

// --- proxy/engine (Phase 3/4 security testing engine) mirrors ---

export type TestStatusValue = "PASS" | "FAIL" | "ERROR" | "NOT_RUN" | "INCONCLUSIVE";
export type Severity = "low" | "medium" | "high" | "critical";

export interface RawExecution {
  raw_input: string;
  raw_output: unknown;
  provider: string;
  model: string;
  status_code: number | null;
  extra: Record<string, unknown>;
}

export interface SecurityTestResult {
  test_id: string;
  name: string;
  category: string;
  severity: Severity;
  status: TestStatusValue;
  detail: string;
  evidence: RawExecution;
  executed_at: string;
  reproduction: Record<string, unknown>;
}

// --- proxy/findings.py (Phase 5 findings subsystem) mirrors ---

export type FindingStatusValue = "OPEN" | "ACKNOWLEDGED" | "RESOLVED" | "RETEST_REQUIRED";

// Mirrors proxy/remediation.py::Remediation (Phase 5, D-057). Structured so
// the UI can render Observed/Analysis/Recommendation as distinct sections
// (spec §23) instead of one opaque string.
export interface Remediation {
  observed: string;
  analysis: string;
  security_impact: string;
  expected_fix: string;
  why_it_addresses: string;
  components_to_review: string[];
  additional_controls: string[];
  verification_guidance: string;
  confidence: "HIGH CONFIDENCE" | "LIKELY" | "REQUIRES INVESTIGATION" | "INSUFFICIENT EVIDENCE";
  project_context: string[];
}

export interface Finding {
  id: number;
  project_id: number | null;
  test_id: string;
  category: string;
  severity: Severity;
  title: string;
  description: string;
  affected_target: string;
  evidence: {
    raw_input: string;
    raw_output: unknown;
    provider: string;
    model: string;
    status_code: number | null;
  };
  reproduction: Record<string, unknown>;
  provider: string;
  model: string;
  status: FindingStatusValue;
  remediation: Remediation;
  created_at: string;
  updated_at: string;
}

export interface FindingsSyncResult {
  results: SecurityTestResult[];
  findings_created: Finding[];
}

// --- proxy/dashboard.py (Phase 6 security dashboard) mirror ---

export interface RecentActivityRow {
  test_id: string;
  category: string;
  severity: Severity;
  status: TestStatusValue;
  provider: string;
  model: string;
  executed_at: string;
}

export interface AffectedModel {
  provider: string;
  model: string;
}

export type SecurityDashboardResult =
  | { status: "ok"; data: SecurityDashboardSummary }
  | { status: "error"; message: string };

// --- proxy/agent_policy.py + agent_actions.py (Phase 9 agent security) mirror ---

export type AgentDecision = "ALLOW" | "DENY" | "REQUIRE_APPROVAL";

export interface AgentProfile {
  agent_id: string;
  model: string;
  tools: string[];
  data_sources: string[];
  rules: { tool: string; action: string; decision: AgentDecision }[];
}

export interface AgentActionLog {
  id: number;
  agent_id: string;
  tool: string;
  action: string;
  data_source: string | null;
  decision: AgentDecision;
  reason: string;
  execution_result: string;
  approved_by: string | null;
  created_at: string;
  updated_at: string;
}

export type ApiResult<T> = { status: "ok"; data: T } | { status: "error"; code: string; message: string };

// --- proxy/events.py (Phase 11 monitoring) mirror ---

export type EventSeverity = "info" | "low" | "medium" | "high" | "critical";

export interface SecurityEvent {
  id: number;
  event_type: string;
  severity: EventSeverity;
  category: string;
  source: string;
  application: string | null;
  model: string | null;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface EventsConfig {
  enabled: boolean;
  retention_days: number;
  min_severity: EventSeverity;
  gateway_record_events: boolean;
  event_types: string[];
  severities: EventSeverity[];
}

export interface EventFilters {
  event_type?: string;
  min_severity?: string;
  category?: string;
  application?: string;
  model?: string;
  since?: string;
}

// --- proxy/regression.py (Phase 7 regression testing) mirror ---

export interface Baseline {
  id: number;
  name: string;
  run_id: string;
  created_at: string;
}

export interface RegressionEntry {
  test_id: string;
  category: string;
  baseline_status: TestStatusValue | null;
  current_status: TestStatusValue;
  baseline_severity: Severity | null;
  current_severity: Severity;
}

export interface FindingSummary {
  id: number;
  test_id: string;
  severity: Severity;
  title: string;
}

export interface RegressionReport {
  regressions: RegressionEntry[];
  new_failures: RegressionEntry[];
  fixed: RegressionEntry[];
  unchanged: RegressionEntry[];
  other_changes: RegressionEntry[];
  severity_changes: RegressionEntry[];
  added_tests: string[];
  removed_tests: string[];
  provider_config_changed: boolean;
  baseline_config: AffectedModel[];
  current_config: AffectedModel[];
  per_test: RegressionEntry[];
  baseline: Baseline;
  current_run_id: string;
  findings: {
    new_findings: FindingSummary[];
    resolved_findings: FindingSummary[];
  };
}

export interface SecurityDashboardSummary {
  last_run_at: string | null;
  total_tests: number;
  passed: number;
  failed: number;
  errors: number;
  not_run: number;
  inconclusive: number;
  open_findings: number;
  severity_distribution: Partial<Record<Severity, number>>;
  recent_activity: RecentActivityRow[];
  affected_models: AffectedModel[];
}
