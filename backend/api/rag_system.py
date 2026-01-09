import json
import os
import numpy as np
import logging
from pathlib import Path
from typing import List, Dict, Any
from django.conf import settings
from sentence_transformers import SentenceTransformer
import faiss
from .llm_adapter import call_local_llm

logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG system for querying journal entries."""
    
    def __init__(self):
        self.embedding_model = None
        self.index = None
        self.entries = []
        self.summaries = []  # Store summaries separately
        self._load_embedding_model()
        self._load_or_create_index()
    
    def _encode_safe(self, texts):
        """Safely encode texts with error handling for device issues."""
        import torch
        try:
            with torch.no_grad():
                # Use batch_encode for better error handling
                if isinstance(texts, str):
                    texts = [texts]
                return self.embedding_model.encode(
                    texts,
                    convert_to_tensor=False,
                    show_progress_bar=False,
                    normalize_embeddings=False,
                    batch_size=1  # Process one at a time to avoid memory issues
                )
        except (StopIteration, AttributeError, RuntimeError) as e:
            # Device access error - try to fix by ensuring model is on CPU
            error_msg = str(e) if e else repr(e)
            logger.warning(f"[RAG] Device error during encode ({type(e).__name__}): {error_msg}")
            try:
                # Force model to CPU if it's not already
                if hasattr(self.embedding_model, '_modules'):
                    for module in self.embedding_model._modules.values():
                        if hasattr(module, 'to'):
                            try:
                                module.to('cpu')
                            except:
                                pass
                # Also try to access device property safely
                try:
                    if hasattr(self.embedding_model, 'device'):
                        _ = self.embedding_model.device
                except:
                    pass
                
                # Retry encoding with even more conservative settings
                with torch.no_grad():
                    if isinstance(texts, str):
                        texts = [texts]
                    return self.embedding_model.encode(
                        texts,
                        convert_to_tensor=False,
                        show_progress_bar=False,
                        normalize_embeddings=False,
                        batch_size=1
                    )
            except Exception as retry_error:
                retry_error_msg = str(retry_error) if retry_error else repr(retry_error)
                logger.error(f"[RAG] Failed to fix device issue: {retry_error_msg}")
                # Last resort: try to reload the model
                try:
                    logger.warning("[RAG] Attempting to reload embedding model as last resort...")
                    self._load_embedding_model()
                    with torch.no_grad():
                        if isinstance(texts, str):
                            texts = [texts]
                        return self.embedding_model.encode(
                            texts,
                            convert_to_tensor=False,
                            show_progress_bar=False,
                            normalize_embeddings=False,
                            batch_size=1
                        )
                except Exception as reload_error:
                    logger.error(f"[RAG] Model reload also failed: {reload_error}")
                    raise RuntimeError(f"Embedding model error: {error_msg}. Reload failed: {reload_error}")
    
    def _load_embedding_model(self):
        """Load the sentence transformer model."""
        try:
            import torch
            import logging
            logger = logging.getLogger(__name__)
            
            model_name = self._get_config()['models']['embedding_model']
            logger.info(f"[RAG] Loading embedding model: {model_name}")
            
            # Set environment variables to avoid meta tensor issues
            os.environ['TRANSFORMERS_NO_ADVISORY_WARNINGS'] = '1'
            os.environ['HF_HUB_DISABLE_EXPERIMENTAL_WARNING'] = '1'
            os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
            
            # Patch transformers to avoid meta tensor issues with PyTorch 2.9.1+
            # This is a workaround for a known compatibility issue
            try:
                from transformers import modeling_utils
                original_from_pretrained = modeling_utils.PreTrainedModel.from_pretrained
                
                def patched_from_pretrained(cls, *args, **kwargs):
                    # Force device_map=None to avoid meta tensors
                    if 'device_map' not in kwargs:
                        kwargs['device_map'] = None
                    # Force low_cpu_mem_usage=False
                    if 'low_cpu_mem_usage' not in kwargs:
                        kwargs['low_cpu_mem_usage'] = False
                    # Ensure torch_dtype is set
                    if 'torch_dtype' not in kwargs:
                        kwargs['torch_dtype'] = torch.float32
                    return original_from_pretrained(*args, **kwargs)
                
                # Apply patch
                modeling_utils.PreTrainedModel.from_pretrained = classmethod(patched_from_pretrained)
                logger.debug("[RAG] Applied transformers patch to avoid meta tensors")
            except Exception as patch_error:
                logger.debug(f"[RAG] Could not apply transformers patch: {patch_error}")
            
            # Try loading with different methods to avoid meta tensor issues
            loaded = False
            last_error = None
            
            # Method 1: Standard load with explicit model_kwargs to avoid meta tensors
            try:
                # For PyTorch 2.9.1+, we need to be very explicit about avoiding meta tensors
                self.embedding_model = SentenceTransformer(
                    model_name,
                    device='cpu',
                    model_kwargs={
                        'torch_dtype': torch.float32,
                        'low_cpu_mem_usage': False,  # Disable low memory mode which can cause meta tensors
                        'device_map': None,  # Explicitly disable device_map to avoid meta tensors
                    }
                )
                logger.info(f"[RAG] Loaded embedding model: {model_name} on CPU")
                loaded = True
            except Exception as e1:
                error_str = str(e1).lower()
                last_error = e1
                if 'meta tensor' in error_str or 'to_empty' in error_str:
                    logger.warning(f"[RAG] Meta tensor error (method 1), trying alternative methods...")
                    
                    # Method 2: Clear cache and reload
                    try:
                        from pathlib import Path
                        import shutil
                        
                        # Try to clear the corrupted cache from multiple possible locations
                        cache_locations = [
                            Path.home() / '.cache' / 'huggingface' / 'hub',
                            Path.home() / '.cache' / 'huggingface' / 'transformers',
                            Path.home() / '.cache' / 'torch' / 'hub',
                        ]
                        
                        model_cache_pattern = model_name.replace('/', '--')
                        for cache_dir in cache_locations:
                            if cache_dir.exists():
                                for item in cache_dir.iterdir():
                                    if model_cache_pattern in str(item) or model_name in str(item):
                                        try:
                                            logger.info(f"[RAG] Clearing potentially corrupted cache: {item}")
                                            shutil.rmtree(item)
                                        except Exception:
                                            pass
                        
                        # Try loading again after cache clear
                        self.embedding_model = SentenceTransformer(
                            model_name,
                            device='cpu',
                            model_kwargs={
                                'torch_dtype': torch.float32,
                                'low_cpu_mem_usage': False,
                                'device_map': None,  # Explicitly disable device_map
                            }
                        )
                        logger.info(f"[RAG] Loaded embedding model (method 2, after cache clear): {model_name}")
                        loaded = True
                    except Exception as e2:
                        logger.debug(f"[RAG] Method 2 failed: {e2}")
                        last_error = e2
                        
                        # Method 3: Try loading with trust_remote_code and explicit device
                        try:
                            logger.info(f"[RAG] Trying with trust_remote_code (method 3)...")
                            self.embedding_model = SentenceTransformer(
                                model_name,
                                device='cpu',
                                trust_remote_code=True,
                                model_kwargs={
                                    'torch_dtype': torch.float32,
                                    'low_cpu_mem_usage': False,
                                    'device_map': None,  # Explicitly disable device_map
                                }
                            )
                            logger.info(f"[RAG] Loaded embedding model (method 3): {model_name}")
                            loaded = True
                        except Exception as e3:
                            logger.debug(f"[RAG] Method 3 failed: {e3}")
                            last_error = e3
                            
                            # Method 4: Load using transformers directly, then wrap in SentenceTransformer
                            try:
                                logger.info(f"[RAG] Trying direct transformers load (method 4)...")
                                from transformers import AutoModel, AutoTokenizer
                                from sentence_transformers import models
                                
                                # Load model directly with explicit settings to avoid meta tensors
                                tokenizer = AutoTokenizer.from_pretrained(
                                    model_name,
                                    use_fast=True
                                )
                                
                                # Load model with all meta tensor prevention flags
                                # Use from_pretrained with explicit CPU placement
                                model = AutoModel.from_pretrained(
                                    model_name,
                                    torch_dtype=torch.float32,
                                    low_cpu_mem_usage=False,
                                    device_map=None,  # Critical: no device_map
                                )
                                
                                # Model should already be on CPU if device_map=None
                                # But don't call .cpu() or .to() as it might trigger meta tensor error
                                # Just set eval mode
                                model.eval()
                                
                                # Create SentenceTransformer components manually
                                # We'll create the transformer and then replace its model
                                word_embedding_model = models.Transformer(
                                    model_name,
                                    max_seq_length=256
                                )
                                # Replace the underlying model with our pre-loaded one
                                # This avoids SentenceTransformer trying to load it again
                                word_embedding_model.auto_model = model
                                word_embedding_model.tokenizer = tokenizer
                                
                                pooling_model = models.Pooling(
                                    word_embedding_model.get_word_embedding_dimension(),
                                    pooling_mode_mean_tokens=True,
                                    pooling_mode_cls_token=False,
                                    pooling_mode_max_tokens=False
                                )
                                
                                self.embedding_model = SentenceTransformer(
                                    modules=[word_embedding_model, pooling_model],
                                    device='cpu'
                                )
                                
                                logger.info(f"[RAG] Loaded embedding model (method 4, direct transformers): {model_name}")
                                loaded = True
                            except Exception as e4:
                                logger.debug(f"[RAG] Method 4 failed: {e4}")
                                last_error = e4
                                
                                # Method 5: Last resort - use a temporary cache directory
                                try:
                                    import tempfile
                                    logger.info(f"[RAG] Trying with temporary cache (method 5)...")
                                    with tempfile.TemporaryDirectory() as tmpdir:
                                        # This forces a fresh download
                                        self.embedding_model = SentenceTransformer(
                                            model_name,
                                            cache_folder=tmpdir,
                                            device='cpu',
                                            model_kwargs={
                                                'torch_dtype': torch.float32,
                                                'low_cpu_mem_usage': False,
                                                'device_map': None,  # Explicitly disable device_map
                                            }
                                        )
                                    logger.info(f"[RAG] Loaded embedding model (method 5): {model_name}")
                                    loaded = True
                                except Exception as e5:
                                    logger.error(f"[RAG] All loading methods failed. Last error: {e5}")
                                    last_error = e5
                else:
                    # Not a meta tensor error, re-raise
                    raise
            
            if not loaded:
                error_msg = str(last_error) if last_error else "Unknown error"
                raise RuntimeError(f"Failed to load embedding model after multiple attempts: {error_msg}")
                    
        except Exception as e:
            import traceback
            logger.error(f"[RAG] Error loading embedding model: {e}")
            logger.error(f"[RAG] Traceback: {traceback.format_exc()}")
            raise
    
    def _get_config(self):
        """Load config.json."""
        with open(settings.CONFIG_FILE, 'r') as f:
            return json.load(f)
    
    def _load_or_create_index(self):
        """Load existing index or create new one."""
        index_path = settings.EMBEDDINGS_DIR / 'faiss_index.bin'
        entries_path = settings.EMBEDDINGS_DIR / 'entries_metadata.json'
        
        # Load summaries
        self.summaries = self._load_summaries()
        
        if index_path.exists() and entries_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))
                with open(entries_path, 'r') as f:
                    metadata = json.load(f)
                    # Separate entries and summaries from metadata
                    self.entries = [item for item in metadata if not item.get('_is_summary', False)]
                    # Summaries are loaded separately, not from metadata
                logger.info(f"Loaded existing index with {len(self.entries)} entries and {len(self.summaries)} summaries")
            except Exception as e:
                logger.warning(f"Error loading index: {e}, rebuilding...")
                self.rebuild_index()
        else:
            self.rebuild_index()
    
    def _get_entry_text(self, entry: Dict[str, Any]) -> str:
        """Extract searchable text from an entry."""
        parts = [
            f"Emotion: {entry.get('emotion', '')}",
            f"Energy: {entry.get('energy', '')}",
            f"Showed up: {entry.get('showed_up', False)}",
            entry.get('free_text', ''),
            entry.get('long_reflection', ''),
        ]
        if entry.get('derived', {}).get('summary'):
            parts.append(f"Summary: {entry['derived']['summary']}")
        return ' '.join(parts)
    
    def _get_summary_text(self, summary: Dict[str, Any]) -> str:
        """Extract searchable text from a summary."""
        summary_data = summary.get('summary', {})
        stats = summary.get('stats', {})
        parts = [
            f"Summary type: {summary.get('type', 'unknown')}",
            f"Date range: {summary.get('date_range', {}).get('start', '')} to {summary.get('date_range', {}).get('end', '')}",
            f"Verdict: {summary_data.get('verdict', '')}",
            ' '.join(summary_data.get('evidence', [])),
            f"Action: {summary_data.get('action', '')}",
        ]
        # Add stats
        if stats:
            parts.append(f"Stats: {stats.get('entry_count', 0)} entries, avg energy {stats.get('avg_energy', 0)}/10")
        return ' '.join(parts)
    
    def _load_summaries(self):
        """Load week/month/year summaries from summaries directory."""
        summaries = []
        summaries_dir = settings.SUMMARIES_DIR
        
        # Load week summaries
        for filepath in sorted(summaries_dir.glob('weekly_*.json')):
            try:
                with open(filepath, 'r') as f:
                    summary = json.load(f)
                    summary['_source_file'] = filepath.name
                    summary['_is_summary'] = True
                    summary['_summary_type'] = 'week'
                    summaries.append(summary)
            except Exception as e:
                logger.warning(f"Error loading week summary {filepath}: {e}")
                continue
        
        # Load month summaries
        for filepath in sorted(summaries_dir.glob('monthly_*.json')):
            try:
                with open(filepath, 'r') as f:
                    summary = json.load(f)
                    summary['_source_file'] = filepath.name
                    summary['_is_summary'] = True
                    summary['_summary_type'] = 'month'
                    summaries.append(summary)
            except Exception as e:
                logger.warning(f"Error loading month summary {filepath}: {e}")
                continue
        
        # Load year summaries
        for filepath in sorted(summaries_dir.glob('yearly_*.json')):
            try:
                with open(filepath, 'r') as f:
                    summary = json.load(f)
                    summary['_source_file'] = filepath.name
                    summary['_is_summary'] = True
                    summary['_summary_type'] = 'year'
                    summaries.append(summary)
            except Exception as e:
                logger.warning(f"Error loading year summary {filepath}: {e}")
                continue
        
        logger.info(f"Loaded {len(summaries)} summaries")
        return summaries
    
    def rebuild_index(self):
        """Rebuild the FAISS index from all entries and summaries."""
        logger.info("Rebuilding index...")
        self.entries = []
        texts = []
        all_items = []  # Store both entries and summaries for metadata
        
        # Load all entries
        for filepath in sorted(settings.ENTRIES_DIR.glob('*.json')):
            try:
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    entry['_is_summary'] = False
                    self.entries.append(entry)
                    all_items.append(entry)
                    texts.append(self._get_entry_text(entry))
            except Exception as e:
                logger.warning(f"Error loading entry {filepath}: {e}")
                continue
        
        # Load summaries (for old data)
        self.summaries = self._load_summaries()
        
        # Add summaries to index (prefer summaries for old data)
        # Strategy: Use summaries for data older than 30 days to save tokens
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        for summary in self.summaries:
            date_range = summary.get('date_range', {})
            end_date_str = date_range.get('end', '')
            if end_date_str:
                try:
                    end_date = datetime.fromisoformat(end_date_str).date()
                    # Only index summaries for data older than 30 days (token optimization)
                    if end_date < thirty_days_ago.date():
                        all_items.append(summary)
                        texts.append(self._get_summary_text(summary))
                        logger.debug(f"[RAG] Added summary to index: {summary.get('_source_file', 'unknown')} (old data)")
                except Exception:
                    # If date parsing fails, include it anyway
                    all_items.append(summary)
                    texts.append(self._get_summary_text(summary))
        
        if not texts:
            logger.info("No entries or summaries found, creating empty index")
            # Create empty index with correct dimension
            dimension = 384  # all-MiniLM-L6-v2 dimension
            self.index = faiss.IndexFlatL2(dimension)
            self._save_index(all_items)
            return
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(texts)} items ({len(self.entries)} entries + {len([s for s in all_items if s.get('_is_summary')])} summaries)...")
        embeddings = self._encode_safe(texts)
        embeddings = np.array(embeddings).astype('float32')
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)
        
        self._save_index(all_items)
        logger.info(f"Index rebuilt with {len(self.entries)} entries and {len([s for s in all_items if s.get('_is_summary')])} summaries")
    
    def _save_index(self, all_items=None):
        """Save index and metadata."""
        index_path = settings.EMBEDDINGS_DIR / 'faiss_index.bin'
        entries_path = settings.EMBEDDINGS_DIR / 'entries_metadata.json'
        
        faiss.write_index(self.index, str(index_path))
        
        # Save all items (entries + summaries) to metadata
        if all_items is None:
            all_items = self.entries + self.summaries
        
        with open(entries_path, 'w') as f:
            json.dump(all_items, f, indent=2)
    
    def add_entry(self, entry: Dict[str, Any]):
        """Add a single entry to the index incrementally."""
        entry['_is_summary'] = False
        text = self._get_entry_text(entry)
        embedding = self._encode_safe([text])
        embedding = np.array(embedding).astype('float32')
        
        if self.index is None:
            dimension = embedding.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
        
        self.index.add(embedding)
        self.entries.append(entry)
        
        # Reload all items for saving
        entries_path = settings.EMBEDDINGS_DIR / 'entries_metadata.json'
        all_items = []
        if entries_path.exists():
            try:
                with open(entries_path, 'r') as f:
                    all_items = json.load(f)
            except Exception:
                all_items = []
        
        # Add new entry to all_items
        all_items.append(entry)
        self._save_index(all_items)
    
    def query(self, query_text: str, k: int = 5) -> Dict[str, Any]:
        """Query the RAG system."""
        # Load all items (entries + summaries) from metadata
        entries_path = settings.EMBEDDINGS_DIR / 'entries_metadata.json'
        all_items = []
        if entries_path.exists():
            try:
                with open(entries_path, 'r') as f:
                    all_items = json.load(f)
            except Exception:
                all_items = self.entries + self.summaries
        else:
            all_items = self.entries + self.summaries
        
        if self.index is None or len(all_items) == 0:
            return {
                'answer': 'No entries available yet. Please create some journal entries first.',
                'sources': [],
                'confidence_estimate': 0.0
            }
        
        # Embed query with robust error handling and fallback
        query_embedding = None
        relevant_items = []
        
        try:
            query_embedding = self._encode_safe([query_text])
            query_embedding = np.array(query_embedding).astype('float32')
            logger.debug(f"[RAG] Query embedded successfully, shape: {query_embedding.shape}")
            
            # Search with embeddings
            try:
                k = min(k, len(all_items))
                if k == 0:
                    return {
                        'answer': 'No entries available yet. Please create some journal entries first.',
                        'sources': [],
                        'confidence_estimate': 0.0
                    }
                distances, indices = self.index.search(query_embedding, k)
                
                # Get relevant items (entries or summaries) with bounds checking
                for idx in indices[0]:
                    if 0 <= idx < len(all_items):
                        relevant_items.append(all_items[idx])
            except Exception as search_error:
                logger.warning(f"[RAG] FAISS search error: {search_error}, falling back to recent entries")
                # Fallback: use most recent entries
                relevant_items = all_items[:k] if len(all_items) >= k else all_items
        except Exception as e:
            import traceback
            error_type = type(e).__name__
            error_msg = str(e) if e and str(e) else f"{error_type} occurred"
            logger.warning(f"[RAG] Embedding error ({error_type}): {error_msg}. Using fallback: recent entries.")
            logger.debug(f"[RAG] Full traceback: {traceback.format_exc()}")
            
            # Fallback: use most recent entries instead of semantic search
            logger.info("[RAG] Using fallback: returning most recent entries for context")
            relevant_items = all_items[:k] if len(all_items) >= k else all_items
            
            # Try to reload embedding model in background for next time
            try:
                logger.debug("[RAG] Attempting to reload embedding model in background...")
                self._load_embedding_model()
                logger.info("[RAG] Embedding model reloaded for future queries")
            except Exception as reload_error:
                logger.debug(f"[RAG] Background reload failed (non-critical): {reload_error}")
        
        # If we still don't have relevant items, use recent entries
        if not relevant_items and all_items:
            logger.info("[RAG] No relevant items found, using most recent entries")
            relevant_items = all_items[:k] if len(all_items) >= k else all_items
        
        # Build context for LLM with intelligent summarization strategy
        # Strategy: Prioritize recent entries, use summaries for older data
        # Token optimization: max 1500 chars (~375 tokens) for better 2-3 sentence responses
        from datetime import datetime, timedelta
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        context_parts = []
        max_context_chars = 1500  # Increased slightly for 2-3 sentence responses
        current_length = 0
        
        # Separate recent entries from older summaries
        recent_entries = []
        older_summaries = []
        
        for item in relevant_items:
            is_summary = item.get('_is_summary', False)
            if is_summary:
                older_summaries.append(item)
            else:
                # Check if entry is recent
                try:
                    entry_date = datetime.fromisoformat(item.get('timestamp', '').replace('Z', '+00:00')).date()
                    if entry_date >= seven_days_ago.date():
                        recent_entries.append(item)
                    else:
                        # Older entry - prefer summary if available
                        older_summaries.append(item)
                except:
                    recent_entries.append(item)
        
        # Prioritize: recent entries first, then summaries (max 3 summaries to save tokens)
        prioritized_items = recent_entries + older_summaries[:3]
        
        for item in prioritized_items:
            is_summary = item.get('_is_summary', False)
            item_text = ""
            
            if is_summary:
                # Handle summary - concise format (token optimized)
                summary_type = item.get('_summary_type', 'unknown')
                date_range = item.get('date_range', {})
                summary_data = item.get('summary', {})
                
                item_text = f"{summary_type.capitalize()} Summary ({date_range.get('start', '')} to {date_range.get('end', '')}): "
                item_text += f"{summary_data.get('verdict', 'N/A')[:120]}"
                evidence = summary_data.get('evidence', [])
                if evidence:
                    item_text += f" Evidence: {', '.join(evidence[:2])[:100]}"
            else:
                # Handle entry - concise format for token optimization
                entry_date = item.get('timestamp', '')[:10]  # YYYY-MM-DD
                filename = f"{item.get('timestamp', '').replace(':', '-').split('.')[0]}Z__{item.get('id', '')}.json"
                item_text = f"Entry {entry_date} ({filename}): {item.get('emotion', 'N/A')}, Energy {item.get('energy', 'N/A')}/10"
                if item.get('showed_up'):
                    item_text += ", showed up"
                if item.get('free_text'):
                    item_text += f", {item.get('free_text')[:100]}"
            
            # Only add if we haven't exceeded token limit
            if current_length + len(item_text) > max_context_chars:
                logger.debug(f"[RAG] Context limit reached ({current_length} chars), stopping for token optimization")
                break
            context_parts.append(item_text)
            current_length += len(item_text) + 1  # +1 for newline
        
        context = '\n'.join(context_parts)
        logger.debug(f"[RAG] Context built: {len(context)} chars (~{len(context) // 4} tokens), {len(recent_entries)} recent entries, {len(older_summaries)} summaries")
        
        # Generate answer using LLM with token optimization
        try:
            config = self._get_config()
            system_instruction, user_prompt = self._build_query_prompt_optimized(query_text, context, config)
            
            try:
                # Use optimized call with system instruction for Gemini
                from .llm_adapter import _using_gemini, _call_gemini
                if _using_gemini():
                    llm_response = _call_gemini(
                        prompt=user_prompt,
                        max_tokens=512,  # Optimized: 512 tokens for 2-3 sentence query responses
                        temp=0.2,
                        system_instruction=system_instruction
                    )
                else:
                    # Local model: combine system and user
                    prompt = f"{system_instruction}\n\n{user_prompt}"
                    llm_response = call_local_llm(prompt, max_tokens=512, temp=0.2)
                answer = self._parse_llm_response(llm_response)
            except Exception as e:
                import traceback
                print(f"LLM error: {e}")
                print(f"LLM traceback: {traceback.format_exc()}")
                answer = {
                    'verdict': 'Unable to generate response at this time.',
                    'evidence': [],
                    'action': 'Please try again later.',
                    'confidence_estimate': 0
                }
        except Exception as e:
            import traceback
            print(f"RAG query processing error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            # Return a basic response if there's an error
            answer = {
                'verdict': 'Unable to process query due to a system error.',
                'evidence': [],
                'action': 'Please try again later.',
                'confidence_estimate': 0
            }
        
        # Build sources (handle both entries and summaries)
        sources = []
        for item in relevant_items:
            is_summary = item.get('_is_summary', False)
            
            if is_summary:
                # Handle summary source
                date_range = item.get('date_range', {})
                source_file = item.get('_source_file', 'unknown')
                summary_type = item.get('_summary_type', 'unknown')
                sources.append({
                    'date': date_range.get('start', ''),
                    'emotion': 'summary',
                    'filename': source_file,
                    'type': summary_type,
                    'date_range': date_range
                })
            else:
                # Handle entry source
                entry_date = item.get('timestamp', '')[:10]
                filename = f"{item.get('timestamp', '').replace(':', '-').split('.')[0]}Z__{item.get('id', '')}.json"
                sources.append({
                    'date': entry_date,
                    'emotion': item.get('emotion', 'unknown'),
                    'filename': filename,
                    'type': 'entry'
                })
        
        confidence = min(len(relevant_items) / k, 1.0)
        
        return {
            'answer': self._format_answer(answer),
            'sources': sources,
            'confidence_estimate': confidence,
            'structured': answer
        }
    
    def _build_query_prompt_optimized(self, query: str, context: str, config: Dict) -> tuple:
        """
        Build optimized prompt for query answering.
        Returns (system_instruction, user_prompt) tuple for token-efficient Gemini calls.
        """
        # Load prompt template
        prompt_path = Path(__file__).parent.parent / 'prompts' / 'query_prompt.txt'
        try:
            with open(prompt_path, 'r') as f:
                template = f.read()
            # Split template into system and user parts
            if "Context from journal entries:" in template:
                parts = template.split("Context from journal entries:", 1)
                system_instruction = parts[0].strip()
                user_template = "Context from journal entries:" + parts[1] if len(parts) > 1 else ""
            else:
                system_instruction = template
                user_template = "Context:\n{context}\n\nUser question: {query}\n\nAnswer in the required format."
            
            user_prompt = user_template.format(context=context, query=query)
            return system_instruction, user_prompt
        except Exception:
            # Fallback to inline prompt - optimized for tokens
            system_instruction = """You are a gentle, supportive personal coach. Help understand patterns and suggest small changes.

Response format:
VERDICT: [One sentence]
EVIDENCE:
- [Point with filename]
- [Point with filename]
ACTION: [One small action]
CONFIDENCE_ESTIMATE: [0-100]

Be gentle, neutral, use only provided context."""
        
            user_prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer in the required format."""
        
            return system_instruction, user_prompt
    
    def _build_query_prompt(self, query: str, context: str, config: Dict) -> str:
        """Legacy method - kept for compatibility."""
        system_instruction, user_prompt = self._build_query_prompt_optimized(query, context, config)
        return f"{system_instruction}\n\n{user_prompt}"
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        result = {
            'verdict': '',
            'evidence': [],
            'action': '',
            'confidence_estimate': 0
        }
        
        if not response or len(response.strip()) < 10:
            result['verdict'] = 'Unable to generate response at this time.'
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
            if len(first_line) > 20:
                result['verdict'] = first_line[:200]
            else:
                # Look for any sentence in the response
                sentences = response.split('.')
                for sent in sentences:
                    sent = sent.strip()
                    if len(sent) > 20 and not sent.startswith('VERDICT') and not sent.startswith('EVIDENCE'):
                        result['verdict'] = sent[:200]
                        break
                if not result['verdict']:
                    result['verdict'] = response[:200] if len(response) > 20 else 'Unable to generate response at this time.'
        
        # Calculate confidence if not provided
        if result['confidence_estimate'] == 0:
            result['confidence_estimate'] = min(100, 20 * max(1, len(result['evidence'])))
        
        return result
    
    def _format_answer(self, answer: Dict[str, Any]) -> str:
        """Format structured answer as readable text."""
        parts = []
        if answer.get('verdict'):
            parts.append(answer['verdict'])
        if answer.get('evidence'):
            parts.append('\nEvidence:')
            for ev in answer['evidence']:
                parts.append(f"  • {ev}")
        if answer.get('action'):
            parts.append(f"\nSuggested action: {answer['action']}")
        if answer.get('confidence_estimate'):
            parts.append(f"\nConfidence: {answer['confidence_estimate']}%")
        
        return '\n'.join(parts) if parts else "Unable to generate response."

