import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createWebhook,
  deleteWebhook,
  getWebhooks,
  testWebhook,
  type Webhook,
  type WebhookFormat,
} from "../api/client";

const FORMATS: { value: WebhookFormat; label: string }[] = [
  { value: "generic", label: "Generic JSON" },
  { value: "discord", label: "Discord" },
  { value: "slack", label: "Slack" },
  { value: "ntfy", label: "ntfy" },
];

export default function Webhooks() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [format, setFormat] = useState<WebhookFormat>("generic");
  const [notifyOnOpen, setNotifyOnOpen] = useState(true);
  const [notifyOnResolve, setNotifyOnResolve] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<Record<number, string>>({});

  const load = () => {
    getWebhooks()
      .then(setWebhooks)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleAdd = (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);
    createWebhook({
      name: name.trim(),
      url: url.trim(),
      format,
      notify_on_open: notifyOnOpen,
      notify_on_resolve: notifyOnResolve,
    })
      .then((webhook) => {
        setWebhooks((prev) => [...prev, webhook]);
        setName("");
        setUrl("");
      })
      .catch((err) => setFormError(err instanceof Error ? err.message : "Failed to add webhook"))
      .finally(() => setSubmitting(false));
  };

  const handleTest = (webhookId: number) => {
    setBusyId(webhookId);
    setTestResult((prev) => ({ ...prev, [webhookId]: "" }));
    testWebhook(webhookId)
      .then(() => setTestResult((prev) => ({ ...prev, [webhookId]: "Sent!" })))
      .catch((err) =>
        setTestResult((prev) => ({
          ...prev,
          [webhookId]: err instanceof Error ? err.message : "Failed",
        }))
      )
      .finally(() => setBusyId(null));
  };

  const handleDelete = (webhookId: number) => {
    if (!window.confirm("Remove this webhook?")) return;
    setBusyId(webhookId);
    deleteWebhook(webhookId)
      .then(() => setWebhooks((prev) => prev.filter((w) => w.id !== webhookId)))
      .finally(() => setBusyId(null));
  };

  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-4 py-4 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Link to="/" className="text-sm text-sky-400 hover:underline">
            ← Back to dashboard
          </Link>
          <h1 className="text-lg font-semibold tracking-tight">Webhooks</h1>
        </div>
      </header>

      <main className="p-4 sm:p-6">
        <section className="rounded-md border border-surface-border bg-surface-raised p-6">
          <h2 className="text-sm font-medium text-slate-400">Add a webhook</h2>
          <p className="mt-1 text-xs text-slate-500">
            Fired when an incident opens (and optionally resolves). Use "Discord"/"Slack" for
            their incoming webhook URLs, "ntfy" for a ntfy topic URL, or "Generic JSON" for your
            own endpoint.
          </p>
          <form onSubmit={handleAdd} className="mt-3 flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-xs uppercase tracking-wide text-slate-500">Name</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Discord alerts"
                className="mt-1 rounded-md border border-surface-border bg-surface-base px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wide text-slate-500">URL</label>
              <input
                required
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://discord.com/api/webhooks/…"
                className="mt-1 w-72 rounded-md border border-surface-border bg-surface-base px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wide text-slate-500">Format</label>
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value as WebhookFormat)}
                className="mt-1 rounded-md border border-surface-border bg-surface-base px-3 py-1.5 text-sm"
              >
                {FORMATS.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={notifyOnOpen}
                onChange={(e) => setNotifyOnOpen(e.target.checked)}
              />
              On open
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={notifyOnResolve}
                onChange={(e) => setNotifyOnResolve(e.target.checked)}
              />
              On resolve
            </label>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-sky-500/20 px-3 py-1.5 text-sm font-medium text-sky-400 hover:bg-sky-500/30 disabled:opacity-50"
            >
              {submitting ? "Adding…" : "Add webhook"}
            </button>
          </form>
          {formError && <p className="mt-2 text-sm text-red-400">{formError}</p>}
        </section>

        <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6">
          <h2 className="text-sm font-medium text-slate-400">Webhooks ({webhooks.length})</h2>
          {loading ? (
            <p className="mt-3 text-slate-400">Loading…</p>
          ) : webhooks.length === 0 ? (
            <p className="mt-3 text-slate-400">No webhooks configured yet.</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="py-1 pr-4">Name</th>
                    <th className="py-1 pr-4">Format</th>
                    <th className="py-1 pr-4">Triggers</th>
                    <th className="py-1 pr-4">Last triggered</th>
                    <th className="py-1 pr-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {webhooks.map((webhook) => (
                    <tr key={webhook.id}>
                      <td className="py-2 pr-4 font-medium text-slate-200">{webhook.name}</td>
                      <td className="py-2 pr-4 text-slate-400">{webhook.format}</td>
                      <td className="py-2 pr-4 text-slate-400">
                        {[
                          webhook.notify_on_open ? "open" : null,
                          webhook.notify_on_resolve ? "resolve" : null,
                        ]
                          .filter(Boolean)
                          .join(", ") || "—"}
                      </td>
                      <td className="py-2 pr-4 text-slate-400">
                        {webhook.last_triggered_at
                          ? new Date(webhook.last_triggered_at).toLocaleString()
                          : "never"}
                        {webhook.last_error && (
                          <p className="text-xs text-red-400" title={webhook.last_error}>
                            last delivery failed
                          </p>
                        )}
                      </td>
                      <td className="py-2 pr-4">
                        <div className="flex items-center gap-3">
                          <button
                            type="button"
                            disabled={busyId === webhook.id}
                            onClick={() => handleTest(webhook.id)}
                            className="text-xs text-sky-400 hover:underline disabled:opacity-50"
                          >
                            Send test
                          </button>
                          <button
                            type="button"
                            disabled={busyId === webhook.id}
                            onClick={() => handleDelete(webhook.id)}
                            className="text-xs text-red-400 hover:underline disabled:opacity-50"
                          >
                            Remove
                          </button>
                          {testResult[webhook.id] && (
                            <span className="text-xs text-slate-400">{testResult[webhook.id]}</span>
                          )}
                        </div>
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
