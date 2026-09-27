import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getContainers,
  getEvents,
  getHealth,
  getStats,
  logout,
  type ContainerSummary,
  type EventSummary,
  type HealthResponse,
  type StatsResponse,
} from "../api/client";
import ResourceOverview from "../components/ResourceOverview";
import { Field, SeverityDot, StateBadge, formatHealth } from "../components/shared";
import labpulseLogo from "../resources/labpulse-logo.svg";

type ConnectionState = "loading" | "online" | "offline";

export default function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [state, setState] = useState<ConnectionState>("loading");
  const [containers, setContainers] = useState<ContainerSummary[]>([]);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [dataError, setDataError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    getHealth()
      .then((data) => {
        if (cancelled) return;
        setHealth(data);
        setState("online");
      })
      .catch(() => {
        if (cancelled) return;
        setState("offline");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const load = () => {
      getContainers()
        .then((data) => {
          if (!cancelled) {
            setContainers(data);
            setDataError(false);
          }
        })
        .catch(() => {
          if (!cancelled) setDataError(true);
        });
      getEvents()
        .then((data) => {
          if (!cancelled) setEvents(data);
        })
        .catch(() => {
          if (!cancelled) setDataError(true);
        });
      getStats()
        .then((data) => {
          if (!cancelled) setStats(data);
        })
        .catch(() => {
          if (!cancelled) setDataError(true);
        });
    };

    load();
    const interval = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img src={labpulseLogo} alt="LabPulse" className="h-12 w-12" />
            <h1 className="text-lg font-semibold tracking-tight">LabPulse</h1>
            <Link to="/incidents" className="text-sm text-sky-400 hover:underline">
              Incidents
            </Link>
            <Link to="/changes" className="text-sm text-sky-400 hover:underline">
              What Changed?
            </Link>
            <Link to="/settings/database" className="text-sm text-sky-400 hover:underline">
              Database
            </Link>
            <Link to="/about" className="text-sm text-sky-400 hover:underline">
              About
            </Link>
          </div>
          <div className="flex items-center gap-4">
            <StatusPill state={state} />
            <button
              type="button"
              onClick={() => logout().finally(() => window.location.reload())}
              className="text-sm text-slate-400 hover:text-slate-200 hover:underline"
            >
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="p-6">
        {dataError && (
          <p className="mb-4 rounded-md border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
            Some dashboard data failed to load. Retrying automatically every 15 seconds.
          </p>
        )}

        <section className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <StatCard label="Total Containers" value={stats?.total_containers} />
          <StatCard label="Healthy" value={stats?.healthy} tone="healthy" />
          <StatCard label="Warning" value={stats?.warning} tone="warning" />
          <StatCard label="Critical" value={stats?.critical} tone="critical" />
          <StatCard label="Errors (24h)" value={stats?.recent_errors} tone="critical" />
          <Link to="/incidents">
            <StatCard label="Recent Incidents" value={stats?.recent_incidents} tone="warning" />
          </Link>
        </section>

        <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6">
          <h2 className="text-sm font-medium text-slate-400">Backend status</h2>
          {state === "loading" && <p className="mt-2 text-slate-400">Checking backend…</p>}
          {state === "offline" && (
            <p className="mt-2 text-red-400">
              Unable to reach the LabPulse API. Is the backend running?
            </p>
          )}
          {state === "online" && health && (
            <dl className="mt-3 grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-4">
              <Field label="Status" value={health.status} />
              <Field label="Version" value={health.version} />
              <Field label="Database" value={health.database} />
              <Field label="Checked" value={new Date(health.timestamp).toLocaleTimeString()} />
            </dl>
          )}
        </section>
        <section>
          <ResourceOverview containers={containers} />
        </section>
        <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-slate-400">
              Containers ({containers.length})
            </h2>
          </div>

          {containers.length === 0 ? (
            <p className="mt-3 text-slate-400">
              No containers discovered yet. LabPulse polls Docker every 15 seconds.
            </p>
          ) : (
            <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="py-1 pr-4">Name</th>
                  <th className="py-1 pr-4">Image</th>
                  <th className="py-1 pr-4">State</th>
                  <th className="py-1 pr-4">Health</th>
                  <th className="py-1 pr-4">Restarts</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {containers.map((c) => (
                  <tr key={c.container_id}>
                    <td className="py-2 pr-4 font-medium text-slate-200">
                      <Link
                        to={`/containers/${c.container_id}`}
                        className="hover:text-sky-400 hover:underline"
                      >
                        {c.name}
                      </Link>
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{c.image}</td>
                    <td className="py-2 pr-4">
                      <StateBadge state={c.state} />
                    </td>
                    <td className="py-2 pr-4 text-slate-400">{formatHealth(c.health_status, c.state)}</td>
                    <td className="py-2 pr-4 text-slate-400">{c.restart_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          )}
        </section>

        <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6">
          <h2 className="text-sm font-medium text-slate-400">Recent timeline</h2>

          {events.length === 0 ? (
            <p className="mt-3 text-slate-400">
              No events recorded yet. Start, stop, or restart a container to see it appear here.
            </p>
          ) : (
            <ul className="mt-3 divide-y divide-surface-border text-sm">
              {events.map((event) => (
                <li key={event.id} className="flex items-start gap-3 py-2">
                  <span className="w-20 shrink-0 pt-0.5 font-mono text-xs text-slate-500">
                    {new Date(event.timestamp).toLocaleTimeString()}
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
          )}
        </section>

      </main>
    </div>
  );
}

function StatusPill({ state }: { state: ConnectionState }) {
  const styles: Record<ConnectionState, string> = {
    loading: "bg-slate-700 text-slate-300",
    online: "bg-emerald-500/15 text-emerald-400",
    offline: "bg-red-500/15 text-red-400",
  };
  const labels: Record<ConnectionState, string> = {
    loading: "Connecting…",
    online: "Online",
    offline: "Offline",
  };

  return (
    <span className={`rounded px-2 py-1 text-xs font-medium ${styles[state]}`}>
      {labels[state]}
    </span>
  );
}

type Tone = "neutral" | "healthy" | "warning" | "critical";

function StatCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number | undefined;
  tone?: Tone;
}) {
  const valueStyles: Record<Tone, string> = {
    neutral: "text-slate-100",
    healthy: "text-emerald-400",
    warning: "text-amber-400",
    critical: "text-red-400",
  };

  return (
    <div className="rounded-md border border-surface-border bg-surface-raised p-4">
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className={`mt-1 text-2xl font-semibold ${valueStyles[tone]}`}>
        {value ?? "—"}
      </dd>
    </div>
  );
}
