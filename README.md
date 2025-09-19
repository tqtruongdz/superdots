# SuperDots

A powerful, cross-platform dotfiles and configuration management tool that uses Git repositories for synchronization across Linux, macOS, and Windows systems.

## Features

- **Cross-Platform Support**: Works seamlessly on Linux, macOS, and Windows
- **Git-Based Synchronization**: Uses Git repositories for version control and sync
- **Intelligent Platform Mapping**: Automatically handles platform-specific paths and configurations
- **Flexible Deployment**: Supports both symbolic links and file copying
- **Template System**: Dynamic configuration templates with variable substitution
- **Conflict Resolution**: Built-in strategies for handling sync conflicts
- **Rich CLI Interface**: Beautiful command-line interface with progress indicators
- **Backup Management**: Automatic backup creation before modifications

## Installation

### From Source

```bash
git clone https://github.com/superdots/superdots.git
cd superdots
pip install -e .
```

### Using pip

```bash
pip install superdots
```

## Quick Start

### 1. Initialize a Repository

```bash
# Initialize a local repository
superdots init

# Or initialize with a remote repository
superdots init --remote-url https://github.com/yourusername/dotfiles.git
```

### 2. Add Configurations

```bash
# Add a single configuration file
superdots add ~/.vimrc --name vimrc --description "Vim configuration"

# Add a configuration directory
superdots add ~/.config/nvim --name neovim

# Add with platform-specific settings
superdots add ~/.bashrc --platforms linux darwin
```

### 3. Synchronize

```bash
# Full sync (pull then push)
superdots sync

# Only pull changes
superdots sync --pull-only

# Only push changes
superdots sync --push-only --message "Update shell configs"
```

### 4. Deploy Configurations

```bash
# Deploy all configurations
superdots deploy --all

# Deploy specific configuration
superdots deploy vimrc

# Deploy with force (overwrite existing)
superdots deploy --all --force
```

## Commands

### Repository Management

- `superdots init [--remote-url URL]` - Initialize repository
- `superdots clone URL [--path PATH]` - Clone existing repository
- `superdots remote add NAME URL` - Add remote repository
- `superdots remote remove NAME` - Remove remote repository
- `superdots remote list` - List remote repositories

### Configuration Management

- `superdots add PATH [OPTIONS]` - Add configuration to management
- `superdots remove NAME [--keep-files]` - Remove configuration
- `superdots list [--platform PLATFORM] [--status STATUS]` - List configurations
- `superdots update NAME|--all` - Update configurations from source
- `superdots deploy NAME|--all [--force]` - Deploy configurations

### Synchronization

- `superdots sync [OPTIONS]` - Synchronize with remote repository
- `superdots status` - Show repository and configuration status

### Global Options

- `--repo-path PATH` - Custom repository path (default: ~/.superdots)
- `--verbose` - Enable verbose logging
- `--log-file PATH` - Custom log file location

## Configuration Structure

SuperDots organizes configurations in a structured repository:

```
.superdots/
├── configs/                 # Platform-specific configurations
│   ├── linux/
│   ├── darwin/
│   └── windows/
├── backups/                 # Automatic backups
├── templates/               # Configuration templates
├── scripts/                 # Installation scripts
└── .superdots/             # SuperDots metadata
    ├── config_index.json
    └── sync_config.json
```

## Platform Support

### Linux
- Shell configs: `.bashrc`, `.zshrc`, `.profile`
- Desktop configs: `.config/` directory structure
- System configs: `/etc/` files (with proper permissions)

### macOS
- Shell configs: `.bash_profile`, `.zshrc`
- Application configs: `~/Library/Application Support/`
- Preferences: `~/Library/Preferences/`

### Windows
- Shell configs: `.bashrc` (Git Bash, WSL)
- Application configs: `%APPDATA%` and `%LOCALAPPDATA%`
- PowerShell profiles

## Template System

SuperDots supports dynamic templates with variable substitution:

```bash
# In a template file
export PATH="{{HOME}}/bin:$PATH"
export EDITOR="{{EDITOR}}"
# Platform: {{PLATFORM}}
# User: {{USER}}
```

Available variables:
- `{{HOME}}` - User home directory
- `{{USER}}` - Username
- `{{PLATFORM}}` - Current platform (linux/darwin/windows)
- `{{HOSTNAME}}` - System hostname
- `{{CONFIG_DIR}}` - Platform config directory

## Advanced Usage

### Platform-Specific Configurations

```bash
# Add configuration for specific platforms
superdots add ~/.config/alacritty/alacritty.yml \
    --platforms linux darwin \
    --name alacritty

# Different configs per platform
superdots add ~/.bashrc --name bash-linux --platforms linux
superdots add ~/.bash_profile --name bash-macos --platforms darwin
```

### Conflict Resolution

```bash
# Auto-resolve conflicts by keeping local changes
superdots sync --auto-resolve --conflict-strategy keep-local

# Auto-resolve by keeping remote changes  
superdots sync --auto-resolve --conflict-strategy keep-remote
```

### Custom Repository Location

```bash
# Use custom repository path
superdots --repo-path ~/my-dotfiles init
superdots --repo-path ~/my-dotfiles add ~/.vimrc
```

## Configuration File

Create `~/.config/superdots/config.yaml` for persistent settings:

```yaml
repository:
  path: ~/.superdots
  remote_url: https://github.com/yourusername/dotfiles.git

sync:
  auto_commit: true
  conflict_resolution: manual
  backup_before_deploy: true

deployment:
  prefer_symlinks: true
  create_missing_dirs: true

platforms:
  # Custom platform mappings
  mappings:
    shell_config:
      linux: ~/.bashrc
      darwin: ~/.bash_profile
      windows: ~/.bashrc
```

## Troubleshooting

### Common Issues

**Repository not found**
```bash
# Ensure repository is initialized
superdots status
# If not initialized, run:
superdots init
```

**Permission errors on Windows**
```bash
# Run as Administrator for symlink support, or use copy mode
superdots add ~/.vimrc --no-symlink
```

**Merge conflicts**
```bash
# Check status and resolve manually
superdots status
git -C ~/.superdots status
# Or use auto-resolution
superdots sync --auto-resolve
```

### Debugging

Enable verbose logging:
```bash
superdots --verbose --log-file debug.log sync
```

Check repository status:
```bash
superdots status
cd ~/.superdots
git status
git log --oneline -n 5
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run tests: `python -m pytest tests/`
5. Submit a pull request

## Development Setup

```bash
git clone https://github.com/superdots/superdots.git
cd superdots
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: https://superdots.readthedocs.io
- **Issues**: https://github.com/superdots/superdots/issues
- **Discussions**: https://github.com/superdots/superdots/discussions

## Acknowledgments

SuperDots is inspired by various dotfiles management tools and aims to provide a unified, cross-platform solution with Git-based synchronization.