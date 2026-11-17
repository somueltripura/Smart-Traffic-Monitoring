/**
 * Smart Traffic Monitoring System - Chart.js Visualizations
 */

class TrafficCharts {
  constructor() {
    this.flowChart = null;
    this.categoryChart = null;
    this.hourlyChart = null;
    this._initFlowChart();
    this._initCategoryChart();
    this._initHourlyChart();
  }

  _initFlowChart() {
    const ctx = document.getElementById("trafficFlowChart")?.getContext("2d");
    if (!ctx) return;

    const maxDataPoints = 15;
    const initialLabels = Array.from({ length: maxDataPoints }, (_, i) => `-${(maxDataPoints - i) * 2}s`);
    const zeros = new Array(maxDataPoints).fill(0);

    this.flowChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: initialLabels,
        datasets: [
          {
            label: "Inbound Flow",
            data: [...zeros],
            borderColor: "#00D9A6",
            backgroundColor: "rgba(0, 217, 166, 0.12)",
            tension: 0.35,
            fill: true,
            pointRadius: 2,
            borderWidth: 2,
          },
          {
            label: "Outbound Flow",
            data: [...zeros],
            borderColor: "#00BFFF",
            backgroundColor: "rgba(0, 191, 255, 0.12)",
            tension: 0.35,
            fill: true,
            pointRadius: 2,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: { color: "#8FA3BF", font: { size: 10 } },
          },
          tooltip: {
            backgroundColor: "#102238",
            borderColor: "#00BFFF",
            borderWidth: 1,
            titleColor: "#FFFFFF",
            bodyColor: "#8FA3BF",
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(255, 255, 255, 0.04)" },
            ticks: { color: "#8FA3BF", font: { size: 9 } },
          },
          y: {
            grid: { color: "rgba(255, 255, 255, 0.04)" },
            ticks: { color: "#8FA3BF", font: { size: 9 }, stepSize: 1 },
            beginAtZero: true,
          },
        },
      },
    });
  }

  _initCategoryChart() {
    const ctx = document.getElementById("vehicleCategoryChart")?.getContext("2d");
    if (!ctx) return;

    this.categoryChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Cars", "Motorcycles", "Buses", "Trucks"],
        datasets: [
          {
            data: [0, 0, 0, 0],
            backgroundColor: ["#00BFFF", "#00D9A6", "#FFB020", "#FF3B4A"],
            borderWidth: 1,
            borderColor: "#102238",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: {
            position: "right",
            labels: { color: "#8FA3BF", font: { size: 10 }, boxWidth: 10 },
          },
        },
      },
    });
  }

  _initHourlyChart() {
    const ctx = document.getElementById("hourlyTrendsChart")?.getContext("2d");
    if (!ctx) return;

    this.hourlyChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"],
        datasets: [
          {
            label: "Vehicle Volume",
            data: [12, 19, 45, 68, 52, 34],
            backgroundColor: "rgba(0, 191, 255, 0.4)",
            borderColor: "#00BFFF",
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#8FA3BF", font: { size: 9 } },
          },
          y: {
            grid: { color: "rgba(255, 255, 255, 0.04)" },
            ticks: { color: "#8FA3BF", font: { size: 9 } },
            beginAtZero: true,
          },
        },
      },
    });
  }

  updateFlowData(inbound, outbound) {
    if (!this.flowChart) return;
    const timeLabel = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    
    this.flowChart.data.labels.shift();
    this.flowChart.data.labels.push(timeLabel);

    this.flowChart.data.datasets[0].data.shift();
    this.flowChart.data.datasets[0].data.push(inbound);

    this.flowChart.data.datasets[1].data.shift();
    this.flowChart.data.datasets[1].data.push(outbound);

    this.flowChart.update("none");
  }

  updateCategoryData(cars, motos, buses, trucks) {
    if (!this.categoryChart) return;
    this.categoryChart.data.datasets[0].data = [cars, motos, buses, trucks];
    this.categoryChart.update();
  }

  updateHourlyTrends(hourlyData) {
    if (!this.hourlyChart || !hourlyData || !hourlyData.length) return;
    this.hourlyChart.data.labels = hourlyData.map(h => h.hour_bucket);
    this.hourlyChart.data.datasets[0].data = hourlyData.map(h => h.max_vehicles || 0);
    this.hourlyChart.update();
  }
}
