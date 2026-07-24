import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Eye, Search, AlertCircle, FileText, Compass } from 'lucide-react';
import { API_BASE_URL } from '../api/config';
import './TraceabilityViewer.css';

const TraceabilityViewer = ({ fileName, initialAnalytics }) => {
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeMetricId, setActiveMetricId] = useState(null);
  const [pdfLibLoaded, setPdfLibLoaded] = useState(false);
  const [pdfDoc, setPdfDoc] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [filterText, setFilterText] = useState('');
  
  const pagesContainerRef = useRef(null);
  const pageRefs = useRef({});

  // 1. Fetch metrics from the DuckDB API endpoint
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const res = await axios.get(`${API_BASE_URL}/api/documents/${encodeURIComponent(fileName)}/metrics`);
        // Filter down to metric type records for coordinate tracing
        let records = res.data.filter(r => r.data_type === 'metric');
        
        // Qualitative Fallback: if no numeric metrics found, fall back to kv_pair / table records
        if (records.length === 0) {
          records = res.data.map(r => ({
            ...r,
            metric_value: r.metric_value !== null && r.metric_value !== undefined ? r.metric_value : r.category
          }));
        }
        setMetrics(records);
        setError(null);
      } catch (err) {
        console.error("Error fetching DuckDB metrics:", err);
        // Fall back to initial upload response if API fetch fails
        if (initialAnalytics && initialAnalytics.metrics && initialAnalytics.metrics.length > 0) {
          setMetrics(initialAnalytics.metrics);
        } else if (initialAnalytics && initialAnalytics.key_value_pairs && initialAnalytics.key_value_pairs.length > 0) {
          const kvRecords = initialAnalytics.key_value_pairs.map((kv, idx) => ({
            id: `kv-${idx}`,
            category: kv.key_name,
            metric_value: kv.value,
            unit: "",
            context_snippet: kv.context_snippet || `${kv.key_name}: ${kv.value}`,
            page_number: kv.page_number || 1,
            bbox: kv.bbox || null
          }));
          setMetrics(kvRecords);
        } else {
          setError("No extracted metrics or key attributes available for coordinate tracing.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [fileName, initialAnalytics]);

  // 2. Load PDF.js script dynamically from CDN
  useEffect(() => {
    if (window.pdfjsLib) {
      setPdfLibLoaded(true);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.min.js';
    script.async = true;
    script.onload = () => {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';
      setPdfLibLoaded(true);
    };
    script.onerror = () => {
      setError("Failed to load PDF rendering engine script.");
    };
    document.body.appendChild(script);

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  // 3. Load PDF Document once pdfjsLib is ready
  useEffect(() => {
    if (!pdfLibLoaded) return;

    let activeDoc = null;

    const loadPdf = async () => {
      try {
        const url = `${API_BASE_URL}/api/documents/${encodeURIComponent(fileName)}/pdf`;
        const loadingTask = window.pdfjsLib.getDocument({
          url,
          withCredentials: true
        });
        const doc = await loadingTask.promise;
        activeDoc = doc;
        setPdfDoc(doc);
        setNumPages(doc.numPages);
      } catch (err) {
        console.error("PDF loading error:", err);
        setError("Error loading source PDF document. Make sure the file was saved correctly.");
      }
    };

    loadPdf();

    return () => {
      if (activeDoc) {
        activeDoc.destroy();
      }
    };
  }, [pdfLibLoaded, fileName]);

  // Handle scrolling to page
  const scrollToPage = (pageNum) => {
    const pageEl = pageRefs.current[pageNum];
    if (pageEl) {
      pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  // Filtered metrics
  const filteredMetrics = metrics.filter(m => {
    const searchStr = `${m.category} ${m.metric_value || ''} ${m.unit || ''} ${m.context_snippet || ''}`.toLowerCase();
    return searchStr.includes(filterText.toLowerCase());
  });

  const isQualitativeTrace = metrics.some(m => typeof m.metric_value === 'string' && isNaN(Number(m.metric_value)));

  return (
    <div className="trace-viewer-container glass-panel animate-fade-in">
      {/* Left Sidebar: Metrics List */}
      <div className="trace-sidebar">
        <div className="sidebar-header">
          <h3>
            <Compass className="icon-purple" size={18} />
            {isQualitativeTrace ? "Key Concepts & Topics" : "Extracted Metrics"}
          </h3>
          <p className="sidebar-subtitle">
            {isQualitativeTrace 
              ? "Hover or click a module topic card to view its source page."
              : "Hover or click a metric card to visually trace it to the source text."}
          </p>
          
          <div className="search-wrapper">
            <Search className="search-icon" size={14} />
            <input 
              type="text" 
              placeholder="Search categories or values..." 
              value={filterText}
              onChange={(e) => setFilterText(e.target.value)}
            />
          </div>
        </div>

        {loading ? (
          <div className="sidebar-loading">
            <span className="spinner"></span>
            <p>Loading database metrics...</p>
          </div>
        ) : error && metrics.length === 0 ? (
          <div className="sidebar-error">
            <AlertCircle size={24} className="error-icon" />
            <p>{error}</p>
          </div>
        ) : filteredMetrics.length === 0 ? (
          <div className="sidebar-empty">
            <p>No matching items found.</p>
          </div>
        ) : (
          <div className="metrics-list scroll-shadows">
            {filteredMetrics.map((m) => {
              const hasBbox = m.bbox && m.bbox.length === 4;
              const displayVal = typeof m.metric_value === 'number' ? m.metric_value.toLocaleString() : (m.metric_value || m.category);
              return (
                <div 
                  key={m.id || `${m.category}-${m.metric_value}`}
                  className={`metric-trace-card ${activeMetricId === m.id ? 'active' : ''} ${!hasBbox ? 'no-bbox' : ''}`}
                  onMouseEnter={() => {
                    if (hasBbox) {
                      setActiveMetricId(m.id);
                      scrollToPage(m.page_number || 1);
                    }
                  }}
                  onClick={() => {
                    setActiveMetricId(m.id);
                    scrollToPage(m.page_number || 1);
                  }}
                >
                  <div className="card-top">
                    <span className="metric-category-badge">{m.category}</span>
                    <span className="page-badge">Pg {m.page_number || 1}</span>
                  </div>
                  
                  <div className="metric-val-display">
                    <span className="metric-value-num" style={{ fontSize: typeof m.metric_value === 'number' ? '1.1rem' : '0.9rem' }}>
                      {displayVal}
                    </span>
                    {m.unit && <span className="metric-unit-text">{m.unit}</span>}
                  </div>

                  {m.context_snippet && (
                    <div className="metric-snippet">
                      &ldquo;{m.context_snippet}&rdquo;
                    </div>
                  )}

                  {hasBbox ? (
                    <div className="trace-action-indicator">
                      <Eye size={12} />
                      Traces to Source
                    </div>
                  ) : (
                    <div className="trace-action-indicator inactive">
                      No coordinate details available
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Right Content: PDF Document Page Viewer */}
      <div className="trace-document-view" ref={pagesContainerRef}>
        {!pdfDoc ? (
          <div className="document-loading-state">
            <div className="loader-ring"></div>
            <p>Rendering document preview canvas...</p>
          </div>
        ) : (
          <div className="pdf-pages-list">
            {Array.from({ length: numPages }, (_, index) => {
              const pageNum = index + 1;
              return (
                <PdfPageRenderer
                  key={pageNum}
                  pdfDoc={pdfDoc}
                  pageNum={pageNum}
                  activeMetric={metrics.find(m => m.id === activeMetricId && m.page_number === pageNum)}
                  setPageRef={(el) => { pageRefs.current[pageNum] = el; }}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

// Sub-component for rendering a single page canvas
const PdfPageRenderer = ({ pdfDoc, pageNum, activeMetric, setPageRef }) => {
  const canvasRef = useRef(null);
  const wrapperRef = useRef(null);
  const [scale, setScale] = useState(1.0);
  const [rendered, setRendered] = useState(false);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    let renderTask = null;

    const renderPage = async () => {
      try {
        const page = await pdfDoc.getPage(pageNum);
        
        // Calculate rendering scale based on container width
        const containerWidth = wrapperRef.current?.clientWidth || 600;
        const defaultViewport = page.getViewport({ scale: 1.0 });
        const calculatedScale = Math.min(2.0, Math.max(0.8, containerWidth / defaultViewport.width));
        setScale(calculatedScale);
        
        const viewport = page.getViewport({ scale: calculatedScale });
        setDimensions({ width: viewport.width, height: viewport.height });

        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext('2d');
        canvas.width = viewport.width;
        canvas.height = viewport.height;

        const renderContext = {
          canvasContext: context,
          viewport: viewport
        };
        
        renderTask = page.render(renderContext);
        await renderTask.promise;
        if (typeof page.cleanup === 'function') {
          page.cleanup();
        }
        setRendered(true);
      } catch (err) {
        console.error(`Error rendering page ${pageNum}:`, err);
      }
    };

    renderPage();

    return () => {
      if (renderTask) {
        renderTask.cancel();
      }
    };
  }, [pdfDoc, pageNum]);

  // Calculate target bounding box highlight dimensions
  let highlightStyles = null;
  if (activeMetric && activeMetric.bbox && activeMetric.page_width && activeMetric.page_height && rendered) {
    const [x0, y0, x1, y1] = activeMetric.bbox;
    // PDF points are relative to the original page width/height
    const scaleX = dimensions.width / activeMetric.page_width;
    const scaleY = dimensions.height / activeMetric.page_height;

    highlightStyles = {
      left: `${x0 * scaleX}px`,
      top: `${y0 * scaleY}px`,
      width: `${(x1 - x0) * scaleX}px`,
      height: `${(y1 - y0) * scaleY}px`
    };
  }

  return (
    <div 
      className="pdf-page-wrapper" 
      ref={(el) => {
        wrapperRef.current = el;
        setPageRef(el);
      }}
      style={{ minHeight: dimensions.height || '400px' }}
    >
      <div className="pdf-canvas-container" style={{ width: dimensions.width, height: dimensions.height }}>
        <canvas ref={canvasRef} />
        
        {highlightStyles && (
          <div 
            className="coordinate-highlight-box" 
            style={highlightStyles}
          />
        )}
      </div>
      <div className="page-number-footer">Page {pageNum}</div>
    </div>
  );
};

export default TraceabilityViewer;
