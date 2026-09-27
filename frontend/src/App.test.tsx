import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the LabPulse header", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.includes("/containers") || url.includes("/events") || url.includes("/metrics")) {
          return Promise.resolve({ ok: true, json: async () => [] });
        }
        if (url.includes("/stats")) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              total_containers: 0,
              healthy: 0,
              warning: 0,
              critical: 0,
              recent_errors: 0,
            }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: async () => ({
            status: "ok",
            app: "LabPulse",
            version: "0.1.0",
            database: "ok",
            timestamp: new Date().toISOString(),
          }),
        });
      })
    );

    render(<App />);

    expect(screen.getByText("LabPulse")).toBeInTheDocument();
    expect(await screen.findByText("Online")).toBeInTheDocument();
  });
});
