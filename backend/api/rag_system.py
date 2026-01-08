import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from django.conf import settings
from sentence_transformers import SentenceTransformer
import faiss
from .llm_adapter import call_local_llm

class RAGSystem:
    """RAG system for querying journal entries."""
    
    def __init__(self):
        self.embedding_model = None
        self.index = None
        self.entries = []
        self._load_embedding_model()
        self._load_or_create_index()
    
    def _load_embedding_model(self):
        """Load the sentence transformer model."""
        try:
            model_name = self._get_config()['models']['embedding_model']
            self.embedding_model = SentenceTransformer(model_name)
            print(f"Loaded embedding model: {model_name}")
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            raise
    
    def _get_config(self):
        """Load config.json."""
        with open(settings.CONFIG_FILE, 'r') as f:
            return json.load(f)
    
    def _load_or_create_index(self):
        """Load existing index or create new one."""
        index_path = settings.EMBEDDINGS_DIR / 'faiss_index.bin'
        entries_path = settings.EMBEDDINGS_DIR / 'entries_metadata.json'
        
        if index_path.exists() and entries_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))
                with open(entries_path, 'r') as f:
                    self.entries = json.load(f)
                print(f"Loaded existing index with {len(self.entries)} entries")
            except Exception as e:
                print(f"Error loading index: {e}, rebuilding...")
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
    
    def rebuild_index(self):
        """Rebuild the FAISS index from all entries."""
        print("Rebuilding index...")
        self.entries = []
        texts = []
        
        # Load all entries
        for filepath in sorted(settings.ENTRIES_DIR.glob('*.json')):
            try:
                with open(filepath, 'r') as f:
                    entry = json.load(f)
                    self.entries.append(entry)
                    texts.append(self._get_entry_text(entry))
            except Exception as e:
                print(f"Error loading entry {filepath}: {e}")
                continue
        
        if not texts:
            print("No entries found, creating empty index")
            # Create empty index with correct dimension
            dimension = 384  # all-MiniLM-L6-v2 dimension
            self.index = faiss.IndexFlatL2(dimension)
            self._save_index()
            return
        
        # Generate embeddings
        print(f"Generating embeddings for {len(texts)} entries...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        embeddings = np.array(embeddings).astype('float32')
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings)
        
        self._save_index()
        print(f"Index rebuilt with {len(self.entries)} entries")
    
    def _save_index(self):
        """Save index and metadata."""
        index_path = settings.EMBEDDINGS_DIR / 'faiss_index.bin'
        entries_path = settings.EMBEDDINGS_DIR / 'entries_metadata.json'
        
        faiss.write_index(self.index, str(index_path))
        with open(entries_path, 'w') as f:
            json.dump(self.entries, f, indent=2)
    
    def add_entry(self, entry: Dict[str, Any]):
        """Add a single entry to the index incrementally."""
        text = self._get_entry_text(entry)
        embedding = self.embedding_model.encode([text])
        embedding = np.array(embedding).astype('float32')
        
        if self.index is None:
            dimension = embedding.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
        
        self.index.add(embedding)
        self.entries.append(entry)
        self._save_index()
    
    def query(self, query_text: str, k: int = 5) -> Dict[str, Any]:
        """Query the RAG system."""
        if self.index is None or len(self.entries) == 0:
            return {
                'answer': 'No entries available yet. Please create some journal entries first.',
                'sources': [],
                'confidence_estimate': 0.0
            }
        
        # Embed query
        try:
            query_embedding = self.embedding_model.encode([query_text])
            query_embedding = np.array(query_embedding).astype('float32')
        except Exception as e:
            import traceback
            print(f"Embedding error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return {
                'answer': 'Error processing query. Please try again.',
                'sources': [],
                'confidence_estimate': 0.0,
                'error': str(e)
            }
        
        # Search
        try:
            k = min(k, len(self.entries))
            if k == 0:
                return {
                    'answer': 'No entries available yet. Please create some journal entries first.',
                    'sources': [],
                    'confidence_estimate': 0.0
                }
            distances, indices = self.index.search(query_embedding, k)
            
            # Get relevant entries with bounds checking
            relevant_entries = []
            for idx in indices[0]:
                if 0 <= idx < len(self.entries):
                    relevant_entries.append(self.entries[idx])
        except Exception as e:
            import traceback
            print(f"FAISS search error: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return {
                'answer': 'Error searching entries. Please try again.',
                'sources': [],
                'confidence_estimate': 0.0,
                'error': str(e)
            }
        
        # Build context for LLM
        context_parts = []
        for i, entry in enumerate(relevant_entries):
            entry_date = entry.get('timestamp', '')[:10]  # YYYY-MM-DD
            filename = f"{entry.get('timestamp', '').replace(':', '-').split('.')[0]}Z__{entry.get('id', '')}.json"
            context_parts.append(f"Entry from {entry_date} ({filename}):")
            context_parts.append(f"  Emotion: {entry.get('emotion', 'N/A')}")
            context_parts.append(f"  Energy: {entry.get('energy', 'N/A')}")
            context_parts.append(f"  Showed up: {entry.get('showed_up', False)}")
            if entry.get('free_text'):
                context_parts.append(f"  Note: {entry.get('free_text')}")
            if entry.get('long_reflection'):
                context_parts.append(f"  Reflection: {entry.get('long_reflection')[:200]}...")
        
        context = '\n'.join(context_parts)
        
        # Generate answer using LLM
        try:
            config = self._get_config()
            prompt = self._build_query_prompt(query_text, context, config)
            
            try:
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
        
        # Build sources
        sources = []
        for entry in relevant_entries:
            entry_date = entry.get('timestamp', '')[:10]
            sources.append({
                'date': entry_date,
                'emotion': entry.get('emotion', ''),
                'filename': f"{entry.get('timestamp', '').replace(':', '-').split('.')[0]}Z__{entry.get('id', '')}.json"
            })
        
        confidence = min(len(relevant_entries) / k, 1.0)
        
        return {
            'answer': self._format_answer(answer),
            'sources': sources,
            'confidence_estimate': confidence,
            'structured': answer
        }
    
    def _build_query_prompt(self, query: str, context: str, config: Dict) -> str:
        """Build the prompt for query answering."""
        # Load prompt template
        prompt_path = Path(__file__).parent.parent / 'prompts' / 'query_prompt.txt'
        try:
            with open(prompt_path, 'r') as f:
                template = f.read()
            return template.format(context=context, query=query)
        except Exception:
            # Fallback to inline prompt
            system_prompt = """You are a gentle, supportive personal coach. Your role is to help someone understand their patterns and make small, sustainable changes. You must:
- Never shame or judge
- Present evidence neutrally
- Give ONE small, actionable suggestion
- Be indirect and gentle in your tone
- Only use information from the provided context
- If data is insufficient, say so clearly

Your response must follow this structure:
VERDICT: [One sentence neutral observation]
EVIDENCE:
- [Evidence item 1 with source filename]
- [Evidence item 2 with source filename]
- [Evidence item 3 with source filename]
ACTION: [One small, specific action]
CONFIDENCE_ESTIMATE: [Integer 0-100]

Use only the CONTEXT provided below. Cite filenames. One-line verdict. Two evidence bullets with filenames. One micro-action. Confidence_estimate."""
        
            user_prompt = f"""Context from journal entries:
{context}

User question: {query}

Provide a gentle, supportive response based ONLY on the context above. If the context doesn't contain enough information, state that clearly."""
        
            return f"{system_prompt}\n\n{user_prompt}"
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
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

