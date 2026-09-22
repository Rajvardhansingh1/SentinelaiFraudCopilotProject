import { Badge } from "@/components/ui/badge";
import type { TestStatusValue } from "@/lib/types";

// Phase 4: PASS/FAIL/ERROR/NOT_RUN/INCONCLUSIVE must never collapse into a
// single boolean — each gets its own color, no overlap.
const VARIANT_BY_STATUS: Record<TestStatusValue, "success" | "danger" | "warning" | "muted" | "default"> = {
  PASS: "success",
  FAIL: "danger",
  ERROR: "default",
  NOT_RUN: "muted",
  INCONCLUSIVE: "warning",
};

export function StatusBadge({ status }: { status: TestStatusValue }) {
  return <Badge variant={VARIANT_BY_STATUS[status]}>{status}</Badge>;
}
