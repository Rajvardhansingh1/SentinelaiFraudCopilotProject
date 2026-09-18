"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { recordReviewDecision } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { PolicyVerdict } from "@/lib/types";

interface Props {
  receiptRef: string;
  policy: PolicyVerdict | null;
  confidence: number;
  hallucinationPct: number;
}

export function HumanDecisionPanel({ receiptRef, policy, confidence, hallucinationPct }: Props) {
  const { sessionId } = useSession();
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function decide(decision: "approved" | "rejected") {
    setSubmitting(true);
    setResult(null);
    try {
      const systemVerdict = policy?.compliant ?? true ? "compliant" : "non_compliant";
      const { status, body } = await recordReviewDecision({
        session_id: sessionId,
        receipt_ref: receiptRef,
        system_verdict: systemVerdict,
        confidence,
        hallucination_pct: hallucinationPct,
        human_decision: decision,
        reviewer_notes: notes,
      });
      if (status === 200 || status === 201) {
        setResult({ ok: true, message: `Recorded: ${decision}` });
      } else {
        const errMsg = "error" in body ? body.error.message : "Failed to record decision.";
        setResult({ ok: false, message: errMsg });
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-3" data-testid="human-decision-panel">
      <h3 className="text-sm font-semibold">Human decision</h3>
      <Textarea
        placeholder="Reviewer notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={3}
        data-testid="reviewer-notes"
      />
      <div className="flex gap-3">
        <Button onClick={() => decide("approved")} disabled={submitting} data-testid="approve-button">
          Approve
        </Button>
        <Button
          variant="secondary"
          onClick={() => decide("rejected")}
          disabled={submitting}
          data-testid="reject-button"
        >
          Reject
        </Button>
      </div>
      {result && (
        <p
          className={result.ok ? "text-sm text-emerald-400" : "text-sm text-red-400"}
          data-testid="decision-toast"
        >
          {result.message}
        </p>
      )}
    </div>
  );
}
