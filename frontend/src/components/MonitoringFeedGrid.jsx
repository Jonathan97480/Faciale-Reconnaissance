import { apiClient } from "../api/client";

export default function MonitoringFeedGrid({
  feedStatus,
  removeNetworkFeed,
  setFeedStatus,
  setMainFeedKey,
  sideFeeds,
  sourceRuntimeMap,
}) {
  if (sideFeeds.length === 0) {
    return <p className="status-line">Aucun flux secondaire disponible.</p>;
  }

  return (
    <div className="stream-grid">
      {sideFeeds.map((feed) => {
        const runtime =
          feed.type === "network" ? sourceRuntimeMap[feed.source] : null;
        const streamIsOk =
          feed.type === "network"
            ? Boolean(runtime?.has_frame) && !runtime?.last_error
            : feedStatus[feed.key] !== false;
        const feedUrl =
          feed.type === "local"
            ? apiClient.getRecognitionPreviewStreamUrl()
            : apiClient.getNetworkPreviewStreamUrl(feed.source);

        return (
          <article
            key={feed.key}
            className="stream-card"
            role="button"
            tabIndex={0}
            onClick={() => setMainFeedKey(feed.key)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                setMainFeedKey(feed.key);
              }
            }}
          >
            <div className="stream-card-head">
              <strong>{feed.label}</strong>
              <span className={`badge ${streamIsOk ? "ok" : "warn"}`}>
                {streamIsOk ? "actif" : "indisponible"}
              </span>
            </div>
            {feed.type === "network" && (
              <div className="button-row" style={{ marginTop: 6 }}>
                <button
                  type="button"
                  onMouseDown={(event) => {
                    event.preventDefault();
                    event.stopPropagation();
                  }}
                  onClick={(event) => {
                    event.stopPropagation();
                    removeNetworkFeed(feed.source);
                  }}
                >
                  Supprimer flux
                </button>
              </div>
            )}
            <p className="stream-source">
              {feed.type === "local" ? "camera locale" : feed.source}
            </p>
            {feed.type === "network" && runtime && (
              <p className="stream-source">
                {runtime.last_error
                  ? `Erreur: ${runtime.last_error}`
                  : runtime.has_frame
                    ? `OK | read=${runtime.last_read_duration_ms}ms`
                    : "Initialisation flux..."}
              </p>
            )}
            <div className="stream-mini-wrap">
              <img
                src={feedUrl}
                alt={`Apercu ${feed.label}`}
                onLoad={() =>
                  setFeedStatus((prev) => ({ ...prev, [feed.key]: true }))
                }
                onError={() =>
                  setFeedStatus((prev) => ({ ...prev, [feed.key]: false }))
                }
              />
            </div>
          </article>
        );
      })}
    </div>
  );
}
