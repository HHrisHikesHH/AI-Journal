#!/bin/bash
# Stop script for Personal RAG Journal
# Easy-to-use stop script for non-technical users

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "⏹️  Stopping Personal RAG Journal"
echo "=========================================="
echo ""

# Stop Django backend
echo "🐍 Stopping backend server..."
if [ -f "logs/django.pid" ]; then
    DJANGO_PID=$(cat logs/django.pid)
    if ps -p $DJANGO_PID > /dev/null 2>&1; then
        kill $DJANGO_PID 2>/dev/null || true
        sleep 2
        if ps -p $DJANGO_PID > /dev/null 2>&1; then
            kill -9 $DJANGO_PID 2>/dev/null || true
        fi
        echo "   ✓ Backend stopped"
    fi
    rm -f logs/django.pid
fi

# Also kill any processes on port 8000 (in case PID file was lost)
if command -v lsof &> /dev/null; then
    for pid in $(lsof -ti:8000 2>/dev/null); do
        kill -9 $pid 2>/dev/null || true
    done
fi

# Stop React frontend
echo ""
echo "⚛️  Stopping frontend..."
if [ -f "logs/react.pid" ]; then
    REACT_PID=$(cat logs/react.pid)
    if ps -p $REACT_PID > /dev/null 2>&1; then
        kill $REACT_PID 2>/dev/null || true
        sleep 2
        if ps -p $REACT_PID > /dev/null 2>&1; then
            kill -9 $REACT_PID 2>/dev/null || true
        fi
        echo "   ✓ Frontend stopped"
    fi
    rm -f logs/react.pid
fi

# Also kill any processes on port 3000 (in case PID file was lost)
if command -v lsof &> /dev/null; then
    for pid in $(lsof -ti:3000 2>/dev/null); do
        kill -9 $pid 2>/dev/null || true
    done
fi

# Git sync (optional, non-blocking)
if [ -d ".git" ]; then
    echo ""
    echo "🔄 Syncing with Git (optional)..."
    python3 scripts/git_sync.py --push 2>/dev/null || echo "   (Git sync skipped - not critical)"
fi

echo ""
echo "=========================================="
echo "✅ Personal RAG Journal stopped"
echo "=========================================="
echo ""
echo "💾 Your entries are saved in the 'entries/' folder"
echo "🔄 To start again, run: ./start.sh"
echo ""

