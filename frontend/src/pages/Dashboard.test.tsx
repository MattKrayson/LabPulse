import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Dashboard from "./Dashboard";

function mockFetch(overrides: { health?: object; containers?: unknown[]; events?: unknown[]; stats?: object } = {}) {
  return vi.fn((url: string) => {
    if (url.includes("/health")) {
      return Promise.resolve({
        ok: true,
        json: async () => overrides.health ?? { status: "ok", app: "LabPulse", version: "0.1.0", database: "ok", timestamp: new Date().toISOString() },
      });
    }
    if (url.includes("/containers")) {
      return Promise.resolve({ ok: true, json: async () => overrides.containers ?? [] });
    }
    if (url.includes("/events")) {
      return Promise.resolve({ ok: true, json: async () => overrides.events ?? [] });
    }
    if (url.includes("/stats")) {
      return Promise.resolve({
        ok: true,
        json: async () =>
          overrides.stats ?? {
            total_containers: 0,
            healthy: 0,
            warning: 0,
            critical: 0,
            recent_errors: 0,
            recent_incidents: 0,
          },
      });
    }
    return Promise.reject(new Error(`unexpected fetch: ${url}`));
  });
}

describe("Dashboard", () => {
  it("shows connecting then online status once the backend responds", async () => {
    vi.stubGlobal("fetch", mockFetch());

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(screen.getByText("Connecting…")).toBeInTheDocument();
    expect(await screen.findByText("Online")).toBeInTheDocument();
  });

  it("shows an offline state when the backend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("network error")))
    );

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(
      await screen.findByText("Unable to reach the LabPulse API. Is the backend running?")
    ).toBeInTheDocument();
  });

  it("renders discovered containers and the recent incidents stat", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        containers: [
          {
            id: 1,
            host_id: 1,
            container_id: "abc123",
            name: "jellyfin",
            image: "jellyfin/jellyfin",
            image_id: "sha256:abc",
            created_at: null,
            state: "running",
            status: "Up 2 hours",
            health_status: "healthy",
            restart_count: 0,
            started_at: new Date().toISOString(),
            is_present: true,
            first_seen_at: new Date().toISOString(),
            last_seen_at: new Date().toISOString(),
          },
        ],
        stats: {
          total_containers: 1,
          healthy: 1,
          warning: 0,
          critical: 0,
          recent_errors: 0,
          recent_incidents: 2,
        },
      })
    );

    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(await screen.findByText("jellyfin")).toBeInTheDocument();
    expect(await screen.findByText("Recent Incidents")).toBeInTheDocument();
    expect(await screen.findByText("2")).toBeInTheDocument();
  });
});
