"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const PROXY_BASE_URL = process.env.NEXT_PUBLIC_PROXY_BASE_URL ?? "http://localhost:8000";
type ReportType = "executive" | "technical";

async function fetchMarkdown(reportType: ReportType): Promise<{ status: "ok"; text: string } | { status: "error"; message: string }> {
  try {
    const resp = await fetch(`${PROXY_BASE_URL}/v1/reports/${reportType}?format=md`);
    if (!resp.ok) return { status: "error", message: `SentinelAI returned ${resp.status}` };
    return { status: "ok", text: await resp.text() };
  } catch (err) {
    return { status: "error", message: err instanceof Error ? err.message : String(err) };
  }
}

function ReportPanel({ reportType, title }: { reportType: ReportType; title: string }) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    const result = await fetchMarkdown(reportType);
    if (result.status === "error") setError(result.message);
    else setText(result.text);
    setLoading(false);
  }

  function download() {
    if (!text) return;
    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sentinelai-${reportType}-report.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex gap-2">
          <Button onClick={load} disabled={loading}>
            {loading ? "Generating..." : text ? "Regenerate" : "Generate"}
          </Button>
          {text && (
            <Button variant="secondary" onClick={download}>
              Download .md
            </Button>
          )}
        </div>
        {error && (
          <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">
            Could not generate report: {error}
          </div>
        )}
        {text && (
          <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-md bg-bg-surface p-3 text-xs">{text}</pre>
        )}
      </CardContent>
    </Card>
  );
}

export default function ReportsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Security reports</h1>
        <p className="text-sm text-text-primary/60">
          Generated only from stored test runs, findings, baselines, and events — nothing here is fabricated.
          Credentials are scrubbed before a report is returned.
        </p>
      </div>
      <ReportPanel reportType="executive" title="Executive summary" />
      <ReportPanel reportType="technical" title="Technical report" />
    </div>
  );
}
