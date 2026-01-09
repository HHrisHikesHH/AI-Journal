# Project Structure

This document explains the organization of the Personal RAG Journal application.

## Directory Structure

```
rag_project/
├── backend/                    # Python Django backend
│   ├── api/                    # Main API application
│   │   ├── views.py           # API endpoints (entry creation, queries, insights)
│   │   ├── rag_system.py      # RAG (Retrieval-Augmented Generation) system
│   │   ├── llm_adapter.py     # LLM integration (Gemini/local models)
│   │   ├── entry_processor.py # Entry processing and derived fields
│   │   ├── action_items.py    # Action items management
│   │   └── prompt_utils.py    # Prompt utilities and truncation
│   ├── journal_api/           # Django project settings
│   │   ├── settings.py        # Django configuration
│   │   └── urls.py            # URL routing
│   ├── prompts/               # AI prompt templates
│   │   ├── system_prompt.txt  # Daily insight prompt
│   │   ├── query_prompt.txt   # Query/guidance prompt
│   │   ├── weekly_prompt.txt  # Weekly summary prompt
│   │   ├── monthly_prompt.txt # Monthly summary prompt
│   │   └── yearly_prompt.txt  # Yearly summary prompt
│   └── manage.py              # Django management script
│
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── EntryForm.js   # Entry creation form
│   │   │   ├── InsightCard.js # Daily insight display
│   │   │   ├── QueryInterface.js # Query/guidance interface
│   │   │   ├── HistoryView.js # Entry history and search
│   │   ├── App.js             # Main app component
│   │   ├── index.js           # React entry point
│   │   └── utils/
│   │       └── configCache.js # Configuration caching
│   ├── public/                 # Static files
│   └── package.json           # Frontend dependencies
│
├── entries/                    # Journal entries (JSON files)
│   └── YYYY-MM-DDTHH-MM-SSZ__<uuid>.json
│
├── local/                      # Local data (not in Git)
│   ├── models/                 # AI model files (if using local model)
│   ├── embeddings/             # FAISS search index
│   │   ├── faiss_index.bin    # Vector search index
│   │   └── entries_metadata.json # Entry metadata
│   ├── summaries/              # Auto-generated summaries
│   │   ├── weekly_*.json       # Weekly summaries
│   │   ├── monthly_*.json     # Monthly summaries
│   │   └── yearly_*.json       # Yearly summaries
│   └── action_items.json       # Action items storage
│
├── logs/                       # Application logs (not in Git)
│   ├── django.log              # Backend logs
│   └── react.log               # Frontend logs
│
├── scripts/                    # Utility scripts
│   ├── weekly_summary.py       # Generate weekly summaries
│   ├── monthly_summary.py      # Generate monthly summaries
│   ├── yearly_summary.py       # Generate yearly summaries
│   ├── git_sync.py             # Git synchronization
│   └── derive_entry.py         # Entry processing utilities
│
├── tests/                      # Test files
│   └── test_api.py             # API endpoint tests
│
├── config.json                 # Main configuration file
├── requirements.txt            # Python dependencies
├── start.sh                    # Start script (Mac/Linux)
├── stop.sh                     # Stop script (Mac/Linux)
├── README.md                   # Main documentation
├── SETUP.md                    # Quick setup guide
└── .gitignore                  # Git ignore rules
```

## Key Files

### Configuration
- **config.json**: Main configuration (emotions, habits, Gemini API key)
- **requirements.txt**: Python package dependencies

### Scripts
- **start.sh**: Starts both backend and frontend servers
- **stop.sh**: Stops both servers gracefully

### Data Storage
- **entries/**: Your journal entries (JSON format, synced via Git)
- **local/**: Local data (not synced, includes search index and summaries)

### Documentation
- **README.md**: Comprehensive documentation
- **SETUP.md**: Quick setup guide for non-technical users

## Data Flow

1. **Entry Creation**: User creates entry → Saved to `entries/` → Added to search index
2. **Daily Insight**: App loads recent entries → Sends to Gemini → Displays insight
3. **Query**: User asks question → RAG system searches entries → Sends context to Gemini → Returns answer
4. **Summarization**: Weekly/monthly scripts generate summaries → Stored in `local/summaries/` → Used for older context

## Token Optimization Strategy

For long-term use (year+):

1. **Recent entries** (< 7 days): Full entries used for context
2. **Older entries** (> 30 days): Summaries used instead of full entries
3. **Context limits**: Max 1500 chars (~375 tokens) per query
4. **Response limits**: 384-512 tokens for 2-3 sentence responses
5. **System instructions**: Separated from user content (more efficient)

This ensures the app remains cost-effective and responsive even with hundreds of entries.
