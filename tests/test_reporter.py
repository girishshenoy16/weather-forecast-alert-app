"""Unit tests for src/reporter.py asserting report generation and test output isolation."""

from pathlib import Path
import pytest

from src.config import ALERT_ORIGIN_TAG, ATTRIBUTION_NOTICE, NON_OFFICIAL_DISCLAIMER
from src.parser import normalize_weather_data
from src.reporter import (
    generate_all_reports,
    generate_detailed_project_report,
    generate_executive_summary_report,
    generate_weather_summary_report,
)
from src.simulator import generate_weather


@pytest.fixture
def sample_records():
    """Generate sample normalized records for offline testing."""
    payload = generate_weather("Mumbai", seed=42)
    return normalize_weather_data(payload, "Mumbai", "IN")


def test_detailed_project_report_generation(tmp_path, sample_records):
    """Test detailed technical report generation with tmp_path isolation."""
    out_file = tmp_path / "DETAILED_REPORT_TEST.md"
    res = generate_detailed_project_report(sample_records, output_path=out_file)

    assert res == str(out_file.resolve())
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")

    # Key Architecture and Math checks
    assert "# Detailed Project Report" in content
    assert "Rothfusz Heat Index" in content
    assert "NWS Wind Chill" in content
    assert ATTRIBUTION_NOTICE in content
    assert NON_OFFICIAL_DISCLAIMER in content
    assert ALERT_ORIGIN_TAG in content


def test_executive_summary_report_generation(tmp_path, sample_records):
    """Test business executive report generation across commercial sectors."""
    out_file = tmp_path / "EXEC_REPORT_TEST.md"
    res = generate_executive_summary_report(sample_records, output_path=out_file)

    assert res == str(out_file.resolve())
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")

    # Cross-sector checks
    assert "Logistics, Fleet & Supply Chain" in content
    assert "Agriculture, Horticulture & Irrigation" in content
    assert "Aviation, Marine & Port Operations" in content
    assert "Construction, Infrastructure" in content
    assert "Event Planning, Hospitality" in content
    assert ATTRIBUTION_NOTICE in content
    assert NON_OFFICIAL_DISCLAIMER in content


def test_weather_summary_text_bulletin_generation(tmp_path, sample_records):
    """Test plain-text meteorological bulletin generation."""
    out_file = tmp_path / "bulletin_test.txt"
    res = generate_weather_summary_report(sample_records, output_path=out_file)

    assert res == str(out_file.resolve())
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")

    assert "METEOROLOGICAL BULLETIN" in content
    assert "[CURRENT CONDITIONS]" in content
    assert "[7-DAY SYNOPTIC OUTLOOK]" in content
    assert ATTRIBUTION_NOTICE in content
    assert NON_OFFICIAL_DISCLAIMER in content


def test_generate_all_reports(tmp_path, sample_records):
    """Test batch generation of all 3 reports inside isolated directory."""
    reports_dir = tmp_path / "reports_sandbox"
    result_dict = generate_all_reports(sample_records, reports_dir=reports_dir)

    assert "detailed_project_report" in result_dict
    assert "executive_summary_report" in result_dict
    assert "weather_summary_report" in result_dict

    for key, path_str in result_dict.items():
        assert Path(path_str).exists()
        assert Path(path_str).stat().st_size > 500
