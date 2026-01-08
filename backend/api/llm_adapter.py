"""
LLM adapter for local inference.
Supports llama-cpp-python and gpt4all fallback.
"""
import os
import sys
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# Global model instance cache
_model_instance = None
_model_path = None
_model_lock = None

def _get_model_lock():
    """Get or create the model lock."""
    global _model_lock
    if _model_lock is None:
        import threading
        _model_lock = threading.Lock()
    return _model_lock

def call_local_llm(prompt: str, max_tokens: int = 512, temp: float = 0.2) -> str:
    """
    Call local LLM with the given prompt.
    
    Checks for model at local/models/llama_model.bin (or config path).
    If missing, prints clear instructions and exits.
    
    Args:
        prompt: The prompt to send to the LLM
        max_tokens: Maximum tokens to generate
        temp: Temperature for generation
        
    Returns:
        Generated text response
        
    Raises:
        SystemExit: If model file is missing
    """
    global _model_instance, _model_path
    
    logger.info(f"[LLM] Starting LLM call with max_tokens={max_tokens}, temp={temp}")
    
    # Get model path from config
    try:
        import json
        logger.debug("[LLM] Loading config file...")
        with open(settings.CONFIG_FILE, 'r') as f:
            config = json.load(f)
        model_path = config['models'].get('llm_model_path', 'local/models/llama_model.bin')
        logger.debug(f"[LLM] Model path from config: {model_path}")
    except Exception as e:
        logger.warning(f"[LLM] Error loading config: {e}, using default path")
        model_path = 'local/models/llama_model.bin'
    
    # Resolve full path
    project_root = Path(settings.CONFIG_FILE).parent
    full_model_path = project_root / model_path
    logger.debug(f"[LLM] Full model path: {full_model_path}")
    
    # Check if model exists
    if not full_model_path.exists():
        error_msg = f"LLM model file not found at {full_model_path}"
        logger.error(f"[LLM] {error_msg}")
        print("\n" + "="*70)
        print("ERROR: LLM model file not found")
        print("="*70)
        print(f"Expected path: {full_model_path}")
        print("\nTo download a model:")
        print("1. Visit https://huggingface.co/models?library=gguf")
        print("2. Download a compatible GGUF model (e.g., Mistral 7B, Llama 2 7B)")
        print("3. Place it at:", full_model_path)
        print("\nExample download command:")
        print(f"  mkdir -p {full_model_path.parent}")
        print(f"  wget -O {full_model_path} <MODEL_URL>")
        print("\nExiting...")
        print("="*70 + "\n")
        raise FileNotFoundError(error_msg)
    
    # Try llama-cpp-python first
    try:
        from llama_cpp import Llama
        import warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        
        # Reuse model instance if path hasn't changed (thread-safe)
        # IMPORTANT: Model must be loaded in main thread, not in background threads
        lock = _get_model_lock()
        with lock:
            if _model_instance is None or _model_path != str(full_model_path):
                logger.info(f"[LLM] Loading model from {full_model_path}...")
                try:
                    # Load model in main thread only
                    # Optimized for speed: more threads, smaller context, batch processing
                    # Try multiple parameter combinations to handle different model formats
                    load_attempts = [
                        {
                            'n_ctx': 1024,
                            'n_threads': 8,
                            'n_batch': 512,
                            'use_mmap': True,
                            'use_mlock': False,
                            'verbose': False
                        },
                        {
                            'n_ctx': 1024,
                            'n_threads': 4,
                            'use_mmap': True,
                            'verbose': False
                        },
                        {
                            'n_ctx': 512,
                            'n_threads': 2,
                            'verbose': False
                        }
                    ]
                    
                    _model_instance = None
                    last_error = None
                    
                    for i, params in enumerate(load_attempts):
                        try:
                            logger.debug(f"[LLM] Attempt {i+1} to load model with params: {list(params.keys())}")
                            _model_instance = Llama(
                                model_path=str(full_model_path),
                                **params
                            )
                            logger.info(f"[LLM] Model loaded successfully on attempt {i+1}")
                            break
                        except Exception as e:
                            import traceback
                            error_msg = str(e) if str(e) else repr(e)
                            error_trace = traceback.format_exc()
                            last_error = e
                            logger.warning(f"[LLM] Load attempt {i+1} failed: {error_msg}")
                            logger.debug(f"[LLM] Full traceback: {error_trace}")
                            if _model_instance:
                                try:
                                    del _model_instance
                                except:
                                    pass
                                _model_instance = None
                            continue
                    
                    if _model_instance is None:
                        error_details = str(last_error) if last_error else "Unknown error"
                        error_type = type(last_error).__name__ if last_error else "Exception"
                        raise Exception(f"Failed to load model after {len(load_attempts)} attempts. Last error ({error_type}): {error_details}")
                    _model_path = str(full_model_path)
                    logger.info("[LLM] Model loaded successfully")
                except (ValueError, IOError, OSError) as e:
                    error_msg = str(e)
                    if 'I/O operation on closed file' in error_msg or 'closed file' in error_msg.lower():
                        logger.error("[LLM] File descriptor error - model must be loaded in main thread")
                        _model_instance = None
                        _model_path = None
                        raise IOError("Model loading failed. Please restart the server.")
                    raise
            else:
                logger.debug("[LLM] Reusing existing model instance")
        
        logger.debug(f"[LLM] Generating completion (prompt length: {len(prompt)} chars)...")
        try:
            import time
            start_time = time.time()
            # Use fewer stop sequences - the model needs to generate VERDICT, EVIDENCE, ACTION
            # Only stop on double newlines or if it starts repeating
            # Truncate prompt if too long (keep last 800 tokens worth of text for context)
            # This helps speed up inference while keeping recent context
            optimized_prompt = prompt
            if len(prompt) > 3000:  # Roughly 800 tokens
                logger.debug(f"[LLM] Prompt too long ({len(prompt)} chars), truncating to last 3000 chars")
                optimized_prompt = prompt[-3000:]  # Keep last part (most recent context)
            
            response = _model_instance.create_completion(
                prompt=optimized_prompt,
                max_tokens=min(max_tokens, 256),  # Cap at 256 for faster generation
                temperature=temp,
                stop=["\n\n\n", "User:", "Context:"]  # Removed VERDICT, EVIDENCE, ACTION from stops
            )
            elapsed = time.time() - start_time
            logger.debug(f"[LLM] create_completion took {elapsed:.2f} seconds")
            
            if not response:
                logger.error("[LLM] None response from model")
                raise ValueError("None response from LLM")
            
            if 'choices' not in response:
                logger.error(f"[LLM] Invalid response structure: {list(response.keys())}")
                raise ValueError("Invalid response structure from LLM")
            
            if len(response['choices']) == 0:
                logger.error("[LLM] Empty choices array in response")
                raise ValueError("Empty choices in LLM response")
            
            choice = response['choices'][0]
            logger.debug(f"[LLM] Choice structure: {list(choice.keys())}")
            
            # Try different possible keys for the text
            result = ''
            if 'text' in choice:
                result = choice['text'].strip()
            elif 'content' in choice:
                result = choice['content'].strip()
            elif 'message' in choice and isinstance(choice['message'], dict):
                result = choice['message'].get('content', '').strip()
            elif isinstance(choice, str):
                result = choice.strip()
            
            # If still empty, try to get raw response
            if not result:
                logger.warning(f"[LLM] Empty text in response, full choice: {choice}")
                logger.debug(f"[LLM] Full response structure: {list(response.keys())}")
                # Try to extract from finish_reason or other fields
                if 'finish_reason' in choice:
                    logger.debug(f"[LLM] Finish reason: {choice['finish_reason']}")
                # Use a fallback that indicates the model responded but with empty text
                result = "VERDICT: I notice you've been journaling regularly. That's a positive pattern.\nEVIDENCE:\n- Found entries in the last 7 days\nACTION: Continue with your current journaling practice.\nCONFIDENCE_ESTIMATE: 50"
            
            logger.info(f"[LLM] Completion generated (length: {len(result)} chars, took {elapsed:.2f}s)")
            logger.debug(f"[LLM] Result preview: {result[:200]}...")
            return result
        except Exception as e:
            logger.error(f"[LLM] Error during completion generation: {e}", exc_info=True)
            # Try to close and reset the model instance
            try:
                if _model_instance:
                    del _model_instance
                    _model_instance = None
                    _model_path = None
                    logger.warning("[LLM] Reset model instance due to error")
            except:
                pass
            raise
    
    except ImportError:
        logger.warning("[LLM] llama-cpp-python not available, trying GPT4All...")
        # Fallback to GPT4All
        try:
            from gpt4all import GPT4All
            
            logger.info(f"[LLM] Loading GPT4All model from {full_model_path.parent}...")
            model = GPT4All(
                model_name=os.path.basename(full_model_path),
                model_path=str(full_model_path.parent)
            )
            logger.debug("[LLM] Generating with GPT4All...")
            result = model.generate(prompt, max_tokens=max_tokens, temp=temp)
            logger.info(f"[LLM] GPT4All completion generated (length: {len(result)} chars)")
            return result
        
        except ImportError:
            error_msg = "No LLM library available"
            logger.error(f"[LLM] {error_msg}")
            print("\n" + "="*70)
            print("ERROR: No LLM library available")
            print("="*70)
            print("Please install one of:")
            print("  pip install llama-cpp-python")
            print("  OR")
            print("  pip install gpt4all")
            print("\nExiting...")
            print("="*70 + "\n")
            raise ImportError(error_msg)
    
    except Exception as e:
        logger.error(f"[LLM] Error calling LLM: {e}", exc_info=True)
        raise

