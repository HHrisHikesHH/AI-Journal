#!/usr/bin/env python3
"""
Git sync script for journal entries.
Handles pull, commit, and push operations safely.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRIES_DIR = PROJECT_ROOT / 'entries'

def run_git_command(cmd, check=True):
    """Run a git command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout + e.stderr, e.returncode

def git_pull():
    """Pull latest changes with rebase."""
    print("Pulling latest changes...")
    stdout, returncode = run_git_command('git pull --rebase', check=False)
    if returncode != 0:
        if 'CONFLICT' in stdout or 'conflict' in stdout.lower():
            print("Warning: Merge conflicts detected. Please resolve manually.")
            return False
        elif 'fatal: not a git repository' in stdout:
            print("Warning: Not a git repository. Skipping pull.")
            return True
        else:
            print(f"Pull completed with warnings: {stdout}")
    else:
        print("Pull successful.")
    return True

def git_status():
    """Check git status."""
    stdout, returncode = run_git_command('git status --porcelain', check=False)
    if returncode != 0:
        return []
    return [line for line in stdout.split('\n') if line.strip()]

def git_commit_and_push():
    """Commit and push changes."""
    # Check if we're in a git repo
    stdout, returncode = run_git_command('git rev-parse --git-dir', check=False)
    if returncode != 0:
        print("Not a git repository. Skipping commit/push.")
        return True
    
    # Check for changes
    status_lines = git_status()
    entry_changes = [line for line in status_lines if 'entries/' in line]
    
    if not entry_changes:
        print("No entry changes to commit.")
        return True
    
    # Add entry files
    print("Staging entry files...")
    for line in entry_changes:
        # Extract filename from status line (format: " M entries/file.json" or "?? entries/file.json")
        parts = line.split()
        if len(parts) >= 2:
            filename = parts[-1]
            run_git_command(f'git add "{filename}"', check=False)
    
    # Commit
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    commit_msg = f"Journal entries update - {timestamp}"
    print("Committing changes...")
    stdout, returncode = run_git_command(
        f'git commit -m "{commit_msg}"',
        check=False
    )
    
    if returncode != 0:
        if 'nothing to commit' in stdout.lower():
            print("No changes to commit.")
            return True
        else:
            print(f"Commit failed: {stdout}")
            return False
    
    print("Commit successful.")
    
    # Push
    print("Pushing to remote...")
    stdout, returncode = run_git_command('git push', check=False)
    
    if returncode != 0:
        if 'fatal: no upstream branch' in stdout:
            print("Warning: No upstream branch set. Changes committed locally.")
            return True
        elif 'Could not resolve host' in stdout or 'Network is unreachable' in stdout:
            print("Warning: Network unavailable. Changes committed locally, will push on next sync.")
            return True
        else:
            print(f"Push failed: {stdout}")
            return False
    
    print("Push successful.")
    return True

def main():
    parser = argparse.ArgumentParser(description='Git sync for journal entries')
    parser.add_argument('--pull', action='store_true', help='Pull latest changes')
    parser.add_argument('--push', action='store_true', help='Commit and push changes')
    
    args = parser.parse_args()
    
    if args.pull:
        success = git_pull()
        sys.exit(0 if success else 1)
    elif args.push:
        success = git_commit_and_push()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()

