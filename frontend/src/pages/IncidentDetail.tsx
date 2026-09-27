import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getIncident, type IncidentDetail as IncidentDetailData } from "../api/client";
import { SeverityDot } from "../components/shared";

export default function IncidentDetail() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const [incident, setIncident] = useState<IncidentDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!incidentId) return;
    let cancelled = false;

    setLoading(true);
    setError(false);
    getIncident(Number(incidentId))
      .then((data) => {
        if (!cancelled) setIncident(data);
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
  }, [incidentId]);

  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-6 py-4">
        <div className="flex items-center gap-4">
          <Link to="/incidents" className="text-sm text-sky-400 hover:underline">
            ← Back to incidents
          </Link>
          <h1 className="text-lg font-semibold tracking-tight">Incident detail</h1>
        </div>
      </header>

      <main className="p-6">
        {loading && <p className="text-slate-400">Loading incident…</p>}
        {!loading && error && <p className="text-red-400">Unable to load this incident.</p>}

        {!loading && !error && incident && (
          <>
            <section className="rounded-md border border-surface-border bg-surface-raised p-6">
              <div className="flex items-center gap-3">
                <SeverityDot severity={incident.severity} />
                <h2 className="text-lg font-semibold text-slate-100">{incident.title}</h2>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-medium ${
                    incident.status === "OPEN"
                      ? "bg-amber-500/15 text-amber-400"
                      : "bg-slate-700 text-slate-300"
                  }`}
                >
                  {incident.status}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-400">
                {new Date(incident.started_at).toLocaleString()} —{" "}
                {new Date(incident.ended_at).toLocaleString()} · {incident.event_count} event
                {incident.event_count === 1 ? "" : "s"}
              </p>
            </section>

            <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6">
              <h2 className="text-sm font-medium text-slate-400">Timeline</h2>
              <ul className="mt-3 divide-y divide-surface-border text-sm">
                {incident.events.map((event) => (
                  <li key={event.id} className="flex items-start gap-3 py-2">
                    <span className="w-40 shrink-0 pt-0.5 font-mono text-xs text-slate-500">
                      {new Date(event.timestamp).toLocaleString()}
                    </span>
                    <SeverityDot severity={event.severity} />
                    <div>
                      <span className="text-slate-200">{event.title}</span>
                      {event.description && (
                        <p className="whitespace-pre-wrap text-xs text-slate-500">{event.description}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
