import React, { useState } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

const SUGGESTED_QUESTIONS = [
  "What drains my energy?",
  "Am I avoiding something important?",
  "Am I lying to myself?",
  "What patterns repeat before burnout?",
  "Am I moving closer to my long-term goals?",
  "Am I being disciplined?",
  "Am I on the right path?"
];

function QueryInterface() {
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError('');
    setAnswer(null);

    try {
      const response = await axios.post(`${API_BASE}/query/`, { query });
      setAnswer(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to get response');
    } finally {
      setLoading(false);
    }
  };

  const handleSuggestedQuestion = (question) => {
    setQuery(question);
  };

  return (
    <div>
      <div className="card">
        <h2>Ask Your Coach</h2>
        <p style={{ color: '#7f8c8d', marginBottom: '20px' }}>
          Ask questions about your patterns, habits, and progress. The coach will respond based on your journal entries.
        </p>

        <div style={{ marginBottom: '20px' }}>
          <label>Suggested Questions:</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '8px' }}>
            {SUGGESTED_QUESTIONS.map(q => (
              <button
                key={q}
                type="button"
                onClick={() => handleSuggestedQuestion(q)}
                style={{
                  padding: '6px 12px',
                  fontSize: '12px',
                  background: '#ecf0f1',
                  border: '1px solid #bdc3c7',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question about your journal entries..."
            rows={4}
            style={{ width: '100%', marginBottom: '12px' }}
          />
          <button type="submit" disabled={loading || !query.trim()}>
            {loading ? 'Asking...' : 'Ask Coach'}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {loading && <div className="loading">Thinking...</div>}

        {answer && (
          <div style={{ marginTop: '24px' }}>
            <div className="answer-box">
              {answer.answer}
            </div>

            {answer.sources && answer.sources.length > 0 && (
              <div className="sources">
                <strong>Sources:</strong>
                {answer.sources.map((source, idx) => (
                  <div key={idx} className="source-item">
                    {source.date} - {source.emotion} ({source.filename})
                  </div>
                ))}
              </div>
            )}

            {answer.confidence_estimate !== undefined && (
              <div style={{ marginTop: '12px', fontSize: '12px', color: '#7f8c8d' }}>
                Confidence: {(answer.confidence_estimate * 100).toFixed(0)}%
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default QueryInterface;

