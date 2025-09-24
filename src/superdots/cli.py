#!/usr/bin/env python3
"""
Command-line interface for SuperDots.

This module provides the main CLI commands for managing dotfiles and configurations
across different platforms using Git repositories for synchronization.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Optional

import click
from rich.console import _STD_STREAMS_OUTPUT, Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from .core.config import ConfigManager, ConfigFile, ConfigStatus, ConfigType, OSType
from .core.sync import SyncManager, SyncStatus, ConflictResolution
from .core.git_handler import GitHandler, GitError
from .utils.logger import get_logger, setup_logging
from .utils.platform import platform_detector
from .utils.path import normalize_path

# Rich console for formatted output
console = Console()


def get_default_repo_path() -> Path:
    """Get the default repository path."""
    return platform_detector.home_dir / '.superdots'


def initialize_managers(repo_path: Path, remote_url: Optional[str] = None):
    """Initialize configuration and sync managers."""
    try:
        git_handler = GitHandler(repo_path, remote_url)
        config_manager = ConfigManager(repo_path)
        sync_manager = SyncManager(config_manager, git_handler)
        return config_manager, sync_manager, git_handler
    except Exception as e:
        console.print(f"[red]Failed to initialize managers: {e}[/red]")
        sys.exit(1)


def format_config_table(configs: List[ConfigFile]) -> tuple[Table, int]:
    """Format configurations as a rich table."""
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Source Path", style="magenta")
    table.add_column("Platforms", style="blue")
    
    total = 0
    for config in configs:
        # Format status with color
        status_color = {
            ConfigStatus.TRACKED: "green",
            ConfigStatus.MODIFIED: "yellow",
            ConfigStatus.MISSING: "red",
            ConfigStatus.CONFLICTED: "red bold",
            ConfigStatus.UNTRACKED: "dim",
        }

        status_text = f"[{status_color.get(config.status, 'white')}]{config.status.value}[/]"
        platforms_text = ", ".join([p.value for p in config.platforms])
        source_path = config.source_paths.get(platform_detector.os_type) 
        if not source_path:
            continue
        
        total += 1
        table.add_row(
            config.name,
            config.config_type.value,
            status_text,
            str(source_path),
            platforms_text
        )

    return table, total


def format_sync_result(result) -> None:
    """Format and display sync result."""
    if result.status == SyncStatus.SUCCESS:
        console.print(f"[green]✓ {result.message}[/green]")
    elif result.status == SyncStatus.CONFLICT:
        console.print(f"[yellow]⚠ {result.message}[/yellow]")
        if result.conflicts:
            console.print("[yellow]Conflicts:[/yellow]")
            for conflict in result.conflicts:
                console.print(f"  - {conflict}")
    elif result.status == SyncStatus.ERROR:
        console.print(f"[red]✗ Sync failed[/red]")
        if result.errors:
            console.print("[red]Errors:[/red]")
            for error in result.errors:
                console.print(f"  - {error}")
    elif result.status == SyncStatus.PARTIAL:
        console.print(f"[yellow]⚠ Partial success: {result.configs_synced} synced, {result.configs_failed} failed[/yellow]")
    else:
        console.print(f"[dim]{result.message}[/dim]")


# Main CLI group
@click.group()
@click.option('--repo-path', type=click.Path(path_type=Path),
              default=get_default_repo_path(),
              help='Path to SuperDots repository')
@click.option('--remote-url', type=str, help='Remote repository URL')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--log-file', type=click.Path(path_type=Path), help='Log file path')
@click.pass_context
def cli(ctx, repo_path: Path, remote_url: Optional[str], verbose: bool, log_file: Optional[Path]):
    """SuperDots - Cross-platform dotfiles and configuration management."""
    ctx.ensure_object(dict)

    # Setup logging
    setup_logging(
        level='DEBUG' if verbose else 'INFO',
        log_file=log_file,
        verbose=verbose
    )

    # Store common options in context
    ctx.obj['repo_path'] = repo_path
    ctx.obj['remote_url'] = remote_url
    ctx.obj['verbose'] = verbose


# Initialize command
@cli.command()
@click.option('--remote-url', type=str, help='Remote repository URL')
@click.option('--force', is_flag=True, help='Force initialization even if directory exists')
@click.pass_context
def init(ctx, remote_url: Optional[str], force: bool):
    """Initialize a new SuperDots repository."""
    repo_path = ctx.obj['repo_path']

    if repo_path.exists() and not force:
        if not Confirm.ask(f"Directory {repo_path} already exists. Continue?"):
            console.print("Initialization cancelled.")
            return

    # Use remote URL from option or context
    if not remote_url:
        remote_url = ctx.obj['remote_url']

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Initializing SuperDots repository...\n", total=None)

            config_manager, sync_manager, git_handler = initialize_managers(repo_path, remote_url)

            progress.update(task, description="Repository initialized successfully!")

        console.print(Panel(
            f"[green]✓ SuperDots repository initialized at:[/green]\n"
            f"[cyan]{repo_path}[/cyan]\n\n"
            f"[dim]Platform: {platform_detector.os_type.value}[/dim]",
            title="Initialization Complete"
        ))

        if remote_url:
            console.print(f"[green]Remote repository configured:[/green] {remote_url}")
        else:
            console.print("[yellow]No remote repository configured. Use 'superdots remote add <url>' to add one.[/yellow]")

    except Exception as e:
        console.print(f"[red]Failed to initialize repository: {e}[/red]")
        sys.exit(1)


# Add command
@cli.command()
@click.argument('source_path', type=click.Path(exists=True, path_type=Path))
@click.option('--extra_paths', type=(click.Choice(['linux', 'darwin', 'windows']), click.Path(exists=False, path_type=Path)), multiple=True, help='Optional additional source paths. <os> <path>')
@click.option('--name', type=str, help='Custom name for the configuration')
@click.option('--description', type=str, help='Description of the configuration')
@click.option('--tags', type=str, multiple=True, help='Tags for categorization')
@click.option('--platforms', type=click.Choice(['linux', 'darwin', 'windows']),
              multiple=True, help='Target platforms')
@click.option('--use-symlink', is_flag=True, help='Use symlinks instead of file copies')
@click.option('--force', is_flag=True, help='Overwrite existing configurations')
@click.pass_context
def add(ctx, source_path: Path, extra_paths: tuple[tuple[str, Path], ...], name: Optional[str], description: Optional[str],
        tags: tuple, platforms: tuple, use_symlink: bool, force: bool):
    """Add a configuration file or directory to management."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    # Convert platforms to OSType
    source_path = normalize_path(source_path, platform_detector.home_dir)
    source_paths = {platform_detector.os_type: source_path}
    if not extra_paths:
        for p in platforms:
            source_paths[OSType(p)] = source_path
    else:
        for platform, path in extra_paths:
            source_paths[OSType(platform)] = normalize_path(path, platform_detector.home_dir)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            console.print(source_path, source_paths)
            task = progress.add_task(f"Adding configuration {name or source_path.name}...", total=None)

            success = config_manager.add_config(
                source_paths=source_paths,
                name=name,
                description=description,
                tags=list(tags) if tags else [],
                use_symlink=use_symlink,
                force=force
            )

            if success:
                progress.update(task, description="Configuration added successfully!")
                console.print(f"[green]✓ Added configuration '[cyan]{name or source_path.name}[/cyan]'[/green]")
            else:
                console.print(f"[red]✗ Failed to add configuration[/red]")
                sys.exit(1)

    except Exception as e:
        console.print(f"[red]Failed to add configuration: {e}[/red]")
        sys.exit(1)


# Remove command
@cli.command()
@click.argument('name', type=str)
@click.option('--keep-files', is_flag=True, help='Keep files in repository')
@click.option('--force', is_flag=True, help='Skip confirmation prompt')
@click.pass_context
def remove(ctx, name: str, keep_files: bool, force: bool):
    """Remove a configuration from management."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    # Check if configuration exists
    config = config_manager.get_config(name)
    if not config:
        console.print(f"[red]Configuration '[cyan]{name}[/cyan]' not found[/red]")
        sys.exit(1)

    # Confirmation
    if not force:
        console.print(f"Configuration: [cyan]{config.name}[/cyan]")
        console.print(f"Source path: [magenta]{config.source_path}[/magenta]")
        console.print(f"Repository path: [magenta]{config.repo_path}[/magenta]")

        if not Confirm.ask("Are you sure you want to remove this configuration?"):
            console.print("Remove cancelled.")
            return

    try:
        if config_manager.remove_config(name, keep_files=keep_files):
            console.print(f"[green]✓ Removed configuration '[cyan]{name}[/cyan]'[/green]")
        else:
            console.print(f"[red]✗ Failed to remove configuration[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Failed to remove configuration: {e}[/red]")
        sys.exit(1)


# List command
@cli.command()
@click.option('--platform', type=click.Choice(['linux', 'darwin', 'windows']),
              help='Filter by platform')
@click.option('--status', type=click.Choice(['tracked', 'modified', 'missing', 'conflicted', 'untracked']),
              help='Filter by status')
@click.option('--tags', type=str, multiple=True, help='Filter by tags')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']),
              default='table', help='Output format')
@click.pass_context
def list(ctx, platform: Optional[str], status: Optional[str], tags: tuple, output_format: str):
    """List managed configurations."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    # Apply filters
    platform_filter = OSType(platform) if platform else None
    status_filter = ConfigStatus(status) if status else None

    configs = config_manager.list_configs(
        platform=platform_filter,
        status=status_filter,
        tags=list(tags) if tags else None
    )

    if not configs:
        console.print("[dim]No configurations found.[/dim]")
        return

    if output_format == 'json':
        # JSON output
        data = [config.to_dict() for config in configs]
        console.print(json.dumps(data, indent=2, default=str))
    else:
        # Table output
        table, total = format_config_table(configs)
        console.print(table)
        console.print(f"\n[dim]Total: {total} configurations[/dim]")


# Status command
@cli.command()
@click.pass_context
def status(ctx):
    """Show status of configurations and repository."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    try:
        # Get sync status
        sync_status = sync_manager.get_sync_status()

        # Repository status
        repo_info = sync_status['repository']
        console.print(Panel(
            f"[cyan]Path:[/cyan] {repo_info['path']}\n"
            f"[cyan]Branch:[/cyan] {repo_info['current_branch']}\n"
            f"[cyan]Dirty:[/cyan] {'Yes' if repo_info['is_dirty'] else 'No'}\n"
            f"[cyan]Remotes:[/cyan] {', '.join(repo_info['remotes']) if repo_info['remotes'] else 'None'}",
            title="Repository Status"
        ))

        # Configuration status
        config_status = sync_status['configurations']
        status_table = Table(show_header=True, header_style="bold blue")
        status_table.add_column("Status", style="cyan")
        status_table.add_column("Count", style="green")
        status_table.add_column("Configurations", style="magenta")

        for status_name, config_names in config_status.items():
            if config_names:
                status_table.add_row(
                    status_name.title(),
                    str(len(config_names)),
                    ", ".join(config_names[:5]) + ("..." if len(config_names) > 5 else "")
                )

        console.print(status_table)

        # Platform info
        platform_info = sync_status['platform']
        console.print(f"\n[dim]Platform: {platform_info['current']} | "
                     f"Symlinks: {'Supported' if platform_info['can_symlink'] else 'Not supported'}[/dim]")

    except Exception as e:
        console.print(f"[red]Failed to get status: {e}[/red]")
        sys.exit(1)


# Deploy command
@cli.command()
@click.argument('name', type=str, required=False)
@click.option('--all', 'deploy_all', is_flag=True, help='Deploy all configurations')
@click.option('--platform', type=click.Choice(['linux', 'darwin', 'windows']),
              help='Target platform')
@click.option('--force', is_flag=True, help='Overwrite existing files')
@click.pass_context
def deploy(ctx, name: Optional[str], deploy_all: bool, platform: Optional[str], force: bool):
    """Deploy configuration(s) to their target locations."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    if not name and not deploy_all:
        console.print("[red]Specify configuration name or use --all flag[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    try:
        if deploy_all:
            target_platform = OSType(platform) if platform else None

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Deploying configurations...", total=None)

                deployed = config_manager.deploy_all(platform=target_platform, force=force)

                progress.update(task, description=f"Deployed {deployed} configurations!")

            console.print(f"[green]✓ Deployed {deployed} configurations[/green]")
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Deploying {name}...", total=None)

                success = config_manager.deploy_config(name, force=force)

                if success:
                    progress.update(task, description=f"Deployed {name} successfully!")
                    console.print(f"[green]✓ Deployed configuration '[cyan]{name}[/cyan]'[/green]")
                else:
                    console.print(f"[red]✗ Failed to deploy configuration[/red]")
                    sys.exit(1)

    except Exception as e:
        console.print(f"[red]Failed to deploy: {e}[/red]")
        sys.exit(1)


# Sync command
@cli.command()
@click.option('--pull-only', is_flag=True, help='Only pull changes from remote')
@click.option('--push-only', is_flag=True, help='Only push changes to remote')
@click.option('--message', '-m', type=str, help='Commit message')
@click.option('--auto-resolve', is_flag=True, help='Automatically resolve conflicts')
@click.option('--no-deploy', is_flag=True, help='Skip deployment after pull')
@click.pass_context
def sync(ctx, pull_only: bool, push_only: bool, message: Optional[str],
         auto_resolve: bool, no_deploy: bool):
    """Synchronize configurations with remote repository."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            if pull_only:
                task = progress.add_task("Pulling changes...", total=None)
                result = sync_manager.pull_changes(auto_resolve=auto_resolve)

            elif push_only:
                task = progress.add_task("Pushing changes...", total=None)
                result = sync_manager.push_changes(message=message)

            else:
                task = progress.add_task("Synchronizing...", total=None)
                result = sync_manager.sync(
                    pull_first=True,
                    auto_commit=True,
                    commit_message=message,
                    auto_resolve=auto_resolve
                )

            progress.update(task, description="Sync completed!")

        format_sync_result(result)

    except Exception as e:
        console.print(f"[red]Failed to sync: {e}[/red]")
        sys.exit(1)


# Remote commands group
@cli.group()
def remote():
    """Manage remote repositories."""
    pass


@remote.command('add')
@click.argument('name', type=str)
@click.argument('url', type=str)
@click.pass_context
def remote_add(ctx, name: str, url: str):
    """Add a remote repository."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    try:
        if git_handler.add_remote(name, url):
            console.print(f"[green]✓ Added remote '[cyan]{name}[/cyan]': {url}[/green]")
        else:
            console.print(f"[red]✗ Failed to add remote[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Failed to add remote: {e}[/red]")
        sys.exit(1)


@remote.command('remove')
@click.argument('name', type=str)
@click.pass_context
def remote_remove(ctx, name: str):
    """Remove a remote repository."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    try:
        if git_handler.remove_remote(name):
            console.print(f"[green]✓ Removed remote '[cyan]{name}[/cyan]'[/green]")
        else:
            console.print(f"[red]✗ Failed to remove remote[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Failed to remove remote: {e}[/red]")
        sys.exit(1)


@remote.command('list')
@click.pass_context
def remote_list(ctx):
    """List remote repositories."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    remotes = git_handler.remotes
    if not remotes:
        console.print("[dim]No remote repositories configured.[/dim]")
    else:
        console.print("[cyan]Remote repositories:[/cyan]")
        for remote in remotes:
            console.print(f"  - {remote}")


# Clone command
@cli.command()
@click.argument('url', type=str)
@click.option('--path', type=click.Path(path_type=Path), help='Target path')
@click.pass_context
def clone(ctx, url: str, path: Optional[Path]):
    """Clone a SuperDots repository."""
    if not path:
        path = ctx.obj['repo_path']

    if path.exists():
        if not Confirm.ask(f"Directory {path} already exists. Overwrite?"):
            console.print("Clone cancelled.")
            return

    try:
        # Initialize with the URL to clone
        config_manager, sync_manager, git_handler = initialize_managers(path)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Cloning repository...", total=None)

            if sync_manager.clone_repository(url, path):
                progress.update(task, description="Repository cloned successfully!")
                console.print(f"[green]✓ Cloned repository to [cyan]{path}[/cyan][/green]")
            else:
                console.print("[red]✗ Failed to clone repository[/red]")
                sys.exit(1)

    except Exception as e:
        console.print(f"[red]Failed to clone repository: {e}[/red]")
        sys.exit(1)


# Update command
@cli.command()
@click.argument('name', type=str, required=False)
@click.option('--all', 'update_all', is_flag=True, help='Update all configurations')
@click.pass_context
def update(ctx, name: Optional[str], update_all: bool):
    """Update configuration(s) from their source locations."""
    repo_path = ctx.obj['repo_path']

    if not repo_path.exists():
        console.print("[red]Repository not initialized. Run 'superdots init' first.[/red]")
        sys.exit(1)

    if not name and not update_all:
        console.print("[red]Specify configuration name or use --all flag[/red]")
        sys.exit(1)

    config_manager, sync_manager, git_handler = initialize_managers(repo_path)

    try:
        if update_all:
            updated = 0
            failed = 0

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Updating configurations...", total=None)

                for config_name in config_manager._configs:
                    if config_manager.update_config(config_name):
                        updated += 1
                    else:
                        failed += 1

                progress.update(task, description=f"Updated {updated} configurations!")

            console.print(f"[green]✓ Updated {updated} configurations[/green]")
            if failed > 0:
                console.print(f"[yellow]⚠ {failed} configurations failed to update[/yellow]")
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Updating {name}...", total=None)

                if config_manager.update_config(name):
                    progress.update(task, description=f"Updated {name} successfully!")
                    console.print(f"[green]✓ Updated configuration '[cyan]{name}[/cyan]'[/green]")
                else:
                    console.print(f"[red]✗ Failed to update configuration[/red]")
                    sys.exit(1)

    except Exception as e:
        console.print(f"[red]Failed to update: {e}[/red]")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()
