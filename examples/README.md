# SuperDots Multi-Platform Configuration Examples

This directory contains examples demonstrating the multi-platform configuration management features in SuperDots.

## Overview

SuperDots now supports managing configuration files that have different paths on different operating systems. This is particularly useful for dotfiles that need to be in different locations on Linux, macOS, and Windows.

## Key Features

### 1. Multi-Platform Paths

Instead of having a single source path, configurations can now have different paths for different operating systems:

```python
# Define different bash config paths for different OS
bash_paths = {
    OSType.LINUX: Path.home() / '.bashrc',
    OSType.MACOS: Path.home() / '.bash_profile',
    OSType.WINDOWS: Path.home() / '.bashrc',  # WSL or Git Bash
}

config_manager.add_config(
    source_paths=bash_paths,
    name='bash_config',
    description='Bash shell configuration for multiple platforms'
)
```

### 2. Platform-Specific Deployment

When deploying configurations, SuperDots automatically uses the path appropriate for the current platform:

```python
# This will deploy to the correct path for the current OS
config_manager.deploy_config('bash_config')
```

### 3. Dynamic Platform Path Management

You can add or remove platform-specific paths after creating a configuration:

```python
# Add a path for a specific platform
config_manager.add_platform_path(
    'bash_config',
    OSType.WINDOWS,
    Path.home() / '.bashrc'
)

# Remove a platform path
config_manager.remove_platform_path('bash_config', OSType.WINDOWS)
```

## Common Use Cases

### Shell Configurations

Different shells use different configuration files on different platforms:

- **Bash**: `.bashrc` on Linux, `.bash_profile` on macOS
- **Zsh**: `.zshrc` (usually same on all platforms)
- **PowerShell**: Different locations on Windows vs PowerShell Core

### Editor Configurations

- **Vim**: `.vimrc` on Unix-like systems, `_vimrc` on Windows
- **Neovim**: `~/.config/nvim/` on Unix, `~/AppData/Local/nvim/` on Windows
- **VS Code**: Different settings.json locations per platform

### Application Configurations

- **Git**: Usually same (`.gitconfig`) but can differ
- **SSH**: `~/.ssh/config` vs Windows equivalent
- **Terminal emulators**: Different config locations per platform

## ConfigFile Changes

The `ConfigFile` dataclass now includes:

- `source_paths: Dict[OSType, Path]` - Multiple OS-specific paths
- `get_source_path(platform)` - Get path for specific platform
- `add_source_path(platform, path)` - Add path for platform
- `remove_source_path(platform)` - Remove platform path
- `has_source_for_platform(platform)` - Check if platform is supported
- `get_supported_platforms()` - List all supported platforms
- `get_existing_platforms()` - List platforms with existing files

## ConfigManager Changes

New methods for multi-platform management:

- `add_platform_path(name, platform, path)` - Add platform-specific path
- `remove_platform_path(name, platform)` - Remove platform path
- `list_platform_paths(name)` - List all platform paths for a config

Modified behavior:

- `add_config()` now accepts either a single path or a dict of platform paths
- `deploy_config()` automatically selects the correct path for current platform
- `update_config()` updates from the current platform's source
- `check_status()` considers all platform paths when determining status

## Migration from Single-Path Configs

Existing configurations with single paths are automatically converted to multi-platform format using the current platform. You can then add paths for other platforms as needed.

## Running the Examples

To run the example script:

```bash
cd superdots/examples
python multi_platform_config.py
```

The example script demonstrates:

1. Adding configurations with multiple platform paths
2. Adding platform paths to existing configurations
3. Deploying configurations for the current platform
4. Checking cross-platform status
5. Managing platform-specific paths

## Best Practices

### 1. Plan Your Platform Support

Before adding a configuration, consider which platforms you want to support and where the configuration files should be located on each platform.

### 2. Test on Multiple Platforms

When possible, test your configurations on multiple platforms to ensure they work correctly in different environments.

### 3. Use Consistent Naming

Use descriptive names for your configurations that make it clear what they're for, especially when managing many cross-platform configs.

### 4. Handle Missing Platforms Gracefully

Not all configurations need to exist on all platforms. The system handles missing platform paths gracefully.

### 5. Backup Before Changes

The system automatically creates backups, but consider manually backing up important configurations before making major changes.

## Error Handling

The system handles various error conditions:

- Missing source paths for the current platform
- Non-existent files when adding platform paths
- Platform paths that conflict with existing ones
- Deployment failures due to permission issues

## Future Enhancements

Potential future features:

- Platform-specific configuration templates
- Automatic platform detection and path suggestion
- Conditional deployment based on installed software
- Configuration migration tools between platforms