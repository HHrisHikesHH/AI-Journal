#!/usr/bin/env python3
"""
Archive old data after yearly summary is created.
Deletes entries, week summaries, and month summaries older than 1 year.
Keeps only year summaries.
"""
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

def archive_old_data():
    """Delete entries, week summaries, and month summaries older than 1 year."""
    today = datetime.now().date()
    one_year_ago = today - timedelta(days=365)
    cutoff_datetime = datetime.combine(one_year_ago, datetime.min.time())
    
    deleted_entries = 0
    deleted_weeks = 0
    deleted_months = 0
    
    # Delete old entries
    print(f"Checking entries older than {one_year_ago}...")
    for filepath in settings.ENTRIES_DIR.glob('*.json'):
        try:
            # Parse date from filename (format: YYYY-MM-DDTHH-MM-SSZ__uuid.json)
            filename = filepath.name
            date_part = filename.split('T')[0]
            entry_date = datetime.strptime(date_part, '%Y-%m-%d').date()
            
            if entry_date < one_year_ago:
                filepath.unlink()
                deleted_entries += 1
        except (ValueError, IndexError) as e:
            # Skip files with unexpected format
            print(f"Warning: Could not parse date from {filename}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Could not delete {filename}: {e}")
            continue
    
    # Delete old week summaries
    print(f"Checking week summaries older than {one_year_ago}...")
    for filepath in settings.SUMMARIES_DIR.glob('weekly_*.json'):
        try:
            # Parse date from filename (format: weekly_YYYY-MM-DD.json)
            filename = filepath.name
            date_part = filename.replace('weekly_', '').replace('.json', '')
            summary_date = datetime.strptime(date_part, '%Y-%m-%d').date()
            
            if summary_date < one_year_ago:
                filepath.unlink()
                deleted_weeks += 1
        except ValueError as e:
            print(f"Warning: Could not parse date from {filename}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Could not delete {filename}: {e}")
            continue
    
    # Delete old month summaries
    print(f"Checking month summaries older than {one_year_ago}...")
    for filepath in settings.SUMMARIES_DIR.glob('monthly_*.json'):
        try:
            # Parse date from filename (format: monthly_YYYY-MM.json)
            filename = filepath.name
            date_part = filename.replace('monthly_', '').replace('.json', '')
            year, month = map(int, date_part.split('-'))
            summary_date = datetime(year, month, 1).date()
            
            # Check if the month is older than 1 year
            if summary_date < datetime(one_year_ago.year, one_year_ago.month, 1).date():
                filepath.unlink()
                deleted_months += 1
        except (ValueError, IndexError) as e:
            print(f"Warning: Could not parse date from {filename}: {e}")
            continue
        except Exception as e:
            print(f"Warning: Could not delete {filename}: {e}")
            continue
    
    # Keep year summaries (don't delete them)
    print(f"\nArchive complete:")
    print(f"  Deleted {deleted_entries} old entries")
    print(f"  Deleted {deleted_weeks} old week summaries")
    print(f"  Deleted {deleted_months} old month summaries")
    print(f"  Year summaries preserved")
    
    return {
        'deleted_entries': deleted_entries,
        'deleted_weeks': deleted_weeks,
        'deleted_months': deleted_months
    }

if __name__ == '__main__':
    archive_old_data()

