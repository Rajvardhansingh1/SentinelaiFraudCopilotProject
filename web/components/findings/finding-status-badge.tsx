import { Badge } from "@/components/ui/badge";
import type { FindingStatusValue } from "@/lib/types";

const VARIANT_BY_STATUS: Record<FindingStatusValue, "success" | "danger" | "warning" | "default"> = {
  OPEN: "danger",
  ACKNOWLEDGED: "warning",
  RETEST_REQUIRED: "default",
  RESOLVED: "success",
};

export function FindingStatusBadge({ status }: { status: FindingStatusValue }) {
  return <Badge variant={VARIANT_BY_STATUS[status]}>{status.replace("_", " ")}</Badge>;
}
