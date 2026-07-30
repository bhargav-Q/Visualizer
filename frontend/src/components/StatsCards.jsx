import React from 'react';
import { TrendingUp, Hash, DollarSign, Activity, FileText, CheckCircle2 } from 'lucide-react';
import './StatsCards.css';

const getCategoryIcon = (label = '') => {
  const l = label.toLowerCase();
  if (l.includes('revenue') || l.includes('sales') || l.includes('$') || l.includes('cost') || l.includes('profit')) {
    return <DollarSign size={18} color="#22c55e" />;
  }
  if (l.includes('growth') || l.includes('rate') || l.includes('%') || l.includes('margin')) {
    return <TrendingUp size={18} color="#6366f1" />;
  }
  if (l.includes('word') || l.includes('page') || l.includes('document')) {
    return <FileText size={18} color="#ec4899" />;
  }
  if (l.includes('status') || l.includes('extracted') || l.includes('active')) {
    return <CheckCircle2 size={18} color="#3b82f6" />;
  }
  return <Activity size={18} color="#8b5cf6" />;
};

const StatsCards = ({ metrics, kpis }) => {
  const cardList = kpis && kpis.length > 0 
    ? kpis.map(k => ({ title: k.label, value: k.value }))
    : (metrics || []);

  if (!cardList || cardList.length === 0) return null;

  return (
    <div 
      className="metrics-grid"
      role="region"
      aria-label="Key Performance Indicators and Metrics Grid"
    >
      {cardList.map((metric, idx) => {
        const title = metric.title || metric.label || 'Metric';
        const val = metric.value !== undefined && metric.value !== null ? metric.value : 'N/A';

        return (
          <div 
            key={idx} 
            className="metric-card glass-panel"
            aria-label={`${title}: ${val}`}
          >
            <div className="metric-card-top">
              <span className="metric-title">{title}</span>
              <div className="metric-icon-box">
                {getCategoryIcon(title)}
              </div>
            </div>
            <div className="metric-card-bottom">
              <span className="metric-value">{val}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default React.memo(StatsCards);
