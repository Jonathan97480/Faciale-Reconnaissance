import MonitoringHistoryPanel from "./MonitoringHistoryPanel";

function formatMetric(value, suffix = "") {
  return typeof value === "number" ? `${value.toFixed(1)}${suffix}` : "--";
}

function formatInteger(value) {
  return typeof value === "number" ? String(value) : "--";
}

function formatTimestamp(value) {
  if (typeof value !== "number") {
    return "--";
  }
  return new Date(value * 1000).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function MonitoringRuntimeMetricsPanel({
  captureSettings,
  localRuntime,
  networkSources,
  performance,
}) {
  const highlightedSources = networkSources
    .filter(
      (source) =>
        source.last_error ||
        (typeof source.consecutive_failures === "number" &&
          source.consecutive_failures > 0)
    )
    .slice(0, 5);

  return (
    <MonitoringHistoryPanel title="Metriques runtime">
      <div className="metrics-grid">
        <article className="metric-card">
          <strong>Cycle detection</strong>
          <div className="metric-list">
            <span>Capture: {formatMetric(performance?.capture_ms, " ms")}</span>
            <span>Decode: {formatMetric(performance?.decode_ms, " ms")}</span>
            <span>Extract: {formatMetric(performance?.extract_ms, " ms")}</span>
            <span>Matching: {formatMetric(performance?.matching_ms, " ms")}</span>
            <span>DB: {formatMetric(performance?.db_ms, " ms")}</span>
            <span>Cycle total: {formatMetric(performance?.cycle_ms, " ms")}</span>
          </div>
        </article>

        <article className="metric-card">
          <strong>Charge courante</strong>
          <div className="metric-list">
            <span>Sources traitees: {formatInteger(performance?.processed_sources)}</span>
            <span>Resultats: {formatInteger(performance?.results_count)}</span>
            <span>
              Stale sautees: {formatInteger(performance?.skipped_stale_sources)}
            </span>
            <span>
              Instables sautees: {formatInteger(performance?.skipped_unstable_sources)}
            </span>
            <span>
              Detection intervalle:{" "}
              {formatMetric(captureSettings?.detection_interval_seconds, " s")}
            </span>
            <span>Maj: {formatTimestamp(performance?.updated_at)}</span>
          </div>
        </article>

        <article className="metric-card">
          <strong>Camera locale</strong>
          <div className="metric-list">
            <span>Read: {formatMetric(localRuntime?.last_read_duration_ms, " ms")}</span>
            <span>
              Derniere frame: {formatTimestamp(localRuntime?.latest_frame_at)}
            </span>
            <span>
              Derniere detection: {formatTimestamp(localRuntime?.last_detection_at)}
            </span>
            <span>
              Erreurs consecutives: {formatInteger(localRuntime?.consecutive_failures)}
            </span>
            <span>Etat: {localRuntime?.last_error || "actif"}</span>
          </div>
        </article>
      </div>

      {highlightedSources.length === 0 && (
        <p className="status-line ok">Aucune source reseau degradee.</p>
      )}

      {highlightedSources.length > 0 && (
        <ul className="history-list">
          {highlightedSources.map((source) => (
            <li key={source.source} className="history-row history-row-runtime">
              <span>{source.source}</span>
              <span>read={formatMetric(source.last_read_duration_ms, " ms")}</span>
              <span>
                age={formatMetric(source.latest_frame_age_seconds, " s")}
              </span>
              <span>
                retry={formatMetric(source.retry_delay_seconds, " s")}
              </span>
              <span>fails={formatInteger(source.consecutive_failures)}</span>
              <span>{source.last_error || "instable"}</span>
            </li>
          ))}
        </ul>
      )}
    </MonitoringHistoryPanel>
  );
}
