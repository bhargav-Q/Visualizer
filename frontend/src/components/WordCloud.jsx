import React from 'react';
import { BarChart2 } from 'lucide-react';
import ErrorBoundary from './ErrorBoundary';
import './WordCloud.css';

const WordCloud = ({ keywords }) => {
  // Vibrant colors for the custom cloud
  const colors = ['#818cf8', '#6366f1', '#4f46e5', '#a855f7', '#d8b4fe', '#c084fc', '#8b5cf6'];

  return (
    <div className="wordcloud-section glass-panel">
      <div className="section-header">
        <BarChart2 size={24} color="var(--accent-color)" />
        <h3>Keyword Analysis</h3>
      </div>
      
      <ErrorBoundary>
        <div className="wordcloud-wrapper custom-cloud">
          {keywords.length > 0 ? (
            keywords.map((kw, idx) => {
              // Scale score (0.0 to 1.0) to font size (16px to 64px)
              const fontSize = 16 + (kw.score * 48);
              const color = colors[idx % colors.length];
              
              return (
                <span 
                  key={idx} 
                  style={{
                    fontSize: `${fontSize}px`,
                    color: color,
                    padding: '8px',
                    fontWeight: 600,
                    lineHeight: 1,
                    opacity: 0.8 + (kw.score * 0.2)
                  }}
                  className="cloud-word"
                >
                  {kw.word}
                </span>
              );
            })
          ) : (
            <div className="no-keywords">No keywords found.</div>
          )}
        </div>
      </ErrorBoundary>
      
      <div className="keyword-tags">
        {keywords.slice(0, 10).map((kw, idx) => (
          <span key={idx} className="keyword-tag">
            {kw.word} <span className="score">{(kw.score * 100).toFixed(0)}%</span>
          </span>
        ))}
      </div>
    </div>
  );
};

export default WordCloud;
