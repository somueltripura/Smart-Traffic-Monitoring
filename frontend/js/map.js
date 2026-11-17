/**
 * Smart Traffic Monitoring System - Leaflet.js Interactive Traffic Map
 */

class TrafficMap {
  constructor(containerId = "traffic-map") {
    this.containerId = containerId;
    this.map = null;
    this.markers = {};
    this.initMap();
  }

  initMap() {
    const el = document.getElementById(this.containerId);
    if (!el || typeof L === "undefined") return;

    // Default center (Downtown NYC)
    this.map = L.map(this.containerId, {
      zoomControl: true,
      attributionControl: false,
    }).setView([40.718, -74.002], 13);

    // Dark Matter Tiles
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(this.map);
  }

  updateCameras(cameras, activeCameraId, onSelectCamera) {
    if (!this.map || !cameras) return;

    cameras.forEach(cam => {
      const lat = cam.latitude || 40.7128;
      const lng = cam.longitude || -74.0060;
      const isActive = cam.id === activeCameraId;

      const markerColor = isActive ? "#00D9A6" : "#00BFFF";
      const iconHtml = `
        <div style="
          width: 22px; 
          height: 22px; 
          border-radius: 50%; 
          background: ${markerColor}; 
          border: 2px solid #FFFFFF; 
          box-shadow: 0 0 10px ${markerColor};
          display: flex;
          align-items: center;
          justify-content: center;
          color: #07111F;
          font-size: 10px;
          font-weight: bold;
        ">
          ${cam.id.replace("cam-", "")}
        </div>
      `;

      const customIcon = L.divIcon({
        className: "custom-cam-marker",
        html: iconHtml,
        iconSize: [22, 22],
        iconAnchor: [11, 11],
      });

      if (this.markers[cam.id]) {
        this.markers[cam.id].setIcon(customIcon);
        this.markers[cam.id].setLatLng([lat, lng]);
      } else {
        const marker = L.marker([lat, lng], { icon: customIcon }).addTo(this.map);

        const popupContent = `
          <div style="font-family: sans-serif; font-size: 12px; line-height: 1.4;">
            <div style="color: #00BFFF; font-weight: bold; font-size: 13px;">${cam.name}</div>
            <div style="color: #8FA3BF; margin: 4px 0;">${cam.location}</div>
            <div style="color: #FFFFFF; font-size: 11px;">Source: ${cam.stream_source}</div>
            <button id="map-btn-${cam.id}" style="
              margin-top: 8px;
              background: #00BFFF;
              color: #07111F;
              border: none;
              padding: 4px 10px;
              border-radius: 4px;
              font-weight: bold;
              cursor: pointer;
              width: 100%;
            ">Switch To Camera</button>
          </div>
        `;
        marker.bindPopup(popupContent);

        marker.on("popupopen", () => {
          const btn = document.getElementById(`map-btn-${cam.id}`);
          if (btn && onSelectCamera) {
            btn.onclick = () => {
              onSelectCamera(cam.id);
              marker.closePopup();
            };
          }
        });

        this.markers[cam.id] = marker;
      }
    });
  }

  focusCamera(cameraId) {
    if (this.markers[cameraId] && this.map) {
      const latlng = this.markers[cameraId].getLatLng();
      this.map.panTo(latlng, { animate: true });
    }
  }
}
