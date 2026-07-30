import React, { useState, useMemo } from 'react';
import { Table, ChevronLeft, ChevronRight, ArrowUpDown } from 'lucide-react';
import { DEFAULT_PAGE_SIZE } from '../utils/constants';
import './DataTablePreview.css';

const ROWS_PER_PAGE = DEFAULT_PAGE_SIZE;

const DataTablePreview = ({ columns, previewRows, totalRowCount }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [sortColIndex, setSortColIndex] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');

  const effectiveRows = previewRows || [];

  const effectiveColumns = useMemo(() => {
    if (columns && columns.length > 0) {
      return columns.map(c => typeof c === 'string' ? { name: c, dtype: 'string' } : (c.name ? c : { name: String(c), dtype: 'string' }));
    }
    if (effectiveRows.length > 0) {
      const firstRow = effectiveRows[0];
      if (typeof firstRow === 'object' && !Array.isArray(firstRow)) {
        return Object.keys(firstRow).map(k => ({ name: k, dtype: 'string' }));
      }
    }
    return [];
  }, [columns, effectiveRows]);

  if (!effectiveRows || effectiveRows.length === 0 || effectiveColumns.length === 0) {
    return <div className="no-data">No preview rows available.</div>;
  }

  const handleHeaderClick = (colIdx) => {
    if (sortColIndex === colIdx) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColIndex(colIdx);
      setSortDirection('asc');
    }
  };

  const sortedRows = useMemo(() => {
    if (sortColIndex === null) return previewRows;
    return [...previewRows].sort((a, b) => {
      let valA = Array.isArray(a) ? a[sortColIndex] : a;
      let valB = Array.isArray(b) ? b[sortColIndex] : b;

      if (valA === null || valA === undefined) valA = '';
      if (valB === null || valB === undefined) valB = '';

      if (typeof valA === 'number' && typeof valB === 'number') {
        return sortDirection === 'asc' ? valA - valB : valB - valA;
      }

      valA = String(valA).toLowerCase();
      valB = String(valB).toLowerCase();

      if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [previewRows, sortColIndex, sortDirection]);

  const totalPages = Math.ceil(sortedRows.length / ROWS_PER_PAGE);
  const startIndex = (currentPage - 1) * ROWS_PER_PAGE;
  const paginatedRows = sortedRows.slice(startIndex, startIndex + ROWS_PER_PAGE);

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage(currentPage - 1);
  };

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage(currentPage + 1);
  };

  return (
    <div 
      className="table-preview-container glass-panel"
      role="region"
      aria-label="Extracted Tabular Data Preview"
    >
      <div className="table-header">
        <div className="table-title-wrapper">
          <Table size={20} color="var(--brand-purple)" />
          <h4>Data Preview <span className="subtitle">(showing first {previewRows.length} of {totalRowCount.toLocaleString()} rows)</span></h4>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="data-table" role="grid" aria-label="Extracted Data Table">
          <thead>
            <tr role="row">
              {effectiveColumns.map((col, idx) => (
                <th 
                  key={idx} 
                  onClick={() => handleHeaderClick(idx)}
                  className="sortable-header"
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  title="Click to sort by column"
                >
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    {col.name}
                    <ArrowUpDown size={12} style={{ opacity: sortColIndex === idx ? 1 : 0.4 }} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginatedRows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                {(() => {
                  const cells = Array.isArray(row) 
                    ? row 
                    : (typeof row === 'object' && row !== null 
                        ? effectiveColumns.map(c => row[c.name] ?? row[c.key])
                        : [row]);
                  return cells.map((cell, cellIdx) => {
                    let displayVal = cell;
                    if (cell === null || cell === undefined) {
                      displayVal = <span className="null-val">NaN</span>;
                    } else if (typeof cell === 'number') {
                      displayVal = cell.toLocaleString(undefined, { maximumFractionDigits: 2 });
                    } else if (typeof cell === 'boolean') {
                      displayVal = cell ? 'True' : 'False';
                    }
                    return <td key={cellIdx}>{displayVal}</td>;
                  });
                })()}
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

export default React.memo(DataTablePreview);
