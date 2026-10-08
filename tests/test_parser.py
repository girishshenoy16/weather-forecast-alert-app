"""Unit tests for src/parser.py asserting WMO decoding, Heat Index, Wind Chill, and null semantics."""

import json
from pathlib import Path
import pytest

from src.parser import (
    calculate_heat_index,
    calculate_wind_chill,
    export_processed_datasets,
    normalize_weather_data,
)
import src.simulator as simulator


def test_wmo_interpretation_known_and_fallback():
    """Test standard WMO codes and unknown/future code safe fallback."""
    from src.config import get_wmo_interpretation

    # Known code 0 (Clear)
    cat_0, desc_0 = get_wmo_interpretation(0)
    assert cat_0 == "Clear"
    assert "Clear" in desc_0

    # Known code 95 (Thunderstorm)
    cat_95, desc_95 = get_wmo_interpretation(95)
    assert cat_95 == "Thunderstorm"

    # Unknown code 999
    cat_unk, desc_unk = get_wmo_interpretation(999)
    assert cat_unk == "Unknown"
    assert desc_unk == "Unknown weather code (999)"


def test_apparent_temperature_passthrough():
    """Test native apparent_temperature passes through to apparent_temp_celsius without modification."""
    payload = {
        "latitude": 51.5,
        "longitude": -0.12,
        "timezone": "UTC",
        "current": {
            "time": "2026-09-27T00:00",
            "interval": 900,
            "temperature_2m": 20.0,
            "apparent_temperature": 18.7,
            "weather_code": 0,
        },
    }

    records = normalize_weather_data(payload, "London", "GB")
    assert len(records) == 1
    assert records[0]["apparent_temp_celsius"] == 18.7


def test_heat_index_boundary_behavior():
    """Test strict T_F >= 80.0°F validity gate evaluated in Fahrenheit."""
    # Below boundary: T_C = 26.6°C -> T_F = 79.88°F (< 80.0°F) -> strictly None
    assert calculate_heat_index(26.6, 60) is None

    # Below boundary: T_F = 79.9°F -> T_C = 26.6111°C
    t_c_below = (79.9 - 32.0) * (5.0 / 9.0)
    assert calculate_heat_index(t_c_below, 60) is None

    # Exactly at boundary: T_F = 80.0°F -> T_C = 240/9°C ≈ 26.6667°C -> valid
    t_c_exact = (80.0 - 32.0) * (5.0 / 9.0)
    hi_exact = calculate_heat_index(t_c_exact, 60)
    assert hi_exact is not None
    assert isinstance(hi_exact, float)

    # Above boundary: T_C = 26.7°C -> T_F = 80.06°F -> valid
    hi_above = calculate_heat_index(26.7, 60)
    assert hi_above is not None
    assert isinstance(hi_above, float)

    # Missing values return None
    assert calculate_heat_index(None, 60) is None
    assert calculate_heat_index(30.0, None) is None


def test_heat_index_adjustments():
    """Test Heat Index low and high humidity adjustment calculations."""
    # Low humidity adjustment: RH < 13% and 80 <= T_F <= 112
    # T_F = 100°F (37.78°C), RH = 10%
    hi_low_rh = calculate_heat_index(37.78, 10)
    assert hi_low_rh is not None

    # High humidity adjustment: RH > 85% and 80 <= T_F <= 87
    # T_F = 84°F (28.89°C), RH = 90%
    hi_high_rh = calculate_heat_index(28.89, 90)
    assert hi_high_rh is not None


def test_wind_chill_calculation():
    """Test NWS Wind Chill calculation and out-of-domain gates."""
    # Freezing wind: T_C = 0.0°C, V = 20.0 km/h -> valid wind chill < 0°C
    wc = calculate_wind_chill(0.0, 20.0)
    assert wc is not None
    assert wc < 0.0

    # Gate: T_C > 10.0°C -> None
    assert calculate_wind_chill(10.1, 20.0) is None

    # Gate: V < 4.8 km/h -> None
    assert calculate_wind_chill(0.0, 4.7) is None

    # Missing inputs -> None
    assert calculate_wind_chill(None, 20.0) is None
    assert calculate_wind_chill(0.0, None) is None


def test_strict_null_semantics_and_field_applicability():
    """Test Field Applicability Matrix partitions and ensure 0 is never substituted for null."""
    payload = simulator.generate_weather("London", seed=42)
    records = normalize_weather_data(payload, "London", "GB")

    curr_records = [r for r in records if r["record_type"] == "CURRENT"]
    hourly_records = [r for r in records if r["record_type"] == "HOURLY"]
    daily_records = [r for r in records if r["record_type"] == "DAILY"]

    assert len(curr_records) == 1
    assert len(hourly_records) == 168
    assert len(daily_records) == 7

    c = curr_records[0]
    # CURRENT applicability
    assert c["precip_current_mm"] is not None
    assert c["precip_current_interval_seconds"] is not None
    assert c["precip_amount_mm"] is None
    assert c["precip_sum_daily_mm"] is None
    assert c["temp_min_celsius"] is None
    assert c["temp_max_celsius"] is None

    h = hourly_records[0]
    # HOURLY applicability
    assert h["precip_amount_mm"] is not None
    assert h["precip_current_mm"] is None
    assert h["precip_current_interval_seconds"] is None
    assert h["precip_sum_daily_mm"] is None
    assert h["temp_min_celsius"] is None
    assert h["temp_max_celsius"] is None

    d = daily_records[0]
    # DAILY applicability
    assert d["precip_sum_daily_mm"] is not None
    assert d["temp_min_celsius"] is not None
    assert d["temp_max_celsius"] is not None
    assert d["wind_speed_max_kmh"] is not None
    assert d["temp_celsius"] is None
    assert d["humidity_pct"] is None
    assert d["precip_amount_mm"] is None
    assert d["precip_current_mm"] is None


def test_export_processed_datasets(tmp_path):
    """Test export of normalized records to CSV and JSON."""
    payload = simulator.generate_weather("London", seed=42)
    records = normalize_weather_data(payload, "London", "GB")

    csv_path = str(tmp_path / "weather_processed_test.csv")
    json_path = str(tmp_path / "weather_processed_test.json")

    c_path, j_path = export_processed_datasets(records, csv_path=csv_path, json_path=json_path)

    assert Path(c_path).exists()
    assert Path(j_path).exists()

    with open(j_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == len(records)
