import { useState } from "react";

import { useConfig } from "../context/ConfigContext";
import ConfigCameraProfilesSection from "./ConfigCameraProfilesSection";
import ConfigGeneralSettings from "./ConfigGeneralSettings";
import ConfigNetworkSourcesSection from "./ConfigNetworkSourcesSection";
import {
  createEmptyCameraProfile,
  normalizeCameraProfile,
  toConfigPayload,
} from "./configPanelUtils";

export default function ConfigPanel() {
  const { config, loading, error, saveConfig } = useConfig();
  const [local, setLocal] = useState(null);
  const [status, setStatus] = useState("");
  const [newNetworkSource, setNewNetworkSource] = useState("");
  const [newCameraProfile, setNewCameraProfile] = useState(createEmptyCameraProfile());

  if (loading) {
    return <section className="panel"><h2>Configuration</h2><p>Chargement...</p></section>;
  }

  if (error) {
    return <section className="panel"><h2>Configuration</h2><p>{error}</p></section>;
  }

  const draft = local || config;

  const persistConfig = async (state, successMessage) => {
    setStatus("Sauvegarde...");
    try {
      await saveConfig(toConfigPayload(state));
      setLocal(null);
      setStatus(successMessage);
      return true;
    } catch {
      setStatus("Echec de sauvegarde.");
      return false;
    }
  };

  const onChange = (field, value) => {
    setLocal({ ...draft, [field]: value });
  };

  const shiftCamera = (delta) => {
    const nextValue = Math.max(0, Number(draft.camera_index) + delta);
    onChange("camera_index", String(nextValue));
  };

  const addNetworkSource = async () => {
    const cleaned = newNetworkSource.trim();
    if (!cleaned) {
      return;
    }

    const base = config ?? draft;
    const current = base?.network_camera_sources ?? [];
    if (current.includes(cleaned)) {
      setStatus("Ce flux est deja ajoute.");
      return;
    }
    if (current.length >= 10) {
      setStatus("Maximum 10 flux reseau.");
      return;
    }

    const nextDraft = { ...base, network_camera_sources: [...current, cleaned] };
    setLocal(nextDraft);
    if (await persistConfig(nextDraft, "Flux reseau ajoute.")) {
      setNewNetworkSource("");
    }
  };

  const removeNetworkSource = async (sourceToRemove) => {
    const base = config ?? draft;
    const current = base?.network_camera_sources ?? [];
    const nextDraft = {
      ...base,
      network_camera_sources: current.filter((source) => source !== sourceToRemove),
    };
    setLocal(nextDraft);
    await persistConfig(nextDraft, `Flux reseau supprime: ${sourceToRemove}`);
  };

  const addCameraProfile = async () => {
    const profile = normalizeCameraProfile(newCameraProfile);
    if (!profile.name || !profile.host) {
      setStatus("Nom et host requis pour le profil camera.");
      return;
    }

    const base = config ?? draft;
    const current = base?.network_camera_profiles ?? [];
    if (current.length >= 10) {
      setStatus("Maximum 10 profils camera.");
      return;
    }

    const nextDraft = { ...base, network_camera_profiles: [...current, profile] };
    setLocal(nextDraft);
    if (await persistConfig(nextDraft, "Profil camera ajoute.")) {
      setNewCameraProfile(createEmptyCameraProfile());
    }
  };

  const removeCameraProfile = async (indexToRemove) => {
    const base = config ?? draft;
    const current = base?.network_camera_profiles ?? [];
    const nextDraft = {
      ...base,
      network_camera_profiles: current.filter((_, index) => index !== indexToRemove),
    };
    setLocal(nextDraft);
    await persistConfig(nextDraft, "Profil camera supprime.");
  };

  return (
    <section className="panel">
      <h2>Configuration</h2>

      <ConfigGeneralSettings draft={draft} onChange={onChange} />

      <ConfigNetworkSourcesSection
        addNetworkSource={addNetworkSource}
        networkSources={draft.network_camera_sources ?? []}
        newNetworkSource={newNetworkSource}
        removeNetworkSource={removeNetworkSource}
        setNewNetworkSource={setNewNetworkSource}
      />

      <ConfigCameraProfilesSection
        addCameraProfile={addCameraProfile}
        newCameraProfile={newCameraProfile}
        profiles={draft.network_camera_profiles ?? []}
        removeCameraProfile={removeCameraProfile}
        setNewCameraProfile={setNewCameraProfile}
      />

      <div className="button-row" style={{ marginTop: 10 }}>
        <button type="button" onClick={() => shiftCamera(-1)}>Camera precedente</button>
        <button type="button" onClick={() => shiftCamera(1)}>Camera suivante</button>
      </div>
      <button onClick={() => persistConfig(draft, "Configuration sauvegardee.")}>Enregistrer</button>
      <p className="status-line">{status}</p>
    </section>
  );
}
