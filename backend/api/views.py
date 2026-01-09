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
from .llm_adapter import call_local_llm, get_model_context_window, ensure_model_loaded
from .prompt_utils import truncate_prompt_to_fit

rag_system = None
last_insight_date = None
last_insight = None
_llm_processing = False  # Flag to prevent concurrent LLM calls

# Config cache
_config_cache = None
_config_cache_time = None
CONFIG_CACHE_TTL = 300  # 5 minutes

def get_rag_system():
    global rag_system
    if rag_system is None:
        rag_system = RAGSystem()
    return rag_system

@csrf_exempt
@require_http_methods(["POST"])
def create_entry(request):
    """Create a new journal entry."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("[CreateEntry] POST /api/entry/ called")
        data = json.loads(request.body)
        logger.debug(f"[CreateEntry] Request data: {data}")
        
        # Validate required fields
        required_fields = ['emotion', 'energy', 'showed_up', 'habits', 'free_text']
        for field in required_fields:
            if field not in data:
                logger.warning(f"[CreateEntry] Missing required field: {field}")
                return JsonResponse({'error': f'Missing required field: {field}'}, status=400)
        
        # Validate free_text length (must be <= 200 chars)
        if len(data['free_text']) > 200:
            logger.warning(f"[CreateEntry] free_text too long: {len(data['free_text'])} chars")
            return JsonResponse({'error': 'free_text must be <= 200 characters'}, status=400)
        
        # Validate emotion is in allowed list (load from config)
        try:
            with open(settings.CONFIG_FILE, 'r') as f:
                config = json.load(f)
            allowed_emotions = config.get('emotions', ["content", "anxious", "sad", "angry", "motivated", "tired", "calm", "stressed"])
        except Exception:
            allowed_emotions = ["content", "anxious", "sad", "angry", "motivated", "tired", "calm", "stressed"]
        
        if data['emotion'] not in allowed_emotions:
            logger.warning(f"[CreateEntry] Invalid emotion: {data['emotion']}, allowed: {allowed_emotions}")
            return JsonResponse({'error': f'emotion must be one of: {", ".join(allowed_emotions)}'}, status=400)
        
        logger.info(f"[CreateEntry] Validation passed, creating entry with emotion: {data['emotion']}")
        
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
        logger.debug(f"[CreateEntry] Entry object created: id={entry_id}, timestamp={timestamp}")
        
        # Process entry to add derived fields
        logger.debug("[CreateEntry] Processing entry to add derived fields...")
        processor = EntryProcessor()
        entry = processor.process_entry(entry)
        logger.debug(f"[CreateEntry] Derived fields: {entry.get('derived', {})}")
        
        # Save entry to file
        filename = f"{entry['timestamp'].replace(':', '-').split('.')[0]}Z__{entry_id}.json"
        filepath = settings.ENTRIES_DIR / filename
        logger.info(f"[CreateEntry] Saving entry to file: {filepath}")
        
        with open(filepath, 'w') as f:
            json.dump(entry, f, indent=2)
        logger.info(f"[CreateEntry] Entry saved to {filename}")
        
        # Add to RAG index incrementally
        logger.debug("[CreateEntry] Adding entry to RAG index...")
        rag = get_rag_system()
        rag.add_entry(entry)
        logger.info("[CreateEntry] Entry added to RAG index")
        
        logger.info(f"[CreateEntry] Entry created successfully: {entry_id}")
        return JsonResponse(entry, status=201)
    
    except json.JSONDecodeError as e:
        logger.error(f"[CreateEntry] Invalid JSON: {e}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        logger.error(f"[CreateEntry] Unexpected error: {e}")
        logger.error(f"[CreateEntry] Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def get_entries(request):
    """Get recent entries (optimized)."""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        days = int(request.GET.get('days', 7))
        cutoff_date = datetime.now() - timedelta(days=days)
        
        logger.debug(f"[GetEntries] Loading entries for last {days} days")
        entries = []
        entry_files = sorted(settings.ENTRIES_DIR.glob('*.json'), reverse=True)
        
        # Limit file reads for performance (assume max 3 entries per day)
        max_files_to_check = min(len(entry_files), days * 3)
        
        for filepath in entry_files[:max_files_to_check]:
            try:
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    entry_timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    if entry_timestamp.replace(tzinfo=None) >= cutoff_date:
                        entries.append(entry)
                    elif len(entries) > 0:  # If we've found entries but this one is too old, we can stop
                        break
            except Exception as e:
                logger.debug(f"[GetEntries] Error reading {filepath.name}: {e}")
                continue
        
        logger.debug(f"[GetEntries] Returning {len(entries)} entries")
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

@csrf_exempt
@require_http_methods(["GET"])
def get_config(request):
    """Get configuration from config.json (cached)."""
    import logging
    import time
    global _config_cache, _config_cache_time
    logger = logging.getLogger(__name__)
    
    try:
        # Check cache first
        current_time = time.time()
        if _config_cache is not None and _config_cache_time is not None:
            if current_time - _config_cache_time < CONFIG_CACHE_TTL:
                logger.debug("[GetConfig] Returning cached config")
                return JsonResponse(_config_cache)
        
        # Cache miss or expired - load from file
        logger.debug(f"[GetConfig] Loading config from {settings.CONFIG_FILE}")
        
        if not settings.CONFIG_FILE.exists():
            logger.error(f"[GetConfig] Config file not found: {settings.CONFIG_FILE}")
            return JsonResponse({'error': f'Config file not found at {settings.CONFIG_FILE}'}, status=500)
        
        with open(settings.CONFIG_FILE, 'r') as f:
            config = json.load(f)
        logger.debug(f"[GetConfig] Config loaded: emotions={len(config.get('emotions', []))}, habits={len(config.get('habits', {}))}")
        
        # Return only the parts needed by frontend
        response_data = {
            'emotions': config.get('emotions', []),
            'habits': list(config.get('habits', {}).keys()),
            'reflection_questions': config.get('reflection_questions', []),
            'goals': config.get('user', {}).get('goals', [])
        }
        
        # Update cache
        _config_cache = response_data
        _config_cache_time = current_time
        
        logger.debug(f"[GetConfig] Config cached, returning: {len(response_data['emotions'])} emotions, {len(response_data['habits'])} habits")
        return JsonResponse(response_data)
    except json.JSONDecodeError as e:
        logger.error(f"[GetConfig] Invalid JSON in config file: {e}")
        return JsonResponse({'error': f'Invalid JSON in config file: {str(e)}'}, status=500)
    except Exception as e:
        logger.error(f"[GetConfig] Error loading config: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def insight_on_open(request):
    """Get daily insight on app open. Rate-limited to once per calendar day."""
    import logging
    logger = logging.getLogger(__name__)
    
    global last_insight_date, last_insight, _llm_processing
    
    logger.info("[Insight] Insight on_open endpoint called")
    today = datetime.now().date()
    logger.debug(f"[Insight] Today's date: {today}, Last insight date: {last_insight_date}")
    
    # Check if user wants to force refresh (for testing polling)
    force_refresh = request.GET.get('force_refresh', '').lower() == 'true'
    
    # If force refresh, reset LLM processing flag to allow new LLM call
    if force_refresh:
        logger.info("[Insight] Force refresh requested, resetting LLM processing flag")
        _llm_processing = False
    
    # Return cached insight if already generated today (unless force refresh)
    if not force_refresh and last_insight_date == today and last_insight:
        logger.debug("[Insight] Cache check: last_insight_date={}, today={}, _llm_processing={}".format(
            last_insight_date, today, _llm_processing))
        
        # Ensure source field is set
        if 'source' not in last_insight:
            last_insight['source'] = 'llm' if last_insight.get('evidence') and any('json' in str(e) for e in last_insight.get('evidence', [])) else 'fallback'
        
        # If we have a cached LLM response, return it immediately
        if last_insight.get('source') == 'llm':
            logger.info("[Insight] Returning cached LLM insight")
            last_insight['llm_processing'] = False
            return JsonResponse(last_insight)
        
        # If we have a fallback, check LLM processing status
        if last_insight.get('source') == 'fallback':
            if _llm_processing:
                # LLM is still processing - return fallback with processing flag
                logger.debug("[Insight] LLM still processing, returning fallback with processing flag")
                last_insight['llm_processing'] = True
                return JsonResponse(last_insight)
            else:
                # LLM processing completed - check if we have an LLM response now
                # (This handles the case where LLM just completed but cache wasn't updated yet)
                # Actually, if LLM completed, last_insight should have been updated
                # So if we're here with a fallback and LLM is not processing, 
                # it means LLM failed or returned invalid response
                logger.debug("[Insight] LLM processing completed, returning fallback (no LLM response available)")
                last_insight['llm_processing'] = False
                return JsonResponse(last_insight)
        
        # Default: return cached insight
        logger.info("[Insight] Returning cached insight from today")
        return JsonResponse(last_insight)
    
    try:
        logger.info("[Insight] Generating new insight...")
        
        # Ensure model is loaded in main thread BEFORE doing anything else
        # This is critical - llama-cpp-python requires model loading in main thread
        logger.info("[Insight] Ensuring model is loaded in main thread...")
        model_loaded = ensure_model_loaded()
        if model_loaded:
            logger.info("[Insight] ✅ Model loaded successfully in main thread")
        else:
            logger.warning("[Insight] ⚠️ Model not loaded in main thread, will use fallback only")
        
        try:
            rag = get_rag_system()
            logger.debug("[Insight] RAG system loaded")
        except Exception as rag_error:
            error_msg = str(rag_error)
            logger.error(f"[Insight] Error loading RAG system: {error_msg}")
            # If it's a meta tensor error, we can still provide fallback insight
            if 'meta tensor' in error_msg.lower() or 'to_empty' in error_msg.lower():
                logger.warning("[Insight] Meta tensor error in RAG system, using fallback without RAG")
                rag = None
            else:
                raise
        
        # Get last 7 days of entries (use entries for recent data, summaries for older context if needed)
        cutoff_date = datetime.now() - timedelta(days=7)
        logger.debug(f"[Insight] Loading entries from last 7 days (cutoff: {cutoff_date})")
        entries = []
        entry_files = sorted(settings.ENTRIES_DIR.glob('*.json'), reverse=True)
        logger.debug(f"[Insight] Found {len(entry_files)} entry files")
        
        for filepath in entry_files:
            try:
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    entry_timestamp = datetime.fromisoformat(entry['timestamp'].replace('Z', '+00:00'))
                    if entry_timestamp.replace(tzinfo=None) >= cutoff_date:
                        entries.append(entry)
            except Exception as e:
                logger.debug(f"[Insight] Error reading entry file {filepath.name}: {e}")
                continue
        
        logger.info(f"[Insight] Loaded {len(entries)} entries from last 7 days")
        
        # Note: For daily insights, we use recent entries only (< 7 days)
        # Summaries are used in query/search endpoints for older data (> 30 days)
        
        if len(entries) < 1:
            logger.info("[Insight] No entries found, returning default message")
            return JsonResponse({
                'verdict': 'Start journaling to receive insights.',
                'evidence': [],
                'action': 'Create your first entry.',
                'confidence_estimate': 0
            })
        
        # Build context (limit entries to prevent context overflow)
        logger.debug("[Insight] Building context from entries...")
        from .prompt_utils import limit_entries_for_context
        # Limit to 8 entries max, 150 chars per entry to ensure we fit in context window
        limited_entries = limit_entries_for_context(entries, max_entries=8, max_chars_per_entry=150)
        
        context_parts = []
        for entry in limited_entries:
            entry_date = entry.get('timestamp', '')[:10]
            filename = f"{entry.get('timestamp', '').replace(':', '-').split('.')[0]}Z__{entry.get('id', '')}.json"
            context_parts.append(f"Entry from {entry_date} ({filename}):")
            context_parts.append(f"  Emotion: {entry.get('emotion', 'N/A')}")
            context_parts.append(f"  Energy: {entry.get('energy', 'N/A')}")
            context_parts.append(f"  Showed up: {entry.get('showed_up', False)}")
            if entry.get('free_text'):
                # free_text already truncated by limit_entries_for_context
                context_parts.append(f"  Note: {entry.get('free_text')}")
        
        context = '\n'.join(context_parts)
        logger.debug(f"[Insight] Context built ({len(context)} chars, {len(limited_entries)} entries)")
        
        # Load prompt template - optimize for token usage
        prompt_path = Path(__file__).parent.parent / 'prompts' / 'system_prompt.txt'
        logger.debug(f"[Insight] Loading prompt from {prompt_path}")
        try:
            with open(prompt_path, 'r') as f:
                system_instruction = f.read().strip()
            logger.debug(f"[Insight] System instruction loaded ({len(system_instruction)} chars)")
        except Exception as e:
            logger.error(f"[Insight] Error loading prompt template: {e}")
            raise
        
        # Optimize context: limit to most recent/relevant entries (token optimization)
        # Limit context to ~800 chars (200 tokens) to keep costs down
        max_context_chars = 800
        if len(context) > max_context_chars:
            logger.debug(f"[Insight] Truncating context from {len(context)} to {max_context_chars} chars for token optimization")
            # Keep the most recent entries (last part of context)
            context = context[-max_context_chars:]
        
        # User prompt - concise for token efficiency
        user_prompt = f"Context:\n{context}\n\nProvide insight in the required format."
        
        # For Gemini: use system instruction separately (more efficient)
        # For local model: combine as before
        from .llm_adapter import _using_gemini
        if _using_gemini():
            # Gemini: system instruction separate, user content is just context
            full_prompt = user_prompt
        else:
            # Local model: combine as before
            full_prompt = f"{system_instruction}\n\n{user_prompt}"
            # Truncate for local model context window
            try:
                max_context_window = get_model_context_window()
                from .prompt_utils import truncate_prompt_to_fit
                full_prompt = truncate_prompt_to_fit(
                    system_instruction,
                    user_prompt,
                    max_context_window,
                    max_tokens_to_generate=200,
                    safety_buffer=50
                )
            except Exception as truncate_error:
                logger.warning(f"[Insight] Error truncating prompt: {truncate_error}, using original")
                full_prompt = f"{system_instruction}\n\n{user_prompt}"
        
        logger.debug(f"[Insight] Final prompt length: {len(full_prompt)} chars (estimated {len(full_prompt) // 4} tokens)")
        
        # Generate fast fallback immediately with more meaningful patterns
        if len(entries) > 0:
            showed_up_count = sum(1 for e in entries if e.get('showed_up', False))
            showed_up_rate = (showed_up_count / len(entries) * 100) if entries else 0
            
            # Calculate emotion frequency from ALL entries
            emotion_counts = {}
            for e in entries:
                emotion = e.get('emotion', 'unknown')
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            top_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else 'unknown'
            
            # Calculate average energy
            total_energy = sum(e.get('energy', 5) for e in entries)
            avg_energy = total_energy / len(entries) if entries else 5
            
            # Find energy pattern
            energy_trend = 'stable'
            if len(entries) >= 3:
                recent_energy = [e.get('energy', 5) for e in entries[:3]]
                older_energy = [e.get('energy', 5) for e in entries[-3:]]
                if len(recent_energy) > 0 and len(older_energy) > 0:
                    recent_avg = sum(recent_energy) / len(recent_energy)
                    older_avg = sum(older_energy) / len(older_energy)
                    if recent_avg > older_avg + 1:
                        energy_trend = 'increasing'
                    elif recent_avg < older_avg - 1:
                        energy_trend = 'decreasing'
            
            # Build evidence with more detail
            evidence = [
                f'Found {len(entries)} entries in the last 7 days',
                f'Showed up {showed_up_count} out of {len(entries)} days ({showed_up_rate:.0f}%)',
                f'Most common emotion: {top_emotion}',
                f'Average energy: {avg_energy:.1f}/10 ({energy_trend})'
            ]
            
            # Generate action based on patterns
            action = 'Continue with your current journaling practice.'
            if showed_up_rate < 70:
                action = 'Focus on showing up consistently, even on difficult days.'
            elif avg_energy < 5:
                action = 'Consider what activities or habits help boost your energy.'
            elif energy_trend == 'decreasing':
                action = 'Your energy has been decreasing - prioritize rest and recovery.'
            
            fallback_parsed = {
                'verdict': f'I notice you\'ve been journaling regularly ({len(entries)} entries in the last week).',
                'evidence': evidence,
                'action': action,
                'confidence_estimate': 70
            }
        else:
            fallback_parsed = {
                'verdict': 'Start journaling to receive insights.',
                'evidence': [],
                'action': 'Create your first entry.',
                'confidence_estimate': 0
            }
        
        # Start LLM in background (non-blocking)
        llm_started = False
        
        # Log the state before deciding whether to start LLM
        logger.debug(f"[Insight] LLM start check: _llm_processing={_llm_processing}, model_loaded={model_loaded}, force_refresh={force_refresh}")
        
        # Check if LLM is already processing and model is loaded
        # model_loaded was checked earlier at the start of the function
        # If force_refresh, we already reset _llm_processing above
        if not _llm_processing and model_loaded:
            import threading
            _llm_processing = True
            llm_started = True
            
            def llm_background_task():
                global last_insight, last_insight_date, _llm_processing
                try:
                    import time
                    start_time = time.time()
                    logger.info("[Insight] 🤖 Starting background LLM call...")
                    logger.info(f"[Insight] 📝 Prompt length: {len(full_prompt)} chars, max_tokens: 256")
                    
                    # Use optimized token limits and system instruction for Gemini
                    from .llm_adapter import _using_gemini, _call_gemini
                    if _using_gemini():
                        # Gemini with system instruction (token optimized for 2-3 sentence responses)
                        response = _call_gemini(
                            prompt=user_prompt if _using_gemini() else full_prompt,
                            max_tokens=384,  # Optimized: 384 tokens for 2-3 sentence insights
                            temp=0.2,
                            system_instruction=system_instruction if _using_gemini() else None
                        )
                    else:
                        # Local model (unchanged)
                        response = call_local_llm(full_prompt, max_tokens=200, temp=0.2)
                    
                    elapsed = time.time() - start_time
                    logger.info(f"[Insight] ⏱️ LLM call completed in {elapsed:.1f} seconds")
                    
                    if response and len(response) > 10:  # Valid response
                        logger.info(f"[Insight] 📄 LLM response received ({len(response)} chars)")
                        logger.debug(f"[Insight] Raw LLM response preview: {response[:200]}...")
                        
                        parsed = _parse_llm_response(response)
                        parsed['source'] = 'llm'  # Mark as LLM-generated
                        parsed['llm_processing'] = False
                        
                        logger.info(f"[Insight] ✨ LLM insight generated successfully!")
                        logger.info(f"[Insight] 📊 Parsed result: verdict={parsed.get('verdict', '')[:60]}..., evidence={len(parsed.get('evidence', []))}, action={parsed.get('action', '')[:50]}...")
                        
                        # Update cache with LLM result
                        last_insight = parsed
                        last_insight_date = today
                        logger.info("[Insight] ✅ Cache updated with LLM response - next API call will return LLM insight")
                    else:
                        logger.warning("[Insight] ⚠️ LLM returned empty/invalid response, keeping fallback")
                except Exception as e:
                    import traceback
                    logger.error(f"[Insight] ❌ Background LLM call failed: {e}")
                    logger.error(f"[Insight] Traceback: {traceback.format_exc()}")
                    # Keep fallback, don't update cache
                finally:
                    _llm_processing = False
                    logger.info("[Insight] 🏁 LLM background task completed")
            
            # Start background thread
            llm_thread = threading.Thread(target=llm_background_task, daemon=True)
            llm_thread.start()
            logger.info("[Insight] LLM processing started in background, returning fallback immediately")
        else:
            if _llm_processing:
                logger.debug("[Insight] LLM already processing, returning fallback")
            elif not model_loaded:
                logger.warning("[Insight] Model not loaded, cannot start LLM task. Returning fallback only.")
            else:
                logger.warning("[Insight] Unknown reason for not starting LLM task")
        
        # Return fallback immediately (fast response)
        # Mark as fallback so frontend knows to poll for LLM result
        fallback_parsed['source'] = 'fallback'
        fallback_parsed['llm_processing'] = llm_started  # True if LLM just started
        
        last_insight_date = today
        last_insight = fallback_parsed
        logger.info("[Insight] Returning fallback insight immediately")
        
        return JsonResponse(fallback_parsed)
    
    except Exception as e:
        import traceback
        logger.error(f"[Insight] Outer exception in insight_on_open: {e}")
        logger.error(f"[Insight] Traceback: {traceback.format_exc()}")
        return JsonResponse({
            'error': str(e),
            'verdict': 'Unable to generate insight due to a system error.',
            'evidence': [],
            'action': 'Please try again later.',
            'confidence_estimate': 0
        }, status=500)

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
    
    if not response or len(response.strip()) < 10:
        # Response too short or empty
        result['verdict'] = 'Unable to generate insight at this time.'
        return result
    
    lines = response.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # More flexible matching for VERDICT
        if line.upper().startswith('VERDICT:') or line.upper().startswith('VERDICT'):
            result['verdict'] = line.split(':', 1)[-1].strip() if ':' in line else line.replace('VERDICT', '').strip()
        elif line.upper().startswith('EVIDENCE:'):
            current_section = 'evidence'
        elif line.upper().startswith('ACTION:'):
            result['action'] = line.split(':', 1)[-1].strip() if ':' in line else line.replace('ACTION', '').strip()
            current_section = None
        elif line.upper().startswith('CONFIDENCE_ESTIMATE:') or line.upper().startswith('CONFIDENCE'):
            try:
                conf_str = line.split(':', 1)[-1].strip() if ':' in line else line.replace('CONFIDENCE', '').strip()
                # Extract first number found
                import re
                numbers = re.findall(r'\d+', conf_str)
                if numbers:
                    result['confidence_estimate'] = min(100, max(0, int(numbers[0])))
            except:
                pass
            current_section = None
        elif current_section == 'evidence' and (line.startswith('-') or line.startswith('*')):
            evidence_text = line[1:].strip()
            if evidence_text:
                result['evidence'].append(evidence_text)
    
    # Fallback if parsing fails - try to extract meaningful content
    if not result['verdict']:
        # Try to find first sentence or meaningful text
        first_line = response.split('\n')[0].strip()
        if len(first_line) > 10:  # Lower threshold
            result['verdict'] = first_line[:300]  # Longer limit
        else:
            # Look for any sentence in the response
            sentences = response.split('.')
            for sent in sentences:
                sent = sent.strip()
                if len(sent) > 10 and not sent.startswith('VERDICT') and not sent.startswith('EVIDENCE'):
                    result['verdict'] = sent[:300]
                    break
            if not result['verdict']:
                # Last resort: use first 300 chars of response
                result['verdict'] = response[:300].strip() if len(response.strip()) > 10 else 'Unable to generate insight at this time.'
    
    # If verdict was found but seems incomplete (ends mid-sentence), try to complete it
    if result['verdict'] and len(result['verdict']) < 50 and not result['verdict'].endswith(('.', '!', '?')):
        # Look for more content in the response
        remaining = response[len(result['verdict']):].strip()
        if remaining:
            # Try to get the next sentence or meaningful chunk
            next_sent = remaining.split('.')[0].strip()
            if len(next_sent) > 10:
                result['verdict'] = result['verdict'] + ' ' + next_sent[:200]
    
    # Calculate confidence if not provided
    if result['confidence_estimate'] == 0:
        result['confidence_estimate'] = min(100, 20 * max(1, len(result['evidence'])))
    
    return result
