#!/bin/bash
# Stop script for Personal RAG Journal

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping Personal RAG Journal..."

# Stop Django
if [ -f "logs/django.pid" ]; then
    DJANGO_PID=$(cat logs/django.pid)
    if ps -p $DJANGO_PID > /dev/null 2>&1; then
        echo "Stopping Django backend (PID: $DJANGO_PID)..."
        kill $DJANGO_PID
        sleep 2
        # Force kill if still running
        if ps -p $DJANGO_PID > /dev/null 2>&1; then
            kill -9 $DJANGO_PID
        fi
    fi
    rm -f logs/django.pid
fi

# Also kill any processes on port 8000 (in case PID file was lost)
if command -v lsof &> /dev/null; then
    for pid in $(lsof -ti:8000 2>/dev/null); do
        echo "Stopping process on port 8000 (PID: $pid)..."
        kill -9 $pid 2>/dev/null || true
    done
fi

# Stop React
if [ -f "logs/react.pid" ]; then
    REACT_PID=$(cat logs/react.pid)
    if ps -p $REACT_PID > /dev/null 2>&1; then
        echo "Stopping React frontend (PID: $REACT_PID)..."
        kill $REACT_PID
        sleep 2
        # Force kill if still running
        if ps -p $REACT_PID > /dev/null 2>&1; then
            kill -9 $REACT_PID
        fi
    fi
    rm -f logs/react.pid
fi

# Also kill any processes on port 3000 (in case PID file was lost)
if command -v lsof &> /dev/null; then
    for pid in $(lsof -ti:3000 2>/dev/null); do
        echo "Stopping process on port 3000 (PID: $pid)..."
        kill -9 $pid 2>/dev/null || true
    done
fi

# Create backup of entries
echo "Creating backup of entries..."
mkdir -p backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
tar -czf "backups/entries_backup_${TIMESTAMP}.tar.gz" entries/ 2>/dev/null || echo "Backup creation failed, continuing..."
echo "Backup created: backups/entries_backup_${TIMESTAMP}.tar.gz"

# Git sync (commit and push)
echo "Syncing entries with git..."
python3 scripts/git_sync.py --push || echo "Git push failed, but entries are saved locally"

echo "Stopped successfully."

