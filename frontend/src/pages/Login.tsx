import { useState } from "react";
import type { FormEvent } from "react";
import { login } from "../api/client";

export default function Login({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    login(username, password)
      .then(() => onLoggedIn())
      .catch(() => setError("Invalid username or password"))
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="flex min-h-full items-center justify-center p-6">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-surface-border bg-surface-raised p-6"
      >
        <h1 className="mb-4 text-lg font-semibold tracking-tight">LabPulse</h1>
        <label className="mb-3 block text-sm">
          Username
          <input
            className="mt-1 w-full rounded border border-surface-border bg-transparent px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
        </label>
        <label className="mb-4 block text-sm">
          Password
          <input
            type="password"
            className="mt-1 w-full rounded border border-surface-border bg-transparent px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="mb-4 text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-sky-500 px-3 py-2 text-sm font-medium text-white hover:bg-sky-400 disabled:opacity-50"
        >
          {submitting ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
