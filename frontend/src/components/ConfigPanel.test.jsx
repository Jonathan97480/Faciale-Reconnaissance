import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConfigPanel from "./ConfigPanel";

const configState = {
  config: {
    detection_interval_seconds: 3,
    match_threshold: 0.6,
    match_margin_threshold: 0.03,
    camera_index: 0,
    camera_source: "",
    network_camera_sources: ["rtsp://cam-1/stream"],
    network_camera_profiles: [],
    multi_camera_cycle_budget_seconds: 2,
    network_camera_retry_base_seconds: 0.5,
    network_camera_retry_max_seconds: 8,
    unstable_source_failure_threshold: 3,
    unstable_source_cycle_skip: 1,
    hls_proxy_max_sessions: 2,
    hls_proxy_idle_ttl_seconds: 30,
    enroll_frames_count: 5,
    face_crop_padding_ratio: 0.2,
    inference_device_preference: "auto",
    inference_device_active: "cpu",
    production_api_rate_limit_window_seconds: 60,
    production_api_rate_limit_max_requests: 30,
  },
  loading: false,
  error: "",
  saveConfig: vi.fn(),
};

vi.mock("../context/ConfigContext", () => ({
  useConfig: () => configState,
}));

describe("ConfigPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    configState.loading = false;
    configState.error = "";
    configState.saveConfig.mockResolvedValue(configState.config);
  });

  it("adds a network source and persists the updated config", async () => {
    render(<ConfigPanel />);

    await userEvent.type(
      screen.getByPlaceholderText("rtsp://..., http://..., fichier video..."),
      "http://cam-2/live.mjpg"
    );
    await userEvent.click(screen.getByRole("button", { name: "Ajouter flux" }));

    await waitFor(() =>
      expect(configState.saveConfig).toHaveBeenCalledWith(
        expect.objectContaining({
          network_camera_sources: [
            "rtsp://cam-1/stream",
            "http://cam-2/live.mjpg",
          ],
        })
      )
    );

    expect(screen.getByText("Flux reseau ajoute.")).toBeInTheDocument();
  });

  it("rejects an invalid camera profile before saving", async () => {
    render(<ConfigPanel />);

    await userEvent.click(
      screen.getByRole("button", { name: "Ajouter profil camera" })
    );

    expect(configState.saveConfig).not.toHaveBeenCalled();
    expect(
      screen.getByText("Nom et host requis pour le profil camera.")
    ).toBeInTheDocument();
  });
});
