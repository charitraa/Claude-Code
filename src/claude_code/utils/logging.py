"""
Logging utilities for Claude Code CLI
"""

import sys
from loguru import logger
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str = None) -> None:
    """
    Setup logging configuration

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    # Remove default handler
    logger.remove()

    # Add console handler with rich formatting
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="10 days",
            backtrace=True,
            diagnose=True,
        )


def get_logger(name: str):
    """
    Get a logger for a specific module

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logger.bind(name=name)