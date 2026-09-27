import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createHost, deleteHost, getHosts, testHost, type Host } from "../api/client";

export default function Hosts() {
  const [hosts, setHosts] = useState<Host[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [connectionUrl, setConnectionUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = () => {
    getHosts()
      .then(setHosts)
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const handleAdd = (event: React.FormEvent) => {
    event.preventDefault();
    setFormError(null);
    setSubmitting(true);
    createHost(name.trim(), connectionUrl.trim())
      .then((host) => {
        setHosts((prev) => [...prev, host]);
        setName("");
        setConnectionUrl("");
      })
      .catch((err) => setFormError(err instanceof Error ? err.message : "Failed to add host"))
      .finally(() => setSubmitting(false));
  };

  const handleTest = (hostId: number) => {
    setBusyId(hostId);
    testHost(hostId)
      .then((updated) => setHosts((prev) => prev.map((h) => (h.id === hostId ? updated : h))))
      .finally(() => setBusyId(null));
  };

  const handleDelete = (hostId: number) => {
    if (!window.confirm("Remove this host and its discovered containers?")) return;
    setBusyId(hostId);
    deleteHost(hostId)
      .then(() => setHosts((prev) => prev.filter((h) => h.id !== hostId)))
      .finally(() => setBusyId(null));
  };

  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-4 py-4 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Link to="/" className="text-sm text-sky-400 hover:underline">
            ← Back to dashboard
          </Link>
          <h1 className="text-lg font-semibold tracking-tight">Docker Hosts</h1>
        </div>
      </header>

      <main className="p-4 sm:p-6">
        <section className="rounded-md border border-surface-border bg-surface-raised p-6">
          <h2 className="text-sm font-medium text-slate-400">Add a remote host</h2>
          <p className="mt-1 text-xs text-slate-500">
            Connects over the Docker Engine API, e.g. <code>tcp://192.168.1.20:2375</code> or an
            SSH URL like <code>ssh://user@192.168.1.20</code>. The remote daemon must have its API
            exposed and reachable from this machine.
          </p>
          <form onSubmit={handleAdd} className="mt-3 flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-xs uppercase tracking-wide text-slate-500">Name</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Living Room NUC"
                className="mt-1 rounded-md border border-surface-border bg-surface-base px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs uppercase tracking-wide text-slate-500">
                Connection URL
              </label>
              <input
                required
                value={connectionUrl}
                onChange={(e) => setConnectionUrl(e.target.value)}
                placeholder="tcp://192.168.1.20:2375"
                className="mt-1 w-64 rounded-md border border-surface-border bg-surface-base px-3 py-1.5 text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-sky-500/20 px-3 py-1.5 text-sm font-medium text-sky-400 hover:bg-sky-500/30 disabled:opacity-50"
            >
              {submitting ? "Adding…" : "Add host"}
            </button>
          </form>
          {formError && <p className="mt-2 text-sm text-red-400">{formError}</p>}
        </section>

        <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6">
          <h2 className="text-sm font-medium text-slate-400">Hosts ({hosts.length})</h2>
          {loading ? (
            <p className="mt-3 text-slate-400">Loading…</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="py-1 pr-4">Name</th>
                    <th className="py-1 pr-4">Connection</th>
                    <th className="py-1 pr-4">Status</th>
                    <th className="py-1 pr-4"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {hosts.map((host) => (
                    <tr key={host.id}>
                      <td className="py-2 pr-4 font-medium text-slate-200">
                        {host.name}
                        {host.is_local && (
                          <span className="ml-2 rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-300">
                            local
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-4 text-slate-400">
                        {host.connection_url ?? "unix socket"}
                      </td>
                      <td className="py-2 pr-4">
                        <HostStatus status={host.status} lastError={host.last_error} />
                      </td>
                      <td className="py-2 pr-4">
                        {!host.is_local && (
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              disabled={busyId === host.id}
                              onClick={() => handleTest(host.id)}
                              className="text-xs text-sky-400 hover:underline disabled:opacity-50"
                            >
                              Test
                            </button>
                            <button
                              type="button"
                              disabled={busyId === host.id}
                              onClick={() => handleDelete(host.id)}
                              className="text-xs text-red-400 hover:underline disabled:opacity-50"
                            >
                              Remove
                            </button>
                          </div>
                        )}
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

function HostStatus({ status, lastError }: { status: Host["status"]; lastError: string | null }) {
  const styles: Record<Host["status"], string> = {
    connected: "bg-emerald-500/15 text-emerald-400",
    error: "bg-red-500/15 text-red-400",
    unknown: "bg-slate-700 text-slate-300",
  };
  return (
    <span
      className={`rounded px-2 py-0.5 text-xs font-medium ${styles[status]}`}
      title={lastError ?? undefined}
    >
      {status}
    </span>
  );
}
