import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

const EMOTIONS = [
  'content', 'anxious', 'sad', 'angry', 'motivated', 'tired', 'calm', 'stressed'
];

const HABITS = ['exercise', 'deep_work', 'meditation', 'reading', 'writing', 'wake_up_on_time', 'sleep_on_time'];

function EntryForm({ onEntryCreated }) {
  const [emotion, setEmotion] = useState('');
  const [energy, setEnergy] = useState(5);
  const [showedUp, setShowedUp] = useState(false);
  const [habits, setHabits] = useState({
    exercise: false,
    deep_work: false,
    sleep_on_time: false
  });
  const [freeText, setFreeText] = useState('');
  const [longReflection, setLongReflection] = useState('');
  const [goals, setGoals] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleHabitChange = (habit) => {
    setHabits(prev => ({
      ...prev,
      [habit]: !prev[habit]
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!emotion) {
      setError('Please select an emotion');
      return;
    }
    
    if (freeText.length > 200) {
      setError('Free text must be 200 characters or less');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      const entryData = {
        emotion,
        energy: parseInt(energy),
        showed_up: showedUp,
        habits,
        goals,
        free_text: freeText,
        long_reflection: longReflection
      };

      await axios.post(`${API_BASE}/entry/`, entryData);
      
      // Reset form
      setEmotion('');
      setEnergy(5);
      setShowedUp(false);
      setHabits({ exercise: false, deep_work: false, sleep_on_time: false });
      setFreeText('');
      setLongReflection('');
      setGoals([]);
      
      onEntryCreated();
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create entry');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card">
      <h2>Today's Reflection</h2>
      
      {error && <div className="error">{error}</div>}
      
      <form onSubmit={handleSubmit}>
        <div>
          <label>How are you feeling in this moment? *</label>
          <div className="emotion-grid">
            {EMOTIONS.map(emo => (
              <button
                key={emo}
                type="button"
                className={`emotion-button ${emotion === emo ? 'selected' : ''}`}
                onClick={() => setEmotion(emo)}
              >
                {emo}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginTop: '28px' }}>
          <label>
            Energy Level: {energy}/10
          </label>
          <input
            type="range"
            min="1"
            max="10"
            value={energy}
            onChange={(e) => setEnergy(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>

        <div style={{ marginTop: '28px' }}>
          <div className="toggle-item">
            <input
              type="checkbox"
              id="showed_up"
              checked={showedUp}
              onChange={(e) => setShowedUp(e.target.checked)}
            />
            <label htmlFor="showed_up" style={{ margin: 0, cursor: 'pointer' }}>
              Did I show up even when I didn't feel like it?
            </label>
          </div>
        </div>

        <div style={{ marginTop: '28px' }}>
          <label>Habits & Practices</label>
          <div className="toggle-group">
            {HABITS.map(habit => (
              <div key={habit} className="toggle-item">
                <input
                  type="checkbox"
                  id={habit}
                  checked={habits[habit]}
                  onChange={() => handleHabitChange(habit)}
                />
                <label htmlFor={habit} style={{ margin: 0, cursor: 'pointer' }}>
                  {habit.replace('_', ' ')}
                </label>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginTop: '28px' }}>
          <label>
            A few words about today (max 200 chars) *
          </label>
          <textarea
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            maxLength={200}
            rows={3}
            required
            placeholder="What's present for you today?"
          />
          <div className={`char-count ${freeText.length > 180 ? 'warning' : ''}`}>
            {freeText.length}/200
          </div>
        </div>

        <div style={{ marginTop: '28px' }}>
          <label>
            Deeper reflection (optional)
          </label>
          <textarea
            value={longReflection}
            onChange={(e) => setLongReflection(e.target.value)}
            rows={6}
            placeholder="Take your time... what patterns do you notice? What feels important?"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || !emotion || !freeText}
          style={{ marginTop: '32px', width: '100%', padding: '16px' }}
        >
          {submitting ? 'Saving...' : 'Save Reflection'}
        </button>
      </form>
    </div>
  );
}

export default EntryForm;

