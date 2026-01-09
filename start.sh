#!/bin/bash
# Start script for Personal RAG Journal
# Easy-to-use startup script for non-technical users

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "🚀 Starting Personal RAG Journal"
echo "=========================================="
echo ""

# Check Python version
echo "📋 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed."
    echo "   Please install Python 3.11+ from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   ✓ Python $PYTHON_VERSION found"

# Activate virtual environment
echo ""
echo "📦 Setting up Python environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "   ✓ Using existing virtual environment"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "   ✓ Using existing virtual environment"
else
    echo "   Creating new virtual environment (this may take a minute)..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    echo "   ✓ Virtual environment created and dependencies installed"
fi

# Create necessary directories
echo ""
echo "📁 Setting up directories..."
mkdir -p logs
mkdir -p entries
mkdir -p local/embeddings
mkdir -p local/summaries
echo "   ✓ Directories ready"

# Check for Gemini API key
echo ""
echo "🔑 Checking configuration..."
if [ -f "config.json" ]; then
    if grep -q "gemini_api_key" config.json && ! grep -q '"gemini_api_key": ""' config.json && ! grep -q "YOUR_API_KEY" config.json; then
        echo "   ✓ Gemini API key configured"
    else
        echo "   ⚠️  Warning: Gemini API key not set in config.json"
        echo "      The app will work but AI features won't be available."
        echo "      See README.md for setup instructions."
    fi
else
    echo "   ⚠️  Warning: config.json not found"
fi

# Git sync (optional, non-blocking)
if [ -d ".git" ]; then
    echo ""
    echo "🔄 Syncing with Git (optional)..."
    python3 scripts/git_sync.py --pull 2>/dev/null || echo "   (Git sync skipped - not critical)"
fi

# Clean up any existing processes
echo ""
echo "🧹 Cleaning up..."
if command -v lsof &> /dev/null; then
    PIDS_8000=$(lsof -ti:8000 2>/dev/null || true)
    PIDS_3000=$(lsof -ti:3000 2>/dev/null || true)
    if [ -n "$PIDS_8000" ] || [ -n "$PIDS_3000" ]; then
        [ -n "$PIDS_8000" ] && kill -9 $PIDS_8000 2>/dev/null || true
        [ -n "$PIDS_3000" ] && kill -9 $PIDS_3000 2>/dev/null || true
        sleep 2
        echo "   ✓ Cleared ports 8000 and 3000"
    else
        echo "   ✓ Ports 8000 and 3000 are free"
    fi
fi

# Rebuild search index (quick check)
echo ""
echo "🔍 Preparing search index..."
cd backend
python3 manage.py shell << EOF 2>/dev/null
from api.rag_system import RAGSystem
rag = RAGSystem()
rag.rebuild_index()
EOF
cd ..
echo "   ✓ Search index ready"

# Generate weekly summary if needed (background, non-blocking)
echo ""
echo "📊 Checking for summaries..."
python3 scripts/weekly_summary.py > /dev/null 2>&1 || true
echo "   ✓ Summary check complete"

# Start Django backend
echo ""
echo "🐍 Starting backend server..."
cd backend
python3 manage.py runserver 8000 > ../logs/django.log 2>&1 &
DJANGO_PID=$!
echo $DJANGO_PID > ../logs/django.pid
cd ..
echo "   ✓ Backend starting (PID: $DJANGO_PID)"

# Wait for backend to initialize
echo "   Waiting for backend to initialize..."
sleep 5

# Start React frontend
echo ""
echo "⚛️  Starting frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "   Installing frontend dependencies (first time only, may take a minute)..."
    npm install --silent
fi
npm start > ../logs/react.log 2>&1 &
REACT_PID=$!
echo $REACT_PID > ../logs/react.pid
cd ..
echo "   ✓ Frontend starting (PID: $REACT_PID)"

# Save PIDs
echo "$DJANGO_PID" > logs/django.pid
echo "$REACT_PID" > logs/react.pid

# Wait a moment for servers to start
sleep 3

echo ""
echo "=========================================="
echo "✅ Personal RAG Journal is running!"
echo "=========================================="
echo ""
echo "📱 Open in your browser:"
echo "   http://localhost:3000"
echo ""
echo "🔧 Backend API:"
echo "   http://localhost:8000"
echo ""
echo "📝 Logs:"
echo "   Backend:  logs/django.log"
echo "   Frontend: logs/react.log"
echo ""
echo "⏹️  To stop the app:"
echo "   ./stop.sh"
echo "   (or press Ctrl+C in this terminal)"
echo ""
echo "=========================================="
echo ""
echo "💡 Tip: Press Ctrl+K to quickly create a new entry!"
echo ""
echo "Watching logs (Ctrl+C to stop watching, app continues running)..."
echo ""

# Tail logs (non-blocking, user can Ctrl+C)
tail -f logs/django.log logs/react.log 2>/dev/null || true

