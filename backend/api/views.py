import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .rag_system import RAGSystem
from .entry_processor import EntryProcessor

rag_system = None

def get_rag_system():
    global rag_system
    if rag_system is None:
        rag_system = RAGSystem()
    return rag_system

@csrf_exempt
@require_http_methods(["POST"])
def create_entry(request):
    """Create a new journal entry."""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['emotion', 'energy', 'showed_up', 'habits', 'free_text']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        # Validate free_text length
        if len(data['free_text']) > 200:
            return JsonResponse({'error': 'free_text must be <= 200 characters'}, status=400)
        
        # Generate entry
        entry_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        device = os.uname().nodename if hasattr(os, 'uname') else 'unknown'
        
        entry = {
            'id': entry_id,
            'timestamp': timestamp,
            'device': device,
            'emotion': data['emotion'],
            'energy': data['energy'],
            'showed_up': data['showed_up'],
            'habits': data['habits'],
            'goals': data.get('goals', []),
            'free_text': data['free_text'],
            'long_reflection': data.get('long_reflection', ''),
            'derived': {}
        }
        
        # Process entry to add derived fields
        processor = EntryProcessor()
        entry = processor.process_entry(entry)
        
        # Save entry to file
        filename = f"{entry['timestamp'].replace(':', '-').split('.')[0]}Z__{entry_id}.json"
        filepath = settings.ENTRIES_DIR / filename
        
        with open(filepath, 'w') as f:
            json.dump(entry, f, indent=2)
        
        # Add to RAG index incrementally
        rag = get_rag_system()
        rag.add_entry(entry)
        
        return JsonResponse(entry, status=201)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_entries(request):
    """Get recent entries."""
    try:
        days = int(request.GET.get('days', 7))
        cutoff_date = datetime.now() - timedelta(days=days)
        
        entries = []
        for filepath in sorted(settings.ENTRIES_DIR.glob('*.json'), reverse=True):
            try:
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    entry_timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    if entry_timestamp.replace(tzinfo=None) >= cutoff_date:
                        entries.append(entry)
            except Exception:
                continue
        
        return JsonResponse({'entries': entries}, safe=False)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def query(request):
    """Query the RAG system."""
    try:
        data = json.loads(request.body)
        query_text = data.get('query', '')
        
        if not query_text:
            return JsonResponse({'error': 'Query is required'}, status=400)
        
        try:
            rag = get_rag_system()
            result = rag.query(query_text)
            return JsonResponse(result)
        except Exception as rag_error:
            import traceback
            error_trace = traceback.format_exc()
            print(f"RAG query error: {rag_error}")
            print(f"Traceback: {error_trace}")
            return JsonResponse({
                'error': f'Error processing query: {str(rag_error)}',
                'details': 'The query system encountered an error. Please try again.'
            }, status=500)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Query endpoint error: {e}")
        print(f"Traceback: {error_trace}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def rebuild_index(request):
    """Rebuild the FAISS index from all entries."""
    try:
        rag = get_rag_system()
        rag.rebuild_index()
        return JsonResponse({'status': 'Index rebuilt successfully'})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_config(request):
    """Get configuration from config.json."""
    try:
        with open(settings.CONFIG_FILE, 'r') as f:
            config = json.load(f)
        # Return only the parts needed by frontend
        return JsonResponse({
            'emotions': config.get('emotions', []),
            'habits': list(config.get('habits', {}).keys()),
            'reflection_questions': config.get('reflection_questions', []),
            'goals': config.get('user', {}).get('goals', [])
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

