#!/usr/bin/env python3
"""
Generate yearly summary using LLM.
Summarizes month summaries from the last year into a year summary.
Creates local/summaries/yearly_YYYY.json
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

def _aggregate_month_stats(month_summaries):
    """Aggregate statistics from month summaries."""
    if not month_summaries:
        return {
            'month_count': 0,
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
    
    for month in month_summaries:
        stats = month.get('stats', {})
        total_entries += stats.get('total_entry_count', 0)
        total_energy += stats.get('avg_energy', 0) * stats.get('total_entry_count', 0)
        total_showed_up += stats.get('avg_showed_up_rate', 0) * stats.get('total_entry_count', 0)
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
        'month_count': len(month_summaries),
        'total_entry_count': total_entries,
        'avg_energy': round(avg_energy, 1),
        'avg_showed_up_rate': round(avg_showed_up_rate, 2),
        'top_emotions': top_emotions,
        'habit_completion': habit_completion
    }

def generate_yearly_summary():
    """Generate yearly summary for the last year."""
    today = datetime.now().date()
    last_year = today.year - 1
    
    # Get first and last day of last year
    year_start = datetime(last_year, 1, 1).date()
    year_end = datetime(last_year, 12, 31).date()
    
    date_range = {
        'start': str(year_start),
        'end': str(year_end)
    }
    
    # Load all month summaries from last year
    month_summaries = []
    source_months = []
    
    summaries_dir = settings.SUMMARIES_DIR
    for filepath in sorted(summaries_dir.glob('monthly_*.json')):
        try:
            with open(filepath, 'r') as f:
                month_data = json.load(f)
                month_date_range = month_data.get('date_range', {})
                month_start = month_date_range.get('start', '')
                
                # Check if this month is in last year
                if month_start:
                    month_start_date = datetime.fromisoformat(month_start).date()
                    if year_start <= month_start_date <= year_end:
                        month_summaries.append(month_data)
                        source_months.append(filepath.name)
        except Exception as e:
            print(f"Error reading month summary {filepath}: {e}")
            continue
    
    # Sort by date (oldest first)
    month_summaries.sort(key=lambda m: m.get('date_range', {}).get('start', ''))
    
    # Aggregate stats
    stats = _aggregate_month_stats(month_summaries)
    
    # Check if we have enough month summaries
    if len(month_summaries) < 3:
        summary_parsed = {
            'verdict': 'Insufficient data to make a confident conclusion about yearly patterns.',
            'evidence': [],
            'action': 'Continue journaling to build a clearer picture.',
            'confidence_estimate': 0
        }
    else:
        # Build context from month summaries
        context_parts = []
        for month in month_summaries:
            month_id = month.get('id', 'unknown')
            month_date_range = month.get('date_range', {})
            month_summary = month.get('summary', {})
            month_stats = month.get('stats', {})
            
            context_parts.append(f"Month Summary {month_id} ({month_date_range.get('start', '')} to {month_date_range.get('end', '')}):")
            context_parts.append(f"  Verdict: {month_summary.get('verdict', 'N/A')}")
            context_parts.append(f"  Evidence: {', '.join(month_summary.get('evidence', [])[:2])}")
            context_parts.append(f"  Action: {month_summary.get('action', 'N/A')}")
            context_parts.append(f"  Stats: {month_stats.get('total_entry_count', 0)} entries, avg energy {month_stats.get('avg_energy', 0)}/10")
            context_parts.append("")
        
        context = '\n'.join(context_parts)
        
        # Load yearly prompt template
        prompt_path = Path(__file__).parent.parent / 'backend' / 'prompts' / 'yearly_prompt.txt'
        try:
            with open(prompt_path, 'r') as f:
                template = f.read()
            prompt = template.format(context=context)
        except Exception as e:
            print(f"Error loading prompt template: {e}")
            # Fallback
            prompt = f"""You are a gentle, supportive personal coach. Analyze the past year's monthly summaries and provide insights.

Context from monthly summaries:
{context}

Analyze patterns across the year and provide:
VERDICT: [One sentence neutral observation about the year]
EVIDENCE:
- [Evidence item 1 with source month filename]
- [Evidence item 2 with source month filename]
- [Evidence item 3 with source month filename]
ACTION: [One small, specific action for the coming year]
CONFIDENCE_ESTIMATE: [Integer 0-100]

Use only the CONTEXT provided. Cite filenames. One-line verdict. Two to three evidence bullets with filenames. One micro-action. Confidence_estimate."""
        
        # Call LLM
        try:
            summary_text = call_local_llm(prompt, max_tokens=256, temp=0.2)
            summary_parsed = _parse_llm_response(summary_text)
        except Exception as e:
            print(f"Error generating yearly summary: {e}")
            summary_parsed = {
                'verdict': 'Unable to generate summary at this time.',
                'evidence': [],
                'action': 'Continue journaling.',
                'confidence_estimate': 0
            }
    
    # Build summary JSON structure
    year_id = f"yearly_{last_year}"
    summary_data = {
        'id': year_id,
        'type': 'year',
        'date_range': date_range,
        'source_months': source_months,
        'summary': summary_parsed,
        'stats': stats,
        'created_at': datetime.now().isoformat() + 'Z'
    }
    
    # Save summary as JSON
    summary_file = settings.SUMMARIES_DIR / f"yearly_{last_year}.json"
    settings.SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    print(f"Yearly summary saved to: {summary_file}")
    print(f"Summary: {summary_parsed.get('verdict', '')[:60]}...")
    
    # Delete summarized month summary files
    deleted_count = 0
    for month_filename in source_months:
        month_file = summaries_dir / month_filename
        if month_file.exists():
            try:
                month_file.unlink()
                deleted_count += 1
            except Exception as e:
                print(f"Warning: Could not delete {month_filename}: {e}")
    
    print(f"Deleted {deleted_count} month summary files")
    return summary_file

if __name__ == '__main__':
    generate_yearly_summary()

