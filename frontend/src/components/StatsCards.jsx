import React from 'react';
import './StatsCards.css';

const StatsCards = ({ metrics }) => {
  return (
    <div className="metrics-grid">
      {metrics.map((metric, idx) => (
        <div key={idx} className="metric-card glass-panel">
          <span className="metric-title">{metric.title}</span>
          <span className="metric-value">{metric.value}</span>
        </div>
      ))}
    </div>
  );
};

export default StatsCards;
