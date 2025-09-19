#!/bin/bash

# SuperDots Installation Script
# This script installs SuperDots on Linux, macOS, and Windows (Git Bash/WSL)

set -e

# Configuration
SUPERDOTS_VERSION="1.0.0"
SUPERDOTS_REPO="https://github.com/superdots/superdots.git"
INSTALL_DIR="$HOME/.local/superdots"
BIN_DIR="$HOME/.local/bin"
VENV_DIR="$INSTALL_DIR/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect platform
detect_platform() {
    case "$(uname -s)" in
        Darwin*)
            PLATFORM="darwin"
            ;;
        Linux*)
            PLATFORM="linux"
            ;;
        CYGWIN*|MINGW32*|MSYS*|MINGW*)
            PLATFORM="windows"
            ;;
        *)
            log_error "Unsupported platform: $(uname -s)"
            exit 1
            ;;
    esac
    log_info "Detected platform: $PLATFORM"
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed."
        log_error "Please install Python 3.8 or later and try again."
        exit 1
    fi

    local python_version
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    log_info "Python version: $python_version"

    # Check if Python version is supported
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
        log_success "Python version is supported"
    else
        log_error "Python 3.8 or later is required. Found: $python_version"
        exit 1
    fi

    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git is required but not installed."
        log_error "Please install Git and try again."
        exit 1
    fi

    log_success "All dependencies are satisfied"
}

# Create installation directory
create_install_dir() {
    log_info "Creating installation directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
}

# Install SuperDots
install_superdots() {
    log_info "Installing SuperDots..."

    # Remove existing installation
    if [ -d "$INSTALL_DIR" ]; then
        log_info "Removing existing installation..."
        rm -rf "$INSTALL_DIR"
    fi

    # Create fresh directory
    create_install_dir

    # Clone repository
    log_info "Cloning SuperDots repository..."
    git clone "$SUPERDOTS_REPO" "$INSTALL_DIR/source" --branch main --depth 1

    # Create virtual environment
    log_info "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"

    # Activate virtual environment and install
    log_info "Installing SuperDots in virtual environment..."
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    pip install --upgrade pip

    # Install SuperDots
    cd "$INSTALL_DIR/source"
    pip install -e .

    # Create wrapper script
    log_info "Creating wrapper script..."
    cat > "$BIN_DIR/superdots" << EOF
#!/bin/bash
# SuperDots wrapper script
source "$VENV_DIR/bin/activate"
exec python -m superdots.cli "\$@"
EOF

    # Make wrapper executable
    chmod +x "$BIN_DIR/superdots"

    # Create short alias
    ln -sf "$BIN_DIR/superdots" "$BIN_DIR/sdots"

    log_success "SuperDots installed successfully"
}

# Setup shell integration
setup_shell_integration() {
    log_info "Setting up shell integration..."

    local shell_config
    local shell_name

    # Detect current shell
    shell_name=$(basename "$SHELL")

    case "$shell_name" in
        bash)
            if [ "$PLATFORM" = "darwin" ]; then
                shell_config="$HOME/.bash_profile"
            else
                shell_config="$HOME/.bashrc"
            fi
            ;;
        zsh)
            shell_config="$HOME/.zshrc"
            ;;
        fish)
            shell_config="$HOME/.config/fish/config.fish"
            ;;
        *)
            log_warning "Unknown shell: $shell_name. Manual setup may be required."
            return
            ;;
    esac

    # Add PATH to shell config if not already present
    if [ -f "$shell_config" ] && ! grep -q "$BIN_DIR" "$shell_config"; then
        log_info "Adding SuperDots to PATH in $shell_config"
        echo "" >> "$shell_config"
        echo "# SuperDots" >> "$shell_config"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$shell_config"

        # Add shell integration
        local integration_script="$INSTALL_DIR/source/templates/shell_integration.sh"
        if [ -f "$integration_script" ]; then
            echo "source \"$integration_script\"" >> "$shell_config"
            log_success "Shell integration added to $shell_config"
        fi
    else
        log_info "SuperDots already in PATH or shell config not found"
    fi

    # Update current session PATH
    export PATH="$BIN_DIR:$PATH"
}

# Verify installation
verify_installation() {
    log_info "Verifying installation..."

    if command -v superdots &> /dev/null; then
        local version
        version=$(superdots --version 2>/dev/null | head -n1)
        log_success "SuperDots is accessible: $version"

        # Test basic functionality
        if superdots --help &> /dev/null; then
            log_success "SuperDots is working correctly"
        else
            log_warning "SuperDots installed but may have issues"
        fi
    else
        log_error "SuperDots installation failed or is not in PATH"
        log_error "You may need to restart your shell or manually add $BIN_DIR to your PATH"
        return 1
    fi
}

# Print usage instructions
print_usage() {
    log_success "Installation completed successfully!"
    echo ""
    echo "=== Getting Started ==="
    echo "1. Restart your shell or run: source ~/.bashrc (or ~/.zshrc)"
    echo "2. Initialize SuperDots: superdots init"
    echo "3. Add your first config: superdots add ~/.vimrc"
    echo "4. Check status: superdots status"
    echo ""
    echo "=== Useful Commands ==="
    echo "• superdots --help          - Show all available commands"
    echo "• superdots init            - Initialize a new repository"
    echo "• superdots add <file>      - Add a configuration file"
    echo "• superdots list            - List all managed configurations"
    echo "• superdots deploy --all    - Deploy all configurations"
    echo "• superdots sync            - Synchronize with remote repository"
    echo ""
    echo "=== Quick Aliases ==="
    echo "• sdots                     - Short alias for superdots"
    echo "• sdstatus                  - Quick status check (with shell integration)"
    echo "• sdsync                    - Quick sync (with shell integration)"
    echo ""
    echo "=== Documentation ==="
    echo "• GitHub: https://github.com/superdots/superdots"
    echo "• Docs: https://superdots.readthedocs.io"
    echo ""
    echo "=== Installation Details ==="
    echo "• Installed to: $INSTALL_DIR"
    echo "• Executables: $BIN_DIR"
    echo "• Platform: $PLATFORM"
    echo ""
}

# Cleanup on failure
cleanup() {
    if [ $? -ne 0 ]; then
        log_error "Installation failed. Cleaning up..."
        rm -rf "$INSTALL_DIR"
    fi
}

# Uninstall function
uninstall() {
    log_info "Uninstalling SuperDots..."

    # Remove installation directory
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        log_success "Removed installation directory"
    fi

    # Remove executables
    rm -f "$BIN_DIR/superdots"
    rm -f "$BIN_DIR/sdots"

    # Remove from shell configs (basic cleanup)
    local shell_configs=("$HOME/.bashrc" "$HOME/.bash_profile" "$HOME/.zshrc")
    for config in "${shell_configs[@]}"; do
        if [ -f "$config" ]; then
            # Remove SuperDots lines (simple approach)
            sed -i.bak '/# SuperDots/,+2d' "$config" 2>/dev/null || true
        fi
    done

    log_success "SuperDots uninstalled successfully"
    log_info "You may need to restart your shell for changes to take effect"
}

# Main installation function
main() {
    echo "=== SuperDots Installation Script ==="
    echo "Version: $SUPERDOTS_VERSION"
    echo "Platform: $(uname -s)"
    echo ""

    # Set trap for cleanup
    trap cleanup EXIT

    # Parse arguments
    case "${1:-install}" in
        install)
            detect_platform
            check_dependencies
            install_superdots
            setup_shell_integration
            if verify_installation; then
                print_usage
            else
                exit 1
            fi
            ;;
        uninstall)
            uninstall
            ;;
        *)
            echo "Usage: $0 [install|uninstall]"
            echo ""
            echo "  install    - Install SuperDots (default)"
            echo "  uninstall  - Remove SuperDots installation"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
