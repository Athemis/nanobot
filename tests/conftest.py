"""Pytest configuration for test-only logging behavior."""

from __future__ import annotations

import sys

from loguru import logger


def pytest_sessionstart(session) -> None:
    """Keep media cleanup logs quiet in tests to avoid teardown stream-noise."""
    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG",
        filter=lambda record: (
            record["name"] != "nanobot.utils.media_cleanup"
            or record["level"].no >= 30
        ),
    )
