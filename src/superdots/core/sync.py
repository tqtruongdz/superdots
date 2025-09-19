#!/usr/bin/env python3
"""
Synchronization manager for SuperDots.

This module provides functionality to synchronize dotfiles and configurations
across different platforms using Git repositories, handling platform-specific
differences and conflict resolution.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime
from enum import Enum

from .config import ConfigManager, ConfigFile, ConfigStatus, OSType
from .git_handler import GitHandler, GitError
from ..utils.logger import get_logger
from ..utils.platform import platform_detector


class SyncStatus(Enum):
    """Synchronization status."""
    SUCCESS = "success"
    CONFLICT = "conflict"
    ERROR = "error"
    NO_CHANGES = "no_changes"
    PARTIAL = "partial"


class ConflictResolution(Enum):
    """Conflict resolution strategies."""
    KEEP_LOCAL = "keep_local"
    KEEP_REMOTE = "keep_remote"
    MERGE = "merge"
    SKIP = "skip"
    MANUAL = "manual"


class SyncResult:
    """Result of a synchronization operation."""

    def __init__(self):
        self.status = SyncStatus.SUCCESS
        self.message = ""
        self.configs_synced = 0
        self.configs_failed = 0
        self.conflicts = []
        self.errors = []

    def add_error(self, config_name: str, error: str):
        """Add an error to the result."""
        self.errors.append(f"{config_name}: {error}")
        self.configs_failed += 1

    def add_conflict(self, config_name: str, conflict_type: str):
        """Add a conflict to the result."""
        self.conflicts.append(f"{config_name}: {conflict_type}")

    def mark_success(self, config_name: str):
        """Mark a configuration as successfully synced."""
        self.configs_synced += 1

    def finalize(self):
        """Finalize the result and determine overall status."""
        if self.errors:
            if self.configs_synced > 0:
                self.status = SyncStatus.PARTIAL
            else:
                self.status = SyncStatus.ERROR
        elif self.conflicts:
            self.status = SyncStatus.CONFLICT
        elif self.configs_synced == 0:
            self.status = SyncStatus.NO_CHANGES
        else:
            self.status = SyncStatus.SUCCESS


class SyncManager:
    """Main synchronization manager class."""

    def __init__(self, config_manager: ConfigManager, git_handler: GitHandler):
        """
        Initialize sync manager.

        Args:
            config_manager: Configuration manager instance
            git_handler: Git handler instance
        """
        self.logger = get_logger(f"{__name__}.SyncManager")
        self.config_manager = config_manager
        self.git_handler = git_handler

        # Sync configuration
        self.sync_config_file = config_manager.repo_path / '.superdots' / 'sync_config.json'
        self.conflict_resolution = ConflictResolution.MANUAL

        # Platform mapping for cross-platform sync
        self.platform_mappings = self._load_platform_mappings()

    def _load_platform_mappings(self) -> Dict[str, Dict[str, str]]:
        """Load platform-specific path mappings."""
        mappings = {
            'home_config_paths': {
                'linux': '~/.config',
                'darwin': '~/.config',  # Many tools use this on macOS
                'windows': '~/AppData/Roaming'
            },
            'shell_configs': {
                'linux': '~/.bashrc',
                'darwin': '~/.bash_profile',
                'windows': '~/.bashrc'
            },
            'editor_configs': {
                'linux': '~/.config/Code/User',
                'darwin': '~/Library/Application Support/Code/User',
                'windows': '~/AppData/Roaming/Code/User'
            }
        }

        # Load custom mappings if they exist
        mappings_file = self.config_manager.repo_path / 'platform_mappings.json'
        if mappings_file.exists():
            try:
                import json
                with open(mappings_file, 'r', encoding='utf-8') as f:
                    custom_mappings = json.load(f)
                    mappings.update(custom_mappings)
            except Exception as e:
                self.logger.warning(f"Failed to load custom platform mappings: {e}")

        return mappings

    def set_conflict_resolution(self, strategy: ConflictResolution):
        """Set the conflict resolution strategy."""
        self.conflict_resolution = strategy
        self.logger.info(f"Conflict resolution strategy set to: {strategy.value}")

    def push_changes(self, message: Optional[str] = None, force: bool = False) -> SyncResult:
        """
        Push local changes to remote repository.

        Args:
            message: Commit message (auto-generated if not provided)
            force: Force push even if there are conflicts

        Returns:
            SyncResult with operation details
        """
        result = SyncResult()

        try:
            # Check if repository is clean
            if not self.git_handler.is_dirty and not force:
                result.status = SyncStatus.NO_CHANGES
                result.message = "No local changes to push"
                return result

            # Update configurations from their source locations
            self.logger.info("Updating configurations from source locations...")
            updated_configs = []

            for name, config in self.config_manager._configs.items():
                if config.source_path.exists():
                    if self.config_manager.update_config(name):
                        updated_configs.append(name)
                        result.mark_success(name)
                    else:
                        result.add_error(name, "Failed to update from source")
                else:
                    self.logger.warning(f"Source path missing for '{name}': {config.source_path}")

            # Generate commit message
            if not message:
                platform = platform_detector.os_type.value
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if updated_configs:
                    config_list = ', '.join(updated_configs[:3])
                    if len(updated_configs) > 3:
                        config_list += f" and {len(updated_configs) - 3} others"
                    message = f"Update configs on {platform}: {config_list} ({timestamp})"
                else:
                    message = f"Sync from {platform} ({timestamp})"

            # Add changes to git
            if not self.git_handler.add_all():
                result.add_error("git", "Failed to add changes")
                result.finalize()
                return result

            # Commit changes
            platform_info = f"{platform_detector.os_type.value}@{os.uname().nodename}"
            if not self.git_handler.commit(message, author_name=f"SuperDots-{platform_info}"):
                result.add_error("git", "Failed to create commit")
                result.finalize()
                return result

            # Push to remote
            if 'origin' in self.git_handler.remotes:
                if self.git_handler.push('origin'):
                    result.message = f"Successfully pushed {len(updated_configs)} configurations"
                    self.logger.info(result.message)
                else:
                    result.add_error("git", "Failed to push to remote")
            else:
                result.add_error("git", "No remote repository configured")

        except Exception as e:
            result.add_error("sync", f"Push operation failed: {e}")
            self.logger.error(f"Push failed: {e}")

        result.finalize()
        return result

    def pull_changes(self, auto_resolve: bool = False) -> SyncResult:
        """
        Pull changes from remote repository and apply them.

        Args:
            auto_resolve: Automatically resolve conflicts using configured strategy

        Returns:
            SyncResult with operation details
        """
        result = SyncResult()

        try:
            # Check if we have uncommitted changes
            if self.git_handler.is_dirty:
                result.add_error("git", "Repository has uncommitted changes. Commit or stash them first.")
                result.finalize()
                return result

            # Fetch changes from remote
            if 'origin' not in self.git_handler.remotes:
                result.add_error("git", "No remote repository configured")
                result.finalize()
                return result

            self.logger.info("Fetching changes from remote repository...")
            if not self.git_handler.fetch('origin'):
                result.add_error("git", "Failed to fetch from remote")
                result.finalize()
                return result

            # Pull changes
            self.logger.info("Pulling changes...")
            if not self.git_handler.pull('origin'):
                # Check if there are conflicts
                if self.git_handler.has_conflicts():
                    self.logger.warning("Merge conflicts detected")
                    result.status = SyncStatus.CONFLICT
                    result.message = "Merge conflicts detected. Manual resolution required."

                    if auto_resolve:
                        conflict_result = self._resolve_conflicts()
                        result.conflicts.extend(conflict_result.conflicts)
                        result.errors.extend(conflict_result.errors)

                    result.finalize()
                    return result
                else:
                    result.add_error("git", "Failed to pull changes")
                    result.finalize()
                    return result

            # Deploy configurations for current platform
            self.logger.info("Deploying configurations for current platform...")
            deployed = self._deploy_platform_configs()
            result.configs_synced = deployed

            if deployed > 0:
                result.message = f"Successfully pulled and deployed {deployed} configurations"
                self.logger.info(result.message)
            else:
                result.status = SyncStatus.NO_CHANGES
                result.message = "No configurations to deploy for current platform"

        except Exception as e:
            result.add_error("sync", f"Pull operation failed: {e}")
            self.logger.error(f"Pull failed: {e}")

        result.finalize()
        return result

    def _deploy_platform_configs(self) -> int:
        """Deploy configurations suitable for the current platform."""
        deployed = 0
        current_platform = platform_detector.os_type

        for name, config in self.config_manager._configs.items():
            if current_platform in config.platforms:
                # Check if this configuration has platform-specific variants
                platform_config = self._get_platform_specific_config(config)

                if platform_config and platform_config.repo_path.exists():
                    try:
                        # Deploy using mapped paths if necessary
                        target_path = self._map_path_for_platform(config.source_path, current_platform)

                        if self._deploy_single_config(platform_config, target_path):
                            deployed += 1
                            self.logger.debug(f"Deployed {name} to {target_path}")
                    except Exception as e:
                        self.logger.error(f"Failed to deploy {name}: {e}")

        return deployed

    def _get_platform_specific_config(self, config: ConfigFile) -> Optional[ConfigFile]:
        """Get platform-specific version of a configuration if it exists."""
        current_platform = platform_detector.os_type

        # First, check if there's a platform-specific version
        platform_repo_path = (
            self.config_manager.configs_dir /
            current_platform.value /
            config.repo_path.relative_to(self.config_manager.configs_dir / config.current_platform.value)
        )

        if platform_repo_path.exists():
            # Create a copy of the config with platform-specific path
            platform_config = ConfigFile(
                name=config.name,
                source_path=config.source_path,
                repo_path=platform_repo_path,
                config_type=config.config_type,
                platforms=config.platforms,
                current_platform=current_platform,
                status=config.status,
                description=config.description,
                tags=config.tags,
                use_symlink=config.use_symlink,
                executable=config.executable,
                template_vars=config.template_vars
            )
            return platform_config

        # If no platform-specific version, return original if it supports current platform
        if current_platform in config.platforms:
            return config

        return None

    def _map_path_for_platform(self, original_path: Path, target_platform: OSType) -> Path:
        """Map a path from one platform to another using platform mappings."""
        original_str = str(original_path)

        # Apply platform mappings
        for category, mappings in self.platform_mappings.items():
            for platform, path_pattern in mappings.items():
                if platform == target_platform.value:
                    # Simple substitution for now - can be extended for more complex mappings
                    expanded_pattern = Path(path_pattern).expanduser()
                    if category == 'home_config_paths':
                        # Map .config paths
                        if '.config' in original_str:
                            mapped_path = str(original_path).replace(
                                str(Path('~/.config').expanduser()),
                                str(expanded_pattern)
                            )
                            return Path(mapped_path)

        # If no mapping found, return original path
        return original_path

    def _deploy_single_config(self, config: ConfigFile, target_path: Path) -> bool:
        """Deploy a single configuration to its target path."""
        try:
            # Create parent directory
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Handle templates
            if config.config_type.value == 'template':
                return self._deploy_template(config, target_path)

            # Remove existing target if it exists
            if target_path.exists():
                if target_path.is_symlink():
                    target_path.unlink()
                elif target_path.is_file():
                    target_path.unlink()
                elif target_path.is_dir():
                    shutil.rmtree(target_path)

            # Deploy based on configuration preferences
            if config.use_symlink and platform_detector.can_symlink():
                return platform_detector.create_symlink(config.repo_path, target_path, force=True)
            else:
                # Copy files
                if config.repo_path.is_file():
                    shutil.copy2(config.repo_path, target_path)
                elif config.repo_path.is_dir():
                    shutil.copytree(config.repo_path, target_path)

                # Set executable permission if needed
                if config.executable and target_path.is_file():
                    os.chmod(target_path, 0o755)

                return True

        except Exception as e:
            self.logger.error(f"Failed to deploy {config.name}: {e}")
            return False

    def _deploy_template(self, config: ConfigFile, target_path: Path) -> bool:
        """Deploy a template configuration with variable substitution."""
        try:
            # Load template content
            template_content = config.repo_path.read_text(encoding='utf-8')

            # Prepare template variables
            template_vars = config.template_vars or {}

            # Add default variables
            default_vars = {
                'HOME': str(platform_detector.home_dir),
                'USER': os.environ.get('USER', os.environ.get('USERNAME', 'user')),
                'PLATFORM': platform_detector.os_type.value,
                'HOSTNAME': os.uname().nodename,
                'CONFIG_DIR': str(platform_detector.get_config_dir()),
            }

            template_vars = {**default_vars, **template_vars}

            # Simple template substitution (can be extended to use Jinja2 if needed)
            rendered_content = template_content
            for key, value in template_vars.items():
                rendered_content = rendered_content.replace(f'{{{{{key}}}}}', str(value))

            # Write rendered content
            target_path.write_text(rendered_content, encoding='utf-8')

            # Set executable permission if needed
            if config.executable:
                os.chmod(target_path, 0o755)

            return True

        except Exception as e:
            self.logger.error(f"Failed to deploy template {config.name}: {e}")
            return False

    def _resolve_conflicts(self) -> SyncResult:
        """Resolve merge conflicts based on configured strategy."""
        result = SyncResult()

        try:
            if self.conflict_resolution == ConflictResolution.KEEP_LOCAL:
                # Keep local changes, discard remote
                if self.git_handler.reset_hard('HEAD'):
                    result.message = "Resolved conflicts by keeping local changes"
                else:
                    result.add_error("git", "Failed to resolve conflicts")

            elif self.conflict_resolution == ConflictResolution.KEEP_REMOTE:
                # Keep remote changes, discard local
                if self.git_handler.reset_hard('origin/' + self.git_handler.current_branch):
                    result.message = "Resolved conflicts by keeping remote changes"
                else:
                    result.add_error("git", "Failed to resolve conflicts")

            elif self.conflict_resolution == ConflictResolution.SKIP:
                # Skip conflicted files
                result.add_conflict("merge", "Conflicts skipped, manual resolution required")

            else:  # MANUAL or MERGE
                result.add_conflict("merge", "Manual conflict resolution required")

        except Exception as e:
            result.add_error("conflict_resolution", str(e))

        result.finalize()
        return result

    def sync(self,
             pull_first: bool = True,
             auto_commit: bool = True,
             commit_message: Optional[str] = None,
             auto_resolve: bool = False) -> SyncResult:
        """
        Perform a full synchronization (pull then push).

        Args:
            pull_first: Whether to pull remote changes first
            auto_commit: Whether to automatically commit local changes
            commit_message: Custom commit message
            auto_resolve: Whether to auto-resolve conflicts

        Returns:
            SyncResult with operation details
        """
        result = SyncResult()

        try:
            # Pull changes first if requested
            if pull_first:
                self.logger.info("Pulling changes from remote...")
                pull_result = self.pull_changes(auto_resolve=auto_resolve)

                result.configs_synced += pull_result.configs_synced
                result.conflicts.extend(pull_result.conflicts)
                result.errors.extend(pull_result.errors)

                # If pull failed with conflicts and no auto-resolve, stop here
                if pull_result.status == SyncStatus.CONFLICT and not auto_resolve:
                    result.status = SyncStatus.CONFLICT
                    result.message = "Pull conflicts detected. Resolve manually or use --auto-resolve."
                    return result

            # Push local changes
            if auto_commit:
                self.logger.info("Pushing local changes...")
                push_result = self.push_changes(message=commit_message)

                result.configs_synced += push_result.configs_synced
                result.configs_failed += push_result.configs_failed
                result.errors.extend(push_result.errors)

                if push_result.status == SyncStatus.SUCCESS:
                    if result.message:
                        result.message += f"; {push_result.message}"
                    else:
                        result.message = push_result.message

        except Exception as e:
            result.add_error("sync", f"Full sync failed: {e}")
            self.logger.error(f"Sync failed: {e}")

        result.finalize()
        return result

    def clone_repository(self, url: str, target_path: Optional[Path] = None) -> bool:
        """
        Clone a SuperDots repository from a URL.

        Args:
            url: Repository URL to clone
            target_path: Optional target path (defaults to configured repo path)

        Returns:
            True if successful, False otherwise
        """
        try:
            if target_path is None:
                target_path = self.config_manager.repo_path

            self.logger.info(f"Cloning repository from {url}...")

            if self.git_handler.clone_repository(url, target_path):
                # Reinitialize config manager with cloned repository
                self.config_manager.__init__(target_path)

                # Deploy configurations for current platform
                deployed = self._deploy_platform_configs()

                self.logger.info(f"Successfully cloned repository and deployed {deployed} configurations")
                return True
            else:
                self.logger.error("Failed to clone repository")
                return False

        except Exception as e:
            self.logger.error(f"Clone operation failed: {e}")
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """Get detailed synchronization status."""
        status = {
            'repository': {
                'path': str(self.git_handler.repo_path),
                'is_valid': self.git_handler.is_valid_repo,
                'is_dirty': self.git_handler.is_dirty,
                'current_branch': self.git_handler.current_branch,
                'remotes': self.git_handler.remotes,
            },
            'configurations': self.config_manager.check_status(),
            'platform': {
                'current': platform_detector.os_type.value,
                'can_symlink': platform_detector.can_symlink(),
            },
            'last_sync': None,  # Could be tracked in a sync log
        }

        # Add recent commits
        try:
            commits = self.git_handler.get_commits(max_count=5)
            status['repository']['recent_commits'] = commits
        except Exception as e:
            self.logger.debug(f"Failed to get recent commits: {e}")
            status['repository']['recent_commits'] = []

        return status

    def create_platform_branch(self, platform: OSType) -> bool:
        """Create a platform-specific branch for managing configurations."""
        try:
            branch_name = f"platform/{platform.value}"

            if self.git_handler.create_branch(branch_name, checkout=False):
                self.logger.info(f"Created platform branch: {branch_name}")
                return True
            else:
                self.logger.error(f"Failed to create platform branch: {branch_name}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to create platform branch: {e}")
            return False
