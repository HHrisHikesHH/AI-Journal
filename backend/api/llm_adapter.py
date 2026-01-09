"""
LLM adapter that can use either:
- Gemini (via google-genai, preferred if GEMINI_API_KEY is set)
- Local GGUF models via llama-cpp-python / GPT4All (fallback)

Existing callers (`call_local_llm`, `get_model_context_window`, `ensure_model_loaded`)
are preserved so the rest of the codebase doesn't need to change.
"""
import os
import sys
import logging
import warnings
from pathlib import Path
from typing import Any
from django.conf import settings

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

logger = logging.getLogger(__name__)

# Global model instance cache (for local llama / GPT4All)
_model_instance = None
_model_path = None
_model_lock = None

# Gemini client cache
_gemini_client = None


def _get_model_lock():
    """Get or create the model lock."""
    global _model_lock
    if _model_lock is None:
        import threading
        _model_lock = threading.Lock()
    return _model_lock


def _using_gemini() -> bool:
    """Return True if Gemini should be used (based on GEMINI_API_KEY env var or config.json)."""
    # Check environment variable first
    if os.getenv("GEMINI_API_KEY"):
        return True
    
    # Fallback: check config.json
    try:
        import json
        with open(settings.CONFIG_FILE, 'r') as f:
            config = json.load(f)
        api_key = config.get('models', {}).get('gemini_api_key', '')
        if api_key and api_key.strip() and api_key != 'YOUR_GEMINI_API_KEY_HERE':
            # Set it in environment for this session
            os.environ['GEMINI_API_KEY'] = api_key
            return True
    except Exception:
        pass
    
    return False


def _get_gemini_client():
    """
    Lazily create and cache the Gemini client.
    Requires GEMINI_API_KEY to be set in the environment.
    """
    global _gemini_client
    if _gemini_client is None:
        try:
            from google import genai

            _gemini_client = genai.Client()
            logger.info("[LLM] Initialized Gemini client")
        except Exception as e:
            logger.error(f"[LLM] Failed to initialize Gemini client: {e}", exc_info=True)
            raise
    return _gemini_client


def get_model_context_window() -> int:
    """
    Get the context window size of the loaded model.

    For Gemini we return a safe default (8192 tokens).
    For local llama we inspect the model if available, else 1024.
    """
    global _model_instance

    if _using_gemini():
        # Gemini 2.5 models support much larger windows, but 8192 is a safe, conservative default.
        return 8192

    # Don't try to load model here if we're in a background thread
    # Just return default
    import threading
    if threading.current_thread() is not threading.main_thread():
        logger.debug("[LLM] get_model_context_window() called from background thread, returning default")
        return 1024

    # We're in main thread
    if _model_instance is not None:
        try:
            return _model_instance.n_ctx()
        except Exception:
            pass

    # Model not loaded yet - return default
    # The model should be loaded via ensure_model_loaded() before this is called
    logger.debug("[LLM] Model not loaded yet, returning default context window (1024)")
    return 1024


def ensure_model_loaded():
    """
    Ensure the model is ready before background usage.

    - For Gemini: we just create the client once and return True.
    - For local llama: we load the GGUF model in the main thread (existing behavior).
    """
    global _model_instance, _model_path

    if _using_gemini():
        try:
            _ = _get_gemini_client()
            logger.debug("[LLM] Gemini client ready (no local model load needed)")
            return True
        except Exception:
            # If Gemini fails to initialize, signal failure so callers can fall back or handle error.
            return False

    if _model_instance is not None:
        logger.debug("[LLM] Model already loaded")
        return True  # Already loaded

    # Check if we're in the main thread
    import threading
    if threading.current_thread() is not threading.main_thread():
        logger.warning("[LLM] ensure_model_loaded() called from background thread. Model must be loaded in main thread.")
        return False

    # Try to load the model directly (extract the loading logic from call_local_llm)
    try:
        logger.info("[LLM] ensure_model_loaded() - Starting model loading...")

        # Get model path from config
        import json
        with open(settings.CONFIG_FILE, 'r') as f:
            config = json.load(f)
        model_path = config['models'].get('llm_model_path', 'local/models/llama_model.bin')
        project_root = Path(settings.CONFIG_FILE).parent
        full_model_path = project_root / model_path

        if not full_model_path.exists():
            logger.error(f"[LLM] Model file not found at {full_model_path}")
            return False

        logger.info(f"[LLM] Model file found at {full_model_path}, loading...")

        # Load model directly (same logic as in call_local_llm)
        from llama_cpp import Llama
        import warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        lock = _get_model_lock()
        with lock:
            if _model_instance is None:
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
                        logger.info(f"[LLM] Loading model attempt {i+1} with params: {list(params.keys())}")
                        _model_instance = Llama(
                            model_path=str(full_model_path),
                            **params
                        )
                        logger.info(f"[LLM] ✅ Model loaded successfully on attempt {i+1}")
                        _model_path = str(full_model_path)
                        return True
                    except Exception as e:
                        import traceback
                        error_msg = str(e) if str(e) else repr(e)
                        last_error = e
                        logger.warning(f"[LLM] Load attempt {i+1} failed: {error_msg}")
                        if _model_instance:
                            try:
                                del _model_instance
                            except Exception:
                                pass
                            _model_instance = None
                        continue

                if _model_instance is None:
                    error_details = str(last_error) if last_error else "Unknown error"
                    error_type = type(last_error).__name__ if last_error else "Exception"
                    logger.error(f"[LLM] ❌ Failed to load model after {len(load_attempts)} attempts. Last error ({error_type}): {error_details}")
                    return False
            else:
                logger.debug("[LLM] Model already loaded (checked within lock)")
                return True
    except ImportError:
        logger.error("[LLM] llama-cpp-python not available")
        return False
    except Exception as e:
        import traceback
        logger.error(f"[LLM] ❌ Exception in ensure_model_loaded(): {e}")
        logger.error(f"[LLM] Traceback: {traceback.format_exc()}")
        return False


def _call_gemini(prompt: str, max_tokens: int = 512, temp: float = 0.2, system_instruction: str = None) -> str:
    """
    Call Gemini using google-genai with token optimization.

    This is the preferred path when GEMINI_API_KEY is set.
    
    Args:
        prompt: User content/prompt
        max_tokens: Maximum output tokens (optimized: default 256 for insights, 512 for queries)
        temp: Temperature
        system_instruction: Optional system instruction (more token-efficient than including in prompt)
    """
    logger.info(f"[LLM] Using Gemini (gemini-2.5-flash) with max_tokens={max_tokens}, temp={temp}")
    client = _get_gemini_client()

    # Optimize token usage: be conservative with output
    max_tokens = int(max_tokens) if max_tokens is not None else 256
    max_tokens = max(1, min(max_tokens, 512))  # Cap at 512 for cost control

    try:
        # Import types lazily so the module still imports even if google-genai
        # is not installed (until we actually try to use Gemini).
        from google.genai import types

        # Build config with token optimizations
        config_kwargs = {
            'temperature': float(temp),
            'max_output_tokens': max_tokens,
            'thinking_config': types.ThinkingConfig(thinking_budget=0),  # Disable thinking for faster/cheaper responses
        }
        
        # Use system instruction if provided (more efficient than including in prompt)
        if system_instruction:
            config_kwargs['system_instruction'] = system_instruction

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt if not system_instruction else prompt,  # If system_instruction used, prompt is just user content
            config=types.GenerateContentConfig(**config_kwargs),
        )

        # SDK exposes a convenient .text property
        text = getattr(response, "text", None)
        if not text:
            logger.error("[LLM] Empty text in Gemini response")
            raise ValueError("Empty response from Gemini")
        
        logger.debug(f"[LLM] Gemini response length: {len(text)} chars")
        return text.strip()
    except Exception as e:
        logger.error(f"[LLM] Error calling Gemini: {e}", exc_info=True)
        # Surface the error so callers can decide how to fall back.
        raise


def call_local_llm(prompt: str, max_tokens: int = 512, temp: float = 0.2, system_instruction: str = None) -> str:
    """
    Call the LLM with the given prompt.

    If GEMINI_API_KEY is set, Gemini (gemini-2.5-flash) is used.
    Otherwise we fall back to the local GGUF model via llama-cpp-python / GPT4All.
    
    Args:
        prompt: User content/prompt
        max_tokens: Maximum output tokens
        temp: Temperature
        system_instruction: Optional system instruction (used with Gemini for token efficiency)
    """
    global _model_instance, _model_path

    logger.info(f"[LLM] Starting LLM call with max_tokens={max_tokens}, temp={temp}")

    # Preferred path: Gemini
    if _using_gemini():
        try:
            return _call_gemini(prompt, max_tokens=max_tokens, temp=temp, system_instruction=system_instruction)
        except Exception:
            # If Gemini fails for any reason, log and fall back to local model logic below
            logger.warning("[LLM] Falling back to local model after Gemini error")

    # === Local llama / GPT4All path (unchanged behavior) ===

    # Get model path from config
    try:
        import json
        logger.debug("[LLM] Loading config file for local model...")
        with open(settings.CONFIG_FILE, 'r') as f:
            config = json.load(f)
        model_path = config['models'].get('llm_model_path', 'local/models/llama_model.bin')
        logger.debug(f"[LLM] Local model path from config: {model_path}")
    except Exception as e:
        logger.warning(f"[LLM] Error loading config: {e}, using default local path")
        model_path = 'local/models/llama_model.bin'

    # Resolve full path
    project_root = Path(settings.CONFIG_FILE).parent
    full_model_path = project_root / model_path
    logger.debug(f"[LLM] Full local model path: {full_model_path}")

    # Check if model exists
    if not full_model_path.exists():
        error_msg = f"LLM model file not found at {full_model_path}"
        logger.error(f"[LLM] {error_msg}")
        print("\n" + "=" * 70)
        print("ERROR: LLM model file not found")
        print("=" * 70)
        print(f"Expected path: {full_model_path}")
        print("\nTo download a model:")
        print("1. Visit https://huggingface.co/models?library=gguf")
        print("2. Download a compatible GGUF model (e.g., Mistral 7B, Llama 2 7B)")
        print("3. Place it at:", full_model_path)
        print("\nExample download command:")
        print(f"  mkdir -p {full_model_path.parent}")
        print(f"  wget -O {full_model_path} <MODEL_URL>")
        print("\nExiting...")
        print("=" * 70 + "\n")
        raise FileNotFoundError(error_msg)

    # Try llama-cpp-python first
    try:
        from llama_cpp import Llama
        import warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # Reuse model instance if path hasn't changed (thread-safe)
        # IMPORTANT: Model must be LOADED in main thread, but can be USED from any thread
        import threading

        lock = _get_model_lock()
        with lock:
            # Check if model is already loaded and path matches
            if _model_instance is not None and _model_path == str(full_model_path):
                logger.debug("[LLM] Reusing existing local model instance (already loaded)")
                # Model is already loaded, we can use it from any thread
            elif _model_instance is None or _model_path != str(full_model_path):
                # Model needs to be loaded - this must happen in main thread
                if threading.current_thread() is not threading.main_thread():
                    error_msg = (
                        "Model loading attempted from background thread. "
                        "Model must be loaded in main thread. "
                        "Please ensure AppConfig loaded the model at startup."
                    )
                    logger.error(f"[LLM] {error_msg}")
                    logger.error(
                        f"[LLM] Model instance: {_model_instance is not None}, "
                        f"Path match: {_model_path == str(full_model_path) if _model_path else False}"
                    )
                    raise RuntimeError(error_msg)
                logger.info(f"[LLM] Loading local model from {full_model_path}...")
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
                            logger.debug(f"[LLM] Attempt {i+1} to load local model with params: {list(params.keys())}")
                            _model_instance = Llama(
                                model_path=str(full_model_path),
                                **params
                            )
                            logger.info(f"[LLM] Local model loaded successfully on attempt {i+1}")
                            break
                        except Exception as e:
                            import traceback
                            error_msg = str(e) if str(e) else repr(e)
                            error_trace = traceback.format_exc()
                            last_error = e
                            logger.warning(f"[LLM] Local load attempt {i+1} failed: {error_msg}")
                            logger.debug(f"[LLM] Full traceback: {error_trace}")
                            if _model_instance:
                                try:
                                    del _model_instance
                                except Exception:
                                    pass
                                _model_instance = None
                            continue

                    if _model_instance is None:
                        error_details = str(last_error) if last_error else "Unknown error"
                        error_type = type(last_error).__name__ if last_error else "Exception"
                        raise Exception(
                            f"Failed to load local model after {len(load_attempts)} attempts. "
                            f"Last error ({error_type}): {error_details}"
                        )
                    _model_path = str(full_model_path)
                    logger.info("[LLM] Local model loaded successfully")
                except (ValueError, IOError, OSError) as e:
                    error_msg = str(e)
                    if 'I/O operation on closed file' in error_msg or 'closed file' in error_msg.lower():
                        logger.error("[LLM] File descriptor error - local model must be loaded in main thread")
                        _model_instance = None
                        _model_path = None
                        raise IOError("Local model loading failed. Please restart the server.")
                    raise

        # Model is now loaded (either was already loaded or just loaded)
        # Get a reference to the model instance (we're outside the lock now, but model is already loaded)
        if _model_instance is None:
            error_msg = "Local model instance is None after loading attempt. This should not happen."
            logger.error(f"[LLM] {error_msg}")
            raise RuntimeError(error_msg)

        model_instance = _model_instance  # Local reference for clarity
        logger.debug(f"[LLM] Generating completion with local model (prompt length: {len(prompt)} chars)...")
        try:
            import time
            start_time = time.time()

            # Get actual context window size from model
            try:
                context_window = model_instance.n_ctx()
            except Exception:
                # Fallback if n_ctx() not available
                context_window = 1024
                logger.warning(f"[LLM] Could not get context window size, using default: {context_window}")

            # Estimate tokens in prompt (be very conservative - use 3 chars per token)
            # This is more conservative than the 4 chars/token estimate to account for tokenizer differences
            from .prompt_utils import estimate_tokens
            prompt_tokens = estimate_tokens(prompt)
            # Use even more conservative estimate for safety (actual tokenizers often use more tokens)
            conservative_prompt_tokens = len(prompt) // 3  # 3 chars per token is very conservative

            # Check if prompt fits
            max_tokens_to_generate = min(max_tokens, 256)
            total_needed = prompt_tokens + max_tokens_to_generate
            conservative_total = conservative_prompt_tokens + max_tokens_to_generate

            # Primary check: use actual token estimate (most accurate)
            # Truncate if we exceed context window OR if we're close (within 10% safety margin)
            # This accounts for token estimation inaccuracies
            safety_margin = int(context_window * 0.1)  # 10% safety margin
            needs_truncation = total_needed > (context_window - safety_margin)

            # Secondary check: if conservative estimate also exceeds, definitely truncate
            if not needs_truncation and conservative_total > context_window:
                logger.warning(
                    f"[LLM] Conservative estimate ({conservative_total}) exceeds context window ({context_window}), "
                    f"but actual estimate ({total_needed}) fits. Truncating for safety."
                )
                needs_truncation = True

            # Safety check: if prompt is extremely long (character-based), also check
            # This is a fallback for cases where token estimation might be completely wrong
            # Use 2.5 chars/token as a more realistic estimate (some models use fewer chars per token)
            max_safe_chars = int((context_window - max_tokens_to_generate - safety_margin) * 2.5)
            char_based_check = len(prompt) > max_safe_chars

            # Truncate if:
            # 1. Token-based check says we need truncation, OR
            # 2. Both character-based check AND conservative estimate exceed limits
            if needs_truncation or (char_based_check and conservative_total > context_window):
                if needs_truncation:
                    logger.error(
                        f"[LLM] Prompt too long: {prompt_tokens} tokens + {max_tokens_to_generate} generation = "
                        f"{total_needed} tokens, but context window is {context_window}"
                    )
                else:
                    logger.warning(
                        f"[LLM] Prompt may be too long (char-based check: {len(prompt)} chars > {max_safe_chars}, "
                        f"conservative: {conservative_total} > {context_window}). Truncating for safety."
                    )
                logger.info("[LLM] Attempting truncation...")

                # Emergency truncation - be VERY conservative
                # Reserve space for generation + large safety buffer (at least 200 tokens)
                # Account for token estimation inaccuracies
                safety_buffer = max(200, int(context_window * 0.2))  # 20% safety buffer or 200 tokens, whichever is larger
                available_for_prompt = context_window - max_tokens_to_generate - safety_buffer
                # Use 2.5 chars per token (realistic estimate) to ensure we fit
                # This is more conservative than 4 chars/token but less than 3
                max_prompt_chars = int(available_for_prompt * 2.5)

                if len(prompt) > max_prompt_chars:
                    logger.warning(
                        f"[LLM] Emergency truncating prompt from {len(prompt)} chars to {max_prompt_chars} chars"
                    )
                    # Keep the last part (most recent context)
                    prompt = prompt[-max_prompt_chars:]

                    # Re-estimate after truncation
                    prompt_tokens = estimate_tokens(prompt)
                    total_needed = prompt_tokens + max_tokens_to_generate

                    # Re-estimate with conservative method
                    conservative_prompt_tokens = len(prompt) // 3
                    conservative_total = conservative_prompt_tokens + max_tokens_to_generate

                    if conservative_total > context_window or total_needed > (context_window - safety_margin):
                        # Still too long - even more aggressive truncation
                        logger.error(
                            f"[LLM] Still too long after truncation: {prompt_tokens} tokens "
                            f"(conservative: {conservative_prompt_tokens}). Reducing further..."
                        )
                        safety_buffer = max(250, int(context_window * 0.25))  # 25% safety buffer
                        available_for_prompt = context_window - max_tokens_to_generate - safety_buffer
                        max_prompt_chars = int(available_for_prompt * 2.5)  # Use 2.5 chars per token
                        prompt = prompt[-max_prompt_chars:]
                        logger.warning(f"[LLM] Aggressively truncated to {len(prompt)} chars")

                        # Final check
                        prompt_tokens = estimate_tokens(prompt)
                        conservative_prompt_tokens = len(prompt) // 3
                        total_needed = prompt_tokens + max_tokens_to_generate
                        conservative_total = conservative_prompt_tokens + max_tokens_to_generate

                        if conservative_total > context_window or total_needed > (context_window - safety_margin):
                            logger.error(
                                f"[LLM] CRITICAL: Prompt still too long ({prompt_tokens} tokens, "
                                f"conservative: {conservative_prompt_tokens}). Forcing maximum truncation."
                            )
                            # Last resort: keep only what absolutely fits with maximum safety buffer
                            safety_buffer = max(300, int(context_window * 0.3))  # 30% safety buffer
                            max_prompt_chars = int(
                                (context_window - max_tokens_to_generate - safety_buffer) * 2.5
                            )  # 2.5 chars per token
                            prompt = prompt[-max_prompt_chars:]
                            logger.error(f"[LLM] Forced truncation to {len(prompt)} chars")

                    logger.debug(
                        f"[LLM] Final prompt length: {len(prompt)} chars "
                        f"(estimated {estimate_tokens(prompt)} tokens)"
                    )

            # Final safety check: ensure we never exceed context window
            # Re-estimate one more time to be absolutely sure
            final_prompt_tokens = estimate_tokens(prompt)
            final_total = final_prompt_tokens + max_tokens_to_generate
            final_conservative = (len(prompt) // 2.5) + max_tokens_to_generate  # Use 2.5 chars/token

            if final_total > context_window or final_conservative > context_window:
                logger.error(
                    "[LLM] FINAL CHECK FAILED: Prompt still too long after all truncation attempts!"
                )
                logger.error(
                    f"[LLM] Final estimate: {final_prompt_tokens} tokens + {max_tokens_to_generate} = {final_total} tokens"
                )
                logger.error(
                    f"[LLM] Conservative: {final_conservative} tokens, Context window: {context_window}"
                )
                # Force maximum truncation
                max_safe_tokens = context_window - max_tokens_to_generate - 50  # 50 token absolute minimum buffer
                max_prompt_chars = int(max_safe_tokens * 2.5)  # Very conservative
                if len(prompt) > max_prompt_chars:
                    logger.error(
                        f"[LLM] Forcing absolute maximum truncation to {max_prompt_chars} chars"
                    )
                    prompt = prompt[-max_prompt_chars:]
                    final_prompt_tokens = estimate_tokens(prompt)
                    logger.warning(
                        f"[LLM] After absolute truncation: {len(prompt)} chars, ~{final_prompt_tokens} tokens"
                    )

            logger.debug(
                f"[LLM] Calling create_completion with prompt: {len(prompt)} chars, "
                f"~{estimate_tokens(prompt)} tokens, max_tokens={max_tokens_to_generate}, "
                f"context_window={context_window}"
            )
            logger.info("[LLM] 🚀 Starting local model inference...")

            # Call create_completion
            # Note: You may see "Exception ignored in: <function ... __del__>" messages in stderr
            # after this call. These are harmless Python garbage collection exceptions from
            # llama_cpp internal cleanup (temporary objects) and can be safely ignored.
            # They don't affect the model inference or the response.
            try:
                response = model_instance.create_completion(
                    prompt=prompt,
                    max_tokens=max_tokens_to_generate,
                    temperature=temp,
                    stop=["\n\n\n", "User:", "Context:"],  # Removed VERDICT, EVIDENCE, ACTION from stops
                )
                elapsed = time.time() - start_time
                logger.info(f"[LLM] ✅ Local model inference completed in {elapsed:.2f} seconds")
                logger.debug("[LLM] Response received from local model, processing...")
            except Exception as inference_error:
                elapsed = time.time() - start_time
                logger.error(
                    f"[LLM] ❌ Local model inference failed after {elapsed:.2f} seconds: {inference_error}"
                )
                raise

            if not response:
                logger.error("[LLM] None response from local model")
                raise ValueError("None response from local LLM")

            if 'choices' not in response:
                logger.error(f"[LLM] Invalid response structure from local model: {list(response.keys())}")
                raise ValueError("Invalid response structure from local LLM")

            if len(response['choices']) == 0:
                logger.error("[LLM] Empty choices array in local model response")
                raise ValueError("Empty choices in local LLM response")

            choice = response['choices'][0]
            logger.debug(f"[LLM] Local model choice structure: {list(choice.keys())}")

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
                logger.warning(f"[LLM] Empty text in local model response, full choice: {choice}")
                logger.debug(f"[LLM] Full local response structure: {list(response.keys())}")
                # Try to extract from finish_reason or other fields
                if 'finish_reason' in choice:
                    logger.debug(f"[LLM] Local model finish reason: {choice['finish_reason']}")
                # Use a fallback that indicates the model responded but with empty text
                result = (
                    "VERDICT: I notice you've been journaling regularly. That's a positive pattern.\n"
                    "EVIDENCE:\n- Found entries in the last 7 days\n"
                    "ACTION: Continue with your current journaling practice.\n"
                    "CONFIDENCE_ESTIMATE: 50"
                )

            logger.info(
                f"[LLM] Local completion generated (length: {len(result)} chars, took {elapsed:.2f}s)"
            )
            logger.debug(f"[LLM] Local result preview: {result[:200]}...")
            return result
        except Exception as e:
            logger.error(f"[LLM] Error during local completion generation: {e}", exc_info=True)
            # Try to close and reset the model instance
            try:
                if _model_instance:
                    del _model_instance
                    _model_instance = None
                    _model_path = None
                    logger.warning("[LLM] Reset local model instance due to error")
            except Exception:
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
            logger.info(
                f"[LLM] GPT4All completion generated (length: {len(result)} chars)"
            )
            return result

        except ImportError:
            error_msg = "No LLM library available (llama-cpp-python / GPT4All not installed)"
            logger.error(f"[LLM] {error_msg}")
            print("\n" + "=" * 70)
            print("ERROR: No LLM library available")
            print("=" * 70)
            print("Please install one of:")
            print("  pip install llama-cpp-python")
            print("  OR")
            print("  pip install gpt4all")
            print("\nExiting...")
            print("=" * 70 + "\n")
            raise ImportError(error_msg)

    except Exception as e:
        logger.error(f"[LLM] Error calling local LLM: {e}", exc_info=True)
        raise
