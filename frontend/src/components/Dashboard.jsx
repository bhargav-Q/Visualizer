import React, { useState } from 'react';
import TabularView from './TabularView';
import TextView from './TextView';
import { ArrowLeft, Database, FileText } from 'lucide-react';
import './Dashboard.css';

const Dashboard = ({ data, onReset }) => {
  const [activeTab, setActiveTab] = useState('overview');

  if (!data) return null;

  const isTabular = data.data_category === 'tabular';
  
  // Normalize active tab based on data category
  const currentTab = isTabular 
    ? (activeTab === 'overview' || activeTab === 'preview' ? activeTab : 'overview')
    : (activeTab === 'summary' || activeTab === 'keywords' ? activeTab : 'summary');

  return (
    <div className="dashboard-container animate-fade-in">
      <div className="dashboard-header">
        <button className="back-button btn-white" onClick={onReset}>
          <ArrowLeft size={16} />
          Upload Another File
        </button>
        
        <div className="file-info">
          <span className="file-icon-wrapper">
            {isTabular ? <Database size={18} color="var(--color-sales-strategy)" /> : <FileText size={18} color="var(--color-ai-sales)" />}
          </span>
          <span className="file-name">{data.file_name}</span>
          <span className={`badge-type ${isTabular ? 'badge-tabular' : 'badge-text'}`}>
            {data.file_type.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="content-type-tabs">
        {isTabular ? (
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
        ) : (
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
        {isTabular && data.tabular && (
          <TabularView tabularData={data.tabular} activeSubTab={currentTab} />
        )}

        {!isTabular && data.text && (
          <TextView textData={data.text} activeSubTab={currentTab} />
        )}
      </div>
    </div>
  );
};

export default Dashboard;
