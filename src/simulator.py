"""Deterministic Offline Meteorological Simulation Engine.

Produces byte-for-byte identical synthetic weather payloads matching the
Open-Meteo API schema using isolated pseudo-random state and canonical JSON encoding.
"""

from datetime import datetime, timedelta, timezone
import json
import os
import random
from typing import Any, Dict, List, Optional

from src.config import SIMULATOR_DEFAULT_REF_TIME, SIMULATOR_DEFAULT_SEED

# Known sample coordinates for major Indian cities to ensure realistic simulation output
KNOWN_CITY_COORDINATES = {
    "mumbai": (19.0760, 72.8777, 14.0),
    "delhi": (28.6139, 77.2090, 216.0),
    "new delhi": (28.6139, 77.2090, 216.0),
    "bengaluru": (12.9716, 77.5946, 920.0),
    "bangalore": (12.9716, 77.5946, 920.0),
    "hyderabad": (17.3850, 78.4867, 542.0),
    "chennai": (13.0827, 80.2707, 6.0),
    "kolkata": (22.5726, 88.3639, 9.0),
    "ahmedabad": (23.0225, 72.5714, 53.0),
    "pune": (18.5204, 73.8567, 560.0),
    "jaipur": (26.9124, 75.7873, 431.0),
    "lucknow": (26.8467, 80.9462, 123.0),
    "surat": (21.1702, 72.8311, 13.0),
    "chandigarh": (30.7333, 76.7794, 321.0),
    "kochi": (9.9312, 76.2673, 4.0),
}


def _parse_ref_time(ref_time_str: str) -> datetime:
    """Parse reference time ISO string to datetime in UTC."""
    # Standard format: 2026-09-27T00:00:00Z
    clean_str = ref_time_str.strip()
    if clean_str.endswith("Z"):
        clean_str = clean_str[:-1] + "+00:00"
    return datetime.fromisoformat(clean_str).astimezone(timezone.utc)


def generate_weather(
    city: str,
    seed: int = SIMULATOR_DEFAULT_SEED,
    ref_time: str = SIMULATOR_DEFAULT_REF_TIME,
) -> Dict[str, Any]:
    """Generate deterministic simulated meteorological payload matching Open-Meteo schema.

    Uses isolated random.Random(seed), zero system-time dependence, and explicit float rounding.
    """
    rng = random.Random(seed)
    base_dt = _parse_ref_time(ref_time)

    city_key = city.lower().strip()
    if city_key in KNOWN_CITY_COORDINATES:
        lat, lon, elev = KNOWN_CITY_COORDINATES[city_key]
    else:
        # Deterministically derive pseudo-coords from city name
        name_hash = sum(ord(c) for c in city_key)
        lat = round(20.0 + (name_hash % 50) + rng.random(), 4)
        lon = round(-120.0 + ((name_hash * 7) % 240) + rng.random(), 4)
        elev = round(10.0 + (name_hash % 200) + rng.random(), 1)

    # 1. Hourly timeline: 168 hours (7 days)
    hourly_time: List[str] = []
    hourly_temp: List[float] = []
    hourly_rh: List[int] = []
    hourly_apparent_temp: List[float] = []
    hourly_precip_prob: List[int] = []
    hourly_precip: List[float] = []
    hourly_rain: List[float] = []
    hourly_weather_code: List[int] = []
    hourly_pressure: List[float] = []
    hourly_wind_speed: List[float] = []
    hourly_wind_dir: List[int] = []

    possible_wmo_codes = [0, 1, 2, 3, 45, 51, 61, 65, 80, 95]

    for h in range(168):
        dt = base_dt + timedelta(hours=h)
        hourly_time.append(dt.strftime("%Y-%m-%dT%H:%M"))

        # Base diurnal cycle temperature
        hour_of_day = dt.hour
        diurnal_cycle = 4.0 * (1.0 - abs((hour_of_day - 14) / 10.0))
        temp = round(15.0 + diurnal_cycle + (rng.uniform(-3.0, 4.0)), 1)
        rh = int(max(20, min(100, round(65.0 - (diurnal_cycle * 3) + rng.uniform(-10.0, 15.0)))))
        
        # Wind speed & direction
        wind_speed = round(max(0.0, 12.0 + rng.uniform(-8.0, 25.0)), 1)
        wind_dir = int(rng.randint(0, 360))

        # Pressure
        pressure = round(1013.2 + rng.uniform(-15.0, 15.0), 1)

        # Precipitation: sparse generation
        has_precip = rng.random() < 0.25
        if has_precip:
            precip = round(max(0.1, rng.expovariate(0.67)), 2)
            precip_prob = int(rng.randint(40, 100))
            w_code = rng.choice([51, 61, 65, 80, 95])
        else:
            precip = 0.0
            precip_prob = int(rng.randint(0, 30))
            w_code = rng.choice([0, 1, 2, 3])

        # Native apparent temperature approximation
        app_temp = round(temp + (0.33 * (rh / 100.0 * 6.105)) - (0.70 * (wind_speed / 3.6)) - 4.0, 1)

        hourly_temp.append(temp)
        hourly_rh.append(rh)
        hourly_apparent_temp.append(app_temp)
        hourly_precip_prob.append(precip_prob)
        hourly_precip.append(precip)
        hourly_rain.append(precip)
        hourly_weather_code.append(w_code)
        hourly_pressure.append(pressure)
        hourly_wind_speed.append(wind_speed)
        hourly_wind_dir.append(wind_dir)

    # 2. Daily timeline: 7 days derived deterministically from hourly slices
    daily_time: List[str] = []
    daily_wmo: List[int] = []
    daily_temp_max: List[float] = []
    daily_temp_min: List[float] = []
    daily_precip_sum: List[float] = []
    daily_precip_prob_max: List[int] = []
    daily_wind_speed_max: List[float] = []

    for d in range(7):
        day_dt = base_dt + timedelta(days=d)
        daily_time.append(day_dt.strftime("%Y-%m-%d"))

        slice_start = d * 24
        slice_end = slice_start + 24
        day_temps = hourly_temp[slice_start:slice_end]
        day_precips = hourly_precip[slice_start:slice_end]
        day_probs = hourly_precip_prob[slice_start:slice_end]
        day_winds = hourly_wind_speed[slice_start:slice_end]
        day_codes = hourly_weather_code[slice_start:slice_end]

        daily_temp_max.append(round(max(day_temps), 1))
        daily_temp_min.append(round(min(day_temps), 1))
        daily_precip_sum.append(round(sum(day_precips), 2))
        daily_precip_prob_max.append(int(max(day_probs)))
        daily_wind_speed_max.append(round(max(day_winds), 1))
        daily_wmo.append(int(max(day_codes)))

    # 3. Current observation (anchored to first hour)
    current_payload = {
        "time": base_dt.strftime("%Y-%m-%dT%H:%M"),
        "interval": 900,
        "temperature_2m": hourly_temp[0],
        "relative_humidity_2m": hourly_rh[0],
        "apparent_temperature": hourly_apparent_temp[0],
        "precipitation": hourly_precip[0],
        "rain": hourly_rain[0],
        "weather_code": hourly_weather_code[0],
        "surface_pressure": hourly_pressure[0],
        "wind_speed_10m": hourly_wind_speed[0],
        "wind_direction_10m": hourly_wind_dir[0],
    }

    payload: Dict[str, Any] = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "generationtime_ms": 0.123,
        "utc_offset_seconds": 0,
        "timezone": "UTC",
        "timezone_abbreviation": "UTC",
        "elevation": elev,
        "current": current_payload,
        "hourly": {
            "time": hourly_time,
            "temperature_2m": hourly_temp,
            "relative_humidity_2m": hourly_rh,
            "apparent_temperature": hourly_apparent_temp,
            "precipitation_probability": hourly_precip_prob,
            "precipitation": hourly_precip,
            "rain": hourly_rain,
            "weather_code": hourly_weather_code,
            "surface_pressure": hourly_pressure,
            "wind_speed_10m": hourly_wind_speed,
            "wind_direction_10m": hourly_wind_dir,
        },
        "daily": {
            "time": daily_time,
            "weather_code": daily_wmo,
            "temperature_2m_max": daily_temp_max,
            "temperature_2m_min": daily_temp_min,
            "precipitation_sum": daily_precip_sum,
            "precipitation_probability_max": daily_precip_prob_max,
            "wind_speed_10m_max": daily_wind_speed_max,
        },
    }

    return payload


def generate_weather_bytes(
    city: str,
    seed: int = SIMULATOR_DEFAULT_SEED,
    ref_time: str = SIMULATOR_DEFAULT_REF_TIME,
) -> bytes:
    """Serialize simulated weather payload to canonical UTF-8 bytes with single trailing newline."""
    payload = generate_weather(city=city, seed=seed, ref_time=ref_time)
    canonical_json_str = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
    return (canonical_json_str + "\n").encode("utf-8")


def save_simulated_payload(
    city: str,
    seed: int = SIMULATOR_DEFAULT_SEED,
    ref_time: str = SIMULATOR_DEFAULT_REF_TIME,
    output_path: Optional[str] = None,
) -> str:
    """Save canonical bytes directly to file using binary write mode ('wb') to guarantee byte determinism."""
    if output_path is None:
        os.makedirs("data/raw", exist_ok=True)
        safe_city = city.strip().replace(" ", "_")
        target_path = os.path.join("data", "raw", f"weather_raw_{safe_city}_simulated.json")
    else:
        target_path = output_path

    target_dir = os.path.dirname(target_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    canonical_bytes = generate_weather_bytes(city=city, seed=seed, ref_time=ref_time)
    with open(target_path, "wb") as f:
        f.write(canonical_bytes)

    return target_path
