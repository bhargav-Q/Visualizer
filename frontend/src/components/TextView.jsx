import React from 'react';
import TextSummary from './TextSummary';
import WordCloud from './WordCloud';
import './TextView.css';

const TextView = ({ textData }) => {
  const { summary, keywords, word_count, page_count, paragraph_count, ai_model } = textData;

  return (
    <div className="text-view">
      
      {/* Top Level Metrics */}
      <div className="metrics-grid">
        <div className="metric-card glass-panel">
          <span className="metric-title">Word Count</span>
          <span className="metric-value">{word_count?.toLocaleString() || 0}</span>
        </div>
        {page_count !== null && page_count !== undefined && (
          <div className="metric-card glass-panel">
            <span className="metric-title">Pages Extracted</span>
            <span className="metric-value">{page_count}</span>
          </div>
        )}
        {paragraph_count !== null && paragraph_count !== undefined && (
          <div className="metric-card glass-panel">
            <span className="metric-title">Paragraphs</span>
            <span className="metric-value">{paragraph_count}</span>
          </div>
        )}
      </div>

      <div className="text-content-grid">
        <TextSummary summary={summary} ai_model={ai_model} />
        <WordCloud keywords={keywords} />
      </div>
      
    </div>
  );
};

export default TextView;
