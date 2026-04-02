"""Tests for shared logging configuration."""

import logging

import structlog

from simpli_core.logging import setup_logging


class TestSetupLogging:
    def test_console_output(self) -> None:
        setup_logging(log_level="DEBUG", json_output=False)
        logger = structlog.get_logger()
        assert logger is not None

    def test_json_output(self) -> None:
        setup_logging(log_level="INFO", json_output=True)
        logger = structlog.get_logger()
        assert logger is not None

    def test_root_logger_level(self) -> None:
        setup_logging(log_level="WARNING")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_default_level_is_info(self) -> None:
        setup_logging()
        root = logging.getLogger()
        assert root.level == logging.INFO
