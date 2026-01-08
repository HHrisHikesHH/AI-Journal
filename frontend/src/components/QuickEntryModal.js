import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

const ALLOWED_EMOTIONS = ["content", "anxious", "sad", "angry", "motivated", "tired", "calm", "stressed"];

function QuickEntryModal({ isOpen, onClose, onEntryCreated }) {
  const [emotions, setEmotions] = useState([]);
  const [habitsList, setHabitsList] = useState([]);
  const [configLoading, setConfigLoading] = useState(true);
  
  const [emotion, setEmotion] = useState('');
  const [showedUp, setShowedUp] = useState(false);
  const [habits, setHabits] = useState({});
  const [freeText, setFreeText] = useState('');
  const [longReflection, setLongReflection] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Fetch config from backend
  useEffect(() => {
    if (isOpen) {
      const fetchConfig = async () => {
        try {
          console.info('[QuickEntry] Fetching config...');
          const response = await axios.get(`${API_BASE}/config/`);
          const config = response.data;
          setEmotions(config.emotions || ALLOWED_EMOTIONS);
          setHabitsList(config.habits || []);
          
          // Initialize habits state
          const initialHabits = {};
          config.habits?.forEach(habit => {
            initialHabits[habit] = false;
          });
          setHabits(initialHabits);
          
          console.info('[QuickEntry] Config loaded', config);
          setConfigLoading(false);
        } catch (err) {
          console.error('Error loading config:', err);
          setEmotions(ALLOWED_EMOTIONS);
          setConfigLoading(false);
        }
      };
      fetchConfig();
    }
  }, [isOpen]);

  // Handle Ctrl+K keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (!isOpen) {
          // Open modal - this will be handled by parent
        } else {
          onClose();
        }
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Prevent background scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleHabitChange = (habit) => {
    setHabits(prev => ({
      ...prev,
      [habit]: !prev[habit]
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validate
    if (!emotion) {
      setError('Please select an emotion');
      return;
    }
    if (!freeText.trim()) {
      setError('Please enter a brief reflection');
      return;
    }
    if (freeText.length > 200) {
      setError('Brief reflection must be 200 characters or less');
      return;
    }
    
    setSubmitting(true);
    
    try {
      console.info('[QuickEntry] Submitting entry...', { emotion, showedUp, habits, freeTextLength: freeText.length });
      const entryData = {
        emotion,
        energy: 5, // Default energy for quick entry
        showed_up: showedUp,
        habits,
        goals: [],
        free_text: freeText.trim(),
        long_reflection: longReflection.trim()
      };
      
      await axios.post(`${API_BASE}/entry/`, entryData);
      
      // Reset form
      setEmotion('');
      setShowedUp(false);
      setFreeText('');
      setLongReflection('');
      const resetHabits = {};
      habitsList.forEach(habit => {
        resetHabits[habit] = false;
      });
      setHabits(resetHabits);
      
      onEntryCreated();
      onClose();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save entry');
      console.error('[QuickEntry] Submit failed', err.response?.data || err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content quick-entry-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Quick Entry</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>
        
        {configLoading ? (
          <div className="loading">Loading...</div>
        ) : (
          <form onSubmit={handleSubmit}>
            {error && <div className="error-message">{error}</div>}
            
            <div className="form-group">
              <label>How are you feeling? *</label>
              <div className="emotion-buttons">
                {emotions.map(em => (
                  <button
                    key={em}
                    type="button"
                    className={`emotion-button ${emotion === em ? 'active' : ''}`}
                    onClick={() => setEmotion(em)}
                    aria-pressed={emotion === em}
                  >
                    {em}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="form-group">
              <label>
                <input
                  type="checkbox"
                  checked={showedUp}
                  onChange={(e) => setShowedUp(e.target.checked)}
                />
                Showed up today
              </label>
            </div>
            
            <div className="form-group">
              <label>Habits</label>
              <div className="habit-checkboxes">
                {habitsList.map(habit => (
                  <label key={habit} className="habit-checkbox">
                    <input
                      type="checkbox"
                      checked={habits[habit] || false}
                      onChange={() => handleHabitChange(habit)}
                    />
                    {habit}
                  </label>
                ))}
              </div>
            </div>
            
            <div className="form-group">
              <label>
                Brief reflection (max 200 chars) *
                <span className="char-count">{freeText.length}/200</span>
              </label>
              <textarea
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                maxLength={200}
                rows={3}
                placeholder="A few words about today..."
                required
              />
            </div>
            
            <div className="form-group">
              <label>Deeper reflection (optional)</label>
              <textarea
                value={longReflection}
                onChange={(e) => setLongReflection(e.target.value)}
                rows={4}
                placeholder="Optional longer reflection..."
              />
            </div>
            
            <div className="form-actions">
              <button type="button" onClick={onClose} className="btn-secondary">
                Cancel
              </button>
              <button type="submit" disabled={submitting} className="btn-primary">
                {submitting ? 'Saving...' : 'Save Entry'}
              </button>
            </div>
            
            <div className="keyboard-hint">
              Press <kbd>Esc</kbd> to close, <kbd>Ctrl+K</kbd> to toggle
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default QuickEntryModal;

