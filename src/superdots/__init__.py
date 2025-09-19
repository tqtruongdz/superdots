"""
SuperDots - A cross-platform dotfiles and configuration management tool

This package provides tools for managing configuration files across different
operating systems using Git repositories for synchronization.
"""

__version__ = "1.0.0"
__author__ = "SuperDots Team"
__email__ = "admin@superdots.dev"
__description__ = "A cross-platform dotfiles and configuration management tool"

# Core imports - use try/except to handle import errors gracefully
try:
    from .core.config import ConfigManager
except ImportError:
    ConfigManager = None

try:
    from .core.sync import SyncManager
except ImportError:
    SyncManager = None

try:
    from .core.git_handler import GitHandler
except ImportError:
    GitHandler = None

try:
    from .utils.platform import PlatformDetector
except ImportError:
    PlatformDetector = None

try:
    from .utils.logger import get_logger
except ImportError:
    get_logger = None

# Version info
VERSION = __version__
VERSION_INFO = tuple(map(int, __version__.split('.')))

# Package metadata
__all__ = [
    'ConfigManager',
    'SyncManager',
    'GitHandler',
    'PlatformDetector',
    'get_logger',
    'VERSION',
    'VERSION_INFO',
]

# Initialize logger
try:
    if get_logger:
        logger = get_logger(__name__)
        logger.info(f"SuperDots v{__version__} initialized")
    else:
        logger = None
except Exception:
    logger = None
