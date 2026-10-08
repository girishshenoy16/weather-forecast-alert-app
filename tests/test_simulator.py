"""Unit tests for src/simulator.py asserting schema, fixed epoch, and byte-for-byte determinism."""

from pathlib import Path
import src.simulator as simulator


def test_simulator_schema():
    """Assert generated dictionary matches Open-Meteo schema requirements."""
    payload = simulator.generate_weather("London", seed=42)

    assert isinstance(payload, dict)
    assert "latitude" in payload
    assert "longitude" in payload
    assert "timezone" in payload
    assert "current" in payload
    assert "hourly" in payload
    assert "daily" in payload

    # Current structure
    curr = payload["current"]
    assert "temperature_2m" in curr
    assert "relative_humidity_2m" in curr
    assert "apparent_temperature" in curr
    assert "precipitation" in curr
    assert "wind_speed_10m" in curr
    assert "weather_code" in curr

    # Hourly structure
    hourly = payload["hourly"]
    assert len(hourly["time"]) == 168
    assert len(hourly["temperature_2m"]) == 168
    assert len(hourly["precipitation"]) == 168

    # Daily structure
    daily = payload["daily"]
    assert len(daily["time"]) == 7
    assert len(daily["temperature_2m_max"]) == 7
    assert len(daily["temperature_2m_min"]) == 7
    assert len(daily["precipitation_sum"]) == 7


def test_simulator_intervals_and_rounding():
    """Assert numeric precision rules and observation interval."""
    payload = simulator.generate_weather("London", seed=42)

    # Observation interval must be integer seconds
    assert isinstance(payload["current"]["interval"], int)
    assert payload["current"]["interval"] in (900, 3600)

    # Float precision checks
    curr_temp = str(payload["current"]["temperature_2m"])
    if "." in curr_temp:
        assert len(curr_temp.split(".")[1]) <= 1

    curr_precip = str(payload["current"]["precipitation"])
    if "." in curr_precip:
        assert len(curr_precip.split(".")[1]) <= 2


def test_simulator_fixed_epoch():
    """Assert timestamps increment deterministically from fixed reference epoch."""
    payload = simulator.generate_weather("London", seed=42, ref_time="2026-09-27T00:00:00Z")

    assert payload["current"]["time"] == "2026-09-27T00:00"
    assert payload["hourly"]["time"][0] == "2026-09-27T00:00"
    assert payload["hourly"]["time"][1] == "2026-09-27T01:00"
    assert payload["daily"]["time"][0] == "2026-09-27"
    assert payload["daily"]["time"][1] == "2026-09-28"


def test_simulator_raw_byte_equality_in_memory():
    """Assert in-memory serialized bytes are byte-for-byte identical across runs."""
    bytes_1 = simulator.generate_weather_bytes("London", seed=42, ref_time="2026-09-27T00:00:00Z")
    bytes_2 = simulator.generate_weather_bytes("London", seed=42, ref_time="2026-09-27T00:00:00Z")

    assert bytes_1 == bytes_2, "In-memory simulated output failed byte-for-byte reproducibility contract"
    assert bytes_1.endswith(b"\n"), "Canonical bytes must terminate with a single trailing newline"


def test_simulator_raw_byte_equality_disk_file(tmp_path):
    """Assert binary write mode produces byte-for-byte identical files on disk."""
    file_1 = str(tmp_path / "sim_run_1.json")
    file_2 = str(tmp_path / "sim_run_2.json")

    path_1 = simulator.save_simulated_payload("London", seed=42, output_path=file_1)
    path_2 = simulator.save_simulated_payload("London", seed=42, output_path=file_2)

    bytes_on_disk_1 = Path(path_1).read_bytes()
    bytes_on_disk_2 = Path(path_2).read_bytes()

    assert bytes_on_disk_1 == bytes_on_disk_2, "Disk file output failed byte-for-byte reproducibility contract"
    assert bytes_on_disk_1 == simulator.generate_weather_bytes("London", seed=42)
