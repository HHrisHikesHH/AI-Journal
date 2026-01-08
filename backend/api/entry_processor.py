import json
from typing import Dict, Any
from textblob import TextBlob

class EntryProcessor:
    """Process entries to derive additional fields."""
    
    def process_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Process an entry and add derived fields."""
        derived = {
            'sentiment': self._get_sentiment(entry),
            'themes': self._extract_themes(entry),
            'flags': self._detect_flags(entry),
            'summary': self._generate_summary(entry)
        }
        
        entry['derived'] = derived
        return entry
    
    def _get_sentiment(self, entry: Dict[str, Any]) -> Dict[str, float]:
        """Get sentiment polarity from text."""
        text = f"{entry.get('free_text', '')} {entry.get('long_reflection', '')}"
        if not text.strip():
            return {'polarity': 0.0, 'subjectivity': 0.0}
        
        try:
            blob = TextBlob(text)
            return {
                'polarity': float(blob.sentiment.polarity),
                'subjectivity': float(blob.sentiment.subjectivity)
            }
        except Exception:
            return {'polarity': 0.0, 'subjectivity': 0.0}
    
    def _extract_themes(self, entry: Dict[str, Any]) -> list:
        """Extract top themes using simple keyword matching."""
        text = f"{entry.get('free_text', '')} {entry.get('long_reflection', '')}".lower()
        
        theme_keywords = {
            'work': ['work', 'project', 'meeting', 'deadline', 'task'],
            'health': ['exercise', 'sleep', 'energy', 'tired', 'rest'],
            'relationships': ['friend', 'family', 'partner', 'talk', 'connect'],
            'growth': ['learn', 'read', 'practice', 'improve', 'skill'],
            'stress': ['stress', 'anxious', 'worried', 'pressure', 'overwhelm'],
            'gratitude': ['grateful', 'thankful', 'appreciate', 'blessed', 'lucky']
        }
        
        theme_scores = {}
        for theme, keywords in theme_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                theme_scores[theme] = score
        
        # Return top 3 themes (top_themes field)
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        return [theme for theme, _ in sorted_themes[:3]]
    
    def _detect_flags(self, entry: Dict[str, Any]) -> list:
        """Detect patterns that might be flags."""
        flags = []
        
        text = entry.get('free_text', '').lower() + ' ' + entry.get('long_reflection', '').lower()
        emotion = entry.get('emotion', '').lower()
        energy = entry.get('energy', 5)
        
        # Evening procrastination (check for keywords in text)
        if ('procrastinat' in text or 'late night' in text) and energy < 4:
            flags.append('evening_procrastination')
        
        # Low energy pattern
        if energy < 3:
            flags.append('low_energy')
        
        # High stress
        if emotion in ['stressed', 'anxious', 'angry'] and energy < 5:
            flags.append('high_stress')
        
        # Consistency concern
        if not entry.get('showed_up', False) and energy < 5:
            flags.append('consistency_concern')
        
        return flags
    
    def _generate_summary(self, entry: Dict[str, Any]) -> str:
        """Generate a one-sentence summary."""
        emotion = entry.get('emotion', 'neutral')
        energy = entry.get('energy', 5)
        showed_up = entry.get('showed_up', False)
        free_text = entry.get('free_text', '')
        
        parts = []
        parts.append(f"Felt {emotion}")
        parts.append(f"energy level {energy}/10")
        
        if showed_up:
            parts.append("showed up despite challenges")
        else:
            parts.append("struggled to show up")
        
        if free_text:
            # Use first 50 chars of free_text
            parts.append(f"- {free_text[:50]}...")
        
        return " ".join(parts)

