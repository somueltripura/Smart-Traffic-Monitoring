/**
 * Smart Traffic Monitoring System - Futuristic Canvas Gauges
 */

class DensityGauge {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.currentValue = 0;
    this.targetValue = 0;
    this.animationFrame = null;
    this._initCanvas();
  }

  _initCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = (rect.width || 140) * dpr;
    this.canvas.height = (rect.height || 140) * dpr;
    this.ctx.scale(dpr, dpr);
    this.width = rect.width || 140;
    this.height = rect.height || 140;
    this.draw(0, "Low");
  }

  update(percentage, level = "Low") {
    this.targetValue = Math.max(0, Math.min(100, percentage));
    this.level = level;
    this._animate();
  }

  _animate() {
    cancelAnimationFrame(this.animationFrame);
    const step = () => {
      const diff = this.targetValue - this.currentValue;
      if (Math.abs(diff) < 0.2) {
        this.currentValue = this.targetValue;
        this.draw(this.currentValue, this.level);
      } else {
        this.currentValue += diff * 0.15;
        this.draw(this.currentValue, this.level);
        this.animationFrame = requestAnimationFrame(step);
      }
    };
    step();
  }

  draw(value, level) {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const cx = this.width / 2;
    const cy = this.height / 2;
    const radius = this.width * 0.38;
    const lineWidth = 10;

    ctx.clearRect(0, 0, this.width, this.height);

    // Track arc
    const startAngle = 0.75 * Math.PI;
    const endAngle = 2.25 * Math.PI;
    const totalSweep = 1.5 * Math.PI;

    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = "rgba(16, 34, 56, 0.9)";
    ctx.lineWidth = lineWidth;
    ctx.lineCap = "round";
    ctx.stroke();

    // Value Arc Color
    let strokeColor = "#00D9A6"; // Low
    if (value >= 70) {
      strokeColor = "#FF3B4A"; // High
    } else if (value >= 35) {
      strokeColor = "#FFB020"; // Medium
    }

    const valueSweep = (value / 100) * totalSweep;
    const currentEnd = startAngle + valueSweep;

    if (value > 0) {
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, currentEnd);
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";
      ctx.shadowBlur = 12;
      ctx.shadowColor = strokeColor;
      ctx.stroke();
      ctx.shadowBlur = 0; // reset
    }

    // Center readout
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    ctx.fillStyle = "#FFFFFF";
    ctx.font = "bold 20px -apple-system, BlinkMacSystemFont, monospace";
    ctx.fillText(`${Math.round(value)}%`, cx, cy - 2);

    ctx.fillStyle = strokeColor;
    ctx.font = "bold 10px -apple-system, BlinkMacSystemFont, monospace";
    ctx.fillText(level.toUpperCase(), cx, cy + 18);
  }
}

class SpeedGauge {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");
    this.currentSpeed = 0;
    this.targetSpeed = 0;
    this.isCalibrated = false;
    this.animationFrame = null;
    this._initCanvas();
  }

  _initCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = (rect.width || 140) * dpr;
    this.canvas.height = (rect.height || 140) * dpr;
    this.ctx.scale(dpr, dpr);
    this.width = rect.width || 140;
    this.height = rect.height || 140;
    this.draw(null, false);
  }

  update(speedKmh, isCalibrated = false) {
    this.isCalibrated = isCalibrated;
    this.targetSpeed = isCalibrated && speedKmh !== null ? Math.max(0, Math.min(140, speedKmh)) : 0;
    this._animate();
  }

  _animate() {
    cancelAnimationFrame(this.animationFrame);
    const step = () => {
      const diff = this.targetSpeed - this.currentSpeed;
      if (Math.abs(diff) < 0.2) {
        this.currentSpeed = this.targetSpeed;
        this.draw(this.isCalibrated ? this.currentSpeed : null, this.isCalibrated);
      } else {
        this.currentSpeed += diff * 0.15;
        this.draw(this.isCalibrated ? this.currentSpeed : null, this.isCalibrated);
        this.animationFrame = requestAnimationFrame(step);
      }
    };
    step();
  }

  draw(speed, isCalibrated) {
    if (!this.ctx) return;
    const ctx = this.ctx;
    const cx = this.width / 2;
    const cy = this.height / 2;
    const radius = this.width * 0.38;
    const lineWidth = 10;

    ctx.clearRect(0, 0, this.width, this.height);

    const startAngle = 0.75 * Math.PI;
    const endAngle = 2.25 * Math.PI;
    const totalSweep = 1.5 * Math.PI;

    // Background track
    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = "rgba(16, 34, 56, 0.9)";
    ctx.lineWidth = lineWidth;
    ctx.lineCap = "round";
    ctx.stroke();

    if (isCalibrated && speed !== null && speed > 0) {
      const valueSweep = (speed / 140) * totalSweep;
      const currentEnd = startAngle + valueSweep;

      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, currentEnd);
      ctx.strokeStyle = "#00BFFF";
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";
      ctx.shadowBlur = 12;
      ctx.shadowColor = "#00BFFF";
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    if (isCalibrated && speed !== null) {
      ctx.fillStyle = "#FFFFFF";
      ctx.font = "bold 19px -apple-system, BlinkMacSystemFont, monospace";
      ctx.fillText(`${Math.round(speed)}`, cx, cy - 2);

      ctx.fillStyle = "#00BFFF";
      ctx.font = "bold 9px -apple-system, BlinkMacSystemFont, monospace";
      ctx.fillText("KM / H", cx, cy + 18);
    } else {
      ctx.fillStyle = "#8FA3BF";
      ctx.font = "bold 13px -apple-system, BlinkMacSystemFont, monospace";
      ctx.fillText("UNSET", cx, cy - 2);

      ctx.fillStyle = "#FFB020";
      ctx.font = "bold 9px -apple-system, BlinkMacSystemFont, monospace";
      ctx.fillText("UNCALIBRATED", cx, cy + 16);
    }
  }
}
