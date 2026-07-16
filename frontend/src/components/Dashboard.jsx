import React from 'react';
import TabularView from './TabularView';
import TextView from './TextView';
import { ArrowLeft } from 'lucide-react';
import './Dashboard.css';

const Dashboard = ({ data, onReset }) => {
  if (!data) return null;

  return (
    <div className="dashboard-container animate-fade-in">
      <div className="dashboard-header">
        <button className="back-button glass-panel" onClick={onReset}>
          <ArrowLeft size={16} />
          Upload Another File
        </button>
        <div className="file-info glass-panel">
          <span className="file-name">{data.file_name}</span>
          <span className="badge">{data.data_category.toUpperCase()}</span>
        </div>
      </div>

      <div className="dashboard-content">
        {data.data_category === 'tabular' && data.tabular && (
          <TabularView tabularData={data.tabular} />
        )}

        {data.data_category === 'text' && data.text && (
          <TextView textData={data.text} />
        )}
      </div>
    </div>
  );
};

export default Dashboard;
