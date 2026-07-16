import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  LineChart, Line
} from 'recharts';
import './TabularView.css';

const TabularView = ({ tabularData }) => {
  const { row_count, col_count, numeric_summary, preview_rows, columns, charts } = tabularData;

  // Custom Tooltip for charts
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="chart-tooltip glass-panel">
          <p className="label">{`${label} : ${payload[0].value}`}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="tabular-view">
      
      {/* Top Level Metrics */}
      <div className="metrics-grid">
        <div className="metric-card glass-panel">
          <span className="metric-title">Total Rows</span>
          <span className="metric-value">{row_count.toLocaleString()}</span>
        </div>
        <div className="metric-card glass-panel">
          <span className="metric-title">Total Columns</span>
          <span className="metric-value">{col_count}</span>
        </div>
        <div className="metric-card glass-panel">
          <span className="metric-title">Numeric Columns</span>
          <span className="metric-value">{Object.keys(numeric_summary || {}).length}</span>
        </div>
      </div>

      {/* Auto-generated Charts */}
      {charts && charts.length > 0 && (
        <div className="charts-section">
          <h3 className="section-title">Data Visualizations</h3>
          <div className="charts-grid">
            {charts.map((chart, idx) => (
              <div key={idx} className="chart-container glass-panel">
                <h4>{chart.title}</h4>
                <div className="chart-wrapper">
                  <ResponsiveContainer width="100%" height={300}>
                    {chart.type === 'bar' ? (
                      <BarChart data={chart.data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                        <XAxis dataKey={chart.x_key} stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                        <YAxis stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                        <RechartsTooltip content={<CustomTooltip />} />
                        <Bar dataKey={chart.y_key} fill="var(--accent-color)" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    ) : (
                      <LineChart data={chart.data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                        <XAxis dataKey={chart.x_key} stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                        <YAxis stroke="var(--text-secondary)" tick={{fill: 'var(--text-secondary)'}} />
                        <RechartsTooltip content={<CustomTooltip />} />
                        <Line type="monotone" dataKey={chart.y_key} stroke="var(--accent-color)" strokeWidth={3} dot={{r: 4, fill: "var(--bg-dark)", strokeWidth: 2}} />
                      </LineChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data Preview Table */}
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

    </div>
  );
};

export default TabularView;
