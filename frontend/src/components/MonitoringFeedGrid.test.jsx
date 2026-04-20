import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import MonitoringFeedGrid from "./MonitoringFeedGrid";

vi.mock("../api/client", () => ({
  apiClient: {
    getRecognitionPreviewStreamUrl: () => "/api/recognition/preview/stream",
    getNetworkPreviewStreamUrl: (source) =>
      `/api/recognition/network-preview/stream?source=${encodeURIComponent(source)}`,
  },
}));

describe("MonitoringFeedGrid", () => {
  it("selects a side feed when the card is clicked", async () => {
    const setMainFeedKey = vi.fn();

    render(
      <MonitoringFeedGrid
        feedStatus={{}}
        localRuntime={{ has_frame: true, last_error: null, last_read_duration_ms: 12 }}
        removeNetworkFeed={vi.fn()}
        setFeedStatus={vi.fn()}
        setMainFeedKey={setMainFeedKey}
        sideFeeds={[
          {
            key: "network:rtsp://cam-1",
            label: "Flux reseau #1",
            type: "network",
            source: "rtsp://cam-1",
          },
        ]}
        sourceRuntimeMap={{
          "rtsp://cam-1": {
            has_frame: false,
            last_error: "timeout",
            last_read_duration_ms: 420,
          },
        }}
      />
    );

    await userEvent.click(screen.getByRole("button", { name: /Flux reseau #1/i }));

    expect(setMainFeedKey).toHaveBeenCalledWith("network:rtsp://cam-1");
    expect(screen.getByText("indisponible")).toBeInTheDocument();
    expect(screen.getByText("Erreur: timeout")).toBeInTheDocument();
  });

  it("removes a network feed without switching the main feed", async () => {
    const setMainFeedKey = vi.fn();
    const removeNetworkFeed = vi.fn();

    render(
      <MonitoringFeedGrid
        feedStatus={{}}
        localRuntime={null}
        removeNetworkFeed={removeNetworkFeed}
        setFeedStatus={vi.fn()}
        setMainFeedKey={setMainFeedKey}
        sideFeeds={[
          {
            key: "network:rtsp://cam-2",
            label: "Flux reseau #2",
            type: "network",
            source: "rtsp://cam-2",
          },
        ]}
        sourceRuntimeMap={{}}
      />
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Supprimer flux" })
    );

    expect(removeNetworkFeed).toHaveBeenCalledWith("rtsp://cam-2");
    expect(setMainFeedKey).not.toHaveBeenCalled();
  });
});
