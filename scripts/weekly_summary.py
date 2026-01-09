#!/usr/bin/env python3
"""
Generate weekly summary using LLM.
Creates local/summaries/weekly_YYYY-MM-DD.json
"""
import json
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

# Add backend to path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from django.conf import settings
from django import setup as django_setup
import os

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_api.settings')
django_setup()

from api.llm_adapter import call_local_llm

def _parse_llm_response(response: str) -> dict:
    """Parse LLM response into structured format."""
    result = {
        'verdict': '',
        'evidence': [],
        'action': '',
        'confidence_estimate': 0
    }
    
    # Extract VERDICT
    verdict_match = re.search(r'VERDICT:\s*(.+?)(?:\n|$)', response, re.IGNORECASE | re.MULTILINE)
    if verdict_match:
        result['verdict'] = verdict_match.group(1).strip()
    
    # Extract EVIDENCE (list items)
    evidence_section = re.search(r'EVIDENCE:\s*\n((?:- .+?\n?)+)', response, re.IGNORECASE | re.MULTILINE)
    if evidence_section:
        evidence_lines = evidence_section.group(1).strip().split('\n')
        for line in evidence_lines:
            line = line.strip()
            if line.startswith('-'):
                result['evidence'].append(line[1:].strip())
    
    # Extract ACTION
    action_match = re.search(r'ACTION:\s*(.+?)(?:\n|$)', response, re.IGNORECASE | re.MULTILINE)
    if action_match:
        result['action'] = action_match.group(1).strip()
    
    # Extract CONFIDENCE_ESTIMATE
    confidence_match = re.search(r'CONFIDENCE_ESTIMATE:\s*(\d+)', response, re.IGNORECASE)
    if confidence_match:
        try:
            result['confidence_estimate'] = int(confidence_match.group(1))
        except ValueError:
            result['confidence_estimate'] = 0
    
    return result

def _calculate_stats(entries):
    """Calculate statistics from entries."""
    if not entries:
        return {
            'entry_count': 0,
            'avg_energy': 0,
            'showed_up_rate': 0,
            'top_emotions': [],
            'habit_completion': {}
        }
    
    # Calculate averages
    total_energy = sum(e.get('energy', 5) for e in entries)
    avg_energy = total_energy / len(entries) if entries else 0
    
    # Showed up rate
    showed_up_count = sum(1 for e in entries if e.get('showed_up', False))
    showed_up_rate = showed_up_count / len(entries) if entries else 0
    
    # Top emotions
    emotions = [e.get('emotion', 'unknown') for e in entries]
    emotion_counts = Counter(emotions)
    top_emotions = [emotion for emotion, _ in emotion_counts.most_common(3)]
    
    # Habit completion
    habit_completion = {}
    all_habits = set()
    for entry in entries:
        if entry.get('habits'):
            all_habits.update(entry['habits'].keys())
    
    for habit in all_habits:
        completed = sum(1 for e in entries if e.get('habits', {}).get(habit, False))
        habit_completion[habit] = completed
    
    return {
        'entry_count': len(entries),
        'avg_energy': round(avg_energy, 1),
        'showed_up_rate': round(showed_up_rate, 2),
        'top_emotions': top_emotions,
        'habit_completion': habit_completion
    }

def generate_weekly_summary():
    """Generate weekly summary for the last 7 days."""
    # Get last 7 days of entries
    today = datetime.now().date()
    week_start = today - timedelta(days=7)
    cutoff_date = datetime.combine(week_start, datetime.min.time())
    
    entries = []
    source_entries = []
    
    for filepath in sorted(settings.ENTRIES_DIR.glob('*.json')):
        try:
            with open(filepath, 'r') as f:
                entry = json.load(f)
                entry_timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                if entry_timestamp.replace(tzinfo=None) >= cutoff_date:
                    entries.append(entry)
                    # Store filename for source_entries
                    filename = filepath.name
                    source_entries.append(filename)
        except Exception as e:
            print(f"Error reading entry {filepath}: {e}")
            continue
    
    # Sort entries by date (oldest first for date range)
    entries.sort(key=lambda e: e.get('timestamp', ''))
    
    # Calculate date range
    if entries:
        first_date = entries[0].get('timestamp', '')[:10]
        last_date = entries[-1].get('timestamp', '')[:10]
        date_range = {'start': first_date, 'end': last_date}
    else:
        date_range = {'start': str(week_start), 'end': str(today)}
    
    # Calculate stats
    stats = _calculate_stats(entries)
    
    # Check if we have enough entries
    if len(entries) < 3:
        summary_parsed = {
            'verdict': 'Insufficient data to make a confident conclusion about weekly patterns.',
            'evidence': [],
            'action': 'Continue journaling to build a clearer picture.',
            'confidence_estimate': 0
        }
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
        except Exception as e:
            print(f"Error loading prompt template: {e}")
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
            summary_text = call_local_llm(prompt, max_tokens=256, temp=0.2)
            summary_parsed = _parse_llm_response(summary_text)
        except Exception as e:
            print(f"Error generating weekly summary: {e}")
            summary_parsed = {
                'verdict': 'Unable to generate summary at this time.',
                'evidence': [],
                'action': 'Continue journaling.',
                'confidence_estimate': 0
            }
    
    # Build summary JSON structure
    summary_id = f"weekly_{today}"
    summary_data = {
        'id': summary_id,
        'type': 'week',
        'date_range': date_range,
        'source_entries': source_entries,
        'summary': summary_parsed,
        'stats': stats,
        'created_at': datetime.now().isoformat() + 'Z'
    }
    
    # Save summary as JSON
    summary_file = settings.SUMMARIES_DIR / f"weekly_{today}.json"
    settings.SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    print(f"Weekly summary saved to: {summary_file}")
    print(f"Summary: {summary_parsed.get('verdict', '')[:60]}...")
    return summary_file

if __name__ == '__main__':
    generate_weekly_summary()
