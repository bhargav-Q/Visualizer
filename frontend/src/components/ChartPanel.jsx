import React, { useState } from 'react';
import { Maximize2, Minimize2 } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  LineChart, Line, Label
} from 'recharts';
import './ChartPanel.css';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="chart-tooltip glass-panel">
        <p className="label">{`${label} : ${payload[0].value.toLocaleString()}`}</p>
      </div>
    );
  }
  return null;
};

const ChartPanel = ({ charts }) => {
  const [focusIndex, setFocusIndex] = useState(null);

  if (!charts || charts.length === 0) return null;

  const getGridClass = () => {
    if (charts.length === 1) return 'cols-1';
    if (charts.length === 2) return 'cols-2';
    return 'cols-3';
  };

  return (
    <div className="charts-section">
      <h3 className="section-title">Data Visualizations</h3>
      <div className={`charts-grid ${getGridClass()}`}>
        {charts.map((chart, idx) => {
          const isExpanded = focusIndex === idx;
          return (
            <div 
              key={idx} 
              className={`chart-container glass-panel ${isExpanded ? 'expanded' : ''}`}
            >
              <div className="chart-header">
                <h4>{chart.title}</h4>
                <button 
                  className="focus-toggle-btn"
                  onClick={() => setFocusIndex(isExpanded ? null : idx)}
                  title={isExpanded ? "Collapse view" : "Expand view"}
                >
                  {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                </button>
              </div>
              <div className="chart-wrapper">
                <ResponsiveContainer width="100%" height={isExpanded ? 450 : 300}>
                  {chart.type === 'bar' ? (
                    <BarChart data={chart.data} margin={{ top: 20, right: 30, left: 35, bottom: 25 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                      <XAxis dataKey={chart.x_key} stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}}>
                        <Label value={chart.x_key} offset={-15} position="insideBottom" fill="var(--text-secondary)" style={{fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em'}} />
                      </XAxis>
                      <YAxis stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}}>
                        <Label value={chart.y_key} angle={-90} position="insideLeft" offset={-15} fill="var(--text-secondary)" style={{fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', textAnchor: 'middle', letterSpacing: '0.05em'}} />
                      </YAxis>
                      <RechartsTooltip content={<CustomTooltip />} />
                      <Bar dataKey={chart.y_key} fill="var(--accent-color)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  ) : (
                    <LineChart data={chart.data} margin={{ top: 20, right: 30, left: 35, bottom: 25 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                      <XAxis dataKey={chart.x_key} stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}}>
                        <Label value={chart.x_key} offset={-15} position="insideBottom" fill="var(--text-secondary)" style={{fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em'}} />
                      </XAxis>
                      <YAxis stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}}>
                        <Label value={chart.y_key} angle={-90} position="insideLeft" offset={-15} fill="var(--text-secondary)" style={{fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', textAnchor: 'middle', letterSpacing: '0.05em'}} />
                      </YAxis>
                      <RechartsTooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey={chart.y_key} stroke="var(--accent-color)" strokeWidth={3} dot={{r: 4, fill: "var(--bg-dark)", strokeWidth: 2}} />
                    </LineChart>
                  )}
                </ResponsiveContainer>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ChartPanel;
