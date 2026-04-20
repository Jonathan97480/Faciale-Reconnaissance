import { describe, expect, it } from "vitest";

import {
  createEmptyCameraProfile,
  normalizeCameraProfile,
  toConfigPayload,
} from "./configPanelUtils";

describe("configPanelUtils", () => {
  it("creates an empty camera profile with expected defaults", () => {
    expect(createEmptyCameraProfile()).toEqual({
      name: "",
      protocol: "rtsp",
      host: "",
      port: 554,
      path: "/stream1",
      username: "",
      password: "",
      onvif_url: "",
      enabled: true,
    });
  });

  it("normalizes config payload values and removes duplicate network sources", () => {
    const payload = toConfigPayload({
      detection_interval_seconds: "3",
      match_threshold: "0.6",
      match_margin_threshold: "0.05",
      camera_index: "1",
      camera_source: "",
      network_camera_sources: [" rtsp://cam-1 ", "rtsp://cam-1", "", "rtsp://cam-2"],
      network_camera_profiles: [
        {
          name: " Main ",
          protocol: "rtsp",
          host: " cam.local ",
          port: "8554",
          path: "",
          username: "admin",
          password: "secret",
          onvif_url: "",
          enabled: 1,
        },
        {
          name: "",
          protocol: "rtsp",
          host: "",
          port: "554",
          path: "/",
          username: "",
          password: "",
          onvif_url: "",
          enabled: true,
        },
      ],
      multi_camera_cycle_budget_seconds: "2",
      network_camera_retry_base_seconds: "0.5",
      network_camera_retry_max_seconds: "8",
      enroll_frames_count: "5",
      face_crop_padding_ratio: "0.2",
      inference_device_preference: "auto",
      production_api_rate_limit_window_seconds: "60",
      production_api_rate_limit_max_requests: "30",
    });

    expect(payload.network_camera_sources).toEqual([
      "rtsp://cam-1",
      "rtsp://cam-2",
    ]);
    expect(payload.network_camera_profiles).toEqual([
      {
        name: "Main",
        protocol: "rtsp",
        host: "cam.local",
        port: 8554,
        path: "",
        username: "admin",
        password: "secret",
        onvif_url: "",
        enabled: true,
      },
    ]);
    expect(payload.match_margin_threshold).toBe(0.05);
    expect(payload.network_camera_retry_base_seconds).toBe(0.5);
    expect(payload.network_camera_retry_max_seconds).toBe(8);
  });

  it("normalizes a single camera profile", () => {
    expect(
      normalizeCameraProfile({
        name: "  Cam A ",
        host: " 10.0.0.8 ",
        path: "",
        port: "8080",
      })
    ).toEqual({
      name: "Cam A",
      host: "10.0.0.8",
      path: "/",
      port: 8080,
    });
  });
});
