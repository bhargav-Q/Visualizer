import React, { useState } from 'react';
import TabularView from './TabularView';
import TextView from './TextView';
// import TraceabilityViewer from './TraceabilityViewer';
import StatsCards from './StatsCards';
import ChartPanel from './ChartPanel';
import DataTablePreview from './DataTablePreview';
import { ArrowLeft, Database, FileText, Search, Download, Copy, Check, ArrowUpDown } from 'lucide-react';
import './Dashboard.css';

const Dashboard = ({ data, onReset }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTableIndex, setSelectedTableIndex] = useState(0);
  const [sortField, setSortField] = useState('key_name');
  const [sortOrder, setSortOrder] = useState('asc');
  const [copied, setCopied] = useState(false);

  const handleDownloadJSON = () => {
    if (!data) return;
    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${(data.file_name || 'analytics_result').replace(/\.[^/.]+$/, '')}_full_output.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyJSON = () => {
    if (!data) return;
    const jsonString = JSON.stringify(data, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  };

  if (!data) return null;

  const isTabular = data.data_category === 'tabular';
  const hasTraceability = data.file_type === 'pdf' || (data.file_name && data.file_name.toLowerCase().endsWith('.pdf'));

  const getValidTab = () => {
    if (isTabular) {
      return (activeTab === 'overview' || activeTab === 'preview') ? activeTab : 'overview';
    }
    const isQualitative = data.data_category === 'qualitative_document' || 
      (data.analytics && (!data.analytics.metrics || data.analytics.metrics.length === 0) && (!data.analytics.tables || data.analytics.tables.length === 0));

    const validTabs = ['overview', 'summary', 'keywords'];
    if ((data.analytics && data.analytics.tables && data.analytics.tables.length > 0) || data.tabular) {
      validTabs.push('tables');
    }
    if (hasTraceability) {
      validTabs.push('traceability');
    }
    if (!validTabs.includes(activeTab)) {
      return isQualitative ? 'summary' : 'overview';
    }
    return activeTab;
  };

  const currentTab = getValidTab();

  // Metrics filtering
  const filteredMetrics = (data.analytics?.metrics || []).filter(m => {
    const term = searchTerm.toLowerCase();
    const category = (m.category || '').toLowerCase();
    const val = (m.metric_value !== undefined && m.metric_value !== null) ? m.metric_value.toString() : '';
    const unit = (m.unit || '').toLowerCase();
    return category.includes(term) || val.includes(term) || unit.includes(term);
  });

  // Key Value pairs filtering
  const rawKvList = data.key_value_pairs || data.analytics?.key_value_pairs || [];
  const filteredKeyValuePairs = rawKvList.filter(kv => {
    const term = searchTerm.toLowerCase();
    const key = (kv.key_name || '').toLowerCase();
    const val = (kv.value || '').toLowerCase();
    return key.includes(term) || val.includes(term);
  });

  // Key Value sorting
  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const sortedKeyValuePairs = [...filteredKeyValuePairs].sort((a, b) => {
    let valA = a[sortField] || '';
    let valB = b[sortField] || '';
    
    valA = valA.toString().toLowerCase();
    valB = valB.toString().toLowerCase();
    
    if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
    if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  // KPI display value formatter
  const formatMetricValue = (val, unit) => {
    if (val === undefined || val === null) return 'N/A';
    const formattedNum = typeof val === 'number' ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : val;
    if (!unit) return formattedNum;
    const lowerUnit = unit.toLowerCase();
    if (lowerUnit === 'usd' || unit === '$') return `$${formattedNum}`;
    if (unit === '%') return `${formattedNum}%`;
    return `${formattedNum} ${unit}`;
  };

  // KPI cards metrics structure
  const kpiMetrics = React.useMemo(() => {
    if (data.kpis && data.kpis.length > 0) {
      return data.kpis.map(k => ({ title: k.label, value: k.value }));
    }
    return filteredMetrics.map(m => ({
      title: m.category,
      value: formatMetricValue(m.metric_value, m.unit)
    }));
  }, [data.kpis, filteredMetrics]);

  // Recharts Metrics comparison chart structure
  const metricsCharts = React.useMemo(() => {
    if (data.charts && data.charts.length > 0) {
      return data.charts;
    }
    if (filteredMetrics.length > 0) {
      return [{
        title: "Metrics Comparison",
        type: "bar",
        x_key: "category",
        y_key: "value",
        data: filteredMetrics.map(m => ({
          category: m.category,
          value: m.metric_value
        }))
      }];
    }
    return [];
  }, [data.charts, filteredMetrics]);

  return (
    <div className="dashboard-container animate-fade-in">
      <div className="dashboard-header">
        <div className="header-action-group" style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="back-button btn-white" onClick={onReset}>
            <ArrowLeft size={16} />
            Upload Another File
          </button>
          <button className="btn-white btn-export" onClick={handleDownloadJSON} title="Download complete output as a JSON file">
            <Download size={15} style={{ color: 'var(--brand-purple)' }} />
            Export JSON
          </button>
          <button className="btn-white btn-export" onClick={handleCopyJSON} title="Copy complete output JSON to clipboard">
            {copied ? <Check size={15} color="#22c55e" /> : <Copy size={15} style={{ color: 'var(--brand-purple)' }} />}
            {copied ? 'Copied!' : 'Copy JSON'}
          </button>
        </div>
        
        <div className="file-info">
          <span className="file-icon-wrapper">
            {!isTabular ? (
              <FileText size={18} color="var(--brand-purple)" />
            ) : (
              <Database size={18} color="var(--color-sales-strategy)" />
            )}
          </span>
          <span className="file-name">{data.file_name}</span>
          <span className={`badge-type ${isTabular ? 'badge-tabular' : 'badge-text'}`}>
            {(data.file_type || data.source_type || 'doc').toUpperCase()}
          </span>
          {!isTabular && data.analytics?.tables && data.analytics.tables.length > 0 && (
            <span className="badge-type badge-mixed">
              Tables Detected
            </span>
          )}
          {data.processing_time !== undefined && data.processing_time !== null && (
            <span className="badge-type badge-time" title="Total API & OCR Processing Time">
              ⏱️ {data.processing_time}s
            </span>
          )}
        </div>
      </div>

      {/* Dynamic Content Navigation Tabs Based On Dataset Classification */}
      <div className="content-type-tabs">
        {isTabular ? (
          <>
            <button 
              className={`ct-tab ${currentTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Overview Analytics
            </button>
            <button 
              className={`ct-tab ${currentTab === 'preview' ? 'active' : ''}`}
              onClick={() => setActiveTab('preview')}
            >
              Data Overview & Charts
            </button>
          </>
        ) : (
          <>
            <button 
              className={`ct-tab ${currentTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Overview Analytics
            </button>
            <button 
              className={`ct-tab ${currentTab === 'summary' ? 'active' : ''}`}
              onClick={() => setActiveTab('summary')}
            >
              Executive Summary
            </button>
            <button 
              className={`ct-tab ${currentTab === 'keywords' ? 'active' : ''}`}
              onClick={() => setActiveTab('keywords')}
            >
              Keyword Analysis
            </button>
            {((data.analytics?.tables && data.analytics.tables.length > 0) || data.tabular) && (
              <button 
                className={`ct-tab ${currentTab === 'tables' ? 'active' : ''}`}
                onClick={() => setActiveTab('tables')}
              >
                Data Tables
              </button>
            )}
            {/* {hasTraceability && (
              <button 
                className={`ct-tab ${currentTab === 'traceability' ? 'active' : ''}`}
                onClick={() => setActiveTab('traceability')}
              >
                Traceability View
              </button>
            )} */}
          </>
        )}
      </div>

      {/* Dashboard Search/Filter Bar for PDF/Word Documents */}
      {!isTabular && currentTab === 'overview' && data.analytics && (
        <div className="search-bar-container glass-panel">
          <Search className="search-icon" size={16} />
          <input 
            type="text" 
            placeholder="Filter metrics, categories, or key-value pairs..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="dashboard-search-input"
          />
        </div>
      )}

      <div className="dashboard-content">
        {/* Spreadsheets Ingestion View */}
        {(currentTab === 'overview' || currentTab === 'preview') && data.tabular && (
          <TabularView tabularData={data.tabular} activeSubTab={currentTab} />
        )}

        {/* Overview Analytics for PDF / Text Documents */}
        {currentTab === 'overview' && !data.tabular && (
          <div className="document-analytics-overview animate-fade-in">
            {/* KPI Cards Section or Qualitative Document Outline */}
            {kpiMetrics.length > 0 ? (
              <div className="kpi-cards-section">
                <h3 className="section-title">Key Performance Indicators</h3>
                <StatsCards metrics={kpiMetrics} />
              </div>
            ) : (
              <div className="qualitative-outline-section glass-panel" style={{ padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)', background: 'var(--bg-card)' }}>
                <h3 className="section-title" style={{ marginTop: 0 }}>📘 Qualitative Document Outline</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '16px' }}>
                  This document contains qualitative syllabus / curriculum topics and key concept highlights instead of numeric metrics.
                </p>
                {data.analytics?.qualitative_sections && data.analytics.qualitative_sections.length > 0 ? (
                  <div className="qualitative-topics-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                    {data.analytics.qualitative_sections[0].main_topics.map((topic, tIdx) => (
                      <div key={tIdx} className="topic-card" style={{ padding: '14px', borderRadius: '8px', background: 'rgba(106, 27, 154, 0.04)', border: '1px solid rgba(106, 27, 154, 0.12)' }}>
                        <h4 style={{ margin: '0 0 8px 0', color: 'var(--brand-purple)', fontSize: '0.95rem' }}>{topic.title}</h4>
                        {topic.description && <p style={{ margin: '0 0 10px 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{topic.description}</p>}
                        {topic.subtopics && topic.subtopics.length > 0 && (
                          <div className="subtopic-badges" style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                            {topic.subtopics.map((sub, sIdx) => (
                              <span key={sIdx} style={{ fontSize: '0.75rem', padding: '3px 8px', borderRadius: '12px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', color: 'var(--text-primary)' }}>
                                {sub}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>Structured topics extracted below in Key-Value attributes and Executive Summary.</p>
                )}
              </div>
            )}

            {/* Metrics Charting Section */}
            {metricsCharts.length > 0 && (
              <div className="metrics-charts-section">
                <ChartPanel charts={metricsCharts} />
              </div>
            )}

            {/* Key-Value Attributes Grid */}
            <div className="kv-grid-section">
              <h3 className="section-title">Key-Value Attributes</h3>
              {sortedKeyValuePairs.length === 0 ? (
                <div className="empty-state-card glass-panel">
                  <p>No key-value attributes match your search filter.</p>
                </div>
              ) : (
                <div className="kv-table-container glass-panel">
                  <table className="kv-table">
                    <thead>
                      <tr>
                        <th onClick={() => handleSort('key_name')} className="sortable-header">
                          Attribute
                          <ArrowUpDown size={14} className="sort-icon" />
                        </th>
                        <th onClick={() => handleSort('value')} className="sortable-header">
                          Value
                          <ArrowUpDown size={14} className="sort-icon" />
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedKeyValuePairs.map((kv, idx) => (
                        <tr key={idx}>
                          <td className="kv-key">{kv.key_name}</td>
                          <td className="kv-val">{kv.value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Extracted Tables View */}
        {currentTab === 'tables' && (
          <div className="extracted-tables-section animate-fade-in">
            {data.analytics?.tables && data.analytics.tables.length > 0 ? (
              <>
                {data.analytics.tables.length > 1 && (
                  <div className="table-selector-wrapper glass-panel">
                    <label htmlFor="table-select" className="table-select-label">Select Table View: </label>
                    <select 
                      id="table-select" 
                      value={selectedTableIndex} 
                      onChange={(e) => setSelectedTableIndex(parseInt(e.target.value))}
                      className="table-selector-dropdown"
                    >
                      {data.analytics.tables.map((t, idx) => (
                        <option key={idx} value={idx}>
                          {t.table_title || `Table ${idx + 1}`}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                
                {(() => {
                  const tbl = data.analytics.tables[selectedTableIndex] || data.analytics.tables[0];
                  const cols = tbl.headers.map(h => ({ name: h, dtype: 'string' }));
                  return (
                    <DataTablePreview 
                      columns={cols} 
                      previewRows={tbl.rows} 
                      totalRowCount={tbl.rows.length} 
                    />
                  );
                })()}
              </>
            ) : data.tabular ? (
              <DataTablePreview 
                columns={data.tabular.columns} 
                previewRows={data.tabular.preview_rows} 
                totalRowCount={data.tabular.row_count} 
              />
            ) : (
              <div className="empty-state-card glass-panel" style={{ padding: '20px', textAlign: 'center' }}>
                <p>No structured data tables were detected in this document.</p>
              </div>
            )}
          </div>
        )}

        {/* Text Summaries and Keywords Cloud */}
        {(currentTab === 'summary' || currentTab === 'keywords') && (
          <TextView 
            textData={data.text || { 
              summary: data.executive_summary || "Executive summary generated successfully.",
              kpis: data.kpis || [],
              keywords: data.keywords || (data.text && data.text.keywords) || [],
              word_count: data.raw_markdown ? data.raw_markdown.split(/\s+/).length : 100,
              page_count: data.page_count || 1,
              paragraph_count: data.raw_markdown ? data.raw_markdown.split('\n\n').length : 1
            }} 
            activeSubTab={currentTab} 
            processingTime={data.processing_time}
            rawMarkdown={data.raw_markdown}
            fileName={data.file_name}
          />
        )}

        {/* Spatial Traceability Canvas (Commented out for future work)
        {currentTab === 'traceability' && (
          <TraceabilityViewer fileName={data.file_name} initialAnalytics={data.analytics} />
        )}
        */}
      </div>
    </div>
  );
};

export default Dashboard;
