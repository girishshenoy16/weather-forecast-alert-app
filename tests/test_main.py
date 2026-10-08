"""Integration tests for main.py CLI driver asserting end-to-end pipeline execution and output isolation."""

from pathlib import Path
import pytest

from main import run_pipeline


def test_main_pipeline_simulation_mode_isolated(tmp_path):
    """Test full pipeline execution in simulation mode redirected to tmp_path sandbox."""
    sandbox_dir = str(tmp_path / "sandbox")

    artifacts = run_pipeline(
        city="Mumbai",
        simulate=True,
        seed=42,
        generate_plots=True,
        compile_dashboard=True,
        generate_reports_flag=True,
        output_dir=sandbox_dir,
    )

    # Assert Ingestion Artifact
    assert "raw_payload" in artifacts
    assert Path(artifacts["raw_payload"]).exists()
    assert Path(artifacts["raw_payload"]).stat().st_size > 1000

    # Assert Normalization Artifacts
    assert "processed_csv" in artifacts
    assert "processed_json" in artifacts
    assert Path(artifacts["processed_csv"]).exists()
    assert Path(artifacts["processed_json"]).exists()

    # Assert Rule Alerts Artifacts
    assert "alert_log" in artifacts
    assert "alert_history" in artifacts
    assert Path(artifacts["alert_log"]).exists()
    assert Path(artifacts["alert_history"]).exists()

    # Assert Visualizer Plots
    assert "plot_trend" in artifacts
    assert "plot_matrix" in artifacts
    assert Path(artifacts["plot_trend"]).exists()
    assert Path(artifacts["plot_matrix"]).exists()

    # Assert Dashboard JSON Artifact
    assert "dashboard_json" in artifacts
    assert "dashboard_html" not in artifacts
    assert Path(artifacts["dashboard_json"]).exists()
    assert Path(artifacts["dashboard_json"]).stat().st_size > 1000

    # Assert Enterprise Reports
    assert "detailed_project_report" in artifacts
    assert "executive_summary_report" in artifacts
    assert "weather_summary_report" in artifacts
    assert Path(artifacts["detailed_project_report"]).exists()
    assert Path(artifacts["executive_summary_report"]).exists()
    assert Path(artifacts["weather_summary_report"]).exists()


def test_main_pipeline_flags_skip_visuals_and_dashboard(tmp_path):
    """Test that --no-plots and --no-dashboard skip generating those artifacts."""
    sandbox_dir = str(tmp_path / "no_plots_sandbox")

    artifacts = run_pipeline(
        city="Delhi",
        simulate=True,
        seed=42,
        generate_plots=False,
        compile_dashboard=False,
        generate_reports_flag=False,
        output_dir=sandbox_dir,
    )

    # Core data must exist
    assert Path(artifacts["processed_csv"]).exists()
    assert Path(artifacts["processed_json"]).exists()

    # Skipped outputs must not be in artifacts
    assert "plot_trend" not in artifacts
    assert "plot_matrix" not in artifacts
    assert "dashboard_json" not in artifacts
    assert "detailed_project_report" not in artifacts
