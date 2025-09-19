"""
Test package for SuperDots.

This package contains unit tests and integration tests for all SuperDots
functionality including configuration management, synchronization, Git operations,
and cross-platform utilities.
"""

import sys
import os
from pathlib import Path

# Add src directory to path so tests can import superdots modules
test_dir = Path(__file__).parent
src_dir = test_dir.parent / 'src'
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Test configuration
TEST_DATA_DIR = test_dir / 'data'
TEST_FIXTURES_DIR = test_dir / 'fixtures'
TEST_TEMP_DIR = test_dir / 'temp'

# Ensure test directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)
TEST_FIXTURES_DIR.mkdir(exist_ok=True)
TEST_TEMP_DIR.mkdir(exist_ok=True)

# Test constants
DEFAULT_TEST_REPO_NAME = 'test_superdots_repo'
DEFAULT_TEST_CONFIG_NAME = 'test_config'

__version__ = '1.0.0'
__all__ = [
    'TEST_DATA_DIR',
    'TEST_FIXTURES_DIR',
    'TEST_TEMP_DIR',
    'DEFAULT_TEST_REPO_NAME',
    'DEFAULT_TEST_CONFIG_NAME',
]
