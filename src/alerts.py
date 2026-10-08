"""Rule-Based Alert Engine and Disclaimer Manager.

Evaluates partitioned meteorological thresholds across CURRENT, HOURLY, and DAILY records,
applies maximum severity precedence, logs runtime events, and maintains alert history.
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from src.config import (
    ALERT_DISCLAIMER_TEXT,
    ALERT_ORIGIN_TAG,
    DEFAULT_ALERT_CONFIG,
    NON_OFFICIAL_DISCLAIMER,
    SEVERITY_PRECEDENCE,
)


def evaluate_record_alerts(
    record: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, str, Optional[str]]:
    """Evaluate alert rules against a single normalized record based on record_type.

    Returns:
        (alert_flag, alert_severity, alert_type)
    """
    rec_type = record.get("record_type", "CURRENT")
    cfg = config if config is not None else DEFAULT_ALERT_CONFIG.get(rec_type, {})

    triggers: List[Tuple[str, str]] = []  # (severity, reason)

    # -------------------------------------------------------------------------
    # Rule Evaluation: CURRENT & HOURLY
    # -------------------------------------------------------------------------
    if rec_type in ("CURRENT", "HOURLY"):
        temp = record.get("temp_celsius")
        wind = record.get("wind_speed_kmh")
        wmo = record.get("wmo_code")
        rh = record.get("humidity_pct")
        precip_1h = record.get("precip_amount_mm")

        # Temperature extremes
        if temp is not None:
            if temp >= cfg.get("EXTREME_HEAT_CRITICAL", 38.0):
                triggers.append(("CRITICAL", "EXTREME_HEAT"))
            elif temp >= cfg.get("EXTREME_HEAT_WARNING", 35.0):
                triggers.append(("WARNING", "HEAT_WARNING"))

            if temp <= cfg.get("EXTREME_COLD_CRITICAL", -5.0):
                triggers.append(("CRITICAL", "EXTREME_COLD"))
            elif temp <= cfg.get("EXTREME_COLD_WARNING", 0.0):
                triggers.append(("WARNING", "COLD_WARNING"))

        # Wind speed (10m)
        if wind is not None:
            if wind >= cfg.get("WIND_SPEED_CRITICAL", 75.0):
                triggers.append(("CRITICAL", "HIGH_WIND_CRITICAL"))
            elif wind >= cfg.get("WIND_SPEED_WARNING", 50.0):
                triggers.append(("WARNING", "HIGH_WIND_WARNING"))

        # Severe WMO Weather
        if wmo is not None:
            if wmo in cfg.get("SEVERE_WMO_CRITICAL", [66, 67, 82, 96, 99]):
                triggers.append(("CRITICAL", "SEVERE_WMO_WEATHER"))
            elif wmo in cfg.get("SEVERE_WMO_WARNING", [65, 75, 86, 95]):
                triggers.append(("WARNING", "SEVERE_WMO_WEATHER"))

        # Hourly precipitation (evaluated strictly on HOURLY records)
        if rec_type == "HOURLY" and precip_1h is not None:
            if precip_1h >= cfg.get("PRECIP_1H_CRITICAL", 25.0):
                triggers.append(("CRITICAL", "HEAVY_RAIN_1H"))
            elif precip_1h >= cfg.get("PRECIP_1H_WARNING", 10.0):
                triggers.append(("WARNING", "HEAVY_RAIN_1H"))

        # Heat Discomfort Advisory
        if temp is not None and rh is not None:
            if (
                temp >= cfg.get("HEAT_DISCOMFORT_ADVISORY_TEMP", 30.0)
                and rh >= cfg.get("HEAT_DISCOMFORT_ADVISORY_HUMIDITY", 80)
            ):
                triggers.append(("ADVISORY", "HEAT_DISCOMFORT"))

    # -------------------------------------------------------------------------
    # Rule Evaluation: DAILY
    # -------------------------------------------------------------------------
    elif rec_type == "DAILY":
        t_max = record.get("temp_max_celsius")
        t_min = record.get("temp_min_celsius")
        p_sum = record.get("precip_sum_daily_mm")
        w_max = record.get("wind_speed_max_kmh")
        wmo = record.get("wmo_code")

        # Daily Peak Heat
        if t_max is not None:
            if t_max >= cfg.get("DAILY_PEAK_HEAT_CRITICAL", 38.0):
                triggers.append(("CRITICAL", "DAILY_PEAK_HEAT"))
            elif t_max >= cfg.get("DAILY_PEAK_HEAT_WARNING", 35.0):
                triggers.append(("WARNING", "DAILY_PEAK_HEAT"))

        # Daily Frost / Freeze
        if t_min is not None:
            if t_min <= cfg.get("DAILY_FREEZE_CRITICAL", -5.0):
                triggers.append(("CRITICAL", "DAILY_FREEZE"))
            elif t_min <= cfg.get("DAILY_FREEZE_WARNING", 0.0):
                triggers.append(("WARNING", "DAILY_FREEZE"))

        # Daily Total Precipitation
        if p_sum is not None:
            if p_sum >= cfg.get("PRECIP_24H_CRITICAL", 100.0):
                triggers.append(("CRITICAL", "DAILY_FLOOD_PREPARATION"))
            elif p_sum >= cfg.get("PRECIP_24H_WARNING", 50.0):
                triggers.append(("WARNING", "DAILY_HEAVY_RAIN"))

        # Daily Max Wind
        if w_max is not None:
            if w_max >= cfg.get("DAILY_MAX_WIND_CRITICAL", 75.0):
                triggers.append(("CRITICAL", "DAILY_HIGH_WIND"))
            elif w_max >= cfg.get("DAILY_MAX_WIND_WARNING", 50.0):
                triggers.append(("WARNING", "DAILY_HIGH_WIND"))

        # Daily WMO Severe Weather
        if wmo is not None:
            if wmo in cfg.get("SEVERE_WMO_CRITICAL", [66, 67, 82, 96, 99]):
                triggers.append(("CRITICAL", "SEVERE_WMO_WEATHER"))
            elif wmo in cfg.get("SEVERE_WMO_WARNING", [65, 75, 86, 95]):
                triggers.append(("WARNING", "SEVERE_WMO_WEATHER"))

    if not triggers:
        return (False, "NONE", None)

    # Resolve maximum severity precedence
    max_sev = max(triggers, key=lambda x: SEVERITY_PRECEDENCE.get(x[0], 0))[0]

    # Combine trigger reasons uniquely preserving order
    unique_reasons: List[str] = []
    for _, reason in triggers:
        if reason not in unique_reasons:
            unique_reasons.append(reason)
    combined_type = ";".join(unique_reasons)

    return (True, max_sev, combined_type)


def process_alerts(
    records: List[Dict[str, Any]],
    log_path: str = "reports/weather_alerts.log",
    history_path: str = "reports/alert_history.csv",
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Evaluate alerts across records, append to history, and dynamically log events.

    Supports configurable log and history paths to isolate test execution from production reports.
    """
    updated_records: List[Dict[str, Any]] = []
    triggered_alerts: List[Dict[str, Any]] = []

    for rec in records:
        r_copy = dict(rec)
        flag, severity, a_type = evaluate_record_alerts(r_copy, config=config)

        r_copy["alert_flag"] = flag
        r_copy["alert_severity"] = severity
        r_copy["alert_type"] = a_type
        r_copy["alert_origin"] = ALERT_ORIGIN_TAG
        r_copy["alert_disclaimer"] = ALERT_DISCLAIMER_TEXT

        updated_records.append(r_copy)

        if flag:
            triggered_alerts.append(r_copy)

    # If alerts triggered, append to history and write to log
    if triggered_alerts:
        os.makedirs(os.path.dirname(history_path) or ".", exist_ok=True)
        os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)

        # 1. Alert History CSV
        history_rows = []
        for a in triggered_alerts:
            history_rows.append({
                "timestamp_iso": a.get("timestamp_iso"),
                "city_name": a.get("city_name"),
                "record_type": a.get("record_type"),
                "alert_severity": a.get("alert_severity"),
                "alert_type": a.get("alert_type"),
                "alert_origin": ALERT_ORIGIN_TAG,
                "alert_disclaimer": ALERT_DISCLAIMER_TEXT,
            })

        history_df = pd.DataFrame(history_rows)
        file_exists = os.path.exists(history_path)
        history_df.to_csv(
            history_path,
            mode="a" if file_exists else "w",
            header=not file_exists,
            index=False,
        )

        # 2. Dynamic Runtime Log
        now_utc = datetime.now(timezone.utc).isoformat()
        with open(log_path, "a", encoding="utf-8") as f:
            for a in triggered_alerts:
                log_line = (
                    f"[{now_utc}] [{a.get('alert_severity')}] "
                    f"City={a.get('city_name')} Type={a.get('record_type')} "
                    f"Trigger={a.get('alert_type')} Timestamp={a.get('timestamp_iso')} "
                    f"{NON_OFFICIAL_DISCLAIMER}\n"
                )
                f.write(log_line)

    return updated_records
