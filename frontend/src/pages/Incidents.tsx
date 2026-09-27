import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getIncidents, type IncidentStatus, type IncidentSummary } from "../api/client";
import { SeverityDot } from "../components/shared";

const STATUS_FILTERS: { key: IncidentStatus | "ALL"; label: string }[] = [
  { key: "ALL", label: "All" },
  { key: "OPEN", label: "Open" },
  { key: "RESOLVED", label: "Resolved" },
];

export default function Incidents() {
  const [filter, setFilter] = useState<IncidentStatus | "ALL">("ALL");
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    setLoading(true);
    setError(false);
    getIncidents(filter === "ALL" ? undefined : filter)
      .then((data) => {
        if (!cancelled) setIncidents(data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [filter]);

  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-4 py-4 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Link to="/" className="text-sm text-sky-400 hover:underline">
            ← Back to dashboard
          </Link>
          <h1 className="text-lg font-semibold tracking-tight">Incidents</h1>
        </div>
      </header>

      <main className="p-4 sm:p-6">
        <section className="flex flex-wrap items-center gap-2">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`rounded px-2 py-1 text-xs font-medium ${
                filter === f.key
                  ? "bg-sky-500/20 text-sky-400"
                  : "bg-surface-raised text-slate-400 hover:text-slate-200"
              }`}
            >
              {f.label}
            </button>
          ))}
        </section>

        <section className="mt-4 rounded-md border border-surface-border bg-surface-raised p-6">
          {loading && <p className="text-slate-400">Loading incidents…</p>}
          {!loading && error && (
            <p className="text-red-400">Unable to reach the LabPulse API.</p>
          )}
          {!loading && !error && incidents.length === 0 && (
            <p className="text-slate-400">No incidents detected.</p>
          )}
          {!loading && !error && incidents.length > 0 && (
            <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="py-1 pr-4"></th>
                  <th className="py-1 pr-4">Source</th>
                  <th className="py-1 pr-4">Title</th>
                  <th className="py-1 pr-4">Started</th>
                  <th className="py-1 pr-4">Ended</th>
                  <th className="py-1 pr-4">Events</th>
                  <th className="py-1 pr-4">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {incidents.map((incident) => (
                  <tr key={incident.id}>
                    <td className="py-2 pr-4">
                      <SeverityDot severity={incident.severity} />
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{incident.source_name}</td>
                    <td className="py-2 pr-4 font-medium text-slate-200">
                      <Link to={`/incidents/${incident.id}`} className="hover:text-sky-400 hover:underline">
                        {incident.title}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-slate-400">
                      {new Date(incident.started_at).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4 text-slate-400">
                      {new Date(incident.ended_at).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{incident.event_count}</td>
                    <td className="py-2 pr-4">
                      <span
                        className={`rounded px-2 py-0.5 text-xs font-medium ${
                          incident.status === "OPEN"
                            ? "bg-amber-500/15 text-amber-400"
                            : "bg-slate-700 text-slate-300"
                        }`}
                      >
                        {incident.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
