import { Link } from "react-router-dom";
import labpulseLogo from "../resources/labpulse-logo.svg";

export default function About() {
  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-6 py-4">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-sm text-sky-400 hover:underline">
            ← Dashboard
          </Link>
          <h1 className="text-lg font-semibold tracking-tight">About</h1>
        </div>
      </header>

      <main className="mx-auto max-w-2xl p-6">
        <section className="rounded-md border border-surface-border bg-surface-raised p-8 text-center">
          <img src={labpulseLogo} alt="LabPulse" className="mx-auto h-40 w-40" />
          <h2 className="mt-4 text-xl font-semibold tracking-tight">LabPulse</h2>
          <p className="mt-2 text-sm text-slate-400">
            A self-hosted homelab observability and incident-history platform.
          </p>
        </section>

        <section className="mt-6 rounded-md border border-surface-border bg-surface-raised p-6 text-sm text-slate-300">
          <p>
            LabPulse watches your Docker host, keeps a history of container
            state, resource usage, and lifecycle events, and correlates the
            noisy bits into incidents so you can see what happened, what
            changed, and when.
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-y-2 text-slate-400">
            <dt>Source</dt>
            <dd>
              <a
                href="https://github.com/MattKrayson/LabPulse"
                target="_blank"
                rel="noreferrer"
                className="text-sky-400 hover:underline"
              >
                github.com/MattKrayson/LabPulse
              </a>
            </dd>
          </dl>
        </section>
      </main>
    </div>
  );
}
