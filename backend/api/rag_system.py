import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from django.conf import settings
from sentence_transformers import SentenceTransformer
import faiss
from .llm_client import LLMClient

class RAGSystem:
    """RAG system for querying journal entries."""
    
    def __init__(self):
        self.embedding_model = None
        self.index = None
        self.entries = []
        self.llm_client = LLMClient()
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
        query_embedding = self.embedding_model.encode([query_text])
        query_embedding = np.array(query_embedding).astype('float32')
        
        # Search
        k = min(k, len(self.entries))
        distances, indices = self.index.search(query_embedding, k)
        
        # Get relevant entries
        relevant_entries = [self.entries[i] for i in indices[0]]
        
        # Build context for LLM
        context_parts = []
        for i, entry in enumerate(relevant_entries):
            entry_date = entry.get('timestamp', '')[:10]  # YYYY-MM-DD
            context_parts.append(f"Entry from {entry_date}:")
            context_parts.append(f"  Emotion: {entry.get('emotion', 'N/A')}")
            context_parts.append(f"  Energy: {entry.get('energy', 'N/A')}")
            context_parts.append(f"  Showed up: {entry.get('showed_up', False)}")
            if entry.get('free_text'):
                context_parts.append(f"  Note: {entry.get('free_text')}")
            if entry.get('long_reflection'):
                context_parts.append(f"  Reflection: {entry.get('long_reflection')[:200]}...")
        
        context = '\n'.join(context_parts)
        
        # Generate answer using LLM
        config = self._get_config()
        prompt = self._build_query_prompt(query_text, context, config)
        
        try:
            llm_response = self.llm_client.generate(prompt)
            answer = self._parse_llm_response(llm_response)
        except Exception as e:
            print(f"LLM error: {e}")
            answer = {
                'reality_check': 'Unable to generate response at this time.',
                'evidence': [],
                'action': 'Please try again later.',
                'sign_off': 'Take care.'
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
        system_prompt = """You are a gentle, supportive personal coach. Your role is to help someone understand their patterns and make small, sustainable changes. You must:
- Never shame or judge
- Present evidence neutrally
- Give ONE small, actionable suggestion
- Be indirect and gentle in your tone
- Only use information from the provided context
- If data is insufficient, say so clearly

Your response must follow this structure:
REALITY_CHECK: [One sentence neutral observation]
EVIDENCE:
- [Evidence item 1 with source date]
- [Evidence item 2 with source date]
- [Evidence item 3 with source date]
ACTION: [One small, specific action]
SIGN_OFF: [Gentle closing phrase]"""
        
        user_prompt = f"""Context from journal entries:
{context}

User question: {query}

Provide a gentle, supportive response based ONLY on the context above. If the context doesn't contain enough information, state that clearly."""
        
        return f"{system_prompt}\n\n{user_prompt}"
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        result = {
            'reality_check': '',
            'evidence': [],
            'action': '',
            'sign_off': ''
        }
        
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('REALITY_CHECK:'):
                result['reality_check'] = line.replace('REALITY_CHECK:', '').strip()
            elif line.startswith('EVIDENCE:'):
                current_section = 'evidence'
            elif line.startswith('ACTION:'):
                result['action'] = line.replace('ACTION:', '').strip()
                current_section = None
            elif line.startswith('SIGN_OFF:'):
                result['sign_off'] = line.replace('SIGN_OFF:', '').strip()
                current_section = None
            elif current_section == 'evidence' and line.startswith('-'):
                result['evidence'].append(line[1:].strip())
        
        # Fallback if parsing fails
        if not result['reality_check']:
            result['reality_check'] = response[:200]
        
        return result
    
    def _format_answer(self, answer: Dict[str, Any]) -> str:
        """Format structured answer as readable text."""
        parts = []
        if answer.get('reality_check'):
            parts.append(answer['reality_check'])
        if answer.get('evidence'):
            parts.append('\nEvidence:')
            for ev in answer['evidence']:
                parts.append(f"  • {ev}")
        if answer.get('action'):
            parts.append(f"\nSuggested action: {answer['action']}")
        if answer.get('sign_off'):
            parts.append(f"\n{answer['sign_off']}")
        
        return '\n'.join(parts) if parts else "Unable to generate response."

