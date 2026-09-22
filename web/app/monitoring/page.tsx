"use client";

import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getEventsConfig, listEvents } from "@/lib/api";
import type { EventFilters, EventsConfig, SecurityEvent } from "@/lib/types";

const SEVERITY_VARIANT: Record<string, "danger" | "warning" | "default" | "muted"> = {
  critical: "danger",
  high: "danger",
  medium: "warning",
  low: "default",
  info: "muted",
};

const WINDOWS: { label: string; hours: number | null }[] = [
  { label: "Last hour", hours: 1 },
  { label: "Last 24h", hours: 24 },
  { label: "Last 7 days", hours: 24 * 7 },
  { label: "All retained", hours: null },
];

const inputClass = "rounded-md border border-bg-surface bg-bg-surface/40 px-2 py-1 text-sm text-text-primary";

export default function MonitoringPage() {
  const [config, setConfig] = useState<EventsConfig | null>(null);
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [windowHours, setWindowHours] = useState<number | null>(24);
  const [filters, setFilters] = useState<EventFilters>({});

  async function load() {
    setLoading(true);
    const since = windowHours ? new Date(Date.now() - windowHours * 3600_000).toISOString() : undefined;
    const result = await listEvents({ ...filters, since });
    if (result.status === "error") {
      setError(result.message);
      setEvents([]);
    } else {
      setError(null);
      setEvents(result.data);
    }
    setLoading(false);
  }

  useEffect(() => {
    getEventsConfig().then(setConfig);
  }, []);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [windowHours, filters]);

  const set = (key: keyof EventFilters) => (value: string) => setFilters((f) => ({ ...f, [key]: value || undefined }));

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Monitoring</h1>
          <p className="text-sm text-text-primary/60">
            Security events — attack attempts, blocks, policy violations, new findings, regressions, suspicious tool
            activity. Events are observations, not vulnerabilities; see Findings for those.
          </p>
          {config && (
            <p className="mt-1 text-xs text-text-primary/50">
              Recording {config.enabled ? "on" : "off"} · retention{" "}
              {config.retention_days > 0 ? `${config.retention_days} days` : "forever"} · min severity{" "}
              {config.min_severity} · gateway events {config.gateway_record_events ? "on" : "off"}
            </p>
          )}
        </div>
        <Button onClick={load} disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <select className={inputClass} value={windowHours ?? ""} onChange={(e) => setWindowHours(e.target.value ? Number(e.target.value) : null)}>
          {WINDOWS.map((w) => (
            <option key={w.label} value={w.hours ?? ""}>
              {w.label}
            </option>
          ))}
        </select>
        <select className={inputClass} value={filters.event_type ?? ""} onChange={(e) => set("event_type")(e.target.value)}>
          <option value="">All event types</option>
          {(config?.event_types ?? []).map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select className={inputClass} value={filters.min_severity ?? ""} onChange={(e) => set("min_severity")(e.target.value)}>
          <option value="">Any severity</option>
          {(config?.severities ?? []).map((s) => (
            <option key={s} value={s}>
              ≥ {s}
            </option>
          ))}
        </select>
        <input className={inputClass} placeholder="Category" onBlur={(e) => set("category")(e.target.value.trim())} />
        <input className={inputClass} placeholder="Application" onBlur={(e) => set("application")(e.target.value.trim())} />
        <input className={inputClass} placeholder="Model" onBlur={(e) => set("model")(e.target.value.trim())} />
      </div>

      {error && (
        <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Could not load events: {error}
        </div>
      )}

      {!loading && !error && events.length === 0 && (
        <p className="text-text-primary/60">No events match these filters.</p>
      )}

      {events.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="bg-bg-surface/60 text-text-primary/60">
              <tr>
                <th className="px-3 py-2">When</th>
                <th className="px-3 py-2">Severity</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Application</th>
                <th className="px-3 py-2">Model</th>
                <th className="px-3 py-2">Summary</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id} className="border-t border-bg-surface/60">
                  <td className="px-3 py-2 text-text-primary/60">{new Date(e.created_at).toLocaleString()}</td>
                  <td className="px-3 py-2">
                    <Badge variant={SEVERITY_VARIANT[e.severity] ?? "muted"}>{e.severity}</Badge>
                  </td>
                  <td className="px-3 py-2">{e.event_type}</td>
                  <td className="px-3 py-2 text-text-primary/80">{e.category}</td>
                  <td className="px-3 py-2 text-text-primary/80">{e.application ?? "—"}</td>
                  <td className="px-3 py-2 text-text-primary/80">{e.model ?? "—"}</td>
                  <td className="px-3 py-2 text-text-primary/70">{e.summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
