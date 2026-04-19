import { useState } from "react";

import { useConfig } from "../context/ConfigContext";

export default function ConfigPanel() {
  const { config, loading, error, saveConfig } = useConfig();
  const [local, setLocal] = useState(null);
  const [status, setStatus] = useState("");
  const [newNetworkSource, setNewNetworkSource] = useState("");

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
      const sanitizedNetworkSources = (draft.network_camera_sources ?? [])
        .map((source) => String(source).trim())
        .filter((source, index, arr) => source && arr.indexOf(source) === index)
        .slice(0, 10);

      await saveConfig({
        detection_interval_seconds: Number(draft.detection_interval_seconds),
        match_threshold: Number(draft.match_threshold),
        camera_index: Number(draft.camera_index),
        camera_source: draft.camera_source ?? "",
        network_camera_sources: sanitizedNetworkSources,
        multi_camera_cycle_budget_seconds: Number(draft.multi_camera_cycle_budget_seconds),
        enroll_frames_count: Number(draft.enroll_frames_count),
        face_crop_padding_ratio: Number(draft.face_crop_padding_ratio),
      });
      setLocal(null);
      setStatus("Configuration sauvegardee.");
    } catch {
      setStatus("Echec de sauvegarde.");
    }
  };

  const addNetworkSource = () => {
    const cleaned = newNetworkSource.trim();
    if (!cleaned) {
      return;
    }
    const current = draft.network_camera_sources ?? [];
    if (current.includes(cleaned)) {
      setStatus("Ce flux est deja ajoute.");
      return;
    }
    if (current.length >= 10) {
      setStatus("Maximum 10 flux reseau.");
      return;
    }
    onChange("network_camera_sources", [...current, cleaned]);
    setNewNetworkSource("");
    setStatus("");
  };

  const removeNetworkSource = (sourceToRemove) => {
    const current = draft.network_camera_sources ?? [];
    onChange(
      "network_camera_sources",
      current.filter((source) => source !== sourceToRemove)
    );
    setStatus("");
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
          Budget cycle multi-cameras (secondes)
          <input
            type="number"
            min="0.1"
            max="10"
            step="0.1"
            value={draft.multi_camera_cycle_budget_seconds ?? 2}
            onChange={(event) => onChange("multi_camera_cycle_budget_seconds", event.target.value)}
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
      <div className="panel" style={{ marginTop: 10 }}>
        <h3>Flux caméras réseau (max 10)</h3>
        <div className="button-row">
          <input
            type="text"
            placeholder="rtsp://..., http://..., fichier video..."
            value={newNetworkSource}
            onChange={(event) => setNewNetworkSource(event.target.value)}
            style={{ width: "100%" }}
          />
          <button type="button" onClick={addNetworkSource}>Ajouter flux</button>
        </div>
        {(draft.network_camera_sources ?? []).length === 0 && (
          <p className="status-line">Aucun flux reseau configure.</p>
        )}
        {(draft.network_camera_sources ?? []).length > 0 && (
          <ul className="history-list">
            {(draft.network_camera_sources ?? []).map((source) => (
              <li key={source} className="history-row">
                <span>{source}</span>
                <button type="button" onClick={() => removeNetworkSource(source)}>Supprimer</button>
              </li>
            ))}
          </ul>
        )}
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
