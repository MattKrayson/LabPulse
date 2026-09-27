import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  getContainer,
  getEventsForSource,
  getHosts,
  getMetrics,
  type ContainerSummary,
  type EventSummary,
  type Host,
  type MetricPoint,
} from "../api/client";
import { Field, SeverityDot, StateBadge, formatHealth, formatUptime } from "../components/shared";

type RangeKey = "1h" | "6h" | "24h" | "7d";

const RANGES: { key: RangeKey; label: string; minutes: number; limit: number }[] = [
  { key: "1h", label: "1 hour", minutes: 60, limit: 500 },
  { key: "6h", label: "6 hours", minutes: 6 * 60, limit: 1500 },
  { key: "24h", label: "24 hours", minutes: 24 * 60, limit: 2000 },
  { key: "7d", label: "7 days", minutes: 7 * 24 * 60, limit: 2000 },
];

function formatTime(timestamp: string, range: RangeKey): string {
  const date = new Date(timestamp);
  return range === "7d"
    ? date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function toSeries(points: MetricPoint[], range: RangeKey) {
  return points.map((p) => ({ time: formatTime(p.timestamp, range), value: p.value }));
}

/** Docker reports network bytes as cumulative counters; convert to a Mbps rate between samples. */
function toRateSeriesMbps(points: MetricPoint[], range: RangeKey) {
  const rows: { time: string; value: number }[] = [];
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const seconds = (new Date(curr.timestamp).getTime() - new Date(prev.timestamp).getTime()) / 1000;
    const byteDelta = curr.value - prev.value;
    if (seconds <= 0 || byteDelta < 0) continue; // counter reset (e.g. container restart)
    const mbps = (byteDelta * 8) / 1_000_000 / seconds;
    rows.push({ time: formatTime(curr.timestamp, range), value: Math.round(mbps * 100) / 100 });
  }
  return rows;
}

function formatContainerId(containerId: string): string {
  return containerId.slice(0, 12);
}

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export default function ContainerDetail() {
  const { containerId } = useParams<{ containerId: string }>();
  const [container, setContainer] = useState<ContainerSummary | null>(null);
  const [hosts, setHosts] = useState<Host[]>([]);
  const [notFound, setNotFound] = useState(false);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [range, setRange] = useState<RangeKey>("1h");
  const [cpu, setCpu] = useState<MetricPoint[]>([]);
  const [memory, setMemory] = useState<MetricPoint[]>([]);
  const [netRx, setNetRx] = useState<MetricPoint[]>([]);
  const [netTx, setNetTx] = useState<MetricPoint[]>([]);

  useEffect(() => {
    getHosts()
      .then((data) => setHosts(data))
      .catch(() => {
        /* host name falls back to "—" */
      });
  }, []);

  useEffect(() => {
    if (!containerId) return;
    let cancelled = false;

    const load = () => {
      getContainer(containerId)
        .then((data) => {
          if (!cancelled) setContainer(data);
        })
        .catch(() => {
          if (!cancelled) setNotFound(true);
        });
      getEventsForSource(containerId)
        .then((data) => {
          if (!cancelled) setEvents(data);
        })
        .catch(() => {
          /* timeline stays empty on error */
        });
    };

    load();
    const interval = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [containerId]);

  useEffect(() => {
    if (!containerId) return;
    let cancelled = false;
    const { minutes, limit } = RANGES.find((r) => r.key === range)!;

    const load = () => {
      getMetrics(containerId, "cpu_percent", minutes, limit).then((d) => !cancelled && setCpu(d));
      getMetrics(containerId, "memory_percent", minutes, limit).then((d) => !cancelled && setMemory(d));
      getMetrics(containerId, "network_rx_bytes", minutes, limit).then((d) => !cancelled && setNetRx(d));
      getMetrics(containerId, "network_tx_bytes", minutes, limit).then((d) => !cancelled && setNetTx(d));
    };

    load();
    const interval = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [containerId, range]);

  if (notFound) {
    return (
      <div className="min-h-full p-6">
        <Link to="/" className="text-sm text-sky-400 hover:underline">
          ← Back to dashboard
        </Link>
        <p className="mt-4 text-slate-400">Container not found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-4 py-4 sm:px-6">
        <Link to="/" className="text-sm text-sky-400 hover:underline">
          ← Back to dashboard
        </Link>
      </header>

      <main className="p-4 sm:p-6">
        <section className="rounded-md border border-surface-border bg-surface-raised p-6">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight text-slate-100">
              {container?.name ?? "Loading…"}
            </h1>
            {container && <StateBadge state={container.state} />}
            {container && (
              <span className="rounded bg-surface-border px-2 py-0.5 font-mono text-xs text-slate-400">
                {formatContainerId(container.container_id)}
              </span>
            )}
          </div>
          {container && (
            <dl className="mt-4 grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-4">
              <Field label="Image" value={container.image} />
              <Field label="Host" value={hosts.find((h) => h.id === container.host_id)?.name ?? "—"} />
              <Field label="Status" value={container.status} />
              <Field label="Health" value={formatHealth(container.health_status, container.state)} />
              <Field
                label="Uptime"
                value={container.state === "running" ? formatUptime(container.started_at) : "—"}
              />
              <Field label="Restart Count" value={String(container.restart_count)} />
              <Field label="Created" value={formatDateTime(container.created_at)} />
              <Field label="First seen by LabPulse" value={formatDateTime(container.first_seen_at)} />
            </dl>
          )}
        </section>

        <section className="mt-6 flex flex-wrap items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-slate-500">Time range</span>
          {RANGES.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`rounded px-2 py-1 text-xs font-medium ${
                range === r.key
                  ? "bg-sky-500/20 text-sky-400"
                  : "bg-surface-raised text-slate-400 hover:text-slate-200"
              }`}
            >
              {r.label}
            </button>
          ))}
        </section>

        <section className="mt-4 grid gap-4 md:grid-cols-2">
          <MetricChart title="CPU %" unit="%" data={toSeries(cpu, range)} />
          <MetricChart title="Memory %" unit="%" data={toSeries(memory, range)} />
          <MetricChart title="Network RX (Mbps)" unit=" Mbps" data={toRateSeriesMbps(netRx, range)} />
          <MetricChart title="Network TX (Mbps)" unit=" Mbps" data={toRateSeriesMbps(netTx, range)} />
        </section>

        <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6">
          <h2 className="text-sm font-medium text-slate-400">Historical events</h2>

          {events.length === 0 ? (
            <p className="mt-3 text-slate-400">No events recorded for this container yet.</p>
          ) : (
            <ul className="mt-3 divide-y divide-surface-border text-sm">
              {events.map((event) => (
                <li key={event.id} className="flex items-start gap-3 py-2">
                  <span className="w-32 shrink-0 pt-0.5 font-mono text-xs text-slate-500">
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
          )}
        </section>
      </main>
    </div>
  );
}

function MetricChart({
  title,
  unit,
  data,
}: {
  title: string;
  unit: string;
  data: { time: string; value: number }[];
}) {
  return (
    <div className="rounded-md border border-surface-border bg-surface-raised p-4">
      <h3 className="text-xs uppercase tracking-wide text-slate-500">{title}</h3>
      <div className="mt-2 h-52">
        {data.length === 0 ? (
          <p className="flex h-full items-center justify-center text-sm text-slate-500">
            Not enough data yet.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748b" }} minTickGap={30} />
              <YAxis unit={unit} tick={{ fontSize: 11, fill: "#64748b" }} width={48} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#38bdf8"
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
