import React, { useState, useEffect } from 'react';
import axios from 'axios';
import EntryForm from './components/EntryForm';
import HistoryView from './components/HistoryView';
import QueryInterface from './components/QueryInterface';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

function App() {
  const [activeTab, setActiveTab] = useState('entry');
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadEntries();
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
  };

  return (
    <div className="App">
      <div className="container">
        <h1>Personal RAG Journal</h1>
        
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'entry' ? 'active' : ''}`}
            onClick={() => setActiveTab('entry')}
          >
            New Entry
          </button>
          <button
            className={`tab ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => setActiveTab('history')}
          >
            History
          </button>
          <button
            className={`tab ${activeTab === 'query' ? 'active' : ''}`}
            onClick={() => setActiveTab('query')}
          >
            Ask Coach
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
    </div>
  );
}

export default App;

