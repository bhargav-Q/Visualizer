import React from 'react';
import './DataTable.css';

const DataTable = ({ columns, preview_rows }) => {
  return (
    <div className="data-table-section glass-panel">
      <h3 className="section-title">Data Preview (Top 100 Rows)</h3>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col, idx) => (
                <th key={idx}>
                  <div className="th-content">
                    <span className="col-name">{col.name}</span>
                    <span className="col-type">{col.dtype}</span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview_rows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {row.map((cell, cellIdx) => (
                  <td key={cellIdx}>{cell !== null ? String(cell) : <span className="null-val">null</span>}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DataTable;
