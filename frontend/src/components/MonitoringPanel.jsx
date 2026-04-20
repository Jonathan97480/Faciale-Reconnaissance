import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import { apiClient } from "../api/client";
import { useConfig } from "../context/ConfigContext";
import MonitoringFeedGrid from "./MonitoringFeedGrid";
import MonitoringHistoryPanel from "./MonitoringHistoryPanel";
import MonitoringImageAnalysisPanel from "./MonitoringImageAnalysisPanel";
import MonitoringMainFeed from "./MonitoringMainFeed";

function buildConfigPayload(state) {
  return {
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
    multi_camera_cycle_budget_seconds: Number(
      state?.multi_camera_cycle_budget_seconds ?? 2
    ),
    enroll_frames_count: Number(state?.enroll_frames_count ?? 5),
    face_crop_padding_ratio: Number(state?.face_crop_padding_ratio ?? 0.2),
    inference_device_preference: String(
      state?.inference_device_preference ?? "auto"
    ),
  };
}

function formatDetectionScore(score) {
  return typeof score === "number" ? `${(score * 100).toFixed(1)}%` : "--";
}

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

  const refreshAll = async () => {
    await refreshLoopState();
    await refreshLatestDetection();
    await refreshHistory();
    await refreshCameraAlerts();
  };
  const refreshAllEffect = useEffectEvent(refreshAll);

  const removeNetworkFeed = async (sourceToRemove) => {
    setStatus("Suppression du flux reseau...");
    try {
      const freshConfig = await apiClient.getConfig();
      const next = {
        ...freshConfig,
        network_camera_sources: (
          freshConfig.network_camera_sources ?? []
        ).filter((source) => source !== sourceToRemove),
      };
      await apiClient.updateConfig(buildConfigPayload(next));
      await refreshLoopState();
      setStatus(`Flux reseau supprime: ${sourceToRemove}`);
    } catch {
      setStatus("Echec suppression flux reseau.");
    }
  };

  useEffect(() => {
    refreshAllEffect();
    let reconnectTimer = null;
    let socket = null;
    let closedByCleanup = false;

    const connect = () => {
      socket = new WebSocket(apiClient.getRecognitionLiveWebSocketUrl());
      socket.onopen = () => setStatus("Monitoring live connecte.");
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          setLoopState({
            loop: payload.loop ?? null,
            capture_settings: payload.capture_settings ?? null,
            local_camera: payload.local_camera ?? null,
            network_cameras: payload.network_cameras ?? null,
          });
          setLatestDetection(payload.latest_detection ?? null);
          setHistory(payload.history ?? []);
          setCameraAlerts(payload.camera_alerts ?? []);
        } catch {
          setStatus("Flux live monitoring invalide.");
        }
      };
      socket.onerror = () => {
        setStatus("Flux live monitoring indisponible.");
      };
      socket.onclose = () => {
        if (closedByCleanup) {
          return;
        }
        setStatus("Flux live monitoring ferme. Reconnexion...");
        reconnectTimer = window.setTimeout(connect, 2000);
      };
    };

    connect();
    return () => {
      closedByCleanup = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
      }
      if (socket) {
        socket.close();
      }
    };
  }, []);

  useEffect(() => {
    const onFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", onFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", onFullscreenChange);
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
        setStatus(
          "Le mode plein ecran n'est pas disponible sur ce navigateur."
        );
      }
      return;
    }
    await document.exitFullscreen();
  };

  const detectedFaces = latestDetection?.faces ?? [];
  const hasUnknownFace = detectedFaces.some(
    (face) => face.status === "inconnu"
  );
  const sourceRuntimeMap = Object.fromEntries(
    (loopState?.network_cameras?.sources ?? []).map((item) => [
      item.source,
      item,
    ])
  );
  const localRuntime = loopState?.local_camera ?? null;
  const allFeeds = useMemo(
    () => [
      { key: "local", label: "Camera locale", type: "local", source: "" },
      ...(config?.network_camera_sources ?? []).map((source, index) => ({
        key: `network:${source}`,
        label: `Flux reseau #${index + 1}`,
        type: "network",
        source,
      })),
    ],
    [config?.network_camera_sources]
  );
  const currentMainFeed =
    allFeeds.find((feed) => feed.key === mainFeedKey) || allFeeds[0];
  const sideFeeds = allFeeds.filter((feed) => feed.key !== currentMainFeed.key);
  const mainFeedRuntime =
    currentMainFeed.type === "local"
      ? localRuntime
      : sourceRuntimeMap[currentMainFeed.source] ?? null;

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
  const useNetworkVideoElement =
    currentMainFeed.type === "network" && audioEnabled;

  return (
    <section className="panel">
      {hasUnknownFace && (
        <div className="alert-banner" role="alert">
          ALERTE: VISAGE INCONNU DETECTE
        </div>
      )}
      <h2>Monitoring</h2>

      <MonitoringMainFeed
        currentMainFeed={currentMainFeed}
        detectedFaces={detectedFaces}
        hasUnknownFace={hasUnknownFace}
        isFullscreen={isFullscreen}
        mainFeedRuntime={mainFeedRuntime}
        loopRunning={loopState?.loop?.running}
        mainFeedUrl={mainFeedUrl}
        setAudioEnabled={setAudioEnabled}
        setCameraStatus={setCameraStatus}
        setFeedStatus={setFeedStatus}
        streamWrapRef={streamWrapRef}
        useNetworkVideoElement={useNetworkVideoElement}
      />

      <p
        className={`status-line ${cameraStatus.includes("actif") ? "ok" : "warn"}`}
      >
        {cameraStatus}
      </p>

      <MonitoringHistoryPanel title="Alertes camera">
        {cameraAlerts.length === 0 && (
          <p className="status-line ok">Aucune alerte camera.</p>
        )}
        {cameraAlerts.length > 0 && (
          <ul className="history-list">
            {cameraAlerts.slice(0, 10).map((alert, index) => (
              <li
                key={`${alert.source}-${alert.type}-${index}`}
                className="history-row"
              >
                <span>{alert.level}</span>
                <span>{alert.type}</span>
                <span>{alert.source}</span>
              </li>
            ))}
          </ul>
        )}
      </MonitoringHistoryPanel>

      <MonitoringHistoryPanel title="Grille des flux configures">
        <MonitoringFeedGrid
          feedStatus={feedStatus}
          localRuntime={localRuntime}
          removeNetworkFeed={removeNetworkFeed}
          setFeedStatus={setFeedStatus}
          setMainFeedKey={setMainFeedKey}
          sideFeeds={sideFeeds}
          sourceRuntimeMap={sourceRuntimeMap}
        />
      </MonitoringHistoryPanel>

      <div className="button-row">
        <button onClick={runCheck}>Lancer verification manuelle</button>
        {currentMainFeed.type === "network" && (
          <button onClick={() => setAudioEnabled((prev) => !prev)}>
            {audioEnabled ? "Couper son" : "Activer son"}
          </button>
        )}
        <button onClick={toggleFullscreen}>
          {isFullscreen ? "Quitter plein ecran" : "Plein ecran HUD"}
        </button>
        <button onClick={refreshAll}>Rafraichir etat loop</button>
      </div>

      <p className="status-line">{status}</p>

      <MonitoringImageAnalysisPanel
        imageAnalysis={imageAnalysis}
        runImageAnalysis={runImageAnalysis}
        setSelectedImage={setSelectedImage}
      />

      {detectedFaces.length > 0 && (
        <ul className="face-list">
          {detectedFaces.map((face, index) => {
            const name = face.face_name || `Inconnu #${index + 1}`;
            return (
              <li className="face-row" key={`${name}-${index}`}>
                <div>
                  <strong>{name}</strong>
                  <div>Confiance: {formatDetectionScore(face.score)}</div>
                </div>
                <span
                  className={`badge ${face.status === "reconnu" ? "ok" : "warn"}`}
                >
                  {face.status}
                </span>
              </li>
            );
          })}
        </ul>
      )}

      <MonitoringHistoryPanel title="Historique live (10 dernieres detections)">
        {history.length === 0 && (
          <p className="status-line">Aucune detection enregistree.</p>
        )}
        {history.length > 0 && (
          <ul className="history-list">
            {history.map((entry) => {
              const time = new Date(entry.created_at).toLocaleTimeString(
                "fr-FR",
                {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                }
              );
              const unknownCount = (entry.faces || []).filter(
                (face) => face.status === "inconnu"
              ).length;
              return (
                <li key={entry.id} className="history-row">
                  <span>{time}</span>
                  <span>Faces: {entry.faces_count}</span>
                  <span>
                    {unknownCount > 0
                      ? `Inconnus: ${unknownCount}`
                      : "0 inconnu"}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </MonitoringHistoryPanel>

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
