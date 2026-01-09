/**
 * Config cache utility using sessionStorage
 * Fetches config once per session and caches it
 */

import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';
const CONFIG_CACHE_KEY = 'journal_app_config';
const CONFIG_CACHE_TIMESTAMP_KEY = 'journal_app_config_timestamp';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

/**
 * Get config from cache or fetch from API
 * @returns {Promise<Object>} Config object with emotions, habits, reflection_questions, goals
 */
export const getConfig = async () => {
  try {
    // Check sessionStorage first
    const cachedConfig = sessionStorage.getItem(CONFIG_CACHE_KEY);
    const cachedTimestamp = sessionStorage.getItem(CONFIG_CACHE_TIMESTAMP_KEY);
    
    if (cachedConfig && cachedTimestamp) {
      const age = Date.now() - parseInt(cachedTimestamp, 10);
      
      // Use cached config if it's less than 5 minutes old
      if (age < CACHE_DURATION) {
        console.log('[ConfigCache] Using cached config from sessionStorage');
        return JSON.parse(cachedConfig);
      } else {
        console.log('[ConfigCache] Cache expired, fetching fresh config');
        sessionStorage.removeItem(CONFIG_CACHE_KEY);
        sessionStorage.removeItem(CONFIG_CACHE_TIMESTAMP_KEY);
      }
    }
    
    // Fetch from API
    console.log('[ConfigCache] Fetching config from API...');
    const response = await axios.get(`${API_BASE}/config/`);
    const config = response.data;
    
    // Store in sessionStorage
    sessionStorage.setItem(CONFIG_CACHE_KEY, JSON.stringify(config));
    sessionStorage.setItem(CONFIG_CACHE_TIMESTAMP_KEY, Date.now().toString());
    
    console.log('[ConfigCache] Config cached in sessionStorage');
    return config;
    
  } catch (error) {
    console.error('[ConfigCache] Error fetching config:', error);
    
    // Try to return cached config even if expired as fallback
    const cachedConfig = sessionStorage.getItem(CONFIG_CACHE_KEY);
    if (cachedConfig) {
      console.log('[ConfigCache] Using expired cache as fallback');
      return JSON.parse(cachedConfig);
    }
    
    // Return empty config if all else fails
    return {
      emotions: [],
      habits: [],
      reflection_questions: [],
      goals: []
    };
  }
};

/**
 * Clear config cache (useful for testing or forced refresh)
 */
export const clearConfigCache = () => {
  sessionStorage.removeItem(CONFIG_CACHE_KEY);
  sessionStorage.removeItem(CONFIG_CACHE_TIMESTAMP_KEY);
  console.log('[ConfigCache] Cache cleared');
};

// Note: React hook removed - use getConfig() directly in useEffect for simplicity

