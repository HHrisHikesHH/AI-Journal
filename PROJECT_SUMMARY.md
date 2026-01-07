# Project Summary: How It Works

This document provides a high-level overview of how the Personal RAG Journal system works.

## Architecture Overview

```
User (Browser)
    ↓
React Frontend (localhost:3000)
    ↓ HTTP REST API
Django Backend (localhost:8000)
    ↓
├── Entry Storage (JSON files in entries/)
├── RAG System (FAISS + Embeddings)
└── Local LLM (llama-cpp-python/gpt4all)
```

## Data Flow

### 1. Entry Creation Flow

```
User fills form → React sends POST /api/entry/
    ↓
Django validates → Creates entry object
    ↓
EntryProcessor adds derived fields (sentiment, themes, flags, summary)
    ↓
Entry saved as JSON file: entries/YYYY-MM-DDTHH-MM-SSZ__uuid.json
    ↓
RAGSystem.add_entry() → Embeds entry text → Adds to FAISS index
    ↓
Response returned to frontend → Entry appears in UI
```

### 2. Query Flow (RAG)

```
User asks question → React sends POST /api/query/
    ↓
RAGSystem.query()
    ├── Embeds query using sentence-transformers
    ├── Searches FAISS index for similar entries (k=5)
    ├── Retrieves relevant entry texts
    └── Builds context string
    ↓
LLMClient.generate()
    ├── Constructs prompt with system instructions + context
    ├── Calls local LLM (llama-cpp-python or gpt4all)
    └── Returns generated response
    ↓
RAGSystem parses response into structured format
    ├── reality_check
    ├── evidence (with sources)
    ├── action
    └── sign_off
    ↓
Formatted answer + sources returned to frontend
```

### 3. Index Rebuild Flow

```
On startup or POST /api/rebuild_index/
    ↓
RAGSystem.rebuild_index()
    ├── Scans entries/ directory for all .json files
    ├── Loads each entry
    ├── Extracts searchable text (_get_entry_text)
    ├── Generates embeddings for all entries (batch)
    └── Creates/updates FAISS index
    ↓
Index saved to local/embeddings/faiss_index.bin
Entry metadata saved to local/embeddings/entries_metadata.json
```

### 4. Git Sync Flow

```
start.sh runs
    ↓
git_sync.py --pull
    ├── git pull --rebase
    └── Handles conflicts gracefully
    ↓
App starts, index rebuilds with all entries
    ↓
User creates entries (saved locally)
    ↓
stop.sh runs
    ↓
git_sync.py --push
    ├── git add entries/*.json
    ├── git commit -m "Journal entries update"
    └── git push (or commits locally if offline)
```

## Key Components

### Backend Components

1. **views.py**: REST API endpoints
   - `create_entry()`: Validates, processes, saves entry
   - `get_entries()`: Returns recent entries
   - `query()`: RAG query endpoint
   - `rebuild_index()`: Rebuilds FAISS index

2. **rag_system.py**: Core RAG implementation
   - `RAGSystem`: Manages embeddings, FAISS, and LLM integration
   - `_get_entry_text()`: Extracts searchable text from entries
   - `query()`: Main query method (embed → search → generate)
   - `_build_query_prompt()`: Constructs LLM prompt with coaching tone
   - `_parse_llm_response()`: Parses structured response

3. **llm_client.py**: Local LLM interface
   - `LLMClient`: Wraps llama-cpp-python or gpt4all
   - `generate()`: Generates text from prompt
   - Falls back to mock responses if model unavailable

4. **entry_processor.py**: Entry enrichment
   - `EntryProcessor`: Adds derived fields
   - `_get_sentiment()`: TextBlob sentiment analysis
   - `_extract_themes()`: Keyword-based theme extraction
   - `_detect_flags()`: Pattern detection (low energy, procrastination, etc.)
   - `_generate_summary()`: One-sentence summary

### Frontend Components

1. **EntryForm.js**: Daily entry form
   - Emotion selector (8 options)
   - Energy slider (1-10)
   - "Showed up" toggle
   - Habit toggles (exercise, deep_work, sleep_on_time)
   - Free text (max 200 chars, required)
   - Long reflection (optional)

2. **HistoryView.js**: Analytics and history
   - Discipline trend (line chart)
   - Habit streaks (current streak counts)
   - Goal alignment (bar chart)
   - Recent entries list

3. **QueryInterface.js**: Coaching interface
   - Query input
   - Suggested questions
   - Answer display with sources
   - Confidence estimate

## Storage Schema

### Entry JSON Structure

```json
{
  "id": "uuid",
  "timestamp": "ISO-8601",
  "device": "machine-name",
  "emotion": "named-emotion",
  "energy": 1-10,
  "showed_up": true/false,
  "habits": {
    "exercise": true,
    "deep_work": false,
    "sleep_on_time": true
  },
  "goals": ["career", "health"],
  "free_text": "string (<=200 chars)",
  "long_reflection": "optional string",
  "derived": {
    "sentiment": {"polarity": 0.6, "subjectivity": 0.7},
    "themes": ["health", "work"],
    "flags": ["low_energy"],
    "summary": "One sentence summary"
  }
}
```

### File Naming

Entries are stored as: `YYYY-MM-DDTHH-MM-SSZ__uuid.json`

Example: `2024-01-15T10-30-00Z__a1b2c3d4-e5f6-7890-abcd-ef1234567890.json`

## Embedding & Search

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimension**: 384
- **Index Type**: FAISS IndexFlatL2 (L2 distance)
- **Search**: k-nearest neighbors (k=5 by default)

Entry text includes:
- Emotion
- Energy level
- Showed up status
- Free text
- Long reflection
- Derived summary

## LLM Prompts

### System Prompt (Coaching Tone)

```
You are a gentle, supportive personal coach. Your role is to help someone understand their patterns and make small, sustainable changes. You must:
- Never shame or judge
- Present evidence neutrally
- Give ONE small, actionable suggestion
- Be indirect and gentle in your tone
- Only use information from the provided context
- If data is insufficient, say so clearly
```

### Response Format

```
REALITY_CHECK: [One sentence neutral observation]
EVIDENCE:
- [Evidence item 1 with source date]
- [Evidence item 2 with source date]
- [Evidence item 3 with source date]
ACTION: [One small, specific action]
SIGN_OFF: [Gentle closing phrase]
```

## Psychology & UX Rules

1. **Never shame**: All responses are neutral and supportive
2. **One action**: Only suggest one small, specific action
3. **Evidence-based**: Always cite sources (entry dates)
4. **Insufficient data**: If not enough entries, state clearly
5. **Gentle sign-off**: Every response ends with a supportive phrase

## Derived Fields Computation

- **Sentiment**: TextBlob polarity (-1 to 1) and subjectivity (0 to 1)
- **Themes**: Keyword matching against predefined themes (work, health, relationships, growth, stress, gratitude)
- **Flags**: Pattern detection:
  - `low_energy`: Energy < 3
  - `evening_procrastination`: Low energy + procrastination keywords
  - `high_stress`: Negative emotion + low energy
  - `consistency_concern`: Didn't show up + low energy
- **Summary**: One sentence combining emotion, energy, showed_up status, and free_text preview

## Weekly Summaries

Generated by `scripts/weekly_summary.py` (run via cron):

1. Loads entries from past 7 days
2. Aggregates stats (emotions, energy, habits, showed_up rate)
3. Builds context string
4. Calls LLM with weekly reflection prompt
5. Saves to `local/summaries/weekly_summary_YYYY-MM-DD.txt`

## Offline Support

- Entries saved locally immediately
- Git commits work offline (local commits)
- Push happens on next `stop.sh` when online
- Index rebuilds on startup with all local entries
- No network required for core functionality

## Security & Privacy

- All data local (entries, embeddings, models)
- No cloud APIs or external services
- Git sync is user-controlled (private repo recommended)
- Optional: git-crypt for encryption

## Performance Considerations

- **Embedding generation**: Batch processing on index rebuild (faster)
- **Incremental indexing**: Single entry added immediately (slower but responsive)
- **FAISS search**: Very fast (milliseconds) even with thousands of entries
- **LLM inference**: Depends on model size and hardware (typically 1-5 seconds)

## Extension Points

1. **Add new fields**: Update entry schema, form, and `_get_entry_text()`
2. **Change embedding model**: Update config, delete old index, rebuild
3. **Different LLM**: Update `llm_client.py` to support other backends
4. **Custom themes**: Modify `entry_processor.py` → `_extract_themes()`
5. **New visualizations**: Add charts to `HistoryView.js`

---

This system is designed to be simple, local-first, and privacy-preserving while providing meaningful insights through RAG-powered coaching.

