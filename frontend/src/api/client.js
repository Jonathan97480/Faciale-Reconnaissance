const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

async function request(path, options = {}, meta = {}) {
    const method = options.method || "GET";
    const shouldLogConfig = path === "/config" && !meta.silent;
    if (shouldLogConfig) {
        console.info("[apiClient] request", { method, path, body: options.body || null });
    }
    const response = await fetch(`${apiBaseUrl}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });

    if (!response.ok) {
        let detail = "";
        try {
            const payload = await response.json();
            detail = payload?.detail ? ` - ${payload.detail}` : "";
        } catch {
            try {
                const text = await response.text();
                detail = text ? ` - ${text}` : "";
            } catch {
                detail = "";
            }
        }
        const message = `API error: ${response.status}${detail}`;
        if (shouldLogConfig) {
            console.error("[apiClient] request failed", { method, path, message });
        }
        throw new Error(message);
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

export const apiClient = {
    getConfig: (meta = {}) => request("/config", {}, meta),
    updateConfig: (payload) =>
        request("/config", { method: "PUT", body: JSON.stringify(payload) }),
    listFaces: () => request("/faces"),
    createFace: (payload) =>
        request("/faces", { method: "POST", body: JSON.stringify(payload) }),
    enrollFace: (payload) =>
        request("/faces/enroll", { method: "POST", body: JSON.stringify(payload) }),
    deleteFace: (id) =>
        fetch(`${apiBaseUrl}/faces/${id}`, { method: "DELETE" }),
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
            headers: { "Content-Type": file.type || "application/octet-stream" },
            body: await file.arrayBuffer(),
        });
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
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
    getRecognitionPreviewUrl: (cacheBuster = "") =>
        `${apiBaseUrl}/recognition/preview${cacheBuster ? `?t=${cacheBuster}` : ""}`,
};
