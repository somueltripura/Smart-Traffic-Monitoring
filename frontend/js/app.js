/**
 * Smart Traffic Monitoring System - Main Frontend Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  // Instances
  const densityGauge = new DensityGauge("densityGauge");
  const speedGauge = new SpeedGauge("speedGauge");
  const charts = new TrafficCharts();
  const trafficMap = new TrafficMap("traffic-map");

  // State
  let activeCameraId = "cam-01";
  let camerasList = [];
  let eventSource = null;
  let isMonitoring = false;

  // DOM Elements
  const cameraSelect = document.getElementById("cameraSelect");
  const btnStart = document.getElementById("btnStart");
  const btnStop = document.getElementById("btnStop");
  const btnUploadModal = document.getElementById("btnUploadModal");
  const btnConfigModal = document.getElementById("btnConfigModal");

  // Video Element
  const videoFeed = document.getElementById("videoFeed");

  // Stat Counters
  const valTotal = document.getElementById("valTotalVehicles");
  const valCars = document.getElementById("valCars");
  const valMotos = document.getElementById("valMotos");
  const valBuses = document.getElementById("valBuses");
  const valTrucks = document.getElementById("valTrucks");
  const valInbound = document.getElementById("valInbound");
  const valOutbound = document.getElementById("valOutbound");

  // System Badges
  const systemStatusDot = document.getElementById("systemStatusDot");
  const systemStatusText = document.getElementById("systemStatusText");
  const clockElement = document.getElementById("digitalClock");
  const fpsBadge = document.getElementById("fpsBadge");
  const latencyBadge = document.getElementById("latencyBadge");
  const aiEngineBadge = document.getElementById("aiEngineBadge");

  // Congestion UI
  const congestionCard = document.getElementById("congestionCard");
  const congestionStatusText = document.getElementById("congestionStatusText");
  const congestionScoreText = document.getElementById("congestionScoreText");

  // Recent Crossings Feed
  const recentEventsList = document.getElementById("recentEventsList");

  // Modals
  const uploadModal = document.getElementById("uploadModal");
  const configModal = document.getElementById("configModal");
  const uploadForm = document.getElementById("uploadForm");
  const configForm = document.getElementById("configForm");

  // 1. Digital Clock
  function updateClock() {
    const now = new Date();
    clockElement.textContent = now.toUTCString().replace("GMT", "UTC");
  }
  setInterval(updateClock, 1000);
  updateClock();

  // 2. Fetch Initial Cameras List
  async function loadCameras() {
    try {
      const data = await API.getCameras();
      camerasList = data.cameras || [];
      cameraSelect.innerHTML = "";

      camerasList.forEach(cam => {
        const opt = document.createElement("option");
        opt.value = cam.id;
        opt.textContent = `${cam.name} (${cam.id})`;
        if (cam.id === activeCameraId) opt.selected = true;
        cameraSelect.appendChild(opt);
      });

      trafficMap.updateCameras(camerasList, activeCameraId, (selectedId) => {
        switchCamera(selectedId);
      });
    } catch (err) {
      console.error("Failed to load cameras:", err);
    }
  }

  // 3. Switch Camera
  async function switchCamera(cameraId) {
    activeCameraId = cameraId;
    cameraSelect.value = cameraId;
    trafficMap.focusCamera(cameraId);

    // If currently monitoring, start stream on new camera
    if (isMonitoring) {
      await API.startDetection(activeCameraId);
    }
    loadAnalytics();
  }

  cameraSelect.addEventListener("change", (e) => {
    switchCamera(e.target.value);
  });

  // 4. Start & Stop Controls
  btnStart.addEventListener("click", async () => {
    try {
      btnStart.disabled = true;
      btnStart.textContent = "STARTING...";
      const res = await API.startDetection(activeCameraId);
      isMonitoring = true;
      updateStreamFeed(true);
      btnStart.style.display = "none";
      btnStop.style.display = "inline-flex";
    } catch (err) {
      alert("Failed to start monitoring: " + err.message);
    } finally {
      btnStart.disabled = false;
      btnStart.textContent = "START MONITORING";
    }
  });

  btnStop.addEventListener("click", async () => {
    try {
      btnStop.disabled = true;
      btnStop.textContent = "STOPPING...";
      await API.stopDetection();
      isMonitoring = false;
      updateStreamFeed(false);
      btnStop.style.display = "none";
      btnStart.style.display = "inline-flex";
    } catch (err) {
      alert("Failed to stop monitoring: " + err.message);
    } finally {
      btnStop.disabled = false;
      btnStop.textContent = "STOP MONITORING";
    }
  });

  function updateStreamFeed(active) {
    if (active) {
      videoFeed.src = `/api/stream/video?t=${Date.now()}`;
      systemStatusDot.className = "status-dot pulse";
      systemStatusText.textContent = "SYSTEM ACTIVE";
    } else {
      videoFeed.src = `/api/stream/video?t=${Date.now()}`;
      systemStatusDot.className = "status-dot";
      systemStatusText.textContent = "STANDBY";
    }
  }

  // 5. Server-Sent Events (SSE) Live Telemetry Stream
  function initSSE() {
    if (eventSource) eventSource.close();

    eventSource = new EventSource("/api/stream/events");

    eventSource.addEventListener("traffic_update", (e) => {
      try {
        const telemetry = JSON.parse(e.data);
        handleTelemetryUpdate(telemetry);
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    });

    eventSource.onerror = () => {
      systemStatusDot.className = "status-dot offline";
      systemStatusText.textContent = "RECONNECTING...";
    };
  }

  function handleTelemetryUpdate(telemetry) {
    if (telemetry.status === "online") {
      systemStatusDot.className = "status-dot pulse";
      systemStatusText.textContent = "ONLINE - DETECTING";
      isMonitoring = true;
      btnStart.style.display = "none";
      btnStop.style.display = "inline-flex";
    }

    // FPS
    if (fpsBadge) fpsBadge.textContent = `${telemetry.fps || 0.0} FPS`;

    // Counts
    const counts = telemetry.vehicle_counts || {};
    valTotal.textContent = counts.total_vehicles || 0;
    valCars.textContent = counts.cars || 0;
    valMotos.textContent = counts.motorcycles || 0;
    valBuses.textContent = counts.buses || 0;
    valTrucks.textContent = counts.trucks || 0;
    valInbound.textContent = counts.inbound || 0;
    valOutbound.textContent = counts.outbound || 0;

    // Density Gauge
    const density = telemetry.density || {};
    densityGauge.update(density.density_percentage || 0, density.density_level || "Low");

    // Speed Gauge
    const speed = telemetry.speed || {};
    speedGauge.update(speed.average_speed_kmh, speed.is_calibrated);

    // Congestion UI
    const cong = telemetry.congestion || {};
    const status = cong.status || "Normal";
    congestionStatusText.textContent = status.toUpperCase();
    congestionScoreText.textContent = `Score: ${(cong.score || 0).toFixed(2)}`;

    congestionCard.className = "congestion-status-card";
    if (status === "Moderate") {
      congestionCard.classList.add("status-moderate");
    } else if (status === "High Congestion") {
      congestionCard.classList.add("status-high");
    }

    // Charts Update
    charts.updateFlowData(counts.inbound || 0, counts.outbound || 0);
    charts.updateCategoryData(counts.cars || 0, counts.motorcycles || 0, counts.buses || 0, counts.trucks || 0);

    // Recent Crossings
    updateRecentCrossings(telemetry.recent_crossings || []);
  }

  function updateRecentCrossings(crossings) {
    if (!crossings || crossings.length === 0) return;
    recentEventsList.innerHTML = "";

    crossings.slice(-6).reverse().forEach(evt => {
      const row = document.createElement("div");
      row.className = `event-row event-${evt.direction}`;
      const speedStr = evt.speed_kmh ? ` | ${evt.speed_kmh} km/h` : "";
      row.innerHTML = `
        <span><strong>#${evt.track_id}</strong> ${evt.vehicle_type.toUpperCase()}</span>
        <span>${evt.direction.toUpperCase()}${speedStr}</span>
      `;
      recentEventsList.appendChild(row);
    });
  }

  // 6. Analytics & Trends
  async function loadAnalytics() {
    try {
      const data = await API.getAnalytics(activeCameraId);
      if (data && data.hourly_trends) {
        charts.updateHourlyTrends(data.hourly_trends);
      }
    } catch (err) {
      console.warn("Failed to load analytics trends:", err);
    }
  }

  // 7. System Health Check
  async function checkHealth() {
    const t0 = performance.now();
    try {
      const data = await API.getHealth();
      const latency = Math.round(performance.now() - t0);
      if (latencyBadge) latencyBadge.textContent = `${latency} ms`;
      if (aiEngineBadge && data.ai_model) {
        aiEngineBadge.textContent = `${data.ai_model.backend.toUpperCase()} (YOLOv8)`;
      }
    } catch (err) {
      if (latencyBadge) latencyBadge.textContent = "TIMEOUT";
    }
  }
  setInterval(checkHealth, 5000);
  checkHealth();

  // 8. Modals Management (Upload Video & Camera Configure)
  btnUploadModal.addEventListener("click", () => {
    uploadModal.classList.add("active");
  });

  btnConfigModal.addEventListener("click", () => {
    const currentCam = camerasList.find(c => c.id === activeCameraId);
    if (currentCam) {
      document.getElementById("cfgCapacity").value = currentCam.road_capacity || 15;
      if (currentCam.counting_line) {
        document.getElementById("cfgLine").value = JSON.stringify(currentCam.counting_line);
      }
      if (currentCam.roi_polygon) {
        document.getElementById("cfgRoi").value = JSON.stringify(currentCam.roi_polygon);
      }
      if (currentCam.calibration_params && currentCam.calibration_params.meters_per_pixel) {
        document.getElementById("cfgScale").value = currentCam.calibration_params.meters_per_pixel;
      }
    }
    configModal.classList.add("active");
  });

  document.querySelectorAll(".modal-close-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      uploadModal.classList.remove("active");
      configModal.classList.remove("active");
    });
  });

  // Handle Video Upload Form
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("videoFileInput");
    if (!fileInput.files || fileInput.files.length === 0) {
      alert("Please select a video file to upload.");
      return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    const submitBtn = uploadForm.querySelector("button[type='submit']");
    submitBtn.disabled = true;
    submitBtn.textContent = "UPLOADING & INITIALIZING...";

    try {
      const res = await API.uploadVideo(formData);
      alert("Video uploaded successfully! Switching to new stream.");
      uploadModal.classList.remove("active");
      uploadForm.reset();
      await loadCameras();
      if (res.camera_id) {
        switchCamera(res.camera_id);
      }
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "START ANALYSIS";
    }
  });

  // Handle Configuration Form
  configForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const capacity = parseInt(document.getElementById("cfgCapacity").value);
    const lineVal = document.getElementById("cfgLine").value;
    const roiVal = document.getElementById("cfgRoi").value;
    const scaleVal = parseFloat(document.getElementById("cfgScale").value);

    const payload = {
      road_capacity: capacity,
    };

    try {
      if (lineVal) payload.counting_line = JSON.parse(lineVal);
      if (roiVal) payload.roi_polygon = JSON.parse(roiVal);
      if (!isNaN(scaleVal) && scaleVal > 0) {
        payload.calibration_params = { mode: "linear", meters_per_pixel: scaleVal, is_calibrated: true };
      }

      await API.configureCamera(activeCameraId, payload);
      alert("Configuration updated successfully!");
      configModal.classList.remove("active");
      await loadCameras();
    } catch (err) {
      alert("Invalid JSON or settings: " + err.message);
    }
  });

  // Startup
  loadCameras();
  initSSE();
  loadAnalytics();
});
