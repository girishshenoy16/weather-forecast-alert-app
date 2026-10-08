"""Unit tests for src/logger.py asserting logger creation, formatting, and isolation."""

import logging
from pathlib import Path
import pytest

from src.logger import get_logger, setup_logger


def test_setup_logger_creates_file_and_formats(tmp_path):
    """Test logger writes structured records with timestamps and levels to tmp_path."""
    log_file = tmp_path / "test_app.log"
    logger = setup_logger("test_weather_app", log_file=log_file, level=logging.INFO)

    logger.info("Informational event executed successfully")
    logger.warning("Advisory threshold approaching caution line")

    # Flush handlers
    for h in logger.handlers:
        h.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")

    assert "[INFO    ]" in content
    assert "[WARNING ]" in content
    assert "Informational event executed successfully" in content
    assert "Advisory threshold approaching caution line" in content
    assert "[test_weather_app]" in content


def test_logger_level_filtering(tmp_path):
    """Test logger filters out records below the specified threshold."""
    log_file = tmp_path / "test_filter.log"
    logger = setup_logger("test_filter_logger", log_file=log_file, level=logging.WARNING)

    logger.debug("Debug event: should be filtered out")
    logger.info("Info event: should be filtered out")
    logger.warning("Warning event: should be recorded")

    for h in logger.handlers:
        h.flush()

    content = log_file.read_text(encoding="utf-8")
    assert "Debug event" not in content
    assert "Info event" not in content
    assert "Warning event: should be recorded" in content


def test_logger_idempotent_handler_attachment(tmp_path):
    """Test repeated setup_logger calls do not duplicate log lines."""
    log_file = tmp_path / "test_idempotent.log"

    logger1 = setup_logger("test_idempotent", log_file=log_file, level=logging.INFO)
    logger2 = setup_logger("test_idempotent", log_file=log_file, level=logging.INFO)

    logger2.info("Single unique message")

    for h in logger2.handlers:
        h.flush()

    content = log_file.read_text(encoding="utf-8")
    assert content.count("Single unique message") == 1
