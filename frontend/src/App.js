import React, { useState, useEffect } from 'react';
import axios from 'axios';
import EntryForm from './components/EntryForm';
import HistoryView from './components/HistoryView';
import QueryInterface from './components/QueryInterface';
import QuickEntryModal from './components/QuickEntryModal';
import InsightCard from './components/InsightCard';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

function App() {
  const [activeTab, setActiveTab] = useState('entry');
  const [entries, setEntries] = useState([]);
  // const [loading, setLoading] = useState(false);
  const [quickEntryOpen, setQuickEntryOpen] = useState(false);

  useEffect(() => {
    loadEntries();
  }, []);

  // Handle Ctrl+K for quick entry
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setQuickEntryOpen(prev => !prev);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const loadEntries = async () => {
    try {
      const response = await axios.get(`${API_BASE}/entries/?days=30`);
      setEntries(response.data.entries || []);
    } catch (error) {
      console.error('Error loading entries:', error);
    }
  };

  const handleEntryCreated = () => {
    loadEntries();
    setActiveTab('history');
    setQuickEntryOpen(false);
  };

  return (
    <div className="App">
      <div className="container">
        <div className="app-header">
          <h1>Personal Journal</h1>
          <button 
            className="quick-entry-btn"
            onClick={() => setQuickEntryOpen(true)}
            title="Quick Entry (Ctrl+K)"
          >
            Quick Entry <kbd>Ctrl+K</kbd>
          </button>
        </div>
        
        {/* Show insight card on app open */}
        <InsightCard onActionCreated={loadEntries} />
        
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'entry' ? 'active' : ''}`}
            onClick={() => setActiveTab('entry')}
          >
            Reflect
          </button>
          <button
            className={`tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            Insights
          </button>
          <button
            className={`tab ${activeTab === 'query' ? 'active' : ''}`}
            onClick={() => setActiveTab('query')}
          >
            Guidance
          </button>
        </div>

        {activeTab === 'entry' && (
          <EntryForm onEntryCreated={handleEntryCreated} />
        )}
        
        {activeTab === 'history' && (
          <HistoryView entries={entries} onRefresh={loadEntries} />
        )}
        
        {activeTab === 'query' && (
          <QueryInterface />
        )}
      </div>
      
      <QuickEntryModal
        isOpen={quickEntryOpen}
        onClose={() => setQuickEntryOpen(false)}
        onEntryCreated={handleEntryCreated}
      />
    </div>
  );
}

export default App;

