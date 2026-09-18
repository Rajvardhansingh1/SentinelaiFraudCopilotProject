"use client";

import { useState } from "react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ReceiptPicker } from "@/components/review/receipt-picker";
import { VerdictCard } from "@/components/review/verdict-card";
import { HumanDecisionPanel } from "@/components/review/human-decision-panel";
import { ExtractionCard } from "@/components/review/evidence/extraction-card";
import { ForensicsCard } from "@/components/review/evidence/forensics-card";
import { PolicyCard } from "@/components/review/evidence/policy-card";
import { ReportCard } from "@/components/review/evidence/report-card";
import { analyzeReceipt } from "@/lib/api";
import { useSession } from "@/lib/session";
import type { AnalyzeReceiptResponse } from "@/lib/types";

export default function ReviewPage() {
  const { sessionId } = useSession();
  const [loading, setLoading] = useState(false);
  const [receiptRef, setReceiptRef] = useState<string>("");
  const [result, setResult] = useState<AnalyzeReceiptResponse | null>(null);

  async function handleRun(file: File, label: string) {
    if (!sessionId) return;
    setLoading(true);
    setReceiptRef(label);
    try {
      const { body } = await analyzeReceipt(sessionId, file);
      setResult(body);
    } finally {
      setLoading(false);
    }
  }

  // D-026: confidence = 1 - hallucination score.
  const hallucinationPct = result?.report_guardrails?.hallucination?.score ?? 0;
  const confidence = 1 - hallucinationPct;

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Receipt Review</h1>
        <p className="text-sm text-slate-400">
          Pick a sample or upload a receipt to run the extraction, forensics, and policy pipeline.
        </p>
      </div>

      <ReceiptPicker onRun={handleRun} loading={loading} />

      {result && (
        <>
          {result.errors.length > 0 && (
            <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
              {result.errors.map((e) => e.message).join(" ")}
            </div>
          )}

          <VerdictCard
            policy={result.policy_verdict}
            forensics={result.forensics_result}
            extractionGuardrails={result.extraction_guardrails}
            confidence={confidence}
            hallucinationPct={hallucinationPct}
          >
            <HumanDecisionPanel
              receiptRef={receiptRef}
              policy={result.policy_verdict}
              confidence={confidence}
              hallucinationPct={hallucinationPct}
            />
          </VerdictCard>

          <Collapsible>
            <CollapsibleTrigger className="text-sm text-accent-teal underline underline-offset-2">
              Show evidence (extraction, forensics, policy, report)
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-3">
              <Tabs defaultValue="extraction">
                <TabsList>
                  <TabsTrigger value="extraction">Extraction</TabsTrigger>
                  <TabsTrigger value="forensics">Forensics</TabsTrigger>
                  <TabsTrigger value="policy">Policy</TabsTrigger>
                  <TabsTrigger value="report">Report</TabsTrigger>
                </TabsList>
                <TabsContent value="extraction">
                  <ExtractionCard fields={result.extracted_fields} />
                </TabsContent>
                <TabsContent value="forensics">
                  <ForensicsCard forensics={result.forensics_result} />
                </TabsContent>
                <TabsContent value="policy">
                  <PolicyCard policy={result.policy_verdict} />
                </TabsContent>
                <TabsContent value="report">
                  <ReportCard reportText={result.report_text} />
                </TabsContent>
              </Tabs>
            </CollapsibleContent>
          </Collapsible>
        </>
      )}
    </div>
  );
}
