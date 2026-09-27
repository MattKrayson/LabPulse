import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import IncidentDetail from "./IncidentDetail";

describe("IncidentDetail", () => {
  it("renders the incident header and event timeline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => ({
            id: 8,
            source_type: "container",
            source_id: "abc123",
            source_name: "labpulse",
            title: "labpulse incident",
            severity: "WARNING",
            status: "OPEN",
            started_at: new Date().toISOString(),
            ended_at: new Date().toISOString(),
            event_count: 1,
            events: [
              {
                id: 83,
                timestamp: new Date().toISOString(),
                severity: "WARNING",
                category: "DOCKER",
                source_type: "container",
                source_id: "abc123",
                source_name: "labpulse",
                title: "labpulse killed",
                description: null,
                event_metadata: null,
                created_at: new Date().toISOString(),
              },
            ],
          }),
        })
      )
    );

    render(
      <MemoryRouter initialEntries={["/incidents/8"]}>
        <Routes>
          <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Loading incident…")).toBeInTheDocument();
    expect(await screen.findByText("labpulse incident")).toBeInTheDocument();
    expect(await screen.findByText("labpulse killed")).toBeInTheDocument();
  });

  it("shows an error state when the incident cannot be loaded", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: false, status: 404, json: async () => ({}) }))
    );

    render(
      <MemoryRouter initialEntries={["/incidents/999"]}>
        <Routes>
          <Route path="/incidents/:incidentId" element={<IncidentDetail />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getByText("Unable to load this incident.")).toBeInTheDocument()
    );
  });
});
