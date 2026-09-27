import type { Severity } from "../api/client";

export function StateBadge({ state }: { state: string }) {
  const styles: Record<string, string> = {
    running: "bg-emerald-500/15 text-emerald-400",
    exited: "bg-slate-700 text-slate-300",
    paused: "bg-amber-500/15 text-amber-400",
    restarting: "bg-amber-500/15 text-amber-400",
    dead: "bg-red-500/15 text-red-400",
  };

  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${styles[state] ?? "bg-slate-700 text-slate-300"}`}>
      {state}
    </span>
  );
}

export function SeverityDot({ severity }: { severity: Severity | string }) {
  const styles: Record<string, string> = {
    INFO: "bg-sky-400",
    WARNING: "bg-amber-400",
    ERROR: "bg-red-400",
    CRITICAL: "bg-red-600",
  };

  return (
    <span
      className={`h-2 w-2 shrink-0 rounded-full ${styles[severity] ?? "bg-slate-500"}`}
      aria-label={severity}
    />
  );
}

export function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="text-slate-200">{value}</dd>
    </div>
  );
}

/** Docker only reports a health status for containers with a HEALTHCHECK defined. */
export function formatHealth(healthStatus: string | null, state?: string): string {
  if (healthStatus) return healthStatus;
  if (state && state !== "running") return "—";
  return "no healthcheck";
}

export function formatUptime(startedAt: string | null): string {
  if (!startedAt) return "—";
  const startMs = new Date(startedAt).getTime();
  if (Number.isNaN(startMs)) return "—";
  let seconds = Math.max(0, Math.floor((Date.now() - startMs) / 1000));

  const days = Math.floor(seconds / 86400);
  seconds -= days * 86400;
  const hours = Math.floor(seconds / 3600);
  seconds -= hours * 3600;
  const minutes = Math.floor(seconds / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}
