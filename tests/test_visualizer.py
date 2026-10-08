"""Unit tests for src/visualizer.py with full test output isolation."""

from pathlib import Path
import pytest

from src.parser import normalize_weather_data
from src.simulator import generate_weather
from src.visualizer import generate_forecast_trend_plot, generate_meteorological_matrix

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


@pytest.fixture
def sample_records():
    """Generate sample normalized records for offline visualization testing."""
    payload = generate_weather("London", seed=42)
    return normalize_weather_data(payload, "London", "GB")


def test_forecast_trend_plot_generation(tmp_path, sample_records):
    """Test dual-axis forecast trend plot generation with test output isolation."""
    out_file = str(tmp_path / "test_forecast_trend.png")

    result_path = generate_forecast_trend_plot(
        processed_data=sample_records,
        output_path=out_file,
        dpi=100,  # fast test DPI
    )

    assert result_path == out_file
    p = Path(out_file)
    assert p.exists()
    assert p.stat().st_size > 1000

    # Assert valid PNG magic bytes
    with open(out_file, "rb") as f:
        header = f.read(8)
    assert header == PNG_HEADER


def test_meteorological_matrix_generation(tmp_path, sample_records):
    """Test 4-panel diagnostic matrix generation with test output isolation."""
    out_file = str(tmp_path / "test_meteorological_matrix.png")

    result_path = generate_meteorological_matrix(
        processed_data=sample_records,
        output_path=out_file,
        dpi=100,
    )

    assert result_path == out_file
    p = Path(out_file)
    assert p.exists()
    assert p.stat().st_size > 1000

    with open(out_file, "rb") as f:
        header = f.read(8)
    assert header == PNG_HEADER


def test_visualizer_handles_null_values_gracefully(tmp_path):
    """Test visualizer handles records with nulls/missing values without crashing."""
    records_with_nulls = [
        {
            "record_type": "HOURLY",
            "timestamp_iso": "2026-09-27T00:00:00Z",
            "temp_celsius": None,
            "apparent_temp_celsius": None,
            "precip_amount_mm": None,
            "wind_speed_kmh": None,
            "pressure_hpa": None,
            "precip_prob_pct": None,
        },
        {
            "record_type": "HOURLY",
            "timestamp_iso": "2026-09-27T01:00:00Z",
            "temp_celsius": 18.5,
            "apparent_temp_celsius": 17.2,
            "precip_amount_mm": 2.5,
            "wind_speed_kmh": 15.0,
            "pressure_hpa": 1012.0,
            "precip_prob_pct": 50,
        },
    ]

    out_trend = str(tmp_path / "null_trend.png")
    out_matrix = str(tmp_path / "null_matrix.png")

    generate_forecast_trend_plot(records_with_nulls, output_path=out_trend, dpi=100)
    generate_meteorological_matrix(records_with_nulls, output_path=out_matrix, dpi=100)

    assert Path(out_trend).exists()
    assert Path(out_matrix).exists()
