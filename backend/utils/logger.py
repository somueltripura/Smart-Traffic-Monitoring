import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from pathlib import Path

from backend.config import Config


def setup_logger(name: str = "TrafficMonitor") -> logging.Logger:
    """Configures and returns a centralized application logger.

    Args:
        name: Name of the logger component.

    Returns:
        logging.Logger configured with console and rotating file handlers.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    log_level = logging.DEBUG if Config.DEBUG else logging.INFO
    logger.setLevel(log_level)

    log_format = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    # Rotating File Handler (10 MB max per file, 5 backups)
    log_file_path = Config.LOGS_DIR / "traffic_system.log"
    try:
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)
    except Exception as exc:
        logger.warning("Could not initialize file logger: %s", exc)

    return logger


# Default system logger instance
logger = setup_logger("System")
