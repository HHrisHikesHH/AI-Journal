"""
Django app configuration for API app.
Loads models at startup in the main thread.
"""
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        """Called when Django starts. Load models in main thread here."""
        import threading
        import traceback
        
        # Only load in main thread (not in worker threads)
        current_thread = threading.current_thread()
        is_main_thread = current_thread is threading.main_thread()
        
        logger.info(f"[AppConfig] ready() called. Thread: {current_thread.name}, Is main: {is_main_thread}")
        
        if is_main_thread:
            logger.info("[AppConfig] Loading models at startup in main thread...")
            
            # Load LLM model in main thread
            try:
                from .llm_adapter import ensure_model_loaded
                logger.info("[AppConfig] Calling ensure_model_loaded()...")
                if ensure_model_loaded():
                    logger.info("[AppConfig] ✅ LLM model loaded successfully at startup")
                else:
                    logger.warning("[AppConfig] ⚠️ LLM model failed to load at startup (will try again on first use)")
            except Exception as e:
                logger.error(f"[AppConfig] Error loading LLM model: {e}")
                logger.error(f"[AppConfig] Traceback: {traceback.format_exc()}")
            
            # Try to load embedding model (but don't fail if it doesn't work)
            # The RAG system will handle this gracefully
            try:
                from .rag_system import RAGSystem
                # Just initialize to trigger loading, but don't fail if it errors
                try:
                    rag = RAGSystem()
                    logger.info("[AppConfig] ✅ RAG system initialized successfully")
                except Exception as rag_error:
                    error_msg = str(rag_error)
                    if 'meta tensor' in error_msg.lower():
                        logger.warning("[AppConfig] ⚠️ RAG system has meta tensor issue (will use fallback)")
                    else:
                        logger.warning(f"[AppConfig] ⚠️ RAG system initialization failed: {rag_error}")
            except Exception as e:
                logger.warning(f"[AppConfig] ⚠️ Could not initialize RAG system: {e}")
        else:
            logger.debug("[AppConfig] Not in main thread, skipping model loading")

