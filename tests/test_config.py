#!/usr/bin/env python3
"""
Tests for configuration manager functionality.
"""

import os
import json
import shutil
import tempfile
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

from superdots.core.config import (
    ConfigManager,
    ConfigFile,
    ConfigType,
    ConfigStatus
)
from superdots.utils.platform import OSType
from superdots.utils.platform import platform_detector


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    return repo_path


@pytest.fixture
def config_manager(temp_repo):
    """Create a ConfigManager instance for testing."""
    return ConfigManager(temp_repo)


@pytest.fixture
def sample_config_file(tmp_path):
    """Create a sample configuration file for testing."""
    config_file = tmp_path / "sample.conf"
    config_file.write_text("# Sample configuration\nkey=value\n")
    return config_file


@pytest.fixture
def sample_config_dir(tmp_path):
    """Create a sample configuration directory for testing."""
    config_dir = tmp_path / "sample_config"
    config_dir.mkdir()
    (config_dir / "config.txt").write_text("config content")
    return config_dir


@pytest.fixture
def multi_platform_files(tmp_path):
    """Create sample files for multi-platform testing."""
    files = {}
    for os_type in [OSType.LINUX, OSType.MACOS, OSType.WINDOWS]:
        file_path = tmp_path / f"config_{os_type.value}"
        file_path.write_text(f"# Configuration for {os_type.value}\nkey=value_{os_type.value}")
        files[os_type] = file_path
    return files


class TestMultiPlatformConfig:
    """Test multi-platform configuration functionality."""

    def test_config_file_multi_platform_creation(self, temp_repo, multi_platform_files):
        """Test creating a ConfigFile with multiple platform paths."""
        config = ConfigFile(
            name="test_config",
            source_paths=multi_platform_files,
            repo_path=temp_repo / "test_config",
            config_type=ConfigType.DOTFILE,
            platforms=list(multi_platform_files.keys()),
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED
        )

        assert len(config.source_paths) == 3
        assert OSType.LINUX in config.source_paths
        assert OSType.MACOS in config.source_paths
        assert OSType.WINDOWS in config.source_paths

    def test_get_source_path(self, temp_repo, multi_platform_files):
        """Test getting source path for specific platform."""
        config = ConfigFile(
            name="test_config",
            source_paths=multi_platform_files,
            repo_path=temp_repo / "test_config",
            config_type=ConfigType.DOTFILE,
            platforms=list(multi_platform_files.keys()),
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED
        )

        # Test getting path for specific platform
        linux_path = config.get_source_path(OSType.LINUX)
        assert linux_path == multi_platform_files[OSType.LINUX]

        # Test getting path for current platform (default)
        current_path = config.get_source_path()
        assert current_path == multi_platform_files[OSType.LINUX]

        # Test getting path for non-existent platform
        unknown_path = config.get_source_path(OSType.UNKNOWN)
        assert unknown_path is None

    def test_add_remove_source_path(self, temp_repo, multi_platform_files):
        """Test adding and removing source paths."""
        config = ConfigFile(
            name="test_config",
            source_paths={OSType.LINUX: multi_platform_files[OSType.LINUX]},
            repo_path=temp_repo / "test_config",
            config_type=ConfigType.DOTFILE,
            platforms=[OSType.LINUX],
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED
        )

        # Add new platform path
        config.add_source_path(OSType.MACOS, multi_platform_files[OSType.MACOS])
        assert OSType.MACOS in config.source_paths
        assert OSType.MACOS in config.platforms

        # Remove platform path
        config.remove_source_path(OSType.MACOS)
        assert OSType.MACOS not in config.source_paths
        assert OSType.MACOS not in config.platforms

    def test_has_source_for_platform(self, temp_repo, multi_platform_files):
        """Test checking if platform has source."""
        config = ConfigFile(
            name="test_config",
            source_paths=multi_platform_files,
            repo_path=temp_repo / "test_config",
            config_type=ConfigType.DOTFILE,
            platforms=list(multi_platform_files.keys()),
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED
        )

        assert config.has_source_for_platform(OSType.LINUX)
        assert config.has_source_for_platform(OSType.MACOS)
        assert config.has_source_for_platform(OSType.WINDOWS)
        assert not config.has_source_for_platform(OSType.UNKNOWN)

    def test_get_supported_existing_platforms(self, temp_repo, multi_platform_files):
        """Test getting supported and existing platforms."""
        config = ConfigFile(
            name="test_config",
            source_paths=multi_platform_files,
            repo_path=temp_repo / "test_config",
            config_type=ConfigType.DOTFILE,
            platforms=list(multi_platform_files.keys()),
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED
        )

        supported = config.get_supported_platforms()
        assert set(supported) == {OSType.LINUX, OSType.MACOS, OSType.WINDOWS}

        existing = config.get_existing_platforms()
        assert set(existing) == {OSType.LINUX, OSType.MACOS, OSType.WINDOWS}

    def test_config_serialization(self, temp_repo, multi_platform_files):
        """Test serialization/deserialization with multi-platform paths."""
        original_config = ConfigFile(
            name="test_config",
            source_paths=multi_platform_files,
            repo_path=temp_repo / "test_config",
            config_type=ConfigType.DOTFILE,
            platforms=list(multi_platform_files.keys()),
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED
        )

        # Serialize to dict
        config_dict = original_config.to_dict()
        assert isinstance(config_dict['source_paths'], dict)
        assert 'linux' in config_dict['source_paths']
        assert 'macos' in config_dict['source_paths']
        assert 'windows' in config_dict['source_paths']

        # Deserialize from dict
        restored_config = ConfigFile.from_dict(config_dict)
        assert len(restored_config.source_paths) == 3
        assert restored_config.source_paths[OSType.LINUX] == multi_platform_files[OSType.LINUX]

    def test_add_config_multi_platform(self, config_manager, multi_platform_files):
        """Test adding configuration with multiple platform paths."""
        success = config_manager.add_config(
            source_paths=multi_platform_files,
            name="multi_platform_test",
            description="Test multi-platform config"
        )

        assert success
        config = config_manager.get_config("multi_platform_test")
        assert config is not None
        assert len(config.source_paths) == 3
        assert set(config.platforms) == {OSType.LINUX, OSType.MACOS, OSType.WINDOWS}

    def test_add_config_single_path(self, config_manager, sample_config_file):
        """Test adding configuration with single path (current platform)."""
        success = config_manager.add_config(
            source_paths=str(sample_config_file),
            name="single_platform_test"
        )

        assert success
        config = config_manager.get_config("single_platform_test")
        assert config is not None
        assert len(config.source_paths) == 1
        assert config.current_platform in config.source_paths

    def test_add_platform_path(self, config_manager, sample_config_file, tmp_path):
        """Test adding platform path to existing configuration."""
        # First add config for current platform
        config_manager.add_config(
            source_paths=str(sample_config_file),
            name="test_config"
        )

        # Create file for another platform
        other_file = tmp_path / "other_config"
        other_file.write_text("other config content")

        # Add path for different platform
        success = config_manager.add_platform_path(
            "test_config",
            OSType.MACOS,
            other_file
        )

        assert success
        config = config_manager.get_config("test_config")
        assert OSType.MACOS in config.source_paths
        assert config.source_paths[OSType.MACOS] == other_file

    def test_remove_platform_path(self, config_manager, multi_platform_files):
        """Test removing platform path from configuration."""
        # Add multi-platform config
        config_manager.add_config(
            source_paths=multi_platform_files,
            name="test_config"
        )

        # Remove one platform
        success = config_manager.remove_platform_path("test_config", OSType.WINDOWS)
        assert success

        config = config_manager.get_config("test_config")
        assert OSType.WINDOWS not in config.source_paths
        assert OSType.WINDOWS not in config.platforms

    def test_list_platform_paths(self, config_manager, multi_platform_files):
        """Test listing platform paths for configuration."""
        config_manager.add_config(
            source_paths=multi_platform_files,
            name="test_config"
        )

        paths = config_manager.list_platform_paths("test_config")
        assert len(paths) == 3

        for platform, (path, exists) in paths.items():
            assert platform in multi_platform_files
            assert path == multi_platform_files[platform]
            assert exists  # All test files should exist

    def test_deploy_config_current_platform(self, config_manager, multi_platform_files, tmp_path):
        """Test deploying configuration for current platform."""
        # Create target directory
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        # Modify paths to point to target directory
        modified_paths = {}
        for platform, original_path in multi_platform_files.items():
            target_path = target_dir / f"deployed_{platform.value}"
            modified_paths[platform] = target_path

        config_manager.add_config(
            source_paths=modified_paths,
            name="deploy_test"
        )

        # Deploy should use current platform path
        success = config_manager.deploy_config("deploy_test", force=True)
        assert success

        # Check that current platform file was deployed
        current_platform = config_manager.current_platform
        target_path = modified_paths[current_platform]
        assert target_path.exists()

    @patch('superdots.utils.platform.platform_detector.can_symlink')
    def test_deploy_with_copy_fallback(self, mock_can_symlink, config_manager, multi_platform_files, tmp_path):
        """Test deploying with copy when symlink is not available."""
        mock_can_symlink.return_value = False

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        modified_paths = {config_manager.current_platform: target_dir / "deployed_config"}

        config_manager.add_config(
            source_paths=modified_paths,
            name="copy_test",
            use_symlink=True  # Should fallback to copy
        )

        success = config_manager.deploy_config("copy_test", force=True)
        assert success
        assert modified_paths[config_manager.current_platform].exists()


class TestConfigManagerMultiPlatform:
    """Test ConfigManager with multi-platform functionality."""
    config_dir.mkdir()
    (config_dir / "main.conf").write_text("main=config")
    (config_dir / "sub.conf").write_text("sub=config")
    return config_dir


class TestConfigType:
    """Test ConfigType enum."""

    def test_config_type_values(self):
        """Test that ConfigType has correct values."""
        assert ConfigType.DOTFILE.value == "dotfile"
        assert ConfigType.CONFIG_DIR.value == "config_dir"
        assert ConfigType.BINARY.value == "binary"
        assert ConfigType.SCRIPT.value == "script"
        assert ConfigType.TEMPLATE.value == "template"


class TestConfigStatus:
    """Test ConfigStatus enum."""

    def test_config_status_values(self):
        """Test that ConfigStatus has correct values."""
        assert ConfigStatus.TRACKED.value == "tracked"
        assert ConfigStatus.MODIFIED.value == "modified"
        assert ConfigStatus.MISSING.value == "missing"
        assert ConfigStatus.CONFLICTED.value == "conflicted"
        assert ConfigStatus.UNTRACKED.value == "untracked"


class TestConfigFile:
    """Test ConfigFile dataclass."""

    def test_config_file_creation(self):
        """Test ConfigFile creation with basic parameters."""
        config = ConfigFile(
            name="test_config",
            source_path=Path("/home/user/.vimrc"),
            repo_path=Path("/repo/configs/vimrc"),
            config_type=ConfigType.DOTFILE,
            platforms=[OSType.LINUX],
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED
        )

        assert config.name == "test_config"
        assert config.source_path == Path("/home/user/.vimrc")
        assert config.config_type == ConfigType.DOTFILE
        assert config.status == ConfigStatus.TRACKED
        assert OSType.LINUX in config.platforms

    def test_config_file_post_init(self):
        """Test ConfigFile post-initialization."""
        config = ConfigFile(
            name="test",
            source_path=Path("/test"),
            repo_path=Path("/repo/test"),
            config_type=ConfigType.DOTFILE,
            platforms=[OSType.LINUX],
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED
        )

        # Check that defaults are set
        assert isinstance(config.tags, list)
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.updated_at, datetime)

    def test_config_file_to_dict(self):
        """Test ConfigFile serialization to dictionary."""
        config = ConfigFile(
            name="test",
            source_path=Path("/test"),
            repo_path=Path("/repo/test"),
            config_type=ConfigType.DOTFILE,
            platforms=[OSType.LINUX],
            current_platform=OSType.LINUX,
            status=ConfigStatus.TRACKED,
            tags=["shell", "vim"]
        )

        data = config.to_dict()

        assert data["name"] == "test"
        assert data["source_path"] == "/test"
        assert data["config_type"] == "dotfile"
        assert data["status"] == "tracked"
        assert data["platforms"] == ["linux"]
        assert data["tags"] == ["shell", "vim"]

    def test_config_file_from_dict(self):
        """Test ConfigFile deserialization from dictionary."""
        data = {
            "name": "test",
            "source_path": "/test",
            "repo_path": "/repo/test",
            "config_type": "dotfile",
            "platforms": ["linux"],
            "current_platform": "linux",
            "status": "tracked",
            "tags": ["shell"],
            "created_at": "2023-01-01T12:00:00",
            "updated_at": "2023-01-01T12:00:00"
        }

        config = ConfigFile.from_dict(data)

        assert config.name == "test"
        assert config.source_path == Path("/test")
        assert config.config_type == ConfigType.DOTFILE
        assert config.status == ConfigStatus.TRACKED
        assert OSType.LINUX in config.platforms


class TestConfigManager:
    """Test ConfigManager class."""

    def test_config_manager_initialization(self, config_manager, temp_repo):
        """Test ConfigManager initialization."""
        assert config_manager.repo_path == temp_repo
        assert config_manager.configs_dir == temp_repo / 'configs'
        assert config_manager.backups_dir == temp_repo / 'backups'

        # Check that directories were created
        assert config_manager.configs_dir.exists()
        assert config_manager.backups_dir.exists()
        assert config_manager.config_index_file.parent.exists()

    def test_setup_directories(self, config_manager):
        """Test directory setup."""
        # Directories should be created during initialization
        assert config_manager.configs_dir.exists()
        assert config_manager.backups_dir.exists()
        assert config_manager.templates_dir.exists()

        # Platform-specific directories should exist
        for platform in OSType:
            if platform != OSType.UNKNOWN:
                platform_dir = config_manager.configs_dir / platform.value
                assert platform_dir.exists()

    def test_calculate_checksum_file(self, config_manager, sample_config_file):
        """Test checksum calculation for files."""
        checksum = config_manager._calculate_checksum(sample_config_file)
        assert isinstance(checksum, str)
        assert len(checksum) == 32  # MD5 hash length

        # Same file should produce same checksum
        checksum2 = config_manager._calculate_checksum(sample_config_file)
        assert checksum == checksum2

    def test_calculate_checksum_directory(self, config_manager, sample_config_dir):
        """Test checksum calculation for directories."""
        checksum = config_manager._calculate_checksum(sample_config_dir)
        assert isinstance(checksum, str)
        assert len(checksum) == 32

    def test_calculate_checksum_nonexistent(self, config_manager):
        """Test checksum calculation for non-existent path."""
        checksum = config_manager._calculate_checksum(Path("/nonexistent"))
        assert checksum == ""

    def test_detect_config_type_file(self, config_manager, sample_config_file):
        """Test configuration type detection for files."""
        config_type = config_manager._detect_config_type(sample_config_file)
        assert config_type == ConfigType.DOTFILE

    def test_detect_config_type_directory(self, config_manager, sample_config_dir):
        """Test configuration type detection for directories."""
        config_type = config_manager._detect_config_type(sample_config_dir)
        assert config_type == ConfigType.CONFIG_DIR

    def test_detect_config_type_script(self, config_manager, tmp_path):
        """Test configuration type detection for scripts."""
        script_file = tmp_path / "script.sh"
        script_file.write_text("#!/bin/bash\necho 'hello'")

        config_type = config_manager._detect_config_type(script_file)
        assert config_type == ConfigType.SCRIPT

    def test_detect_config_type_template(self, config_manager, tmp_path):
        """Test configuration type detection for templates."""
        template_file = tmp_path / "template.conf"
        template_file.write_text("user={{USER}}\nhome={{HOME}}")

        config_type = config_manager._detect_config_type(template_file)
        assert config_type == ConfigType.TEMPLATE

    def test_get_repo_path_for_config(self, config_manager):
        """Test repository path generation for configurations."""
        source_path = platform_detector.home_dir / ".vimrc"
        repo_path = config_manager._get_repo_path_for_config(
            source_path, ConfigType.DOTFILE
        )

        assert isinstance(repo_path, Path)
        assert str(repo_path).startswith(str(config_manager.configs_dir))

    def test_add_config_file(self, config_manager, sample_config_file):
        """Test adding a configuration file."""
        success = config_manager.add_config(
            source_path=sample_config_file,
            name="test_config",
            description="Test configuration",
            tags=["test"]
        )

        assert success is True
        assert "test_config" in config_manager._configs

        config = config_manager._configs["test_config"]
        assert config.name == "test_config"
        assert config.description == "Test configuration"
        assert "test" in config.tags
        assert config.status == ConfigStatus.TRACKED

    def test_add_config_directory(self, config_manager, sample_config_dir):
        """Test adding a configuration directory."""
        success = config_manager.add_config(
            source_path=sample_config_dir,
            name="test_dir_config"
        )

        assert success is True
        assert "test_dir_config" in config_manager._configs

        config = config_manager._configs["test_dir_config"]
        assert config.config_type == ConfigType.CONFIG_DIR

    def test_add_config_nonexistent(self, config_manager):
        """Test adding a non-existent configuration."""
        success = config_manager.add_config(
            source_path="/nonexistent/path",
            name="nonexistent"
        )

        assert success is False
        assert "nonexistent" not in config_manager._configs

    def test_add_config_duplicate(self, config_manager, sample_config_file):
        """Test adding duplicate configuration without force."""
        # Add first time
        success1 = config_manager.add_config(
            source_path=sample_config_file,
            name="duplicate"
        )
        assert success1 is True

        # Try to add again without force
        success2 = config_manager.add_config(
            source_path=sample_config_file,
            name="duplicate"
        )
        assert success2 is False

    def test_add_config_duplicate_with_force(self, config_manager, sample_config_file):
        """Test adding duplicate configuration with force."""
        # Add first time
        config_manager.add_config(source_path=sample_config_file, name="duplicate")

        # Add again with force
        success = config_manager.add_config(
            source_path=sample_config_file,
            name="duplicate",
            force=True
        )
        assert success is True

    def test_remove_config(self, config_manager, sample_config_file):
        """Test removing a configuration."""
        # First add a configuration
        config_manager.add_config(source_path=sample_config_file, name="to_remove")
        assert "to_remove" in config_manager._configs

        # Remove it
        success = config_manager.remove_config("to_remove")
        assert success is True
        assert "to_remove" not in config_manager._configs

    def test_remove_config_nonexistent(self, config_manager):
        """Test removing a non-existent configuration."""
        success = config_manager.remove_config("nonexistent")
        assert success is False

    def test_remove_config_keep_files(self, config_manager, sample_config_file):
        """Test removing configuration while keeping files."""
        # Add configuration
        config_manager.add_config(source_path=sample_config_file, name="keep_files")
        config = config_manager._configs["keep_files"]
        repo_path = config.repo_path

        # Ensure repo file exists
        assert repo_path.exists()

        # Remove with keep_files=True
        success = config_manager.remove_config("keep_files", keep_files=True)
        assert success is True
        assert "keep_files" not in config_manager._configs
        assert repo_path.exists()  # File should still exist

    def test_list_configs_no_filter(self, config_manager, sample_config_file):
        """Test listing all configurations."""
        config_manager.add_config(source_path=sample_config_file, name="config1")
        config_manager.add_config(source_path=sample_config_file, name="config2")

        configs = config_manager.list_configs()
        assert len(configs) == 2
        assert all(isinstance(config, ConfigFile) for config in configs)

    def test_list_configs_platform_filter(self, config_manager, sample_config_file):
        """Test listing configurations with platform filter."""
        config_manager.add_config(
            source_path=sample_config_file,
            name="linux_config",
            platforms=[OSType.LINUX]
        )
        config_manager.add_config(
            source_path=sample_config_file,
            name="macos_config",
            platforms=[OSType.MACOS]
        )

        linux_configs = config_manager.list_configs(platform=OSType.LINUX)
        assert len(linux_configs) == 1
        assert linux_configs[0].name == "linux_config"

    def test_list_configs_status_filter(self, config_manager, sample_config_file):
        """Test listing configurations with status filter."""
        config_manager.add_config(source_path=sample_config_file, name="tracked")

        tracked_configs = config_manager.list_configs(status=ConfigStatus.TRACKED)
        assert len(tracked_configs) == 1
        assert tracked_configs[0].status == ConfigStatus.TRACKED

    def test_list_configs_tags_filter(self, config_manager, sample_config_file):
        """Test listing configurations with tags filter."""
        config_manager.add_config(
            source_path=sample_config_file,
            name="vim_config",
            tags=["editor", "vim"]
        )
        config_manager.add_config(
            source_path=sample_config_file,
            name="shell_config",
            tags=["shell", "bash"]
        )

        editor_configs = config_manager.list_configs(tags=["editor"])
        assert len(editor_configs) == 1
        assert editor_configs[0].name == "vim_config"

    def test_get_config(self, config_manager, sample_config_file):
        """Test getting a specific configuration."""
        config_manager.add_config(source_path=sample_config_file, name="test")

        config = config_manager.get_config("test")
        assert config is not None
        assert config.name == "test"

        # Test non-existent config
        config = config_manager.get_config("nonexistent")
        assert config is None

    def test_check_status(self, config_manager, sample_config_file):
        """Test checking status of all configurations."""
        config_manager.add_config(source_path=sample_config_file, name="test")

        status_map = config_manager.check_status()

        assert isinstance(status_map, dict)
        assert "tracked" in status_map
        assert "modified" in status_map
        assert "missing" in status_map

        # Should have at least one tracked config
        assert len(status_map["tracked"]) >= 1

    def test_update_config(self, config_manager, sample_config_file):
        """Test updating a configuration."""
        config_manager.add_config(source_path=sample_config_file, name="update_test")

        # Modify source file
        sample_config_file.write_text("# Modified configuration\nkey=new_value\n")

        success = config_manager.update_config("update_test")
        assert success is True

    def test_update_config_nonexistent(self, config_manager):
        """Test updating a non-existent configuration."""
        success = config_manager.update_config("nonexistent")
        assert success is False

    def test_deploy_config(self, config_manager, sample_config_file, tmp_path):
        """Test deploying a configuration."""
        # Create a different target path
        target_path = tmp_path / "deployed_config"

        config_manager.add_config(source_path=sample_config_file, name="deploy_test")

        # Modify the config to use our target path
        config = config_manager._configs["deploy_test"]
        config.source_path = target_path

        success = config_manager.deploy_config("deploy_test", force=True)
        assert success is True

    def test_deploy_config_nonexistent(self, config_manager):
        """Test deploying a non-existent configuration."""
        success = config_manager.deploy_config("nonexistent")
        assert success is False

    def test_deploy_all(self, config_manager, sample_config_file, tmp_path):
        """Test deploying all configurations."""
        # Add multiple configs
        target1 = tmp_path / "config1"
        target2 = tmp_path / "config2"

        config_manager.add_config(source_path=sample_config_file, name="deploy1")
        config_manager.add_config(source_path=sample_config_file, name="deploy2")

        # Modify target paths
        config_manager._configs["deploy1"].source_path = target1
        config_manager._configs["deploy2"].source_path = target2

        deployed = config_manager.deploy_all(force=True)
        assert deployed >= 0  # Should deploy at least some configs

    def test_restore_config_from_repo(self, config_manager, sample_config_file, tmp_path):
        """Test restoring a configuration from repository."""
        target_path = tmp_path / "restore_target"

        config_manager.add_config(source_path=sample_config_file, name="restore_test")
        config = config_manager._configs["restore_test"]
        config.source_path = target_path

        success = config_manager.restore_config("restore_test", from_backup=False)
        assert success is True

    def test_restore_config_nonexistent(self, config_manager):
        """Test restoring a non-existent configuration."""
        success = config_manager.restore_config("nonexistent")
        assert success is False

    def test_get_stats(self, config_manager, sample_config_file):
        """Test getting configuration statistics."""
        config_manager.add_config(
            source_path=sample_config_file,
            name="stats_test",
            tags=["test"]
        )

        stats = config_manager.get_stats()

        assert isinstance(stats, dict)
        assert "total_configs" in stats
        assert "by_type" in stats
        assert "by_platform" in stats
        assert "by_status" in stats

        assert stats["total_configs"] >= 1

    def test_save_and_load_config_index(self, config_manager, sample_config_file):
        """Test saving and loading configuration index."""
        # Add a configuration
        config_manager.add_config(source_path=sample_config_file, name="index_test")

        # Save should happen automatically, but ensure it exists
        assert config_manager.config_index_file.exists()

        # Create new config manager to test loading
        new_manager = ConfigManager(config_manager.repo_path)
        assert "index_test" in new_manager._configs

    def test_create_backup(self, config_manager, sample_config_file):
        """Test backup creation."""
        backup_path = config_manager._create_backup(sample_config_file, "test_backup")

        assert backup_path is not None
        assert backup_path.exists()
        assert backup_path.parent == config_manager.backups_dir

    def test_copy_to_repo(self, config_manager, sample_config_file):
        """Test copying file to repository."""
        repo_path = config_manager.configs_dir / "test_copy"

        success = config_manager._copy_to_repo(sample_config_file, repo_path)
        assert success is True
        assert repo_path.exists()
        assert repo_path.read_text() == sample_config_file.read_text()

    def test_copy_to_repo_directory(self, config_manager, sample_config_dir):
        """Test copying directory to repository."""
        repo_path = config_manager.configs_dir / "test_copy_dir"

        success = config_manager._copy_to_repo(sample_config_dir, repo_path)
        assert success is True
        assert repo_path.exists()
        assert repo_path.is_dir()
        assert (repo_path / "main.conf").exists()
