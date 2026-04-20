export function createEmptyCameraProfile() {
  return {
    name: "",
    protocol: "rtsp",
    host: "",
    port: 554,
    path: "/stream1",
    username: "",
    password: "",
    onvif_url: "",
    enabled: true,
  };
}

export function toConfigPayload(state) {
  const sanitizedNetworkSources = (state.network_camera_sources ?? [])
    .map((source) => String(source).trim())
    .filter((source, index, arr) => source && arr.indexOf(source) === index)
    .slice(0, 10);

  const sanitizedProfiles = (state.network_camera_profiles ?? [])
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

  return {
    detection_interval_seconds: Number(state.detection_interval_seconds),
    match_threshold: Number(state.match_threshold),
    camera_index: Number(state.camera_index),
    camera_source: state.camera_source ?? "",
    network_camera_sources: sanitizedNetworkSources,
    network_camera_profiles: sanitizedProfiles,
    multi_camera_cycle_budget_seconds: Number(state.multi_camera_cycle_budget_seconds),
    enroll_frames_count: Number(state.enroll_frames_count),
    face_crop_padding_ratio: Number(state.face_crop_padding_ratio),
    inference_device_preference: String(state.inference_device_preference ?? "auto"),
  };
}

export function normalizeCameraProfile(profile) {
  return {
    ...profile,
    name: String(profile.name).trim(),
    host: String(profile.host).trim(),
    path: String(profile.path || "/"),
    port: Number(profile.port || 554),
  };
}
