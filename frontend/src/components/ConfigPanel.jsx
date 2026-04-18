import { useState } from "react";

import { useConfig } from "../context/ConfigContext";

export default function ConfigPanel() {
  const { config, loading, error, saveConfig } = useConfig();
  const [local, setLocal] = useState(null);
  const [status, setStatus] = useState("");

  if (loading) {
    return <section className="panel"><h2>Configuration</h2><p>Chargement...</p></section>;
  }

  if (error) {
    return <section className="panel"><h2>Configuration</h2><p>{error}</p></section>;
  }

  const draft = local || config;

  const onChange = (field, value) => {
    setLocal({ ...draft, [field]: value });
  };

  const shiftCamera = (delta) => {
    const nextValue = Math.max(0, Number(draft.camera_index) + delta);
    onChange("camera_index", String(nextValue));
  };

  const onSave = async () => {
    setStatus("Sauvegarde...");
    try {
      await saveConfig({
        detection_interval_seconds: Number(draft.detection_interval_seconds),
        match_threshold: Number(draft.match_threshold),
        camera_index: Number(draft.camera_index),
        camera_source: draft.camera_source ?? "",
        enroll_frames_count: Number(draft.enroll_frames_count),
        face_crop_padding_ratio: Number(draft.face_crop_padding_ratio),
      });
      setLocal(null);
      setStatus("Configuration sauvegardee.");
    } catch {
      setStatus("Echec de sauvegarde.");
    }
  };

  return (
    <section className="panel">
      <h2>Configuration</h2>
      <div className="field-grid">
        <label>
          Intervalle de detection (secondes)
          <input
            type="number"
            min="0.1"
            step="0.1"
            value={draft.detection_interval_seconds}
            onChange={(event) => onChange("detection_interval_seconds", event.target.value)}
          />
        </label>
        <label>
          Seuil de reconnaissance
          <input
            type="number"
            min="0"
            max="1"
            step="0.01"
            value={draft.match_threshold}
            onChange={(event) => onChange("match_threshold", event.target.value)}
          />
        </label>
        <label>
          Index caméra locale
          <input
            type="number"
            min="0"
            step="1"
            value={draft.camera_index}
            onChange={(event) => onChange("camera_index", event.target.value)}
          />
        </label>
        <label>
          Source caméra réseau (URL, RTSP, fichier vidéo)
          <input
            type="text"
            placeholder="Laisser vide pour webcam locale"
            value={draft.camera_source ?? ""}
            onChange={(event) => onChange("camera_source", event.target.value)}
            style={{ width: "100%" }}
          />
        </label>
        <label>
          Nombre de frames d'enrolement
          <input
            type="number"
            min="1"
            max="30"
            step="1"
            value={draft.enroll_frames_count ?? 5}
            onChange={(event) => onChange("enroll_frames_count", event.target.value)}
          />
        </label>
        <label>
          Marge crop visage (ratio)
          <input
            type="number"
            min="0"
            max="1"
            step="0.01"
            value={draft.face_crop_padding_ratio ?? 0.2}
            onChange={(event) => onChange("face_crop_padding_ratio", event.target.value)}
          />
        </label>
      </div>
      <div className="button-row" style={{ marginTop: 10 }}>
        <button type="button" onClick={() => shiftCamera(-1)}>Camera precedente</button>
        <button type="button" onClick={() => shiftCamera(1)}>Camera suivante</button>
      </div>
      <button onClick={onSave}>Enregistrer</button>
      <p className="status-line">{status}</p>
    </section>
  );
}
