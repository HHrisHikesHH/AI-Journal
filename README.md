# Personal RAG Journal & AI Coaching App

A private, local-first journaling application with AI-powered coaching insights. Your data stays on your device, and the app uses Google's Gemini AI to provide thoughtful, supportive insights about your patterns and habits.

## 🚀 Quick Start (For Everyone)

### Step 1: Get Your Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" and create a new key
4. Copy your API key (it looks like: `AIzaSy...`)

### Step 2: Set Up the App

1. **Open Terminal** (on Mac/Linux) or **Command Prompt** (on Windows)

2. **Navigate to the project folder:**
   ```bash
   cd /path/to/rag_project
   ```

3. **Make scripts executable** (Mac/Linux only):
   ```bash
   chmod +x start.sh stop.sh
   ```

4. **Edit the configuration file:**
   - Open `config.json` in any text editor
   - Find the line: `"gemini_api_key": "YOUR_API_KEY_HERE"`
   - Replace `YOUR_API_KEY_HERE` with your actual API key from Step 1
   - Save the file

### Step 3: Install Dependencies

**On Mac/Linux:**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

**On Windows:**
```cmd
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Step 4: Start the App

**On Mac/Linux:**
```bash
./start.sh
```

**On Windows:**
```cmd
start.sh
```

The app will:
- Start the backend server on http://localhost:8000
- Start the frontend on http://localhost:3000
- Open automatically in your browser

### Step 5: Use the App

1. **Open your browser** and go to: http://localhost:3000
2. **Create your first entry:**
   - Click "New Entry" or use the "Reflect" tab
   - Select your emotion
   - Rate your energy (1-10)
   - Toggle "Showed Up" if you completed your daily practice
   - Add a brief note (required, max 200 characters)
   - Optionally add a longer reflection
   - Click "Save Entry"

3. **View your daily insight:**
   - The app shows a daily AI-generated insight when you open it
   - This updates once per day automatically

4. **Ask questions:**
   - Use the "Seeking Guidance" section to ask questions about your patterns
   - Example: "What patterns do you notice in my energy levels?"

### Step 6: Stop the App

**On Mac/Linux:**
```bash
./stop.sh
```

**On Windows:**
```cmd
stop.sh
```

Or simply press `Ctrl+C` in the terminal where the app is running.

## 📁 Project Structure

```
rag_project/
├── backend/              # Python backend (Django)
│   ├── api/              # API endpoints and logic
│   ├── journal_api/      # Django settings
│   └── prompts/          # AI prompt templates
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   └── App.js        # Main app component
│   └── package.json      # Frontend dependencies
├── entries/              # Your journal entries (JSON files)
├── local/                # Local data (not synced)
│   ├── models/           # AI model files (if using local model)
│   ├── embeddings/       # Search index
│   └── summaries/        # Weekly/monthly summaries
├── logs/                 # Application logs
├── scripts/              # Utility scripts
├── config.json           # Configuration file (EDIT THIS!)
├── start.sh              # Start script
├── stop.sh               # Stop script
└── requirements.txt      # Python dependencies
```

## ⚙️ Configuration

Edit `config.json` to customize:

- **Emotions**: List of emotions you can select
- **Habits**: Habits you want to track
- **Goals**: Your personal goals
- **Gemini API Key**: Your Google Gemini API key (required)

Example:
```json
{
  "models": {
    "gemini_api_key": "AIzaSy...your-key-here..."
  },
  "emotions": ["content", "anxious", "sad", "happy", "tired"],
  "habits": {
    "exercise": "Physical activity",
    "meditation": "Meditation practice"
  }
}
```

## 💡 Features

### Daily Insights
- **Automatic insights** when you open the app
- **AI-powered analysis** of your recent entries
- **Gentle, supportive coaching** style
- **Evidence-based observations** with source citations

### Journal Entries
- **Entry creation** through the Reflect tab
- **Track emotions, energy, and habits**
- **Optional longer reflections**
- **All data stored locally** on your device

### Seeking Guidance
- **Ask questions** about your patterns
- **Semantic search** through your entries
- **Contextual answers** based on your journal history
- **Actionable suggestions**

### Long-Term Context Management
- **Automatic summarization** of older entries
- **Smart context selection** (recent entries + relevant summaries)
- **Token-optimized** for year-long usage
- **Maintains relevance** without losing context

## 🔧 Troubleshooting

### "API Key Error" or "Gemini not working"
- Check that your API key is correctly set in `config.json`
- Make sure there are no extra spaces or quotes around the key
- Verify your API key is active at [Google AI Studio](https://aistudio.google.com/)

### "Port already in use"
- The app uses ports 8000 (backend) and 3000 (frontend)
- Close other applications using these ports
- Or run: `lsof -ti:8000 | xargs kill -9` (Mac/Linux)

### "Module not found" errors
- Make sure you activated the virtual environment: `source venv/bin/activate`
- Reinstall dependencies: `pip install -r requirements.txt`

### App won't start
- Check the logs in `logs/django.log` and `logs/react.log`
- Make sure Python 3.11+ is installed: `python3 --version`
- Make sure Node.js 18+ is installed: `node --version`

### Responses are too short
- The app is configured for 2-3 sentence responses
- If responses seem incomplete, check your API key has sufficient quota
- Try refreshing the insight or query

## 📊 Data Management

### Where Your Data Lives
- **Entries**: `entries/` folder (JSON files)
- **Summaries**: `local/summaries/` (auto-generated)
- **Search Index**: `local/embeddings/` (auto-generated)

### Backup Your Data
Your entries are stored as JSON files in the `entries/` folder. To backup:
1. Copy the entire `entries/` folder
2. Or use Git to sync (if configured)

### Export Data
- Use the "Export" feature in the app
- Or manually copy files from `entries/` folder

## 🎯 Best Practices

1. **Journal regularly** - Daily entries provide better insights
2. **Be honest** - The AI is supportive and non-judgmental
3. **Use "Showed Up"** - Track consistency in your habits
4. **Review insights** - Check your daily insights to notice patterns
5. **Ask questions** - Use "Seeking Guidance" to explore your patterns

## 🔒 Privacy & Security

- **All data stays local** - Your entries are stored on your device
- **No cloud storage** - Unless you configure Git sync
- **API calls** - Only your journal entries (not personal info) are sent to Gemini
- **No tracking** - The app doesn't track or share your data

## 📝 Token Optimization

The app is optimized for long-term use:

- **Smart summarization**: Older entries (>30 days) are automatically summarized
- **Context limits**: Recent entries prioritized, summaries used for older data
- **Efficient prompts**: System instructions separated for better token usage
- **Response limits**: 2-3 sentence responses (384-512 tokens) for quality and cost control

This means you can use the app for a year or more without running into token limits or high costs.

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs**: `logs/django.log` and `logs/react.log`
2. **Verify configuration**: Make sure `config.json` is correct
3. **Check dependencies**: Ensure all packages are installed
4. **Restart the app**: Stop and start again

## 📄 License

Private use only. All data stays local.

---

**Made with care for your personal growth journey.** 🌱
