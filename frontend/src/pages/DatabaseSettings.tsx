import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import SetupWizard from "./SetupWizard";
import { getSetupStatus } from "../api/client";

export default function DatabaseSettings() {
  const [currentUrlMasked, setCurrentUrlMasked] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getSetupStatus()
      .then((status) => setCurrentUrlMasked(status.database_url_masked))
      .catch(() => setCurrentUrlMasked(null));
  }, []);

  return (
    <div className="min-h-full">
      <header className="border-b border-surface-border bg-surface-raised px-6 py-4">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-sm text-sky-400 hover:underline">
            ← Dashboard
          </Link>
          <h1 className="text-lg font-semibold tracking-tight">Database settings</h1>
        </div>
      </header>
      <main>
        {saved && (
          <p className="mx-auto mt-6 max-w-md rounded-md border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-center text-sm text-emerald-400">
            Database connection updated.
          </p>
        )}
        <SetupWizard
          variant="settings"
          currentUrlMasked={currentUrlMasked}
          onComplete={() => {
            setSaved(true);
            getSetupStatus()
              .then((status) => setCurrentUrlMasked(status.database_url_masked))
              .catch(() => undefined);
          }}
        />
      </main>
    </div>
  );
}
