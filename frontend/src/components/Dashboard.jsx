import React, { useState } from 'react';
import TabularView from './TabularView';
import TextView from './TextView';
import TraceabilityViewer from './TraceabilityViewer';
import StatsCards from './StatsCards';
import ChartPanel from './ChartPanel';
import DataTablePreview from './DataTablePreview';
import { ArrowLeft, Database, FileText, BarChart3, Search, ArrowUpDown, Download, Copy, Check } from 'lucide-react';
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
  const hasTraceability = data.file_type === 'pdf' && data.analytics;

  // Determine valid tab based on data category and content
  const getValidTab = () => {
    if (isTabular) {
      return (activeTab === 'overview' || activeTab === 'preview') ? activeTab : 'overview';
    }
    const validTabs = ['overview', 'summary', 'keywords'];
    if (data.analytics && data.analytics.tables && data.analytics.tables.length > 0) {
      validTabs.push('tables');
    }
    if (hasTraceability) {
      validTabs.push('traceability');
    }
    return validTabs.includes(activeTab) ? activeTab : 'overview';
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
  const filteredKeyValuePairs = (data.analytics?.key_value_pairs || []).filter(kv => {
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
  const kpiMetrics = filteredMetrics.map(m => ({
    title: m.category,
    value: formatMetricValue(m.metric_value, m.unit)
  }));

  // Recharts Metrics comparison chart structure
  const metricsCharts = filteredMetrics.length > 0 ? [{
    title: "Metrics Comparison",
    type: "bar",
    x_key: "category",
    y_key: "value",
    data: filteredMetrics.map(m => ({
      category: m.category,
      value: m.metric_value
    }))
  }] : [];

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
            {data.file_type.toUpperCase()}
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

      {/* Navigation Tabs */}
      <div className="content-type-tabs">
        {isTabular && (
          <>
            <button 
              className={`ct-tab ${currentTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Dashboard Overview
            </button>
            <button 
              className={`ct-tab ${currentTab === 'preview' ? 'active' : ''}`}
              onClick={() => setActiveTab('preview')}
            >
              Raw Data Preview
            </button>
          </>
        )}

        {!isTabular && (
          <>
            <button 
              className={`ct-tab ${currentTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Overview Analytics
            </button>
            {data.analytics && data.analytics.tables && data.analytics.tables.length > 0 && (
              <button 
                className={`ct-tab ${currentTab === 'tables' ? 'active' : ''}`}
                onClick={() => setActiveTab('tables')}
              >
                Data Tables
              </button>
            )}
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
            {hasTraceability && (
              <button 
                className={`ct-tab ${currentTab === 'traceability' ? 'active' : ''}`}
                onClick={() => setActiveTab('traceability')}
              >
                Traceability View
              </button>
            )}
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
        {isTabular && data.tabular && (
          <TabularView tabularData={data.tabular} activeSubTab={currentTab} />
        )}

        {/* Overview Analytics for Documents (KPI cards, charts, attributes grid) */}
        {!isTabular && currentTab === 'overview' && data.analytics && (
          <div className="document-analytics-overview animate-fade-in">
            {/* KPI Cards Section */}
            {kpiMetrics.length > 0 && (
              <div className="kpi-cards-section">
                <h3 className="section-title">Key Performance Indicators</h3>
                <StatsCards metrics={kpiMetrics} />
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

        {/* Extracted Tables for Documents */}
        {!isTabular && currentTab === 'tables' && data.analytics?.tables && data.analytics.tables.length > 0 && (
          <div className="extracted-tables-section animate-fade-in">
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
          </div>
        )}

        {/* Text summaries and keywords cloud */}
        {!isTabular && data.text && (currentTab === 'summary' || currentTab === 'keywords') && (
          <TextView textData={data.text} activeSubTab={currentTab} processingTime={data.processing_time} />
        )}

        {/* Bounding box traceback canvas overlay */}
        {!isTabular && currentTab === 'traceability' && hasTraceability && (
          <TraceabilityViewer fileName={data.file_name} initialAnalytics={data.analytics} />
        )}
      </div>
    </div>
  );
};

export default Dashboard;
