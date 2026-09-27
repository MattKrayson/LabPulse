import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import WhatChanged from "./WhatChanged";

describe("WhatChanged", () => {
  it("shows a loading state then renders changes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve({
          ok: true,
          json: async () => [
            {
              container_id: "abc123",
              type: "restarted",
              description: "jellyfin restarted 2 times",
              detail: "Total restart count: 2",
            },
          ],
        })
      )
    );

    render(
      <MemoryRouter>
        <WhatChanged />
      </MemoryRouter>
    );

    expect(screen.getByText("Comparing state…")).toBeInTheDocument();
    expect(await screen.findByText("jellyfin restarted 2 times")).toBeInTheDocument();
    expect(await screen.findByText("Total restart count: 2")).toBeInTheDocument();
  });

  it("shows an empty state when there are no changes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve({ ok: true, json: async () => [] }))
    );

    render(
      <MemoryRouter>
        <WhatChanged />
      </MemoryRouter>
    );

    expect(
      await screen.findByText("No meaningful changes detected in the selected window.")
    ).toBeInTheDocument();
  });

  it("shows an error state when the API is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new Error("network error")))
    );

    render(
      <MemoryRouter>
        <WhatChanged />
      </MemoryRouter>
    );

    await waitFor(() =>
      expect(screen.getByText("Unable to reach the LabPulse API.")).toBeInTheDocument()
    );
  });
});
