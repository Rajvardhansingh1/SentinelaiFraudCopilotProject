"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FindingStatusBadge } from "@/components/findings/finding-status-badge";
import { getFinding, updateFindingStatus } from "@/lib/api";
import type { Finding, FindingStatusValue } from "@/lib/types";

const NEXT_STATUSES: FindingStatusValue[] = ["OPEN", "ACKNOWLEDGED", "RETEST_REQUIRED", "RESOLVED"];

export default function FindingDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);

  async function load() {
    setLoading(true);
    const f = await getFinding(id);
    setFinding(f);
    setLoading(false);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleStatusChange(status: FindingStatusValue) {
    setUpdating(true);
    const updated = await updateFindingStatus(id, status);
    if (updated) setFinding(updated);
    setUpdating(false);
  }

  if (loading) return <p className="text-text-primary/60">Loading...</p>;

  if (!finding) {
    return (
      <div className="space-y-3">
        <p className="text-text-primary/60">Finding not found.</p>
        <Link href="/findings" className="text-accent-teal underline underline-offset-2">
          Back to findings
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <Link href="/findings" className="text-sm text-accent-teal underline underline-offset-2">
          ← Findings
        </Link>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-2xl font-semibold text-text-primary">{finding.title}</h1>
          <FindingStatusBadge status={finding.status} />
        </div>
        <p className="mt-1 text-sm text-text-primary/60">{finding.description}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Finding</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-2">
          <div>Category: {finding.category}</div>
          <div>Severity: <Badge>{finding.severity}</Badge></div>
          <div>Affected target: {finding.affected_target}</div>
          <div>Provider / model: {finding.provider} / {finding.model}</div>
          <div>Opened: {new Date(finding.created_at).toLocaleString()}</div>
          <div>Updated: {new Date(finding.updated_at).toLocaleString()}</div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Remediation guidance</CardTitle>
        </CardHeader>
        <CardContent>{finding.remediation}</CardContent>
      </Card>

      <div className="flex gap-2">
        {NEXT_STATUSES.map((s) => (
          <Button
            key={s}
            variant={s === finding.status ? "primary" : "secondary"}
            disabled={updating || s === finding.status}
            onClick={() => handleStatusChange(s)}
          >
            {s.replace("_", " ")}
          </Button>
        ))}
      </div>

      <Tabs defaultValue="test">
        <TabsList>
          <TabsTrigger value="test">Test</TabsTrigger>
          <TabsTrigger value="attack">Attack</TabsTrigger>
          <TabsTrigger value="response">Model response</TabsTrigger>
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
          <TabsTrigger value="reproduce">Reproduce</TabsTrigger>
        </TabsList>

        <TabsContent value="test">
          <p>Test ID: <code>{finding.test_id}</code></p>
          <p>Category: {finding.category}</p>
        </TabsContent>

        <TabsContent value="attack">
          <pre className="whitespace-pre-wrap rounded-md bg-bg-surface p-3 text-xs">{finding.evidence.raw_input}</pre>
        </TabsContent>

        <TabsContent value="response">
          <pre className="whitespace-pre-wrap rounded-md bg-bg-surface p-3 text-xs">
            {JSON.stringify(finding.evidence.raw_output, null, 2)}
          </pre>
        </TabsContent>

        <TabsContent value="evidence">
          <pre className="whitespace-pre-wrap rounded-md bg-bg-surface p-3 text-xs">
            {JSON.stringify(finding.evidence, null, 2)}
          </pre>
        </TabsContent>

        <TabsContent value="reproduce">
          <pre className="whitespace-pre-wrap rounded-md bg-bg-surface p-3 text-xs">
            {JSON.stringify(finding.reproduction, null, 2)}
          </pre>
        </TabsContent>
      </Tabs>
    </div>
  );
}
