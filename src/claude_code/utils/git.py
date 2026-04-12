"""
Git operations for Claude Code CLI
"""

import os
import subprocess
from typing import Optional
from dataclasses import dataclass


@dataclass
class GitStatus:
    """Git status result"""
    branch: str
    staged: list[str]
    modified: list[str]
    untracked: list[str]
    conflicted: list[str]
    is_dirty: bool


@dataclass
class GitDiff:
    """Git diff result"""
    files: list[dict]
    has_changes: bool


def is_git_repo(path: str = ".") -> bool:
    """Check if path is a git repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_git_status(path: str = ".") -> Optional[GitStatus]:
    """Get git status."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        
        staged = []
        modified = []
        untracked = []
        conflicted = []
        
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            file_path = line[3:]
            
            if "U" in status or ("UU" in status):
                conflicted.append(file_path)
            elif status.strip() == "":
                untracked.append(file_path)
            elif status[0] in ("M", "A", "D", "R", "C"):
                staged.append(file_path)
            elif status[1] == "M":
                modified.append(file_path)
        
        return GitStatus(
            branch=get_git_branch(path) or "unknown",
            staged=staged,
            modified=modified,
            untracked=untracked,
            conflicted=conflicted,
            is_dirty=bool(staged or modified or untracked or conflicted),
        )
    except Exception:
        return None


def get_git_branch(path: str = ".") -> Optional[str]:
    """Get current git branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def get_git_diff(path: str = ".", staged: bool = False) -> Optional[GitDiff]:
    """Get git diff."""
    try:
        args = ["git", "diff", "--stat"]
        if staged:
            args.append("--staged")
        
        result = subprocess.run(
            args,
            cwd=path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return None
        
        files = []
        for line in result.stdout.strip().split("\n"):
            if line and "|" in line:
                parts = line.split("|")
                if len(parts) == 2:
                    files.append({
                        "file": parts[0].strip(),
                        "changes": parts[1].strip(),
                    })
        
        return GitDiff(
            files=files,
            has_changes=len(files) > 0,
        )
    except Exception:
        return None


def git_add(path: str, files: list[str]) -> bool:
    """Stage files for commit."""
    try:
        result = subprocess.run(
            ["git", "add"] + files,
            cwd=path,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def git_commit(path: str, message: str) -> bool:
    """Create a git commit."""
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=path,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def git_log(path: str, max_count: int = 10) -> list[dict]:
    """Get git log."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{max_count}", "--oneline", "--pretty=format:%H|%s|%an|%ad"],
            cwd=path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                if len(parts) >= 4:
                    commits.append({
                        "hash": parts[0][:7],
                        "message": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                    })
        
        return commits
    except Exception:
        return []
