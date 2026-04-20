import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MonitoringRuntimeMetricsPanel from "./MonitoringRuntimeMetricsPanel";

describe("MonitoringRuntimeMetricsPanel", () => {
  it("renders runtime metrics and degraded sources", () => {
    render(
      <MonitoringRuntimeMetricsPanel
        captureSettings={{ detection_interval_seconds: 3 }}
        localRuntime={{
          last_read_duration_ms: 18.4,
          latest_frame_at: 1710000000,
          last_detection_at: 1710000001,
          consecutive_failures: 0,
          last_error: null,
        }}
        networkSources={[
          {
            source: "rtsp://cam-1",
            last_read_duration_ms: 220.5,
            latest_frame_age_seconds: 4.3,
            retry_delay_seconds: 2,
            consecutive_failures: 5,
            last_error: "timeout",
          },
        ]}
        performance={{
          capture_ms: 12.3,
          decode_ms: 5.1,
          extract_ms: 18.8,
          matching_ms: 6.2,
          db_ms: 2.9,
          cycle_ms: 41.7,
          processed_sources: 2,
          results_count: 1,
          skipped_stale_sources: 1,
          skipped_unstable_sources: 2,
          updated_at: 1710000002,
        }}
      />
    );

    expect(screen.getByText("Metriques runtime")).toBeInTheDocument();
    expect(screen.getByText("Capture: 12.3 ms")).toBeInTheDocument();
    expect(screen.getByText("Decode: 5.1 ms")).toBeInTheDocument();
    expect(screen.getByText("Instables sautees: 2")).toBeInTheDocument();
    expect(screen.getByText("rtsp://cam-1")).toBeInTheDocument();
    expect(screen.getByText("fails=5")).toBeInTheDocument();
    expect(screen.getByText("timeout")).toBeInTheDocument();
  });
});
