"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { evaluateAgentAction, listAgentActions, listAgents, resolveAgentAction } from "@/lib/api";
import type { AgentActionLog, AgentDecision, AgentProfile } from "@/lib/types";

const DECISION_VARIANT: Record<AgentDecision, "success" | "danger" | "warning"> = {
  ALLOW: "success",
  DENY: "danger",
  REQUIRE_APPROVAL: "warning",
};

const inputClass = "rounded-md border border-bg-surface bg-bg-surface/40 px-2 py-1 text-sm text-text-primary";

export default function AgentSecurityPage() {
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [agentId, setAgentId] = useState("");
  const [actions, setActions] = useState<AgentActionLog[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tool, setTool] = useState("");
  const [action, setAction] = useState("");
  const [dataSource, setDataSource] = useState("");
  const [approver, setApprover] = useState("");
  const [lastDecision, setLastDecision] = useState<AgentActionLog | null>(null);

  async function loadActions(id: string) {
    const result = await listAgentActions(id || undefined);
    if (result.status === "ok") setActions(result.data);
    else setError(result.message);
  }

  useEffect(() => {
    listAgents().then((result) => {
      if (result.status === "error") {
        setError(result.message);
      } else {
        setAgents(result.data);
        if (result.data.length > 0) setAgentId(result.data[0].agent_id);
      }
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (agentId) loadActions(agentId);
  }, [agentId]);

  const agent = agents.find((a) => a.agent_id === agentId);

  async function handleEvaluate() {
    setError(null);
    const result = await evaluateAgentAction(agentId, { tool, action, data_source: dataSource });
    if (result.status === "error") return setError(result.message);
    setLastDecision(result.data);
    loadActions(agentId);
  }

  async function handleResolve(id: number, approve: boolean) {
    setError(null);
    const result = await resolveAgentAction(id, approve, approver);
    if (result.status === "error") setError(`${result.code}: ${result.message}`);
    loadActions(agentId);
  }

  if (loading) return <p className="text-text-primary/60">Loading agents...</p>;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Agent security</h1>
        <p className="text-sm text-text-primary/60">
          Tool/permission policy (ALLOW / DENY / REQUIRE_APPROVAL). SentinelAI only decides and records — it never
          executes a tool. Profiles come from server-side config (<code>proxy/agent_profiles.yaml</code>).
        </p>
      </div>

      {error && (
        <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>
      )}

      {agents.length === 0 && !error && (
        <p className="text-text-primary/60">No agent profiles configured. Add one to the server&apos;s agent profiles file.</p>
      )}

      {agent && (
        <>
          <div className="flex items-center gap-2">
            <select className={inputClass} value={agentId} onChange={(e) => setAgentId(e.target.value)}>
              {agents.map((a) => (
                <option key={a.agent_id} value={a.agent_id}>
                  {a.agent_id}
                </option>
              ))}
            </select>
            <span className="text-xs text-text-primary/50">model: {agent.model}</span>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Tools &amp; data sources</CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <p>Tools: {agent.tools.join(", ") || "none"}</p>
                <p>Data sources: {agent.data_sources.join(", ") || "none"}</p>
                <p className="text-xs text-text-primary/50">Anything not listed is denied (default deny).</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Rules</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-1">
                  {agent.rules.map((r) => (
                    <li key={`${r.tool}.${r.action}`} className="flex items-center gap-2">
                      <code>
                        {r.tool}.{r.action}
                      </code>
                      <Badge variant={DECISION_VARIANT[r.decision]}>{r.decision}</Badge>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Test a requested action</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center gap-2">
              <input className={inputClass} placeholder="tool" value={tool} onChange={(e) => setTool(e.target.value)} />
              <input className={inputClass} placeholder="action" value={action} onChange={(e) => setAction(e.target.value)} />
              <input className={inputClass} placeholder="data source (optional)" value={dataSource} onChange={(e) => setDataSource(e.target.value)} />
              <Button onClick={handleEvaluate} disabled={!tool || !action}>
                Evaluate
              </Button>
              {lastDecision && (
                <span className="flex items-center gap-2 text-sm">
                  <Badge variant={DECISION_VARIANT[lastDecision.decision]}>{lastDecision.decision}</Badge>
                  <span className="text-text-primary/60">{lastDecision.reason}</span>
                </span>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Decision log</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-3 flex items-center gap-2">
                <input className={inputClass} placeholder="Your name (approver)" value={approver} onChange={(e) => setApprover(e.target.value)} />
                <span className="text-xs text-text-primary/50">Required to approve/reject. An agent cannot approve itself.</span>
              </div>
              {actions.length === 0 ? (
                <p className="text-text-primary/50">No decisions recorded for this agent yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-text-primary/50">
                      <tr>
                        <th className="py-1 pr-3">When</th>
                        <th className="py-1 pr-3">Tool.action</th>
                        <th className="py-1 pr-3">Decision</th>
                        <th className="py-1 pr-3">Result</th>
                        <th className="py-1 pr-3">Approver</th>
                        <th className="py-1 pr-3" />
                      </tr>
                    </thead>
                    <tbody>
                      {actions.map((a) => (
                        <tr key={a.id} className="border-t border-bg-surface/60">
                          <td className="py-1 pr-3 text-text-primary/60">{new Date(a.created_at).toLocaleString()}</td>
                          <td className="py-1 pr-3">
                            <code>
                              {a.tool}.{a.action}
                            </code>
                            {a.data_source && <span className="text-text-primary/50"> @ {a.data_source}</span>}
                          </td>
                          <td className="py-1 pr-3">
                            <Badge variant={DECISION_VARIANT[a.decision]}>{a.decision}</Badge>
                          </td>
                          <td className="py-1 pr-3">{a.execution_result}</td>
                          <td className="py-1 pr-3">{a.approved_by ?? "—"}</td>
                          <td className="py-1 pr-3">
                            {a.execution_result === "pending_approval" && (
                              <span className="flex gap-1">
                                <Button variant="secondary" disabled={!approver.trim()} onClick={() => handleResolve(a.id, true)}>
                                  Approve
                                </Button>
                                <Button variant="ghost" disabled={!approver.trim()} onClick={() => handleResolve(a.id, false)}>
                                  Reject
                                </Button>
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
