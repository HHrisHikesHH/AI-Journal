import React, { useState, useMemo, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar } from 'recharts';
import { format, subDays, parseISO } from 'date-fns';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

function HistoryView({ entries, onRefresh }) {
  const [timeRange, setTimeRange] = useState('7');
  const [habitsList, setHabitsList] = useState([]);
  const [configLoading, setConfigLoading] = useState(true);

  // Fetch config from backend
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await axios.get(`${API_BASE}/config/`);
        const config = response.data;
        setHabitsList(config.habits || []);
        setConfigLoading(false);
      } catch (err) {
        console.error('Error loading config:', err);
        setConfigLoading(false);
      }
    };
    fetchConfig();
  }, []);

  const filteredEntries = useMemo(() => {
    const days = parseInt(timeRange);
    const cutoff = subDays(new Date(), days);
    return entries.filter(entry => {
      try {
        const entryDate = parseISO(entry.timestamp);
        return entryDate >= cutoff;
      } catch {
        return false;
      }
    }).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
  }, [entries, timeRange]);

  // Discipline trend data
  const disciplineData = useMemo(() => {
    const byDate = {};
    filteredEntries.forEach(entry => {
      const date = entry.timestamp.split('T')[0];
      if (!byDate[date]) {
        byDate[date] = { date, showedUp: 0, total: 0 };
      }
      byDate[date].total++;
      if (entry.showed_up) {
        byDate[date].showedUp++;
      }
    });
    return Object.values(byDate)
      .map(d => ({ ...d, rate: d.total > 0 ? (d.showedUp / d.total) * 100 : 0 }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [filteredEntries]);

  // Habit streaks
  const habitStreaks = useMemo(() => {
    const streaks = {};
    // Initialize streaks with all habits from config
    habitsList.forEach(habit => {
      streaks[habit] = 0;
    });
    
    const sorted = [...filteredEntries].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    for (const habit of habitsList) {
      let current = 0;
      for (const entry of sorted) {
        if (entry.habits && entry.habits[habit]) {
          current++;
        } else {
          break;
        }
      }
      streaks[habit] = current;
    }
    return streaks;
  }, [filteredEntries, habitsList]);

  // Goal alignment (simple: entries with goals mentioned)
  const goalData = useMemo(() => {
    const goalCounts = {};
    filteredEntries.forEach(entry => {
      if (entry.goals && Array.isArray(entry.goals)) {
        entry.goals.forEach(goal => {
          goalCounts[goal] = (goalCounts[goal] || 0) + 1;
        });
      }
    });
    return Object.entries(goalCounts).map(([goal, count]) => ({ goal, count }));
  }, [filteredEntries]);

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px', flexWrap: 'wrap', gap: '12px' }}>
          <h2>Your Journey</h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)} style={{ padding: '10px 16px', minWidth: '140px' }}>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
            </select>
            <button onClick={onRefresh}>Refresh</button>
          </div>
        </div>

        <div className="visualization">
          <h3>Consistency Over Time</h3>
          <LineChart width={800} height={300} data={disciplineData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={(d) => format(parseISO(d), 'MM/dd')} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="rate" stroke="#5f735f" name="Show Up Rate %" strokeWidth={2} />
          </LineChart>
        </div>

        <div className="visualization">
          <h3>Practice Streaks</h3>
          {configLoading ? (
            <div className="loading">Loading...</div>
          ) : (
            <div>
              {Object.entries(habitStreaks).map(([habit, streak]) => (
                <div key={habit} className="streak-item">
                  <span style={{ textTransform: 'capitalize' }}>{habit.replace(/_/g, ' ')}</span>
                  <span className="streak-count">{streak} days</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="visualization">
          <h3>Goal Alignment</h3>
          {goalData.length > 0 ? (
            <BarChart width={800} height={300} data={goalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="goal" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#5f735f" />
            </BarChart>
          ) : (
            <p style={{ color: 'var(--sage-500)', fontStyle: 'italic', fontWeight: 300, textAlign: 'center', padding: '20px' }}>No goal data available</p>
          )}
        </div>

        <div style={{ marginTop: '40px' }}>
          <h3>Recent Reflections</h3>
          <div className="entry-list">
            {filteredEntries.slice(0, 10).map(entry => (
              <div key={entry.id} className="entry-item">
                <div className="entry-date">
                  {format(parseISO(entry.timestamp), 'MMM dd, yyyy HH:mm')}
                </div>
                <span className="entry-emotion">{entry.emotion}</span>
                <span className="entry-emotion">Energy: {entry.energy}/10</span>
                {entry.showed_up && <span className="entry-emotion" style={{ backgroundColor: 'var(--sage-600)', color: 'white' }}>Showed Up</span>}
                {entry.free_text && (
                  <div className="entry-text">{entry.free_text}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default HistoryView;

