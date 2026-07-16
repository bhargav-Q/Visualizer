import React from 'react';
import ReactWordcloud from 'react-wordcloud';
import { BarChart2 } from 'lucide-react';
import './WordCloud.css';

const WordCloud = ({ keywords }) => {
  const wordCloudData = keywords.map(kw => ({
    text: kw.word,
    value: kw.score * 100
  }));

  const wordCloudOptions = {
    colors: ['#818cf8', '#6366f1', '#4f46e5', '#a855f7', '#d8b4fe'],
    enableTooltip: true,
    deterministic: false,
    fontFamily: 'Inter, sans-serif',
    fontSizes: [20, 60],
    fontStyle: 'normal',
    fontWeight: 'bold',
    padding: 1,
    rotations: 3,
    rotationAngles: [0, 90],
    scale: 'sqrt',
    spiral: 'archimedean',
    transitionDuration: 1000
  };

  return (
    <div className="wordcloud-section glass-panel">
      <div className="section-header">
        <BarChart2 size={24} color="var(--accent-color)" />
        <h3>Keyword Analysis</h3>
      </div>
      
      <div className="wordcloud-wrapper">
        {wordCloudData.length > 0 ? (
          <ReactWordcloud words={wordCloudData} options={wordCloudOptions} />
        ) : (
          <div className="no-keywords">No keywords found.</div>
        )}
      </div>
      
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
