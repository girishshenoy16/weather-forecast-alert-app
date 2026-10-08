"""Unit tests for src/alerts.py asserting partitioned rules, precedence, and isolated output."""

import os
from pathlib import Path
import pandas as pd
import pytest

from src.alerts import evaluate_record_alerts, process_alerts
from src.config import ALERT_DISCLAIMER_TEXT, ALERT_ORIGIN_TAG


def test_alert_partitioned_rules_hourly_vs_daily():
    """Test 1h rain triggers only on HOURLY records, while 24h flood triggers only on DAILY."""
    # Record with 30mm precipitation
    rec_hourly = {
        "record_type": "HOURLY",
        "precip_amount_mm": 30.0,
    }
    flag_h, sev_h, type_h = evaluate_record_alerts(rec_hourly)
    assert flag_h is True
    assert sev_h == "CRITICAL"
    assert "HEAVY_RAIN_1H" in type_h

    # CURRENT record with precip_amount_mm should ignore it (rule partitioned strictly to HOURLY)
    rec_current = {
        "record_type": "CURRENT",
        "precip_amount_mm": 30.0,
    }
    flag_c, sev_c, _ = evaluate_record_alerts(rec_current)
    assert flag_c is False
    assert sev_c == "NONE"

    # DAILY record with 120mm daily sum triggers daily flood
    rec_daily = {
        "record_type": "DAILY",
        "precip_sum_daily_mm": 120.0,
    }
    flag_d, sev_d, type_d = evaluate_record_alerts(rec_daily)
    assert flag_d is True
    assert sev_d == "CRITICAL"
    assert "DAILY_FLOOD_PREPARATION" in type_d


def test_alert_severity_precedence_and_concatenation():
    """Test multiple breached thresholds resolve to maximum severity with concatenated triggers."""
    # Record with both High Wind WARNING (55 km/h) and Severe Thunderstorm CRITICAL (WMO 99)
    record = {
        "record_type": "CURRENT",
        "wind_speed_kmh": 55.0,  # WARNING
        "wmo_code": 99,           # CRITICAL
    }
    flag, sev, a_type = evaluate_record_alerts(record)
    assert flag is True
    assert sev == "CRITICAL"  # CRITICAL > WARNING
    assert "HIGH_WIND_WARNING" in a_type
    assert "SEVERE_WMO_WEATHER" in a_type
    assert ";" in a_type


def test_alert_discomfort_advisory():
    """Test heat discomfort advisory triggers at temp >= 30°C and RH >= 80%."""
    record = {
        "record_type": "CURRENT",
        "temp_celsius": 32.0,
        "humidity_pct": 85,
    }
    flag, sev, a_type = evaluate_record_alerts(record)
    assert flag is True
    assert sev == "ADVISORY"
    assert "HEAT_DISCOMFORT" in a_type


def test_alert_missing_values_skip_cleanly():
    """Test missing or null input variables safely skip rules without exceptions."""
    record = {
        "record_type": "CURRENT",
        "temp_celsius": None,
        "wind_speed_kmh": None,
        "wmo_code": None,
        "humidity_pct": None,
    }
    flag, sev, a_type = evaluate_record_alerts(record)
    assert flag is False
    assert sev == "NONE"
    assert a_type is None


def test_process_alerts_with_isolated_output(tmp_path):
    """Test alert engine runtime logging and history tracking using isolated temporary paths."""
    # Ensure production reports are not touched
    prod_log = Path("reports/weather_alerts.log")
    prod_csv = Path("reports/alert_history.csv")
    prod_log_exists_before = prod_log.exists()
    prod_csv_exists_before = prod_csv.exists()
    prod_log_mtime_before = prod_log.stat().st_mtime if prod_log_exists_before else None

    test_log = str(tmp_path / "test_weather_alerts.log")
    test_csv = str(tmp_path / "test_alert_history.csv")

    records = [
        {
            "city_name": "London",
            "country_code": "GB",
            "record_type": "CURRENT",
            "timestamp_iso": "2026-09-27T12:00:00Z",
            "temp_celsius": 40.0,  # CRITICAL heat
        },
        {
            "city_name": "London",
            "country_code": "GB",
            "record_type": "HOURLY",
            "timestamp_iso": "2026-09-27T13:00:00Z",
            "temp_celsius": 20.0,  # Normal
        },
    ]

    updated = process_alerts(
        records,
        log_path=test_log,
        history_path=test_csv,
    )

    assert len(updated) == 2
    assert updated[0]["alert_flag"] is True
    assert updated[0]["alert_severity"] == "CRITICAL"
    assert updated[0]["alert_origin"] == ALERT_ORIGIN_TAG
    assert updated[0]["alert_disclaimer"] == ALERT_DISCLAIMER_TEXT

    # Check isolated log and CSV were created in tmp_path
    assert Path(test_log).exists()
    assert Path(test_csv).exists()

    df_hist = pd.read_csv(test_csv)
    assert len(df_hist) == 1
    assert df_hist.iloc[0]["alert_severity"] == "CRITICAL"
    assert df_hist.iloc[0]["alert_origin"] == ALERT_ORIGIN_TAG

    # Verify production files were not modified
    if prod_log_exists_before:
        assert prod_log.stat().st_mtime == prod_log_mtime_before
