"""Unified Application CLI Driver for Weather Forecast & Alert Application.

Orchestrates the entire meteorological intelligence pipeline:
Data Ingestion (Live API or Deterministic Simulation) ->
Transformation & Normalization -> Rule-Based Alert Engine ->
Matplotlib Visualizations -> Dashboard JSON Artifact -> Comprehensive Reports.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import colorama
from colorama import Fore, Style

from src.api_client import fetch_weather_forecast, get_city_coordinates
from src.alerts import process_alerts
from src.config import (
    ALERT_DISCLAIMER_TEXT,
    ALERT_ORIGIN_TAG,
    ATTRIBUTION_NOTICE,
    DEFAULT_CITY,
    NON_OFFICIAL_DISCLAIMER,
    SIMULATOR_DEFAULT_REF_TIME,
    SIMULATOR_DEFAULT_SEED,
    WeatherAppException,
)
from src.logger import setup_logger
from src.parser import (
    export_dashboard_json,
    export_processed_datasets,
    normalize_weather_data,
)
from src.reporter import generate_all_reports
from src.simulator import generate_weather, save_simulated_payload
from src.visualizer import generate_forecast_trend_plot, generate_meteorological_matrix

# Initialize colorama for cross-platform ANSI support
colorama.init(autoreset=True)


def print_banner() -> None:
    """Print high-contrast enterprise terminal banner."""
    print(Fore.CYAN + Style.BRIGHT + "=" * 80)
    print(Fore.YELLOW + Style.BRIGHT + "   WEATHER FORECAST & ALERT APPLICATION — PIPELINE CONTROLLER")
    print(Fore.CYAN + Style.BRIGHT + "=" * 80)
    print(Fore.WHITE + "   Dual-Engine Architecture: Open-Meteo REST API & Deterministic Simulation")
    print(Fore.LIGHTBLACK_EX + "   Role Alignment: Python Developer | API Specialist | Data & Automation")
    print(Fore.CYAN + Style.BRIGHT + "-" * 80)


def run_pipeline(
    city: str = DEFAULT_CITY,
    simulate: bool = False,
    seed: int = SIMULATOR_DEFAULT_SEED,
    ref_time: str = SIMULATOR_DEFAULT_REF_TIME,
    generate_plots: bool = True,
    compile_dashboard: bool = True,
    generate_reports_flag: bool = True,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute complete end-to-end meteorological pipeline.

    Returns:
        Dictionary of generated artifacts and status metrics.
    """
    base_dir = Path(output_dir) if output_dir else Path(".")
    data_raw_dir = base_dir / "data" / "raw"
    data_proc_dir = base_dir / "data" / "processed"
    reports_dir = base_dir / "reports"
    plots_dir = base_dir / "outputs" / "plots"
    docs_dir = base_dir / "docs"
    logs_dir = base_dir / "logs"

    data_raw_dir.mkdir(parents=True, exist_ok=True)
    data_proc_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    app_log_file = str(logs_dir / "weather_app.log")
    logger = setup_logger("weather_app", log_file=app_log_file)
    logger.info("=" * 60)
    logger.info("Pipeline execution initiated: city='%s', simulate=%s, seed=%s, ref_time='%s'", city, simulate, seed, ref_time)

    artifacts: Dict[str, Any] = {}
    artifacts["application_log"] = app_log_file

    print_banner()

    # -------------------------------------------------------------------------
    # Stage 1: Data Ingestion
    # -------------------------------------------------------------------------
    if simulate:
        logger.info("Stage 1 Ingestion: Running in deterministic simulation mode (seed=%d, epoch=%s)", seed, ref_time)
        print(Fore.MAGENTA + Style.BRIGHT + f"\n[STAGE 1/6] Ingestion: Deterministic Simulation Mode (City: {city})")
        print(Fore.WHITE + f"  Using isolated seed={seed}, reference epoch={ref_time}")
        sim_file = str(data_raw_dir / f"weather_raw_{city}_simulated.json")
        raw_path = save_simulated_payload(city=city, seed=seed, ref_time=ref_time, output_path=sim_file)
        payload = generate_weather(city=city, seed=seed, ref_time=ref_time)
        city_name = city
        country_code = "IN" if city.lower() in ("mumbai", "delhi", "bengaluru", "kolkata", "chennai", "hyderabad", "pune") else "SIM"
        artifacts["raw_payload"] = raw_path
        logger.info("Stage 1 Ingestion: Saved raw simulated payload to %s", raw_path)
        print(Fore.GREEN + f"  [SUCCESS] Raw canonical bytes saved to: {raw_path}")
    else:
        logger.info("Stage 1 Ingestion: Querying Open-Meteo REST API for city='%s'", city)
        print(Fore.CYAN + Style.BRIGHT + f"\n[STAGE 1/6] Ingestion: Live Open-Meteo REST API (City: {city})")
        print(Fore.WHITE + "  Resolving coordinates via Geocoding API...")
        lat, lon, city_name, country_code, timezone_str = get_city_coordinates(city)
        logger.info("Stage 1 Ingestion: Geocoded %s to lat=%.4f, lon=%.4f, tz=%s", city_name, lat, lon, timezone_str)
        print(Fore.WHITE + f"  Resolved: {city_name}, {country_code} ({lat:.4f}°, {lon:.4f}°) | Timezone: {timezone_str}")

        print(Fore.WHITE + "  Querying forecast endpoint with bounded exponential backoff...")
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_city = city_name.replace(" ", "_")
        raw_file = str(data_raw_dir / f"weather_raw_{safe_city}_{now_str}.json")
        payload, raw_path = fetch_weather_forecast(
            lat=lat,
            lon=lon,
            timezone_str=timezone_str,
            city=city_name,
            output_path=raw_file,
        )
        artifacts["raw_payload"] = raw_path
        logger.info("Stage 1 Ingestion: Saved live raw payload to %s", raw_path)
        print(Fore.GREEN + f"  [SUCCESS] Raw API response saved to: {raw_path}")

    # -------------------------------------------------------------------------
    # Stage 2: Normalization & Field Applicability Partitioning
    # -------------------------------------------------------------------------
    logger.info("Stage 2 Normalization: Parsing meteorological payload and computing thermal indices")
    print(Fore.CYAN + Style.BRIGHT + "\n[STAGE 2/6] Normalization & Biometeorological Computation")
    records = normalize_weather_data(payload, city_name=city_name, country_code=country_code)
    csv_file = str(data_proc_dir / "weather_data_processed.csv")
    json_file = str(data_proc_dir / "weather_data_processed.json")
    c_out, j_out = export_processed_datasets(records, csv_path=csv_file, json_path=json_file)
    artifacts["processed_csv"] = c_out
    artifacts["processed_json"] = j_out
    logger.info("Stage 2 Normalization: Exported %d normalized records to CSV and JSON", len(records))
    print(Fore.GREEN + f"  [SUCCESS] Processed 25-column dataset: {len(records)} records ({c_out})")

    # -------------------------------------------------------------------------
    # Stage 3: Rule-Based Alert Evaluation
    # -------------------------------------------------------------------------
    logger.info("Stage 3 Alert Engine: Evaluating threshold rules across %d records", len(records))
    print(Fore.CYAN + Style.BRIGHT + "\n[STAGE 3/6] Rule-Based Alert Engine Evaluation")
    log_file = str(reports_dir / "weather_alerts.log")
    hist_file = str(reports_dir / "alert_history.csv")
    updated_records = process_alerts(records, log_path=log_file, history_path=hist_file)
    active_alerts = [r for r in updated_records if r.get("alert_flag")]
    artifacts["alert_log"] = log_file
    artifacts["alert_history"] = hist_file
    artifacts["active_alerts_count"] = len(active_alerts)

    max_severity = "NONE"
    order = {"CRITICAL": 3, "WARNING": 2, "ADVISORY": 1, "NONE": 0}
    for a in active_alerts:
        sev = a.get("alert_severity", "NONE")
        if order.get(sev, 0) > order.get(max_severity, 0):
            max_severity = sev

    sev_color = {
        "CRITICAL": Fore.RED + Style.BRIGHT,
        "WARNING": Fore.YELLOW + Style.BRIGHT,
        "ADVISORY": Fore.LIGHTYELLOW_EX,
        "NONE": Fore.GREEN + Style.BRIGHT,
    }.get(max_severity, Fore.WHITE)

    logger.info("Stage 3 Alert Engine: Evaluated records; active_alerts=%d, max_severity=%s", len(active_alerts), max_severity)
    print(Fore.WHITE + f"  Evaluated {len(updated_records)} records against local threshold matrix.")
    print(sev_color + f"  Active Rule Advisories: {len(active_alerts)} | Max Severity: {max_severity}")

    # -------------------------------------------------------------------------
    # Stage 4: Publication-Grade Visualizations (Phase 7)
    # -------------------------------------------------------------------------
    if generate_plots:
        logger.info("Stage 4 Visualizations: Generating 300 DPI Matplotlib trend and matrix charts")
        print(Fore.CYAN + Style.BRIGHT + "\n[STAGE 4/6] Data Visualizations (300 DPI Matplotlib)")
        p1 = str(plots_dir / "forecast_trend_sample.png")
        p2 = str(plots_dir / "meteorological_matrix.png")
        out_p1 = generate_forecast_trend_plot(updated_records, output_path=p1)
        out_p2 = generate_meteorological_matrix(updated_records, output_path=p2)
        artifacts["plot_trend"] = out_p1
        artifacts["plot_matrix"] = out_p2
        logger.info("Stage 4 Visualizations: Generated plots: trend=%s, matrix=%s", out_p1, out_p2)
        print(Fore.GREEN + f"  [SUCCESS] Dual-axis timeline plot saved: {out_p1}")
        print(Fore.GREEN + f"  [SUCCESS] 4-Panel diagnostic matrix saved: {out_p2}")
    else:
        logger.info("Stage 4 Visualizations: Skipped (--no-plots)")
        print(Fore.LIGHTBLACK_EX + "\n[STAGE 4/6] Data Visualizations: Skipped (--no-plots)")

    # -------------------------------------------------------------------------
    # Stage 5: PowerBI-Style Dashboard JSON Data Artifact (Phase 8)
    # -------------------------------------------------------------------------
    if compile_dashboard:
        logger.info("Stage 5 Dashboard: Exporting dashboard-ready JSON artifact")
        print(Fore.CYAN + Style.BRIGHT + "\n[STAGE 5/6] Dashboard JSON Artifact Generation (Frontend Data Contract)")
        dash_json_file = str(docs_dir / "weather_data.json")
        out_dash_json = export_dashboard_json(updated_records, output_path=dash_json_file)
        artifacts["dashboard_json"] = out_dash_json
        logger.info("Stage 5 Dashboard: Exported precomputed dashboard data to %s", out_dash_json)
        print(Fore.GREEN + f"  [SUCCESS] Precomputed dashboard JSON saved: {out_dash_json}")
    else:
        logger.info("Stage 5 Dashboard: Skipped (--no-dashboard)")
        print(Fore.LIGHTBLACK_EX + "\n[STAGE 5/6] Dashboard JSON: Skipped (--no-dashboard)")

    # -------------------------------------------------------------------------
    # Stage 6: Comprehensive Enterprise Reports (Phase 9)
    # -------------------------------------------------------------------------
    if generate_reports_flag:
        logger.info("Stage 6 Reports: Generating enterprise Markdown and text bulletins")
        print(Fore.CYAN + Style.BRIGHT + "\n[STAGE 6/6] Enterprise Report Generation")
        reports_dict = generate_all_reports(updated_records, reports_dir=reports_dir)
        artifacts.update(reports_dict)
        logger.info("Stage 6 Reports: Generated deliverables: \n")
        for report_name, report_path in reports_dict.items():
            logger.info("%s: %s", report_name, report_path)
        print(Fore.GREEN + f"  [SUCCESS] Detailed Technical Report: {reports_dict['detailed_project_report']}")
        print(Fore.GREEN + f"  [SUCCESS] Executive Business Summary: {reports_dict['executive_summary_report']}")
        print(Fore.GREEN + f"  [SUCCESS] Meteorological Bulletin:    {reports_dict['weather_summary_report']}")
    else:
        logger.info("Stage 6 Reports: Skipped")
        print(Fore.LIGHTBLACK_EX + "\n[STAGE 6/6] Reports: Skipped")

    # -------------------------------------------------------------------------
    # Pipeline Summary & Attribution
    # -------------------------------------------------------------------------
    curr_rec = next((r for r in updated_records if r.get("record_type") == "CURRENT"), {})
    logger.info("Pipeline execution completed successfully for %s, %s (advisories=%d, max_severity=%s)", city_name, country_code, len(active_alerts), max_severity)
    print(Fore.CYAN + Style.BRIGHT + "\n" + "=" * 80)
    print(Fore.YELLOW + Style.BRIGHT + f"   PIPELINE EXECUTION COMPLETE — {city_name}, {country_code}")
    print(Fore.CYAN + Style.BRIGHT + "=" * 80)
    print(Fore.WHITE + f"   Temperature : {curr_rec.get('temp_celsius', '--')} °C (Feels like: {curr_rec.get('apparent_temp_celsius', '--')} °C)")
    print(Fore.WHITE + f"   Moisture    : {curr_rec.get('humidity_pct', '--')} % RH | Surface Pressure: {curr_rec.get('pressure_hpa', '--')} hPa")
    print(Fore.WHITE + f"   Wind Speed  : {curr_rec.get('wind_speed_kmh', '--')} km/h | Condition: {curr_rec.get('weather_description', 'Nominal')}")
    print(Fore.WHITE + f"   Advisories  : {len(active_alerts)} active events (Severity: {max_severity})")
    print(Fore.LIGHTBLACK_EX + f"   App Log     : {app_log_file}")
    print(Fore.LIGHTBLACK_EX + f"   Origin      : {ALERT_ORIGIN_TAG}")
    print(Fore.LIGHTYELLOW_EX + f"   Notice      : {NON_OFFICIAL_DISCLAIMER}")
    print(Fore.CYAN + f"   Data Credit : {ATTRIBUTION_NOTICE}")
    print(Fore.CYAN + Style.BRIGHT + "=" * 80 + "\n")

    return artifacts


def main() -> int:
    """CLI Entrypoint parser and executor."""
    parser = argparse.ArgumentParser(
        description="Weather Forecast & Alert Application — Automated Meteorological Intelligence Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--city",
        type=str,
        default=DEFAULT_CITY,
        help="City name to fetch forecast for via live Open-Meteo Geocoding/Forecast API",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run offline deterministic simulation engine (zero live API calls, seed=42)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SIMULATOR_DEFAULT_SEED,
        help="Random seed for deterministic simulation mode",
    )
    parser.add_argument(
        "--ref-time",
        type=str,
        default=SIMULATOR_DEFAULT_REF_TIME,
        help="Fixed baseline ISO timestamp for simulator timeline",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip Matplotlib 300 DPI chart generation",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Skip dashboard JSON artifact generation (docs/weather_data.json)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom root directory destination for all generated outputs",
    )

    args = parser.parse_args()

    try:
        run_pipeline(
            city=args.city,
            simulate=args.simulate,
            seed=args.seed,
            ref_time=args.ref_time,
            generate_plots=not args.no_plots,
            compile_dashboard=not args.no_dashboard,
            generate_reports_flag=True,
            output_dir=args.output_dir,
        )
        return 0
    except WeatherAppException as e:
        print(Fore.RED + Style.BRIGHT + f"\n[APPLICATION ERROR] {e}")
        return 1
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n[INTERRUPTED] Pipeline aborted by user.")
        return 130
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + f"\n[UNEXPECTED CRITICAL ERROR] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
