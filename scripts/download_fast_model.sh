#!/bin/bash
# Download script for fast LLM models
# This script downloads a fast, lightweight model optimized for speed

set -e

MODELS_DIR="local/models"
mkdir -p "$MODELS_DIR"

echo "=========================================="
echo "Fast LLM Model Downloader"
echo "=========================================="
echo ""
echo "Choose a model:"
echo "1) TinyLlama 1.1B (~700MB) - FASTEST, good for simple patterns"
echo "2) Phi-2 2.7B (~1.6GB) - Fast, better quality"
echo "3) Qwen2.5-1.5B (~1GB) - Good balance"
echo ""
read -p "Enter choice (1-3) [default: 1]: " choice
choice=${choice:-1}

cd "$MODELS_DIR"

case $choice in
    1)
        echo "Downloading TinyLlama 1.1B..."
        wget -O phi-2.Q4_K_M.gguf \
            https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
        echo "✅ TinyLlama downloaded successfully!"
        ;;
    2)
        echo "Downloading Phi-2 2.7B..."
        wget -O phi-2.Q4_K_M.gguf \
            https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf
        echo "✅ Phi-2 downloaded successfully!"
        ;;
    3)
        echo "Downloading Qwen2.5-1.5B..."
        wget -O phi-2.Q4_K_M.gguf \
            https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct.Q4_K_M.gguf
        echo "✅ Qwen2.5 downloaded successfully!"
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "Model downloaded to: $(pwd)/phi-2.Q4_K_M.gguf"
echo "File size: $(du -h phi-2.Q4_K_M.gguf | cut -f1)"
echo ""
echo "✅ Done! The model is ready to use."
echo "   Make sure config.json points to: local/models/phi-2.Q4_K_M.gguf"

