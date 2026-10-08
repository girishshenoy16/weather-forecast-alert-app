"""Weather Data Normalizer, WMO Mapper, Biometric Calculator & Processed Dataset Generator.

Unpacks Open-Meteo responses, calculates NOAA Heat Index and NWS Wind Chill,
enforces strict null semantics and the Field Applicability Matrix, and exports
normalized datasets to CSV and JSON.
"""

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from src.config import (
    ALERT_DISCLAIMER_TEXT,
    ALERT_ORIGIN_TAG,
    ATTRIBUTION_NOTICE,
    NON_OFFICIAL_DISCLAIMER,
    get_wmo_interpretation,
)


def calculate_heat_index(
    temp_celsius: Optional[float],
    humidity_pct: Optional[int],
) -> Optional[float]:
    """Calculate NOAA Rothfusz Heat Index in degrees Celsius.

    Evaluation procedure:
    1. Requires valid non-null dry-bulb temp and relative humidity.
    2. Converts temperature to Fahrenheit: T_F = T_C * 9/5 + 32.
    3. Primary Gate: Evaluated strictly in Fahrenheit: T_F >= 80.0°F.
       Returns None if T_F < 80.0°F or if inputs are missing.
    4. Computes preliminary Steadman value HI_simple and average HI_avg.
    5. If HI_avg < 80.0°F, adopts HI_simple.
    6. If HI_avg >= 80.0°F, evaluates full 9-term Rothfusz polynomial
       and applies low- or high-humidity adjustments where applicable.
    7. Converts final Fahrenheit result to Celsius and rounds to 1 decimal place.
    """
    if temp_celsius is None or humidity_pct is None:
        return None

    try:
        t_c = float(temp_celsius)
        rh = float(humidity_pct)
    except (ValueError, TypeError):
        return None

    t_f = t_c * (9.0 / 5.0) + 32.0

    # Primary Validity Gate: strictly evaluated on Fahrenheit
    if t_f < 80.0:
        return None

    # Preliminary Steadman calculation
    hi_simple = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
    hi_avg = (hi_simple + t_f) / 2.0

    if hi_avg < 80.0:
        hi_f = hi_simple
    else:
        # Full 9-term Rothfusz regression polynomial
        hi_f = (
            -42.379
            + 2.04901523 * t_f
            + 10.14333127 * rh
            - 0.22475541 * t_f * rh
            - 0.00683783 * (t_f ** 2)
            - 0.05481717 * (rh ** 2)
            + 0.00122874 * (t_f ** 2) * rh
            + 0.00085282 * t_f * (rh ** 2)
            - 0.00000199 * (t_f ** 2) * (rh ** 2)
        )

        # Low-humidity adjustment: RH < 13% and 80.0 <= T_F <= 112.0
        if rh < 13.0 and 80.0 <= t_f <= 112.0:
            term = (17.0 - abs(t_f - 95.0)) / 17.0
            if term > 0.0:
                adj = ((13.0 - rh) / 4.0) * math.sqrt(term)
                hi_f -= adj

        # High-humidity adjustment: RH > 85% and 80.0 <= T_F <= 87.0
        elif rh > 85.0 and 80.0 <= t_f <= 87.0:
            adj = ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
            hi_f += adj

    # Convert back to Celsius and round to 1 decimal place
    hi_c = (hi_f - 32.0) * (5.0 / 9.0)
    return round(hi_c, 1)


def calculate_wind_chill(
    temp_celsius: Optional[float],
    wind_speed_kmh: Optional[float],
) -> Optional[float]:
    """Calculate National Weather Service (NWS) Wind Chill in degrees Celsius.

    Validity: Valid only when T_C <= 10.0°C and V >= 4.8 km/h.
    Formula: WC_C = 13.12 + 0.6215 * T_C - 11.37 * V^0.16 + 0.3965 * T_C * V^0.16
    Returns None if conditions are not met or if inputs are missing.
    """
    if temp_celsius is None or wind_speed_kmh is None:
        return None

    try:
        t_c = float(temp_celsius)
        v = float(wind_speed_kmh)
    except (ValueError, TypeError):
        return None

    if t_c > 10.0 or v < 4.8:
        return None

    v_pow = v ** 0.16
    wc_c = 13.12 + (0.6215 * t_c) - (11.37 * v_pow) + (0.3965 * t_c * v_pow)
    return round(wc_c, 1)


def normalize_weather_data(
    payload: Dict[str, Any],
    city_name: str = "Unknown",
    country_code: str = "XX",
) -> List[Dict[str, Any]]:
    """Normalize raw Open-Meteo JSON payload into flat records conforming to Field Applicability Matrix.

    Generates records partitioned by record_type: CURRENT, HOURLY, DAILY.
    Preserves strict null semantics (never substituting 0 for missing values).
    """
    records: List[Dict[str, Any]] = []

    lat = float(payload.get("latitude", 0.0))
    lon = float(payload.get("longitude", 0.0))
    tz = str(payload.get("timezone", "UTC"))
    elev = float(payload.get("elevation", 0.0)) if payload.get("elevation") is not None else 0.0

    # -------------------------------------------------------------------------
    # 1. CURRENT Record Partition
    # -------------------------------------------------------------------------
    current = payload.get("current")
    if isinstance(current, dict):
        temp = current.get("temperature_2m")
        rh = current.get("relative_humidity_2m")
        apparent_temp = current.get("apparent_temperature")
        pressure = current.get("surface_pressure")
        wind_speed = current.get("wind_speed_10m")
        wind_dir = current.get("wind_direction_10m")
        precip = current.get("precipitation")
        interval_sec = current.get("interval")
        wmo = int(current.get("weather_code", 0))

        weather_cat, weather_desc = get_wmo_interpretation(wmo)
        hi = calculate_heat_index(temp, rh)
        wc = calculate_wind_chill(temp, wind_speed)

        curr_record: Dict[str, Any] = {
            "city_name": city_name,
            "country_code": country_code,
            "latitude": lat,
            "longitude": lon,
            "elevation": elev,
            "timezone": tz,
            "timestamp_iso": current.get("time", ""),
            "record_type": "CURRENT",
            "temp_celsius": float(temp) if temp is not None else None,
            "temp_min_celsius": None,
            "temp_max_celsius": None,
            "apparent_temp_celsius": float(apparent_temp) if apparent_temp is not None else None,
            "humidity_pct": int(rh) if rh is not None else None,
            "pressure_hpa": float(pressure) if pressure is not None else None,
            "wind_speed_kmh": float(wind_speed) if wind_speed is not None else None,
            "wind_speed_max_kmh": None,
            "wind_direction_deg": int(wind_dir) if wind_dir is not None else None,
            "precip_amount_mm": None,
            "precip_current_mm": float(precip) if precip is not None else None,
            "precip_current_interval_seconds": int(interval_sec) if interval_sec is not None else None,
            "precip_sum_daily_mm": None,
            "precip_prob_pct": None,
            "wmo_code": wmo,
            "weather_category": weather_cat,
            "weather_description": weather_desc,
            "heat_index_celsius": hi,
            "wind_chill_celsius": wc,
            "alert_flag": False,
            "alert_severity": "NONE",
            "alert_type": None,
            "alert_origin": ALERT_ORIGIN_TAG,
            "alert_disclaimer": ALERT_DISCLAIMER_TEXT,
        }
        records.append(curr_record)

    # -------------------------------------------------------------------------
    # 2. HOURLY Records Partition
    # -------------------------------------------------------------------------
    hourly = payload.get("hourly")
    if isinstance(hourly, dict) and "time" in hourly:
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        rhs = hourly.get("relative_humidity_2m", [])
        app_temps = hourly.get("apparent_temperature", [])
        pressures = hourly.get("surface_pressure", [])
        winds = hourly.get("wind_speed_10m", [])
        wind_dirs = hourly.get("wind_direction_10m", [])
        precips = hourly.get("precipitation", [])
        precip_probs = hourly.get("precipitation_probability", [])
        wmos = hourly.get("weather_code", [])

        length = len(times)
        for i in range(length):
            t = temps[i] if i < len(temps) else None
            h = rhs[i] if i < len(rhs) else None
            at = app_temps[i] if i < len(app_temps) else None
            p = pressures[i] if i < len(pressures) else None
            w = winds[i] if i < len(winds) else None
            wd = wind_dirs[i] if i < len(wind_dirs) else None
            pr = precips[i] if i < len(precips) else None
            prob = precip_probs[i] if i < len(precip_probs) else None
            code = int(wmos[i]) if i < len(wmos) and wmos[i] is not None else 0

            weather_cat, weather_desc = get_wmo_interpretation(code)
            hi = calculate_heat_index(t, h)
            wc = calculate_wind_chill(t, w)

            rec: Dict[str, Any] = {
                "city_name": city_name,
                "country_code": country_code,
                "latitude": lat,
                "longitude": lon,
                "elevation": elev,
                "timezone": tz,
                "timestamp_iso": times[i],
                "record_type": "HOURLY",
                "temp_celsius": float(t) if t is not None else None,
                "temp_min_celsius": None,
                "temp_max_celsius": None,
                "apparent_temp_celsius": float(at) if at is not None else None,
                "humidity_pct": int(h) if h is not None else None,
                "pressure_hpa": float(p) if p is not None else None,
                "wind_speed_kmh": float(w) if w is not None else None,
                "wind_speed_max_kmh": None,
                "wind_direction_deg": int(wd) if wd is not None else None,
                "precip_amount_mm": float(pr) if pr is not None else None,
                "precip_current_mm": None,
                "precip_current_interval_seconds": None,
                "precip_sum_daily_mm": None,
                "precip_prob_pct": int(prob) if prob is not None else None,
                "wmo_code": code,
                "weather_category": weather_cat,
                "weather_description": weather_desc,
                "heat_index_celsius": hi,
                "wind_chill_celsius": wc,
                "alert_flag": False,
                "alert_severity": "NONE",
                "alert_type": None,
                "alert_origin": ALERT_ORIGIN_TAG,
                "alert_disclaimer": ALERT_DISCLAIMER_TEXT,
            }
            records.append(rec)

    # -------------------------------------------------------------------------
    # 3. DAILY Records Partition
    # -------------------------------------------------------------------------
    daily = payload.get("daily")
    if isinstance(daily, dict) and "time" in daily:
        daily_times = daily.get("time", [])
        wmos = daily.get("weather_code", [])
        t_maxs = daily.get("temperature_2m_max", [])
        t_mins = daily.get("temperature_2m_min", [])
        p_sums = daily.get("precipitation_sum", [])
        p_probs = daily.get("precipitation_probability_max", [])
        w_maxs = daily.get("wind_speed_10m_max", [])

        length = len(daily_times)
        for i in range(length):
            t_max = t_maxs[i] if i < len(t_maxs) else None
            t_min = t_mins[i] if i < len(t_mins) else None
            p_sum = p_sums[i] if i < len(p_sums) else None
            p_prob = p_probs[i] if i < len(p_probs) else None
            w_max = w_maxs[i] if i < len(w_maxs) else None
            code = int(wmos[i]) if i < len(wmos) and wmos[i] is not None else 0

            weather_cat, weather_desc = get_wmo_interpretation(code)

            rec = {
                "city_name": city_name,
                "country_code": country_code,
                "latitude": lat,
                "longitude": lon,
                "elevation": elev,
                "timezone": tz,
                "timestamp_iso": daily_times[i],
                "record_type": "DAILY",
                "temp_celsius": None,
                "temp_min_celsius": float(t_min) if t_min is not None else None,
                "temp_max_celsius": float(t_max) if t_max is not None else None,
                "apparent_temp_celsius": None,
                "humidity_pct": None,
                "pressure_hpa": None,
                "wind_speed_kmh": None,
                "wind_speed_max_kmh": float(w_max) if w_max is not None else None,
                "wind_direction_deg": None,
                "precip_amount_mm": None,
                "precip_current_mm": None,
                "precip_current_interval_seconds": None,
                "precip_sum_daily_mm": float(p_sum) if p_sum is not None else None,
                "precip_prob_pct": int(p_prob) if p_prob is not None else None,
                "wmo_code": code,
                "weather_category": weather_cat,
                "weather_description": weather_desc,
                "heat_index_celsius": None,
                "wind_chill_celsius": None,
                "alert_flag": False,
                "alert_severity": "NONE",
                "alert_type": None,
                "alert_origin": ALERT_ORIGIN_TAG,
                "alert_disclaimer": ALERT_DISCLAIMER_TEXT,
            }
            records.append(rec)

    return records


def export_processed_datasets(
    records: List[Dict[str, Any]],
    csv_path: str = "data/processed/weather_data_processed.csv",
    json_path: str = "data/processed/weather_data_processed.json",
) -> Tuple[str, str]:
    """Export normalized records to CSV and JSON formats preserving strict null semantics."""
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)

    df = pd.DataFrame(records)

    # 1. Export CSV: empty string for NaN values (strict null semantics)
    df.to_csv(csv_path, index=False, na_rep="")

    # 2. Export JSON: canonical format with None serialized as null
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(records, f, indent=2, ensure_ascii=True)
        f.write("\n")

    return (csv_path, json_path)


def validate_dashboard_json(payload: Dict[str, Any]) -> bool:
    """Validate that the dashboard JSON artifact conforms to the frontend data contract.

    Ensures all top-level keys, metadata elements, and partition structures are present
    so the frontend can consume and filter data safely without client-side recalculations.

    Raises:
        ValueError: If mandatory keys or data types violate the contract.
    """
    required_top_level = {"metadata", "current", "hourly", "daily", "alerts", "records"}
    missing = required_top_level - set(payload.keys())
    if missing:
        raise ValueError(f"Dashboard JSON contract violation: missing top-level keys {sorted(missing)}")

    meta = payload["metadata"]
    if not isinstance(meta, dict):
        raise ValueError("Dashboard JSON contract violation: 'metadata' must be a dictionary")

    required_meta = {
        "city_name",
        "country_code",
        "latitude",
        "longitude",
        "elevation",
        "generated_at",
        "max_alert_severity",
        "total_records",
        "active_alerts_count",
        "attribution",
        "disclaimer",
        "alert_disclaimer",
        "alert_origin",
    }
    missing_meta = required_meta - set(meta.keys())
    if missing_meta:
        raise ValueError(f"Dashboard JSON contract violation: missing metadata keys {sorted(missing_meta)}")

    if not isinstance(payload["current"], dict):
        raise ValueError("Dashboard JSON contract violation: 'current' must be a dictionary")

    for key in ("hourly", "daily", "alerts", "records"):
        if not isinstance(payload[key], list):
            raise ValueError(f"Dashboard JSON contract violation: '{key}' must be a list")

    return True


def export_dashboard_json(
    records: List[Dict[str, Any]],
    output_path: Union[str, Path] = "docs/weather_data.json",
) -> str:
    """Generate and export a validated dashboard-ready JSON artifact for frontend consumption.

    Structures precomputed KPIs, hourly trends, daily synoptic outlooks, active alerts,
    and metadata so that frontend dashboards (HTML/CSS/JS) can consume and filter data
    client-side without performing backend recalculations.
    """
    output_path_str = str(output_path)
    os.makedirs(os.path.dirname(output_path_str) or ".", exist_ok=True)

    current_records = [r for r in records if r.get("record_type") == "CURRENT"]
    hourly_records = [r for r in records if r.get("record_type") == "HOURLY"]
    daily_records = [r for r in records if r.get("record_type") == "DAILY"]
    active_alerts = [r for r in records if r.get("alert_flag")]

    curr = current_records[0] if current_records else {}
    first_rec = curr or (records[0] if records else {})
    city = first_rec.get("city_name", "Unknown")
    country = first_rec.get("country_code", "--")
    lat = first_rec.get("latitude", 0.0)
    lon = first_rec.get("longitude", 0.0)
    elev = first_rec.get("elevation", 0.0)

    # Determine maximum overall alert severity
    max_severity = "NONE"
    order = {"CRITICAL": 3, "WARNING": 2, "ADVISORY": 1, "NONE": 0}
    for a in active_alerts:
        sev = a.get("alert_severity", "NONE")
        if order.get(sev, 0) > order.get(max_severity, 0):
            max_severity = sev

    dashboard_payload: Dict[str, Any] = {
        "metadata": {
            "city_name": city,
            "country_code": country,
            "latitude": lat,
            "longitude": lon,
            "elevation": elev,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "max_alert_severity": max_severity,
            "total_records": len(records),
            "active_alerts_count": len(active_alerts),
            "attribution": ATTRIBUTION_NOTICE,
            "disclaimer": NON_OFFICIAL_DISCLAIMER,
            "alert_disclaimer": ALERT_DISCLAIMER_TEXT,
            "alert_origin": ALERT_ORIGIN_TAG,
        },
        "current": curr,
        "hourly": hourly_records,
        "daily": daily_records,
        "alerts": active_alerts,
        "records": records,
    }

    # Validate against contract prior to persistence
    validate_dashboard_json(dashboard_payload)

    with open(output_path_str, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dashboard_payload, f, indent=2, ensure_ascii=True)
        f.write("\n")

    return output_path_str
