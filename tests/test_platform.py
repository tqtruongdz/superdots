#!/usr/bin/env python3
"""
Tests for platform detection utilities.
"""

import os
import platform
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from superdots.utils.platform import (
    PlatformDetector,
    OSType,
    get_os_type,
    is_linux,
    is_macos,
    is_windows,
    get_home_dir,
    get_config_dir,
    platform_detector
)


class TestOSType:
    """Test OSType enum."""

    def test_os_type_values(self):
        """Test that OSType has correct values."""
        assert OSType.LINUX.value == "linux"
        assert OSType.MACOS.value == "darwin"
        assert OSType.WINDOWS.value == "windows"
        assert OSType.UNKNOWN.value == "unknown"


class TestPlatformDetector:
    """Test PlatformDetector class."""

    @patch('platform.system')
    def test_detect_linux(self, mock_system):
        """Test Linux detection."""
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()
        assert detector.os_type == OSType.LINUX
        assert detector.is_linux is True
        assert detector.is_macos is False
        assert detector.is_windows is False

    @patch('platform.system')
    def test_detect_macos(self, mock_system):
        """Test macOS detection."""
        mock_system.return_value = 'Darwin'
        detector = PlatformDetector()
        assert detector.os_type == OSType.MACOS
        assert detector.is_linux is False
        assert detector.is_macos is True
        assert detector.is_windows is False

    @patch('platform.system')
    def test_detect_windows(self, mock_system):
        """Test Windows detection."""
        mock_system.return_value = 'Windows'
        detector = PlatformDetector()
        assert detector.os_type == OSType.WINDOWS
        assert detector.is_linux is False
        assert detector.is_macos is False
        assert detector.is_windows is True

    @patch('platform.system')
    def test_detect_unknown(self, mock_system):
        """Test unknown OS detection."""
        mock_system.return_value = 'SomeWeirdOS'
        detector = PlatformDetector()
        assert detector.os_type == OSType.UNKNOWN
        assert detector.is_linux is False
        assert detector.is_macos is False
        assert detector.is_windows is False

    def test_home_dir(self):
        """Test home directory detection."""
        detector = PlatformDetector()
        assert detector.home_dir == Path.home()
        assert isinstance(detector.home_dir, Path)

    @patch('platform.system')
    def test_config_paths_linux(self, mock_system):
        """Test config paths on Linux."""
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()

        config_dir = detector.get_config_dir()
        assert config_dir == Path.home() / '.config'

        local_share_dir = detector.get_config_dir('local_share')
        assert local_share_dir == Path.home() / '.local' / 'share'

    @patch('platform.system')
    @patch.dict(os.environ, {'APPDATA': '/mock/appdata', 'LOCALAPPDATA': '/mock/localappdata'})
    def test_config_paths_windows(self, mock_system):
        """Test config paths on Windows."""
        mock_system.return_value = 'Windows'
        detector = PlatformDetector()

        config_dir = detector.get_config_dir()
        assert str(config_dir) == '/mock/appdata'

    def test_normalize_path(self):
        """Test path normalization."""
        detector = PlatformDetector()

        # Test with string path
        path_str = "~/test/path"
        normalized = detector.normalize_path(path_str)
        assert isinstance(normalized, Path)
        assert str(normalized).startswith(str(Path.home()))

        # Test with Path object
        path_obj = Path("~/test/path")
        normalized = detector.normalize_path(path_obj)
        assert isinstance(normalized, Path)

    @patch('platform.system')
    def test_get_dotfiles_locations_linux(self, mock_system):
        """Test dotfile locations on Linux."""
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()

        locations = detector.get_dotfiles_locations()

        assert 'shell' in locations
        assert 'editors' in locations
        assert 'git' in locations

        # Check some expected paths
        shell_paths = locations['shell']
        assert any('.bashrc' in str(path) for path in shell_paths)
        assert any('.zshrc' in str(path) for path in shell_paths)

    def test_get_shell_config_files(self):
        """Test getting existing shell config files."""
        detector = PlatformDetector()
        shell_files = detector.get_shell_config_files()

        # Should return only existing files
        for file_path in shell_files:
            assert file_path.exists()
            assert isinstance(file_path, Path)

    @patch('platform.system')
    def test_get_executable_extension(self, mock_system):
        """Test executable extension detection."""
        # Windows
        mock_system.return_value = 'Windows'
        detector = PlatformDetector()
        assert detector.get_executable_extension() == '.exe'

        # Linux
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()
        assert detector.get_executable_extension() == ''

    @patch('platform.system')
    def test_get_script_extension(self, mock_system):
        """Test script extension detection."""
        # Windows
        mock_system.return_value = 'Windows'
        detector = PlatformDetector()
        assert detector.get_script_extension() == '.bat'

        # Linux
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()
        assert detector.get_script_extension() == '.sh'

    def test_get_path_separator(self):
        """Test path separator detection."""
        detector = PlatformDetector()
        assert detector.get_path_separator() == os.pathsep

    @patch('platform.system')
    def test_can_symlink_linux(self, mock_system):
        """Test symlink capability on Linux."""
        mock_system.return_value = 'Linux'
        detector = PlatformDetector()
        assert detector.can_symlink() is True

    @patch('platform.system')
    @patch('ctypes.windll.shell32.IsUserAnAdmin')
    def test_can_symlink_windows(self, mock_admin, mock_system):
        """Test symlink capability on Windows."""
        mock_system.return_value = 'Windows'

        # Test as admin
        mock_admin.return_value = True
        detector = PlatformDetector()
        assert detector.can_symlink() is True

        # Test as non-admin
        mock_admin.return_value = False
        detector = PlatformDetector()
        assert detector.can_symlink() is False

    def test_get_system_info(self):
        """Test system info gathering."""
        detector = PlatformDetector()
        info = detector.get_system_info()

        required_keys = [
            'os_type', 'platform', 'machine', 'processor',
            'architecture', 'python_version', 'home_directory',
            'config_directory', 'can_symlink'
        ]

        for key in required_keys:
            assert key in info
            assert info[key] is not None

        assert info['os_type'] in ['linux', 'darwin', 'windows', 'unknown']


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_get_os_type(self):
        """Test get_os_type function."""
        os_type = get_os_type()
        assert isinstance(os_type, OSType)
        assert os_type in [OSType.LINUX, OSType.MACOS, OSType.WINDOWS, OSType.UNKNOWN]

    def test_is_functions(self):
        """Test is_* functions."""
        # These should return booleans and be mutually exclusive (except for unknown)
        linux_result = is_linux()
        macos_result = is_macos()
        windows_result = is_windows()

        assert isinstance(linux_result, bool)
        assert isinstance(macos_result, bool)
        assert isinstance(windows_result, bool)

        # Only one should be True (unless unknown OS)
        true_count = sum([linux_result, macos_result, windows_result])
        assert true_count <= 1

    def test_get_home_dir(self):
        """Test get_home_dir function."""
        home = get_home_dir()
        assert isinstance(home, Path)
        assert home == Path.home()

    def test_get_config_dir(self):
        """Test get_config_dir function."""
        config_dir = get_config_dir()
        assert isinstance(config_dir, Path)

        # Test with custom name
        custom_dir = get_config_dir('local_share')
        assert isinstance(custom_dir, Path)


class TestGlobalInstance:
    """Test global platform_detector instance."""

    def test_global_instance(self):
        """Test that global instance exists and works."""
        assert platform_detector is not None
        assert isinstance(platform_detector, PlatformDetector)
        assert hasattr(platform_detector, 'os_type')
        assert hasattr(platform_detector, 'home_dir')


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Create a temporary home directory for testing."""
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()

    # Mock Path.home() to return our fake home
    monkeypatch.setattr(Path, 'home', lambda: fake_home)

    return fake_home


class TestCreateSymlink:
    """Test symlink creation functionality."""

    def test_create_symlink_success(self, temp_home):
        """Test successful symlink creation."""
        detector = PlatformDetector()

        # Create source file
        source = temp_home / "source.txt"
        source.write_text("test content")

        # Create symlink
        target = temp_home / "link.txt"

        if detector.can_symlink():
            result = detector.create_symlink(source, target)
            assert result is True
            assert target.exists()
            # On systems that support symlinks, check if it's actually a symlink
            if hasattr(target, 'is_symlink') and target.is_symlink():
                assert target.is_symlink()
        else:
            # On systems without symlink support, should fall back to copy
            result = detector.create_symlink(source, target)
            assert result is True
            assert target.exists()
            assert target.read_text() == "test content"

    def test_create_symlink_force(self, temp_home):
        """Test symlink creation with force option."""
        detector = PlatformDetector()

        # Create source file
        source = temp_home / "source.txt"
        source.write_text("test content")

        # Create existing target
        target = temp_home / "existing.txt"
        target.write_text("existing content")

        # Create symlink with force
        result = detector.create_symlink(source, target, force=True)
        assert result is True
        assert target.exists()

    def test_create_symlink_directory(self, temp_home):
        """Test symlink creation for directories."""
        detector = PlatformDetector()

        # Create source directory
        source = temp_home / "source_dir"
        source.mkdir()
        (source / "file.txt").write_text("test")

        # Create symlink to directory
        target = temp_home / "link_dir"

        result = detector.create_symlink(source, target)
        assert result is True
        assert target.exists()
        assert (target / "file.txt").exists()
