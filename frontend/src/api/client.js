const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

async function request(path, options = {}) {
    const response = await fetch(`${apiBaseUrl}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }

    return response.json();
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
    getConfig: () => request("/config"),
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
