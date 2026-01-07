#!/usr/bin/env python3
"""
Standalone script to derive fields for an entry file.
Can be run on a single entry or all entries.
"""
import json
import sys
from pathlib import Path

# Add backend to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from api.entry_processor import EntryProcessor

def process_entry_file(filepath):
    """Process a single entry file."""
    try:
        with open(filepath, 'r') as f:
            entry = json.load(f)
        
        processor = EntryProcessor()
        entry = processor.process_entry(entry)
        
        # Write back
        with open(filepath, 'w') as f:
            json.dump(entry, f, indent=2)
        
        print(f"Processed: {filepath.name}")
        return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    if len(sys.argv) > 1:
        # Process specific file
        filepath = Path(sys.argv[1])
        if filepath.exists():
            process_entry_file(filepath)
        else:
            print(f"File not found: {filepath}")
    else:
        # Process all entries
        entries_dir = PROJECT_ROOT / 'entries'
        count = 0
        for filepath in entries_dir.glob('*.json'):
            if process_entry_file(filepath):
                count += 1
        print(f"Processed {count} entries")

if __name__ == '__main__':
    main()

