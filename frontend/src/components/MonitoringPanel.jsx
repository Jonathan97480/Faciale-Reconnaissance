import { useEffect, useRef, useState } from "react";

import { apiClient } from "../api/client";

export default function MonitoringPanel() {
  const [result, setResult] = useState(null);
  const [imageAnalysis, setImageAnalysis] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [latestDetection, setLatestDetection] = useState(null);
  const [history, setHistory] = useState([]);
  const [loopState, setLoopState] = useState(null);
  const [status, setStatus] = useState("");
  const [cameraStatus, setCameraStatus] = useState("Apercu camera backend actif.");
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

  useEffect(() => {
    refreshLoopState();
    refreshLatestDetection();
    refreshHistory();

    const timer = setInterval(() => {
      refreshLoopState();
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
          src={apiClient.getRecognitionPreviewStreamUrl()}
          alt="Apercu camera backend"
          onError={() => setCameraStatus("Aucune image camera (verifiez index camera et disponibilite).")}
          onLoad={() => setCameraStatus("Apercu camera backend actif.")}
        />
        <div className="hud-overlay">
          <div className="hud-corners" />
          <div className="hud-topline">TACTICAL IDENT / LIVE FEED</div>
          <div className="hud-meta">
            <span>FACES: {detectedFaces.length}</span>
            <span>LOOP: {loopState?.loop?.running ? "RUNNING" : "STOPPED"}</span>
            <span>UNKNOWN: {hasUnknownFace ? "YES" : "NO"}</span>
          </div>
        </div>
      </div>
      <p className={`status-line ${cameraStatus.includes("actif") ? "ok" : "warn"}`}>{cameraStatus}</p>
      <div className="button-row">
        <button onClick={runCheck}>Lancer verification manuelle</button>
        <button onClick={toggleFullscreen}>{isFullscreen ? "Quitter plein ecran" : "Plein ecran HUD"}</button>
        <button
          onClick={async () => {
            await refreshLoopState();
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
