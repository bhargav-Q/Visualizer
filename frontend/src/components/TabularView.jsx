import React, { useState } from 'react';
import StatsCards from './StatsCards';
import ChartPanel from './ChartPanel';
import DataTablePreview from './DataTablePreview';
import './TabularView.css';

const TabularView = ({ tabularData, activeSubTab }) => {
  const [activeSheetIndex, setActiveSheetIndex] = useState(0);
  
  if (!tabularData) return null;

  const hasMultipleSheets = tabularData.sheets && tabularData.sheets.length > 1;

  // Determine the active data source — per-sheet or top-level
  const getActiveData = () => {
    if (hasMultipleSheets) {
      const sheet = tabularData.sheets[activeSheetIndex];
      return {
        row_count: sheet.row_count || 0,
        col_count: sheet.col_count || 0,
        numeric_summary: sheet.numeric_summary || {},
        categorical_summary: sheet.categorical_summary || {},
        columns: sheet.columns || [],
        preview_rows: sheet.preview_rows || [],
        charts: sheet.charts || [],
        sheet_name: sheet.sheet_name
      };
    }
    return {
      row_count: tabularData.row_count || 0,
      col_count: tabularData.col_count || 0,
      numeric_summary: tabularData.numeric_summary || {},
      categorical_summary: tabularData.categorical_summary || {},
      columns: tabularData.columns || [],
      preview_rows: tabularData.preview_rows || [],
      charts: tabularData.charts || [],
      sheet_name: null
    };
  };

  const activeData = getActiveData();

  const metrics = [
    { title: "Total Rows", value: activeData.row_count?.toLocaleString() || 0 },
    { title: "Total Columns", value: activeData.col_count },
    { title: "Numeric Columns", value: Object.keys(activeData.numeric_summary || {}).length }
  ];

  // Add sheet count metric when multi-sheet
  if (hasMultipleSheets) {
    metrics.push({ title: "Worksheets", value: tabularData.sheets.length });
  }

  return (
    <div className="tabular-view">
      {/* Worksheet Navigation Tabs */}
      {hasMultipleSheets && (
        <div className="worksheet-tabs-bar">
          <div className="worksheet-tabs-label">Worksheets</div>
          <div className="worksheet-tabs-scroll">
            {tabularData.sheets.map((sheet, idx) => (
              <button
                key={idx}
                className={`worksheet-tab ${idx === activeSheetIndex ? 'active' : ''}`}
                onClick={() => setActiveSheetIndex(idx)}
                title={sheet.sheet_name}
              >
                <span className="worksheet-tab-icon">
                  {idx === activeSheetIndex ? '◆' : '◇'}
                </span>
                <span className="worksheet-tab-name">{sheet.sheet_name}</span>
                <span className="worksheet-tab-badge">{sheet.row_count} rows</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {activeSubTab === 'overview' ? (
        <>
          <StatsCards metrics={metrics} />
          <ChartPanel charts={activeData.charts} />
        </>
      ) : (
        <DataTablePreview 
          columns={activeData.columns} 
          previewRows={activeData.preview_rows} 
          totalRowCount={activeData.row_count} 
        />
      )}
    </div>
  );
};

export default TabularView;
