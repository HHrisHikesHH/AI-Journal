#!/bin/bash
# Start script for Personal RAG Journal

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Personal RAG Journal..."

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Git sync (pull)
echo "Syncing with git..."
python3 scripts/git_sync.py --pull || echo "Git pull failed, continuing..."

# Kill any existing processes on ports 8000 and 3000
echo "Cleaning up any existing processes..."
if command -v lsof &> /dev/null; then
    for pid in $(lsof -ti:8000 2>/dev/null); do
        echo "Killing process on port 8000 (PID: $pid)..."
        kill -9 $pid 2>/dev/null || true
    done
    for pid in $(lsof -ti:3000 2>/dev/null); do
        echo "Killing process on port 3000 (PID: $pid)..."
        kill -9 $pid 2>/dev/null || true
    done
    sleep 2
fi

# Rebuild index
echo "Rebuilding search index..."
cd backend
python3 manage.py shell << EOF
from api.rag_system import RAGSystem
rag = RAGSystem()
rag.rebuild_index()
EOF
cd ..

# Generate weekly summary if it's a new week (runs in background)
echo "Checking for weekly summary..."
python3 scripts/weekly_summary.py > /dev/null 2>&1 || echo "Weekly summary generation skipped (will run on schedule)"

# Start Django backend
echo "Starting Django backend..."
cd backend
# Suppress llama-cpp cleanup warnings
python3 manage.py runserver 8000 > ../logs/django.log 2>&1 &
DJANGO_PID=$!
echo $DJANGO_PID > ../logs/django.pid
cd ..

# Wait a moment for Django to start
sleep 3

# Start React frontend
echo "Starting React frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi
npm start > ../logs/react.log 2>&1 &
REACT_PID=$!
echo $REACT_PID > ../logs/react.pid
cd ..

# Create logs directory if it doesn't exist
mkdir -p logs

# Save PIDs
echo "Backend PID: $DJANGO_PID"
echo "Frontend PID: $REACT_PID"
echo "$DJANGO_PID" > logs/django.pid
echo "$REACT_PID" > logs/react.pid

echo ""
echo "=========================================="
echo "Personal RAG Journal is starting..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Logs:"
echo "  Backend: logs/django.log"
echo "  Frontend: logs/react.log"
echo ""
echo "To stop: ./stop.sh"
echo "=========================================="

# Tail logs
tail -f logs/django.log logs/react.log

