"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authHeaders, getActiveProjectId } from "@/lib/auth";

const PROXY_BASE_URL = process.env.NEXT_PUBLIC_PROXY_BASE_URL ?? "http://localhost:8000";
type ReportType = "executive" | "technical";
type Format = "md" | "csv";

async function fetchReport(
  reportType: ReportType,
  format: Format
): Promise<{ status: "ok"; text: string } | { status: "error"; message: string }> {
  const projectId = getActiveProjectId();
  if (projectId === null) return { status: "error", message: "No active project selected." };
  try {
    const resp = await fetch(
      `${PROXY_BASE_URL}/v1/reports/${reportType}?format=${format}&project_id=${projectId}`,
      { headers: authHeaders() }
    );
    if (!resp.ok) return { status: "error", message: `SentinelAI returned ${resp.status}` };
    return { status: "ok", text: await resp.text() };
  } catch (err) {
    return { status: "error", message: err instanceof Error ? err.message : String(err) };
  }
}

function ReportPanel({ reportType, title, csv }: { reportType: ReportType; title: string; csv: boolean }) {
  const [text, setText] = useState<string | null>(null);
  const [format, setFormat] = useState<Format>("md");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load(fmt: Format) {
    setLoading(true);
    setError(null);
    const result = await fetchReport(reportType, fmt);
    if (result.status === "error") setError(result.message);
    else {
      setText(result.text);
      setFormat(fmt);
    }
    setLoading(false);
  }

  function download() {
    if (!text) return;
    const mime = format === "csv" ? "text/csv" : "text/markdown";
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sentinelai-${reportType}-report.${format}`;
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
          <Button onClick={() => load("md")} disabled={loading}>
            {loading ? "Generating..." : text ? "Regenerate" : "Generate"}
          </Button>
          {csv && (
            <Button variant="secondary" onClick={() => load("csv")} disabled={loading}>
              Generate CSV
            </Button>
          )}
          {text && (
            <Button variant="secondary" onClick={download}>
              Download .{format}
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
          Generated only from stored test runs, findings, baselines, and events for the active project — nothing
          here is fabricated. Credentials are scrubbed before a report is returned.
        </p>
      </div>
      <ReportPanel reportType="executive" title="Executive summary" csv={false} />
      <ReportPanel reportType="technical" title="Technical report" csv />
    </div>
  );
}
