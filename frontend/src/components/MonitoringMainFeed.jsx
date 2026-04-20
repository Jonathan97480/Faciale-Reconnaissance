export default function MonitoringMainFeed({
  currentMainFeed,
  detectedFaces,
  hasUnknownFace,
  isFullscreen,
  loopRunning,
  mainFeedUrl,
  setAudioEnabled,
  setCameraStatus,
  setFeedStatus,
  streamWrapRef,
  useNetworkVideoElement,
}) {
  return (
    <div className={`stream-wrap ${isFullscreen ? "fullscreen" : ""}`} ref={streamWrapRef}>
      {useNetworkVideoElement ? (
        <video
          src={currentMainFeed.source}
          autoPlay
          playsInline
          muted={false}
          onError={() => {
            setFeedStatus((prev) => ({ ...prev, [currentMainFeed.key]: false }));
            setAudioEnabled(false);
            setCameraStatus(
              `Audio non supporte par ce flux (${currentMainFeed.label}). Retour en mode preview.`
            );
          }}
          onLoadedData={() => {
            setFeedStatus((prev) => ({ ...prev, [currentMainFeed.key]: true }));
            setCameraStatus(`Flux principal actif (${currentMainFeed.label}).`);
          }}
        />
      ) : (
        <img
          src={mainFeedUrl}
          alt={`Apercu ${currentMainFeed.label}`}
          onError={() => {
            setFeedStatus((prev) => ({ ...prev, [currentMainFeed.key]: false }));
            setCameraStatus(`Flux principal indisponible (${currentMainFeed.label}).`);
          }}
          onLoad={() => {
            setFeedStatus((prev) => ({ ...prev, [currentMainFeed.key]: true }));
            setCameraStatus(`Flux principal actif (${currentMainFeed.label}).`);
          }}
        />
      )}
      <div className="hud-overlay">
        <div className="hud-corners" />
        <div className="hud-topline">TACTICAL IDENT / {currentMainFeed.label.toUpperCase()}</div>
        <div className="hud-meta">
          <span>FACES: {detectedFaces.length}</span>
          <span>LOOP: {loopRunning ? "RUNNING" : "STOPPED"}</span>
          <span>UNKNOWN: {hasUnknownFace ? "YES" : "NO"}</span>
        </div>
      </div>
    </div>
  );
}
