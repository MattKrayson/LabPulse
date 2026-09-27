import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getMetrics, type ContainerSummary, type MetricType } from "../api/client";

const LINE_COLORS = [
  "#38bdf8",
  "#34d399",
  "#fbbf24",
  "#f87171",
  "#a78bfa",
  "#f472b6",
  "#22d3ee",
  "#a3e635",
  "#fb923c",
  "#818cf8",
];

type SeriesRow = Record<string, number | string> & { time: string };

async function buildSeries(
  containers: ContainerSummary[],
  metricType: MetricType
): Promise<{ data: SeriesRow[]; names: string[] }> {
  const tracked = containers;
  const results = await Promise.all(
    tracked.map((c) =>
      getMetrics(c.container_id, metricType).catch(() => [])
    )
  );

  const rowsByTimestamp = new Map<string, SeriesRow>();
  tracked.forEach((container, index) => {
    for (const point of results[index]) {
      const row = rowsByTimestamp.get(point.timestamp) ?? {
        time: new Date(point.timestamp).toLocaleTimeString(),
        timestamp: point.timestamp,
      };
      row[container.name] = Math.round(point.value * 10) / 10;
      rowsByTimestamp.set(point.timestamp, row);
    }
  });

  const data = Array.from(rowsByTimestamp.values()).sort((a, b) =>
    String(a.timestamp).localeCompare(String(b.timestamp))
  );

  return { data, names: tracked.map((c) => c.name) };
}

function ResourceChart({
  title,
  unit,
  data,
  names,
  selected,
  onToggle,
}: {
  title: string;
  unit: string;
  data: SeriesRow[];
  names: string[];
  selected: string[];
  onToggle: (name: string) => void;
}) {
  return (
    <div>
      <h3 className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</h3>
      {data.length === 0 ? (
        <p className="mt-3 text-sm text-slate-400">Not enough data yet.</p>
      ) : (
        <div className="mt-2 h-48">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#64748b" }} />
              <YAxis
                tick={{ fontSize: 11, fill: "#64748b" }}
                unit={unit}
                width={40}
              />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
                position={{ y: 0 }}
                wrapperStyle={{ pointerEvents: "none" }}
              />
              <Legend
                wrapperStyle={{ fontSize: 11, cursor: "pointer" }}
                onClick={(entry) => onToggle(String(entry.dataKey))}
                formatter={(value) => (
                  <span
                    style={{
                      color: selected.length === 0 || selected.includes(value) ? "#cbd5e1" : "#475569",
                      textDecoration: selected.includes(value) ? "underline" : "none",
                    }}
                  >
                    {value}
                  </span>
                )}
              />
              {names.map((name, index) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={LINE_COLORS[index % LINE_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                  isAnimationActive={false}
                  hide={selected.length > 0 && !selected.includes(name)}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default function ResourceOverview({ containers }: { containers: ContainerSummary[] }) {
  const [cpu, setCpu] = useState<{ data: SeriesRow[]; names: string[] }>({ data: [], names: [] });
  const [memory, setMemory] = useState<{ data: SeriesRow[]; names: string[] }>({ data: [], names: [] });
  const [selected, setSelected] = useState<string[]>([]);

  const running = containers.filter((c) => c.state === "running");
  const key = running.map((c) => c.container_id).join(",");

  const toggleName = (name: string) => {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]
    );
  };

  useEffect(() => {
    if (running.length === 0) {
      setCpu({ data: [], names: [] });
      setMemory({ data: [], names: [] });
      return;
    }

    let cancelled = false;

    const load = () => {
      buildSeries(running, "cpu_percent").then((result) => {
        if (!cancelled) setCpu(result);
      });
      buildSeries(running, "memory_percent").then((result) => {
        if (!cancelled) setMemory(result);
      });
    };

    load();
    const interval = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return (
    <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-slate-400">Resource overview</h2>
        {selected.length > 0 && (
          <button
            type="button"
            onClick={() => setSelected([])}
            className="rounded border border-surface-border px-2 py-1 text-xs text-slate-300 hover:bg-surface-border"
          >
            Clear filter
          </button>
        )}
      </div>
      {running.length === 0 ? (
        <p className="mt-3 text-slate-400">No running containers to chart yet.</p>
      ) : (
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <ResourceChart
            title="CPU %"
            unit="%"
            data={cpu.data}
            names={cpu.names}
            selected={selected}
            onToggle={toggleName}
          />
          <ResourceChart
            title="Memory %"
            unit="%"
            data={memory.data}
            names={memory.names}
            selected={selected}
            onToggle={toggleName}
          />
        </div>
      )}
    </section>
  );
}
