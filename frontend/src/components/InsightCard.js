import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

function InsightCard({ onActionCreated }) {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadInsight();
  }, []);

  const loadInsight = async () => {
    try {
      setLoading(true);
      setError('');
      const response = await axios.get(`${API_BASE}/insight/on_open`);
      setInsight(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Unable to load insight');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAction = async () => {
    if (!insight?.action) return;
    
    try {
      await axios.post(`${API_BASE}/action/`, {
        text: insight.action,
        source_query: 'Daily insight'
      });
      if (onActionCreated) {
        onActionCreated();
      }
      alert('Action item created!');
    } catch (err) {
      console.error('Error creating action:', err);
    }
  };

  if (loading) {
    return (
      <div className="insight-card">
        <div className="loading">Loading insight...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="insight-card">
        <div className="error-message">{error}</div>
      </div>
    );
  }

  if (!insight) {
    return null;
  }

  return (
    <div className="insight-card">
      <div className="insight-header">
        <h3>Today's Insight</h3>
        <button onClick={loadInsight} className="refresh-btn" aria-label="Refresh">↻</button>
      </div>
      
      {insight.verdict && (
        <div className="insight-verdict">
          {insight.verdict}
        </div>
      )}
      
      {insight.evidence && insight.evidence.length > 0 && (
        <div className="insight-evidence">
          <strong>Evidence:</strong>
          <ul>
            {insight.evidence.map((ev, idx) => (
              <li key={idx}>{ev}</li>
            ))}
          </ul>
        </div>
      )}
      
      {insight.action && (
        <div className="insight-action">
          <strong>Suggested Action:</strong>
          <p>{insight.action}</p>
          <button onClick={handleCreateAction} className="btn-small">
            Create Action Item
          </button>
        </div>
      )}
      
      {insight.confidence_estimate !== undefined && (
        <div className="insight-confidence">
          Confidence: {insight.confidence_estimate}%
        </div>
      )}
    </div>
  );
}

export default InsightCard;

