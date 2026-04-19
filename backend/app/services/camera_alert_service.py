import time


def build_camera_alerts(
    source_stats: list[dict[str, object]],
    max_read_latency_ms: float = 350.0,
    max_detection_staleness_seconds: float = 8.0,
) -> list[dict[str, object]]:
    now = time.time()
    alerts: list[dict[str, object]] = []

    for stats in source_stats:
        source = str(stats.get("source", "unknown"))
        has_frame = bool(stats.get("has_frame"))
        last_error = stats.get("last_error")
        read_ms = float(stats.get("last_read_duration_ms") or 0.0)
        last_detection_at = stats.get("last_detection_at")

        if last_error or not has_frame:
            alerts.append(
                {
                    "source": source,
                    "level": "critical",
                    "type": "camera_down",
                    "message": str(last_error or "No frame available"),
                }
            )

        if read_ms > max_read_latency_ms:
            alerts.append(
                {
                    "source": source,
                    "level": "warning",
                    "type": "high_read_latency",
                    "message": f"Read latency {round(read_ms, 2)}ms > {max_read_latency_ms}ms",
                }
            )

        if last_detection_at:
            staleness = now - float(last_detection_at)
            if staleness > max_detection_staleness_seconds:
                alerts.append(
                    {
                        "source": source,
                        "level": "warning",
                        "type": "detection_stale",
                        "message": (
                            f"Last detection is stale ({round(staleness, 1)}s)"
                        ),
                    }
                )

    return alerts
