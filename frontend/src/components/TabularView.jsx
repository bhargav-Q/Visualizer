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
      const safeIndex = Math.min(activeSheetIndex, (tabularData.sheets?.length || 1) - 1);
      const sheet = tabularData.sheets[safeIndex] || {};
      return {
        row_count: sheet.row_count ?? tabularData.row_count ?? 0,
        col_count: sheet.col_count ?? (sheet.columns ? sheet.columns.length : tabularData.col_count ?? 0),
        columns: sheet.columns || tabularData.columns || [],
        preview_rows: sheet.preview_rows || sheet.data_preview || tabularData.preview_rows || tabularData.data_preview || [],
        charts: (sheet.charts && sheet.charts.length > 0) ? sheet.charts : (tabularData.charts || []),
        kpis: sheet.kpis || tabularData.kpis || [],
        sheet_name: sheet.sheet_name || null
      };
    }
    return {
      row_count: tabularData.row_count || tabularData.total_rows || 0,
      col_count: tabularData.col_count || tabularData.total_columns || (tabularData.columns ? tabularData.columns.length : 0),
      columns: tabularData.columns || [],
      preview_rows: tabularData.preview_rows || tabularData.data_preview || [],
      charts: tabularData.charts || [],
      kpis: tabularData.kpis || [],
      sheet_name: null
    };
  };

  const activeData = getActiveData();

  const metrics = (activeData.kpis && activeData.kpis.length > 0)
    ? activeData.kpis.map(k => ({ title: k.label, value: k.value }))
    : [
        { title: "Total Rows", value: activeData.row_count ? activeData.row_count.toLocaleString() : "0" },
        { title: "Total Columns", value: activeData.col_count || (activeData.columns ? activeData.columns.length : 0) },
        { title: "Numeric Columns", value: activeData.columns ? activeData.columns.filter(c => {
            const dt = typeof c === 'object' ? (c.dtype || '') : '';
            return dt.includes('int') || dt.includes('float') || dt.includes('number');
          }).length : 0 }
      ];

  // Add sheet count metric when multi-sheet
  if (hasMultipleSheets && !metrics.some(m => m.title === "Worksheets")) {
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
          totalRowCount={activeData.row_count || activeData.preview_rows.length} 
        />
      )}
    </div>
  );
};

export default TabularView;
