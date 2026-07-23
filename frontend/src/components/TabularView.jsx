import React from 'react';
import StatsCards from './StatsCards';
import ChartPanel from './ChartPanel';
import DataDetailsAccordion from './DataDetailsAccordion';
import DataTablePreview from './DataTablePreview';
import './TabularView.css';

const TabularView = ({ tabularData, activeSubTab }) => {
  if (!tabularData) return null;
  const { row_count = 0, col_count = 0, numeric_summary, categorical_summary, columns, preview_rows, charts } = tabularData;

  const metrics = [
    { title: "Total Rows", value: row_count?.toLocaleString() || 0 },
    { title: "Total Columns", value: col_count },
    { title: "Numeric Columns", value: Object.keys(numeric_summary || {}).length }
  ];

  return (
    <div className="tabular-view">
      {activeSubTab === 'overview' ? (
        <>
          <StatsCards metrics={metrics} />
          <ChartPanel charts={charts} />
          <DataDetailsAccordion 
            columns={columns} 
            numericSummary={numeric_summary} 
            categoricalSummary={categorical_summary} 
          />
        </>
      ) : (
        <DataTablePreview 
          columns={columns} 
          previewRows={preview_rows} 
          totalRowCount={row_count} 
        />
      )}
    </div>
  );
};

export default TabularView;
