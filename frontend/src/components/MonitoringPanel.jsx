import { useEffect, useRef, useState } from "react";

import { apiClient } from "../api/client";

export default function MonitoringPanel() {
  const [result, setResult] = useState(null);
  const [imageAnalysis, setImageAnalysis] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [latestDetection, setLatestDetection] = useState(null);
  const [history, setHistory] = useState([]);
  const [loopState, setLoopState] = useState(null);
  const [runtimeConfig, setRuntimeConfig] = useState(null);
  const [status, setStatus] = useState("");
  const [cameraStatus, setCameraStatus] = useState("Apercu flux actif.");
  const [feedStatus, setFeedStatus] = useState({});
  const [mainFeedKey, setMainFeedKey] = useState("local");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const streamWrapRef = useRef(null);

  const refreshLoopState = async () => {
    try {
      const response = await apiClient.getLoopStatus();
      setLoopState(response);
    } catch {
      setStatus("Echec de lecture de l'etat runtime.");
    }
  };

  const refreshLatestDetection = async () => {
    try {
      const response = await apiClient.getLatestDetection();
      setLatestDetection(response.detection ?? null);
    } catch {
      setStatus("Echec de lecture de la derniere detection.");
    }
  };

  const refreshHistory = async () => {
    try {
      const response = await apiClient.getDetectionHistory(10);
      setHistory(response.detections ?? []);
    } catch {
      setStatus("Echec de lecture de l'historique.");
    }
  };

  const refreshConfig = async () => {
    try {
      const response = await apiClient.getConfig();
      setRuntimeConfig(response);
    } catch {
      setStatus("Echec de lecture de la configuration runtime.");
    }
  };

  useEffect(() => {
    refreshLoopState();
    refreshConfig();
    refreshLatestDetection();
    refreshHistory();

    const timer = setInterval(() => {
      refreshLoopState();
      refreshConfig();
      refreshLatestDetection();
      refreshHistory();
    }, 3000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", onFullscreenChange);
  }, []);

  const runCheck = async () => {
    setStatus("Detection en cours...");
    try {
      const response = await apiClient.checkRecognition({ embedding: null });
      setResult(response);
      setStatus("Detection terminee.");
      await refreshLoopState();
    } catch {
      setStatus("Echec de detection.");
    }
  };

  const runImageAnalysis = async () => {
    if (!selectedImage) {
      setStatus("Selectionnez une image avant analyse.");
      return;
    }
    setStatus("Analyse image en cours...");
    try {
      const response = await apiClient.analyzeImageFile(selectedImage);
      setImageAnalysis(response);
      setStatus("Analyse image terminee.");
    } catch {
      setStatus("Echec de l'analyse image.");
    }
  };

  const toggleFullscreen = async () => {
    const target = streamWrapRef.current;
    if (!target) {
      return;
    }
    if (!document.fullscreenElement) {
      try {
        await target.requestFullscreen();
      } catch {
        setStatus("Le mode plein ecran n'est pas disponible sur ce navigateur.");
      }
      return;
    }
    await document.exitFullscreen();
  };

  const detectedFaces = latestDetection?.faces ?? [];
  const hasUnknownFace = detectedFaces.some((face) => face.status === "inconnu");
  const networkSources = runtimeConfig?.network_camera_sources ?? [];
  const allFeeds = [
    { key: "local", label: "Camera locale", type: "local", source: "" },
    ...networkSources.map((source, index) => ({
      key: `network:${source}`,
      label: `Flux reseau #${index + 1}`,
      type: "network",
      source,
    })),
  ];
  const currentMainFeed = allFeeds.find((feed) => feed.key === mainFeedKey) || allFeeds[0];
  const sideFeeds = allFeeds.filter((feed) => feed.key !== currentMainFeed.key);

  useEffect(() => {
    if (!allFeeds.some((feed) => feed.key === mainFeedKey)) {
      setMainFeedKey("local");
    }
  }, [mainFeedKey, allFeeds]);

  const mainFeedUrl =
    currentMainFeed.type === "local"
      ? apiClient.getRecognitionPreviewStreamUrl()
      : apiClient.getNetworkPreviewStreamUrl(currentMainFeed.source);

  return (
    <section className="panel">
      {hasUnknownFace && (
        <div className="alert-banner" role="alert">
          ALERTE: VISAGE INCONNU DETECTE
        </div>
      )}
      <h2>Monitoring</h2>
      <div className={`stream-wrap ${isFullscreen ? "fullscreen" : ""}`} ref={streamWrapRef}>
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
        <div className="hud-overlay">
          <div className="hud-corners" />
          <div className="hud-topline">TACTICAL IDENT / {currentMainFeed.label.toUpperCase()}</div>
          <div className="hud-meta">
            <span>FACES: {detectedFaces.length}</span>
            <span>LOOP: {loopState?.loop?.running ? "RUNNING" : "STOPPED"}</span>
            <span>UNKNOWN: {hasUnknownFace ? "YES" : "NO"}</span>
          </div>
        </div>
      </div>
      <p className={`status-line ${cameraStatus.includes("actif") ? "ok" : "warn"}`}>{cameraStatus}</p>
      <section className="history-panel">
        <h3>Grille des flux configures</h3>
        {sideFeeds.length === 0 && (
          <p className="status-line">Aucun flux secondaire disponible.</p>
        )}
        {sideFeeds.length > 0 && (
          <div className="stream-grid">
            {sideFeeds.map((feed) => {
              const streamIsOk = feedStatus[feed.key] !== false;
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
                  <p className="stream-source">{feed.type === "local" ? "camera locale" : feed.source}</p>
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
        )}
      </section>
      <div className="button-row">
        <button onClick={runCheck}>Lancer verification manuelle</button>
        <button onClick={toggleFullscreen}>{isFullscreen ? "Quitter plein ecran" : "Plein ecran HUD"}</button>
        <button
          onClick={async () => {
            await refreshLoopState();
            await refreshConfig();
            await refreshLatestDetection();
            await refreshHistory();
          }}
        >
          Rafraichir etat loop
        </button>
      </div>
      <p className="status-line">{status}</p>
      <section className="history-panel">
        <h3>Analyse d'image (API)</h3>
        <div className="button-row">
          <input
            type="file"
            accept="image/*"
            onChange={(event) => setSelectedImage(event.target.files?.[0] ?? null)}
          />
          <button onClick={runImageAnalysis}>Analyser image</button>
        </div>
        {imageAnalysis?.faces?.length > 0 && (
          <div className="crop-grid">
            {imageAnalysis.faces.map((face, index) => (
              <article key={`crop-${index}`} className="crop-card">
                {face.face_image_base64 ? (
                  <img
                    src={`data:image/jpeg;base64,${face.face_image_base64}`}
                    alt={`Visage detecte ${index + 1}`}
                  />
                ) : (
                  <div className="crop-missing">Crop indisponible</div>
                )}
                <div>
                  <strong>{face.face_name || `Inconnu #${index + 1}`}</strong>
                  <div>Statut: {face.status}</div>
                  <div>
                    Score: {typeof face.score === "number" ? `${(face.score * 100).toFixed(1)}%` : "--"}
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
        {imageAnalysis && (
          <pre className="block-json">{JSON.stringify(imageAnalysis, null, 2)}</pre>
        )}
      </section>
      {detectedFaces.length > 0 && (
        <ul className="face-list">
          {detectedFaces.map((face, index) => {
            const name = face.face_name || `Inconnu #${index + 1}`;
            const score =
              typeof face.score === "number"
                ? `${(face.score * 100).toFixed(1)}%`
                : "--";
            return (
              <li className="face-row" key={`${name}-${index}`}>
                <div>
                  <strong>{name}</strong>
                  <div>Confiance: {score}</div>
                </div>
                <span className={`badge ${face.status === "reconnu" ? "ok" : "warn"}`}>
                  {face.status}
                </span>
              </li>
            );
          })}
        </ul>
      )}
      <section className="history-panel">
        <h3>Historique live (10 dernieres detections)</h3>
        {history.length === 0 && <p className="status-line">Aucune detection enregistree.</p>}
        {history.length > 0 && (
          <ul className="history-list">
            {history.map((entry) => {
              const time = new Date(entry.created_at).toLocaleTimeString("fr-FR", {
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              });
              const unknownCount = (entry.faces || []).filter((face) => face.status === "inconnu").length;
              return (
                <li key={entry.id} className="history-row">
                  <span>{time}</span>
                  <span>Faces: {entry.faces_count}</span>
                  <span>{unknownCount > 0 ? `Inconnus: ${unknownCount}` : "0 inconnu"}</span>
                </li>
              );
            })}
          </ul>
        )}
      </section>
      {loopState && (
        <pre className="block-json">{JSON.stringify(loopState, null, 2)}</pre>
      )}
      {latestDetection && (
        <pre className="block-json">
          {JSON.stringify(latestDetection, null, 2)}
        </pre>
      )}
      {result && (
        <pre className="block-json">{JSON.stringify(result, null, 2)}</pre>
      )}
    </section>
  );
}
