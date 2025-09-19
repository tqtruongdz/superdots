#!/usr/bin/env python3
"""
Platform detection and OS-specific utilities for SuperDots.

This module provides cross-platform functionality to detect the operating system,
handle path differences, and manage OS-specific configuration locations.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Dict, List, Optional, Union
from enum import Enum


class OSType(Enum):
    """Supported operating system types."""
    LINUX = "linux"
    MACOS = "darwin"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class PlatformDetector:
    """Handles platform detection and OS-specific operations."""

    def __init__(self):
        self._os_type = self._detect_os()
        self._home_dir = Path.home()
        self._config_paths = self._get_config_paths()

    @staticmethod
    def _detect_os() -> OSType:
        """Detect the current operating system."""
        system = platform.system().lower()

        if system == "linux":
            return OSType.LINUX
        elif system == "darwin":
            return OSType.MACOS
        elif system == "windows":
            return OSType.WINDOWS
        else:
            return OSType.UNKNOWN

    @property
    def os_type(self) -> OSType:
        """Get the detected OS type."""
        return self._os_type

    @property
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self._os_type == OSType.LINUX

    @property
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self._os_type == OSType.MACOS

    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self._os_type == OSType.WINDOWS

    @property
    def home_dir(self) -> Path:
        """Get the user's home directory."""
        return self._home_dir

    def _get_config_paths(self) -> Dict[str, Path]:
        """Get OS-specific configuration directory paths."""
        paths = {}

        if self.is_linux:
            paths.update({
                'config': Path.home() / '.config',
                'local_share': Path.home() / '.local' / 'share',
                'cache': Path.home() / '.cache',
                'bin': Path.home() / '.local' / 'bin',
                'fonts': Path.home() / '.local' / 'share' / 'fonts',
            })
        elif self.is_macos:
            paths.update({
                'config': Path.home() / '.config',  # Many tools use this on macOS too
                'macos_config': Path.home() / 'Library' / 'Application Support',
                'preferences': Path.home() / 'Library' / 'Preferences',
                'cache': Path.home() / 'Library' / 'Caches',
                'bin': Path('/usr/local/bin'),
                'fonts': Path.home() / 'Library' / 'Fonts',
            })
        elif self.is_windows:
            appdata = os.environ.get('APPDATA', str(Path.home() / 'AppData' / 'Roaming'))
            localappdata = os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))

            paths.update({
                'config': Path(appdata),
                'local_config': Path(localappdata),
                'cache': Path(localappdata) / 'Temp',
                'bin': Path.home() / 'bin',
                'fonts': Path(os.environ.get('WINDIR', 'C:\\Windows')) / 'Fonts',
            })

        return paths

    def get_config_dir(self, name: str = 'config') -> Path:
        """Get a specific configuration directory path."""
        return self._config_paths.get(name, self.home_dir / '.config')

    def get_dotfiles_locations(self) -> Dict[str, List[Path]]:
        """Get common dotfile locations for the current OS."""
        locations = {
            'shell': [],
            'editors': [],
            'terminal': [],
            'git': [],
            'ssh': [],
            'development': [],
            'system': [],
        }

        home = self.home_dir

        if self.is_linux or self.is_macos:
            locations.update({
                'shell': [
                    home / '.bashrc',
                    home / '.bash_profile',
                    home / '.zshrc',
                    home / '.zsh_profile',
                    home / '.profile',
                    home / '.config' / 'fish',
                ],
                'editors': [
                    home / '.vimrc',
                    home / '.config' / 'nvim',
                    home / '.emacs.d',
                    home / '.config' / 'Code' / 'User',
                ],
                'terminal': [
                    home / '.config' / 'alacritty',
                    home / '.config' / 'kitty',
                    home / '.config' / 'terminator',
                    home / '.tmux.conf',
                ],
                'git': [
                    home / '.gitconfig',
                    home / '.gitignore_global',
                    home / '.config' / 'git',
                ],
                'ssh': [
                    home / '.ssh' / 'config',
                ],
                'development': [
                    home / '.config' / 'pip',
                    home / '.npmrc',
                    home / '.yarnrc',
                    home / '.cargo' / 'config.toml',
                ],
            })

            if self.is_macos:
                locations['editors'].extend([
                    home / 'Library' / 'Application Support' / 'Code' / 'User',
                ])
                locations['terminal'].extend([
                    home / 'Library' / 'Preferences' / 'com.apple.Terminal.plist',
                ])

        elif self.is_windows:
            appdata = Path(os.environ.get('APPDATA', str(home / 'AppData' / 'Roaming')))
            localappdata = Path(os.environ.get('LOCALAPPDATA', str(home / 'AppData' / 'Local')))

            locations.update({
                'shell': [
                    home / '.bashrc',
                    home / '.bash_profile',
                    appdata / 'Microsoft' / 'Windows' / 'PowerShell',
                ],
                'editors': [
                    home / '.vimrc',
                    appdata / 'Code' / 'User',
                    localappdata / 'nvim',
                ],
                'terminal': [
                    appdata / 'alacritty',
                    localappdata / 'Microsoft' / 'Windows Terminal',
                ],
                'git': [
                    home / '.gitconfig',
                    home / '.gitignore_global',
                ],
                'ssh': [
                    home / '.ssh' / 'config',
                ],
                'development': [
                    appdata / 'pip',
                    home / '.npmrc',
                    home / '.yarnrc',
                ],
            })

        return locations

    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize a path for the current OS."""
        path = Path(path).expanduser().resolve()

        # Handle Windows path issues
        if self.is_windows:
            # Convert forward slashes to backslashes
            path = Path(str(path).replace('/', os.sep))

        return path

    def get_shell_config_files(self) -> List[Path]:
        """Get shell configuration files for the current OS."""
        shells = []
        home = self.home_dir

        if self.is_linux or self.is_macos:
            shells = [
                home / '.bashrc',
                home / '.bash_profile',
                home / '.zshrc',
                home / '.zsh_profile',
                home / '.profile',
            ]
        elif self.is_windows:
            shells = [
                home / '.bashrc',
                home / '.bash_profile',
            ]

        return [shell for shell in shells if shell.exists()]

    def get_executable_extension(self) -> str:
        """Get the executable file extension for the current OS."""
        return '.exe' if self.is_windows else ''

    def get_script_extension(self) -> str:
        """Get the script file extension for the current OS."""
        return '.bat' if self.is_windows else '.sh'

    def get_path_separator(self) -> str:
        """Get the path separator for the current OS."""
        return os.pathsep

    def can_symlink(self) -> bool:
        """Check if the current OS and user can create symbolic links."""
        if self.is_windows:
            # On Windows, symlinks require special permissions
            try:
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            except:
                return False
        return True

    def create_symlink(self, source: Path, target: Path, force: bool = False) -> bool:
        """Create a symbolic link from source to target."""
        try:
            target = self.normalize_path(target)
            source = self.normalize_path(source)

            # Remove existing target if force is True
            if force and target.exists():
                if target.is_symlink():
                    target.unlink()
                elif target.is_file():
                    target.unlink()
                elif target.is_dir():
                    import shutil
                    shutil.rmtree(target)

            # Create parent directory if it doesn't exist
            target.parent.mkdir(parents=True, exist_ok=True)

            # Create symlink
            if self.is_windows and not self.can_symlink():
                # Fall back to copying on Windows if no admin rights
                import shutil
                if source.is_file():
                    shutil.copy2(source, target)
                else:
                    shutil.copytree(source, target)
                return True
            else:
                target.symlink_to(source)
                return True

        except Exception as e:
            print(f"Failed to create symlink {source} -> {target}: {e}")
            return False

    def get_system_info(self) -> Dict[str, str]:
        """Get detailed system information."""
        return {
            'os_type': self.os_type.value,
            'platform': platform.platform(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'architecture': platform.architecture()[0],
            'python_version': platform.python_version(),
            'home_directory': str(self.home_dir),
            'config_directory': str(self.get_config_dir()),
            'can_symlink': str(self.can_symlink()),
        }


# Global instance for convenience
platform_detector = PlatformDetector()

# Convenience functions
def get_os_type() -> OSType:
    """Get the current OS type."""
    return platform_detector.os_type

def is_linux() -> bool:
    """Check if running on Linux."""
    return platform_detector.is_linux

def is_macos() -> bool:
    """Check if running on macOS."""
    return platform_detector.is_macos

def is_windows() -> bool:
    """Check if running on Windows."""
    return platform_detector.is_windows

def get_home_dir() -> Path:
    """Get the user's home directory."""
    return platform_detector.home_dir

def get_config_dir(name: str = 'config') -> Path:
    """Get a configuration directory path."""
    return platform_detector.get_config_dir(name)
