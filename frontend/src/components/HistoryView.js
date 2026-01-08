import React, { useState, useMemo, useEffect } from 'react';
import { 
  LineChart, Line, AreaChart, Area, BarChart, Bar, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, 
  ComposedChart, ScatterChart, Scatter, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer 
} from 'recharts';
import { format, subDays, parseISO, getDay, getHours } from 'date-fns';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000/api';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function HistoryView({ entries, onRefresh }) {
  const [timeRange, setTimeRange] = useState('30');
  const [habitsList, setHabitsList] = useState([]);
  const [emotionsList, setEmotionsList] = useState([]);
  const [configLoading, setConfigLoading] = useState(true);
  const [activeInsightTab, setActiveInsightTab] = useState('overview');

  // Fetch config from backend
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const response = await axios.get(`${API_BASE}/config/`);
        const config = response.data;
        setHabitsList(config.habits || []);
        setEmotionsList(config.emotions || []);
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

  // ===== OVERVIEW PATTERNS =====
  
  // Discipline trend data
  const disciplineData = useMemo(() => {
    const byDate = {};
    filteredEntries.forEach(entry => {
      const date = entry.timestamp.split('T')[0];
      if (!byDate[date]) {
        byDate[date] = { date, showedUp: 0, total: 0, energySum: 0 };
      }
      byDate[date].total++;
      byDate[date].energySum += entry.energy || 5;
      if (entry.showed_up) {
        byDate[date].showedUp++;
      }
    });
    return Object.values(byDate)
      .map(d => ({ 
        ...d, 
        rate: d.total > 0 ? (d.showedUp / d.total) * 100 : 0,
        avgEnergy: d.total > 0 ? (d.energySum / d.total).toFixed(1) : 0
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [filteredEntries]);

  // Showed up streak
  const showedUpStreak = useMemo(() => {
    const sorted = [...filteredEntries].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    let current = 0;
    let longest = 0;
    let tempLongest = 0;
    
    for (const entry of sorted) {
      if (entry.showed_up) {
        current++;
        tempLongest++;
        longest = Math.max(longest, tempLongest);
      } else {
        tempLongest = 0;
        // Don't reset current streak if we're looking at past entries
        // Only reset if this is the most recent entry
        if (current > 0 && entry === sorted[0]) {
          current = 0;
        }
      }
    }
    
    return { current, longest };
  }, [filteredEntries]);

  // Habit streaks
  const habitStreaks = useMemo(() => {
    const streaks = {};
    habitsList.forEach(habit => {
      streaks[habit] = { current: 0, longest: 0 };
    });
    
    const sorted = [...filteredEntries].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    for (const habit of habitsList) {
      let current = 0;
      let longest = 0;
      let maxStreak = 0;
      
      for (const entry of sorted) {
        if (entry.habits && entry.habits[habit]) {
          current++;
          maxStreak = Math.max(maxStreak, current);
        } else {
          longest = Math.max(longest, current);
          current = 0;
        }
      }
      longest = Math.max(longest, current);
      streaks[habit] = { current, longest };
    }
    return streaks;
  }, [filteredEntries, habitsList]);

  // ===== ENERGY PATTERNS =====
  
  // Average energy by emotion
  const energyByEmotion = useMemo(() => {
    const emotionStats = {};
    filteredEntries.forEach(entry => {
      const emotion = entry.emotion || 'unknown';
      if (!emotionStats[emotion]) {
        emotionStats[emotion] = { sum: 0, count: 0 };
      }
      emotionStats[emotion].sum += entry.energy || 5;
      emotionStats[emotion].count++;
    });
    
    return Object.entries(emotionStats)
      .map(([emotion, stats]) => ({
        emotion,
        avgEnergy: (stats.sum / stats.count).toFixed(1),
        count: stats.count
      }))
      .sort((a, b) => parseFloat(b.avgEnergy) - parseFloat(a.avgEnergy));
  }, [filteredEntries]);

  // Energy trend over time
  const energyTrendData = useMemo(() => {
    const byDate = {};
    filteredEntries.forEach(entry => {
      const date = entry.timestamp.split('T')[0];
      if (!byDate[date]) {
        byDate[date] = { date, energySum: 0, count: 0 };
      }
      byDate[date].energySum += entry.energy || 5;
      byDate[date].count++;
    });
    return Object.values(byDate)
      .map(d => ({ 
        date: d.date,
        avgEnergy: (d.energySum / d.count).toFixed(1)
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [filteredEntries]);

  // Energy vs habits correlation
  const habitEnergyImpact = useMemo(() => {
    const impact = {};
    habitsList.forEach(habit => {
      let withHabit = { sum: 0, count: 0 };
      let withoutHabit = { sum: 0, count: 0 };
      
      filteredEntries.forEach(entry => {
        if (entry.habits && entry.habits[habit]) {
          withHabit.sum += entry.energy || 5;
          withHabit.count++;
        } else {
          withoutHabit.sum += entry.energy || 5;
          withoutHabit.count++;
        }
      });
      
      impact[habit] = {
        with: withHabit.count > 0 ? (withHabit.sum / withHabit.count).toFixed(1) : 0,
        without: withoutHabit.count > 0 ? (withoutHabit.sum / withoutHabit.count).toFixed(1) : 0,
        diff: withHabit.count > 0 && withoutHabit.count > 0 
          ? ((withHabit.sum / withHabit.count) - (withoutHabit.sum / withoutHabit.count)).toFixed(1) 
          : 0
      };
    });
    return impact;
  }, [filteredEntries, habitsList]);

  // ===== EMOTION PATTERNS =====
  
  // Emotion frequency
  const emotionFrequency = useMemo(() => {
    const frequency = {};
    filteredEntries.forEach(entry => {
      const emotion = entry.emotion || 'unknown';
      frequency[emotion] = (frequency[emotion] || 0) + 1;
    });
    return Object.entries(frequency)
      .map(([emotion, count]) => ({ emotion, count }))
      .sort((a, b) => b.count - a.count);
  }, [filteredEntries]);

  // Emotion trends over time
  const emotionTrendData = useMemo(() => {
    const byDate = {};
    filteredEntries.forEach(entry => {
      const date = entry.timestamp.split('T')[0];
      if (!byDate[date]) {
        byDate[date] = {};
      }
      const emotion = entry.emotion || 'unknown';
      byDate[date][emotion] = (byDate[date][emotion] || 0) + 1;
    });
    
    // Get top emotions
    const topEmotions = emotionFrequency.slice(0, 5).map(e => e.emotion);
    
    return Object.entries(byDate)
      .map(([date, emotions]) => {
        const data = { date };
        topEmotions.forEach(emotion => {
          data[emotion] = emotions[emotion] || 0;
        });
        return data;
      })
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [filteredEntries, emotionFrequency]);

  // Showed up rate by emotion
  const showedUpByEmotion = useMemo(() => {
    const emotionStats = {};
    filteredEntries.forEach(entry => {
      const emotion = entry.emotion || 'unknown';
      if (!emotionStats[emotion]) {
        emotionStats[emotion] = { showedUp: 0, total: 0 };
      }
      emotionStats[emotion].total++;
      if (entry.showed_up) {
        emotionStats[emotion].showedUp++;
      }
    });
    
    return Object.entries(emotionStats)
      .map(([emotion, stats]) => ({
        emotion,
        rate: (stats.showedUp / stats.total * 100).toFixed(1),
        count: stats.total
      }))
      .sort((a, b) => parseFloat(b.rate) - parseFloat(a.rate));
  }, [filteredEntries]);

  // ===== TEMPORAL PATTERNS =====
  
  // Day of week patterns
  const dayOfWeekPatterns = useMemo(() => {
    const dayStats = {};
    DAYS.forEach(day => {
      dayStats[day] = { 
        energySum: 0, count: 0, showedUp: 0, total: 0,
        habits: {}
      };
      habitsList.forEach(habit => {
        dayStats[day].habits[habit] = 0;
      });
    });
    
    filteredEntries.forEach(entry => {
      try {
        const date = parseISO(entry.timestamp);
        const dayIdx = getDay(date);
        const dayName = DAYS[dayIdx];
        
        dayStats[dayName].energySum += entry.energy || 5;
        dayStats[dayName].count++;
        dayStats[dayName].total++;
        if (entry.showed_up) {
          dayStats[dayName].showedUp++;
        }
        
        if (entry.habits) {
          habitsList.forEach(habit => {
            if (entry.habits[habit]) {
              dayStats[dayName].habits[habit]++;
            }
          });
        }
      } catch (e) {
        // Skip invalid dates
      }
    });
    
    return DAYS.map(day => {
      const stats = dayStats[day] || { count: 0, energySum: 0, showedUp: 0, total: 0 };
      return {
        day,
        avgEnergy: stats.count > 0 ? parseFloat((stats.energySum / stats.count).toFixed(1)) : 0,
        showedUpRate: stats.total > 0 ? parseFloat((stats.showedUp / stats.total * 100).toFixed(1)) : 0,
        entryCount: stats.count
      };
    });
  }, [filteredEntries, habitsList]);

  // ===== HABIT PATTERNS =====
  
  // Habit completion rates
  const habitCompletionRates = useMemo(() => {
    const rates = {};
    habitsList.forEach(habit => {
      let completed = 0;
      filteredEntries.forEach(entry => {
        if (entry.habits && entry.habits[habit]) {
          completed++;
        }
      });
      rates[habit] = {
        completed,
        total: filteredEntries.length,
        rate: filteredEntries.length > 0 ? (completed / filteredEntries.length * 100).toFixed(1) : 0
      };
    });
    return rates;
  }, [filteredEntries, habitsList]);

  // Habit combinations (which habits are done together)
  const habitCombinations = useMemo(() => {
    const combinations = {};
    filteredEntries.forEach(entry => {
      if (!entry.habits) return;
      
      const activeHabits = habitsList.filter(habit => entry.habits[habit]);
      if (activeHabits.length >= 2) {
        // Create pairs
        for (let i = 0; i < activeHabits.length; i++) {
          for (let j = i + 1; j < activeHabits.length; j++) {
            const pair = [activeHabits[i], activeHabits[j]].sort().join(' + ');
            combinations[pair] = (combinations[pair] || 0) + 1;
          }
        }
      }
    });
    
    return Object.entries(combinations)
      .map(([pair, count]) => ({ pair, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }, [filteredEntries, habitsList]);

  // ===== BURNOUT INDICATORS =====
  
  // Low energy streak analysis
  const burnoutIndicators = useMemo(() => {
    let lowEnergyStreak = 0;
    let maxLowEnergyStreak = 0;
    let highStressStreak = 0;
    let maxHighStressStreak = 0;
    
    const sorted = [...filteredEntries].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    sorted.forEach(entry => {
      // Low energy streak (energy < 4)
      if ((entry.energy || 5) < 4) {
        lowEnergyStreak++;
        maxLowEnergyStreak = Math.max(maxLowEnergyStreak, lowEnergyStreak);
      } else {
        lowEnergyStreak = 0;
      }
      
      // High stress streak (stressed/anxious/angry + energy < 5)
      const stressEmotions = ['stressed', 'anxious', 'angry'];
      if (stressEmotions.includes(entry.emotion) && (entry.energy || 5) < 5) {
        highStressStreak++;
        maxHighStressStreak = Math.max(maxHighStressStreak, highStressStreak);
      } else {
        highStressStreak = 0;
      }
    });
    
    return {
      currentLowEnergyStreak: lowEnergyStreak,
      maxLowEnergyStreak,
      currentHighStressStreak: highStressStreak,
      maxHighStressStreak
    };
  }, [filteredEntries]);

  // ===== GOAL ALIGNMENT =====
  
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

  // ===== KEY INSIGHTS =====
  
  const keyInsights = useMemo(() => {
    const insights = [];
    
    // Best day of week
    if (dayOfWeekPatterns.length > 0) {
      const bestDay = dayOfWeekPatterns.reduce((best, day) => 
        parseFloat(day.avgEnergy) > parseFloat(best.avgEnergy) ? day : best
      );
      insights.push(`Best energy day: ${bestDay.day} (avg ${bestDay.avgEnergy}/10)`);
    }
    
    // Most consistent habit
    if (Object.keys(habitCompletionRates).length > 0) {
      const mostConsistent = Object.entries(habitCompletionRates)
        .reduce((best, [habit, rate]) => 
          parseFloat(rate.rate) > parseFloat(best.rate) 
            ? { habit, ...rate } 
            : best
        , { habit: '', rate: 0 });
      insights.push(`Most consistent habit: ${mostConsistent.habit.replace(/_/g, ' ')} (${mostConsistent.rate}%)`);
    }
    
    // Highest energy emotion
    if (energyByEmotion.length > 0) {
      const highest = energyByEmotion[0];
      insights.push(`Highest energy emotion: ${highest.emotion} (avg ${highest.avgEnergy}/10)`);
    }
    
    // Best habit for energy
    if (Object.keys(habitEnergyImpact).length > 0) {
      const bestHabit = Object.entries(habitEnergyImpact)
        .reduce((best, [habit, impact]) => 
          parseFloat(impact.diff) > parseFloat(best.diff) 
            ? { habit, ...impact } 
            : best
        , { habit: '', diff: 0 });
      if (parseFloat(bestHabit.diff) > 0) {
        insights.push(`Best habit for energy: ${bestHabit.habit.replace(/_/g, ' ')} (+${bestHabit.diff})`);
      }
    }
    
    // Burnout risk
    if (burnoutIndicators.currentLowEnergyStreak >= 3) {
      insights.push(`⚠️ Low energy streak: ${burnoutIndicators.currentLowEnergyStreak} days - consider rest`);
    }
    
    return insights;
  }, [dayOfWeekPatterns, habitCompletionRates, energyByEmotion, habitEnergyImpact, burnoutIndicators]);

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px', flexWrap: 'wrap', gap: '12px' }}>
          <h2>Insights & Patterns</h2>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <select value={timeRange} onChange={(e) => setTimeRange(e.target.value)} style={{ padding: '10px 16px', minWidth: '140px' }}>
              <option value="7">Last 7 days</option>
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
            </select>
            <button onClick={onRefresh}>Refresh</button>
          </div>
        </div>

        {/* Key Insights Box */}
        {keyInsights.length > 0 && (
          <div style={{ 
            background: 'linear-gradient(135deg, rgba(95, 115, 95, 0.1) 0%, rgba(157, 181, 164, 0.1) 100%)',
            padding: '20px',
            borderRadius: '12px',
            marginBottom: '28px',
            border: '1px solid var(--sage-300)'
          }}>
            <h3 style={{ marginBottom: '16px', fontSize: '1.2rem' }}>Key Insights</h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
              {keyInsights.map((insight, idx) => (
                <div key={idx} style={{
                  padding: '10px 16px',
                  background: 'rgba(255, 255, 255, 0.7)',
                  borderRadius: '8px',
                  fontSize: '14px',
                  fontWeight: 300,
                  color: 'var(--sage-700)'
                }}>
                  {insight}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Insight Tabs */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', flexWrap: 'wrap', borderBottom: '1px solid var(--sage-200)', paddingBottom: '4px' }}>
          {['overview', 'energy', 'emotions', 'habits', 'temporal', 'burnout'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveInsightTab(tab)}
              className="tab"
              style={{
                padding: '10px 20px',
                fontSize: '14px',
                background: activeInsightTab === tab ? 'var(--sage-100)' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                borderRadius: '8px 8px 0 0',
                textTransform: 'capitalize'
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* OVERVIEW TAB */}
        {activeInsightTab === 'overview' && (
          <>
            <div className="visualization">
              <h3>Consistency & Energy Over Time</h3>
              <ResponsiveContainer width="100%" height={300}>
                <ComposedChart data={disciplineData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                  <XAxis dataKey="date" tickFormatter={(d) => format(parseISO(d), 'MM/dd')} stroke="var(--sage-600)" />
                  <YAxis yAxisId="left" stroke="var(--sage-600)" />
                  <YAxis yAxisId="right" orientation="right" stroke="var(--sage-600)" />
                  <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                  <Legend />
                  <Area yAxisId="left" type="monotone" dataKey="avgEnergy" fill="var(--sage-300)" fillOpacity={0.3} stroke="var(--sage-500)" name="Avg Energy" />
                  <Line yAxisId="right" type="monotone" dataKey="rate" stroke="#5f735f" strokeWidth={2} name="Show Up %" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            <div className="visualization">
              <h3>Showed Up Streak</h3>
              <div className="streak-item" style={{ 
                background: showedUpStreak.current > 0 ? 'rgba(95, 115, 95, 0.1)' : 'rgba(255, 255, 255, 0.6)',
                border: `2px solid ${showedUpStreak.current > 0 ? 'var(--sage-500)' : 'var(--sage-300)'}`
              }}>
                <div>
                  <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>Showed Up</span>
                  <span style={{ marginLeft: '12px', fontSize: '13px', color: 'var(--sage-500)' }}>
                    Longest: {showedUpStreak.longest} days
                  </span>
                </div>
                <span className="streak-count" style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: 600,
                  color: showedUpStreak.current > 0 ? 'var(--sage-700)' : 'var(--sage-400)'
                }}>
                  {showedUpStreak.current} days
                </span>
              </div>
            </div>

            <div className="visualization">
              <h3>Practice Streaks</h3>
              {configLoading ? (
                <div className="loading">Loading...</div>
              ) : (
                <div>
                  {Object.entries(habitStreaks).map(([habit, streaks]) => (
                    <div key={habit} className="streak-item">
                      <div>
                        <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{habit.replace(/_/g, ' ')}</span>
                        <span style={{ marginLeft: '12px', fontSize: '13px', color: 'var(--sage-500)' }}>
                          Longest: {streaks.longest} days
                        </span>
                      </div>
                      <span className="streak-count">{streaks.current} days</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="visualization">
              <h3>Goal Alignment</h3>
              {goalData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={goalData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                    <XAxis dataKey="goal" stroke="var(--sage-600)" />
                    <YAxis stroke="var(--sage-600)" />
                    <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                    <Bar dataKey="count" fill="#5f735f" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p style={{ color: 'var(--sage-500)', fontStyle: 'italic', fontWeight: 300, textAlign: 'center', padding: '20px' }}>No goal data available</p>
              )}
            </div>
          </>
        )}

        {/* ENERGY TAB */}
        {activeInsightTab === 'energy' && (
          <>
            <div className="visualization">
              <h3>Average Energy by Emotion</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={energyByEmotion}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                  <XAxis dataKey="emotion" stroke="var(--sage-600)" />
                  <YAxis stroke="var(--sage-600)" />
                  <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                  <Bar dataKey="avgEnergy" fill="#5f735f" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="visualization">
              <h3>Energy Trend Over Time</h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={energyTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                  <XAxis dataKey="date" tickFormatter={(d) => format(parseISO(d), 'MM/dd')} stroke="var(--sage-600)" />
                  <YAxis stroke="var(--sage-600)" />
                  <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                  <Area type="monotone" dataKey="avgEnergy" stroke="var(--sage-500)" fill="var(--sage-300)" fillOpacity={0.5} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="visualization">
              <h3>Habit Impact on Energy</h3>
              {Object.entries(habitEnergyImpact).length > 0 ? (
                <div>
                  {Object.entries(habitEnergyImpact)
                    .sort((a, b) => parseFloat(b[1].diff) - parseFloat(a[1].diff))
                    .map(([habit, impact]) => (
                      <div key={habit} style={{
                        padding: '16px',
                        background: 'rgba(255, 255, 255, 0.5)',
                        borderRadius: '8px',
                        marginBottom: '12px',
                        border: '1px solid var(--sage-200)'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                          <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>{habit.replace(/_/g, ' ')}</span>
                          <span style={{ 
                            fontWeight: 600, 
                            color: parseFloat(impact.diff) > 0 ? 'var(--sage-600)' : '#b8865a',
                            fontSize: '16px'
                          }}>
                            {parseFloat(impact.diff) > 0 ? '+' : ''}{impact.diff}
                          </span>
                        </div>
                        <div style={{ fontSize: '13px', color: 'var(--sage-500)' }}>
                          With: {impact.with}/10 | Without: {impact.without}/10
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <p style={{ color: 'var(--sage-500)', fontStyle: 'italic', fontWeight: 300, textAlign: 'center', padding: '20px' }}>No habit data available</p>
              )}
            </div>
          </>
        )}

        {/* EMOTIONS TAB */}
        {activeInsightTab === 'emotions' && (
          <>
            <div className="visualization">
              <h3>Emotion Frequency</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={emotionFrequency}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                  <XAxis dataKey="emotion" stroke="var(--sage-600)" />
                  <YAxis stroke="var(--sage-600)" />
                  <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                  <Bar dataKey="count" fill="#5f735f" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="visualization">
              <h3>Show Up Rate by Emotion</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={showedUpByEmotion}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                  <XAxis dataKey="emotion" stroke="var(--sage-600)" />
                  <YAxis stroke="var(--sage-600)" />
                  <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                  <Bar dataKey="rate" fill="#5f735f" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="visualization">
              <h3>Emotion Trends Over Time</h3>
              <ResponsiveContainer width="100%" height={350}>
                <ComposedChart data={emotionTrendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                  <XAxis dataKey="date" tickFormatter={(d) => format(parseISO(d), 'MM/dd')} stroke="var(--sage-600)" />
                  <YAxis stroke="var(--sage-600)" />
                  <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                  <Legend />
                  {emotionFrequency.slice(0, 5).map((item, idx) => {
                    const colors = ['#5f735f', '#9db5a4', '#8b7355', '#7d917d', '#a8b5a8'];
                    return (
                      <Line 
                        key={item.emotion} 
                        type="monotone" 
                        dataKey={item.emotion} 
                        stroke={colors[idx % colors.length]} 
                        strokeWidth={2}
                        name={item.emotion}
                      />
                    );
                  })}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </>
        )}

        {/* HABITS TAB */}
        {activeInsightTab === 'habits' && (
          <>
            <div className="visualization">
              <h3>Habit Completion Rates</h3>
              {Object.entries(habitCompletionRates).length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={Object.entries(habitCompletionRates).map(([habit, rate]) => ({
                    habit: habit.replace(/_/g, ' '),
                    rate: parseFloat(rate.rate),
                    completed: rate.completed,
                    total: rate.total
                  })).sort((a, b) => b.rate - a.rate)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                    <XAxis dataKey="habit" stroke="var(--sage-600)" />
                    <YAxis stroke="var(--sage-600)" />
                    <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                    <Bar dataKey="rate" fill="#5f735f" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p style={{ color: 'var(--sage-500)', fontStyle: 'italic', fontWeight: 300, textAlign: 'center', padding: '20px' }}>No habit data available</p>
              )}
            </div>

            <div className="visualization">
              <h3>Habit Combinations</h3>
              {habitCombinations.length > 0 ? (
                <div>
                  <p style={{ color: 'var(--sage-600)', fontSize: '14px', marginBottom: '16px', fontStyle: 'italic' }}>
                    Habits that are often done together
                  </p>
                  {habitCombinations.map(({ pair, count }) => (
                    <div key={pair} style={{
                      padding: '12px 16px',
                      background: 'rgba(255, 255, 255, 0.5)',
                      borderRadius: '8px',
                      marginBottom: '8px',
                      border: '1px solid var(--sage-200)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <span style={{ textTransform: 'capitalize' }}>{pair.replace(/_/g, ' ')}</span>
                      <span style={{ fontWeight: 600, color: 'var(--sage-600)' }}>{count} times</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p style={{ color: 'var(--sage-500)', fontStyle: 'italic', fontWeight: 300, textAlign: 'center', padding: '20px' }}>Not enough data for habit combinations</p>
              )}
            </div>
          </>
        )}

        {/* TEMPORAL TAB */}
        {activeInsightTab === 'temporal' && (
          <>
            <div className="visualization">
              <h3>Day of Week Patterns</h3>
              <ResponsiveContainer width="100%" height={350}>
                <ComposedChart data={dayOfWeekPatterns}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--sage-200)" />
                  <XAxis dataKey="day" stroke="var(--sage-600)" />
                  <YAxis yAxisId="left" stroke="var(--sage-600)" />
                  <YAxis yAxisId="right" orientation="right" stroke="var(--sage-600)" />
                  <Tooltip contentStyle={{ background: 'rgba(255, 255, 255, 0.95)', border: '1px solid var(--sage-300)', borderRadius: '8px' }} />
                  <Legend />
                  <Bar yAxisId="left" dataKey="avgEnergy" fill="var(--sage-400)" name="Avg Energy" radius={[8, 8, 0, 0]} />
                  <Line yAxisId="right" type="monotone" dataKey="showedUpRate" stroke="#5f735f" strokeWidth={2} name="Show Up %" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </>
        )}

        {/* BURNOUT TAB */}
        {activeInsightTab === 'burnout' && (
          <>
            <div className="visualization">
              <h3>Burnout Risk Indicators</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
                <div style={{
                  padding: '20px',
                  background: burnoutIndicators.currentLowEnergyStreak >= 3 
                    ? 'rgba(212, 165, 116, 0.2)' 
                    : 'rgba(157, 181, 164, 0.2)',
                  borderRadius: '12px',
                  border: `2px solid ${burnoutIndicators.currentLowEnergyStreak >= 3 ? '#d4a574' : 'var(--sage-400)'}`,
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '24px', fontWeight: 600, color: 'var(--sage-700)', marginBottom: '8px' }}>
                    {burnoutIndicators.currentLowEnergyStreak}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--sage-600)' }}>Current Low Energy Streak</div>
                  <div style={{ fontSize: '11px', color: 'var(--sage-500)', marginTop: '4px' }}>
                    Max: {burnoutIndicators.maxLowEnergyStreak} days
                  </div>
                </div>
                
                <div style={{
                  padding: '20px',
                  background: burnoutIndicators.currentHighStressStreak >= 2 
                    ? 'rgba(212, 165, 116, 0.2)' 
                    : 'rgba(157, 181, 164, 0.2)',
                  borderRadius: '12px',
                  border: `2px solid ${burnoutIndicators.currentHighStressStreak >= 2 ? '#d4a574' : 'var(--sage-400)'}`,
                  textAlign: 'center'
                }}>
                  <div style={{ fontSize: '24px', fontWeight: 600, color: 'var(--sage-700)', marginBottom: '8px' }}>
                    {burnoutIndicators.currentHighStressStreak}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--sage-600)' }}>Current High Stress Streak</div>
                  <div style={{ fontSize: '11px', color: 'var(--sage-500)', marginTop: '4px' }}>
                    Max: {burnoutIndicators.maxHighStressStreak} days
                  </div>
                </div>
              </div>
              
              {burnoutIndicators.currentLowEnergyStreak >= 3 && (
                <div style={{
                  padding: '16px',
                  background: 'rgba(212, 165, 116, 0.1)',
                  borderRadius: '8px',
                  border: '1px solid rgba(212, 165, 116, 0.3)',
                  color: '#b8865a',
                  fontSize: '14px',
                  fontStyle: 'italic'
                }}>
                  ⚠️ Low energy streak detected. Consider taking a rest day or reducing intensity.
                </div>
              )}
            </div>
          </>
        )}

        {/* Recent Reflections */}
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
