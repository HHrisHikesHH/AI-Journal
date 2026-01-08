"""
Integration tests for the journal API.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from datetime import datetime

# Add backend to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'journal_api.settings')
django.setup()

from django.test import Client
from django.conf import settings

class JournalAPITestCase(unittest.TestCase):
    """Test cases for journal API endpoints."""
    
    def setUp(self):
        """Set up test client."""
        self.client = Client()
        # Ensure entries directory exists
        settings.ENTRIES_DIR.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up test entries."""
        # Remove test entries (entries with 'test' in ID)
        for filepath in settings.ENTRIES_DIR.glob('*.json'):
            try:
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    if 'test' in entry.get('id', '').lower():
                        filepath.unlink()
            except Exception:
                pass
    
    def test_create_entry(self):
        """Test creating a new entry."""
        entry_data = {
            'emotion': 'content',
            'energy': 7,
            'showed_up': True,
            'habits': {
                'exercise': True,
                'deep_work': False,
                'sleep_on_time': True
            },
            'goals': ['career', 'health'],
            'free_text': 'Had a good day, test entry',
            'long_reflection': ''
        }
        
        response = self.client.post(
            '/api/entry/',
            data=json.dumps(entry_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertIn('id', data)
        self.assertEqual(data['emotion'], 'content')
        self.assertEqual(data['energy'], 7)
        self.assertIn('derived', data)
        
        # Verify file was created
        entry_id = data['id']
        files = list(settings.ENTRIES_DIR.glob(f'*{entry_id}.json'))
        self.assertTrue(len(files) > 0, "Entry file should be created")
    
    def test_get_entries(self):
        """Test retrieving entries."""
        # Create a test entry first
        entry_data = {
            'emotion': 'motivated',
            'energy': 8,
            'showed_up': True,
            'habits': {'exercise': True, 'deep_work': True, 'sleep_on_time': False},
            'goals': ['career'],
            'free_text': 'Test entry for retrieval',
            'long_reflection': ''
        }
        
        create_response = self.client.post(
            '/api/entry/',
            data=json.dumps(entry_data),
            content_type='application/json'
        )
        self.assertEqual(create_response.status_code, 201)
        
        # Retrieve entries
        response = self.client.get('/api/entries/?days=7')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('entries', data)
        self.assertIsInstance(data['entries'], list)
    
    def test_query_endpoint(self):
        """Test query endpoint."""
        # First create an entry
        entry_data = {
            'emotion': 'anxious',
            'energy': 4,
            'showed_up': False,
            'habits': {'exercise': False, 'deep_work': False, 'sleep_on_time': False},
            'goals': [],
            'free_text': 'Feeling overwhelmed with work, test query entry',
            'long_reflection': ''
        }
        
        create_response = self.client.post(
            '/api/entry/',
            data=json.dumps(entry_data),
            content_type='application/json'
        )
        self.assertEqual(create_response.status_code, 201)
        
        # Query
        query_data = {'query': 'What drains my energy?'}
        response = self.client.post(
            '/api/query/',
            data=json.dumps(query_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('answer', data)
        self.assertIn('sources', data)
        self.assertIn('confidence_estimate', data)
    
    def test_rebuild_index(self):
        """Test rebuilding the index."""
        response = self.client.post('/api/rebuild_index/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('status', data)
        
        # Verify index file was created
        index_path = settings.EMBEDDINGS_DIR / 'faiss_index.bin'
        self.assertTrue(index_path.exists(), "FAISS index file should be created")
    
    def test_entry_create_validation(self):
        """Test entry creation with validation (free_text <= 200 chars)."""
        # Test with valid entry
        entry_data = {
            'emotion': 'content',
            'energy': 7,
            'showed_up': True,
            'habits': {'exercise': True},
            'goals': [],
            'free_text': 'A' * 200,  # Exactly 200 chars
            'long_reflection': ''
        }
        
        response = self.client.post(
            '/api/entry/',
            data=json.dumps(entry_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # Test with invalid entry (free_text > 200 chars)
        entry_data['free_text'] = 'A' * 201  # 201 chars
        response = self.client.post(
            '/api/entry/',
            data=json.dumps(entry_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
        self.assertIn('200', data['error'])
    
    def test_query_basic(self):
        """Test basic query functionality with seeded entries."""
        # Create multiple test entries
        entries = [
            {
                'emotion': 'motivated',
                'energy': 8,
                'showed_up': True,
                'habits': {'exercise': True, 'deep_work': True},
                'goals': ['career'],
                'free_text': 'Great day, made progress on project',
                'long_reflection': ''
            },
            {
                'emotion': 'tired',
                'energy': 3,
                'showed_up': False,
                'habits': {'exercise': False},
                'goals': ['health'],
                'free_text': 'Feeling exhausted, need rest',
                'long_reflection': ''
            }
        ]
        
        for entry_data in entries:
            response = self.client.post(
                '/api/entry/',
                data=json.dumps(entry_data),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 201)
        
        # Rebuild index to include new entries
        self.client.post('/api/rebuild_index/')
        
        # Query
        query_data = {'query': 'What patterns do you see?'}
        response = self.client.post(
            '/api/query/',
            data=json.dumps(query_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('answer', data)
        self.assertIsInstance(data['answer'], str)
        self.assertGreater(len(data['answer']), 0, "Answer should not be empty")
        self.assertIn('sources', data)
        self.assertIsInstance(data['sources'], list)

if __name__ == '__main__':
    unittest.main()

