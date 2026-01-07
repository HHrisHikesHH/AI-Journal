# Personal RAG Journal & Coaching App

A local-first, private journaling application with AI-powered coaching insights. All data stays on your device, synced via Git. No cloud APIs, no external services.

## Features

- **Daily Journaling**: Quick 60-second entry flow with emotion tracking, habit toggles, and optional longer reflections
- **RAG-Powered Coaching**: Ask questions about your patterns and get insights grounded in your journal entries
- **Visual Analytics**: Track discipline trends, habit streaks, and goal alignment over time
- **Local-Only**: All processing happens on your machine using local LLMs and embeddings
- **Git Sync**: Entries are stored as JSON files and synced via Git (works offline, commits locally)

## Architecture

- **Backend**: Django REST API with FAISS vector search and local LLM inference
- **Frontend**: React single-page application
- **Storage**: JSON files in `entries/` directory (one file per entry)
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Store**: FAISS (CPU-optimized)
- **LLM**: llama-cpp-python or gpt4all (local inference)

## Prerequisites

- Python 3.8+
- Node.js 16+ and npm
- Git
- 8GB+ RAM (for local LLM)
- A local LLM model file (see Setup below)

## Quick Start

### 1. Initial Setup

```bash
# Clone or initialize the repository
git clone <your-private-repo-url> personal-rag
cd personal-rag

# Or initialize a new repo
git init
git remote add origin <your-private-repo-url>
```

### 2. Install Dependencies

```bash
# Check environment
./scripts/check_env.sh

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

### 3. Download LLM Model

You need to download a local LLM model. Recommended: **LLaMA 3 8B Instruct** (GGUF format).

**Option 1: Using Hugging Face**
```bash
# Create models directory
mkdir -p local/models

# Download LLaMA 3 8B Instruct (GGUF)
# Visit: https://huggingface.co/models?search=llama-3-8b-instruct-gguf
# Download a Q4_K_M or Q5_K_M quantized version (~5GB)
# Place it in: local/models/llama-3-8b-instruct.gguf
```

**Option 2: Using llama.cpp**
```bash
# Install llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make

# Download model (example)
./scripts/download-gguf-model.sh meta-llama/Meta-Llama-3-8B-Instruct
# Copy the .gguf file to local/models/
```

**Update config.json** to point to your model:
```json
{
  "models": {
    "llm_model_path": "local/models/your-model.gguf"
  }
}
```

### 4. Initialize Git Repository (if new)

```bash
# Add all files except local/ directory
git add .
git commit -m "Initial commit"

# Set up remote (if not already done)
git remote add origin <your-private-repo-url>
git push -u origin main
```

### 5. Start the Application

```bash
./start.sh
```

This will:
- Pull latest changes from Git
- Rebuild the search index
- Start Django backend on http://localhost:8000
- Start React frontend on http://localhost:3000

Open http://localhost:3000 in your browser.

### 6. Stop the Application

```bash
./stop.sh
```

This will:
- Gracefully stop both servers
- Commit any new entries to Git
- Push changes to remote (if online)

## API Endpoints

### `POST /api/entry/`
Create a new journal entry.

**Request Body:**
```json
{
  "emotion": "content",
  "energy": 7,
  "showed_up": true,
  "habits": {
    "exercise": true,
    "deep_work": false,
    "sleep_on_time": true
  },
  "goals": ["career", "health"],
  "free_text": "Had a good day",
  "long_reflection": "Optional longer reflection..."
}
```

**Response:** Created entry object with `id`, `timestamp`, and `derived` fields.

### `GET /api/entries/?days=7`
Get recent entries.

**Query Parameters:**
- `days` (optional): Number of days to retrieve (default: 7)

**Response:**
```json
{
  "entries": [...]
}
```

### `POST /api/query/`
Query the RAG system with a question.

**Request Body:**
```json
{
  "query": "What drains my energy?"
}
```

**Response:**
```json
{
  "answer": "Formatted answer text...",
  "sources": [
    {
      "date": "2024-01-15",
      "emotion": "tired",
      "filename": "2024-01-15T10-30-00Z__uuid.json"
    }
  ],
  "confidence_estimate": 0.8,
  "structured": {
    "reality_check": "...",
    "evidence": [...],
    "action": "...",
    "sign_off": "..."
  }
}
```

### `POST /api/rebuild_index/`
Rebuild the FAISS index from all entries.

**Response:**
```json
{
  "status": "Index rebuilt successfully"
}
```

## Project Structure

```
personal-rag/
├── backend/                 # Django backend
│   ├── journal_api/         # Django project settings
│   ├── api/                 # API app
│   │   ├── views.py         # API endpoints
│   │   ├── rag_system.py    # RAG system (embeddings, FAISS, LLM)
│   │   ├── llm_client.py    # Local LLM client
│   │   └── entry_processor.py  # Entry processing (sentiment, themes)
│   └── manage.py
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── EntryForm.js
│   │   │   ├── HistoryView.js
│   │   │   └── QueryInterface.js
│   │   └── App.js
│   └── package.json
├── entries/                 # Journal entries (JSON files)
│   └── YYYY-MM-DDTHH-MM-SSZ__uuid.json
├── local/                   # Local data (not in Git)
│   ├── models/              # LLM model files
│   ├── embeddings/          # FAISS index and metadata
│   └── summaries/           # Weekly summaries
├── scripts/
│   ├── git_sync.py          # Git sync (pull/push)
│   ├── derive_entry.py      # Process entries (standalone)
│   ├── weekly_summary.py    # Generate weekly summaries
│   └── check_env.sh         # Environment check
├── tests/                   # Integration tests
├── config.json              # Configuration
├── requirements.txt         # Python dependencies
├── start.sh                 # Start script
└── stop.sh                  # Stop script
```

## Configuration

Edit `config.json` to customize:

- **User identity and goals**: Personalize the coaching tone
- **Model paths**: Point to your LLM model
- **Habits**: Add/remove habit fields
- **Emotions**: Customize emotion list
- **Reflection questions**: Add your own questions

## Weekly Summaries

Set up a cron job to generate weekly summaries:

```bash
# Edit crontab
crontab -e

# Add this line (runs every Monday at 9 AM)
0 9 * * 1 cd /path/to/personal-rag && source venv/bin/activate && python3 scripts/weekly_summary.py
```

Summaries are saved to `local/summaries/weekly_summary_YYYY-MM-DD.txt`.

## Troubleshooting

### Offline Mode

The app works offline. Entries are saved locally and committed to Git. When you're back online, run `./stop.sh` or manually:

```bash
python3 scripts/git_sync.py --push
```

### Merge Conflicts

If you have conflicts after `git pull`:

```bash
# Resolve conflicts manually
git status
# Edit conflicted files
git add entries/
git commit -m "Resolved merge conflicts"
git push
```

### Rebuilding Index

If the search index gets corrupted:

```bash
# Via API
curl -X POST http://localhost:8000/api/rebuild_index/

# Or manually
cd backend
python3 manage.py shell
>>> from api.rag_system import RAGSystem
>>> rag = RAGSystem()
>>> rag.rebuild_index()
```

### LLM Not Working

If the LLM doesn't load:

1. Check model path in `config.json`
2. Verify model file exists: `ls -lh local/models/`
3. Check logs: `tail -f logs/django.log`
4. Try alternative: Install `gpt4all` instead of `llama-cpp-python`

```bash
pip install gpt4all
# Update llm_client.py to use GPT4All
```

### Port Already in Use

If port 8000 or 3000 is in use:

```bash
# Kill existing processes
lsof -ti:8000 | xargs kill
lsof -ti:3000 | xargs kill

# Or change ports in:
# - backend/journal_api/settings.py (Django)
# - frontend/package.json (React proxy)
```

## Security & Privacy

- **All data is local**: Entries, embeddings, and models stay on your machine
- **Git sync**: Use a private Git repository
- **Encryption**: Consider using `git-crypt` for sensitive entries:

```bash
# Install git-crypt
brew install git-crypt  # macOS
# or apt-get install git-crypt  # Linux

# Initialize
git-crypt init
echo "entries/*.json filter=git-crypt diff=git-crypt" >> .gitattributes
```

## Customization Guide

### Change Coach Tone/Identity

Edit `backend/api/rag_system.py`, method `_build_query_prompt()`:
- Modify the `system_prompt` string
- Adjust the coaching style and language

### Add/Remove Habit Fields

1. Edit `config.json` → `habits` object
2. Edit `frontend/src/components/EntryForm.js` → `HABITS` array
3. Update entry schema in `backend/api/views.py` if needed

### Change Emotion List

1. Edit `config.json` → `emotions` array
2. Edit `frontend/src/components/EntryForm.js` → `EMOTIONS` array

### Modify Reflection Questions

Edit `config.json` → `reflection_questions` array and `frontend/src/components/QueryInterface.js` → `SUGGESTED_QUESTIONS` array.

## Testing

Run integration tests:

```bash
cd backend
python3 manage.py test ../tests
```

Or run specific test:

```bash
python3 -m unittest tests.test_api.JournalAPITestCase.test_create_entry
```

## First Start Checklist

Before first run on a new device:

- [ ] Python 3.8+ installed
- [ ] Node.js 16+ installed
- [ ] Git repository cloned/initialized
- [ ] Virtual environment created and activated
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Frontend dependencies installed (`cd frontend && npm install`)
- [ ] LLM model downloaded and placed in `local/models/`
- [ ] `config.json` updated with correct model path
- [ ] Git remote configured (if syncing)
- [ ] Run `./scripts/check_env.sh` to verify setup

## Sample Prompts

### Weekly Reflection Prompt

The system uses this template for weekly summaries:

```
You are a gentle, supportive personal coach. Review this week's journal entries and provide a weekly reflection.

[Context with aggregated stats and recent entries]

Provide a gentle weekly reflection following this structure:
REALITY_CHECK: [One sentence neutral observation about the week]
EVIDENCE:
- [Key pattern or insight 1]
- [Key pattern or insight 2]
- [Key pattern or insight 3]
ACTION: [One small, specific action for the coming week]
SIGN_OFF: [Gentle closing phrase]

Be indirect, supportive, and never judgmental.
```

### Query Prompts

For "Am I being disciplined?":
- System computes discipline rate from `showed_up` + habit completions over last 30 days
- Presents evidence neutrally
- Suggests one small action

For "Am I on the right path?":
- Analyzes goal alignment from entries
- Looks at progress indicators
- Provides gentle guidance

## How It Works

1. **Entry Creation**: User submits entry → Django saves JSON file → Entry processed for derived fields → Added to FAISS index incrementally
2. **Query Flow**: User asks question → Query embedded → FAISS search finds relevant entries → LLM generates answer using retrieved context → Response formatted with sources
3. **Git Sync**: `start.sh` pulls latest → `stop.sh` commits and pushes new entries → Works offline (commits locally)
4. **Indexing**: On startup, all entries loaded → Text extracted → Embedded → FAISS index built/updated
5. **Weekly Summaries**: Cron job runs → Aggregates past week's entries → LLM generates summary → Saved to `local/summaries/`

## License

MIT License - Use freely for personal projects.

## Support

For issues or questions:
1. Check logs: `logs/django.log` and `logs/react.log`
2. Run environment check: `./scripts/check_env.sh`
3. Review troubleshooting section above

---

**Remember**: This is a personal tool. Your data stays with you. Be gentle with yourself. 🌱

