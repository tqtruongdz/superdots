#!/usr/bin/env python3
"""
Example script demonstrating multi-platform configuration management with SuperDots.

This script shows how to use the new multi-platform path functionality
to manage configuration files that have different locations on different operating systems.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from superdots.core.config import ConfigManager, ConfigFile
from superdots.utils.platform import OSType


def example_bash_config():
    """Example: Bash configuration with different paths per OS."""
    print("=== Example: Bash Configuration ===")

    # Initialize config manager
    repo_path = Path.home() / '.superdots'
    config_manager = ConfigManager(repo_path)

    # Define different bash config paths for different OS
    bash_paths = {
        OSType.LINUX: Path.home() / '.bashrc',
        OSType.MACOS: Path.home() / '.bash_profile',
        OSType.WINDOWS: Path.home() / '.bashrc',  # WSL or Git Bash
    }

    # Add configuration with multiple OS paths
    success = config_manager.add_config(
        source_paths=bash_paths,
        name='bash_config',
        description='Bash shell configuration for multiple platforms',
        tags=['shell', 'bash'],
        use_symlink=True
    )

    if success:
        print("✅ Successfully added bash configuration with multi-platform paths")

        # Show platform paths
        paths = config_manager.list_platform_paths('bash_config')
        for platform, (path, exists) in paths.items():
            status = "✅" if exists else "❌"
            print(f"  {platform.value}: {path} {status}")
    else:
        print("❌ Failed to add bash configuration")


def example_vim_config():
    """Example: Vim configuration with different paths per OS."""
    print("\n=== Example: Vim Configuration ===")

    repo_path = Path.home() / '.superdots'
    config_manager = ConfigManager(repo_path)

    # Define different vim config paths for different OS
    vim_paths = {
        OSType.LINUX: Path.home() / '.vimrc',
        OSType.MACOS: Path.home() / '.vimrc',
        OSType.WINDOWS: Path.home() / '_vimrc',  # Windows vim uses _vimrc
    }

    success = config_manager.add_config(
        source_paths=vim_paths,
        name='vim_config',
        description='Vim editor configuration',
        tags=['editor', 'vim'],
        use_symlink=True
    )

    if success:
        print("✅ Successfully added vim configuration")


def example_git_config():
    """Example: Git configuration (same path on all platforms)."""
    print("\n=== Example: Git Configuration ===")

    repo_path = Path.home() / '.superdots'
    config_manager = ConfigManager(repo_path)

    # Git config is the same on all platforms
    git_paths = {
        OSType.LINUX: Path.home() / '.gitconfig',
        OSType.MACOS: Path.home() / '.gitconfig',
        OSType.WINDOWS: Path.home() / '.gitconfig',
    }

    success = config_manager.add_config(
        source_paths=git_paths,
        name='git_config',
        description='Git configuration file',
        tags=['git', 'vcs'],
        use_symlink=True
    )

    if success:
        print("✅ Successfully added git configuration")


def example_add_platform_later():
    """Example: Adding platform-specific path later."""
    print("\n=== Example: Adding Platform Path Later ===")

    repo_path = Path.home() / '.superdots'
    config_manager = ConfigManager(repo_path)

    # First, add config for current platform only
    current_bashrc = Path.home() / '.bashrc'
    if current_bashrc.exists():
        success = config_manager.add_config(
            source_paths=str(current_bashrc),  # Single path for current platform
            name='bashrc_example',
            description='Example bash configuration'
        )

        if success:
            print("✅ Added configuration for current platform")

            # Later, add paths for other platforms
            other_platforms = {
                OSType.MACOS: Path.home() / '.bash_profile',
                OSType.WINDOWS: Path.home() / '.bashrc',
            }

            for platform, path in other_platforms.items():
                # Note: This will fail if the path doesn't exist
                # In real usage, you'd create the file first or copy from repo
                result = config_manager.add_platform_path(
                    'bashrc_example',
                    platform,
                    path,
                    force=False
                )
                if result:
                    print(f"✅ Added {platform.value} path: {path}")
                else:
                    print(f"❌ Failed to add {platform.value} path: {path}")


def example_deploy_current_platform():
    """Example: Deploying configuration for current platform."""
    print("\n=== Example: Deploying Configuration ===")

    repo_path = Path.home() / '.superdots'
    config_manager = ConfigManager(repo_path)

    # List all configurations
    configs = config_manager.list_configs()

    if configs:
        print(f"Found {len(configs)} configurations:")

        for config in configs:
            print(f"\n📁 {config.name}")
            print(f"   Type: {config.config_type.value}")
            print(f"   Platforms: {[p.value for p in config.platforms]}")

            # Show current platform path
            current_path = config.get_source_path()
            if current_path:
                exists = "✅" if current_path.exists() else "❌"
                print(f"   Current platform path: {current_path} {exists}")
            else:
                print(f"   ❌ No path defined for current platform ({config.current_platform.value})")

            # Try to deploy
            if config.name in ['bash_config', 'vim_config', 'git_config']:
                print(f"   Deploying {config.name}...")
                success = config_manager.deploy_config(config.name, force=True)
                if success:
                    print(f"   ✅ Deployed successfully")
                else:
                    print(f"   ❌ Deployment failed")
    else:
        print("No configurations found")


def example_cross_platform_status():
    """Example: Checking status across platforms."""
    print("\n=== Example: Cross-Platform Status ===")

    repo_path = Path.home() / '.superdots'
    config_manager = ConfigManager(repo_path)

    # Get overall status
    status = config_manager.check_status()

    print("Configuration Status:")
    for status_type, config_names in status.items():
        if config_names:
            print(f"  {status_type.upper()}: {', '.join(config_names)}")

    # Show detailed platform info for each config
    configs = config_manager.list_configs()
    for config in configs:
        print(f"\n📁 {config.name}")

        for platform in config.get_supported_platforms():
            path = config.source_paths[platform]
            exists = path.exists()
            status_icon = "✅" if exists else "❌"
            print(f"   {platform.value}: {path} {status_icon}")


def main():
    """Run all examples."""
    print("SuperDots Multi-Platform Configuration Examples")
    print("=" * 50)

    try:
        example_bash_config()
        example_vim_config()
        example_git_config()
        example_add_platform_later()
        example_deploy_current_platform()
        example_cross_platform_status()

        print("\n" + "=" * 50)
        print("All examples completed!")

    except Exception as e:
        print(f"❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
