#!/usr/bin/env python3
"""
Generate weekly summary using LLM.
Creates local/summaries/weekly_summary_YYYY-MM-DD.txt
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from django.conf import settings
from django import setup as django_setup
import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_api.settings')
django_setup()

from api.rag_system import RAGSystem
from api.llm_adapter import call_local_llm

def generate_weekly_summary():
    """Generate weekly summary for the last 7 days."""
    # Get last 7 days of entries
    cutoff_date = datetime.now() - timedelta(days=7)
    entries = []
    
    for filepath in sorted(settings.ENTRIES_DIR.glob('*.json')):
        try:
            with open(filepath, 'r') as f:
                entry = json.load(f)
                entry_timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                if entry_timestamp.replace(tzinfo=None) >= cutoff_date:
                    entries.append(entry)
        except Exception:
            continue
    
    # Check if we have enough entries
    if len(entries) < 3:
        summary_text = """VERDICT: Insufficient data to make a confident conclusion about weekly patterns.
EVIDENCE: []
ACTION: Continue journaling to build a clearer picture.
CONFIDENCE_ESTIMATE: 0"""
    else:
        # Build context
        context_parts = []
        for entry in entries:
            entry_date = entry.get('timestamp', '')[:10]
            filename = f"{entry.get('timestamp', '').replace(':', '-').split('.')[0]}Z__{entry.get('id', '')}.json"
            context_parts.append(f"Entry from {entry_date} ({filename}):")
            context_parts.append(f"  Emotion: {entry.get('emotion', 'N/A')}")
            context_parts.append(f"  Energy: {entry.get('energy', 'N/A')}")
            context_parts.append(f"  Showed up: {entry.get('showed_up', False)}")
            if entry.get('free_text'):
                context_parts.append(f"  Note: {entry.get('free_text')}")
            if entry.get('long_reflection'):
                context_parts.append(f"  Reflection: {entry.get('long_reflection')[:200]}...")
        
        context = '\n'.join(context_parts)
        
        # Load weekly prompt template
        prompt_path = Path(__file__).parent.parent / 'backend' / 'prompts' / 'weekly_prompt.txt'
        try:
            with open(prompt_path, 'r') as f:
                template = f.read()
            prompt = template.format(context=context)
        except Exception:
            # Fallback
            prompt = f"""You are a gentle, supportive personal coach analyzing the past week's journal entries.

Context from journal entries:
{context}

Analyze the patterns from the last 7 days and provide:
VERDICT: [One sentence neutral observation about the week]
EVIDENCE:
- [Evidence item 1 with source filename]
- [Evidence item 2 with source filename]
- [Evidence item 3 with source filename]
ACTION: [One small, specific action for the coming week]
CONFIDENCE_ESTIMATE: [Integer 0-100, where 20 * number_of_sources_used, capped at 100]

Use only the CONTEXT provided. Cite filenames. One-line verdict. Two evidence bullets with filenames. One micro-action. Confidence_estimate."""
        
        # Call LLM
        try:
            summary_text = call_local_llm(prompt, max_tokens=512, temp=0.2)
        except Exception as e:
            print(f"Error generating weekly summary: {e}")
            summary_text = f"""VERDICT: Unable to generate summary at this time.
EVIDENCE: []
ACTION: Continue journaling.
CONFIDENCE_ESTIMATE: 0
Error: {str(e)}"""
    
    # Save summary
    today = datetime.now().date()
    summary_file = settings.SUMMARIES_DIR / f"weekly_summary_{today}.txt"
    settings.SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(summary_file, 'w') as f:
        f.write(f"Weekly Summary for {today}\n")
        f.write("=" * 70 + "\n\n")
        f.write(summary_text)
    
    print(f"Weekly summary saved to: {summary_file}")
    return summary_file

if __name__ == '__main__':
    generate_weekly_summary()
