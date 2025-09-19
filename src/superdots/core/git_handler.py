#!/usr/bin/env python3
"""
Git repository handler for SuperDots.

This module provides functionality to manage Git repositories for storing
and synchronizing dotfiles and configuration files across different systems.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Union
from urllib.parse import urlparse

try:
    import git
    from git import Repo, Remote, InvalidGitRepositoryError, GitCommandError
    HAS_GITPYTHON = True
except ImportError:
    HAS_GITPYTHON = False
    git = None
    Repo = Remote = InvalidGitRepositoryError = GitCommandError = None

from ..utils.logger import get_logger
from ..utils.platform import platform_detector


class GitError(Exception):
    """Custom exception for Git-related errors."""
    pass


class GitHandler:
    """Handles Git repository operations for SuperDots."""

    def __init__(self, repo_path: Union[str, Path], remote_url: Optional[str] = None):
        """
        Initialize Git handler.

        Args:
            repo_path: Path to the Git repository
            remote_url: Optional remote repository URL
        """
        self.logger = get_logger(f"{__name__}.GitHandler")
        self.repo_path = Path(repo_path).resolve()
        self.remote_url = remote_url
        self.repo: Optional[Repo] = None

        if not HAS_GITPYTHON:
            self.logger.warning("GitPython not available, falling back to subprocess")

        self._ensure_repo_exists()

    def _ensure_repo_exists(self):
        """Ensure the repository exists and is properly initialized."""
        try:
            if self.repo_path.exists() and (self.repo_path / '.git').exists():
                if HAS_GITPYTHON:
                    self.repo = Repo(self.repo_path)
                self.logger.debug(f"Using existing repository at {self.repo_path}")
            else:
                self._init_repository()
        except Exception as e:
            raise GitError(f"Failed to initialize repository: {e}")

    def _init_repository(self):
        """Initialize a new Git repository."""
        try:
            self.repo_path.mkdir(parents=True, exist_ok=True)

            if HAS_GITPYTHON:
                self.repo = Repo.init(self.repo_path)
                self.logger.info(f"Initialized new Git repository at {self.repo_path}")
            else:
                self._run_git_command(['init'], cwd=self.repo_path)
                self.logger.info(f"Initialized new Git repository at {self.repo_path}")

            # Create initial structure
            self._create_initial_structure()

            # Add remote if provided
            if self.remote_url:
                self.add_remote('origin', self.remote_url)

        except Exception as e:
            raise GitError(f"Failed to initialize repository: {e}")

    def _create_initial_structure(self):
        """Create initial repository structure."""
        # Create basic directories
        dirs_to_create = [
            'configs',
            'scripts',
            'templates',
            'backups'
        ]

        for dir_name in dirs_to_create:
            dir_path = self.repo_path / dir_name
            dir_path.mkdir(exist_ok=True)

            # Create .gitkeep files to ensure directories are tracked
            gitkeep = dir_path / '.gitkeep'
            if not gitkeep.exists():
                gitkeep.touch()

        # Create README if it doesn't exist
        readme_path = self.repo_path / 'README.md'
        if not readme_path.exists():
            readme_content = self._generate_readme()
            readme_path.write_text(readme_content, encoding='utf-8')

        # Create .gitignore if it doesn't exist
        gitignore_path = self.repo_path / '.gitignore'
        if not gitignore_path.exists():
            gitignore_content = self._generate_gitignore()
            gitignore_path.write_text(gitignore_content, encoding='utf-8')

        # Initial commit
        self.add_all()
        self.commit("Initial SuperDots repository structure")

    def _generate_readme(self) -> str:
        """Generate default README content."""
        return """# SuperDots Configuration Repository

This repository contains dotfiles and configuration files managed by SuperDots.

## Structure

- `configs/`: Configuration files organized by category
- `scripts/`: Installation and setup scripts
- `templates/`: Configuration templates
- `backups/`: Backup copies of original files

## Usage

Use the `superdots` command-line tool to manage configurations:

```bash
# Initialize or sync configurations
superdots sync

# Add new configuration
superdots add ~/.vimrc

# List managed configurations
superdots list

# Deploy configurations
superdots deploy
```

## Platform Support

This repository supports synchronization across:
- Linux
- macOS
- Windows

Platform-specific configurations are automatically handled.
"""

    def _generate_gitignore(self) -> str:
        """Generate default .gitignore content."""
        return """# SuperDots gitignore

# Temporary files
*.tmp
*.temp
*~
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Cache files
.cache/
__pycache__/
*.pyc
*.pyo

# Editor files
.vscode/
.idea/
*.swp
*.swo

# OS specific
.Trash-*/
ehthumbs.db

# Sensitive files (customize as needed)
# **/secrets.*
# **/*_secret*
# **/*.key
# **/*.pem
"""

    def _run_git_command(self, args: List[str], cwd: Optional[Path] = None) -> str:
        """Run a Git command using subprocess."""
        if cwd is None:
            cwd = self.repo_path

        cmd = ['git'] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            raise GitError(f"Git command failed: {error_msg}")

    @property
    def is_valid_repo(self) -> bool:
        """Check if the repository is valid."""
        try:
            if HAS_GITPYTHON and self.repo:
                return not self.repo.bare
            else:
                self._run_git_command(['status', '--porcelain'])
                return True
        except:
            return False

    @property
    def is_dirty(self) -> bool:
        """Check if the repository has uncommitted changes."""
        try:
            if HAS_GITPYTHON and self.repo:
                return self.repo.is_dirty()
            else:
                output = self._run_git_command(['status', '--porcelain'])
                return bool(output.strip())
        except:
            return False

    @property
    def current_branch(self) -> str:
        """Get the current branch name."""
        try:
            if HAS_GITPYTHON and self.repo:
                return self.repo.active_branch.name
            else:
                return self._run_git_command(['branch', '--show-current'])
        except:
            return "main"

    @property
    def remotes(self) -> List[str]:
        """Get list of remote names."""
        try:
            if HAS_GITPYTHON and self.repo:
                return [remote.name for remote in self.repo.remotes]
            else:
                output = self._run_git_command(['remote'])
                return output.split('\n') if output else []
        except:
            return []

    def add_remote(self, name: str, url: str) -> bool:
        """Add a remote repository."""
        try:
            if HAS_GITPYTHON and self.repo:
                if name in [remote.name for remote in self.repo.remotes]:
                    self.repo.delete_remote(name)
                self.repo.create_remote(name, url)
            else:
                # Remove existing remote if it exists
                try:
                    self._run_git_command(['remote', 'remove', name])
                except GitError:
                    pass
                self._run_git_command(['remote', 'add', name, url])

            self.logger.info(f"Added remote '{name}': {url}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add remote '{name}': {e}")
            return False

    def remove_remote(self, name: str) -> bool:
        """Remove a remote repository."""
        try:
            if HAS_GITPYTHON and self.repo:
                self.repo.delete_remote(name)
            else:
                self._run_git_command(['remote', 'remove', name])

            self.logger.info(f"Removed remote '{name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove remote '{name}': {e}")
            return False

    def add_file(self, file_path: Union[str, Path]) -> bool:
        """Add a file to the staging area."""
        try:
            rel_path = Path(file_path).relative_to(self.repo_path)

            if HAS_GITPYTHON and self.repo:
                self.repo.index.add([str(rel_path)])
            else:
                self._run_git_command(['add', str(rel_path)])

            self.logger.debug(f"Added file to staging: {rel_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add file {file_path}: {e}")
            return False

    def add_all(self) -> bool:
        """Add all changes to the staging area."""
        try:
            if HAS_GITPYTHON and self.repo:
                self.repo.git.add(A=True)
            else:
                self._run_git_command(['add', '-A'])

            self.logger.debug("Added all changes to staging area")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add all changes: {e}")
            return False

    def commit(self, message: str, author_name: Optional[str] = None, author_email: Optional[str] = None) -> bool:
        """Create a commit with the given message."""
        try:
            # Set author if provided
            env = os.environ.copy()
            if author_name:
                env['GIT_AUTHOR_NAME'] = author_name
            if author_email:
                env['GIT_AUTHOR_EMAIL'] = author_email

            if HAS_GITPYTHON and self.repo:
                if author_name or author_email:
                    actor = git.Actor(author_name or "SuperDots", author_email or "superdots@localhost")
                    self.repo.index.commit(message, author=actor)
                else:
                    self.repo.index.commit(message)
            else:
                cmd = ['commit', '-m', message]
                result = subprocess.run(
                    ['git'] + cmd,
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    env=env
                )
                if result.returncode != 0:
                    # Check if it's just "nothing to commit"
                    if "nothing to commit" not in result.stdout:
                        raise GitError(result.stderr or result.stdout)

            self.logger.info(f"Created commit: {message}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create commit: {e}")
            return False

    def push(self, remote: str = 'origin', branch: Optional[str] = None) -> bool:
        """Push changes to remote repository."""
        try:
            if branch is None:
                branch = self.current_branch

            if HAS_GITPYTHON and self.repo:
                remote_obj = self.repo.remote(remote)
                remote_obj.push(branch)
            else:
                self._run_git_command(['push', remote, branch])

            self.logger.info(f"Pushed to {remote}/{branch}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to push to {remote}: {e}")
            return False

    def pull(self, remote: str = 'origin', branch: Optional[str] = None) -> bool:
        """Pull changes from remote repository."""
        try:
            if branch is None:
                branch = self.current_branch

            if HAS_GITPYTHON and self.repo:
                remote_obj = self.repo.remote(remote)
                remote_obj.pull(branch)
            else:
                self._run_git_command(['pull', remote, branch])

            self.logger.info(f"Pulled from {remote}/{branch}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to pull from {remote}: {e}")
            return False

    def fetch(self, remote: str = 'origin') -> bool:
        """Fetch changes from remote repository."""
        try:
            if HAS_GITPYTHON and self.repo:
                remote_obj = self.repo.remote(remote)
                remote_obj.fetch()
            else:
                self._run_git_command(['fetch', remote])

            self.logger.debug(f"Fetched from {remote}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to fetch from {remote}: {e}")
            return False

    def clone_repository(self, url: str, target_path: Path) -> bool:
        """Clone a repository from URL."""
        try:
            target_path = Path(target_path)
            if target_path.exists():
                shutil.rmtree(target_path)

            if HAS_GITPYTHON:
                Repo.clone_from(url, target_path)
            else:
                subprocess.run(
                    ['git', 'clone', url, str(target_path)],
                    check=True,
                    capture_output=True
                )

            self.logger.info(f"Cloned repository from {url} to {target_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clone repository: {e}")
            return False

    def get_status(self) -> Dict[str, List[str]]:
        """Get repository status."""
        status = {
            'staged': [],
            'modified': [],
            'untracked': [],
        }

        try:
            if HAS_GITPYTHON and self.repo:
                # Staged files
                status['staged'] = [item.a_path for item in self.repo.index.diff("HEAD")]
                # Modified files
                status['modified'] = [item.a_path for item in self.repo.index.diff(None)]
                # Untracked files
                status['untracked'] = self.repo.untracked_files
            else:
                output = self._run_git_command(['status', '--porcelain'])
                for line in output.split('\n'):
                    if not line:
                        continue

                    status_code = line[:2]
                    file_path = line[3:]

                    if status_code[0] in ['A', 'M', 'D', 'R', 'C']:
                        status['staged'].append(file_path)
                    if status_code[1] in ['M', 'D']:
                        status['modified'].append(file_path)
                    if status_code == '??':
                        status['untracked'].append(file_path)
        except Exception as e:
            self.logger.error(f"Failed to get repository status: {e}")

        return status

    def get_commits(self, max_count: int = 10) -> List[Dict[str, str]]:
        """Get recent commits."""
        commits = []

        try:
            if HAS_GITPYTHON and self.repo:
                for commit in self.repo.iter_commits(max_count=max_count):
                    commits.append({
                        'hash': commit.hexsha[:8],
                        'message': commit.message.strip(),
                        'author': str(commit.author),
                        'date': commit.committed_datetime.isoformat(),
                    })
            else:
                output = self._run_git_command([
                    'log', f'-{max_count}', '--pretty=format:%h|%s|%an|%ai'
                ])
                for line in output.split('\n'):
                    if line:
                        parts = line.split('|', 3)
                        if len(parts) == 4:
                            commits.append({
                                'hash': parts[0],
                                'message': parts[1],
                                'author': parts[2],
                                'date': parts[3],
                            })
        except Exception as e:
            self.logger.error(f"Failed to get commits: {e}")

        return commits

    def has_conflicts(self) -> bool:
        """Check if repository has merge conflicts."""
        try:
            if HAS_GITPYTHON and self.repo:
                return len(list(self.repo.index.unmerged_blobs())) > 0
            else:
                output = self._run_git_command(['status', '--porcelain'])
                return 'UU' in output or 'AA' in output
        except:
            return False

    def reset_hard(self, commit: str = 'HEAD') -> bool:
        """Reset repository to a specific commit."""
        try:
            if HAS_GITPYTHON and self.repo:
                self.repo.git.reset('--hard', commit)
            else:
                self._run_git_command(['reset', '--hard', commit])

            self.logger.warning(f"Reset repository to {commit}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to reset repository: {e}")
            return False

    def create_branch(self, branch_name: str, checkout: bool = True) -> bool:
        """Create a new branch."""
        try:
            if HAS_GITPYTHON and self.repo:
                new_branch = self.repo.create_head(branch_name)
                if checkout:
                    new_branch.checkout()
            else:
                args = ['checkout', '-b', branch_name] if checkout else ['branch', branch_name]
                self._run_git_command(args)

            self.logger.info(f"Created branch '{branch_name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create branch '{branch_name}': {e}")
            return False

    def checkout_branch(self, branch_name: str) -> bool:
        """Checkout a branch."""
        try:
            if HAS_GITPYTHON and self.repo:
                self.repo.heads[branch_name].checkout()
            else:
                self._run_git_command(['checkout', branch_name])

            self.logger.info(f"Checked out branch '{branch_name}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to checkout branch '{branch_name}': {e}")
            return False
