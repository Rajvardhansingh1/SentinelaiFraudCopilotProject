"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/security/status-badge";
import { createBaseline, getRegressionReport, listBaselines } from "@/lib/api";
import type { Baseline, RegressionEntry, RegressionReport } from "@/lib/types";

function EntryList({ entries, emptyText }: { entries: RegressionEntry[]; emptyText: string }) {
  if (entries.length === 0) return <p className="text-text-primary/50">{emptyText}</p>;
  return (
    <ul className="space-y-1 text-sm">
      {entries.map((e) => (
        <li key={e.test_id} className="flex items-center gap-2">
          <span className="text-text-primary/80">{e.test_id}</span>
          <span className="text-text-primary/40">({e.category})</span>
          <StatusBadge status={e.baseline_status ?? "NOT_RUN"} />
          <span className="text-text-primary/40">→</span>
          <StatusBadge status={e.current_status} />
        </li>
      ))}
    </ul>
  );
}

export default function RegressionPage() {
  const [baselines, setBaselines] = useState<Baseline[]>([]);
  const [report, setReport] = useState<RegressionReport | null>(null);
  const [errorState, setErrorState] = useState<{ code: string; message: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

  async function loadReport() {
    setLoading(true);
    setErrorState(null);
    const result = await getRegressionReport();
    if (result.status === "error") {
      setErrorState({ code: result.code, message: result.message });
      setReport(null);
    } else {
      setReport(result.data);
    }
    setLoading(false);
  }

  async function loadBaselines() {
    setBaselines(await listBaselines());
  }

  useEffect(() => {
    loadBaselines();
    loadReport();
  }, []);

  async function handleCreateBaseline() {
    setCreating(true);
    const result = await createBaseline(newName || `baseline ${new Date().toLocaleString()}`);
    setCreating(false);
    if (result.status === "ok") {
      setNewName("");
      await loadBaselines();
      await loadReport();
    } else {
      setErrorState({ code: result.code, message: result.message });
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Regression</h1>
        <p className="text-sm text-text-primary/60">
          Compares the latest recorded test run against a pinned baseline. No single security score — every
          individual test result stays visible below.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Baseline name (optional)"
          className="rounded-md border border-bg-surface bg-bg-surface/40 px-3 py-2 text-sm text-text-primary"
        />
        <Button onClick={handleCreateBaseline} disabled={creating}>
          {creating ? "Creating..." : "Create baseline from latest run"}
        </Button>
        <Button variant="secondary" onClick={loadReport} disabled={loading}>
          {loading ? "Loading..." : "Refresh report"}
        </Button>
      </div>

      {baselines.length > 0 && (
        <p className="text-xs text-text-primary/50">
          {baselines.length} baseline{baselines.length === 1 ? "" : "s"} recorded. Report compares against the most
          recent one unless the API is called with a specific <code>baseline_id</code>.
        </p>
      )}

      {loading && <p className="text-text-primary/60">Loading regression report...</p>}

      {!loading && errorState?.code === "baseline_not_found" && (
        <div className="rounded-md border border-bg-surface bg-bg-surface/40 px-4 py-3 text-sm text-text-primary/60">
          No baseline exists yet. Run tests (Findings page or the button above) to record a run, then create a
          baseline.
        </div>
      )}

      {!loading && errorState?.code === "no_run_to_compare" && (
        <div className="rounded-md border border-bg-surface bg-bg-surface/40 px-4 py-3 text-sm text-text-primary/60">
          A baseline exists, but no test run has been recorded since. Run tests to compare against it.
        </div>
      )}

      {!loading && errorState && !["baseline_not_found", "no_run_to_compare"].includes(errorState.code) && (
        <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Could not load the regression report: {errorState.message}
        </div>
      )}

      {!loading && report && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Card>
              <CardHeader>
                <CardTitle>Regressions</CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-bold text-red-400">{report.regressions.length}</CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>New failures</CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-bold text-amber-400">{report.new_failures.length}</CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Fixed</CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-bold text-emerald-400">{report.fixed.length}</CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Unchanged</CardTitle>
              </CardHeader>
              <CardContent className="text-2xl font-bold text-text-primary/70">{report.unchanged.length}</CardContent>
            </Card>
          </div>

          {report.provider_config_changed && (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
              Model/provider configuration changed since the baseline — results may differ for reasons unrelated to
              guardrail regressions.
            </div>
          )}

          {(report.added_tests.length > 0 || report.removed_tests.length > 0) && (
            <div className="flex gap-4 text-sm text-text-primary/60">
              {report.added_tests.length > 0 && <span>+{report.added_tests.length} tests added</span>}
              {report.removed_tests.length > 0 && <span>-{report.removed_tests.length} tests removed</span>}
            </div>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Regressions (previously passing, now failing)</CardTitle>
            </CardHeader>
            <CardContent>
              <EntryList entries={report.regressions} emptyText="No regressions." />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Fixed (previously failing, now passing)</CardTitle>
            </CardHeader>
            <CardContent>
              <EntryList entries={report.fixed} emptyText="Nothing newly fixed." />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Findings since baseline</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <p className="mb-1 font-medium text-text-primary/80">New</p>
                {report.findings.new_findings.length === 0 ? (
                  <p className="text-text-primary/50">None.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {report.findings.new_findings.map((f) => (
                      <li key={f.id}>
                        <Badge variant="danger">{f.severity}</Badge> {f.title}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div>
                <p className="mb-1 font-medium text-text-primary/80">Resolved</p>
                {report.findings.resolved_findings.length === 0 ? (
                  <p className="text-text-primary/50">None.</p>
                ) : (
                  <ul className="space-y-1 text-sm">
                    {report.findings.resolved_findings.map((f) => (
                      <li key={f.id}>
                        <Badge variant="success">{f.severity}</Badge> {f.title}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>All test results (baseline → current)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-text-primary/50">
                    <tr>
                      <th className="py-1 pr-3">Test</th>
                      <th className="py-1 pr-3">Category</th>
                      <th className="py-1 pr-3">Baseline</th>
                      <th className="py-1 pr-3">Current</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.per_test.map((e) => (
                      <tr key={e.test_id} className="border-t border-bg-surface/60">
                        <td className="py-1 pr-3">{e.test_id}</td>
                        <td className="py-1 pr-3 text-text-primary/60">{e.category}</td>
                        <td className="py-1 pr-3">{e.baseline_status ? <StatusBadge status={e.baseline_status} /> : <span className="text-text-primary/40">—</span>}</td>
                        <td className="py-1 pr-3">
                          <StatusBadge status={e.current_status} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
