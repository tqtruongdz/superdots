#!/bin/bash
# SuperDots Shell Integration Script
# This script provides shell integration functions for SuperDots
# Source this file in your shell configuration to enable SuperDots features

# Check if SuperDots is available
if ! command -v superdots &> /dev/null; then
    echo "Warning: SuperDots command not found. Some features may not work."
    return 1
fi

# ============================================================================
# Configuration
# ============================================================================

# SuperDots configuration directory
export SUPERDOTS_CONFIG_DIR="${SUPERDOTS_CONFIG_DIR:-$HOME/.config/superdots}"
export SUPERDOTS_REPO_PATH="${SUPERDOTS_REPO_PATH:-$HOME/.superdots}"

# Shell integration settings
export SUPERDOTS_AUTO_SYNC="${SUPERDOTS_AUTO_SYNC:-false}"
export SUPERDOTS_SYNC_INTERVAL="${SUPERDOTS_SYNC_INTERVAL:-3600}"  # 1 hour in seconds
export SUPERDOTS_PROMPT_INTEGRATION="${SUPERDOTS_PROMPT_INTEGRATION:-true}"

# ============================================================================
# Utility Functions
# ============================================================================

# Check if SuperDots repository exists and is valid
_superdots_check_repo() {
    if [ ! -d "$SUPERDOTS_REPO_PATH" ]; then
        return 1
    fi

    if [ ! -d "$SUPERDOTS_REPO_PATH/.git" ]; then
        return 1
    fi

    return 0
}

# Get SuperDots status information
_superdots_get_status() {
    if ! _superdots_check_repo; then
        echo "not_initialized"
        return 1
    fi

    # Check if repository is dirty
    if cd "$SUPERDOTS_REPO_PATH" && git status --porcelain 2>/dev/null | grep -q .; then
        echo "dirty"
        return 0
    fi

    # Check if we're ahead/behind remote
    if cd "$SUPERDOTS_REPO_PATH" 2>/dev/null; then
        local ahead behind
        ahead=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "0")
        behind=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo "0")

        if [ "$ahead" -gt 0 ] && [ "$behind" -gt 0 ]; then
            echo "diverged"
        elif [ "$ahead" -gt 0 ]; then
            echo "ahead"
        elif [ "$behind" -gt 0 ]; then
            echo "behind"
        else
            echo "clean"
        fi
    else
        echo "unknown"
    fi
}

# Get last sync time
_superdots_last_sync() {
    local sync_file="$SUPERDOTS_CONFIG_DIR/.last_sync"
    if [ -f "$sync_file" ]; then
        cat "$sync_file"
    else
        echo "0"
    fi
}

# Update last sync time
_superdots_update_sync_time() {
    mkdir -p "$SUPERDOTS_CONFIG_DIR"
    date +%s > "$SUPERDOTS_CONFIG_DIR/.last_sync"
}

# Check if auto-sync is needed
_superdots_need_sync() {
    if [ "$SUPERDOTS_AUTO_SYNC" != "true" ]; then
        return 1
    fi

    local last_sync current_time
    last_sync=$(_superdots_last_sync)
    current_time=$(date +%s)

    if [ $((current_time - last_sync)) -gt "$SUPERDOTS_SYNC_INTERVAL" ]; then
        return 0
    fi

    return 1
}

# ============================================================================
# SuperDots Commands
# ============================================================================

# Quick status check
sdstatus() {
    local status
    status=$(_superdots_get_status)

    case "$status" in
        "not_initialized")
            echo "🔴 SuperDots: Not initialized"
            echo "   Run 'superdots init' to get started"
            ;;
        "clean")
            echo "🟢 SuperDots: Clean"
            ;;
        "dirty")
            echo "🟡 SuperDots: Local changes"
            echo "   Run 'superdots sync' to sync changes"
            ;;
        "ahead")
            echo "🔵 SuperDots: Ahead of remote"
            echo "   Run 'superdots sync' to push changes"
            ;;
        "behind")
            echo "🟠 SuperDots: Behind remote"
            echo "   Run 'superdots sync' to pull changes"
            ;;
        "diverged")
            echo "🟣 SuperDots: Diverged from remote"
            echo "   Run 'superdots sync --auto-resolve' to resolve"
            ;;
        *)
            echo "❓ SuperDots: Unknown status"
            ;;
    esac
}

# Quick sync
sdsync() {
    local message="$*"
    if [ -n "$message" ]; then
        superdots sync --message "$message"
    else
        superdots sync
    fi

    if [ $? -eq 0 ]; then
        _superdots_update_sync_time
    fi
}

# Quick add configuration
sdadd() {
    if [ $# -eq 0 ]; then
        echo "Usage: sdadd <path> [name]"
        return 1
    fi

    local path="$1"
    local name="$2"

    if [ -n "$name" ]; then
        superdots add "$path" --name "$name"
    else
        superdots add "$path"
    fi
}

# Quick deploy
sddeploy() {
    if [ $# -eq 0 ]; then
        superdots deploy --all
    else
        superdots deploy "$1"
    fi
}

# Edit SuperDots configuration
sdedit() {
    local config_file="$SUPERDOTS_CONFIG_DIR/config.yaml"

    if [ ! -f "$config_file" ]; then
        echo "Creating default SuperDots configuration..."
        mkdir -p "$SUPERDOTS_CONFIG_DIR"
        cat > "$config_file" << 'EOF'
# SuperDots Configuration
repository:
  path: ~/.superdots
  auto_init: true

sync:
  auto_sync: false
  sync_interval: 3600
  conflict_resolution: manual

deployment:
  prefer_symlinks: true
  backup_before_deploy: true

shell:
  prompt_integration: true
  auto_cd_hooks: true
EOF
    fi

    ${EDITOR:-vim} "$config_file"
}

# ============================================================================
# Auto-sync Hook
# ============================================================================

# Background sync function (non-blocking)
_superdots_auto_sync() {
    if _superdots_need_sync; then
        echo "🔄 SuperDots: Auto-syncing in background..."
        (
            superdots sync --quiet &> /dev/null
            if [ $? -eq 0 ]; then
                _superdots_update_sync_time
            fi
        ) &
        disown
    fi
}

# ============================================================================
# Prompt Integration
# ============================================================================

# Get prompt status indicator
_superdots_prompt_status() {
    if [ "$SUPERDOTS_PROMPT_INTEGRATION" != "true" ]; then
        return
    fi

    local status
    status=$(_superdots_get_status)

    case "$status" in
        "clean") echo "✓" ;;
        "dirty") echo "●" ;;
        "ahead") echo "↑" ;;
        "behind") echo "↓" ;;
        "diverged") echo "⇅" ;;
        "not_initialized") echo "○" ;;
        *) echo "?" ;;
    esac
}

# Add to PS1 for bash/zsh
if [ -n "$BASH_VERSION" ] || [ -n "$ZSH_VERSION" ]; then
    # Function to add SuperDots status to prompt
    _superdots_prompt() {
        local status_char
        status_char=$(_superdots_prompt_status)
        if [ -n "$status_char" ]; then
            echo " [SD:$status_char]"
        fi
    }

    # Add to existing PS1 if not already present
    if [[ "$PS1" != *"SD:"* ]]; then
        if [ -n "$BASH_VERSION" ]; then
            PS1='$(_superdots_prompt)'"$PS1"
        elif [ -n "$ZSH_VERSION" ]; then
            setopt PROMPT_SUBST
            PS1='$(_superdots_prompt)'"$PS1"
        fi
    fi
fi

# ============================================================================
# Directory Change Hooks
# ============================================================================

# Hook for directory changes
_superdots_cd_hook() {
    # Auto-sync when entering home directory
    if [ "$PWD" = "$HOME" ] && [ "$SUPERDOTS_AUTO_SYNC" = "true" ]; then
        _superdots_auto_sync
    fi

    # Check for local SuperDots repository
    if [ -f ".superdots-local" ]; then
        echo "🎯 Local SuperDots configuration found"
        echo "   Run 'superdots deploy --local' to apply local configs"
    fi
}

# Add CD hook for bash
if [ -n "$BASH_VERSION" ]; then
    if ! declare -f cd > /dev/null; then
        cd() {
            builtin cd "$@"
            _superdots_cd_hook
        }
    fi
fi

# Add CD hook for zsh
if [ -n "$ZSH_VERSION" ]; then
    autoload -U add-zsh-hook
    add-zsh-hook chpwd _superdots_cd_hook
fi

# ============================================================================
# Completion
# ============================================================================

# Basic completion for SuperDots commands
_superdots_completion() {
    local cur prev commands
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="init add remove list status deploy sync clone remote update"

    case "$prev" in
        superdots)
            COMPREPLY=($(compgen -W "$commands" -- "$cur"))
            ;;
        add)
            COMPREPLY=($(compgen -f -- "$cur"))
            ;;
        remove|deploy|update)
            if command -v superdots &> /dev/null; then
                local configs
                configs=$(superdots list --format json 2>/dev/null | grep -o '"name": *"[^"]*"' | cut -d'"' -f4)
                COMPREPLY=($(compgen -W "$configs" -- "$cur"))
            fi
            ;;
        remote)
            COMPREPLY=($(compgen -W "add remove list" -- "$cur"))
            ;;
        sync)
            COMPREPLY=($(compgen -W "--message --pull-only --push-only --auto-resolve" -- "$cur"))
            ;;
        *)
            COMPREPLY=()
            ;;
    esac
}

# Register completion
if [ -n "$BASH_VERSION" ]; then
    complete -F _superdots_completion superdots
    complete -F _superdots_completion sdadd
    complete -F _superdots_completion sddeploy
fi

# ============================================================================
# Aliases
# ============================================================================

# Short aliases for common operations
alias sd='superdots'
alias sds='sdstatus'
alias sdl='superdots list'
alias sdr='superdots remote'

# ============================================================================
# Welcome Message
# ============================================================================

# Show welcome message on first load
if [ -z "$SUPERDOTS_INTEGRATION_LOADED" ]; then
    export SUPERDOTS_INTEGRATION_LOADED=1

    echo "🚀 SuperDots shell integration loaded!"
    echo "   Quick commands: sdstatus, sdsync, sdadd, sddeploy"
    echo "   Full help: superdots --help"

    # Show initial status
    if _superdots_check_repo; then
        sdstatus
    else
        echo "   Get started: superdots init"
    fi

    # Auto-sync on shell startup if needed
    _superdots_auto_sync
fi
