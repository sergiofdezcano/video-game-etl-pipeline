"""
Logging configuration for the ETL pipeline.
"""
import logging
import sys
from typing import Optional
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_format: str = "standard",
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Configure logging for the application.

    Sets up console logging with optional file output. Configures third-party
    library loggers to reduce noise. Supports both standard and JSON formats.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('standard' or 'json')
        log_file: Optional path to log file for persistent logging

    Returns:
        Configured logger instance

    Raises:
        ValueError: If invalid logging level is provided
    """
    # Validate and convert logging level
    try:
        numeric_level = getattr(logging, level.upper())
    except AttributeError:
        raise ValueError(
            f"Invalid logging level: {level}. "
            f"Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
        )

    # Configure log format
    if log_format == "json":
        # Structured JSON logging for machine parsing
        format_str = (
            '{"time":"%(asctime)s",'
            '"level":"%(levelname)s",'
            '"module":"%(name)s",'
            '"function":"%(funcName)s",'
            '"line":%(lineno)d,'
            '"message":"%(message)s"}'
        )
    else:
        # Human-readable standard format
        format_str = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '%(funcName)s:%(lineno)d - %(message)s'
        )

    # Setup handlers
    handlers = [logging.StreamHandler(sys.stdout)]

    # Add file handler if log_file is specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        handlers.append(file_handler)

    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=format_str,
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers,
        force=True  # Override any existing configuration
    )

    # Set third-party loggers to WARNING to reduce noise
    for lib_name in ['urllib3', 'requests', 'boto3', 'botocore', 's3transfer']:
        logging.getLogger(lib_name).setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={level}, format={log_format}, "
        f"file={'enabled' if log_file else 'disabled'}"
    )

    return logger
