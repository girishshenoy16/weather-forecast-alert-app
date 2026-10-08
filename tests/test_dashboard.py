"""Unit tests for Phase 8 dashboard JSON data contract asserting schema and test output isolation.

Validates that the Python data pipeline generates a precomputed dashboard JSON artifact
for frontend filtering and visualization without creating or overwriting dashboard HTML.
"""

import json
from pathlib import Path
import pytest

from src.config import (
    ALERT_DISCLAIMER_TEXT,
    ALERT_ORIGIN_TAG,
    ATTRIBUTION_NOTICE,
    NON_OFFICIAL_DISCLAIMER,
)
from src.parser import (
    export_dashboard_json,
    normalize_weather_data,
    validate_dashboard_json,
)
from src.simulator import generate_weather


@pytest.fixture
def sample_records():
    """Generate sample normalized records for offline testing."""
    payload = generate_weather("Pune", seed=42)
    return normalize_weather_data(payload, "Pune", "IN")


def test_export_dashboard_json_structure_and_keys(tmp_path, sample_records):
    """Test dashboard JSON generation with strict output isolation to tmp_path."""
    isolated_file = tmp_path / "weather_data.json"

    result_path = export_dashboard_json(
        records=sample_records,
        output_path=str(isolated_file),
    )

    assert result_path == str(isolated_file)
    assert isolated_file.exists()
    assert isolated_file.stat().st_size > 1000

    with open(isolated_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Core contract keys
    assert "metadata" in payload
    assert "current" in payload
    assert "hourly" in payload
    assert "daily" in payload
    assert "alerts" in payload
    assert "records" in payload

    # Metadata contract
    meta = payload["metadata"]
    assert meta["city_name"] == "Pune"
    assert meta["country_code"] == "IN"
    assert "latitude" in meta
    assert "longitude" in meta
    assert "elevation" in meta
    assert "generated_at" in meta
    assert "max_alert_severity" in meta
    assert meta["total_records"] == len(sample_records)
    assert meta["active_alerts_count"] == len(payload["alerts"])

    # Mandatory Legal & Attribution Notices in JSON Contract
    assert meta["attribution"] == ATTRIBUTION_NOTICE
    assert meta["disclaimer"] == NON_OFFICIAL_DISCLAIMER
    assert meta["alert_disclaimer"] == ALERT_DISCLAIMER_TEXT
    assert meta["alert_origin"] == ALERT_ORIGIN_TAG

    # Hourly & Daily Data Arrays
    assert isinstance(payload["hourly"], list)
    assert len(payload["hourly"]) > 0
    assert isinstance(payload["daily"], list)
    assert len(payload["daily"]) > 0

    # Ensure all hourly records are marked HOURLY
    for rec in payload["hourly"]:
        assert rec.get("record_type") == "HOURLY"

    # Ensure all daily records are marked DAILY
    for rec in payload["daily"]:
        assert rec.get("record_type") == "DAILY"


def test_export_dashboard_json_empty_records(tmp_path):
    """Test dashboard JSON generator handles empty records list without crashing."""
    isolated_file = tmp_path / "empty_weather_data.json"

    result_path = export_dashboard_json([], output_path=str(isolated_file))

    assert Path(result_path).exists()
    with open(isolated_file, "r", encoding="utf-8") as f:
        payload = json.load(f)

    assert payload["metadata"]["total_records"] == 0
    assert payload["metadata"]["active_alerts_count"] == 0
    assert payload["metadata"]["max_alert_severity"] == "NONE"
    assert payload["metadata"]["attribution"] == ATTRIBUTION_NOTICE
    assert payload["hourly"] == []
    assert payload["daily"] == []
    assert payload["alerts"] == []
    assert payload["records"] == []


def test_dashboard_json_contract_preserves_html_isolation(tmp_path, sample_records):
    """Assert that generating dashboard JSON never touches or overwrites HTML/CSS/JS frontend files."""
    dummy_docs = tmp_path / "docs"
    dummy_docs.mkdir()
    html_file = dummy_docs / "index.html"
    css_file = dummy_docs / "style.css"
    js_file = dummy_docs / "app.js"

    # Simulate user manually authored files
    html_file.write_text("<!DOCTYPE html><html>Manual User Dashboard</html>", encoding="utf-8")
    css_file.write_text("/* Manual User Styles */", encoding="utf-8")
    js_file.write_text("// Manual User Scripts", encoding="utf-8")

    json_target = dummy_docs / "weather_data.json"
    export_dashboard_json(sample_records, output_path=str(json_target))

    assert json_target.exists()
    # Confirm manual files were not touched, modified, or overwritten
    assert html_file.read_text(encoding="utf-8") == "<!DOCTYPE html><html>Manual User Dashboard</html>"
    assert css_file.read_text(encoding="utf-8") == "/* Manual User Styles */"
    assert js_file.read_text(encoding="utf-8") == "// Manual User Scripts"


def test_validate_dashboard_json_contract_enforcement(sample_records):
    """Test that validate_dashboard_json enforces required schema and detects violations."""
    from datetime import datetime, timezone

    # Valid payload
    valid_payload = {
        "metadata": {
            "city_name": "Pune",
            "country_code": "IN",
            "latitude": 18.52,
            "longitude": 73.85,
            "elevation": 560.0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "max_alert_severity": "NONE",
            "total_records": 10,
            "active_alerts_count": 0,
            "attribution": ATTRIBUTION_NOTICE,
            "disclaimer": NON_OFFICIAL_DISCLAIMER,
            "alert_disclaimer": ALERT_DISCLAIMER_TEXT,
            "alert_origin": ALERT_ORIGIN_TAG,
        },
        "current": {},
        "hourly": [],
        "daily": [],
        "alerts": [],
        "records": [],
    }
    assert validate_dashboard_json(valid_payload) is True

    # Missing top-level key
    invalid_payload = dict(valid_payload)
    del invalid_payload["metadata"]
    with pytest.raises(ValueError, match="missing top-level keys"):
        validate_dashboard_json(invalid_payload)

    # Missing metadata key
    invalid_meta_payload = dict(valid_payload)
    invalid_meta_payload["metadata"] = dict(valid_payload["metadata"])
    del invalid_meta_payload["metadata"]["city_name"]
    with pytest.raises(ValueError, match="missing metadata keys"):
        validate_dashboard_json(invalid_meta_payload)

    # Malformed data type (hourly is not list)
    invalid_type_payload = dict(valid_payload)
    invalid_type_payload["hourly"] = "not_a_list"
    with pytest.raises(ValueError, match="'hourly' must be a list"):
        validate_dashboard_json(invalid_type_payload)


def test_export_dashboard_json_supports_path_object(tmp_path, sample_records):
    """Test that export_dashboard_json accepts pathlib.Path objects directly."""
    target_path = tmp_path / "subdir" / "weather_contract.json"
    result = export_dashboard_json(sample_records, output_path=target_path)
    assert result == str(target_path)
    assert target_path.exists()
    assert target_path.stat().st_size > 1000
