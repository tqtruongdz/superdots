"""
Core modules for SuperDots.

This package contains the main functionality for managing configurations,
synchronization, and Git operations in SuperDots.
"""

from .config import ConfigManager, ConfigFile, ConfigType, ConfigStatus
from .sync import SyncManager, SyncStatus, ConflictResolution
from .git_handler import GitHandler, GitError

__all__ = [
    'ConfigManager',
    'ConfigFile',
    'ConfigType',
    'ConfigStatus',
    'SyncManager',
    'SyncStatus',
    'ConflictResolution',
    'GitHandler',
    'GitError',
]
