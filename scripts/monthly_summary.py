#!/usr/bin/env python3
"""
Generate monthly summary using LLM.
Summarizes week summaries from the last month into a month summary.
Creates local/summaries/monthly_YYYY-MM.json
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

def _aggregate_week_stats(week_summaries):
    """Aggregate statistics from week summaries."""
    if not week_summaries:
        return {
            'week_count': 0,
            'total_entry_count': 0,
            'avg_energy': 0,
            'avg_showed_up_rate': 0,
            'top_emotions': [],
            'habit_completion': {}
        }
    
    total_entries = 0
    total_energy = 0
    total_showed_up = 0
    all_emotions = []
    habit_completion = {}
    
    for week in week_summaries:
        stats = week.get('stats', {})
        total_entries += stats.get('entry_count', 0)
        total_energy += stats.get('avg_energy', 0) * stats.get('entry_count', 0)
        total_showed_up += stats.get('showed_up_rate', 0) * stats.get('entry_count', 0)
        all_emotions.extend(stats.get('top_emotions', []))
        
        # Aggregate habit completion
        for habit, count in stats.get('habit_completion', {}).items():
            habit_completion[habit] = habit_completion.get(habit, 0) + count
    
    avg_energy = total_energy / total_entries if total_entries > 0 else 0
    avg_showed_up_rate = total_showed_up / total_entries if total_entries > 0 else 0
    
    # Top emotions
    emotion_counts = Counter(all_emotions)
    top_emotions = [emotion for emotion, _ in emotion_counts.most_common(5)]
    
    return {
        'week_count': len(week_summaries),
        'total_entry_count': total_entries,
        'avg_energy': round(avg_energy, 1),
        'avg_showed_up_rate': round(avg_showed_up_rate, 2),
        'top_emotions': top_emotions,
        'habit_completion': habit_completion
    }

def generate_monthly_summary():
    """Generate monthly summary for the last month."""
    today = datetime.now().date()
    
    # Calculate last month's date range
    if today.month == 1:
        last_month = 12
        last_year = today.year - 1
    else:
        last_month = today.month - 1
        last_year = today.year
    
    # Get first and last day of last month
    if last_month == 12:
        next_month_start = datetime(last_year + 1, 1, 1).date()
    else:
        next_month_start = datetime(last_year, last_month + 1, 1).date()
    
    last_month_start = datetime(last_year, last_month, 1).date()
    last_month_end = next_month_start - timedelta(days=1)
    
    date_range = {
        'start': str(last_month_start),
        'end': str(last_month_end)
    }
    
    # Load all week summaries from last month
    week_summaries = []
    source_weeks = []
    
    summaries_dir = settings.SUMMARIES_DIR
    for filepath in sorted(summaries_dir.glob('weekly_*.json')):
        try:
            with open(filepath, 'r') as f:
                week_data = json.load(f)
                week_date_range = week_data.get('date_range', {})
                week_start = week_date_range.get('start', '')
                
                # Check if this week is in last month
                if week_start:
                    week_start_date = datetime.fromisoformat(week_start).date()
                    if last_month_start <= week_start_date <= last_month_end:
                        week_summaries.append(week_data)
                        source_weeks.append(filepath.name)
        except Exception as e:
            print(f"Error reading week summary {filepath}: {e}")
            continue
    
    # Sort by date (oldest first)
    week_summaries.sort(key=lambda w: w.get('date_range', {}).get('start', ''))
    
    # Aggregate stats
    stats = _aggregate_week_stats(week_summaries)
    
    # Check if we have enough week summaries
    if len(week_summaries) < 2:
        summary_parsed = {
            'verdict': 'Insufficient data to make a confident conclusion about monthly patterns.',
            'evidence': [],
            'action': 'Continue journaling to build a clearer picture.',
            'confidence_estimate': 0
        }
    else:
        # Build context from week summaries
        context_parts = []
        for week in week_summaries:
            week_id = week.get('id', 'unknown')
            week_date_range = week.get('date_range', {})
            week_summary = week.get('summary', {})
            week_stats = week.get('stats', {})
            
            context_parts.append(f"Week Summary {week_id} ({week_date_range.get('start', '')} to {week_date_range.get('end', '')}):")
            context_parts.append(f"  Verdict: {week_summary.get('verdict', 'N/A')}")
            context_parts.append(f"  Evidence: {', '.join(week_summary.get('evidence', [])[:2])}")
            context_parts.append(f"  Action: {week_summary.get('action', 'N/A')}")
            context_parts.append(f"  Stats: {week_stats.get('entry_count', 0)} entries, avg energy {week_stats.get('avg_energy', 0)}/10, showed up {week_stats.get('showed_up_rate', 0)*100:.0f}%")
            context_parts.append("")
        
        context = '\n'.join(context_parts)
        
        # Load monthly prompt template
        prompt_path = Path(__file__).parent.parent / 'backend' / 'prompts' / 'monthly_prompt.txt'
        try:
            with open(prompt_path, 'r') as f:
                template = f.read()
            prompt = template.format(context=context)
        except Exception as e:
            print(f"Error loading prompt template: {e}")
            # Fallback
            prompt = f"""You are a gentle, supportive personal coach. Analyze the past month's weekly summaries and provide insights.

Context from weekly summaries:
{context}

Analyze patterns across the month and provide:
VERDICT: [One sentence neutral observation about the month]
EVIDENCE:
- [Evidence item 1 with source week filename]
- [Evidence item 2 with source week filename]
- [Evidence item 3 with source week filename]
ACTION: [One small, specific action for the coming month]
CONFIDENCE_ESTIMATE: [Integer 0-100]

Use only the CONTEXT provided. Cite filenames. One-line verdict. Two to three evidence bullets with filenames. One micro-action. Confidence_estimate."""
        
        # Call LLM
        try:
            summary_text = call_local_llm(prompt, max_tokens=256, temp=0.2)
            summary_parsed = _parse_llm_response(summary_text)
        except Exception as e:
            print(f"Error generating monthly summary: {e}")
            summary_parsed = {
                'verdict': 'Unable to generate summary at this time.',
                'evidence': [],
                'action': 'Continue journaling.',
                'confidence_estimate': 0
            }
    
    # Build summary JSON structure
    month_id = f"monthly_{last_year}-{last_month:02d}"
    summary_data = {
        'id': month_id,
        'type': 'month',
        'date_range': date_range,
        'source_weeks': source_weeks,
        'summary': summary_parsed,
        'stats': stats,
        'created_at': datetime.now().isoformat() + 'Z'
    }
    
    # Save summary as JSON
    summary_file = settings.SUMMARIES_DIR / f"monthly_{last_year}-{last_month:02d}.json"
    settings.SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    print(f"Monthly summary saved to: {summary_file}")
    print(f"Summary: {summary_parsed.get('verdict', '')[:60]}...")
    
    # Delete summarized week summary files
    deleted_count = 0
    for week_filename in source_weeks:
        week_file = summaries_dir / week_filename
        if week_file.exists():
            try:
                week_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Warning: Could not delete {week_filename}: {e}")
    
    print(f"Deleted {deleted_count} week summary files")
    return summary_file

if __name__ == '__main__':
    generate_monthly_summary()

