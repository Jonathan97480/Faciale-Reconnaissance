export default function ConfigGeneralSettings({ draft, onChange }) {
  return (
    <>
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
        <label>
          Acceleration IA (GPU)
          <select
            value={draft.inference_device_preference ?? "auto"}
            onChange={(event) => onChange("inference_device_preference", event.target.value)}
          >
            <option value="auto">Auto (GPU si disponible)</option>
            <option value="cuda">Forcer GPU (CUDA)</option>
            <option value="cpu">Forcer CPU</option>
          </select>
        </label>
      </div>
      <p className="status-line">
        Appareil IA actif: <strong>{draft.inference_device_active ?? "cpu"}</strong>
      </p>
    </>
  );
}
