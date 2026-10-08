"""Unit tests for src/api_client.py with 100% mocked HTTP and fast deterministic retries."""

import json
from unittest.mock import MagicMock, patch
import pytest
import requests

from src.api_client import fetch_weather_forecast, get_city_coordinates
from src.config import (
    APIConnectionError,
    APIRateLimitError,
    APIResponseError,
    APIServerError,
    CityNotFoundError,
)


def test_geocoding_success():
    """Test successful geocoding returns expected coordinate tuple."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "latitude": 51.5085,
                "longitude": -0.1257,
                "name": "London",
                "country_code": "GB",
                "timezone": "Europe/London",
            }
        ]
    }

    with patch("requests.get", return_value=mock_response):
        lat, lon, name, country, tz = get_city_coordinates("London")

    assert lat == 51.5085
    assert lon == -0.1257
    assert name == "London"
    assert country == "GB"
    assert tz == "Europe/London"


def test_geocoding_city_not_found():
    """Test geocoding with empty results list raises CityNotFoundError without retry."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(CityNotFoundError, match="zero matching locations"):
            get_city_coordinates("NonExistentCityName123")


def test_geocoding_missing_results_key():
    """Test geocoding response missing 'results' key raises APIResponseError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"error": "Invalid structure"}

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(APIResponseError, match="missing mandatory 'results' key"):
            get_city_coordinates("London")


def test_geocoding_malformed_json():
    """Test non-JSON geocoding response raises APIResponseError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("No JSON object could be decoded")

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(APIResponseError, match="Malformed non-JSON"):
            get_city_coordinates("London")


def test_forecast_persists_raw_payload(tmp_path):
    """Test fetch_weather_forecast persists raw payload to target path."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    payload = {
        "latitude": 51.5,
        "longitude": -0.12,
        "current": {"temperature_2m": 15.0},
        "hourly": {"time": ["2026-09-27T00:00"]},
        "daily": {"time": ["2026-09-27"]},
    }
    mock_response.json.return_value = payload

    test_file = str(tmp_path / "weather_raw_London_test.json")

    with patch("requests.get", return_value=mock_response):
        data, saved_path = fetch_weather_forecast(
            lat=51.5,
            lon=-0.12,
            city="London",
            output_path=test_file,
        )

    assert data == payload
    assert saved_path == test_file
    with open(test_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded == payload


def test_api_request_timeout():
    """Test request timeouts execute 3 retries and raise APIConnectionError upon exhaustion."""
    sleep_calls = []

    with patch("requests.get", side_effect=requests.exceptions.Timeout("Connection timed out")):
        with pytest.raises(APIConnectionError, match="Forecast connection/timeout error after 3 attempts"):
            fetch_weather_forecast(
                lat=51.5,
                lon=-0.12,
                max_retries=3,
                sleep_fn=sleep_calls.append,
                uniform_fn=lambda a, b: 0.5,
            )

    # 3 attempts -> 2 sleeps between attempts
    assert len(sleep_calls) == 2
    assert sleep_calls[0] == 2 ** 1 + 0.5  # 2.5s
    assert sleep_calls[1] == 2 ** 2 + 0.5  # 4.5s


def test_api_http_500_server_error():
    """Test upstream 500 server error retries 3 times and raises APIServerError upon exhaustion."""
    mock_500 = MagicMock()
    mock_500.status_code = 500
    mock_500.text = "Internal Server Error"
    sleep_calls = []

    with patch("requests.get", return_value=mock_500):
        with pytest.raises(APIServerError, match="Server error 500 persisted after 3 attempts"):
            fetch_weather_forecast(
                lat=51.5,
                lon=-0.12,
                max_retries=3,
                sleep_fn=sleep_calls.append,
                uniform_fn=lambda a, b: 0.1,
            )

    assert len(sleep_calls) == 2
    assert sleep_calls[0] == 2 ** 1 + 0.1
    assert sleep_calls[1] == 2 ** 2 + 0.1


def test_api_rate_limit_429():
    """Test HTTP 429 parses Retry-After header and raises APIRateLimitError upon exhaustion."""
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "5"}
    sleep_calls = []

    with patch("requests.get", return_value=mock_429):
        with pytest.raises(APIRateLimitError, match="Rate limit exceeded after 3 attempts"):
            fetch_weather_forecast(
                lat=51.5,
                lon=-0.12,
                max_retries=3,
                sleep_fn=sleep_calls.append,
            )

    assert len(sleep_calls) == 2
    assert sleep_calls[0] == 5.0
    assert sleep_calls[1] == 5.0


def test_api_rate_limit_429_safety_cap():
    """Test HTTP 429 with large Retry-After is capped at 30 seconds safety max."""
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"Retry-After": "120"}
    sleep_calls = []

    with patch("requests.get", return_value=mock_429):
        with pytest.raises(APIRateLimitError):
            fetch_weather_forecast(
                lat=51.5,
                lon=-0.12,
                max_retries=3,
                sleep_fn=sleep_calls.append,
            )

    assert sleep_calls[0] == 30.0


def test_api_non_retryable_client_error():
    """Test HTTP 400 Bad Request fails immediately without retry."""
    mock_400 = MagicMock()
    mock_400.status_code = 400
    mock_400.text = "Bad Request: Invalid Coordinates"
    sleep_calls = []

    with patch("requests.get", return_value=mock_400) as mock_get:
        with pytest.raises(APIResponseError, match="Client error HTTP 400"):
            fetch_weather_forecast(
                lat=999.0,
                lon=999.0,
                sleep_fn=sleep_calls.append,
            )

    assert mock_get.call_count == 1
    assert len(sleep_calls) == 0


def test_api_retry_behavior_transient_503(tmp_path):
    """Test transient 503 errors recover on 3rd attempt after 2 retries."""
    mock_503 = MagicMock()
    mock_503.status_code = 503
    mock_503.text = "Service Unavailable"

    mock_200 = MagicMock()
    mock_200.status_code = 200
    payload = {
        "current": {"temperature_2m": 18.0},
        "hourly": {"time": []},
        "daily": {"time": []},
    }
    mock_200.json.return_value = payload

    sleep_calls = []
    test_file = str(tmp_path / "weather_transient_503.json")

    with patch("requests.get", side_effect=[mock_503, mock_503, mock_200]) as mock_get:
        data, path = fetch_weather_forecast(
            lat=51.5,
            lon=-0.12,
            output_path=test_file,
            sleep_fn=sleep_calls.append,
            uniform_fn=lambda a, b: 0.0,
        )

    assert mock_get.call_count == 3
    assert len(sleep_calls) == 2
    assert data == payload
    assert path == test_file
