import React, { useState } from 'react';
import { Maximize2, Minimize2 } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  LineChart, Line, Label, PieChart, Pie, Cell, Legend
} from 'recharts';
import { PIE_COLORS } from '../utils/constants';
import './ChartPanel.css';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const dataName = payload[0].name;
    const value = payload[0].value;
    const formattedVal = (typeof value === 'number') ? value.toLocaleString() : (value ?? 'N/A');
    return (
      <div className="chart-tooltip">
        <p className="label">{label ? `${label}` : `${dataName}`}: {formattedVal}</p>
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
              className={`chart-container ${isExpanded ? 'expanded' : ''}`}
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
                <ResponsiveContainer width="99%" height={isExpanded ? 450 : 320} minHeight={300}>
                  {chart.type === 'bar' ? (
                    <BarChart data={chart.data} margin={{ top: 20, right: 30, left: 35, bottom: 25 }}>
                      <defs>
                        <linearGradient id={`barGrad-${idx}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--brand-purple)" stopOpacity={0.9}/>
                          <stop offset="95%" stopColor="var(--brand-purple-accent)" stopOpacity={0.6}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(106,27,154,0.08)" vertical={false} />
                      <XAxis dataKey={chart.x_key} stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)', fontFamily: 'Work Sans', fontSize: 11}}>
                        <Label value={chart.x_key} offset={-15} position="insideBottom" fill="var(--text-muted)" style={{fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', fontFamily: 'Work Sans'}} />
                      </XAxis>
                      <YAxis stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)', fontFamily: 'Work Sans', fontSize: 11}}>
                        <Label value={chart.y_key} angle={-90} position="insideLeft" offset={-15} fill="var(--text-muted)" style={{fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', textAnchor: 'middle', letterSpacing: '0.05em', fontFamily: 'Work Sans'}} />
                      </YAxis>
                      <RechartsTooltip content={<CustomTooltip />} />
                      <Bar dataKey={chart.y_key} fill={`url(#barGrad-${idx})`} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  ) : chart.type === 'pie' ? (
                    <PieChart>
                      <Pie
                        data={chart.data}
                        cx="50%"
                        cy="45%"
                        innerRadius={isExpanded ? 80 : 50}
                        outerRadius={isExpanded ? 120 : 80}
                        paddingAngle={4}
                        dataKey={chart.y_key}
                        nameKey={chart.x_key}
                      >
                        {chart.data.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <RechartsTooltip content={<CustomTooltip />} />
                      <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{fontFamily: 'Work Sans', fontSize: 12, color: 'var(--text-secondary)'}} />
                    </PieChart>
                  ) : (
                    <LineChart data={chart.data} margin={{ top: 20, right: 30, left: 35, bottom: 25 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(106,27,154,0.08)" vertical={false} />
                      <XAxis dataKey={chart.x_key} stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)', fontFamily: 'Work Sans', fontSize: 11}}>
                        <Label value={chart.x_key} offset={-15} position="insideBottom" fill="var(--text-muted)" style={{fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', fontFamily: 'Work Sans'}} />
                      </XAxis>
                      <YAxis stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)', fontFamily: 'Work Sans', fontSize: 11}}>
                        <Label value={chart.y_key} angle={-90} position="insideLeft" offset={-15} fill="var(--text-muted)" style={{fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', textAnchor: 'middle', letterSpacing: '0.05em', fontFamily: 'Work Sans'}} />
                      </YAxis>
                      <RechartsTooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey={chart.y_key} stroke="var(--brand-purple)" strokeWidth={3} dot={{r: 5, fill: "#ffffff", stroke: "var(--brand-purple-accent)", strokeWidth: 2}} activeDot={{r: 7}} />
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

export default React.memo(ChartPanel);
