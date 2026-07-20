import React, { useState } from 'react';
import { Table, ChevronLeft, ChevronRight } from 'lucide-react';
import './DataTablePreview.css';

const ROWS_PER_PAGE = 10;

const DataTablePreview = ({ columns, previewRows, totalRowCount }) => {
  const [currentPage, setCurrentPage] = useState(1);

  if (!columns || !previewRows || previewRows.length === 0) {
    return <div className="no-data">No preview rows available.</div>;
  }

  const totalPages = Math.ceil(previewRows.length / ROWS_PER_PAGE);
  const startIndex = (currentPage - 1) * ROWS_PER_PAGE;
  const paginatedRows = previewRows.slice(startIndex, startIndex + ROWS_PER_PAGE);

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage(currentPage - 1);
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage(currentPage + 1);
  };

  return (
    <div className="table-preview-container glass-panel">
      <div className="table-header">
        <div className="table-title-wrapper">
          <Table size={20} color="var(--brand-purple)" />
          <h4>Data Preview <span className="subtitle">(showing first {previewRows.length} of {totalRowCount.toLocaleString()} rows)</span></h4>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((col, idx) => (
                <th key={idx}>{col.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedRows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {Array.isArray(row) ? row.map((cell, cellIdx) => {
                  let displayVal = cell;
                  if (cell === null || cell === undefined) {
                    displayVal = <span className="null-val">NaN</span>;
                  } else if (typeof cell === 'number') {
                    displayVal = cell.toLocaleString(undefined, { maximumFractionDigits: 2 });
                  } else if (typeof cell === 'boolean') {
                    displayVal = cell ? 'True' : 'False';
                  }
                  return <td key={cellIdx}>{displayVal}</td>;
                }) : <td>{String(row)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button 
            className="page-link" 
            onClick={handlePrevPage} 
            disabled={currentPage === 1}
            title="Previous Page"
          >
            <ChevronLeft size={16} />
          </button>
          
          <div className="page-numbers">
            {Array.from({ length: totalPages }, (_, idx) => idx + 1)
              .filter(p => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
              .map((page, idx, arr) => {
                const prev = arr[idx - 1];
                const showEllipsis = prev && page - prev > 1;
                return (
                  <React.Fragment key={page}>
                    {showEllipsis && <span className="ellipsis">...</span>}
                    <button 
                      className={`page-link ${currentPage === page ? 'active' : ''}`}
                      onClick={() => setCurrentPage(page)}
                    >
                      {page}
                    </button>
                  </React.Fragment>
                );
              })}
          </div>

          <button 
            className="page-link" 
            onClick={handleNextPage} 
            disabled={currentPage === totalPages}
            title="Next Page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
};

export default DataTablePreview;
