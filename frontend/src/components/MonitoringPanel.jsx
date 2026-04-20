import { useEffect, useRef, useState } from "react";

import { apiClient } from "../api/client";
import { useConfig } from "../context/ConfigContext";

export default function MonitoringPanel() {
  const { config } = useConfig();
  const [result, setResult] = useState(null);
  const [imageAnalysis, setImageAnalysis] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [latestDetection, setLatestDetection] = useState(null);
  const [history, setHistory] = useState([]);
  const [cameraAlerts, setCameraAlerts] = useState([]);
  const [loopState, setLoopState] = useState(null);
  const [status, setStatus] = useState("");
  const [cameraStatus, setCameraStatus] = useState("Apercu flux actif.");
  const [feedStatus, setFeedStatus] = useState({});
  const [audioEnabled, setAudioEnabled] = useState(false);
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

  const refreshCameraAlerts = async () => {
    try {
      const response = await apiClient.getCameraAlerts();
      setCameraAlerts(response.alerts ?? []);
    } catch {
      setStatus("Echec de lecture des alertes camera.");
    }
  };

  const buildConfigPayload = (state) => ({
    detection_interval_seconds: Number(state?.detection_interval_seconds ?? 3),
    match_threshold: Number(state?.match_threshold ?? 0.6),
    camera_index: Number(state?.camera_index ?? 0),
    camera_source: String(state?.camera_source ?? ""),
    network_camera_sources: (state?.network_camera_sources ?? [])
      .map((source) => String(source).trim())
      .filter((source, index, arr) => source && arr.indexOf(source) === index)
      .slice(0, 10),
    network_camera_profiles: (state?.network_camera_profiles ?? [])
      .map((profile) => ({
        ...profile,
        name: String(profile.name ?? "").trim(),
        host: String(profile.host ?? "").trim(),
        path: String(profile.path ?? "/"),
        username: String(profile.username ?? ""),
        password: String(profile.password ?? ""),
        onvif_url: String(profile.onvif_url ?? ""),
        port: Number(profile.port ?? 554),
        enabled: Boolean(profile.enabled),
      }))
      .filter((profile) => profile.name && profile.host)
      .slice(0, 10),
    multi_camera_cycle_budget_seconds: Number(state?.multi_camera_cycle_budget_seconds ?? 2),
    enroll_frames_count: Number(state?.enroll_frames_count ?? 5),
    face_crop_padding_ratio: Number(state?.face_crop_padding_ratio ?? 0.2),
    inference_device_preference: String(state?.inference_device_preference ?? "auto"),
  });

  const removeNetworkFeed = async (sourceToRemove) => {
    setStatus("Suppression du flux reseau...");
    try {
      const freshConfig = await apiClient.getConfig();
      const next = {
        ...freshConfig,
        network_camera_sources: (freshConfig.network_camera_sources ?? []).filter(
          (source) => source !== sourceToRemove
        ),
      };
      await apiClient.updateConfig(buildConfigPayload(next));
      await refreshLoopState();
      setStatus(`Flux reseau supprime: ${sourceToRemove}`);
    } catch (err) {
      setStatus("Echec suppression flux reseau.");
    }
  };

  useEffect(() => {
    refreshLoopState();
    refreshLatestDetection();
    refreshHistory();
    refreshCameraAlerts();

    const timer = setInterval(() => {
      refreshLoopState();
      refreshLatestDetection();
      refreshHistory();
      refreshCameraAlerts();
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
  const networkSources =
    config?.network_camera_sources ?? [];
  const sourceRuntimeMap = Object.fromEntries(
    (loopState?.network_cameras?.sources ?? []).map((item) => [item.source, item])
  );
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

  useEffect(() => {
    if (currentMainFeed.type !== "network" && audioEnabled) {
      setAudioEnabled(false);
    }
  }, [currentMainFeed.type, audioEnabled]);

  const mainFeedUrl =
    currentMainFeed.type === "local"
      ? apiClient.getRecognitionPreviewStreamUrl()
      : apiClient.getNetworkPreviewStreamUrl(currentMainFeed.source);
  const useNetworkVideoElement = currentMainFeed.type === "network" && audioEnabled;

  return (
    <section className="panel">
      {hasUnknownFace && (
        <div className="alert-banner" role="alert">
          ALERTE: VISAGE INCONNU DETECTE
        </div>
      )}
      <h2>Monitoring</h2>
      <div className={`stream-wrap ${isFullscreen ? "fullscreen" : ""}`} ref={streamWrapRef}>
        {useNetworkVideoElement ? (
          <video
            src={currentMainFeed.source}
            autoPlay
            playsInline
            muted={!audioEnabled}
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
            <span>LOOP: {loopState?.loop?.running ? "RUNNING" : "STOPPED"}</span>
            <span>UNKNOWN: {hasUnknownFace ? "YES" : "NO"}</span>
          </div>
        </div>
      </div>
      <p className={`status-line ${cameraStatus.includes("actif") ? "ok" : "warn"}`}>{cameraStatus}</p>
      <section className="history-panel">
        <h3>Alertes camera</h3>
        {cameraAlerts.length === 0 && (
          <p className="status-line ok">Aucune alerte camera.</p>
        )}
        {cameraAlerts.length > 0 && (
          <ul className="history-list">
            {cameraAlerts.slice(0, 10).map((alert, index) => (
              <li key={`${alert.source}-${alert.type}-${index}`} className="history-row">
                <span>{alert.level}</span>
                <span>{alert.type}</span>
                <span>{alert.source}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="history-panel">
        <h3>Grille des flux configures</h3>
        {sideFeeds.length === 0 && (
          <p className="status-line">Aucun flux secondaire disponible.</p>
        )}
        {sideFeeds.length > 0 && (
          <div className="stream-grid">
            {sideFeeds.map((feed) => {
              const runtime = feed.type === "network" ? sourceRuntimeMap[feed.source] : null;
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
                  <p className="stream-source">{feed.type === "local" ? "camera locale" : feed.source}</p>
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
        )}
      </section>
      <div className="button-row">
        <button onClick={runCheck}>Lancer verification manuelle</button>
        {currentMainFeed.type === "network" && (
          <button onClick={() => setAudioEnabled((prev) => !prev)}>
            {audioEnabled ? "Couper son" : "Activer son"}
          </button>
        )}
        <button onClick={toggleFullscreen}>{isFullscreen ? "Quitter plein ecran" : "Plein ecran HUD"}</button>
        <button
          onClick={async () => {
            await refreshLoopState();
            await refreshLatestDetection();
            await refreshHistory();
            await refreshCameraAlerts();
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
