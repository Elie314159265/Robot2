"""
Logging configuration and utilities
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_dir: str = "logs"
) -> logging.Logger:
    """
    Setup logger with file and console handlers.

    Args:
        name: Logger name
        level: Logging level
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # File handler
    log_file = Path(log_dir) / f"{name}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers
    if not logger.handlers:
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger
