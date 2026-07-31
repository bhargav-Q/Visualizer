import React, { useState, useMemo } from 'react';
import { Maximize2, Minimize2, BarChart2, TrendingUp, PieChart as PieIcon, Activity, Download, FileText } from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, Legend
} from 'recharts';
import { PIE_COLORS } from '../utils/constants';
import './ChartPanel.css';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const dataName = payload[0].name || label;
    const value = payload[0].value;
    const formattedVal = (typeof value === 'number') ? value.toLocaleString() : (value ?? 'N/A');
    return (
      <div className="chart-tooltip">
        <p className="label">{dataName}: <strong>{formattedVal}</strong></p>
      </div>
    );
  }
  return null;
};

const SingleChartCard = ({ chart, idx }) => {
  const [overrideType, setOverrideType] = useState(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // Normalize chart data schema using useMemo for performance < 100ms
  const { normalizedData, xKey, yKey, defaultType } = useMemo(() => {
    let data = [];
    let x_key = chart.x_axis_label || chart.x_key || 'Category';
    let y_key = chart.y_axis_label || chart.y_key || 'Value';

    if (Array.isArray(chart.x_data) && Array.isArray(chart.y_data)) {
      data = chart.x_data.map((xVal, i) => ({
        [x_key]: xVal,
        [y_key]: chart.y_data[i] !== undefined ? chart.y_data[i] : 0
      }));
    } else if (Array.isArray(chart.data)) {
      data = chart.data;
      x_key = chart.x_key || x_key;
      y_key = chart.y_key || y_key;
    }

    const type = (chart.chart_type || chart.type || 'bar').toLowerCase();
    return { normalizedData: data, xKey: x_key, yKey: y_key, defaultType: type };
  }, [chart]);

  const activeType = overrideType || defaultType;

  const handleExportCSV = () => {
    if (!normalizedData || normalizedData.length === 0) return;
    const headers = [xKey, yKey].join(",");
    const rows = normalizedData.map(d => `"${d[xKey]}",${d[yKey]}`).join("\n");
    const csvContent = "data:text/csv;charset=utf-8," + [headers, rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${(chart.title || 'chart').replace(/\s+/g, '_')}_data.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const pageRangeTag = chart.page_range || chart.page_number;

  // Smart XAxis configuration responsive to expanded/maximized vs minimized card state
  const xAxisConfig = useMemo(() => {
    const count = normalizedData.length;

    if (!isExpanded) {
      // Minimized Card View: Auto-sample overlapping labels to keep card clean & uncluttered
      if (count > 12) {
        return {
          interval: 'preserveStartEnd',
          angle: -30,
          textAnchor: 'end',
          height: 42,
          tick: { fill: '#94a3b8', fontSize: 10 }
        };
      } else if (count > 5) {
        return {
          interval: 'preserveStartEnd',
          angle: -25,
          textAnchor: 'end',
          height: 38,
          tick: { fill: '#94a3b8', fontSize: 10 }
        };
      }
      return {
        interval: 0,
        height: 30,
        tick: { fill: '#94a3b8', fontSize: 11 }
      };
    } else {
      // Maximized Card View: Unhide 100% of labels (interval=0) with full room to display
      if (count > 12) {
        return {
          interval: 0,
          angle: -45,
          textAnchor: 'end',
          height: 75,
          tick: { fill: '#94a3b8', fontSize: 9.5 }
        };
      } else if (count > 5) {
        return {
          interval: 0,
          angle: -30,
          textAnchor: 'end',
          height: 50,
          tick: { fill: '#94a3b8', fontSize: 10 }
        };
      }
      return {
        interval: 0,
        height: 30,
        tick: { fill: '#94a3b8', fontSize: 11 }
      };
    }
  }, [normalizedData.length, isExpanded]);

  const chartMargin = useMemo(() => ({
    top: 20,
    right: 25,
    left: 10,
    bottom: xAxisConfig.height + 5
  }), [xAxisConfig.height]);

  return (
    <div 
      className={`chart-container glass-panel ${isExpanded ? 'expanded' : ''}`}
      role="region"
      aria-label={`Chart visualization: ${chart.title || 'Data Analytics'}`}
    >
      <div className="chart-header">
        <div className="chart-title-group">
          <h4>{chart.title || 'Data Insights'}</h4>
          <span className="chart-type-badge">{activeType.toUpperCase()}</span>
          {pageRangeTag && (
            <span className="chart-page-badge" title={`Source document location: ${pageRangeTag}`}>
              <FileText size={11} style={{ marginRight: '4px' }} />
              {String(pageRangeTag).toLowerCase().includes('page') ? pageRangeTag : `Page ${pageRangeTag}`}
            </span>
          )}
        </div>

        <div className="chart-controls-group">
          {/* ARIA Accessible Chart Type Switcher */}
          <div 
            className="chart-type-switcher" 
            role="tablist" 
            aria-label="Select Chart Display Type"
          >
            <button 
              role="tab"
              aria-selected={activeType === 'bar'}
              aria-label="Display as Bar Chart"
              className={`switcher-btn ${activeType === 'bar' ? 'active' : ''}`}
              onClick={() => setOverrideType('bar')}
              title="Bar Chart"
            >
              <BarChart2 size={13} />
            </button>
            <button 
              role="tab"
              aria-selected={activeType === 'line'}
              aria-label="Display as Line Chart"
              className={`switcher-btn ${activeType === 'line' ? 'active' : ''}`}
              onClick={() => setOverrideType('line')}
              title="Line Chart"
            >
              <TrendingUp size={13} />
            </button>
            <button 
              role="tab"
              aria-selected={activeType === 'area'}
              aria-label="Display as Area Chart"
              className={`switcher-btn ${activeType === 'area' ? 'active' : ''}`}
              onClick={() => setOverrideType('area')}
              title="Area Chart"
            >
              <Activity size={13} />
            </button>
            <button 
              role="tab"
              aria-selected={activeType === 'pie'}
              aria-label="Display as Pie Chart"
              className={`switcher-btn ${activeType === 'pie' ? 'active' : ''}`}
              onClick={() => setOverrideType('pie')}
              title="Pie Chart"
            >
              <PieIcon size={13} />
            </button>
          </div>

          <button 
            className="focus-toggle-btn"
            onClick={handleExportCSV}
            title="Export chart data to CSV"
            aria-label="Export chart data to CSV"
          >
            <Download size={14} />
          </button>

          <button 
            className="focus-toggle-btn"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? "Collapse view" : "Expand view"}
            aria-label={isExpanded ? "Collapse chart view" : "Expand chart view"}
          >
            {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      <div className="chart-wrapper">
        <ResponsiveContainer width="99%" height={isExpanded ? 450 : 320 + (xAxisConfig.height > 40 ? 30 : 0)} minHeight={280}>
          {activeType === 'bar' ? (
            <BarChart data={normalizedData} margin={chartMargin}>
              <defs>
                <linearGradient id={`barGrad-${idx}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.9}/>
                  <stop offset="95%" stopColor="#ec4899" stopOpacity={0.7}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey={xKey} stroke="#94a3b8" {...xAxisConfig} />
              <YAxis stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 11}} />
              <RechartsTooltip content={<CustomTooltip />} />
              <Bar dataKey={yKey} fill={`url(#barGrad-${idx})`} radius={[6, 6, 0, 0]} />
            </BarChart>
          ) : activeType === 'line' ? (
            <LineChart data={normalizedData} margin={chartMargin}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey={xKey} stroke="#94a3b8" {...xAxisConfig} />
              <YAxis stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 11}} />
              <RechartsTooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey={yKey} stroke="#6366f1" strokeWidth={3} dot={{r: 4, fill: "#ffffff", stroke: "#ec4899", strokeWidth: 2}} activeDot={{r: 7}} />
            </LineChart>
          ) : activeType === 'area' ? (
            <AreaChart data={normalizedData} margin={chartMargin}>
              <defs>
                <linearGradient id={`areaGrad-${idx}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#ec4899" stopOpacity={0.05}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.12)" vertical={false} />
              <XAxis dataKey={xKey} stroke="#94a3b8" {...xAxisConfig} />
              <YAxis stroke="#94a3b8" tick={{fill: '#94a3b8', fontSize: 11}} />
              <RechartsTooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey={yKey} stroke="#6366f1" strokeWidth={2.5} fillOpacity={1} fill={`url(#areaGrad-${idx})`} />
            </AreaChart>
          ) : (
            <PieChart>
              <Pie
                data={normalizedData}
                cx="50%"
                cy="42%"
                innerRadius={isExpanded ? 65 : 40}
                outerRadius={isExpanded ? 100 : 65}
                paddingAngle={4}
                dataKey={yKey}
                nameKey={xKey}
              >
                {normalizedData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <RechartsTooltip content={<CustomTooltip />} />
            </PieChart>
          )}
        </ResponsiveContainer>

        {activeType === 'pie' && (
          <div className="pie-custom-legend-wrapper">
            {normalizedData.map((entry, index) => {
              const label = String(entry[xKey] || `Item ${index + 1}`);
              const color = PIE_COLORS[index % PIE_COLORS.length];
              const val = entry[yKey];
              return (
                <div key={index} className="pie-legend-item" title={`${label}: ${val}`}>
                  <span className="pie-legend-dot" style={{ backgroundColor: color }} />
                  <span className="pie-legend-text" style={{ color: color }}>{label}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

const ChartPanel = ({ charts }) => {
  if (!charts || charts.length === 0) return null;

  const getGridClass = () => {
    if (charts.length === 1) return 'cols-1';
    if (charts.length === 2) return 'cols-2';
    return 'cols-3';
  };

  return (
    <div className="charts-section">
      <h3 className="section-title">Data Visualizations</h3>
      <div className={`charts-grid ${getGridClass()}`}>
        {charts.map((chart, idx) => (
          <SingleChartCard key={idx} chart={chart} idx={idx} />
        ))}
      </div>
    </div>
  );
};

export default React.memo(ChartPanel);
