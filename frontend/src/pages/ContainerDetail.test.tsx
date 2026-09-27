import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import ContainerDetail from "./ContainerDetail";

describe("ContainerDetail", () => {
  it("renders container info and historical events", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/metrics")) {
          return Promise.resolve({ ok: true, json: async () => [] });
        }
        if (url.includes("/hosts")) {
          return Promise.resolve({
            ok: true,
            json: async () => [{ id: 1, name: "Local Docker Host", hostname: null, is_local: true, created_at: new Date().toISOString() }],
          });
        }
        if (url.includes("/events")) {
          return Promise.resolve({
            ok: true,
            json: async () => [
              {
                id: 1,
                timestamp: new Date().toISOString(),
                severity: "INFO",
                category: "DOCKER",
                source_type: "container",
                source_id: "abc123",
                source_name: "jellyfin",
                title: "Container started",
                description: null,
                event_metadata: null,
                created_at: new Date().toISOString(),
              },
            ],
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({
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
          }),
        });
      })
    );

    render(
      <MemoryRouter initialEntries={["/containers/abc123"]}>
        <Routes>
          <Route path="/containers/:containerId" element={<ContainerDetail />} />
        </Routes>
      </MemoryRouter>
    );

    expect(await screen.findByText("jellyfin")).toBeInTheDocument();
    expect(await screen.findByText("Container started")).toBeInTheDocument();
  });
});
