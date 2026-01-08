import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

function InsightCard({ onActionCreated }) {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isPolling, setIsPolling] = useState(false);
  const pollIntervalRef = useRef(null);
  const hasStartedPollingRef = useRef(false);

  useEffect(() => {
    loadInsight();
  }, []);

  // Poll for LLM response if we got a fallback with LLM processing
  useEffect(() => {
    // Only start polling if we have a fallback and LLM is processing
    if (!insight) {
      // Clean up if insight is cleared
      if (pollIntervalRef.current) {
        console.log('[InsightCard] 🧹 Cleaning up polling (insight cleared)');
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        hasStartedPollingRef.current = false;
        setIsPolling(false);
      }
      return;
    }
    
    // If we already have LLM response, stop polling if active
    if (insight.source === 'llm') {
      if (pollIntervalRef.current) {
        console.log('[InsightCard] ✅ LLM response available, stopping polling');
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        hasStartedPollingRef.current = false;
        setIsPolling(false);
      }
      return;
    }
    
    // Start polling if we have fallback and LLM is processing, but only once
    if (insight.source === 'fallback' && insight.llm_processing && !hasStartedPollingRef.current) {
      console.log('[InsightCard] 🔄 LLM processing detected! Starting automatic polling...');
      console.log('[InsightCard] 📊 Current insight:', {
        source: insight.source,
        llm_processing: insight.llm_processing,
        verdict: insight.verdict?.substring(0, 50) + '...'
      });
      
      hasStartedPollingRef.current = true;
      setIsPolling(true);
      let pollCount = 0;
      const maxPolls = 24; // Poll for 2 minutes (24 * 5s = 120s)
      
      pollIntervalRef.current = setInterval(async () => {
        pollCount++;
        try {
          console.log(`[InsightCard] 🔍 [${pollCount}/${maxPolls}] Checking for LLM response...`);
          const response = await axios.get(`${API_BASE}/insight/on_open/`, { timeout: 10000 });
          
          const responseSource = response.data?.source;
          const responseProcessing = response.data?.llm_processing;
          
          console.log(`[InsightCard] 📥 Response received:`, {
            source: responseSource,
            llm_processing: responseProcessing,
            has_verdict: !!response.data?.verdict
          });
          
          if (response.data && responseSource === 'llm') {
            console.log('[InsightCard] ✨✨✨ LLM RESPONSE READY! ✨✨✨');
            console.log('[InsightCard] 📝 LLM Insight:', {
              verdict: response.data.verdict?.substring(0, 100) + '...',
              evidence_count: response.data.evidence?.length || 0,
              action: response.data.action?.substring(0, 50) + '...',
              confidence: response.data.confidence_estimate
            });
            console.log('[InsightCard] 🔄 Updating UI with LLM response...');
            
            // Stop polling first
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            hasStartedPollingRef.current = false;
            setIsPolling(false);
            
            // Update insight state using functional update to ensure we get the latest
            setInsight(prevInsight => {
              // Only update if we don't already have an LLM response
              if (prevInsight?.source === 'llm') {
                console.log('[InsightCard] ℹ️ Already have LLM response, skipping update');
                return prevInsight;
              }
              console.log('[InsightCard] ✅ Setting new LLM insight in state');
              return response.data;
            });
            console.log('[InsightCard] ✅ UI update triggered! Polling stopped.');
            return;
          } else if (response.data && responseSource === 'fallback' && !responseProcessing) {
            // LLM processing stopped but no result - stop polling
            console.log('[InsightCard] ⚠️ LLM processing stopped, no result available');
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            hasStartedPollingRef.current = false;
            setIsPolling(false);
            return;
          } else {
            console.log(`[InsightCard] ⏳ Still waiting... (source: ${responseSource}, processing: ${responseProcessing})`);
          }
        } catch (err) {
          console.warn('[InsightCard] ⚠️ Polling check failed:', err.response?.status || err.message);
        }
        
        // Stop after max polls
        if (pollCount >= maxPolls) {
          console.log('[InsightCard] ⏱️ Stopped polling after 2 minutes (max attempts reached)');
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          hasStartedPollingRef.current = false;
          setIsPolling(false);
        }
      }, 5000); // Poll every 5 seconds
      
      console.log('[InsightCard] ✅ Polling started! Will check every 5 seconds for LLM response.');
    } else if (insight.source === 'fallback' && !insight.llm_processing) {
      // Fallback but LLM not processing - stop any polling
      if (pollIntervalRef.current) {
        console.log('[InsightCard] ℹ️ Fallback response, LLM not processing - stopping polling');
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        hasStartedPollingRef.current = false;
        setIsPolling(false);
      }
    }
    
    // Cleanup function - only runs on unmount
    return () => {
      if (pollIntervalRef.current) {
        console.log('[InsightCard] 🧹 Component unmounting, cleaning up polling');
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        hasStartedPollingRef.current = false;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [insight?.source, insight?.llm_processing]); // Only depend on source and llm_processing to avoid unnecessary re-runs

  const loadInsight = async () => {
    try {
      console.log('[InsightCard] Loading insight...');
      setLoading(true);
      setError('');
      setIsPolling(false);
      console.log('[InsightCard] Making API call to /insight/on_open');
      const response = await axios.get(`${API_BASE}/insight/on_open/`, { timeout: 60000 });
      console.log('[InsightCard] Insight response received:', response.data);
      setInsight(response.data);
      console.log('[InsightCard] Insight loaded successfully, source:', response.data.source);
    } catch (err) {
      console.error('[InsightCard] Error loading insight:', err);
      console.error('[InsightCard] Error response:', err.response?.data);
      console.error('[InsightCard] Error status:', err.response?.status);
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

  const isLLMResponse = insight.source === 'llm';
  const isFallback = insight.source === 'fallback';
  const isProcessing = insight.llm_processing && isFallback;

  return (
    <div className="insight-card">
      <div className="insight-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h3>Today's Insight</h3>
          {isLLMResponse && (
            <span className="insight-badge llm-badge" title="Generated by AI">
              ✨ AI Insight
            </span>
          )}
          {isFallback && !isProcessing && (
            <span className="insight-badge fallback-badge" title="Quick summary">
              📊 Quick Summary
            </span>
          )}
          {isProcessing && (
            <span className="insight-badge processing-badge" title="AI is analyzing...">
              ⏳ AI Analyzing... {isPolling && '(checking...)'}
            </span>
          )}
        </div>
        <button onClick={loadInsight} className="refresh-btn" aria-label="Refresh" disabled={loading}>
          {loading ? '⟳' : '↻'}
        </button>
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

