import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getChanges, type ChangeEntry } from "../api/client";

type RangeKey = "24h" | "7d" | "30d";

const RANGES: { key: RangeKey; label: string; hours: number }[] = [
  { key: "24h", label: "24 hours", hours: 24 },
  { key: "7d", label: "7 days", hours: 7 * 24 },
  { key: "30d", label: "30 days", hours: 30 * 24 },
];

function sign(type: string): "+" | "-" {
  return type === "container_removed" ? "-" : "+";
}

function tone(type: string): string {
  if (type === "new_container") return "text-emerald-400";
  if (type === "container_removed") return "text-red-400";
  if (type === "image_changed") return "text-sky-400";
  if (type === "restarted") return "text-amber-400";
  if (type.endsWith("_increased")) return "text-amber-400";
  if (type.endsWith("_decreased")) return "text-emerald-400";
  return "text-slate-300";
}

export default function WhatChanged() {
  const [range, setRange] = useState<RangeKey>("24h");
  const [changes, setChanges] = useState<ChangeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const hours = RANGES.find((r) => r.key === range)!.hours;

    setLoading(true);
    setError(false);
    getChanges(hours)
      .then((data) => {
        if (!cancelled) setChanges(data);
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
  }, [range]);

  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/" className="text-sm text-sky-400 hover:underline">
              ← Back to dashboard
            </Link>
            <h1 className="text-lg font-semibold tracking-tight">What Changed?</h1>
          </div>
        </div>
      </header>

      <main className="p-6">
        <section className="flex items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-slate-500">Compare against</span>
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
              {r.label} ago
            </button>
          ))}
        </section>

        <section className="mt-4 rounded-md border border-surface-border bg-surface-raised p-6">
          {loading && <p className="text-slate-400">Comparing state…</p>}
          {!loading && error && (
            <p className="text-red-400">Unable to reach the LabPulse API.</p>
          )}
          {!loading && !error && changes.length === 0 && (
            <p className="text-slate-400">
              No meaningful changes detected in the selected window.
            </p>
          )}
          {!loading && !error && changes.length > 0 && (
            <ul className="divide-y divide-surface-border text-sm">
              {changes.map((change, index) => (
                <li key={`${change.container_id}-${change.type}-${index}`} className="flex items-start gap-3 py-3">
                  <span className={`font-mono font-semibold ${tone(change.type)}`}>
                    {sign(change.type)}
                  </span>
                  <div>
                    <p className="text-slate-200">{change.description}</p>
                    {change.detail && (
                      <p className="mt-0.5 text-xs text-slate-500">{change.detail}</p>
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
