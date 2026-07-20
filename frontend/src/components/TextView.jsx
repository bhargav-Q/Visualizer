import React from 'react';
import TextSummary from './TextSummary';
import WordCloud from './WordCloud';
import StatsCards from './StatsCards';
import './TextView.css';

const TextView = ({ textData, activeSubTab }) => {
  if (!textData) return null;
  const { summary, keywords, word_count, page_count, paragraph_count, ai_model } = textData;

  const metrics = [
    { title: "Word Count", value: word_count?.toLocaleString() || 0 }
  ];

  if (page_count !== null && page_count !== undefined) {
    metrics.push({ title: "Pages Extracted", value: page_count });
  }

  if (paragraph_count !== null && paragraph_count !== undefined) {
    metrics.push({ title: "Paragraphs", value: paragraph_count });
  }

  return (
    <div className="text-view">
      {activeSubTab === 'summary' ? (
        <div className="text-summary-view-wrapper animate-fade-in">
          <StatsCards metrics={metrics} />
          <TextSummary summary={summary} ai_model={ai_model} />
        </div>
      ) : (
        <div className="text-keywords-view-wrapper animate-fade-in">
          <WordCloud keywords={keywords} />
        </div>
      )}
    </div>
  );
};

export default TextView;
