import React from 'react';
import { Columns } from 'lucide-react';
import './DataDetailsAccordion.css';

const DataDetailsAccordion = ({ columns, numericSummary, categoricalSummary }) => {
  if (!columns || columns.length === 0) return null;

  return (
    <div className="accordion-section">
      <div className="section-header">
        <Columns size={24} color="var(--brand-purple)" />
        <h3 className="section-title">Column Schema & Statistical Breakdown</h3>
      </div>
      
      <div className="accordion-list">
        {columns.map((col, idx) => {
          const isNumeric = numericSummary && numericSummary[col.name];
          const isCategorical = categoricalSummary && categoricalSummary[col.name];
          
          let dtypeClass = 'dtype-other';
          if (col.dtype.includes('float')) dtypeClass = 'dtype-float';
          else if (col.dtype.includes('int')) dtypeClass = 'dtype-int';
          else if (col.dtype.includes('object') || col.dtype.includes('str')) dtypeClass = 'dtype-object';
          else if (col.dtype.includes('date')) dtypeClass = 'dtype-date';

          return (
            <details key={idx} className="geo-faq-item glass-panel">
              <summary className="geo-faq-question">
                <span className="col-name-wrapper">
                  <span className="col-index">#{(idx + 1).toString().padStart(2, '0')}</span>
                  <span className="col-name">{col.name}</span>
                </span>
                <span className={`col-dtype ${dtypeClass}`}>{col.dtype}</span>
              </summary>
              
              <div className="geo-faq-answer">
                {isNumeric && (
                  <div className="stat-grid">
                    <div className="stat-row">
                      <span className="stat-label">Mean</span>
                      <span className="stat-val">{numericSummary[col.name].mean?.toLocaleString(undefined, {maximumFractionDigits: 2}) ?? 'N/A'}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Median</span>
                      <span className="stat-val">{numericSummary[col.name].median?.toLocaleString(undefined, {maximumFractionDigits: 2}) ?? 'N/A'}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Min Value</span>
                      <span className="stat-val">{numericSummary[col.name].min?.toLocaleString(undefined, {maximumFractionDigits: 2}) ?? 'N/A'}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Max Value</span>
                      <span className="stat-val">{numericSummary[col.name].max?.toLocaleString(undefined, {maximumFractionDigits: 2}) ?? 'N/A'}</span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Std Dev</span>
                      <span className="stat-val">{numericSummary[col.name].std?.toLocaleString(undefined, {maximumFractionDigits: 2}) ?? 'N/A'}</span>
                    </div>
                  </div>
                )}

                {isCategorical && (
                  <div className="categorical-info">
                    <div className="unique-count">
                      <strong>Unique Values:</strong> {categoricalSummary[col.name].unique}
                    </div>
                    {categoricalSummary[col.name].top_values && (
                      <div className="top-values">
                        <div className="top-values-title">Top Occurrences:</div>
                        <div className="top-values-list">
                          {categoricalSummary[col.name].top_values.map((item, keyIdx) => (
                            <div key={keyIdx} className="top-value-pill">
                              <span className="val">{item.value || 'null'}</span>
                              <span className="count">{item.count} rows</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {!isNumeric && !isCategorical && (
                  <div className="no-summary">
                    No statistical summary available for this column type.
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </div>
    </div>
  );
};

export default DataDetailsAccordion;
