#!/usr/bin/env python3
"""
Create realistic test entries for a week to test insights and patterns.
"""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Get project root
project_root = Path(__file__).parent.parent
entries_dir = project_root / 'entries'
entries_dir.mkdir(exist_ok=True)

# Load config to get valid emotions and habits
config_path = project_root / 'config.json'
with open(config_path, 'r') as f:
    config = json.load(f)

emotions = config.get('emotions', [])
habits_config = config.get('habits', {})
habits_list = list(habits_config.keys())

# Realistic week-long journal entries with varied patterns
test_entries = [
    # Day 1 - Monday - Good start
    {
        'emotion': 'motivated',
        'energy': 8,
        'showed_up': True,
        'habits': {'exercise': True, 'deep_work': True, 'meditation': False, 'reading': True},
        'free_text': 'Started the week strong. Completed morning workout and had a productive deep work session. Feeling energized.',
        'long_reflection': 'The morning routine really set the tone. Exercise gave me clarity and the deep work session was focused. Need to add meditation tomorrow.',
        'goals': ['career', 'health']
    },
    # Day 2 - Tuesday - Slight dip
    {
        'emotion': 'calm',
        'energy': 6,
        'showed_up': True,
        'habits': {'exercise': False, 'deep_work': True, 'meditation': True, 'reading': False},
        'free_text': 'Felt more balanced today. Skipped exercise but did meditation. Deep work was steady but not as intense.',
        'long_reflection': 'Meditation helped center me. I notice when I skip exercise, my energy is lower. Need to maintain consistency.',
        'goals': ['career', 'health']
    },
    # Day 3 - Wednesday - Stress building
    {
        'emotion': 'stressed',
        'energy': 5,
        'showed_up': True,
        'habits': {'exercise': True, 'deep_work': True, 'meditation': False, 'reading': False},
        'free_text': 'Work pressure mounting. Did exercise but felt rushed. Deep work was interrupted by meetings.',
        'long_reflection': 'The stress is building. I exercised but it felt forced. Meetings broke my flow. Need to protect deep work time better.',
        'goals': ['career']
    },
    # Day 4 - Thursday - Low energy
    {
        'emotion': 'tired',
        'energy': 4,
        'showed_up': False,
        'habits': {'exercise': False, 'deep_work': False, 'meditation': False, 'reading': True},
        'free_text': 'Exhausted today. Couldn\'t muster energy for much. Just read a bit in the evening.',
        'long_reflection': 'Hit a wall today. No exercise, no deep work. Just reading helped me unwind. Need to rest properly tonight.',
        'goals': ['health']
    },
    # Day 5 - Friday - Recovery
    {
        'emotion': 'content',
        'energy': 7,
        'showed_up': True,
        'habits': {'exercise': True, 'deep_work': True, 'meditation': True, 'reading': False},
        'free_text': 'Better day after rest. Got back to exercise and deep work. Meditation helped reset my mindset.',
        'long_reflection': 'The rest yesterday helped. Today felt like a reset. All three habits - exercise, deep work, meditation - made a difference.',
        'goals': ['career', 'health']
    },
    # Day 6 - Saturday - Weekend energy
    {
        'emotion': 'grateful',
        'energy': 8,
        'showed_up': True,
        'habits': {'exercise': True, 'deep_work': False, 'meditation': True, 'reading': True},
        'free_text': 'Weekend energy is different. Long morning run, meditation, and reading. No deep work but that\'s okay.',
        'long_reflection': 'Weekends feel more spacious. Exercise was longer, meditation deeper. Reading for pleasure instead of work. This balance feels right.',
        'goals': ['health', 'relationships']
    },
    # Day 7 - Sunday - Reflection day
    {
        'emotion': 'calm',
        'energy': 6,
        'showed_up': True,
        'habits': {'exercise': False, 'deep_work': False, 'meditation': True, 'reading': True, 'writing': True},
        'free_text': 'Quiet Sunday. Meditation, reading, and some writing. Reflecting on the week.',
        'long_reflection': 'Good week overall. Started strong, hit a low mid-week, recovered well. The pattern shows I need better rest management. Exercise and meditation are key.',
        'goals': ['health']
    },
    # Day 8 - Monday - New week, anxious start
    {
        'emotion': 'anxious',
        'energy': 5,
        'showed_up': True,
        'habits': {'exercise': True, 'deep_work': True, 'meditation': False, 'reading': False},
        'free_text': 'New week anxiety. Did the habits but felt scattered. Need to find focus.',
        'long_reflection': 'Monday anxiety is real. I did the work but my mind was racing. Should have meditated first.',
        'goals': ['career']
    },
    # Day 9 - Tuesday - Finding rhythm
    {
        'emotion': 'motivated',
        'energy': 7,
        'showed_up': True,
        'habits': {'exercise': True, 'deep_work': True, 'meditation': True, 'reading': False},
        'free_text': 'Found my rhythm today. All key habits done. Deep work was productive.',
        'long_reflection': 'When I do all three - exercise, meditation, deep work - the day flows better. This is the pattern I want to maintain.',
        'goals': ['career', 'health']
    },
    # Day 10 - Wednesday - Mid-week energy
    {
        'emotion': 'content',
        'energy': 7,
        'showed_up': True,
        'habits': {'exercise': True, 'deep_work': True, 'meditation': False, 'reading': True},
        'free_text': 'Steady day. Good energy maintained. Exercise and deep work both solid.',
        'long_reflection': 'Maintaining energy mid-week is key. Exercise in the morning sets the tone. Deep work quality was high.',
        'goals': ['career', 'health']
    },
]

def create_entry(entry_data, days_ago):
    """Create a journal entry file."""
    # Calculate timestamp
    timestamp = datetime.now() - timedelta(days=days_ago)
    # Add some time variation (morning, afternoon, evening)
    hour = 9 + (days_ago % 3) * 4  # 9am, 1pm, 5pm rotation
    timestamp = timestamp.replace(hour=hour, minute=30, second=0, microsecond=0)
    
    # Format timestamp
    timestamp_str = timestamp.strftime('%Y-%m-%dT%H-%M-%SZ')
    
    # Generate UUID
    entry_id = str(uuid.uuid4())
    
    # Create entry object
    entry = {
        'id': entry_id,
        'timestamp': timestamp.isoformat() + 'Z',
        'device': 'web',
        'emotion': entry_data['emotion'],
        'energy': entry_data['energy'],
        'showed_up': entry_data['showed_up'],
        'habits': entry_data['habits'],
        'goals': entry_data.get('goals', ['career', 'health']),
        'free_text': entry_data['free_text'],
        'long_reflection': entry_data.get('long_reflection', ''),
        'derived': {}
    }
    
    # Create filename
    filename = f"{timestamp_str}__{entry_id}.json"
    filepath = entries_dir / filename
    
    # Write entry
    with open(filepath, 'w') as f:
        json.dump(entry, f, indent=2)
    
    print(f"Created: {filename}")
    return filepath

def main():
    print("Creating test entries...")
    print(f"Entries directory: {entries_dir}")
    print()
    
    # Create entries (most recent first)
    created_files = []
    for i, entry_data in enumerate(test_entries):
        filepath = create_entry(entry_data, days_ago=i)
        created_files.append(filepath)
    
    print()
    print(f"✅ Created {len(created_files)} test entries")
    print()
    print("Entry summary:")
    print("-" * 60)
    for i, entry_data in enumerate(test_entries):
        days_ago = i
        timestamp = datetime.now() - timedelta(days=days_ago)
        date_str = timestamp.strftime('%Y-%m-%d')
        print(f"{date_str}: {entry_data['emotion']} (energy: {entry_data['energy']}, showed_up: {entry_data['showed_up']})")
    print()
    print("Now test the insights and patterns in the UI!")

if __name__ == '__main__':
    main()

