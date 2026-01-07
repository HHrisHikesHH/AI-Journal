#!/bin/bash
# Environment check script

echo "Checking environment..."

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Python: $PYTHON_VERSION"
else
    echo "✗ Python 3 not found"
    exit 1
fi

# Check pip
if command -v pip3 &> /dev/null; then
    echo "✓ pip3 found"
else
    echo "✗ pip3 not found"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✓ Node.js: $NODE_VERSION"
else
    echo "✗ Node.js not found"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✓ npm: $NPM_VERSION"
else
    echo "✗ npm not found"
    exit 1
fi

# Check virtual environment
if [ -d "venv" ] || [ -d ".venv" ]; then
    echo "✓ Virtual environment found"
else
    echo "⚠ Virtual environment not found (will be created)"
fi

# Check model file
MODEL_PATH="local/models/llama-3-8b-instruct.gguf"
if [ -f "$MODEL_PATH" ]; then
    echo "✓ LLM model found: $MODEL_PATH"
else
    echo "⚠ LLM model not found: $MODEL_PATH"
    echo "  Please download a model and place it in local/models/"
    echo "  Recommended: LLaMA 3 8B Instruct (GGUF format)"
    echo "  Download from: https://huggingface.co/models?search=llama-3-8b-instruct-gguf"
fi

# Check entries directory
if [ -d "entries" ]; then
    ENTRY_COUNT=$(find entries -name "*.json" | wc -l)
    echo "✓ Entries directory found ($ENTRY_COUNT entries)"
else
    echo "⚠ Entries directory not found (will be created)"
fi

echo ""
echo "Environment check complete!"

