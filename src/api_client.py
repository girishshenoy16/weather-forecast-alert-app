"""Open-Meteo API Client for Geocoding and Forecast Ingestion.

Implements defensive response validation, typed exceptions, and bounded
exponential backoff retries with support for deterministic mock testing.
"""

from datetime import datetime, timezone
import json
import os
import random
import re
import time
from typing import Any, Callable, Dict, Optional, Tuple
import requests

from src.config import (
    API_MAX_RETRY_ATTEMPTS,
    API_RATE_LIMIT_SAFETY_CAP_SECONDS,
    API_REQUEST_TIMEOUT_SECONDS,
    DEFAULT_HEADERS,
    FORECAST_API_URL,
    GEOCODING_API_URL,
    APIConnectionError,
    APIRateLimitError,
    APIResponseError,
    APIServerError,
    CityNotFoundError,
)


def _sanitize_filename(name: str) -> str:
    """Sanitize string for safe cross-platform file naming."""
    return re.sub(r"[^\w\-]", "_", name.strip())


def get_city_coordinates(
    city_name: str,
    timeout: float = API_REQUEST_TIMEOUT_SECONDS,
) -> Tuple[float, float, str, str, str]:
    """Query Open-Meteo Geocoding API to resolve coordinates and metadata.

    Returns:
        (latitude, longitude, name, country_code, timezone)

    Raises:
        CityNotFoundError: If city returns empty results list.
        APIResponseError: If response is missing 'results' key or is not valid JSON.
        APIConnectionError: On timeout or network failure.
    """
    if not city_name or not city_name.strip():
        raise CityNotFoundError("City name must not be empty.")

    params = {
        "name": city_name.strip(),
        "count": 1,
        "language": "en",
        "format": "json",
    }

    try:
        response = requests.get(
            GEOCODING_API_URL,
            params=params,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
        )
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
        raise APIConnectionError(f"Geocoding network error: {exc}") from exc
    except requests.exceptions.RequestException as exc:
        raise APIResponseError(f"Geocoding request failed: {exc}") from exc

    if response.status_code != 200:
        raise APIResponseError(
            f"Geocoding API returned HTTP status {response.status_code}: {response.text}"
        )

    try:
        data = response.json()
    except Exception as exc:
        raise APIResponseError(f"Malformed non-JSON response from Geocoding API: {exc}") from exc

    if not isinstance(data, dict):
        raise APIResponseError("Geocoding API response payload is not a JSON object.")

    if "results" not in data:
        raise APIResponseError("Geocoding response missing mandatory 'results' key.")

    results = data["results"]
    if not isinstance(results, list) or len(results) == 0:
        raise CityNotFoundError(f"City '{city_name}' yielded zero matching locations.")

    first = results[0]
    try:
        latitude = float(first["latitude"])
        longitude = float(first["longitude"])
        name = str(first["name"])
        country_code = str(first.get("country_code", ""))
        tz = str(first.get("timezone", "UTC"))
    except (KeyError, ValueError, TypeError) as exc:
        raise APIResponseError(f"Malformed geocoding result entry: {exc}") from exc

    return (latitude, longitude, name, country_code, tz)


def fetch_weather_forecast(
    lat: float = 0.0,
    lon: float = 0.0,
    timezone_str: str = "auto",
    city: str = "location",
    output_path: Optional[str] = None,
    timeout: float = API_REQUEST_TIMEOUT_SECONDS,
    max_retries: int = API_MAX_RETRY_ATTEMPTS,
    sleep_fn: Optional[Callable[[float], None]] = None,
    uniform_fn: Optional[Callable[[float, float], float]] = None,
    **kwargs: Any,
) -> Tuple[Dict[str, Any], str]:
    """Query Open-Meteo Forecast API with bounded exponential backoff retries.

    Persists raw unaltered response to output_path or default path in data/raw/.

    Returns:
        (response_dict, persisted_file_path)
    """
    if "latitude" in kwargs:
        lat = float(kwargs["latitude"])
    if "longitude" in kwargs:
        lon = float(kwargs["longitude"])
    if "output_dir" in kwargs and output_path is None:
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_city = _sanitize_filename(city) if city else "location"
        output_path = os.path.join(kwargs["output_dir"], f"weather_raw_{safe_city}_{now_str}.json")

    _sleep = sleep_fn if sleep_fn is not None else time.sleep
    _uniform = uniform_fn if uniform_fn is not None else random.uniform

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,rain,weather_code,surface_pressure,"
            "wind_speed_10m,wind_direction_10m"
        ),
        "hourly": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation_probability,precipitation,rain,weather_code,"
            "surface_pressure,wind_speed_10m,wind_direction_10m"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_sum,precipitation_probability_max,wind_speed_10m_max"
        ),
        "wind_speed_unit": "kmh",
        "timezone": timezone_str,
    }

    last_error: Optional[Exception] = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(
                FORECAST_API_URL,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=timeout,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = exc
            if attempt == max_retries:
                raise APIConnectionError(
                    f"Forecast connection/timeout error after {max_retries} attempts: {exc}"
                ) from exc
            backoff = (2 ** attempt) + _uniform(0.0, 1.0)
            _sleep(backoff)
            continue
        except requests.exceptions.RequestException as exc:
            raise APIResponseError(f"Forecast request error: {exc}") from exc

        # Handle HTTP 429 Too Many Requests
        if response.status_code == 429:
            last_error = APIRateLimitError("HTTP 429 Too Many Requests")
            if attempt == max_retries:
                raise APIRateLimitError(
                    f"Rate limit exceeded after {max_retries} attempts."
                )

            retry_after_hdr = response.headers.get("Retry-After")
            backoff: float
            if retry_after_hdr:
                try:
                    backoff = min(float(retry_after_hdr), API_RATE_LIMIT_SAFETY_CAP_SECONDS)
                except (ValueError, TypeError):
                    backoff = float(2 ** attempt)
            else:
                backoff = float(2 ** attempt)
            _sleep(backoff)
            continue

        # Handle HTTP 5xx Server Errors
        if 500 <= response.status_code < 600:
            last_error = APIServerError(
                f"HTTP {response.status_code} Upstream Server Error"
            )
            if attempt == max_retries:
                raise APIServerError(
                    f"Server error {response.status_code} persisted after {max_retries} attempts."
                )
            backoff = (2 ** attempt) + _uniform(0.0, 1.0)
            _sleep(backoff)
            continue

        # Handle non-retryable 4xx client errors
        if 400 <= response.status_code < 500:
            raise APIResponseError(
                f"Client error HTTP {response.status_code}: {response.text}"
            )

        if response.status_code != 200:
            raise APIResponseError(
                f"Unexpected HTTP {response.status_code} from Forecast API: {response.text}"
            )

        # Successful 200 response: parse JSON
        try:
            data = response.json()
        except Exception as exc:
            raise APIResponseError(f"Malformed non-JSON response from Forecast API: {exc}") from exc

        if not isinstance(data, dict):
            raise APIResponseError("Forecast API payload is not a valid JSON dictionary.")

        # Determine target output file path
        if output_path is not None:
            final_path = output_path
        else:
            now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            safe_city = _sanitize_filename(city) if city else "location"
            os.makedirs("data/raw", exist_ok=True)
            final_path = os.path.join("data", "raw", f"weather_raw_{safe_city}_{now_str}.json")

        # Save unaltered JSON payload directly with canonical UTF-8 encoding
        dir_name = os.path.dirname(final_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        payload_bytes = (
            json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
        ).encode("utf-8")
        with open(final_path, "wb") as f:
            f.write(payload_bytes)

        return (data, final_path)

    if last_error:
        raise last_error
    raise APIResponseError("Exhausted retries without valid response.")
