import React, { useState } from 'react';
import TabularView from './TabularView';
import TextView from './TextView';
import { ArrowLeft, Database, FileText, BarChart3 } from 'lucide-react';
import './Dashboard.css';

const Dashboard = ({ data, onReset }) => {
  const [activeTab, setActiveTab] = useState('overview');

  if (!data) return null;

  const isTabular = data.data_category === 'tabular';
  const isMixed = data.data_category === 'mixed';
  const isTextOnly = data.data_category === 'text';

  // Determine valid tab based on data category
  const getValidTab = () => {
    if (isTabular) {
      return (activeTab === 'overview' || activeTab === 'preview') ? activeTab : 'overview';
    }
    if (isMixed) {
      return ['overview', 'preview', 'summary', 'keywords'].includes(activeTab) ? activeTab : 'overview';
    }
    return (activeTab === 'summary' || activeTab === 'keywords') ? activeTab : 'summary';
  };

  const currentTab = getValidTab();

  return (
    <div className="dashboard-container animate-fade-in">
      <div className="dashboard-header">
        <button className="back-button btn-white" onClick={onReset}>
          <ArrowLeft size={16} />
          Upload Another File
        </button>
        
        <div className="file-info">
          <span className="file-icon-wrapper">
            {isMixed ? (
              <BarChart3 size={18} color="var(--brand-purple)" />
            ) : isTabular ? (
              <Database size={18} color="var(--color-sales-strategy)" />
            ) : (
              <FileText size={18} color="var(--color-ai-sales)" />
            )}
          </span>
          <span className="file-name">{data.file_name}</span>
          <span className={`badge-type ${isTabular || isMixed ? 'badge-tabular' : 'badge-text'}`}>
            {data.file_type.toUpperCase()}
          </span>
          {isMixed && (
            <span className="badge-type badge-mixed">
              Tables Detected
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

        {isMixed && (
          <>
            <button 
              className={`ct-tab ${currentTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              Table Analysis
            </button>
            <button 
              className={`ct-tab ${currentTab === 'preview' ? 'active' : ''}`}
              onClick={() => setActiveTab('preview')}
            >
              Raw Data Preview
            </button>
            <button 
              className={`ct-tab ${currentTab === 'summary' ? 'active' : ''}`}
              onClick={() => setActiveTab('summary')}
            >
              Text Summary
            </button>
            <button 
              className={`ct-tab ${currentTab === 'keywords' ? 'active' : ''}`}
              onClick={() => setActiveTab('keywords')}
            >
              Keyword Analysis
            </button>
          </>
        )}

        {isTextOnly && (
          <>
            <button 
              className={`ct-tab ${currentTab === 'summary' ? 'active' : ''}`}
              onClick={() => setActiveTab('summary')}
            >
              AI Document Summary
            </button>
            <button 
              className={`ct-tab ${currentTab === 'keywords' ? 'active' : ''}`}
              onClick={() => setActiveTab('keywords')}
            >
              Keyword Analysis
            </button>
          </>
        )}
      </div>

      <div className="dashboard-content">
        {(isTabular || isMixed) && data.tabular && (currentTab === 'overview' || currentTab === 'preview') && (
          <TabularView tabularData={data.tabular} activeSubTab={currentTab} />
        )}

        {(isTextOnly || isMixed) && data.text && (currentTab === 'summary' || currentTab === 'keywords') && (
          <TextView textData={data.text} activeSubTab={currentTab} />
        )}
      </div>
    </div>
  );
};

export default Dashboard;
