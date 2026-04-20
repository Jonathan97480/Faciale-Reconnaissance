import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import MonitoringMainFeed from "./MonitoringMainFeed";

describe("MonitoringMainFeed", () => {
  it("marks the image preview as active when it loads", () => {
    const setFeedStatus = vi.fn();
    const setCameraStatus = vi.fn();

    render(
      <MonitoringMainFeed
        currentMainFeed={{
          key: "local",
          label: "Camera locale",
          type: "local",
          source: "",
        }}
        detectedFaces={[]}
        hasUnknownFace={false}
        isFullscreen={false}
        mainFeedRuntime={{ has_frame: true, last_error: null }}
        loopRunning
        mainFeedUrl="/api/recognition/preview/stream"
        setAudioEnabled={vi.fn()}
        setCameraStatus={setCameraStatus}
        setFeedStatus={setFeedStatus}
        streamWrapRef={{ current: null }}
        useNetworkVideoElement={false}
      />
    );

    fireEvent.load(screen.getByAltText("Apercu Camera locale"));

    expect(setFeedStatus).toHaveBeenCalled();
    expect(setCameraStatus).toHaveBeenCalledWith(
      "Flux principal actif (Camera locale)."
    );
    expect(screen.getByText("FEED: LIVE")).toBeInTheDocument();
  });

  it("falls back to preview mode when network audio playback fails", () => {
    const setFeedStatus = vi.fn();
    const setCameraStatus = vi.fn();
    const setAudioEnabled = vi.fn();

    const { container } = render(
      <MonitoringMainFeed
        currentMainFeed={{
          key: "network:rtsp://cam-1",
          label: "Flux reseau #1",
          type: "network",
          source: "http://cam-1/index.m3u8",
        }}
        detectedFaces={[{ status: "inconnu" }]}
        hasUnknownFace
        isFullscreen={false}
        mainFeedRuntime={{ has_frame: false, last_error: "audio error" }}
        loopRunning={false}
        mainFeedUrl=""
        setAudioEnabled={setAudioEnabled}
        setCameraStatus={setCameraStatus}
        setFeedStatus={setFeedStatus}
        streamWrapRef={{ current: null }}
        useNetworkVideoElement
      />
    );

    fireEvent.error(container.querySelector("video"));

    expect(setFeedStatus).toHaveBeenCalled();
    expect(setAudioEnabled).toHaveBeenCalledWith(false);
    expect(setCameraStatus).toHaveBeenCalledWith(
      "Audio non supporte par ce flux (Flux reseau #1). Retour en mode preview."
    );
    expect(screen.getByText("UNKNOWN: YES")).toBeInTheDocument();
    expect(screen.getByText("LOOP: STOPPED")).toBeInTheDocument();
  });
});
