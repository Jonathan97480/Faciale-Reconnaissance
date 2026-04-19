import { useState } from "react";

import { useConfig } from "../context/ConfigContext";

export default function ConfigPanel() {
  const { config, loading, error, saveConfig } = useConfig();
  const [local, setLocal] = useState(null);
  const [status, setStatus] = useState("");
  const [newNetworkSource, setNewNetworkSource] = useState("");
  const [newCameraProfile, setNewCameraProfile] = useState({
    name: "",
    protocol: "rtsp",
    host: "",
    port: 554,
    path: "/stream1",
    username: "",
    password: "",
    onvif_url: "",
    enabled: true,
  });

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
      const sanitizedProfiles = (draft.network_camera_profiles ?? [])
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
        .slice(0, 10);

      await saveConfig({
        detection_interval_seconds: Number(draft.detection_interval_seconds),
        match_threshold: Number(draft.match_threshold),
        camera_index: Number(draft.camera_index),
        camera_source: draft.camera_source ?? "",
        network_camera_sources: sanitizedNetworkSources,
        network_camera_profiles: sanitizedProfiles,
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

  const addCameraProfile = () => {
    const profile = {
      ...newCameraProfile,
      name: String(newCameraProfile.name).trim(),
      host: String(newCameraProfile.host).trim(),
      path: String(newCameraProfile.path || "/"),
      port: Number(newCameraProfile.port || 554),
    };
    if (!profile.name || !profile.host) {
      setStatus("Nom et host requis pour le profil camera.");
      return;
    }
    const current = draft.network_camera_profiles ?? [];
    if (current.length >= 10) {
      setStatus("Maximum 10 profils camera.");
      return;
    }
    onChange("network_camera_profiles", [...current, profile]);
    setNewCameraProfile({
      name: "",
      protocol: "rtsp",
      host: "",
      port: 554,
      path: "/stream1",
      username: "",
      password: "",
      onvif_url: "",
      enabled: true,
    });
    setStatus("");
  };

  const removeCameraProfile = (indexToRemove) => {
    const current = draft.network_camera_profiles ?? [];
    onChange(
      "network_camera_profiles",
      current.filter((_, index) => index !== indexToRemove)
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
      <div className="panel" style={{ marginTop: 10 }}>
        <h3>Profils camera standards (RTSP/MJPEG/HTTP/HLS)</h3>
        <div className="field-grid">
          <label>
            Nom
            <input
              type="text"
              value={newCameraProfile.name}
              onChange={(event) => setNewCameraProfile({ ...newCameraProfile, name: event.target.value })}
            />
          </label>
          <label>
            Protocole
            <select
              value={newCameraProfile.protocol}
              onChange={(event) => setNewCameraProfile({ ...newCameraProfile, protocol: event.target.value })}
            >
              <option value="rtsp">RTSP</option>
              <option value="mjpeg">MJPEG</option>
              <option value="http">HTTP</option>
              <option value="hls">HLS</option>
            </select>
          </label>
          <label>
            Host/IP
            <input
              type="text"
              value={newCameraProfile.host}
              onChange={(event) => setNewCameraProfile({ ...newCameraProfile, host: event.target.value })}
            />
          </label>
          <label>
            Port
            <input
              type="number"
              min="1"
              max="65535"
              value={newCameraProfile.port}
              onChange={(event) => setNewCameraProfile({ ...newCameraProfile, port: event.target.value })}
            />
          </label>
          <label>
            Path stream
            <input
              type="text"
              value={newCameraProfile.path}
              onChange={(event) => setNewCameraProfile({ ...newCameraProfile, path: event.target.value })}
            />
          </label>
          <label>
            Username
            <input
              type="text"
              value={newCameraProfile.username}
              onChange={(event) => setNewCameraProfile({ ...newCameraProfile, username: event.target.value })}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={newCameraProfile.password}
              onChange={(event) => setNewCameraProfile({ ...newCameraProfile, password: event.target.value })}
            />
          </label>
          <label>
            URL ONVIF (optionnel)
            <input
              type="text"
              value={newCameraProfile.onvif_url}
              onChange={(event) => setNewCameraProfile({ ...newCameraProfile, onvif_url: event.target.value })}
            />
          </label>
        </div>
        <div className="button-row" style={{ marginTop: 8 }}>
          <button type="button" onClick={addCameraProfile}>Ajouter profil camera</button>
        </div>
        {(draft.network_camera_profiles ?? []).length === 0 && (
          <p className="status-line">Aucun profil camera standard configure.</p>
        )}
        {(draft.network_camera_profiles ?? []).length > 0 && (
          <ul className="history-list">
            {(draft.network_camera_profiles ?? []).map((profile, index) => (
              <li key={`${profile.name}-${index}`} className="history-row">
                <span>{profile.name}</span>
                <span>{profile.protocol.toUpperCase()} {profile.host}:{profile.port}{profile.path}</span>
                <button type="button" onClick={() => removeCameraProfile(index)}>Supprimer</button>
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
