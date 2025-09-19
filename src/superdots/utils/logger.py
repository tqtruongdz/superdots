#!/usr/bin/env python3
"""
Logging utilities for SuperDots.

This module provides a centralized logging system with support for different
log levels, colored output, and file logging.
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from colorama import init as colorama_init, Fore, Back, Style
    from rich.console import Console
    from rich.logging import RichHandler
    HAS_RICH = True
    HAS_COLORAMA = True
    colorama_init()
except ImportError:
    HAS_RICH = False
    HAS_COLORAMA = False
    Fore = Back = Style = None


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output for console logging."""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def __init__(self, fmt: str = None, datefmt: str = None, use_colors: bool = True):
        super().__init__(fmt, datefmt)
        self.use_colors = use_colors and HAS_COLORAMA

    def format(self, record: logging.LogRecord) -> str:
        if self.use_colors:
            # Save original levelname
            original_levelname = record.levelname

            # Color the levelname
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"

            # Format the message
            formatted = super().format(record)

            # Restore original levelname
            record.levelname = original_levelname

            return formatted
        else:
            return super().format(record)


class SuperDotsLogger:
    """Main logger class for SuperDots."""

    def __init__(self, name: str = 'superdots'):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        self._setup_handlers()

    def _setup_handlers(self):
        """Setup logging handlers for console and file output."""

        # Console handler
        if HAS_RICH:
            console_handler = RichHandler(
                console=Console(stderr=True),
                show_time=False,
                show_path=False,
                rich_tracebacks=True
            )
            console_format = "%(message)s"
        else:
            console_handler = logging.StreamHandler(sys.stderr)
            console_format = "[%(levelname)s] %(name)s: %(message)s"
            console_handler.setFormatter(ColoredFormatter(console_format))

        console_handler.setLevel(logging.INFO)
        if HAS_RICH:
            console_handler.setFormatter(logging.Formatter(console_format))

        self.logger.addHandler(console_handler)

        # File handler (if log directory exists)
        self._setup_file_handler()

    def _setup_file_handler(self):
        """Setup file logging handler."""
        try:
            # Try to create logs directory
            log_dir = Path.home() / '.config' / 'superdots' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)

            log_file = log_dir / 'superdots.log'

            # Use rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=5 * 1024 * 1024,  # 5MB
                backupCount=5
            )

            file_format = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(logging.Formatter(
                file_format,
                datefmt='%Y-%m-%d %H:%M:%S'
            ))

            file_handler.setLevel(logging.DEBUG)
            self.logger.addHandler(file_handler)

        except Exception as e:
            # If we can't setup file logging, just continue with console
            self.logger.warning(f"Could not setup file logging: {e}")

    def set_level(self, level: str):
        """Set the logging level."""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL,
        }

        log_level = level_map.get(level.upper(), logging.INFO)
        self.logger.setLevel(log_level)

        # Also update console handler level
        for handler in self.logger.handlers:
            if isinstance(handler, (logging.StreamHandler, RichHandler if HAS_RICH else type(None))):
                handler.setLevel(log_level)

    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, *args, **kwargs)


# Global logger instances
_loggers: Dict[str, SuperDotsLogger] = {}


def get_logger(name: str = 'superdots') -> SuperDotsLogger:
    """Get or create a logger instance."""
    if name not in _loggers:
        _loggers[name] = SuperDotsLogger(name)
    return _loggers[name]


def set_log_level(level: str, logger_name: str = 'superdots'):
    """Set logging level for a specific logger."""
    logger = get_logger(logger_name)
    logger.set_level(level)


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[Path] = None,
    verbose: bool = False
):
    """Setup logging configuration."""
    if verbose:
        level = 'DEBUG'

    # Setup main logger
    logger = get_logger()
    logger.set_level(level)

    # Add custom file handler if specified
    if log_file:
        try:
            log_file = Path(log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_format = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(filename)s:%(lineno)d - %(message)s"
            )
            file_handler.setFormatter(logging.Formatter(
                file_format,
                datefmt='%Y-%m-%d %H:%M:%S'
            ))

            logger.logger.addHandler(file_handler)
            logger.info(f"Logging to file: {log_file}")

        except Exception as e:
            logger.warning(f"Could not setup custom log file {log_file}: {e}")


# Convenience functions
def debug(message: str, *args, **kwargs):
    """Log debug message using default logger."""
    get_logger().debug(message, *args, **kwargs)


def info(message: str, *args, **kwargs):
    """Log info message using default logger."""
    get_logger().info(message, *args, **kwargs)


def warning(message: str, *args, **kwargs):
    """Log warning message using default logger."""
    get_logger().warning(message, *args, **kwargs)


def error(message: str, *args, **kwargs):
    """Log error message using default logger."""
    get_logger().error(message, *args, **kwargs)


def critical(message: str, *args, **kwargs):
    """Log critical message using default logger."""
    get_logger().critical(message, *args, **kwargs)


def exception(message: str, *args, **kwargs):
    """Log exception with traceback using default logger."""
    get_logger().exception(message, *args, **kwargs)
