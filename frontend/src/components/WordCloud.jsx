import React from 'react';
import { BarChart2 } from 'lucide-react';
import ErrorBoundary from './ErrorBoundary';
import './WordCloud.css';

const WordCloud = ({ keywords }) => {
  // Brand specific palette matching category colors
  const colors = ['#6a1b9a', '#9c4dcc', '#2563eb', '#22c55e', '#d97700', '#dc2626'];

  return (
    <div className="wordcloud-section glass-panel">
      <div className="section-header">
        <BarChart2 size={24} color="var(--brand-purple)" />
        <h3>Keyword Analysis</h3>
      </div>
      
      <ErrorBoundary>
        <div className="wordcloud-wrapper custom-cloud">
          {keywords && keywords.length > 0 ? (
            keywords.map((kw, idx) => {
              const normScore = kw.score > 1 ? kw.score / 100 : (kw.score || 0);
              // Scale score (0.0 to 1.0) to font size (16px to 54px)
              const fontSize = 16 + (normScore * 38);
              const color = colors[idx % colors.length];
              
              return (
                <span 
                  key={idx} 
                  style={{
                    fontSize: `${fontSize}px`,
                    color: color,
                    padding: '8px',
                    fontWeight: 600,
                    lineHeight: 1.1,
                    opacity: 0.75 + (normScore * 0.25)
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
        {keywords && keywords.slice(0, 10).map((kw, idx) => {
          const normScore = kw.score > 1 ? kw.score / 100 : (kw.score || 0);
          return (
            <span key={idx} className="keyword-tag">
              {kw.word} <span className="score">{(normScore * 100).toFixed(0)}%</span>
            </span>
          );
        })}
      </div>
    </div>
  );
};

export default WordCloud;
