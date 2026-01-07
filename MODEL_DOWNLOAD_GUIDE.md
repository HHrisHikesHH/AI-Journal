# LLM Model Download Guide

## Performance Impact

**Will it slow down your machine?**

- **Small models (3B-7B, Q4 quantization)**: Minimal impact
  - RAM usage: ~4-8GB
  - CPU inference: 1-5 seconds per response
  - Good for most use cases
  
- **Medium models (8B-13B, Q4 quantization)**: Moderate impact
  - RAM usage: ~8-16GB
  - CPU inference: 3-10 seconds per response
  - Better quality, slower responses

- **Large models (13B+, Q4 quantization)**: Significant impact
  - RAM usage: 16GB+
  - CPU inference: 10-30+ seconds per response
  - Best quality, but may slow down your system

**Recommendation**: Start with a **7B Q4_K_M quantized model** - good balance of quality and speed.

## Quick Download Options

### Option 1: Using Hugging Face (Recommended)

**Best for beginners - Small, fast model:**

```bash
# Create models directory
mkdir -p /home/htadmin/Documents/rag_project/local/models
cd /home/htadmin/Documents/rag_project/local/models

# Download a small, fast model (Phi-3 Mini, ~2.3GB, very fast)
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_K_M.gguf

# Or download LLaMA 3 8B Q4 (better quality, ~4.7GB, slower)
# wget https://huggingface.co/bartowski/Llama-3-8B-Instruct-GGUF/resolve/main/Llama-3-8B-Instruct-Q4_K_M.gguf
```

**Update config.json:**
```json
{
  "models": {
    "llm_model_path": "local/models/Phi-3-mini-4k-instruct-q4_K_M.gguf"
  }
}
```

### Option 2: Using huggingface-cli (Easier)

```bash
# Install huggingface-cli if not already installed
pip install huggingface_hub[cli]

# Download model
cd /home/htadmin/Documents/rag_project/local/models
huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf Phi-3-mini-4k-instruct-q4_K_M.gguf --local-dir . --local-dir-use-symlinks False
```

### Option 3: Manual Download from Hugging Face

1. Visit: https://huggingface.co/models?search=gguf
2. Search for: "Phi-3-mini" or "Llama-3-8B-Instruct"
3. Look for files ending in `.gguf`
4. Download a **Q4_K_M** or **Q5_K_M** quantized version
5. Place in: `/home/htadmin/Documents/rag_project/local/models/`
6. Update `config.json` with the filename

## Recommended Models (Best to Worst for Performance)

### 1. Phi-3 Mini (Fastest, Good Quality)
- **Size**: ~2.3GB (Q4_K_M)
- **RAM**: ~4GB
- **Speed**: Very fast (1-3 seconds)
- **Quality**: Good for coaching responses
- **Download**: `microsoft/Phi-3-mini-4k-instruct-gguf`

### 2. LLaMA 3 8B (Balanced)
- **Size**: ~4.7GB (Q4_K_M)
- **RAM**: ~6-8GB
- **Speed**: Moderate (3-8 seconds)
- **Quality**: Excellent
- **Download**: `bartowski/Llama-3-8B-Instruct-GGUF`

### 3. Mistral 7B (Good Alternative)
- **Size**: ~4.1GB (Q4_K_M)
- **RAM**: ~6GB
- **Speed**: Moderate (3-7 seconds)
- **Quality**: Very good
- **Download**: `TheBloke/Mistral-7B-Instruct-v0.2-GGUF`

## Step-by-Step: Download Phi-3 Mini (Recommended)

```bash
# 1. Navigate to project
cd /home/htadmin/Documents/rag_project

# 2. Create models directory
mkdir -p local/models

# 3. Download model (this will take a few minutes)
cd local/models
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_K_M.gguf

# 4. Verify download
ls -lh *.gguf

# 5. Update config.json
cd ../..
# Edit config.json and change:
# "llm_model_path": "local/models/Phi-3-mini-4k-instruct-q4_K_M.gguf"
```

## Update Config

After downloading, update `config.json`:

```json
{
  "models": {
    "llm_model_path": "local/models/Phi-3-mini-4k-instruct-q4_K_M.gguf",
    "llm_model_type": "llama",
    "llm_max_tokens": 512,
    "llm_temperature": 0.2
  }
}
```

## Test the Model

After downloading and updating config:

```bash
# Start the app
./start.sh

# Or test manually
cd backend
source ../venv/bin/activate
python manage.py shell
>>> from api.llm_client import LLMClient
>>> client = LLMClient()
>>> response = client.generate("Hello, how are you?", max_tokens=50)
>>> print(response)
```

## Performance Tips

1. **Use Q4 quantization**: Smaller files, faster inference
2. **Close other apps**: Free up RAM for better performance
3. **Start small**: Try Phi-3 Mini first, upgrade if needed
4. **Use CPU**: Works fine on CPU, GPU optional (faster but not required)

## Troubleshooting

**Model not loading?**
- Check file path in config.json
- Verify file exists: `ls -lh local/models/*.gguf`
- Check file permissions: `chmod 644 local/models/*.gguf`

**Too slow?**
- Use a smaller model (Phi-3 Mini)
- Reduce `llm_max_tokens` in config.json (try 256 instead of 512)
- Close other applications

**Out of memory?**
- Use a smaller model
- Close other applications
- Consider using Q3 quantization (smaller but lower quality)

## Model File Sizes Reference

- **Q2**: Smallest, fastest, lower quality (~1.5GB for 7B)
- **Q3**: Small, fast, decent quality (~2GB for 7B)
- **Q4_K_M**: **Recommended** - Good balance (~2.3-4.7GB)
- **Q5_K_M**: Larger, slower, better quality (~3-6GB)
- **Q8**: Largest, slowest, best quality (~7-13GB)

## Quick Command Reference

```bash
# Download Phi-3 Mini (recommended)
cd /home/htadmin/Documents/rag_project/local/models
wget https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4_K_M.gguf

# Verify
ls -lh *.gguf

# Update config (edit manually or use sed)
# Then restart: ./start.sh
```

---

**Note**: The app works fine without a model (uses mock responses). Download a model only if you want real LLM-generated coaching responses.

