#!/usr/bin/env python3
"""
Configuration manager for SuperDots.

This module provides functionality to manage configuration files, including
tracking, backup, restoration, and cross-platform handling.
"""

import os
import shutil
import hashlib
import json
from rich.console import Console
import yaml
import toml
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from superdots.utils.path import normalize_path

from ..utils.logger import get_logger
from ..utils.platform import platform_detector, OSType


class ConfigType(Enum):
    """Configuration file types."""
    DOTFILE = "dotfile"
    CONFIG_DIR = "config_dir"
    BINARY = "binary"
    SCRIPT = "script"
    TEMPLATE = "template"


class ConfigStatus(Enum):
    """Configuration status."""
    TRACKED = "tracked"
    MODIFIED = "modified"
    MISSING = "missing"
    CONFLICTED = "conflicted"
    UNTRACKED = "untracked"


@dataclass
class ConfigFile:
    """Represents a configuration file or directory."""

    # Basic information
    name: str
    source_paths: Dict[OSType, Path]  # Multiple OS-specific paths
    repo_path: Path
    config_type: ConfigType

    # Platform information
    platforms: List[OSType]
    current_platform: OSType

    # Status information
    status: ConfigStatus
    checksum: Optional[str] = None
    backup_path: Optional[Path] = None

    # Metadata
    description: Optional[str] = None
    tags: List[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Installation options
    use_symlink: bool = True
    executable: bool = False
    template_vars: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Post-initialization processing."""
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert Path objects to strings
        data['source_paths'] = {os_type.value: str(path) for os_type, path in self.source_paths.items()}
        data['repo_path'] = str(self.repo_path)
        if self.backup_path:
            data['backup_path'] = str(self.backup_path)

        # Convert enums to values
        data['config_type'] = self.config_type.value
        data['status'] = self.status.value
        data['current_platform'] = self.current_platform.value
        data['platforms'] = [p.value for p in self.platforms]

        # Convert datetime to ISO string
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigFile':
        """Create instance from dictionary."""
        # Convert strings back to Path objects
        data['source_paths'] = {OSType(os_type): Path(path) for os_type, path in data['source_paths'].items()}
        data['repo_path'] = Path(data['repo_path'])
        if data.get('backup_path'):
            data['backup_path'] = Path(data['backup_path'])

        # Convert values back to enums
        data['config_type'] = ConfigType(data['config_type'])
        data['status'] = ConfigStatus(data['status'])
        data['current_platform'] = OSType(data['current_platform'])
        data['platforms'] = [OSType(p) for p in data['platforms']]

        # Convert ISO strings back to datetime
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        return cls(**data)

    def get_source_path(self, platform: Optional[OSType] = None) -> Optional[Path]:
        """Get source path for the specified platform."""
        if platform is None:
            platform = self.current_platform
        return self.source_paths.get(platform)

    def add_source_path(self, platform: OSType, path: Path):
        """Add or update source path for a platform."""
        self.source_paths[platform] = path
        if platform not in self.platforms:
            self.platforms.append(platform)

    def remove_source_path(self, platform: OSType):
        """Remove source path for a platform."""
        if platform in self.source_paths:
            del self.source_paths[platform]
        if platform in self.platforms:
            self.platforms.remove(platform)

    def has_source_for_platform(self, platform: OSType) -> bool:
        """Check if configuration has a source path for the specified platform."""
        return platform in self.source_paths and self.source_paths[platform].exists()

    def get_supported_platforms(self) -> List[OSType]:
        """Get list of platforms that have defined source paths."""
        return list(self.source_paths.keys())

    def get_existing_platforms(self) -> List[OSType]:
        """Get list of platforms that have existing source paths."""
        return [platform for platform, path in self.source_paths.items() if path.exists()]


class ConfigManager:
    """Main configuration manager class."""

    def __init__(self, repo_path: Union[str, Path]):
        """
        Initialize configuration manager.

        Args:
            repo_path: Path to the SuperDots repository
        """
        self.logger = get_logger(f"{__name__}.ConfigManager")
        self.repo_path = Path(repo_path).resolve()
        self.configs_dir = self.repo_path / 'configs'
        self.backups_dir = self.repo_path / 'backups'
        self.templates_dir = self.repo_path / 'templates'

        # Configuration tracking
        self.config_index_file = self.repo_path / '.superdots' / 'config_index.json'
        self._configs: Dict[str, ConfigFile] = {}

        # Platform detection
        self.current_platform = platform_detector.os_type

        # Ensure directories exist
        self._setup_directories()

        # Load existing configurations
        self._load_config_index()

    def _setup_directories(self):
        """Setup required directories."""
        directories = [
            self.configs_dir,
            self.backups_dir,
            self.templates_dir,
            self.config_index_file.parent,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        # Create platform-specific subdirectories
        # for platform in OSType:
        #     if platform != OSType.UNKNOWN:
        #         platform_dir = self.configs_dir / platform.value
        #         platform_dir.mkdir(exist_ok=True)

    def _load_config_index(self):
        """Load configuration index from file."""
        if not self.config_index_file.exists():
            self._save_config_index()
            return

        try:
            with open(self.config_index_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._configs = {}
            for name, config_data in data.get('configs', {}).items():
                try:
                    self._configs[name] = ConfigFile.from_dict(config_data)
                except Exception as e:
                    self.logger.warning(f"Failed to load config '{name}': {e}")

            self.logger.debug(f"Loaded {len(self._configs)} configurations from index")

        except Exception as e:
            self.logger.error(f"Failed to load config index: {e}")
            self._configs = {}

    def _save_config_index(self):
        """Save configuration index to file."""
        try:
            data = {
                'version': '1.0',
                'platform': self.current_platform.value,
                'updated_at': datetime.now().isoformat(),
                'configs': {name: config.to_dict() for name, config in self._configs.items()}
            }

            with open(self.config_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.logger.debug("Saved configuration index")

        except Exception as e:
            self.logger.error(f"Failed to save config index: {e}")

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file."""
        if not file_path.exists():
            return ""

        hash_md5 = hashlib.md5()

        if file_path.is_file():
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
        elif file_path.is_dir():
            # For directories, hash the structure and file checksums
            for root, dirs, files in os.walk(file_path):
                # Sort to ensure consistent ordering
                dirs.sort()
                files.sort()

                for name in files:
                    file_path_obj = Path(root) / name
                    rel_path = file_path_obj.relative_to(file_path)
                    hash_md5.update(str(rel_path).encode())

                    if file_path_obj.is_file():
                        with open(file_path_obj, 'rb') as f:
                            for chunk in iter(lambda: f.read(4096), b""):
                                hash_md5.update(chunk)

        return hash_md5.hexdigest()

    def _detect_config_type(self, path: Path) -> ConfigType:
        """Detect the type of configuration based on path and content."""
        if path.is_dir():
            return ConfigType.CONFIG_DIR

        if not path.is_file():
            return ConfigType.DOTFILE

        # Check if it's a script
        if path.suffix in ['.sh', '.bat', '.ps1', '.py', '.rb', '.pl']:
            return ConfigType.SCRIPT

        # Check if it's executable
        if os.access(path, os.X_OK):
            return ConfigType.BINARY

        # Check for template patterns
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            if '{{' in content and '}}' in content:
                return ConfigType.TEMPLATE
        except:
            pass

        return ConfigType.DOTFILE

    def _get_repo_path_for_config(self, name: str, config_type: ConfigType, platforms: List[OSType]) -> Path:
        """Generate repository path for a configuration."""
        # Use a common location for multi-platform configs
        common_dir = self.configs_dir / ('common' if len(platforms) > 1 else platforms[0].value)
        

        # Create a safe filename based on the config name
        safe_name = name.replace('/', '_').replace('\\', '_')

        # Organize by config type
        if config_type == ConfigType.CONFIG_DIR:
            repo_path = common_dir / 'directories' / safe_name
        elif config_type == ConfigType.SCRIPT:
            repo_path = common_dir / 'scripts' / safe_name
        elif config_type == ConfigType.BINARY:
            repo_path = common_dir / 'binaries' / safe_name
        elif config_type == ConfigType.TEMPLATE:
            repo_path = common_dir / 'templates' / safe_name
        else:
            repo_path = common_dir / 'dotfiles' / safe_name

        return repo_path

    def add_config(
        self,
        source_paths: Dict[OSType, Path],
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        use_symlink: bool = True,
        force: bool = False
    ) -> bool:
        """
        Add a configuration file or directory to management.

        Args:
            source_paths: Path(s) to the configuration file/directory. Can be:
                         - Dict[OSType, Path]: platform-specific paths
            name: Optional custom name for the configuration
            description: Optional description
            tags: Optional tags for categorization
            platforms: Target platforms (auto-detected from source_paths if not provided)
            use_symlink: Whether to use symlinks for deployment
            force: Whether to overwrite existing configurations

        Returns:
            True if successful, False otherwise
        """
        self.logger.debug("Here")
        try:
            # Dictionary of platform-specific paths
            # Validate that at least one path exists
            existing_paths = {os_type: path for os_type, path in source_paths.items() if path.exists()}
            if not existing_paths:
                self.logger.error("No source paths exist")
                return False

            # Generate name from first path if not provided
            if not name:
                name = source_paths[self.current_platform].name

            # Check if already managed
            if name in self._configs and not force:
                self.logger.error(f"Configuration '{name}' already exists. Use --force to overwrite.")
                return False

            # Detect configuration type from first existing path
            first_existing_path = next(iter(existing_paths.values()))
            config_type = self._detect_config_type(first_existing_path)

            # Set platforms
            platforms = list(source_paths.keys())

            # Generate repository path
            self.logger.debug(f"{source_paths}")
            repo_path = self._get_repo_path_for_config(name, config_type, platforms)
            
            source_paths_norm = {key: normalize_path(value, platform_detector.home_dir, False) for key, value in source_paths.items()}
            # Create configuration object
            config = ConfigFile(
                name=name,
                source_paths=source_paths_norm,
                repo_path=repo_path,
                config_type=config_type,
                platforms=platforms,
                current_platform=self.current_platform,
                status=ConfigStatus.UNTRACKED,
                description=description,
                tags=tags or [],
                use_symlink=use_symlink,
                executable=os.access(first_existing_path, os.X_OK) if first_existing_path.is_file() else False
            )

            # Create backup of current platform's file
            current_path = source_paths.get(self.current_platform)
            if current_path and current_path.exists():
                backup_path = self._create_backup(current_path, name)
                if backup_path:
                    config.backup_path = normalize_path(backup_path, platform_detector.home_dir, False)

            # Copy to repository (use current platform's file if available, otherwise first existing)
            source_for_repo = current_path if current_path and current_path.exists() else first_existing_path
            if self._copy_to_repo(source_for_repo, repo_path):
                config.checksum = self._calculate_checksum(repo_path)
                config.status = ConfigStatus.TRACKED

                # Add to tracking
                self._configs[name] = config
                self._save_config_index()

                self.logger.info(f"Added configuration '{name}' ({config_type.value})")
                return True
            else:
                self.logger.error(f"Failed to copy configuration to repository")
                return False

        except Exception as e:
            self.logger.error(f"Failed to add configuration: {e}")
            return False

    def remove_config(self, name: str, keep_files: bool = False) -> bool:
        """
        Remove a configuration from management.

        Args:
            name: Name of the configuration to remove
            keep_files: Whether to keep the files in the repository

        Returns:
            True if successful, False otherwise
        """
        try:
            if name not in self._configs:
                self.logger.error(f"Configuration '{name}' not found")
                return False

            config = self._configs[name]

            # Remove from repository if requested
            if not keep_files and config.repo_path.exists():
                if config.repo_path.is_file():
                    config.repo_path.unlink()
                else:
                    shutil.rmtree(config.repo_path)

            # Remove from tracking
            del self._configs[name]
            self._save_config_index()

            self.logger.info(f"Removed configuration '{name}'")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove configuration '{name}': {e}")
            return False

    def _create_backup(self, source_path: Path, name: str) -> Optional[Path]:
        """Create a backup of the source file/directory."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{name}_{timestamp}"
            backup_path = self.backups_dir / backup_name

            if source_path.is_file():
                shutil.copy2(source_path, backup_path)
            elif source_path.is_dir():
                shutil.copytree(source_path, backup_path)

            self.logger.debug(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            self.logger.warning(f"Failed to create backup for {source_path}: {e}")
            return None

    def _copy_to_repo(self, source_path: Path, repo_path: Path) -> bool:
        """Copy source to repository path."""
        try:
            repo_path.parent.mkdir(parents=True, exist_ok=True)

            if repo_path.exists():
                if repo_path.is_file():
                    repo_path.unlink()
                else:
                    shutil.rmtree(repo_path)

            if source_path.is_file():
                shutil.copy2(source_path, repo_path)
            elif source_path.is_dir():
                shutil.copytree(source_path, repo_path)

            return True

        except Exception as e:
            self.logger.error(f"Failed to copy {source_path} to {repo_path}: {e}")
            return False

    def deploy_config(self, name: str, force: bool = False) -> bool:
        """
        Deploy a configuration to its target location.

        Args:
            name: Name of the configuration to deploy
            force: Whether to overwrite existing files

        Returns:
            True if successful, False otherwise
        """
        try:
            if name not in self._configs:
                self.logger.error(f"Configuration '{name}' not found")
                return False

            config = self._configs[name]

            # Check if current platform is supported
            if self.current_platform not in config.platforms:
                self.logger.warning(
                    f"Configuration '{name}' is not supported on {self.current_platform.value}"
                )
                return False

            # Get source path for current platform
            source_path = config.get_source_path(self.current_platform)
            if not source_path:
                self.logger.error(f"No source path defined for {self.current_platform.value}")
                return False

            # Check if source exists
            if source_path.exists() and not force:
                self.logger.warning(
                    f"Target already exists: {source_path}. Use --force to overwrite."
                )
                return False

            # Create parent directory
            source_path.parent.mkdir(parents=True, exist_ok=True)

            # Deploy based on configuration
            success = False
            if config.use_symlink and platform_detector.can_symlink():
                success = platform_detector.create_symlink(
                    config.repo_path, source_path, force=force
                )
            else:
                # Copy files
                if config.repo_path.is_file():
                    shutil.copy2(config.repo_path, source_path)
                    success = True
                elif config.repo_path.is_dir():
                    if source_path.exists():
                        shutil.rmtree(source_path)
                    shutil.copytree(config.repo_path, source_path)
                    success = True

            # Set executable permission if needed
            if success and config.executable and source_path.is_file():
                os.chmod(source_path, 0o755)

            if success:
                config.status = ConfigStatus.TRACKED
                config.updated_at = datetime.now()
                self._save_config_index()
                self.logger.info(f"Deployed configuration '{name}'")

            return success

        except Exception as e:
            self.logger.error(f"Failed to deploy configuration '{name}': {e}")
            return False

    def deploy_all(self, platform: Optional[OSType] = None, force: bool = False) -> int:
        """
        Deploy all configurations for the specified platform.

        Args:
            platform: Target platform (defaults to current platform)
            force: Whether to overwrite existing files

        Returns:
            Number of successfully deployed configurations
        """
        if platform is None:
            platform = self.current_platform

        deployed = 0
        for name, config in self._configs.items():
            if platform in config.platforms:
                if self.deploy_config(name, force=force):
                    deployed += 1

        self.logger.info(f"Deployed {deployed}/{len(self._configs)} configurations")
        return deployed

    def update_config(self, name: str) -> bool:
        """
        Update a configuration from its source location.

        Args:
            name: Name of the configuration to update

        Returns:
            True if successful, False otherwise
        """
        try:
            if name not in self._configs:
                self.logger.error(f"Configuration '{name}' not found")
                return False

            config = self._configs[name]

            # Get source path for current platform
            source_path = config.get_source_path(self.current_platform)
            if not source_path:
                self.logger.error(f"No source path defined for {self.current_platform.value}")
                return False

            if not source_path.exists():
                self.logger.error(f"Source path does not exist: {source_path}")
                config.status = ConfigStatus.MISSING
                self._save_config_index()
                return False

            # Check if file has changed
            current_checksum = self._calculate_checksum(source_path)
            if current_checksum == config.checksum:
                self.logger.debug(f"Configuration '{name}' is up to date")
                return True

            # Create backup of current repo version
            if config.repo_path.exists():
                backup_path = self._create_backup(config.repo_path, f"{name}_repo")

            # Copy updated version to repository
            if self._copy_to_repo(source_path, config.repo_path):
                config.checksum = current_checksum
                config.status = ConfigStatus.TRACKED
                config.updated_at = datetime.now()
                self._save_config_index()

                self.logger.info(f"Updated configuration '{name}'")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to update configuration '{name}': {e}")
            return False

    def list_configs(
        self,
        platform: Optional[OSType] = None,
        tags: Optional[List[str]] = None,
        status: Optional[ConfigStatus] = None
    ) -> List[ConfigFile]:
        """
        List configurations with optional filtering.

        Args:
            platform: Filter by platform
            tags: Filter by tags (any match)
            status: Filter by status

        Returns:
            List of matching configurations
        """
        configs = list(self._configs.values())

        # Filter by platform
        if platform:
            configs = [c for c in configs if platform in c.platforms]

        # Filter by tags
        if tags:
            configs = [c for c in configs if any(tag in c.tags for tag in tags)]

        # Filter by status
        if status:
            configs = [c for c in configs if c.status == status]

        return sorted(configs, key=lambda c: c.name)

    def get_config(self, name: str) -> Optional[ConfigFile]:
        """Get a configuration by name."""
        return self._configs.get(name)

    def check_status(self) -> Dict[str, List[str]]:
        """
        Check the status of all configurations.

        Returns:
            Dictionary with status categories and configuration names
        """
        status_map = {
            'tracked': [],
            'modified': [],
            'missing': [],
            'conflicted': [],
            'untracked': [],
        }

        for name, config in self._configs.items():
            # Get source path for current platform
            source_path = config.get_source_path(self.current_platform)

            # Check if source exists for current platform
            if not source_path or not source_path.exists():
                # Check if any platform has an existing source
                has_existing_source = any(path.exists() for path in config.source_paths.values())
                if has_existing_source:
                    # Has sources on other platforms but not current
                    config.status = ConfigStatus.TRACKED
                    status_map['tracked'].append(name)
                else:
                    # No sources exist anywhere
                    config.status = ConfigStatus.MISSING
                    status_map['missing'].append(name)
                continue

            # Check if repo version exists
            if not config.repo_path.exists():
                config.status = ConfigStatus.UNTRACKED
                status_map['untracked'].append(name)
                continue

            # Check for modifications
            source_checksum = self._calculate_checksum(source_path)
            repo_checksum = self._calculate_checksum(config.repo_path)

            if source_checksum != repo_checksum:
                config.status = ConfigStatus.MODIFIED
                status_map['modified'].append(name)
            else:
                config.status = ConfigStatus.TRACKED
                status_map['tracked'].append(name)

        self._save_config_index()
        return status_map

    def restore_config(self, name: str, from_backup: bool = False) -> bool:
        """
        Restore a configuration from repository or backup.

        Args:
            name: Name of the configuration to restore
            from_backup: Whether to restore from backup instead of repository

        Returns:
            True if successful, False otherwise
        """
        try:
            if name not in self._configs:
                self.logger.error(f"Configuration '{name}' not found")
                return False

            config = self._configs[name]

            # Get source path for current platform
            source_path = config.get_source_path(self.current_platform)
            if not source_path:
                self.logger.error(f"No source path defined for {self.current_platform.value}")
                return False

            if from_backup:
                if not config.backup_path or not config.backup_path.exists():
                    self.logger.error(f"No backup available for '{name}'")
                    return False
                source = config.backup_path
            else:
                if not config.repo_path.exists():
                    self.logger.error(f"Repository version not found for '{name}'")
                    return False
                source = config.repo_path

            # Create parent directory
            source_path.parent.mkdir(parents=True, exist_ok=True)

            # Restore file/directory
            if source_path.exists():
                if source_path.is_file():
                    source_path.unlink()
                else:
                    shutil.rmtree(source_path)

            if source.is_file():
                shutil.copy2(source, source_path)
            else:
                shutil.copytree(source, source_path)

            # Set permissions
            if config.executable and source_path.is_file():
                os.chmod(source_path, 0o755)

            config.status = ConfigStatus.TRACKED
            config.updated_at = datetime.now()
            self._save_config_index()

            self.logger.info(f"Restored configuration '{name}' from {'backup' if from_backup else 'repository'}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to restore configuration '{name}': {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about managed configurations."""
        stats = {
            'total_configs': len(self._configs),
            'by_type': {},
            'by_platform': {},
            'by_status': {},
            'last_updated': None,
        }

        for config in self._configs.values():
            # Count by type
            type_name = config.config_type.value
            stats['by_type'][type_name] = stats['by_type'].get(type_name, 0) + 1

            # Count by platform
            for platform in config.platforms:
                platform_name = platform.value
                stats['by_platform'][platform_name] = stats['by_platform'].get(platform_name, 0) + 1

            # Count by status
            status_name = config.status.value
            stats['by_status'][status_name] = stats['by_status'].get(status_name, 0) + 1

            # Track latest update
            if config.updated_at:
                if not stats['last_updated'] or config.updated_at > stats['last_updated']:
                    stats['last_updated'] = config.updated_at

        return stats

    def add_platform_path(
        self,
        name: str,
        platform: OSType,
        source_path: Union[str, Path],
        force: bool = False
    ) -> bool:
        """
        Add a source path for a specific platform to an existing configuration.

        Args:
            name: Name of the configuration
            platform: Target platform
            source_path: Path to the configuration file/directory for this platform
            force: Whether to overwrite existing platform path

        Returns:
            True if successful, False otherwise
        """
        try:
            if name not in self._configs:
                self.logger.error(f"Configuration '{name}' not found")
                return False

            config = self._configs[name]
            path = Path(source_path).expanduser().resolve()

            # Check if platform already has a path
            if platform in config.source_paths and not force:
                self.logger.error(f"Platform {platform.value} already has a path for '{name}'. Use --force to overwrite.")
                return False

            # Validate path exists
            if not path.exists():
                self.logger.error(f"Source path does not exist: {path}")
                return False

            # Add the path
            config.add_source_path(platform, path)
            config.updated_at = datetime.now()
            self._save_config_index()

            self.logger.info(f"Added {platform.value} path for configuration '{name}': {path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add platform path: {e}")
            return False

    def remove_platform_path(self, name: str, platform: OSType) -> bool:
        """
        Remove a source path for a specific platform from a configuration.

        Args:
            name: Name of the configuration
            platform: Platform to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            if name not in self._configs:
                self.logger.error(f"Configuration '{name}' not found")
                return False

            config = self._configs[name]

            if platform not in config.source_paths:
                self.logger.error(f"Configuration '{name}' has no path for {platform.value}")
                return False

            # Remove the path
            config.remove_source_path(platform)
            config.updated_at = datetime.now()
            self._save_config_index()

            self.logger.info(f"Removed {platform.value} path for configuration '{name}'")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove platform path: {e}")
            return False

    def list_platform_paths(self, name: str) -> Dict[OSType, Tuple[Path, bool]]:
        """
        List all platform paths for a configuration.

        Args:
            name: Name of the configuration

        Returns:
            Dictionary mapping platform to (path, exists) tuple
        """
        if name not in self._configs:
            return {}

        config = self._configs[name]
        return {
            platform: (path, path.exists())
            for platform, path in config.source_paths.items()
        }
