import json
import os
import uuid
import csv
from datetime import datetime, timedelta
from pathlib import Path
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .rag_system import RAGSystem
from .entry_processor import EntryProcessor
from .action_items import create_action, get_actions, update_action, delete_action
from .llm_adapter import call_local_llm

rag_system = None
last_insight_date = None
last_insight = None

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
        
        # Validate free_text length (must be <= 200 chars)
        if len(data['free_text']) > 200:
            return JsonResponse({'error': 'free_text must be <= 200 characters'}, status=400)
        
        # Validate emotion is in allowed list
        allowed_emotions = ["content", "anxious", "sad", "angry", "motivated", "tired", "calm", "stressed"]
        if data['emotion'] not in allowed_emotions:
            return JsonResponse({'error': f'emotion must be one of: {", ".join(allowed_emotions)}'}, status=400)
        
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
            
            # Extract action from result and create action item if present
            if result.get('structured', {}).get('action'):
                action_text = result['structured']['action']
                create_action(action_text, source_query=query_text)
            
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

@require_http_methods(["GET"])
def insight_on_open(request):
    """Get daily insight on app open. Rate-limited to once per calendar day."""
    global last_insight_date, last_insight
    
    today = datetime.now().date()
    
    # Return cached insight if already generated today
    if last_insight_date == today and last_insight:
        return JsonResponse(last_insight)
    
    try:
        rag = get_rag_system()
        
        # Get last 7 days of entries
        cutoff_date = datetime.now() - timedelta(days=7)
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
        
        if len(entries) < 1:
            return JsonResponse({
                'verdict': 'Start journaling to receive insights.',
                'evidence': [],
                'action': 'Create your first entry.',
                'confidence_estimate': 0
            })
        
        # Build context
        context_parts = []
        for entry in entries[:10]:  # Use up to 10 most recent
            entry_date = entry.get('timestamp', '')[:10]
            filename = f"{entry.get('timestamp', '').replace(':', '-').split('.')[0]}Z__{entry.get('id', '')}.json"
            context_parts.append(f"Entry from {entry_date} ({filename}):")
            context_parts.append(f"  Emotion: {entry.get('emotion', 'N/A')}")
            context_parts.append(f"  Energy: {entry.get('energy', 'N/A')}")
            context_parts.append(f"  Showed up: {entry.get('showed_up', False)}")
            if entry.get('free_text'):
                context_parts.append(f"  Note: {entry.get('free_text')}")
        
        context = '\n'.join(context_parts)
        
        # Load prompt template
        prompt_path = Path(__file__).parent.parent / 'prompts' / 'system_prompt.txt'
        with open(prompt_path, 'r') as f:
            system_prompt = f.read()
        
        user_prompt = f"""Context from recent journal entries:
{context}

Provide one neutral observation and one micro-action based on the patterns above."""
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Call LLM
        try:
            response = call_local_llm(full_prompt, max_tokens=512, temp=0.2)
            parsed = _parse_llm_response(response)
            
            # Cache for today
            last_insight_date = today
            last_insight = parsed
            
            return JsonResponse(parsed)
        except Exception as e:
            print(f"Error generating insight: {e}")
            return JsonResponse({
                'verdict': 'Unable to generate insight at this time.',
                'evidence': [],
                'action': 'Continue journaling.',
                'confidence_estimate': 0
            })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def search(request):
    """Search entries with semantic search and filters."""
    try:
        query_text = request.GET.get('q', '')
        emotion_filter = request.GET.get('emotion')
        habit_filter = request.GET.get('habit')
        from_date = request.GET.get('from')
        to_date = request.GET.get('to')
        
        # Load all entries
        entries = []
        for filepath in sorted(settings.ENTRIES_DIR.glob('*.json'), reverse=True):
            try:
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    
                    # Apply filters
                    if emotion_filter and entry.get('emotion') != emotion_filter:
                        continue
                    if habit_filter and not entry.get('habits', {}).get(habit_filter, False):
                        continue
                    if from_date:
                        entry_date = entry.get('timestamp', '')[:10]
                        if entry_date < from_date:
                            continue
                    if to_date:
                        entry_date = entry.get('timestamp', '')[:10]
                        if entry_date > to_date:
                            continue
                    
                    entries.append(entry)
            except Exception:
                continue
        
        # If query provided, use semantic search
        if query_text:
            rag = get_rag_system()
            # Get embeddings for all filtered entries
            texts = [rag._get_entry_text(e) for e in entries]
            if texts:
                query_embedding = rag.embedding_model.encode([query_text])
                entry_embeddings = rag.embedding_model.encode(texts)
                
                # Simple cosine similarity
                import numpy as np
                similarities = np.dot(entry_embeddings, query_embedding.T).flatten()
                top_indices = np.argsort(similarities)[::-1][:20]  # Top 20
                entries = [entries[i] for i in top_indices if i < len(entries)]
        
        return JsonResponse({'entries': entries, 'count': len(entries)})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def export_entries(request):
    """Export all entries as CSV or JSON."""
    format_type = request.GET.get('format', 'json')
    
    # Load all entries
    entries = []
    for filepath in sorted(settings.ENTRIES_DIR.glob('*.json')):
        try:
            with open(filepath, 'r') as f:
                entries.append(json.load(f))
        except Exception:
            continue
    
    if format_type == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="entries_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['id', 'timestamp', 'emotion', 'energy', 'showed_up', 'free_text', 'habits', 'goals'])
        
        for entry in entries:
            writer.writerow([
                entry.get('id', ''),
                entry.get('timestamp', ''),
                entry.get('emotion', ''),
                entry.get('energy', ''),
                entry.get('showed_up', False),
                entry.get('free_text', ''),
                json.dumps(entry.get('habits', {})),
                json.dumps(entry.get('goals', []))
            ])
        
        return response
    
    else:  # JSON
        response = HttpResponse(json.dumps(entries, indent=2), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="entries_export.json"'
        return response

@csrf_exempt
@require_http_methods(["POST"])
def create_action_item(request):
    """Create a new action item."""
    try:
        data = json.loads(request.body)
        text = data.get('text', '')
        
        if not text:
            return JsonResponse({'error': 'text is required'}, status=400)
        
        action = create_action(
            text,
            source_entry_id=data.get('source_entry_id'),
            source_query=data.get('source_query')
        )
        
        return JsonResponse(action, status=201)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_action_items(request):
    """Get all action items."""
    try:
        completed = request.GET.get('completed')
        if completed is not None:
            completed = completed.lower() == 'true'
        else:
            completed = None
        
        actions = get_actions(completed=completed)
        return JsonResponse({'actions': actions})
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_action_item(request, action_id):
    """Update an action item."""
    try:
        data = json.loads(request.body)
        completed = data.get('completed')
        text = data.get('text')
        
        action = update_action(action_id, completed=completed, text=text)
        return JsonResponse(action)
    
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_action_item(request, action_id):
    """Delete an action item."""
    try:
        delete_action(action_id)
        return JsonResponse({'status': 'deleted'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def _parse_llm_response(response: str) -> dict:
    """Parse LLM response into structured format."""
    result = {
        'verdict': '',
        'evidence': [],
        'action': '',
        'confidence_estimate': 0
    }
    
    lines = response.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if line.startswith('VERDICT:'):
            result['verdict'] = line.replace('VERDICT:', '').strip()
        elif line.startswith('EVIDENCE:'):
            current_section = 'evidence'
        elif line.startswith('ACTION:'):
            result['action'] = line.replace('ACTION:', '').strip()
            current_section = None
        elif line.startswith('CONFIDENCE_ESTIMATE:'):
            try:
                result['confidence_estimate'] = int(line.replace('CONFIDENCE_ESTIMATE:', '').strip())
            except:
                pass
            current_section = None
        elif current_section == 'evidence' and line.startswith('-'):
            result['evidence'].append(line[1:].strip())
    
    # Fallback if parsing fails
    if not result['verdict']:
        result['verdict'] = response[:200]
    
    # Calculate confidence if not provided
    if result['confidence_estimate'] == 0:
        result['confidence_estimate'] = min(100, 20 * len(result['evidence']))
    
    return result
