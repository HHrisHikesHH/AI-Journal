import React, { useState, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar } from 'recharts';
import { format, subDays, parseISO } from 'date-fns';

function HistoryView({ entries, onRefresh }) {
  const [timeRange, setTimeRange] = useState('7');

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
    const streaks = { exercise: 0, deep_work: 0, sleep_on_time: 0 };
    const sorted = [...filteredEntries].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    for (const habit of Object.keys(streaks)) {
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
  }, [filteredEntries]);

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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2>History</h2>
          <div>
            <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)}>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
            </select>
            <button onClick={onRefresh} style={{ marginLeft: '10px' }}>Refresh</button>
          </div>
        </div>

        <div className="visualization">
          <h3>Discipline Trend</h3>
          <LineChart width={800} height={300} data={disciplineData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tickFormatter={(d) => format(parseISO(d), 'MM/dd')} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="rate" stroke="#3498db" name="Show Up Rate %" />
          </LineChart>
        </div>

        <div className="visualization">
          <h3>Habit Streaks</h3>
          <div className="streak-item">
            <span>Exercise</span>
            <span className="streak-count">{habitStreaks.exercise} days</span>
          </div>
          <div className="streak-item">
            <span>Deep Work</span>
            <span className="streak-count">{habitStreaks.deep_work} days</span>
          </div>
          <div className="streak-item">
            <span>Sleep on Time</span>
            <span className="streak-count">{habitStreaks.sleep_on_time} days</span>
          </div>
        </div>

        <div className="visualization">
          <h3>Goal Alignment</h3>
          {goalData.length > 0 ? (
            <BarChart width={800} height={300} data={goalData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="goal" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#27ae60" />
            </BarChart>
          ) : (
            <p>No goal data available</p>
          )}
        </div>

        <div style={{ marginTop: '30px' }}>
          <h3>Recent Entries</h3>
          <div className="entry-list">
            {filteredEntries.slice(0, 10).map(entry => (
              <div key={entry.id} className="entry-item">
                <div className="entry-date">
                  {format(parseISO(entry.timestamp), 'MMM dd, yyyy HH:mm')}
                </div>
                <span className="entry-emotion">{entry.emotion}</span>
                <span className="entry-emotion">Energy: {entry.energy}/10</span>
                {entry.showed_up && <span className="entry-emotion" style={{ backgroundColor: '#27ae60', color: 'white' }}>Showed Up</span>}
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

