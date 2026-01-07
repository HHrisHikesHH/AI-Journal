# Customization Guide

This guide explains how to customize the Personal RAG Journal to match your preferences.

## Changing Coach Identity/Tone

The coach's personality and tone are defined in the system prompt. To modify:

**File**: `backend/api/rag_system.py`

**Method**: `_build_query_prompt()`

**Current system prompt** (lines ~180-195):
```python
system_prompt = """You are a gentle, supportive personal coach. Your role is to help someone understand their patterns and make small, sustainable changes. You must:
- Never shame or judge
- Present evidence neutrally
- Give ONE small, actionable suggestion
- Be indirect and gentle in your tone
- Only use information from the provided context
- If data is insufficient, say so clearly
...
```

**To change the tone**, modify the system prompt. Examples:

- **More direct**: Change "Be indirect and gentle" to "Be clear and direct while remaining supportive"
- **More analytical**: Add "Focus on data-driven insights and patterns"
- **More empathetic**: Add "Acknowledge emotions and validate experiences"

**Also update** `scripts/weekly_summary.py` (line ~60) for weekly summary prompts.

## Adding/Removing Habit Fields

### Step 1: Update config.json

Edit `config.json` → `habits` object:

```json
{
  "habits": {
    "exercise": "Physical activity or movement",
    "deep_work": "Focused work session",
    "sleep_on_time": "Went to bed at planned time",
    "meditation": "Daily meditation practice",  // Add new habit
    "reading": "Read for 30 minutes"             // Add another
  }
}
```

### Step 2: Update Frontend

Edit `frontend/src/components/EntryForm.js`:

```javascript
const HABITS = ['exercise', 'deep_work', 'sleep_on_time', 'meditation', 'reading'];
```

### Step 3: Update Backend (if needed)

The backend automatically handles any habits in the request. No changes needed unless you want validation.

**Optional**: Add validation in `backend/api/views.py` → `create_entry()`:

```python
# Validate habits exist in config
config = json.load(open(settings.CONFIG_FILE))
valid_habits = list(config['habits'].keys())
for habit in data['habits']:
    if habit not in valid_habits:
        return JsonResponse({'error': f'Invalid habit: {habit}'}, status=400)
```

## Changing Emotion List

### Step 1: Update config.json

Edit `config.json` → `emotions` array:

```json
{
  "emotions": [
    "content",
    "anxious",
    "sad",
    "angry",
    "motivated",
    "tired",
    "calm",
    "stressed",
    "grateful",    // Add new emotion
    "frustrated"   // Add another
  ]
}
```

### Step 2: Update Frontend

Edit `frontend/src/components/EntryForm.js`:

```javascript
const EMOTIONS = [
  'content', 'anxious', 'sad', 'angry', 'motivated', 
  'tired', 'calm', 'stressed', 'grateful', 'frustrated'
];
```

The backend accepts any emotion string, so no backend changes needed.

## Modifying Reflection Questions

### Step 1: Update config.json

Edit `config.json` → `reflection_questions` array:

```json
{
  "reflection_questions": [
    "What drains my energy?",
    "Am I avoiding something important?",
    "Am I lying to myself?",
    "What patterns repeat before burnout?",
    "Am I moving closer to my long-term goals?",
    "What am I grateful for?",  // Add new question
    "Where am I growing?"       // Add another
  ]
}
```

### Step 2: Update Frontend

Edit `frontend/src/components/QueryInterface.js`:

```javascript
const SUGGESTED_QUESTIONS = [
  "What drains my energy?",
  "Am I avoiding something important?",
  // ... add your questions here
  "What am I grateful for?",
  "Where am I growing?"
];
```

## Changing User Goals

Edit `config.json` → `user` → `goals`:

```json
{
  "user": {
    "goals": ["career", "health", "relationships", "creativity", "learning"]
  }
}
```

The frontend will use this for goal selection. Update `EntryForm.js` if you want a fixed list instead of free-form.

## Customizing Entry Schema

To add new fields to entries:

### Step 1: Update Frontend Form

Edit `frontend/src/components/EntryForm.js`:

```javascript
// Add state
const [customField, setCustomField] = useState('');

// Add to form JSX
<div>
  <label>Custom Field</label>
  <input
    type="text"
    value={customField}
    onChange={(e) => setCustomField(e.target.value)}
  />
</div>

// Add to entryData
const entryData = {
  // ... existing fields
  custom_field: customField
};
```

### Step 2: Update Backend

Edit `backend/api/views.py` → `create_entry()`:

```python
entry = {
    # ... existing fields
    'custom_field': data.get('custom_field', ''),
}
```

### Step 3: Update RAG System (if searchable)

Edit `backend/api/rag_system.py` → `_get_entry_text()`:

```python
def _get_entry_text(self, entry: Dict[str, Any]) -> str:
    parts = [
        # ... existing parts
        f"Custom field: {entry.get('custom_field', '')}",
    ]
    return ' '.join(parts)
```

## Changing LLM Model

### Step 1: Download New Model

Place the model file in `local/models/`.

### Step 2: Update config.json

```json
{
  "models": {
    "llm_model_path": "local/models/your-new-model.gguf",
    "llm_model_type": "llama",  // or "gpt4all"
    "llm_max_tokens": 512,
    "llm_temperature": 0.2
  }
}
```

### Step 3: Update LLM Client (if needed)

If using a different model format, edit `backend/api/llm_client.py` → `_load_model()`.

## Adjusting Coaching Response Format

The coaching response structure is defined in:

1. **System prompt**: `backend/api/rag_system.py` → `_build_query_prompt()`
2. **Response parser**: `backend/api/rag_system.py` → `_parse_llm_response()`
3. **Formatter**: `backend/api/rag_system.py` → `_format_answer()`

To change the format (e.g., add more sections):

1. Update the system prompt to request new sections
2. Update `_parse_llm_response()` to extract new sections
3. Update `_format_answer()` to display new sections

Example: Add a "Patterns" section:

```python
# In _build_query_prompt, add:
"PATTERNS: [2-3 recurring patterns you notice]"

# In _parse_llm_response, add:
elif line.startswith('PATTERNS:'):
    result['patterns'] = line.replace('PATTERNS:', '').strip()

# In _format_answer, add:
if answer.get('patterns'):
    parts.append(f"\nPatterns: {answer['patterns']}")
```

## Changing Embedding Model

Edit `config.json`:

```json
{
  "models": {
    "embedding_model": "sentence-transformers/all-mpnet-base-v2"
  }
}
```

**Note**: Changing embedding models requires rebuilding the index. The dimension may change, so delete `local/embeddings/faiss_index.bin` and rebuild.

## Customizing Derived Fields

Edit `backend/api/entry_processor.py`:

- `_get_sentiment()`: Change sentiment analysis method
- `_extract_themes()`: Modify theme keywords or extraction logic
- `_detect_flags()`: Add new flag detection rules
- `_generate_summary()`: Change summary format

## Summary

Most customizations involve:
1. **config.json**: Central configuration
2. **Frontend components**: UI and form fields
3. **Backend views.py**: Entry creation/validation
4. **Backend rag_system.py**: Coaching prompts and logic
5. **Backend entry_processor.py**: Derived field computation

After making changes:
- Restart the app: `./stop.sh && ./start.sh`
- Rebuild index if embedding model changed
- Test with a sample entry

