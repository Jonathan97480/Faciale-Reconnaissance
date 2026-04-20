const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

function buildWebSocketUrl(path) {
  const apiUrl = new URL(apiBaseUrl, window.location.origin);
  apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  apiUrl.pathname = `${apiUrl.pathname.replace(/\/$/, "")}${path}`;
  apiUrl.search = "";
  apiUrl.hash = "";
  return apiUrl.toString();
}

class ApiError extends Error {
  constructor(status, detail) {
    super(`API error: ${status}${detail ? ` - ${detail}` : ""}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseErrorDetail(response) {
  try {
    const payload = await response.json();
    if (payload?.detail) {
      return String(payload.detail);
    }
  } catch {}

  try {
    const text = await response.text();
    return text || "";
  } catch {
    return "";
  }
}

async function request(path, options = {}, meta = {}) {
  const method = options.method || "GET";
  const shouldLogConfig = path === "/config" && !meta.silent;
  const headers = new Headers(options.headers || {});

  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (shouldLogConfig) {
    console.info("[apiClient] request", { method, path, body: options.body || null });
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const detail = await parseErrorDetail(response);
    const error = new ApiError(response.status, detail);
    if (shouldLogConfig) {
      console.error("[apiClient] request failed", { method, path, message: error.message });
    }
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return response.text();
  }

  const payload = await response.json();
  if (shouldLogConfig) {
    console.info("[apiClient] response", { method, path, payload });
  }
  return payload;
}

function arrayBufferToBase64(arrayBuffer) {
  const bytes = new Uint8Array(arrayBuffer);
  let binary = "";
  for (const b of bytes) {
    binary += String.fromCharCode(b);
  }
  return btoa(binary);
}

export { ApiError };

export const apiClient = {
  login: (username, password) => {
    const form = new URLSearchParams();
    form.set("username", username);
    form.set("password", password);
    return request("/auth/login", {
      method: "POST",
      body: form,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },
  logout: () => request("/auth/logout", { method: "POST" }),
  getCurrentUser: () => request("/auth/me"),
  getConfig: (meta = {}) => request("/config", {}, meta),
  updateConfig: (payload) => request("/config", { method: "PUT", body: JSON.stringify(payload) }),
  listFaces: () => request("/faces"),
  createFace: (payload) => request("/faces", { method: "POST", body: JSON.stringify(payload) }),
  enrollFace: (payload) => request("/faces/enroll", { method: "POST", body: JSON.stringify(payload) }),
  deleteFace: (id) => request(`/faces/${id}`, { method: "DELETE" }),
  checkRecognition: (payload) =>
    request("/recognition/check", { method: "POST", body: JSON.stringify(payload) }),
  getLoopStatus: () => request("/recognition/loop/status"),
  getCameraAlerts: () => request("/cameras/alerts"),
  discoverOnvif: (timeoutSeconds = 2) =>
    request(`/cameras/onvif/discover?timeout_seconds=${timeoutSeconds}`),
  getResolvedCameraProfiles: () => request("/cameras/profiles/resolved"),
  getLatestDetection: () => request("/recognition/latest"),
  getDetectionHistory: (limit = 10) => request(`/recognition/history?limit=${limit}`),
  analyzeImageFile: async (file) => {
    const response = await fetch(`${apiBaseUrl}/recognition/analyze-image`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: await file.arrayBuffer(),
    });
    if (!response.ok) {
      throw new ApiError(response.status, await parseErrorDetail(response));
    }
    return response.json();
  },
  analyzeImageFiles: async (files) => {
    const items = [];
    for (const file of files) {
      const buffer = await file.arrayBuffer();
      items.push({
        filename: file.name || "image",
        content_type: file.type || "application/octet-stream",
        image_base64: arrayBufferToBase64(buffer),
      });
    }
    return request("/recognition/analyze-images", {
      method: "POST",
      body: JSON.stringify({ items }),
    });
  },
  getRecognitionPreviewStreamUrl: () => `${apiBaseUrl}/recognition/preview/stream`,
  getNetworkPreviewStreamUrl: (source) =>
    `${apiBaseUrl}/recognition/network-preview/stream?source=${encodeURIComponent(source)}`,
  getRecognitionLiveWebSocketUrl: () => buildWebSocketUrl("/recognition/live"),
  getRecognitionPreviewUrl: (cacheBuster = "") =>
    `${apiBaseUrl}/recognition/preview${cacheBuster ? `?t=${cacheBuster}` : ""}`,
};
