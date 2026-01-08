"""
LLM adapter for local inference.
Supports llama-cpp-python and gpt4all fallback.
"""
import os
import sys
from pathlib import Path
from django.conf import settings

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
    # Get model path from config
    try:
        import json
        with open(settings.CONFIG_FILE, 'r') as f:
            config = json.load(f)
        model_path = config['models'].get('llm_model_path', 'local/models/llama_model.bin')
    except Exception:
        model_path = 'local/models/llama_model.bin'
    
    # Resolve full path
    project_root = Path(settings.CONFIG_FILE).parent
    full_model_path = project_root / model_path
    
    # Check if model exists
    if not full_model_path.exists():
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
        sys.exit(1)
    
    # Try llama-cpp-python first
    try:
        from llama_cpp import Llama
        import warnings
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        
        model = Llama(
            model_path=str(full_model_path),
            n_ctx=2048,
            verbose=False
        )
        
        response = model.create_completion(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temp,
            stop=["\n\n\n", "User:", "Context:", "VERDICT:", "EVIDENCE:", "ACTION:"]
        )
        return response['choices'][0]['text'].strip()
    
    except ImportError:
        # Fallback to GPT4All
        try:
            from gpt4all import GPT4All
            
            model = GPT4All(
                model_name=os.path.basename(full_model_path),
                model_path=str(full_model_path.parent)
            )
            return model.generate(prompt, max_tokens=max_tokens, temp=temp)
        
        except ImportError:
            print("\n" + "="*70)
            print("ERROR: No LLM library available")
            print("="*70)
            print("Please install one of:")
            print("  pip install llama-cpp-python")
            print("  OR")
            print("  pip install gpt4all")
            print("\nExiting...")
            print("="*70 + "\n")
            sys.exit(1)
    
    except Exception as e:
        print(f"Error calling LLM: {e}")
        raise

