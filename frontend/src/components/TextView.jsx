import React from 'react';
import TextSummary from './TextSummary';
import WordCloud from './WordCloud';
import StatsCards from './StatsCards';
import DocumentReader from './DocumentReader';
import './TextView.css';

const TextView = ({ textData, activeSubTab, processingTime, rawMarkdown, fileName }) => {
  if (!textData) return null;
  const { summary, keywords, kpis, word_count, page_count, paragraph_count, ai_model } = textData;

  // Prefer domain content KPIs extracted by DeepSeek-V4-Flash over file metadata
  const displayKpis = kpis && kpis.length > 0 
    ? kpis 
    : [
        { label: "Word Count", value: word_count?.toLocaleString() || 0 },
        { label: "Pages Extracted", value: page_count || 1 },
        { label: "Paragraphs", value: paragraph_count || 1 }
      ];

  return (
    <div className="text-view">
      {activeSubTab === 'summary' && (
        <div className="text-summary-view-wrapper animate-fade-in">
          <StatsCards kpis={displayKpis} />
          <TextSummary summary={summary} ai_model={ai_model || "NVIDIA NIM DeepSeek-V4-Flash"} />
        </div>
      )}

      {activeSubTab === 'keywords' && (
        <div className="text-keywords-view-wrapper animate-fade-in">
          <WordCloud keywords={keywords} />
        </div>
      )}

      {activeSubTab === 'reader' && (
        <div className="text-reader-view-wrapper animate-fade-in">
          <DocumentReader rawMarkdown={rawMarkdown} fileName={fileName} />
        </div>
      )}
    </div>
  );
};

export default TextView;
