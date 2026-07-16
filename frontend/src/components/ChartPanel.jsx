import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  LineChart, Line
} from 'recharts';
import './ChartPanel.css';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="chart-tooltip glass-panel">
        <p className="label">{`${label} : ${payload[0].value}`}</p>
      </div>
    );
  }
  return null;
};

const ChartPanel = ({ charts }) => {
  if (!charts || charts.length === 0) return null;

  return (
    <div className="charts-section">
      <h3 className="section-title">Data Visualizations</h3>
      <div className="charts-grid">
        {charts.map((chart, idx) => (
          <div key={idx} className="chart-container glass-panel">
            <h4>{chart.title}</h4>
            <div className="chart-wrapper">
              <ResponsiveContainer width="100%" height={300}>
                {chart.type === 'bar' ? (
                  <BarChart data={chart.data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                    <XAxis dataKey={chart.x_key} stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                    <YAxis stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                    <RechartsTooltip content={<CustomTooltip />} />
                    <Bar dataKey={chart.y_key} fill="var(--accent-color)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                ) : (
                  <LineChart data={chart.data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                    <XAxis dataKey={chart.x_key} stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                    <YAxis stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                    <RechartsTooltip content={<CustomTooltip />} />
                    <Line type="monotone" dataKey={chart.y_key} stroke="var(--accent-color)" strokeWidth={3} dot={{r: 4, fill: "var(--bg-dark)", strokeWidth: 2}} />
                  </LineChart>
                )}
              </ResponsiveContainer>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChartPanel;
