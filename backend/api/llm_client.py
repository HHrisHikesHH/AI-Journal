import json
import os
from pathlib import Path
from django.conf import settings

class LLMClient:
    """Client for local LLM inference."""
    
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the local LLM model."""
        try:
            config = self._get_config()
            model_path = config['models']['llm_model_path']
            # PROJECT_ROOT is defined in settings.py
            from pathlib import Path
            project_root = Path(settings.CONFIG_FILE).parent
            full_path = project_root / model_path
            
            if not full_path.exists():
                print(f"Warning: Model file not found at {full_path}")
                print("Falling back to mock responses. Please download a model.")
                self.model = None
                return
            
            # Try llama-cpp-python first
            try:
                from llama_cpp import Llama
                self.model = Llama(
                    model_path=str(full_path),
                    n_ctx=2048,
                    verbose=False
                )
                print(f"Loaded LLM model: {model_path}")
            except ImportError:
                print("llama-cpp-python not available, trying gpt4all...")
                try:
                    from gpt4all import GPT4All
                    self.model = GPT4All(model_name=os.path.basename(full_path), model_path=str(full_path.parent))
                    print(f"Loaded GPT4All model: {model_path}")
                except ImportError:
                    print("Neither llama-cpp-python nor gpt4all available. Using mock responses.")
                    self.model = None
        except Exception as e:
            print(f"Error loading LLM: {e}")
            self.model = None
    
    def _get_config(self):
        """Load config.json."""
        with open(settings.CONFIG_FILE, 'r') as f:
            return json.load(f)
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.2) -> str:
        """Generate text from prompt."""
        if self.model is None:
            return self._mock_response(prompt)
        
        config = self._get_config()
        max_tokens = config['models'].get('llm_max_tokens', max_tokens)
        temperature = config['models'].get('llm_temperature', temperature)
        
        try:
            # Try llama-cpp-python interface
            if hasattr(self.model, 'create_completion'):
                response = self.model.create_completion(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=["\n\n\n", "User:", "Context:"]
                )
                return response['choices'][0]['text'].strip()
            # Try gpt4all interface
            elif hasattr(self.model, 'generate'):
                return self.model.generate(prompt, max_tokens=max_tokens, temp=temperature)
            else:
                return self._mock_response(prompt)
        except Exception as e:
            print(f"LLM generation error: {e}")
            return self._mock_response(prompt)
    
    def _mock_response(self, prompt: str) -> str:
        """Generate a mock response when LLM is not available."""
        return """REALITY_CHECK: Based on your journal entries, I notice some patterns emerging.
EVIDENCE:
- Your energy levels have varied over the past week
- You've been consistent with some habits
- Your reflections show thoughtful self-awareness
ACTION: Consider setting a small daily reminder to check in with yourself.
SIGN_OFF: You're doing the work, and that matters."""

