#!/usr/bin/env python3
"""
Generate weekly summary using LLM.
Should be run via cron weekly.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

import os
from django.conf import settings
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_api.settings')
django.setup()

from api.llm_client import LLMClient

def load_weekly_entries():
    """Load entries from the past week."""
    entries = []
    cutoff = datetime.now() - timedelta(days=7)
    
    for filepath in sorted(settings.ENTRIES_DIR.glob('*.json')):
        try:
            with open(filepath, 'r') as f:
                entry = json.load(f)
                entry_date = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                if entry_date.replace(tzinfo=None) >= cutoff:
                    entries.append(entry)
        except Exception:
            continue
    
    return entries

def build_weekly_context(entries):
    """Build context string from weekly entries."""
    if not entries:
        return "No entries this week."
    
    # Aggregate stats
    emotions = defaultdict(int)
    total_energy = 0
    showed_up_count = 0
    habit_counts = defaultdict(int)
    
    for entry in entries:
        emotions[entry.get('emotion', 'unknown')] += 1
        total_energy += entry.get('energy', 5)
        if entry.get('showed_up'):
            showed_up_count += 1
        for habit, completed in entry.get('habits', {}).items():
            if completed:
                habit_counts[habit] += 1
    
    context_parts = [
        f"Week Summary ({len(entries)} entries):",
        f"  Most common emotions: {dict(emotions)}",
        f"  Average energy: {total_energy / len(entries):.1f}/10",
        f"  Showed up: {showed_up_count}/{len(entries)} days",
        f"  Habit completions: {dict(habit_counts)}",
        "",
        "Recent reflections:"
    ]
    
    for entry in entries[-5:]:  # Last 5 entries
        date = entry['timestamp'][:10]
        context_parts.append(f"  {date}: {entry.get('free_text', '')[:100]}")
    
    return '\n'.join(context_parts)

def generate_weekly_summary():
    """Generate weekly summary using LLM."""
    entries = load_weekly_entries()
    context = build_weekly_context(entries)
    
    prompt = f"""You are a gentle, supportive personal coach. Review this week's journal entries and provide a weekly reflection.

{context}

Provide a gentle weekly reflection following this structure:
REALITY_CHECK: [One sentence neutral observation about the week]
EVIDENCE:
- [Key pattern or insight 1]
- [Key pattern or insight 2]
- [Key pattern or insight 3]
ACTION: [One small, specific action for the coming week]
SIGN_OFF: [Gentle closing phrase]

Be indirect, supportive, and never judgmental."""

    llm_client = LLMClient()
    summary = llm_client.generate(prompt, max_tokens=512, temperature=0.2)
    
    # Save summary
    summary_date = datetime.now().strftime('%Y-%m-%d')
    summary_file = settings.SUMMARIES_DIR / f'weekly_summary_{summary_date}.txt'
    
    with open(summary_file, 'w') as f:
        f.write(f"Weekly Summary - {summary_date}\n")
        f.write("=" * 50 + "\n\n")
        f.write(summary)
        f.write("\n\n")
        f.write("=" * 50 + "\n")
        f.write(f"Based on {len(entries)} entries from the past week.\n")
    
    print(f"Weekly summary saved to: {summary_file}")
    return summary_file

if __name__ == '__main__':
    generate_weekly_summary()

