# Personal RAG Journal & Coaching App

A local-first, private journaling application with AI-powered coaching insights. All data stays on your device, synced via Git. No cloud APIs, no external services.

## Features

- **Quick Entry Shortcuts**: Desktop keyboard shortcut `Ctrl+K` to open a quick-entry modal
- **One-action Daily + Weekly Coaching**: Daily insight on app open, weekly summaries
- **Showed_up + Streaks + Action Items**: Track showed_up, visualize streaks, manage action items from coach suggestions
- **Proactive Coaching**: Insight on app open (rate-limited to once per calendar day)
- **Search + Filter**: Semantic search with emotion, habit, and date filters
- **Export & Backup**: Export entries as CSV/JSON, automatic backups on stop
- **Mobile PWA-ready**: Single-page React app optimized for mobile

## Prerequisites

- **Python 3.11** (exact version required)
- **pip** (Python package manager)
- **Node.js 18+** and npm
- **Git**
- **8GB+ RAM** (for local LLM)
- **A local LLM model file** (see Setup below)

## First-Start Checklist

Before running `./start.sh`, complete these 5 steps:

### Step 1: Set Up Private Git Repository

```bash
# Initialize Git repository (if not already initialized)
git init

# Add your private Git remote
git remote add origin <YOUR_PRIVATE_GIT_REPO_URL>

# Verify remote is set
git remote get-url origin
```

**Important**: The scripts will check for a Git remote and fail with clear instructions if `origin` is not configured.

### Step 2: Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Step 3: Download LLM Model

You must download a local LLM model. The app will check for the model and exit with clear instructions if missing.

**Expected path**: `local/models/phi-2.Q4_K_M.gguf` (or path specified in `config.json`)

**Quick Download (Recommended)**: Use the download script:

```bash
./scripts/download_fast_model.sh
```

This will let you choose from:
1. **TinyLlama 1.1B** (~700MB) - FASTEST, good for simple patterns
2. **Phi-2 2.7B** (~1.6GB) - Fast, better quality  
3. **Qwen2.5-1.5B** (~1GB) - Good balance

**Manual Download** (if script doesn't work):

```bash
# Create models directory
mkdir -p local/models

# Download TinyLlama 1.1B (recommended for speed)
cd local/models
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -O phi-2.Q4_K_M.gguf
cd ../..
```

**Update `config.json`** to point to your model (already configured for Phi-2):

```json
{
  "models": {
    "llm_model_path": "local/models/phi-2.Q4_K_M.gguf"
  }
}
```

**Note**: The app is optimized for speed with:
- 8 CPU threads (utilizes more cores)
- Reduced context window (1024 tokens)
- Batch processing enabled
- Memory mapping for faster loading

### Step 4: Verify Configuration

Check that `config.json` exists and contains:
- `emotions`: List of allowed emotions
- `habits`: Object with habit definitions
- `models.llm_model_path`: Path to your LLM model file

### Step 5: Run Start Script

```bash
./start.sh
```

The script will:
1. Check prerequisites
2. Pull latest entries from Git (`git pull --rebase`)
3. Rebuild FAISS index
4. Start Django backend on port 8000
5. Start React frontend on port 3000
6. Generate weekly summary (if needed)

## Usage

### Starting the App

```bash
./start.sh
```

Access the app at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api

### Stopping the App

```bash
./stop.sh
```

The script will:
1. Stop Django and React servers
2. Create timestamped backup of `entries/` to `backups/`
3. Commit new entries to Git
4. Push to remote repository

### Quick Entry (Ctrl+K)

Press `Ctrl+K` (or `Cmd+K` on Mac) to open the quick-entry modal. This allows you to:
- Select an emotion (required)
- Toggle "showed_up" (required)
- Toggle habits (configurable from backend)
- Enter brief reflection (max 200 chars, required)
- Enter longer reflection (optional)

### Daily Insight

On app open, you'll see a daily insight card with:
- One neutral observation
- Evidence bullets with source filenames
- One micro-action
- Confidence estimate

This is rate-limited to once per calendar day.

### Weekly Summary

Weekly summaries are automatically generated and saved to:
`local/summaries/weekly_summary_YYYY-MM-DD.txt`

The summary includes:
- Verdict (one sentence)
- Evidence bullets with source filenames
- Action (one small action)
- Confidence estimate

## API Endpoints

### Entry Management

- `POST /api/entry/` - Create a new entry
  - Required: `emotion`, `energy`, `showed_up`, `habits`, `free_text` (<=200 chars)
  - Optional: `goals`, `long_reflection`
  
- `GET /api/entries/?days=7` - Get recent entries

### Coaching & Insights

- `GET /api/insight/on_open` - Get daily insight (rate-limited)
- `POST /api/query/` - Query the RAG system
  - Body: `{"query": "your question"}`
  - Returns: `{answer, sources, confidence_estimate, structured}`

### Search & Export

- `GET /api/search?q=text&emotion=content&habit=exercise&from=2024-01-01&to=2024-01-31` - Search entries
- `GET /api/export?format=csv|json` - Export all entries

### Action Items

- `POST /api/action/` - Create action item from coach suggestion
- `GET /api/actions/?completed=true|false` - Get action items
- `POST /api/action/<id>/` - Update action item
- `DELETE /api/action/<id>/delete/` - Delete action item

### Index Management

- `POST /api/rebuild_index/` - Rebuild FAISS index from all entries

## Configuration

Edit `config.json` to customize:

- **Emotions**: Allowed emotion choices (exact list: `["content","anxious","sad","angry","motivated","tired","calm","stressed"]`)
- **Habits**: Configurable habits to track
- **Goals**: User goals for alignment tracking
- **LLM Model**: Path to local LLM model file
- **LLM Parameters**: `max_tokens`, `temperature`

## Data Storage

- **Entries**: `entries/YYYY-MM-DDTHH-MM-SSZ__<uuid>.json`
- **FAISS Index**: `local/embeddings/faiss_index.bin` (not in Git)
- **Embeddings Cache**: `local/embeddings/` (not in Git)
- **Weekly Summaries**: `local/summaries/weekly_summary_YYYY-MM-DD.txt`
- **Action Items**: `local/action_items.json`
- **Backups**: `backups/entries_backup_<timestamp>.tar.gz`

## Git Sync

The app uses Git for synchronization:

- **On Start**: `git pull --rebase` (with conflict-safe behavior)
- **On Stop**: `git add entries/`, `git commit -m "auto: entries"`, `git push`

**Important**: 
- Only `entries/` files are committed
- `local/` directory is ignored (see `.gitignore`)
- Scripts check for Git remote and fail gracefully if not configured

### Resolving Git Conflicts

If conflicts occur during `git pull --rebase`:

```bash
# Check status
git status

# Resolve conflicts manually
# Edit conflicted files, then:
git add entries/
git rebase --continue

# Or abort and start fresh
git rebase --abort
```

## Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Run tests
cd backend
python manage.py test ../tests
```

Test files:
- `tests/test_api.py` - API endpoint tests
  - `test_entry_create` - Entry creation and file persistence
  - `test_rebuild_index` - Index rebuild and file creation
  - `test_query_basic` - Basic query functionality

## Troubleshooting

### Model File Not Found

If you see: "ERROR: LLM model file not found"

1. Check that the model file exists at the path in `config.json`
2. Verify the path is relative to project root
3. Download the model if missing (see Step 3 in First-Start Checklist)

### Git Remote Not Configured

If you see: "Git remote 'origin' is not configured"

```bash
git remote add origin <YOUR_PRIVATE_GIT_REPO_URL>
git push -u origin main
```

### Port Already in Use

If ports 8000 or 3000 are in use:

```bash
# Kill processes on ports
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9

# Or use the start script (it handles this automatically)
./start.sh
```

### Import Errors

If you see import errors:

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Check Python version (must be 3.11)
python3 --version
```

## Project Structure

```
personal-rag/
├── backend/              # Django backend
│   ├── api/              # API app
│   │   ├── views.py      # API endpoints
│   │   ├── rag_system.py # RAG implementation
│   │   ├── llm_adapter.py # LLM adapter
│   │   └── action_items.py # Action items management
│   ├── journal_api/      # Django project settings
│   └── prompts/          # Prompt templates
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── QuickEntryModal.js
│   │   │   ├── InsightCard.js
│   │   │   ├── HistoryView.js
│   │   │   └── QueryInterface.js
│   │   └── App.js
│   └── package.json
├── entries/              # Journal entries (JSON files)
├── local/                # Local data (not in Git)
│   ├── models/           # LLM model files
│   ├── embeddings/       # FAISS index and cache
│   └── summaries/       # Weekly summaries
├── scripts/              # Utility scripts
│   ├── git_sync.py       # Git synchronization
│   ├── weekly_summary.py # Weekly summary generation
│   └── derive_entry.py   # Entry processing
├── tests/                # Test files
├── start.sh              # Start script
├── stop.sh               # Stop script
├── config.json           # Configuration
└── requirements.txt      # Python dependencies
```

## License

Private use only. All data stays local.
