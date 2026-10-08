"""Matplotlib Publication-Grade Meteorological Visualization Module.

Generates dual-axis forecast trend timelines and 4-panel meteorological diagnostic
matrices adhering to strict scientific aesthetics, high resolution (300 DPI),
and legal CC BY 4.0 data attribution.
"""

import os
from typing import Any, Dict, List, Optional, Union
import matplotlib
# Use Agg backend for headless / server / CI execution
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import ATTRIBUTION_NOTICE, NON_OFFICIAL_DISCLAIMER


def _load_data_as_df(
    data: Union[str, pd.DataFrame, List[Dict[str, Any]]]
) -> pd.DataFrame:
    """Normalize input into pandas DataFrame."""
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, list):
        df = pd.DataFrame(data)
    elif isinstance(data, str):
        if data.endswith(".csv"):
            df = pd.read_csv(data)
        else:
            df = pd.read_json(data)
    else:
        raise ValueError("Unsupported data format for visualizer.")
    return df


def generate_forecast_trend_plot(
    processed_data: Union[str, pd.DataFrame, List[Dict[str, Any]]],
    output_path: str = "outputs/plots/forecast_trend_sample.png",
    dpi: int = 300,
) -> str:
    """Generate dual-axis timeline chart: temperature curves (primary Y) and precipitation bars (secondary Y)."""
    df = _load_data_as_df(processed_data)

    hourly_df = df[df["record_type"] == "HOURLY"].copy()
    if hourly_df.empty:
        hourly_df = df.copy()

    # Limit to first 48 or 72 hours for clean chart legibility
    if len(hourly_df) > 72:
        hourly_df = hourly_df.iloc[:72]

    timestamps = pd.to_datetime(hourly_df["timestamp_iso"])
    temps = pd.to_numeric(hourly_df["temp_celsius"], errors="coerce")
    feels_like = pd.to_numeric(hourly_df["apparent_temp_celsius"], errors="coerce")
    precip = pd.to_numeric(hourly_df["precip_amount_mm"], errors="coerce").fillna(0.0)

    # Dark executive theme palette
    bg_color = "#0B132B"
    card_color = "#1C2541"
    text_color = "#E0E6ED"
    temp_color = "#FF6B6B"
    feels_color = "#FFA07A"
    precip_color = "#4D96FF"
    grid_color = "#2E3856"

    fig, ax1 = plt.subplots(figsize=(12, 6), facecolor=bg_color)
    ax1.set_facecolor(card_color)

    # 1. Primary Y-axis: Temperature curves
    l1 = ax1.plot(
        timestamps,
        temps,
        color=temp_color,
        linewidth=2.5,
        label="Temperature (°C)",
    )
    l2 = ax1.plot(
        timestamps,
        feels_like,
        color=feels_color,
        linewidth=1.8,
        linestyle="--",
        label="Feels Like (°C)",
    )
    ax1.set_ylabel("Temperature (°C)", color=temp_color, fontsize=12, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=temp_color)
    ax1.tick_params(axis="x", labelcolor=text_color, rotation=30)
    ax1.grid(True, linestyle=":", color=grid_color, alpha=0.7)

    # 2. Secondary Y-axis: 1-hour Precipitation bars
    ax2 = ax1.twinx()
    # Compute width in days for bar alignment
    bar_width = 0.035 if len(timestamps) > 1 else 0.1
    b1 = ax2.bar(
        timestamps,
        precip,
        width=bar_width,
        color=precip_color,
        alpha=0.55,
        label="Hourly Precipitation (mm)",
    )
    ax2.set_ylabel("1h Precipitation (mm)", color=precip_color, fontsize=12, fontweight="bold")
    ax2.tick_params(axis="y", labelcolor=precip_color)
    max_p = max(precip.max() if not precip.empty else 0.0, 5.0)
    ax2.set_ylim(0, max_p * 2.5)  # headroom so bars don't drown temperature lines

    # Formatting X-axis dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %H:%M"))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=6))

    # Combined Legend
    lines = l1 + l2 + [b1]
    labels = [l.get_label() for l in lines]
    leg = ax1.legend(lines, labels, loc="upper right", facecolor=bg_color, edgecolor=grid_color)
    for text in leg.get_texts():
        text.set_color(text_color)

    # Title & CC BY 4.0 Attribution
    city_name = hourly_df["city_name"].iloc[0] if "city_name" in hourly_df.columns else "Location"
    plt.title(
        f"Meteorological Forecast Trend Timeline — {city_name}",
        color=text_color,
        fontsize=14,
        fontweight="bold",
        pad=15,
    )

    # Attribution Footer
    fig.text(
        0.5,
        0.01,
        ATTRIBUTION_NOTICE,
        ha="center",
        fontsize=9,
        color="#8D99AE",
        style="italic",
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])

    target_dir = os.path.dirname(output_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    fig.savefig(output_path, dpi=dpi, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return output_path


def generate_meteorological_matrix(
    processed_data: Union[str, pd.DataFrame, List[Dict[str, Any]]],
    output_path: str = "outputs/plots/meteorological_matrix.png",
    dpi: int = 300,
) -> str:
    """Generate 4-panel multi-variable diagnostic matrix figure."""
    df = _load_data_as_df(processed_data)
    hourly_df = df[df["record_type"] == "HOURLY"].copy()
    if hourly_df.empty:
        hourly_df = df.copy()

    if len(hourly_df) > 72:
        hourly_df = hourly_df.iloc[:72]

    timestamps = pd.to_datetime(hourly_df["timestamp_iso"])
    temps = pd.to_numeric(hourly_df["temp_celsius"], errors="coerce")
    feels = pd.to_numeric(hourly_df["apparent_temp_celsius"], errors="coerce")
    wind = pd.to_numeric(hourly_df["wind_speed_kmh"], errors="coerce").fillna(0.0)
    pressure = pd.to_numeric(hourly_df["pressure_hpa"], errors="coerce")
    precip = pd.to_numeric(hourly_df["precip_amount_mm"], errors="coerce").fillna(0.0)
    precip_prob = pd.to_numeric(hourly_df["precip_prob_pct"], errors="coerce").fillna(0)

    bg_color = "#0B132B"
    card_color = "#1C2541"
    text_color = "#E0E6ED"
    grid_color = "#2E3856"

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), facecolor=bg_color)

    # Panel 1: Temperature & Feels-Like Curves
    ax_t = axes[0, 0]
    ax_t.set_facecolor(card_color)
    ax_t.plot(timestamps, temps, color="#FF6B6B", label="Dry-Bulb (°C)", linewidth=2)
    ax_t.plot(timestamps, feels, color="#FFA07A", linestyle="--", label="Feels-Like (°C)", linewidth=1.5)
    ax_t.set_title("1. Thermal Regimes", color=text_color, fontsize=11, fontweight="bold")
    ax_t.grid(True, linestyle=":", color=grid_color)
    ax_t.tick_params(colors=text_color)
    ax_t.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
    leg1 = ax_t.legend(facecolor=bg_color, edgecolor=grid_color)
    for t in leg1.get_texts():
        t.set_color(text_color)

    # Panel 2: Wind Speed with Threshold Reference Lines
    ax_w = axes[0, 1]
    ax_w.set_facecolor(card_color)
    ax_w.plot(timestamps, wind, color="#6BCB77", linewidth=2, label="10m Wind Speed (km/h)")
    ax_w.axhline(50.0, color="#FFD93D", linestyle=":", linewidth=1.5, label="Warning (50 km/h)")
    ax_w.axhline(75.0, color="#FF6B6B", linestyle="--", linewidth=1.5, label="Critical (75 km/h)")
    ax_w.set_title("2. Anemometric Dynamics", color=text_color, fontsize=11, fontweight="bold")
    ax_w.grid(True, linestyle=":", color=grid_color)
    ax_w.tick_params(colors=text_color)
    ax_w.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
    leg2 = ax_w.legend(facecolor=bg_color, edgecolor=grid_color)
    for t in leg2.get_texts():
        t.set_color(text_color)

    # Panel 3: Surface Atmospheric Pressure
    ax_p = axes[1, 0]
    ax_p.set_facecolor(card_color)
    ax_p.plot(timestamps, pressure, color="#9D4EDD", linewidth=2, label="Surface Pressure (hPa)")
    mean_p = pressure.mean()
    if not np.isnan(mean_p):
        ax_p.axhline(mean_p, color="#C77DFF", linestyle=":", label=f"Mean ({mean_p:.1f} hPa)")
    ax_p.set_title("3. Barometric Profile", color=text_color, fontsize=11, fontweight="bold")
    ax_p.grid(True, linestyle=":", color=grid_color)
    ax_p.tick_params(colors=text_color)
    ax_p.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))
    leg3 = ax_p.legend(facecolor=bg_color, edgecolor=grid_color)
    for t in leg3.get_texts():
        t.set_color(text_color)

    # Panel 4: Precipitation & Probability
    ax_pr = axes[1, 1]
    ax_pr.set_facecolor(card_color)
    bar_width = 0.035 if len(timestamps) > 1 else 0.1
    ax_pr.bar(timestamps, precip, width=bar_width, color="#4D96FF", alpha=0.6, label="Precipitation (mm)")
    ax_pr.set_ylabel("1h Accumulation (mm)", color="#4D96FF", fontsize=10)
    ax_pr.tick_params(colors=text_color)
    ax_pr.xaxis.set_major_formatter(mdates.DateFormatter("%d %H:%M"))

    ax_prob = ax_pr.twinx()
    ax_prob.plot(timestamps, precip_prob, color="#00F5D4", linewidth=1.5, linestyle="--", label="Precip Prob (%)")
    ax_prob.set_ylabel("Probability (%)", color="#00F5D4", fontsize=10)
    ax_prob.tick_params(colors=text_color)
    ax_prob.set_ylim(0, 105)

    ax_pr.set_title("4. Hydrological Matrix", color=text_color, fontsize=11, fontweight="bold")
    ax_pr.grid(True, linestyle=":", color=grid_color)

    city_name = hourly_df["city_name"].iloc[0] if "city_name" in hourly_df.columns else "Location"
    fig.suptitle(
        f"Meteorological Diagnostic Matrix — {city_name}",
        color=text_color,
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )

    fig.text(
        0.5,
        0.02,
        f"{ATTRIBUTION_NOTICE} | {NON_OFFICIAL_DISCLAIMER}",
        ha="center",
        fontsize=8.5,
        color="#8D99AE",
        style="italic",
    )

    plt.tight_layout(rect=[0, 0.04, 1, 0.96])

    target_dir = os.path.dirname(output_path)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    fig.savefig(output_path, dpi=dpi, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    return output_path
