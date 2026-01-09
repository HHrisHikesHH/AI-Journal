import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

function InsightCard() {
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isPolling, setIsPolling] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const pollIntervalRef = useRef(null);
  const hasStartedPollingRef = useRef(false);

  useEffect(() => {
    loadInsight(false); // Initial load, no force refresh
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
    
    // If we already have LLM response and not refreshing, stop polling if active
    if (insight.source === 'llm' && !isRefreshing && !insight.llm_processing) {
      if (pollIntervalRef.current) {
        console.log('[InsightCard] ✅ LLM response available, stopping polling');
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
        hasStartedPollingRef.current = false;
        setIsPolling(false);
      }
      return;
    }
    
    // Start polling if:
    // 1. We have fallback and LLM is processing, OR
    // 2. We're refreshing and LLM is processing (even if we had an LLM response before)
    const shouldPoll = (insight.source === 'fallback' || isRefreshing) && insight.llm_processing && !hasStartedPollingRef.current;
    
    if (shouldPoll) {
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
            setIsRefreshing(false); // Re-enable refresh button
            
            // Always update with new LLM response (even if we had one before - this is a refresh)
            setInsight(response.data);
            console.log('[InsightCard] ✅ UI updated with fresh LLM response! Polling stopped.');
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
  }, [insight?.source, insight?.llm_processing, isRefreshing]); // Include isRefreshing to handle refresh polling

  const loadInsight = async (forceRefresh = false) => {
    try {
      if (forceRefresh) {
        console.log('[InsightCard] 🔄 Refresh button clicked - forcing new insight generation');
        setIsRefreshing(true);
        // Keep current insight visible while generating new one
      } else {
        console.log('[InsightCard] Loading insight...');
        setLoading(true);
      }
      
      setError('');
      setIsPolling(false);
      
      const url = forceRefresh 
        ? `${API_BASE}/insight/on_open/?force_refresh=true`
        : `${API_BASE}/insight/on_open/`;
      
      console.log('[InsightCard] Making API call to', url);
      const response = await axios.get(url, { timeout: 60000 });
      console.log('[InsightCard] Insight response received:', {
        source: response.data?.source,
        llm_processing: response.data?.llm_processing,
        verdict: response.data?.verdict?.substring(0, 50) + '...'
      });
      
      // Handle refresh scenarios
      if (forceRefresh) {
        if (response.data?.source === 'llm' && !response.data?.llm_processing) {
          // Got fresh LLM response immediately (unlikely but possible)
          console.log('[InsightCard] ✅ Got fresh LLM response immediately');
          setInsight(response.data);
          setIsRefreshing(false);
        } else if (response.data?.llm_processing) {
          // LLM is generating new response - keep current insight visible and poll
          console.log('[InsightCard] ⏳ LLM is generating new response, keeping current insight visible');
          console.log('[InsightCard] ⏳ Will poll for update - current insight stays on screen');
          // Don't update insight yet - keep showing the old one
          // Mark current insight as being refreshed by updating llm_processing flag
          setInsight(prev => prev ? { ...prev, llm_processing: true } : response.data);
          // Polling will be handled by the useEffect and update when ready
        } else {
          // Got fallback without processing - shouldn't happen on refresh, but handle it
          console.log('[InsightCard] ⚠️ Got fallback on refresh, setting as new insight');
          setInsight(response.data);
          setIsRefreshing(false);
        }
      } else {
        // Normal load - update insight state
        setInsight(response.data);
        console.log('[InsightCard] Insight loaded successfully, source:', response.data.source);
      }
      
    } catch (err) {
      console.error('[InsightCard] Error loading insight:', err);
      console.error('[InsightCard] Error response:', err.response?.data);
      console.error('[InsightCard] Error status:', err.response?.status);
      setError(err.response?.data?.error || 'Unable to load insight');
      setIsRefreshing(false);
    } finally {
      if (!forceRefresh) {
        setLoading(false);
      }
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
          {isRefreshing && insight?.source === 'llm' && (
            <span className="insight-badge processing-badge" title="Generating fresh insight...">
              🔄 Refreshing...
            </span>
          )}
        </div>
        <button 
          onClick={() => loadInsight(true)} 
          className="refresh-btn" 
          aria-label="Refresh" 
          disabled={loading || isRefreshing || (insight?.llm_processing === true)}
          title={isRefreshing || insight?.llm_processing ? "Generating new insight..." : "Refresh insight"}
        >
          {(loading || isRefreshing || insight?.llm_processing) ? '⟳' : '↻'}
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
      
      
      {insight.confidence_estimate !== undefined && (
        <div className="insight-confidence">
          Confidence: {insight.confidence_estimate}%
        </div>
      )}
    </div>
  );
}

export default InsightCard;

