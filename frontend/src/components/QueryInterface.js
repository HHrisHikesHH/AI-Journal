import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getConfig } from '../utils/configCache';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

function QueryInterface() {
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const [configLoading, setConfigLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Fetch config from cache or API
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setConfigLoading(true);
        const config = await getConfig();
        setSuggestedQuestions(config.reflection_questions || []);
        setConfigLoading(false);
      } catch (err) {
        console.error('Error loading config:', err);
        setConfigLoading(false);
      }
    };
    fetchConfig();
  }, []);

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
    <div className="card">
      <h2>Seek Guidance</h2>
      <p style={{ color: 'var(--sage-600)', marginBottom: '28px', fontStyle: 'italic', fontWeight: 300, lineHeight: '1.8' }}>
        Ask what you need to know. Your reflections will guide the response.
      </p>

      {suggestedQuestions.length > 0 && (
        <div style={{ marginBottom: '28px' }}>
          <label>Suggested Questions:</label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginTop: '12px' }}>
            {suggestedQuestions.map(q => (
            <button
              key={q}
              type="button"
              onClick={() => handleSuggestedQuestion(q)}
              className="emotion-button"
              style={{ fontSize: '13px', padding: '10px 16px' }}
            >
              {q}
            </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '20px' }}>
          <label>Your Question</label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What would you like to explore?"
            rows={4}
          />
        </div>
        <button type="submit" disabled={loading || !query.trim()} style={{ width: '100%' }}>
          {loading ? 'Reflecting...' : 'Seek Guidance'}
        </button>
      </form>

      {error && <div className="error" style={{ marginTop: '24px' }}>{error}</div>}

      {loading && <div className="loading">Reflecting...</div>}

      {answer && (
        <div style={{ marginTop: '28px' }}>
          <div className="answer-box">
            {answer.answer}
          </div>

          {answer.sources && answer.sources.length > 0 && (
            <div className="sources">
              <strong style={{ color: 'var(--sage-700)', fontWeight: 400 }}>Sources:</strong>
              {answer.sources.map((source, idx) => (
                <div key={idx} className="source-item">
                  {source.date} - {source.emotion} ({source.filename})
                </div>
              ))}
            </div>
          )}

          {answer.confidence_estimate !== undefined && (
            <div style={{ marginTop: '16px', fontSize: '13px', color: 'var(--sage-500)', fontStyle: 'italic', fontWeight: 300 }}>
              Confidence: {(answer.confidence_estimate * 100).toFixed(0)}%
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default QueryInterface;

