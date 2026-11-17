/**
 * Smart Traffic Monitoring System - REST API Client
 */

const API = {
  baseURL: "/api",

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    try {
      const response = await fetch(url, {
        headers: {
          "Accept": "application/json",
          ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  },

  // Health check
  async getHealth() {
    return this.request("/health");
  },

  // Real-time Traffic Telemetry
  async getTraffic() {
    return this.request("/traffic");
  },

  async getCounts() {
    return this.request("/traffic/counts");
  },

  async getDensity() {
    return this.request("/traffic/density");
  },

  async getSpeed() {
    return this.request("/traffic/speed");
  },

  async getCongestion() {
    return this.request("/traffic/congestion");
  },

  // Detection Controls
  async startDetection(cameraId = "cam-01", source = null) {
    return this.request("/detection/start", {
      method: "POST",
      body: JSON.stringify({ camera_id: cameraId, source: source }),
    });
  },

  async stopDetection() {
    return this.request("/detection/stop", {
      method: "POST",
    });
  },

  // Cameras Management
  async getCameras() {
    return this.request("/cameras");
  },

  async addCamera(cameraData) {
    return this.request("/cameras", {
      method: "POST",
      body: JSON.stringify(cameraData),
    });
  },

  async configureCamera(cameraId, configData) {
    return this.request(`/cameras/${cameraId}/configure`, {
      method: "POST",
      body: JSON.stringify(configData),
    });
  },

  // Video Upload
  async uploadVideo(formData) {
    return this.request("/upload", {
      method: "POST",
      body: formData,
    });
  },

  // Historical Analytics & Reporting
  async getAnalytics(cameraId = null) {
    const query = cameraId ? `?camera_id=${encodeURIComponent(cameraId)}` : "";
    return this.request(`/analytics${query}`);
  },

  async getHistory(cameraId = null, limit = 50) {
    const params = new URLSearchParams();
    if (cameraId) params.append("camera_id", cameraId);
    params.append("limit", limit);
    return this.request(`/history?${params.toString()}`);
  },
};
