# First Start Checklist

Use this checklist when setting up the Personal RAG Journal on a new device or after cloning the repository.

## Pre-Flight Checks

- [ ] **Python 3.8+ installed**
  ```bash
  python3 --version
  # Should show 3.8 or higher
  ```

- [ ] **Node.js 16+ installed**
  ```bash
  node --version
  # Should show v16 or higher
  ```

- [ ] **Git installed and configured**
  ```bash
  git --version
  git config --global user.name "Your Name"
  git config --global user.email "your.email@example.com"
  ```

## Repository Setup

- [ ] **Repository cloned or initialized**
  ```bash
  # If cloning:
  git clone <your-private-repo-url> personal-rag
  cd personal-rag
  
  # If initializing new:
  git init
  git remote add origin <your-private-repo-url>
  ```

- [ ] **Verify project structure**
  ```bash
  ls -la
  # Should see: backend/, frontend/, entries/, scripts/, config.json, etc.
  ```

## Environment Setup

- [ ] **Virtual environment created**
  ```bash
  python3 -m venv venv
  # or
  python3 -m venv .venv
  ```

- [ ] **Virtual environment activated**
  ```bash
  source venv/bin/activate  # Linux/Mac
  # or
  .venv\Scripts\activate  # Windows
  ```

- [ ] **Python dependencies installed**
  ```bash
  pip install --upgrade pip
  pip install -r requirements.txt
  ```

- [ ] **Frontend dependencies installed**
  ```bash
  cd frontend
  npm install
  cd ..
  ```

## Model Setup

- [ ] **LLM model downloaded**
  - Recommended: LLaMA 3 8B Instruct (GGUF format, ~5GB)
  - Download from: https://huggingface.co/models?search=llama-3-8b-instruct-gguf
  - Place in: `local/models/llama-3-8b-instruct.gguf`

- [ ] **Model path verified**
  ```bash
  ls -lh local/models/
  # Should show your model file
  ```

- [ ] **config.json updated**
  ```bash
  cat config.json | grep llm_model_path
  # Should point to: local/models/your-model.gguf
  ```

## Git Configuration

- [ ] **Git remote configured** (if syncing)
  ```bash
  git remote -v
  # Should show your repository URL
  ```

- [ ] **Initial sync completed**
  ```bash
  git pull origin main  # or master
  # Should pull existing entries if any
  ```

## Directory Structure

- [ ] **Required directories exist**
  ```bash
  mkdir -p entries local/models local/embeddings local/summaries logs
  ```

- [ ] **Entries directory has example entries** (optional)
  ```bash
  ls entries/
  # Should show example-*.json files
  ```

## Verification

- [ ] **Run environment check**
  ```bash
  ./scripts/check_env.sh
  # Should show all checks passing (or warnings for missing model)
  ```

- [ ] **Test Django setup**
  ```bash
  cd backend
  python3 manage.py check
  # Should show: System check identified no issues
  cd ..
  ```

## First Start

- [ ] **Start the application**
  ```bash
  ./start.sh
  ```

- [ ] **Verify services are running**
  - Backend: http://localhost:8000/api/entries/ (should return JSON)
  - Frontend: http://localhost:3000 (should show the app)

- [ ] **Create a test entry**
  - Go to "New Entry" tab
  - Fill out the form
  - Submit
  - Verify entry appears in "History" tab

- [ ] **Test query functionality**
  - Go to "Ask Coach" tab
  - Ask: "What drains my energy?"
  - Verify response appears (may be mock if model not loaded)

- [ ] **Verify entry file created**
  ```bash
  ls -lt entries/ | head -5
  # Should show your new entry file
  ```

## Sync Verification (Multi-Device)

If using multiple devices:

- [ ] **Device 1: Create entry and stop**
  ```bash
  ./stop.sh
  # Should commit and push
  ```

- [ ] **Device 2: Pull and verify**
  ```bash
  git pull
  ls entries/
  # Should show entry from Device 1
  ```

- [ ] **Device 2: Start and verify index**
  ```bash
  ./start.sh
  # Index should rebuild with entries from both devices
  ```

## Troubleshooting

If something fails:

1. **Check logs**
   ```bash
   tail -f logs/django.log
   tail -f logs/react.log
   ```

2. **Verify model file**
   ```bash
   file local/models/*.gguf
   # Should show: GGUF model data
   ```

3. **Check Python packages**
   ```bash
   pip list | grep -E "Django|sentence-transformers|faiss|llama"
   ```

4. **Check Node packages**
   ```bash
   cd frontend && npm list --depth=0
   ```

5. **Rebuild index manually**
   ```bash
   cd backend
   python3 manage.py shell
   >>> from api.rag_system import RAGSystem
   >>> rag = RAGSystem()
   >>> rag.rebuild_index()
   ```

## Common Issues

- **Port already in use**: Kill existing processes or change ports
- **Model not found**: Verify path in config.json and file exists
- **Import errors**: Ensure virtual environment is activated
- **Git conflicts**: Resolve manually, then commit and push

## Success Criteria

You're ready to go when:
- ✅ `./start.sh` runs without errors
- ✅ Frontend loads at http://localhost:3000
- ✅ You can create an entry
- ✅ Entry appears in history
- ✅ Query returns a response (even if mock)

---

**Next Steps**: Start journaling! The app will learn your patterns over time. Be gentle with yourself. 🌱

