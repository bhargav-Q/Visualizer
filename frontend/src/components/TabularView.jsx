import React from 'react';
import StatsCards from './StatsCards';
import ChartPanel from './ChartPanel';
import DataTable from './DataTable';
import './TabularView.css';

const TabularView = ({ tabularData }) => {
  const { row_count, col_count, numeric_summary, preview_rows, columns, charts } = tabularData;

  const metrics = [
    { title: "Total Rows", value: row_count.toLocaleString() },
    { title: "Total Columns", value: col_count },
    { title: "Numeric Columns", value: Object.keys(numeric_summary || {}).length }
  ];

  return (
    <div className="tabular-view">
      <StatsCards metrics={metrics} />
      <ChartPanel charts={charts} />
      <DataTable columns={columns} preview_rows={preview_rows} />
    </div>
  );
};

export default TabularView;
