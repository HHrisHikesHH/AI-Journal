"""
Action items management system.
Stores action items created from coach suggestions.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from django.conf import settings

ACTIONS_FILE = settings.LOCAL_DIR / 'action_items.json'

def load_actions() -> List[Dict[str, Any]]:
    """Load all action items."""
    if not ACTIONS_FILE.exists():
        return []
    
    try:
        with open(ACTIONS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_actions(actions: List[Dict[str, Any]]):
    """Save all action items."""
    ACTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACTIONS_FILE, 'w') as f:
        json.dump(actions, f, indent=2)

def create_action(text: str, source_entry_id: str = None, source_query: str = None) -> Dict[str, Any]:
    """Create a new action item."""
    actions = load_actions()
    
    action = {
        'id': f"action_{len(actions)}_{int(datetime.now().timestamp())}",
        'text': text,
        'created_at': datetime.now().isoformat(),
        'completed': False,
        'completed_at': None,
        'source_entry_id': source_entry_id,
        'source_query': source_query
    }
    
    actions.append(action)
    save_actions(actions)
    return action

def get_actions(completed: bool = None) -> List[Dict[str, Any]]:
    """Get action items, optionally filtered by completion status."""
    actions = load_actions()
    
    if completed is None:
        return actions
    
    return [a for a in actions if a.get('completed', False) == completed]

def update_action(action_id: str, completed: bool = None, text: str = None) -> Dict[str, Any]:
    """Update an action item."""
    actions = load_actions()
    
    for action in actions:
        if action['id'] == action_id:
            if completed is not None:
                action['completed'] = completed
                if completed:
                    action['completed_at'] = datetime.now().isoformat()
                else:
                    action['completed_at'] = None
            if text is not None:
                action['text'] = text
            save_actions(actions)
            return action
    
    raise ValueError(f"Action {action_id} not found")

def delete_action(action_id: str):
    """Delete an action item."""
    actions = load_actions()
    actions = [a for a in actions if a['id'] != action_id]
    save_actions(actions)

