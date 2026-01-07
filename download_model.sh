#!/bin/bash
# Quick script to download a recommended LLM model

MODEL_DIR="/home/htadmin/Documents/rag_project/local/models"
mkdir -p "$MODEL_DIR"
cd "$MODEL_DIR"

echo "=========================================="
echo "LLM Model Download Script"
echo "=========================================="
echo ""
echo "Your system: 15GB RAM, 12 CPU cores"
echo "Recommended: Phi-3 Mini (fast) or LLaMA 3 8B (better quality)"
echo ""

# Option 1: Phi-3 Mini (Fastest, ~2.3GB)
echo "Option 1: Phi-3 Mini (Recommended for speed)"
echo "  Size: ~2.3GB"
echo "  RAM: ~4GB"
echo "  Speed: Very fast (1-3 seconds per response)"
echo ""

# Option 2: LLaMA 3 8B (Better quality, ~4.7GB)
echo "Option 2: LLaMA 3 8B (Better quality)"
echo "  Size: ~4.7GB"
echo "  RAM: ~6-8GB"
echo "  Speed: Moderate (3-8 seconds per response)"
echo ""

read -p "Choose model (1 for Phi-3 Mini, 2 for LLaMA 3 8B, or 'q' to quit): " choice

case $choice in
  1)
    echo ""
    echo "Downloading Phi-3 Mini (this may take a few minutes)..."
    wget -c https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_K_M.gguf
    if [ $? -eq 0 ]; then
      echo ""
      echo "✓ Download complete!"
      echo ""
      echo "Update config.json with:"
      echo '  "llm_model_path": "local/models/Phi-3-mini-4k-instruct-q4_K_M.gguf"'
      MODEL_FILE="Phi-3-mini-4k-instruct-q4_K_M.gguf"
    else
      echo "✗ Download failed. Please try manually."
      exit 1
    fi
    ;;
  2)
    echo ""
    echo "Downloading LLaMA 3 8B (this may take 5-10 minutes)..."
    wget -c https://huggingface.co/bartowski/Llama-3-8B-Instruct-GGUF/resolve/main/Llama-3-8B-Instruct-Q4_K_M.gguf
    if [ $? -eq 0 ]; then
      echo ""
      echo "✓ Download complete!"
      echo ""
      echo "Update config.json with:"
      echo '  "llm_model_path": "local/models/Llama-3-8B-Instruct-Q4_K_M.gguf"'
      MODEL_FILE="Llama-3-8B-Instruct-Q4_K_M.gguf"
    else
      echo "✗ Download failed. Please try manually."
      exit 1
    fi
    ;;
  q|Q)
    echo "Cancelled."
    exit 0
    ;;
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

# Verify file
if [ -f "$MODEL_FILE" ]; then
  SIZE=$(du -h "$MODEL_FILE" | cut -f1)
  echo ""
  echo "Model file: $MODEL_FILE"
  echo "Size: $SIZE"
  echo ""
  echo "Next steps:"
  echo "1. Edit config.json and update 'llm_model_path'"
  echo "2. Restart the app: ./start.sh"
  echo ""
  echo "The model will use ~4-8GB RAM when running."
  echo "It may slow down your system slightly during inference (1-8 seconds per query)."
else
  echo "Error: Model file not found after download."
  exit 1
fi

