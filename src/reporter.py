"""Automated Comprehensive Enterprise Report Generator Module.

Synthesizes three publication-grade reports:
1. reports/DETAILED_PROJECT_REPORT.md (Technical, mathematical, and architectural documentation)
2. reports/EXECUTIVE_SUMMARY_REPORT.md (Commercial, sector-impact, and decision-support briefing)
3. reports/weather_summary_report.txt (Plain-text meteorological bulletin)

Fully parameterized for test output isolation with pytest tmp_path.
Embeds mandatory CC BY 4.0 data attribution and non-official advisory disclaimers.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from src.config import (
    ALERT_DISCLAIMER_TEXT,
    ALERT_ORIGIN_TAG,
    ATTRIBUTION_NOTICE,
    NON_OFFICIAL_DISCLAIMER,
)


def _load_data(data_source: Union[str, Path, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Load normalized records from list or JSON filepath."""
    if isinstance(data_source, (str, Path)):
        p = Path(data_source)
        if not p.exists():
            raise FileNotFoundError(f"Processed dataset not found: {p}")
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    elif isinstance(data_source, list):
        return data_source
    else:
        raise ValueError("data_source must be a filepath string, Path, or list of dictionaries.")


def generate_detailed_project_report(
    processed_data: Union[str, Path, List[Dict[str, Any]]],
    output_path: Union[str, Path] = "reports/DETAILED_PROJECT_REPORT.md",
) -> str:
    """Generate comprehensive technical and architectural Markdown report."""
    records = _load_data(processed_data)
    curr = next((r for r in records if r.get("record_type") == "CURRENT"), {})
    hourly = [r for r in records if r.get("record_type") == "HOURLY"]
    daily = [r for r in records if r.get("record_type") == "DAILY"]
    alerts = [r for r in records if r.get("alert_flag")]

    city = curr.get("city_name", "Target Region")
    country = curr.get("country_code", "--")
    lat = curr.get("latitude", 0.0)
    lon = curr.get("longitude", 0.0)
    elev = curr.get("elevation", 0.0)
    timestamp = curr.get("timestamp_iso", curr.get("timestamp", datetime.now(timezone.utc).isoformat()))

    content = f"""# Detailed Project Report: Weather Forecast & Alert Application
**System Version**: 1.0.0 (Production Architecture)  
**Target Roles**: Python Developer | API Integration Specialist | Data Analyst | Automation Engineer  
**Dataset Evaluation Anchor**: {city}, {country} (Lat: {lat:.4f}°, Lon: {lon:.4f}°, Elev: {elev:.1f} m)  
**Generation Timestamp**: {timestamp}  

---

## 1. Executive & Technical Overview

The **Weather Forecast & Alert Application** is an enterprise-grade meteorological data ingestion, normalization, analytical evaluation, and alerting pipeline. Designed from the ground up to follow industry best practices, the application bridges backend data engineering with executive visual analytics.

### Core System Capabilities
1. **Dual-Engine Ingestion**:
   * **Live Open-Meteo REST Client**: Queries Open-Meteo Geocoding and Forecast APIs with zero API key requirement, defended by bounded exponential backoff retries, rate limit safety caps, and typed domain exceptions.
   * **Deterministic Simulator Engine**: Synthesizes schema-compliant meteorological payloads using an isolated `random.Random(seed=42)` and a fixed reference epoch (`2026-09-27T00:00:00Z`), guaranteeing cross-platform byte-for-byte reproducibility via binary write mode (`"wb"`).
2. **Standardized Normalization**:
   * Unpacks heterogeneous Open-Meteo arrays into a strictly partitioned 25-column Field Applicability Matrix (`CURRENT`, `HOURLY`, `DAILY`).
   * Decouples WMO interpretation codes with robust fallback for unknown or future codes.
   * Enforces strict null semantics where non-applicable physical variables are preserved as `None` / `null` rather than substituted with misleading zeros.
3. **Biometeorological Algorithms**:
   * Full 9-term polynomial **NOAA Rothfusz Heat Index** gated by an unambiguous Fahrenheit primary gate ($T_F \\ge 80.0^\\circ\\text{{F}}$).
   * **NWS Wind Chill** calculation with strict physical validity criteria ($T_C \\le 10^\\circ\\text{{C}}$, $V \\ge 4.8\\text{{ km/h}}$).
4. **Rule-Based Threshold Alert Engine**:
   * Independent partitioned evaluation with maximum severity precedence (`CRITICAL > WARNING > ADVISORY > NONE`).
   * Mandatory origin tagging (`{ALERT_ORIGIN_TAG}`) and prominent non-official advisory disclaimers.
5. **Multi-Format Analytics & Reporting**:
   * 300 DPI publication-grade Matplotlib figures (`forecast_trend_sample.png`, `meteorological_matrix.png`).
   * Client-side PowerBI-style interactive web dashboard (`docs/index.html`) deployed to GitHub Pages.
   * Automated executive Markdown and text bulletins.

---

## 2. Architecture & Data Pipeline

```
  ┌──────────────────────────────────────────────────────────────────┐
  │                   1. DATA INGESTION LAYER                        │
  │  Open-Meteo REST API (HTTP Client)  │  Deterministic Simulator   │
  │  Bounded retries, 429 safety caps   │  seed=42, fixed epoch      │
  └─────────────────────────────────┬────────────────────────────────┘
                                    │ Raw JSON Payload
                                    ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                 2. NORMALIZATION & ENRICHMENT                    │
  │  Field Applicability Partitioning (CURRENT, HOURLY, DAILY)       │
  │  Rothfusz Heat Index Gate ($T_F >= 80°F$) │ NWS Wind Chill       │
  │  Strict Null Semantics & WMO Decoder                             │
  └─────────────────────────────────┬────────────────────────────────┘
                                    │ Processed Datasets (CSV & JSON)
                                    ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                   3. RULE-BASED ALERT ENGINE                     │
  │  Partitioned Rule Evaluation (Rain, Frost, Heat, Gales, Discomf) │
  │  Precedence: CRITICAL > WARNING > ADVISORY > NONE                │
  │  Audit Log (weather_alerts.log) & History (alert_history.csv)    │
  └─────────────────────────────────┬────────────────────────────────┘
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼                                                     ▼
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│     4. VISUALIZATION ENGINE     │           │    5. PRESENTATION & AUDIT      │
│  Dual-Axis Trend Chart (300 DPI)│           │  PowerBI Dashboard (index.html) │
│  4-Panel Meteorological Matrix  │           │  Automated Enterprise Reports   │
└─────────────────────────────────┘           └─────────────────────────────────┘
```

---

## 3. Mathematical & Algorithmic Rigor

### 3.1 NOAA Rothfusz Heat Index Decision Flow
The apparent temperature due to relative humidity is calculated using the National Weather Service (NWS) Rothfusz regression equation:
$$\\text{{HI}} = -42.379 + 2.04901523 T_F + 10.14333127 RH - 0.22475541 T_F RH - 0.00683783 T_F^2 - 0.05481717 RH^2 + 0.00122874 T_F^2 RH + 0.00085282 T_F RH^2 - 0.00000199 T_F^2 RH^2$$

**Validity Gates & Adjustments**:
* **Primary Gate**: Evaluated strictly on Fahrenheit ($T_F \\ge 80.0^\\circ\\text{{F}}$). If $T_F < 80.0^\\circ\\text{{F}}$, Heat Index evaluates to `null` to avoid unphysical results.
* **Preliminary Steadman Formula**:
  $$\\text{{HI}}_{{\\text{{simple}}}} = 0.5 \\cdot [T_F + 61.0 + ((T_F - 68.0) \\cdot 1.2) + (RH \\cdot 0.094)]$$
* **Low Humidity Adjustment** ($RH < 13\\%$ and $80^\\circ\\text{{F}} \\le T_F \\le 112^\\circ\\text{{F}}$):
  $$\\text{{Adj}}_{{\\text{{low}}}} = -\\frac{{13 - RH}}{{4}} \\sqrt{{\\frac{{17 - |T_F - 95|}}{{17}}}}$$
* **High Humidity Adjustment** ($RH > 85\\%$ and $80^\\circ\\text{{F}} \\le T_F \\le 87^\\circ\\text{{F}}$):
  $$\\text{{Adj}}_{{\\text{{high}}}} = \\frac{{RH - 85}}{{10}} \\cdot \\frac{{87 - T_F}}{{5}}$$

### 3.2 NWS Wind Chill Temperature Index
$$\\text{{WC}} = 13.12 + 0.6215 T_C - 11.37 V^{{0.16}} + 0.3965 T_C V^{{0.16}}$$
* **Gating**: Strictly valid and computed only when $T_C \\le 10.0^\\circ\\text{{C}}$ and $V \\ge 4.8\\text{{ km/h}}$. Returns `null` outside these boundaries.

---

## 4. Current Synoptic Evaluation Summary

| Parameter | Current Value | Synoptic High (7d) | Synoptic Low (7d) | Units |
| :--- | :--- | :--- | :--- | :--- |
| **Dry-Bulb Temperature** | {curr.get('temp_celsius', '--')} | {max([d.get('temp_max_celsius', 0) for d in daily] or ['--'])} | {min([d.get('temp_min_celsius', 0) for d in daily] or ['--'])} | °C |
| **Apparent Temperature** | {curr.get('apparent_temp_celsius', '--')} | -- | -- | °C |
| **Relative Humidity** | {curr.get('humidity_pct', '--')} | -- | -- | % |
| **Surface Pressure** | {curr.get('pressure_hpa', '--')} | -- | -- | hPa |
| **10m Wind Speed** | {curr.get('wind_speed_kmh', '--')} | {max([d.get('wind_speed_max_kmh', 0) for d in daily] or ['--'])} | -- | km/h |
| **Precipitation Sum** | {curr.get('precip_current_mm', 0.0)} | {sum([d.get('precip_sum_daily_mm', 0.0) or 0.0 for d in daily]):.2f} (7d Total) | -- | mm |
| **Condition** | {curr.get('weather_description', 'Nominal')} | -- | -- | WMO {curr.get('wmo_code', '--')} |

---

## 5. Active Rule Alert Engine Audit

* **Total Records Evaluated**: {len(records)}
* **Active Advisories Triggered**: {len(alerts)}
* **Rule Engine Origin**: `{ALERT_ORIGIN_TAG}`
* **Operational Notice**:
  > {NON_OFFICIAL_DISCLAIMER}
  > {ALERT_DISCLAIMER_TEXT}

---

## 6. Mandatory Legal & Attribution Compliance

{ATTRIBUTION_NOTICE}  
Weather forecast data is ingested under the Creative Commons Attribution 4.0 International (CC BY 4.0) License from Open-Meteo.com.
"""

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    return str(out_file.resolve())


def generate_executive_summary_report(
    processed_data: Union[str, Path, List[Dict[str, Any]]],
    output_path: Union[str, Path] = "reports/EXECUTIVE_SUMMARY_REPORT.md",
) -> str:
    """Generate business-oriented executive summary report covering 5 commercial sectors."""
    records = _load_data(processed_data)
    curr = next((r for r in records if r.get("record_type") == "CURRENT"), {})
    daily = [r for r in records if r.get("record_type") == "DAILY"]
    alerts = [r for r in records if r.get("alert_flag")]

    city = curr.get("city_name", "Target Metropolitan Region")
    country = curr.get("country_code", "--")
    timestamp = curr.get("timestamp_iso", curr.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")))

    curr_temp = curr.get("temp_celsius", 0.0) or 0.0
    wind_speed = curr.get("wind_speed_kmh", 0.0) or 0.0
    total_rain_7d = sum([d.get("precip_sum_daily_mm", 0.0) or 0.0 for d in daily])
    max_wind_7d = max([d.get("wind_speed_max_kmh", 0.0) or 0.0 for d in daily] or [0.0])

    content = f"""# Executive Summary Report: Meteorological Impact & Operations
**Location Target**: {city}, {country}  
**Report Date**: {timestamp}  
**Classification**: Operational Management & Risk Assessment  
**Advisory Level**: {curr.get('alert_severity', 'NOMINAL')}  

---

## 1. Executive Meteorological Briefing

This briefing provides senior operational decision-makers with high-impact meteorological intelligence for **{city}**, synthesizing synoptic forecast trends, threshold exceedance advisories, and cross-sector operational risk assessments.

### Key Executive Metrics
* **Current Operational Temperature**: **{curr_temp:.1f}°C** (Feels Like: **{curr.get('apparent_temp_celsius', curr_temp):.1f}°C**)
* **Current 10m Wind Velocity**: **{wind_speed:.1f} km/h** (Peak 7-day gust: **{max_wind_7d:.1f} km/h**)
* **Cumulative 7-Day Precipitation**: **{total_rain_7d:.2f} mm**
* **Active Advisory Events**: **{len(alerts)} alerts** across the 7-day outlook

---

## 2. Cross-Sector Commercial Impact Analysis

### 🚚 1. Logistics, Fleet & Supply Chain Operations
* **Risk Assessment**: {('ELEVATED' if max_wind_7d >= 50 or total_rain_7d >= 30 else 'LOW / NOMINAL')}
* **Operational Guidance**:
  * High-profile freight vehicles face increased lateral drag when crosswinds exceed 45 km/h.
  * Cold chain perishable transport must maintain active temperature buffer monitoring if ambient temperatures fluctuate outside nominal bounds.
  * Route dispatchers should prepare contingency routing around low-lying regional corridors vulnerable to localized hydroplaning.

### 🌾 2. Agriculture, Horticulture & Irrigation
* **Risk Assessment**: {('CRITICAL / FROST WATCH' if curr_temp <= 4 else ('HEAT STRESS' if curr_temp >= 35 else 'OPTIMAL'))}
* **Operational Guidance**:
  * Cumulative rainfall projection of {total_rain_7d:.1f} mm informs precision automated drip-irrigation schedules.
  * Crop canopy moisture levels must be balanced against fungal spore incubation thresholds.
  * Early-morning ground frost prevention protocols should remain on standby during colder seasons.

### ✈️ 3. Aviation, Marine & Port Operations
* **Risk Assessment**: {('WARNING - GALE PROTOCOL' if max_wind_7d >= 50 else 'CLEAR / OPERATIONAL')}
* **Operational Guidance**:
  * Container crane operations must enforce mandatory hoisting limits if sustained wind gusts exceed 50 km/h.
  * Approach trajectories and terminal area operations should account for diurnal boundary layer thermal inversions.

### 🏗️ 4. Construction, Infrastructure & Outdoor Civil Engineering
* **Risk Assessment**: {('MODERATE WORKPLACE RISK' if curr_temp >= 32 or max_wind_7d >= 40 else 'LOW HAZARD')}
* **Operational Guidance**:
  * Outdoor concrete curing and asphalt pouring operations require rain-free windows; precipitation outlook indicates {total_rain_7d:.1f} mm total accumulation.
  * Tower cranes and suspended scaffolding require mandatory wind tie-offs prior to peak gust periods.
  * Worker hydration and heat-stress rest cycle rotations must be mandated if Heat Index exceeds 32°C.

### 🎉 5. Event Planning, Hospitality & Public Venues
* **Risk Assessment**: {('CONTINGENCY REQUIRED' if total_rain_7d >= 20 else 'FAVORABLE OUTLOOK')}
* **Operational Guidance**:
  * Outdoor events should prepare marquee anchoring and rain-cover contingency plans.
  * Audience comfort and hydration stations should be provisioned in accordance with thermal indices.

---

## 3. Active Rule Alerts & Disclaimer Notice

* **Evaluated Advisories**: {len(alerts)} active event(s) recorded in operational logs.
* **Origin**: `{ALERT_ORIGIN_TAG}`
* **Standard Advisory Disclaimer**:
  > **{NON_OFFICIAL_DISCLAIMER}**  
  > {ALERT_DISCLAIMER_TEXT}

---

## 4. Legal & Open Data Attribution

{ATTRIBUTION_NOTICE}
"""

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    return str(out_file.resolve())


def generate_weather_summary_report(
    processed_data: Union[str, Path, List[Dict[str, Any]]],
    output_path: Union[str, Path] = "reports/weather_summary_report.txt",
) -> str:
    """Generate structured plain-text ASCII meteorological bulletin."""
    records = _load_data(processed_data)
    curr = next((r for r in records if r.get("record_type") == "CURRENT"), {})
    daily = [r for r in records if r.get("record_type") == "DAILY"]
    alerts = [r for r in records if r.get("alert_flag")]

    city = curr.get("city_name", "Target Region")
    country = curr.get("country_code", "--")
    timestamp = curr.get("timestamp_iso", curr.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")))

    lines = [
        "=" * 78,
        f"METEOROLOGICAL BULLETIN — {city.upper()}, {country.upper()}",
        f"Timestamp: {timestamp} | Origin: {ALERT_ORIGIN_TAG}",
        "=" * 78,
        "",
        "[CURRENT CONDITIONS]",
        f"  Dry-Bulb Temperature : {curr.get('temp_celsius', '--')} °C",
        f"  Apparent Temperature : {curr.get('apparent_temp_celsius', '--')} °C",
        f"  Relative Humidity    : {curr.get('humidity_pct', '--')} %",
        f"  Surface Pressure     : {curr.get('pressure_hpa', '--')} hPa",
        f"  10m Wind Velocity    : {curr.get('wind_speed_kmh', '--')} km/h ({curr.get('wind_direction_deg', '--')} deg)",
        f"  Weather Condition    : {curr.get('weather_description', 'Nominal')} (WMO {curr.get('wmo_code', '--')})",
        f"  Active Alert Status  : {curr.get('alert_severity', 'NONE')}",
        "",
        "-" * 78,
        "[7-DAY SYNOPTIC OUTLOOK]",
        f"  {'Date':<12} {'Condition':<20} {'Min (°C)':<10} {'Max (°C)':<10} {'Rain (mm)':<10} {'Wind (km/h)':<10}",
        "  " + "-" * 74,
    ]

    for d in daily:
        date_str = str(d.get("timestamp_iso", d.get("timestamp", "--")))[:10]
        lines.append(
            f"  {date_str:<12} "
            f"{d.get('weather_description', 'Nominal')[:18]:<20} "
            f"{str(d.get('temp_min_celsius', '--')):<10} "
            f"{str(d.get('temp_max_celsius', '--')):<10} "
            f"{str(round(d.get('precip_sum_daily_mm', 0.0) or 0.0, 2)):<10} "
            f"{str(round(d.get('wind_speed_max_kmh', 0.0) or 0.0, 1)):<10}"
        )

    lines.extend([
        "",
        "-" * 78,
        "[ACTIVE THRESHOLD ADVISORIES]",
    ])

    if alerts:
        for idx, a in enumerate(alerts[:5], 1):
            time_val = a.get("timestamp_iso", a.get("timestamp", "--"))
            lines.append(f"  {idx}. [{a.get('alert_severity')}] {a.get('record_type')} ({time_val})")
            lines.append(f"     Trigger: {a.get('alert_type') or a.get('alert_triggers') or 'Adverse Threshold'}")
    else:
        lines.append("  Zero active threshold exceedances detected. Conditions nominal.")

    lines.extend([
        "",
        "=" * 78,
        f"NOTICE: {NON_OFFICIAL_DISCLAIMER}",
        f"DATA ATTRIBUTION: {ATTRIBUTION_NOTICE}",
        "=" * 78,
        "",
    ])

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(out_file.resolve())


def generate_all_reports(
    processed_data: Union[str, Path, List[Dict[str, Any]]],
    reports_dir: Union[str, Path] = "reports",
) -> Dict[str, str]:
    """Generate all three enterprise report deliverables in the specified directory."""
    r_dir = Path(reports_dir)
    r_dir.mkdir(parents=True, exist_ok=True)

    detailed_path = r_dir / "DETAILED_PROJECT_REPORT.md"
    exec_path = r_dir / "EXECUTIVE_SUMMARY_REPORT.md"
    txt_path = r_dir / "weather_summary_report.txt"

    p1 = generate_detailed_project_report(processed_data, output_path=detailed_path)
    p2 = generate_executive_summary_report(processed_data, output_path=exec_path)
    p3 = generate_weather_summary_report(processed_data, output_path=txt_path)

    return {
        "detailed_project_report": p1,
        "executive_summary_report": p2,
        "weather_summary_report": p3,
    }
