/**
 * Weather Forecast & Alert Application — Executive Web Dashboard Logic
 * Role Alignment: Frontend Data Integration & PowerBI Chart.js Architecture
 * Pure Client-Side JavaScript (GitHub Pages Compatible)
 */

(function () {
  "use strict";

  // Dashboard Global State
  let weatherData = null;
  let currentUnit = "C"; // "C" or "F"
  let selectedDay = null; // null (default first 24h) or "YYYY-MM-DD"
  let selectedCategory = "ALL"; // "ALL" or specific category

  // Chart.js Instances Registry for Clean Lifecycle Management
  const charts = {
    hourlyTemp: null,
    hourlyPrecip: null,
    hourlyWind: null,
    hourlyHumidity: null,
    dailyTemp: null,
    dailyPrecip: null,
  };

  // Color Palette Constants
  const THEME = {
    blue: "#2563EB",
    cyan: "#0284C7",
    amber: "#D97706",
    teal: "#0D9488",
    indigo: "#4F46E5",
    line: "#E2E8F0",
    ink: "#0F172A",
    muted: "#64748B",
    critical: "#EF4444",
    warning: "#F59E0B",
    advisory: "#EAB308",
    nominal: "#10B981",
  };

  // ---------------------------------------------------------------------------
  // Utility & Conversion Helpers
  // ---------------------------------------------------------------------------
  function cToF(c) {
    if (c === null || c === undefined || isNaN(c)) return null;
    return (c * 9) / 5 + 32;
  }

  function convertTemp(c) {
    if (c === null || c === undefined || isNaN(c)) return null;
    return currentUnit === "F" ? cToF(c) : c;
  }

  function formatTemp(c, withUnit = true) {
    const val = convertTemp(c);
    if (val === null) return "--";
    return val.toFixed(1) + (withUnit ? `°${currentUnit}` : "°");
  }

  function dateOnly(iso) {
    if (!iso) return "";
    return iso.split("T")[0];
  }

  function hourOnly(iso) {
    if (!iso || !iso.includes("T")) return "";
    const timePart = iso.split("T")[1];
    return timePart.substring(0, 5);
  }

  function parseLocalDate(iso) {
    if (!iso) return null;
    const clean = iso.split("T")[0];
    const parts = clean.split("-").map(Number);
    if (parts.length < 3 || isNaN(parts[0])) return new Date(iso);
    return new Date(parts[0], parts[1] - 1, parts[2], 12, 0, 0);
  }

  function formatWeekday(iso) {
    const d = parseLocalDate(iso);
    if (!d) return "";
    return d.toLocaleDateString("en-US", { weekday: "short" });
  }

  function formatShortDate(iso) {
    const d = parseLocalDate(iso);
    if (!d) return "";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function destroyChart(key) {
    if (charts[key]) {
      charts[key].destroy();
      charts[key] = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Data Loading & Initialization
  // ---------------------------------------------------------------------------
  async function loadWeatherData() {
    try {
      const response = await fetch("./weather_data.json");
      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
      }
      weatherData = await response.json();
    } catch (err) {
      console.warn("Could not fetch ./weather_data.json:", err);
      renderErrorState(err);
      return;
    }

    waitForChartAndInit();
  }

  function waitForChartAndInit(retries = 20) {
    if (typeof Chart !== "undefined") {
      try {
        initDashboard();
      } catch (err) {
        console.error("Dashboard initialization error:", err);
        renderChartError(err);
      }
    } else if (retries > 0) {
      setTimeout(() => waitForChartAndInit(retries - 1), 100);
    } else {
      renderChartError(new Error("Chart.js visualization library could not be loaded."));
    }
  }

  function renderChartError(err) {
    const container = document.querySelector(".dashboard-container");
    if (!container) return;
    const msg = document.createElement("div");
    msg.style.margin = "20px auto";
    msg.style.padding = "16px 24px";
    msg.style.background = "#FEF3C7";
    msg.style.border = "1.5px solid #F59E0B";
    msg.style.borderRadius = "12px";
    msg.style.maxWidth = "800px";
    msg.style.textAlign = "center";
    msg.innerHTML = `
      <h3 style="color:#92400E; font-family:'Outfit',sans-serif; font-size:16px; margin-bottom:4px;">
        Visualization Component Warning
      </h3>
      <p style="color:#B45309; font-size:12.5px;">
        ${err.message} Please check your connection and refresh the browser.
      </p>
    `;
    container.prepend(msg);
  }

  function renderErrorState(err) {
    const container = document.querySelector(".dashboard-container");
    if (!container) return;
    const msg = document.createElement("div");
    msg.style.margin = "40px auto";
    msg.style.padding = "24px 32px";
    msg.style.background = "#FEF2F2";
    msg.style.border = "1.5px solid #EF4444";
    msg.style.borderRadius = "16px";
    msg.style.maxWidth = "800px";
    msg.style.textAlign = "center";
    msg.innerHTML = `
      <h3 style="color:#991B1B; font-family:'Outfit',sans-serif; font-size:18px; margin-bottom:8px;">
        Unable to Load Dashboard Data (weather_data.json)
      </h3>
      <p style="color:#B91C1C; font-size:13px; line-height:1.6; margin-bottom:14px;">
        ${err.message}. If opening locally via <code>file://</code>, local browser security blocks JSON fetch.
      </p>
      <div style="background:#FFFFFF; padding:12px 18px; border-radius:10px; font-family:'Space Mono',monospace; font-size:12px; color:#1F2937; display:inline-block;">
        python -m http.server 8000 --directory docs
      </div>
      <p style="color:#6B7280; font-size:12px; margin-top:10px;">
        Then open <b>http://localhost:8000</b> in your browser.
      </p>
    `;
    container.prepend(msg);
  }

  // ---------------------------------------------------------------------------
  // Top Level Dashboard Controller
  // ---------------------------------------------------------------------------
  function initDashboard() {
    if (!weatherData) return;

    renderHeader();
    renderCurrentKPIs();
    renderControls();
    renderHourlyCharts();
    renderDailyCharts();
    renderAlertsPanel();
    renderFooter();
  }

  // ---------------------------------------------------------------------------
  // Section 1: Header Metadata
  // ---------------------------------------------------------------------------
  function renderHeader() {
    const meta = weatherData.metadata || {};
    const curr = weatherData.current || {};

    const titleEl = document.getElementById("headerCityTitle");
    if (titleEl) {
      titleEl.textContent = `${meta.city_name || "Mumbai"}, ${meta.country_code || "IN"}`;
    }

    const subEl = document.getElementById("headerSubtitle");
    if (subEl) {
      const genTime = meta.generated_at ? new Date(meta.generated_at).toLocaleString() : "Live";
      subEl.textContent = `Coordinates: ${meta.latitude?.toFixed(4)}°N, ${meta.longitude?.toFixed(4)}°E · Timezone: ${curr.timezone || "Asia/Kolkata"} · Updated: ${genTime}`;
    }

    const badgeEl = document.getElementById("headerBadge");
    if (badgeEl) {
      badgeEl.innerHTML = `
        <div><strong>ELEVATION:</strong> ${meta.elevation || 0} m</div>
        <div><strong>RECORDS:</strong> ${meta.total_records || 0} normalized</div>
        <div style="color:#38BDF8;"><strong>STATUS:</strong> ${meta.max_alert_severity || "NONE"}</div>
      `;
    }
  }

  // ---------------------------------------------------------------------------
  // Section 2: Top Current Conditions (4-5 Compact KPIs)
  // ---------------------------------------------------------------------------
  function renderCurrentKPIs() {
    const curr = weatherData.current || {};
    const meta = weatherData.metadata || {};

    // 1. Current Temperature
    const tempValEl = document.getElementById("kpiTempVal");
    const tempSubEl = document.getElementById("kpiTempSub");
    if (tempValEl) tempValEl.textContent = formatTemp(curr.temp_celsius);
    if (tempSubEl) {
      if (curr.heat_index_celsius !== null) {
        tempSubEl.textContent = `Heat Index: ${formatTemp(curr.heat_index_celsius)}`;
      } else if (curr.wind_chill_celsius !== null) {
        tempSubEl.textContent = `Wind Chill: ${formatTemp(curr.wind_chill_celsius)}`;
      } else {
        tempSubEl.textContent = `Heat Index: Not applicable`;
      }
    }

    // 2. Feels-Like Temperature
    const feelsValEl = document.getElementById("kpiFeelsVal");
    const feelsSubEl = document.getElementById("kpiFeelsSub");
    if (feelsValEl) feelsValEl.textContent = formatTemp(curr.apparent_temp_celsius);
    if (feelsSubEl) {
      const diff = curr.apparent_temp_celsius - curr.temp_celsius;
      feelsSubEl.textContent = diff >= 0 ? `+${diff.toFixed(1)}° offset vs ambient` : `${diff.toFixed(1)}° offset vs ambient`;
    }

    // 3. Humidity
    const humValEl = document.getElementById("kpiHumidityVal");
    const humSubEl = document.getElementById("kpiHumiditySub");
    if (humValEl) humValEl.textContent = curr.humidity_pct !== null ? `${curr.humidity_pct}%` : "--";
    if (humSubEl) {
      humSubEl.textContent = curr.pressure_hpa ? `Pressure: ${curr.pressure_hpa} hPa` : "Atmospheric Moisture";
    }

    // 4. Wind Speed
    const windValEl = document.getElementById("kpiWindVal");
    const windSubEl = document.getElementById("kpiWindSub");
    if (windValEl) windValEl.textContent = curr.wind_speed_kmh !== null ? `${curr.wind_speed_kmh} km/h` : "--";
    if (windSubEl) {
      windSubEl.textContent = curr.wind_direction_deg !== null ? `Direction: ${curr.wind_direction_deg}°` : "10m Sustained Wind";
    }

    // 5. Current Weather Condition / Alert Status
    const statusValEl = document.getElementById("kpiStatusVal");
    const statusPillEl = document.getElementById("kpiStatusPill");
    if (statusValEl) {
      statusValEl.textContent = curr.weather_category || "Nominal";
    }
    if (statusPillEl) {
      const sev = meta.max_alert_severity || curr.alert_severity || "NONE";
      statusPillEl.className = "status-pill";
      if (sev === "CRITICAL") statusPillEl.classList.add("status-critical");
      else if (sev === "WARNING") statusPillEl.classList.add("status-warning");
      else if (sev === "ADVISORY") statusPillEl.classList.add("status-advisory");
      else statusPillEl.classList.add("status-nominal");

      statusPillEl.innerHTML = `<span class="status-indicator-dot"></span> Severity: ${sev}`;
    }
  }

  // ---------------------------------------------------------------------------
  // Section 3: Interactive Controls (Day Strip, Category Pills, Units)
  // ---------------------------------------------------------------------------
  function renderControls() {
    renderDayStrip();
    setupCategoryFilters();
    setupUnitToggle();
    setupResetButton();
  }

  function renderDayStrip() {
    const stripEl = document.getElementById("dayStrip");
    if (!stripEl) return;
    stripEl.innerHTML = "";

    const daily = weatherData.daily || [];
    const hourly = weatherData.hourly || [];

    // Pill 1: "Default 24h"
    const allPill = document.createElement("div");
    allPill.className = `day-pill ${selectedDay === null ? "active" : ""}`;
    allPill.innerHTML = `
      <div class="day-pill-name">Next 24h</div>
      <div class="day-pill-range">Live Rolling</div>
      <div class="day-pill-desc">Hourly Focus</div>
    `;
    allPill.addEventListener("click", () => {
      selectedDay = null;
      updateActiveDayPill();
      renderHourlyCharts();
    });
    stripEl.appendChild(allPill);

    // 7 Daily Outlook Pills
    daily.forEach((d) => {
      const isoDate = dateOnly(d.timestamp_iso);
      const dayHourlyCount = hourly.filter((h) => dateOnly(h.timestamp_iso) === isoDate).length;
      const pill = document.createElement("div");
      pill.className = `day-pill ${selectedDay === isoDate ? "active" : ""}`;
      pill.dataset.date = isoDate;
      pill.innerHTML = `
        <div class="day-pill-name">${formatWeekday(d.timestamp_iso)} (${formatShortDate(d.timestamp_iso)})</div>
        <div class="day-pill-range">${formatTemp(d.temp_min_celsius, false)} - ${formatTemp(d.temp_max_celsius)}</div>
        <div class="day-pill-desc">${d.weather_category || "Clear"}${dayHourlyCount === 0 ? " · (0h)" : ""}</div>
      `;
      pill.addEventListener("click", () => {
        selectedDay = isoDate;
        updateActiveDayPill();
        renderHourlyCharts();
      });
      stripEl.appendChild(pill);
    });
  }

  function updateActiveDayPill() {
    const pills = document.querySelectorAll("#dayStrip .day-pill");
    pills.forEach((p) => {
      if (selectedDay === null && p.querySelector(".day-pill-name")?.textContent === "Next 24h") {
        p.classList.add("active");
      } else if (p.dataset.date === selectedDay) {
        p.classList.add("active");
      } else {
        p.classList.remove("active");
      }
    });
  }

  function setupCategoryFilters() {
    const btns = document.querySelectorAll(".cat-btn");
    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const clickedCat = btn.dataset.cat || "ALL";
        // Toggle behavior: clicking already active category toggles back to ALL
        if (selectedCategory === clickedCat && clickedCat !== "ALL") {
          selectedCategory = "ALL";
        } else {
          selectedCategory = clickedCat;
        }
        updateCategoryButtonUI();
        renderHourlyCharts();
      });
    });
  }

  function updateCategoryButtonUI() {
    const btns = document.querySelectorAll(".cat-btn");
    btns.forEach((b) => {
      const cat = b.dataset.cat || "ALL";
      if (cat === selectedCategory) {
        b.classList.add("active");
      } else {
        b.classList.remove("active");
      }
    });

    const tagEl = document.getElementById("activeFilterTag");
    if (tagEl) {
      if (selectedCategory !== "ALL") {
        tagEl.style.display = "inline-flex";
        tagEl.innerHTML = `Active Filter: <strong>${selectedCategory}</strong> <span class="filter-clear-x" title="Clear hourly filter">&times;</span>`;
        const clearX = tagEl.querySelector(".filter-clear-x");
        if (clearX) {
          clearX.onclick = (e) => {
            e.stopPropagation();
            selectedCategory = "ALL";
            updateCategoryButtonUI();
            renderHourlyCharts();
          };
        }
      } else {
        tagEl.style.display = "none";
      }
    }
  }

  function setupUnitToggle() {
    const btns = document.querySelectorAll(".unit-btn");
    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const targetUnit = btn.dataset.unit;
        if (targetUnit === currentUnit) return;
        currentUnit = targetUnit;

        btns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        // Re-render components with new temperature unit
        renderCurrentKPIs();
        renderDayStrip();
        renderHourlyCharts();
        renderDailyCharts();
      });
    });
  }

  function setupResetButton() {
    const resetBtn = document.getElementById("resetFiltersBtn");
    if (!resetBtn) return;
    resetBtn.addEventListener("click", () => {
      selectedDay = null;
      selectedCategory = "ALL";

      updateCategoryButtonUI();
      updateActiveDayPill();
      renderHourlyCharts();
    });
  }

  // ---------------------------------------------------------------------------
  // Section 4: Middle Hourly Forecast (4 Prioritized Charts & Empty States)
  // ---------------------------------------------------------------------------
  function getRolling24Rows() {
    const all = weatherData?.hourly || [];
    if (!all.length) return [];

    const currIso = weatherData?.current?.timestamp_iso;
    if (currIso) {
      const currHourPrefix = currIso.substring(0, 13);
      const matchIdx = all.findIndex((r) => r.timestamp_iso && r.timestamp_iso >= currHourPrefix);
      if (matchIdx !== -1) {
        return all.slice(matchIdx, matchIdx + 24);
      }
    }
    return all.slice(0, 24);
  }

  function getBaseHourly() {
    const all = weatherData?.hourly || [];
    if (selectedDay !== null) {
      return all.filter((r) => dateOnly(r.timestamp_iso) === selectedDay);
    }
    return getRolling24Rows();
  }

  function getFilteredHourly() {
    let rows = getBaseHourly();
    if (selectedCategory !== "ALL") {
      rows = rows.filter((r) => r.weather_category === selectedCategory);
    }
    return rows;
  }

  function renderHourlyCharts() {
    const baseRows = getBaseHourly();
    const rows = getFilteredHourly();
    const chartGridEl = document.getElementById("hourlyChartGrid");
    const emptyStateEl = document.getElementById("hourlyEmptyState");
    const badgeEl = document.getElementById("hourlyBadge");

    // Case 1: Zero timesteps available — Display clear, compact empty state
    if (rows.length === 0) {
      // Destroy any existing chart instances to avoid residual blank axes
      destroyChart("hourlyTemp");
      destroyChart("hourlyPrecip");
      destroyChart("hourlyWind");
      destroyChart("hourlyHumidity");

      if (chartGridEl) chartGridEl.style.display = "none";
      if (emptyStateEl) {
        emptyStateEl.style.display = "flex";
        const iconEl = document.getElementById("emptyStateIcon");
        const titleEl = document.getElementById("emptyStateTitle");
        const descEl = document.getElementById("emptyStateDesc");
        const fallbackBtn = document.getElementById("emptyStateFallbackBtn");
        const resetFilterBtn = document.getElementById("emptyStateResetFilterBtn");

        const dayLabel = selectedDay
          ? `${formatWeekday(selectedDay)}, ${formatShortDate(selectedDay)}`
          : "the Next 24h rolling period";

        if (baseRows.length === 0) {
          // Selected date has truly 0 hourly records in the dataset
          if (iconEl) iconEl.textContent = "📅";
          if (titleEl) titleEl.textContent = "Hourly data unavailable for this day";
          if (descEl) descEl.textContent = `No hourly observations are available for ${dayLabel}.`;
          if (fallbackBtn) {
            fallbackBtn.style.display = "inline-flex";
            fallbackBtn.textContent = "Switch to Next 24h / Live Rolling";
            fallbackBtn.onclick = () => {
              selectedDay = null;
              updateActiveDayPill();
              renderHourlyCharts();
            };
          }
          if (resetFilterBtn) resetFilterBtn.style.display = "none";
          if (badgeEl) badgeEl.textContent = `Viewing: ${selectedDay || "Selected Day"} (0 timesteps · Unavailable)`;
        } else {
          // Date has hourly records, but category filter matched 0
          if (iconEl) iconEl.textContent = "🔍";
          if (titleEl) titleEl.textContent = `No hourly records matching "${selectedCategory}"`;
          if (descEl) descEl.textContent = `No ${selectedCategory.toLowerCase()} observations found for ${dayLabel} (${baseRows.length} total hourly observations available).`;
          if (resetFilterBtn) {
            resetFilterBtn.style.display = "inline-flex";
            resetFilterBtn.textContent = `Show All Conditions (${baseRows.length} timesteps)`;
            resetFilterBtn.onclick = () => {
              selectedCategory = "ALL";
              updateCategoryButtonUI();
              renderHourlyCharts();
            };
          }
          if (fallbackBtn) {
            fallbackBtn.style.display = "inline-flex";
            fallbackBtn.textContent = "Switch to Next 24h / Live Rolling";
            fallbackBtn.onclick = () => {
              selectedDay = null;
              updateActiveDayPill();
              renderHourlyCharts();
            };
          }
          if (badgeEl) {
            const scopeName = selectedDay ? selectedDay : "Rolling 24 Hours";
            badgeEl.textContent = `Viewing: ${scopeName} · Filter: ${selectedCategory} (0 timesteps)`;
          }
        }
      }
      return;
    }

    // Case 2: Timesteps exist — Render the 4 prioritized charts normally
    if (emptyStateEl) emptyStateEl.style.display = "none";
    if (chartGridEl) chartGridEl.style.display = "grid";

    const labels = rows.map((r) =>
      selectedDay ? hourOnly(r.timestamp_iso) : `${formatWeekday(r.timestamp_iso)} ${hourOnly(r.timestamp_iso)}`
    );

    // Update Section Subtitle Badge
    if (badgeEl) {
      const scopeLabel = selectedDay ? selectedDay : "Rolling 24 Hours";
      const filterLabel = selectedCategory !== "ALL" ? ` · Filter: ${selectedCategory}` : "";
      badgeEl.textContent = `Viewing: ${scopeLabel}${filterLabel} (${rows.length} timesteps)`;
    }

    renderHourlyTempChart(labels, rows);
    renderHourlyPrecipChart(labels, rows);
    renderHourlyWindChart(labels, rows);
    renderHourlyHumidityChart(labels, rows);
  }

  // 1. 24-Hour Temperature Line Chart
  function renderHourlyTempChart(labels, rows) {
    destroyChart("hourlyTemp");
    const ctx = document.getElementById("chartHourlyTemp");
    if (!ctx) return;

    const actualTemps = rows.map((r) => convertTemp(r.temp_celsius));
    const feelsTemps = rows.map((r) => convertTemp(r.apparent_temp_celsius));

    charts.hourlyTemp = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: `Actual Temp (°${currentUnit})`,
            data: actualTemps,
            borderColor: THEME.blue,
            backgroundColor: "rgba(37, 99, 235, 0.08)",
            borderWidth: 2.5,
            pointRadius: 1,
            pointHoverRadius: 5,
            fill: true,
            tension: 0.35,
          },
          {
            label: `Feels Like (°${currentUnit})`,
            data: feelsTemps,
            borderColor: THEME.amber,
            borderDash: [4, 4],
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            fill: false,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", labels: { boxWidth: 10, font: { size: 11 } } },
          tooltip: {
            callbacks: {
              label: (c) => `${c.dataset.label}: ${c.parsed.y !== null ? c.parsed.y.toFixed(1) + "°" + currentUnit : "--"}`,
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
          y: { grid: { color: THEME.line }, ticks: { callback: (v) => v + "°" } },
        },
      },
    });
  }

  // 2. 24-Hour Precipitation Bar Chart
  function renderHourlyPrecipChart(labels, rows) {
    destroyChart("hourlyPrecip");
    const ctx = document.getElementById("chartHourlyPrecip");
    if (!ctx) return;

    const amounts = rows.map((r) => r.precip_amount_mm || 0);
    const probs = rows.map((r) => r.precip_prob_pct || 0);
    const maxAmount = Math.max(...amounts, 0);
    const maxProb = Math.max(...probs, 0);
    const isDry = maxAmount <= 0.05 && maxProb <= 5;

    // Update Header Badge
    const badgeEl = document.getElementById("precipStatusBadge");
    if (badgeEl) {
      if (isDry) {
        badgeEl.textContent = "No precipitation expected";
        badgeEl.style.background = "rgba(16, 185, 129, 0.12)";
        badgeEl.style.color = "#059669";
        badgeEl.style.fontWeight = "600";
      } else {
        badgeEl.textContent = `Peak: ${maxAmount.toFixed(1)} mm (${maxProb}%)`;
        badgeEl.style.background = "#F1F5F9";
        badgeEl.style.color = "#64748B";
        badgeEl.style.fontWeight = "normal";
      }
    }

    // Update Footer Note
    const footerEl = document.getElementById("precipFooterNote");
    if (footerEl) {
      if (isDry) {
        footerEl.textContent = "Zero rainfall forecasted (0.0 mm) · Clear/Dry baseline";
      } else {
        footerEl.textContent = "Accumulation depth (mm) and precipitation chance (%)";
      }
    }

    charts.hourlyPrecip = new Chart(ctx, {
      data: {
        labels,
        datasets: [
          {
            type: "bar",
            label: "Precip Amount (mm)",
            data: amounts,
            backgroundColor: "rgba(2, 132, 199, 0.8)",
            borderRadius: 3,
            yAxisID: "y",
          },
          {
            type: "line",
            label: "Precip Probability (%)",
            data: probs,
            borderColor: THEME.indigo,
            borderWidth: 2,
            pointRadius: 1,
            fill: false,
            tension: 0.3,
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top", labels: { boxWidth: 10, font: { size: 11 } } },
          subtitle: {
            display: isDry,
            text: "No precipitation expected across this horizon (0.00 mm total)",
            color: "#64748B",
            font: { size: 11, style: "italic", weight: "500" },
            padding: { bottom: 6 },
          },
          tooltip: {
            callbacks: {
              label: (c) => (c.dataset.type === "bar" ? `Amount: ${c.parsed.y.toFixed(2)} mm` : `Probability: ${c.parsed.y}%`),
            },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
          y: {
            position: "left",
            min: 0,
            max: isDry ? 5 : undefined,
            grid: { color: THEME.line },
            title: { display: true, text: "mm", font: { size: 11 } },
          },
          y1: {
            position: "right",
            min: 0,
            max: 100,
            grid: { display: false },
            title: { display: true, text: "%", font: { size: 11 } },
          },
        },
      },
    });
  }

  // 3. 24-Hour Wind Speed Line Chart
  function renderHourlyWindChart(labels, rows) {
    destroyChart("hourlyWind");
    const ctx = document.getElementById("chartHourlyWind");
    if (!ctx) return;

    const winds = rows.map((r) => r.wind_speed_kmh);

    charts.hourlyWind = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Wind Speed (km/h)",
            data: winds,
            borderColor: THEME.teal,
            backgroundColor: "rgba(13, 148, 136, 0.12)",
            borderWidth: 2.2,
            pointRadius: 1,
            fill: true,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (c) => `Wind: ${c.parsed.y} km/h` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
          y: {
            grid: { color: THEME.line },
            title: { display: true, text: "km/h", font: { size: 11 } },
          },
        },
      },
    });
  }

  // 4. 24-Hour Humidity Line Chart
  function renderHourlyHumidityChart(labels, rows) {
    destroyChart("hourlyHumidity");
    const ctx = document.getElementById("chartHourlyHumidity");
    if (!ctx) return;

    const humids = rows.map((r) => r.humidity_pct);

    charts.hourlyHumidity = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Relative Humidity (%)",
            data: humids,
            borderColor: THEME.cyan,
            backgroundColor: "rgba(2, 132, 199, 0.1)",
            borderWidth: 2.2,
            pointRadius: 1,
            fill: true,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: (c) => `Humidity: ${c.parsed.y}%` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { size: 10 } } },
          y: {
            max: 100,
            grid: { color: THEME.line },
            title: { display: true, text: "%", font: { size: 11 } },
          },
        },
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Section 5: Bottom 7-Day Outlook & Weather Alerts
  // ---------------------------------------------------------------------------
  function renderDailyCharts() {
    const daily = weatherData.daily || [];
    if (daily.length === 0) {
      destroyChart("dailyTemp");
      destroyChart("dailyPrecip");
      return;
    }
    const labels = daily.map((d) => `${formatWeekday(d.timestamp_iso)} (${formatShortDate(d.timestamp_iso)})`);

    // 1. 7-Day Temperature Range Chart
    destroyChart("dailyTemp");
    const ctxTemp = document.getElementById("chartDailyTemp");
    if (ctxTemp) {
      const maxTemps = daily.map((d) => convertTemp(d.temp_max_celsius));
      const minTemps = daily.map((d) => convertTemp(d.temp_min_celsius));

      charts.dailyTemp = new Chart(ctxTemp, {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: `High (°${currentUnit})`,
              data: maxTemps,
              borderColor: THEME.amber,
              backgroundColor: THEME.amber,
              borderWidth: 2.5,
              pointRadius: 3,
              tension: 0.3,
            },
            {
              label: `Low (°${currentUnit})`,
              data: minTemps,
              borderColor: THEME.blue,
              backgroundColor: THEME.blue,
              borderWidth: 2.5,
              pointRadius: 3,
              tension: 0.3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: "top", labels: { boxWidth: 10, font: { size: 11 } } },
            tooltip: {
              callbacks: {
                label: (c) => `${c.dataset.label}: ${c.parsed.y !== null ? c.parsed.y.toFixed(1) + "°" + currentUnit : "--"}`,
              },
            },
          },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 } } },
            y: { grid: { color: THEME.line }, ticks: { callback: (v) => v + "°" } },
          },
        },
      });
    }

    // 2. 7-Day Daily Precipitation Bar Chart
    destroyChart("dailyPrecip");
    const ctxPrecip = document.getElementById("chartDailyPrecip");
    if (ctxPrecip) {
      const precipSums = daily.map((d) => d.precip_sum_daily_mm || 0);

      charts.dailyPrecip = new Chart(ctxPrecip, {
        type: "bar",
        data: {
          labels,
          datasets: [
            {
              label: "Daily Precipitation (mm)",
              data: precipSums,
              backgroundColor: "rgba(37, 99, 235, 0.75)",
              borderRadius: 4,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: { label: (c) => `Accumulation: ${c.parsed.y.toFixed(2)} mm` },
            },
          },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 } } },
            y: {
              grid: { color: THEME.line },
              title: { display: true, text: "mm", font: { size: 11 } },
            },
          },
        },
      });
    }
  }

  // 3. Weather Alerts Panel
  function renderAlertsPanel() {
    const listEl = document.getElementById("alertsList");
    const countBadge = document.getElementById("alertsCountBadge");
    const alertsCard = document.querySelector(".alerts-card");
    if (!listEl) return;

    listEl.innerHTML = "";
    const alerts = weatherData.alerts || [];

    if (alertsCard) {
      if (alerts.length > 0) {
        alertsCard.classList.add("has-alerts");
      } else {
        alertsCard.classList.remove("has-alerts");
      }
    }

    if (countBadge) {
      countBadge.textContent = `${alerts.length} Active`;
      countBadge.style.background = alerts.length > 0 ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)";
      countBadge.style.color = alerts.length > 0 ? "#DC2626" : "#059669";
    }

    if (alerts.length === 0) {
      listEl.innerHTML = `
        <div class="nominal-banner">
          <div class="nominal-icon">✓</div>
          <div class="nominal-title">All Systems Nominal</div>
          <div class="nominal-subtitle">Zero rule threshold exceedances across all current, hourly, and daily horizons.</div>
        </div>
      `;
      return;
    }

    // Display active alert cards
    alerts.forEach((a) => {
      const sev = (a.alert_severity || "ADVISORY").toLowerCase();
      const card = document.createElement("div");
      card.className = `alert-item-card sev-${sev}`;
      card.innerHTML = `
        <div class="alert-item-header">
          <span class="alert-type-badge">${a.alert_type || "ADVISORY"}</span>
          <span class="alert-time">${hourOnly(a.timestamp_iso) || dateOnly(a.timestamp_iso)}</span>
        </div>
        <div class="alert-desc">${a.weather_description || "Threshold Exceeded"}</div>
        <div class="alert-origin-tag">Origin: ${a.alert_origin || "APPLICATION_RULE_ENGINE"} · Severity: ${a.alert_severity}</div>
      `;
      listEl.appendChild(card);
    });
  }

  // ---------------------------------------------------------------------------
  // Section 6: Footer Attributions
  // ---------------------------------------------------------------------------
  function renderFooter() {
    const meta = weatherData.metadata || {};
    const credEl = document.getElementById("footerCredit");
    const discEl = document.getElementById("footerDisclaimer");
    const recEl = document.getElementById("footerRecords");

    if (credEl && meta.attribution) credEl.textContent = meta.attribution;
    if (discEl && meta.disclaimer) discEl.textContent = meta.disclaimer;
    if (recEl && meta.total_records) {
      recEl.textContent = `${meta.total_records} Verified Records`;
    }
  }

  // Start on DOM ready
  document.addEventListener("DOMContentLoaded", loadWeatherData);
})();
