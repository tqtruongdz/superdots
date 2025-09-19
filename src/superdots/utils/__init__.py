"""
Utility modules for SuperDots.

This package contains utility functions and classes for platform detection,
logging, and other common operations used throughout SuperDots.
"""

from .logger import get_logger, setup_logging
from .platform import platform_detector, get_os_type, is_linux, is_macos, is_windows

__all__ = [
    'get_logger',
    'setup_logging',
    'platform_detector',
    'get_os_type',
    'is_linux',
    'is_macos',
    'is_windows',
]
