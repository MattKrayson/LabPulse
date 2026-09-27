import { useState } from "react";
import type { FormEvent } from "react";
import {
  applyDatabaseConfig,
  testDatabaseConfig,
  getHealth,
  SetupError,
  type DatabaseMode,
} from "../api/client";

interface SetupWizardProps {
  onComplete: () => void;
  /** Shows a smaller inline card (for the "change later" settings page) instead of a full-page splash. */
  variant?: "first-run" | "settings";
  currentUrlMasked?: string | null;
}

interface ConnectionFields {
  host: string;
  port: string;
  database: string;
  username: string;
  password: string;
}

const EMPTY_FIELDS: ConnectionFields = { host: "", port: "5432", database: "", username: "", password: "" };

function buildDatabaseUrl(fields: ConnectionFields): string {
  const user = encodeURIComponent(fields.username);
  const pass = encodeURIComponent(fields.password);
  const port = fields.port || "5432";
  return `postgresql+psycopg2://${user}:${pass}@${fields.host}:${port}/${fields.database}`;
}

export default function SetupWizard({ onComplete, variant = "first-run", currentUrlMasked }: SetupWizardProps) {
  const [mode, setMode] = useState<DatabaseMode>("internal");
  const [fields, setFields] = useState<ConnectionFields>(EMPTY_FIELDS);
  const [testing, setTesting] = useState(false);
  const [applying, setApplying] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const [testResult, setTestResult] = useState<"ok" | "error" | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const busy = testing || applying;
  const fieldsComplete = fields.host && fields.database && fields.username;

  const updateField = (key: keyof ConnectionFields) => (event: { target: { value: string } }) => {
    setFields((prev) => ({ ...prev, [key]: event.target.value }));
    setTestResult(null);
  };

  const handleTest = (event: FormEvent) => {
    event.preventDefault();
    setTesting(true);
    setTestResult(null);
    setMessage(null);
    testDatabaseConfig(mode, mode === "custom" ? buildDatabaseUrl(fields) : undefined)
      .then(() => {
        setTestResult("ok");
        setMessage("Connection succeeded.");
      })
      .catch((err) => {
        setTestResult("error");
        setMessage(err instanceof SetupError ? err.message : "Could not test the connection.");
      })
      .finally(() => setTesting(false));
  };

  const handleApply = () => {
    setConfirming(false);
    setApplying(true);
    setMessage(null);
    applyDatabaseConfig(mode, mode === "custom" ? buildDatabaseUrl(fields) : undefined)
      .then((result) => {
        if (result.restarting) {
          setApplying(false);
          setRestarting(true);
          waitForRestart();
          return;
        }
        onComplete();
      })
      .catch((err) => {
        setTestResult("error");
        setMessage(err instanceof SetupError ? err.message : "Could not set up the database.");
      })
      .finally(() => setApplying(false));
  };

  const waitForRestart = (attempt = 0) => {
    const maxAttempts = 30; // ~45s
    getHealth()
      .then((health) => {
        if (health.status === "ok" || health.status === "degraded") {
          onComplete();
        } else {
          throw new Error("not ready");
        }
      })
      .catch(() => {
        if (attempt >= maxAttempts) {
          setMessage("The container is taking longer than expected to restart. Try refreshing the page.");
          return;
        }
        setTimeout(() => waitForRestart(attempt + 1), 1500);
      });
  };

  const card = (
    <form
      onSubmit={handleTest}
      className="w-full max-w-md rounded-lg border border-surface-border bg-surface-raised p-6"
    >
      <h1 className="mb-1 text-lg font-semibold tracking-tight">
        {variant === "first-run" ? "Set up your database" : "Database connection"}
      </h1>
      <p className="mb-4 text-sm text-slate-400">
        {variant === "first-run"
          ? "Choose where LabPulse stores its data before it starts collecting anything."
          : "Change the database LabPulse uses. Existing data collection keeps running until you apply a new connection."}
      </p>
      {currentUrlMasked && (
        <p className="mb-4 rounded border border-surface-border bg-black/20 px-3 py-2 text-xs text-slate-400">
          Currently connected to: <span className="text-slate-200">{currentUrlMasked}</span>
        </p>
      )}

      <div className="mb-4 flex gap-2">
        <button
          type="button"
          onClick={() => {
            setMode("internal");
            setTestResult(null);
            setMessage(null);
            setFields(EMPTY_FIELDS);
          }}
          className={`flex-1 rounded border px-3 py-2 text-sm ${
            mode === "internal"
              ? "border-sky-500 bg-sky-500/10 text-sky-300"
              : "border-surface-border text-slate-400"
          }`}
        >
          Internal (SQLite)
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("custom");
            setTestResult(null);
            setMessage(null);
          }}
          className={`flex-1 rounded border px-3 py-2 text-sm ${
            mode === "custom"
              ? "border-sky-500 bg-sky-500/10 text-sky-300"
              : "border-surface-border text-slate-400"
          }`}
        >
          Custom connection
        </button>
      </div>

      {mode === "custom" && (
        <div className="mb-4 grid grid-cols-2 gap-3">
          <label className="col-span-2 block text-sm">
            Host / IP
            <input
              className="mt-1 w-full rounded border border-surface-border bg-transparent px-3 py-2 text-sm"
              placeholder="10.5.0.33"
              value={fields.host}
              onChange={updateField("host")}
              autoFocus
            />
          </label>
          <label className="block text-sm">
            Port
            <input
              className="mt-1 w-full rounded border border-surface-border bg-transparent px-3 py-2 text-sm"
              placeholder="5432"
              value={fields.port}
              onChange={updateField("port")}
            />
          </label>
          <label className="block text-sm">
            Database name
            <input
              className="mt-1 w-full rounded border border-surface-border bg-transparent px-3 py-2 text-sm"
              placeholder="labpulse"
              value={fields.database}
              onChange={updateField("database")}
            />
          </label>
          <label className="block text-sm">
            Username
            <input
              className="mt-1 w-full rounded border border-surface-border bg-transparent px-3 py-2 text-sm"
              value={fields.username}
              onChange={updateField("username")}
            />
          </label>
          <label className="block text-sm">
            Password
            <input
              type="password"
              className="mt-1 w-full rounded border border-surface-border bg-transparent px-3 py-2 text-sm"
              value={fields.password}
              onChange={updateField("password")}
            />
          </label>
        </div>
      )}

      {message && (
        <p
          className={`mb-4 text-sm ${testResult === "ok" ? "text-emerald-400" : "text-red-400"}`}
        >
          {message}
        </p>
      )}

      {confirming ? (
        <div className="mb-4 rounded border border-amber-500/40 bg-amber-500/10 p-3">
          <p className="mb-3 text-sm text-amber-300">
            Applying this connection will restart the LabPulse container. It will be briefly
            unavailable while it restarts.
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setConfirming(false)}
              className="flex-1 rounded border border-surface-border px-3 py-2 text-sm hover:bg-white/5"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleApply}
              className="flex-1 rounded bg-amber-500 px-3 py-2 text-sm font-medium text-black hover:bg-amber-400"
            >
              Yes, apply &amp; restart
            </button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={busy || (mode === "custom" && !fieldsComplete)}
            className="flex-1 rounded border border-surface-border px-3 py-2 text-sm hover:bg-white/5 disabled:opacity-50"
          >
            {testing ? "Testing..." : "Test connection"}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(true)}
            disabled={busy || testResult !== "ok"}
            className="flex-1 rounded bg-sky-500 px-3 py-2 text-sm font-medium text-white hover:bg-sky-400 disabled:opacity-50"
          >
            {applying ? "Saving..." : "Save & continue"}
          </button>
        </div>
      )}
    </form>
  );

  const restartingCard = (
    <div className="w-full max-w-md rounded-lg border border-surface-border bg-surface-raised p-6 text-center">
      <h1 className="mb-2 text-lg font-semibold tracking-tight">Restarting LabPulse…</h1>
      <p className="text-sm text-slate-400">
        Applying the new database connection and restarting the container. This page will
        continue automatically once it's back.
      </p>
      {message && <p className="mt-4 text-sm text-red-400">{message}</p>}
    </div>
  );

  if (restarting) {
    if (variant === "settings") {
      return <div className="flex justify-center p-6">{restartingCard}</div>;
    }
    return <div className="flex min-h-full items-center justify-center p-6">{restartingCard}</div>;
  }

  if (variant === "settings") {
    return <div className="flex justify-center p-6">{card}</div>;
  }

  return <div className="flex min-h-full items-center justify-center p-6">{card}</div>;
}
