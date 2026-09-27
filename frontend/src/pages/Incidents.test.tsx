import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Incidents from "./Incidents";

describe("Incidents", () => {
  it("shows a loading state then renders incidents", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => [
            {
              id: 1,
              source_type: "container",
              source_id: "abc123",
              source_name: "jellyfin",
              title: "jellyfin incident",
              severity: "WARNING",
              status: "OPEN",
              started_at: new Date().toISOString(),
              ended_at: new Date().toISOString(),
              event_count: 2,
            },
          ],
        })
      )
    );

    render(
      <MemoryRouter>
        <Incidents />
      </MemoryRouter>
    );

    expect(screen.getByText("Loading incidents…")).toBeInTheDocument();
    expect(await screen.findByText("jellyfin incident")).toBeInTheDocument();
  });

  it("shows an empty state when there are no incidents", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: async () => [] }))
    );

    render(
      <MemoryRouter>
        <Incidents />
      </MemoryRouter>
    );

    expect(await screen.findByText("No incidents detected.")).toBeInTheDocument();
  });

  it("shows an error state when the API is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("network error")))
    );

    render(
      <MemoryRouter>
        <Incidents />
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getByText("Unable to reach the LabPulse API.")).toBeInTheDocument()
    );
  });
});
