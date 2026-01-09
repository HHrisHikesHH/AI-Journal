# Quick Setup Guide

## For Non-Technical Users

### What You Need
1. A computer (Mac, Windows, or Linux)
2. Internet connection
3. A Google account (for Gemini API key)

### Step-by-Step Setup (5 minutes)

#### Step 1: Get Your API Key (2 minutes)
1. Open your web browser
2. Go to: https://aistudio.google.com/
3. Sign in with your Google account
4. Click "Get API Key"
5. Click "Create API Key"
6. Copy the key (it starts with `AIzaSy...`)

#### Step 2: Configure the App (1 minute)
1. Open the `config.json` file (double-click it)
2. Find this line: `"gemini_api_key": "YOUR_API_KEY_HERE"`
3. Replace `YOUR_API_KEY_HERE` with your copied API key
4. Save the file (Ctrl+S or Cmd+S)

#### Step 3: Install Dependencies (2 minutes)

**On Mac/Linux:**
1. Open Terminal
2. Type: `cd ` (with a space after cd)
3. Drag the `rag_project` folder into Terminal
4. Press Enter
5. Type: `./start.sh` and press Enter
6. Wait for "✅ Personal RAG Journal is running!"

**On Windows:**
1. Open Command Prompt
2. Type: `cd ` (with a space after cd)
3. Drag the `rag_project` folder into Command Prompt
4. Press Enter
5. Type: `start.sh` and press Enter
6. Wait for "✅ Personal RAG Journal is running!"

#### Step 4: Use the App
1. Your browser should open automatically
2. If not, go to: http://localhost:3000
3. Create your first entry!

### Troubleshooting

**"Command not found" or "Permission denied"**
- On Mac/Linux: Type `chmod +x start.sh stop.sh` first
- On Windows: Make sure you're using Command Prompt, not PowerShell

**"Python not found"**
- Install Python from https://www.python.org/
- Make sure to check "Add Python to PATH" during installation

**"npm not found"**
- Install Node.js from https://nodejs.org/
- Download the LTS version

**"API Key Error"**
- Double-check your API key in `config.json`
- Make sure there are no extra spaces
- Verify the key works at https://aistudio.google.com/

### Need Help?
Check the main README.md file for more detailed instructions.

