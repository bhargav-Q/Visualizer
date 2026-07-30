import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Search, FileText, Code, Copy, Check, ZoomIn, ZoomOut, ChevronLeft, ChevronRight, CornerUpLeft } from 'lucide-react';
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
  const [currentPage, setCurrentPage] = useState(1);
  const [zoomScale, setZoomScale] = useState(1.1);
  const [rightTab, setRightTab] = useState('text'); // 'text' | 'json'
  const [filterText, setFilterText] = useState('');
  const [copiedId, setCopiedId] = useState(null);
  const [jsonCopied, setJsonCopied] = useState(false);

  const pagesContainerRef = useRef(null);
  const pageRefs = useRef({});

  // 1. Fetch metrics from backend API
  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        setLoading(true);
        const res = await axios.get(`${API_BASE_URL}/api/documents/${encodeURIComponent(fileName)}/metrics`);
        let records = res.data.filter(r => r.data_type === 'metric');
        
        if (records.length === 0) {
          records = res.data.map((r, idx) => ({
            ...r,
            id: r.id || `rec-${idx}`,
            metric_value: r.metric_value !== null && r.metric_value !== undefined ? r.metric_value : (r.category || r.key_name)
          }));
        }
        setMetrics(records);
        const firstWithBbox = records.find(r => r.bbox && r.bbox.length === 4);
        if (firstWithBbox) {
          setActiveMetricId(firstWithBbox.id || `${firstWithBbox.category}-${firstWithBbox.metric_value}-1`);
        }
        setError(null);
      } catch (err) {
        console.error("Error fetching metrics:", err);
        if (initialAnalytics && initialAnalytics.metrics && initialAnalytics.metrics.length > 0) {
          setMetrics(initialAnalytics.metrics);
          const firstWithBbox = initialAnalytics.metrics.find(r => r.bbox && r.bbox.length === 4);
          if (firstWithBbox) setActiveMetricId(firstWithBbox.id);
        } else if (initialAnalytics && initialAnalytics.key_value_pairs) {
          const kvRecords = initialAnalytics.key_value_pairs.map((kv, idx) => ({
            id: `kv-${idx}`,
            category: kv.key_name,
            metric_value: kv.value,
            context_snippet: kv.context_snippet || `${kv.key_name}: ${kv.value}`,
            page_number: kv.page_number || 1,
            bbox: kv.bbox || null
          }));
          setMetrics(kvRecords);
          const firstWithBbox = kvRecords.find(r => r.bbox && r.bbox.length === 4);
          if (firstWithBbox) setActiveMetricId(firstWithBbox.id);
        } else {
          setError("No bounding box coordinates found for this document.");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchMetrics();
  }, [fileName, initialAnalytics]);

  // 2. Load PDF.js script dynamically
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
    script.onerror = () => setError("Failed to load PDF rendering engine.");
    document.body.appendChild(script);

    return () => {
      if (document.body.contains(script)) document.body.removeChild(script);
    };
  }, []);

  // 3. Load PDF Document
  useEffect(() => {
    if (!pdfLibLoaded) return;
    let activeDoc = null;
    const loadPdf = async () => {
      try {
        const url = `${API_BASE_URL}/api/documents/${encodeURIComponent(fileName)}/pdf`;
        const loadingTask = window.pdfjsLib.getDocument({ url, withCredentials: true });
        const doc = await loadingTask.promise;
        activeDoc = doc;
        setPdfDoc(doc);
        setNumPages(doc.numPages);
      } catch (err) {
        console.error("PDF load error:", err);
        setError("Source PDF document not found on server.");
      }
    };
    loadPdf();
    return () => {
      if (activeDoc) activeDoc.destroy();
    };
  }, [pdfLibLoaded, fileName]);

  const scrollToPage = (pageNum) => {
    setCurrentPage(pageNum);
    const pageEl = pageRefs.current[pageNum];
    if (pageEl) {
      pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleCopyText = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCopyFullJSON = () => {
    navigator.clipboard.writeText(JSON.stringify(metrics, null, 2));
    setJsonCopied(true);
    setTimeout(() => setJsonCopied(false), 2000);
  };

  const filteredMetrics = metrics.filter(m => {
    const searchStr = `${m.category || ''} ${m.metric_value || ''} ${m.context_snippet || ''}`.toLowerCase();
    return searchStr.includes(filterText.toLowerCase());
  });

  return (
    <div className="paddle-trace-container">
      {/* Top PaddleOCR Control Sub-Header */}
      <div className="paddle-top-header">
        <div className="paddle-header-left">
          <span className="paddle-source-tag">Source File</span>
          <span className="paddle-filename" title={fileName}>{fileName}</span>
          <div className="paddle-page-nav">
            <button 
              className="paddle-nav-btn" 
              disabled={currentPage <= 1} 
              onClick={() => scrollToPage(currentPage - 1)}
            >
              <ChevronLeft size={15} />
            </button>
            <span className="paddle-page-indicator">{currentPage} / {numPages || 1}</span>
            <button 
              className="paddle-nav-btn" 
              disabled={currentPage >= numPages} 
              onClick={() => scrollToPage(currentPage + 1)}
            >
              <ChevronRight size={15} />
            </button>
          </div>
          <div className="paddle-zoom-controls">
            <button className="paddle-zoom-btn" onClick={() => setZoomScale(prev => Math.max(0.7, prev - 0.15))}>
              <ZoomOut size={14} />
            </button>
            <span className="paddle-zoom-val">{Math.round(zoomScale * 100)}%</span>
            <button className="paddle-zoom-btn" onClick={() => setZoomScale(prev => Math.min(2.0, prev + 0.15))}>
              <ZoomIn size={14} />
            </button>
          </div>
        </div>

        <div className="paddle-header-right">
          <span className="paddle-model-badge">Parsing Engine: Mistral OCR (300 DPI)</span>
          <div className="paddle-tab-switch">
            <button 
              className={`paddle-tab-btn ${rightTab === 'text' ? 'active' : ''}`}
              onClick={() => setRightTab('text')}
            >
              <FileText size={14} />
              Text recognition
            </button>
            <button 
              className={`paddle-tab-btn ${rightTab === 'json' ? 'active' : ''}`}
              onClick={() => setRightTab('json')}
            >
              <Code size={14} />
              JSON
            </button>
          </div>
        </div>
      </div>

      {/* Main Dual Column Split-View (50% PDF Left / 50% Recognition Right) */}
      <div className="paddle-split-viewport">
        {/* LEFT COLUMN: PDF Document Page Canvas with Interactive Bounding Boxes */}
        <div className="paddle-pdf-column" ref={pagesContainerRef}>
          {!pdfDoc ? (
            <div className="paddle-loading-box">
              <span className="paddle-spinner"></span>
              <p>Rendering source PDF canvas...</p>
            </div>
          ) : (
            <div className="paddle-pdf-pages">
              {Array.from({ length: numPages }, (_, index) => {
                const pageNum = index + 1;
                return (
                  <PaddlePdfPageRenderer
                    key={pageNum}
                    pdfDoc={pdfDoc}
                    pageNum={pageNum}
                    zoomScale={zoomScale}
                    metrics={metrics}
                    activeMetricId={activeMetricId}
                    setActiveMetricId={setActiveMetricId}
                    handleCopyText={handleCopyText}
                    copiedId={copiedId}
                    setPageRef={(el) => { pageRefs.current[pageNum] = el; }}
                  />
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: Text Recognition Cards / JSON Viewer */}
        <div className="paddle-recognition-column">
          {rightTab === 'text' ? (
            <div className="paddle-text-panel">
              <div className="paddle-search-bar">
                <Search size={14} className="paddle-search-icon" />
                <input 
                  type="text" 
                  placeholder="Filter extracted text or categories..." 
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
                />
              </div>

              <div className="paddle-cards-list">
                {filteredMetrics.length === 0 ? (
                  <div className="paddle-empty-msg">No matching text records found.</div>
                ) : (
                  filteredMetrics.map((m, idx) => {
                    const mId = m.id || `${m.category}-${m.metric_value}-${m.page_number || 1}-${idx}`;
                    const isActive = activeMetricId === mId;
                    const valText = typeof m.metric_value === 'number' ? m.metric_value.toLocaleString() : (m.metric_value || m.category);

                    return (
                      <div 
                        key={mId}
                        className={`paddle-rec-card ${isActive ? 'active' : ''}`}
                        onMouseEnter={() => {
                          setActiveMetricId(mId);
                          if (m.page_number) scrollToPage(m.page_number);
                        }}
                        onClick={() => {
                          setActiveMetricId(mId);
                          if (m.page_number) scrollToPage(m.page_number);
                        }}
                      >
                        <div className="paddle-card-top">
                          <span className="paddle-card-tag">{m.category || 'Recognized Text'}</span>
                          <span className="paddle-card-pg">Pg {m.page_number || 1}</span>
                        </div>

                        <div className="paddle-card-val">
                          <span>{valText}</span>
                          <button 
                            className="paddle-mini-copy" 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyText(valText, mId);
                            }}
                            title="Copy text"
                          >
                            {copiedId === mId ? <Check size={13} color="#22c55e" /> : <Copy size={13} />}
                          </button>
                        </div>

                        {m.context_snippet && (
                          <div className="paddle-card-snippet">&ldquo;{m.context_snippet}&rdquo;</div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          ) : (
            <div className="paddle-json-panel">
              <div className="paddle-json-header">
                <span>Recognized Document JSON Schema</span>
                <button className="paddle-copy-json-btn" onClick={handleCopyFullJSON}>
                  {jsonCopied ? <Check size={14} color="#22c55e" /> : <Copy size={14} />}
                  {jsonCopied ? 'Copied JSON!' : 'Copy JSON'}
                </button>
              </div>
              <pre className="paddle-json-code">
                {JSON.stringify(metrics, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Sub-component for rendering PDF canvas page with bounding boxes
const PaddlePdfPageRenderer = ({
  pdfDoc,
  pageNum,
  zoomScale,
  metrics,
  activeMetricId,
  setActiveMetricId,
  handleCopyText,
  copiedId,
  setPageRef
}) => {
  const canvasRef = useRef(null);
  const wrapperRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    let renderTask = null;
    const renderPage = async () => {
      try {
        const page = await pdfDoc.getPage(pageNum);
        const defaultViewport = page.getViewport({ scale: 1.0 });
        const containerWidth = wrapperRef.current?.clientWidth || 550;
        
        const baseScale = containerWidth / defaultViewport.width;
        const finalScale = baseScale * zoomScale;

        const viewport = page.getViewport({ scale: finalScale });
        setDimensions({ width: viewport.width, height: viewport.height });

        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext('2d');
        canvas.width = viewport.width;
        canvas.height = viewport.height;

        renderTask = page.render({ canvasContext: context, viewport });
        await renderTask.promise;
      } catch (err) {
        console.error(`Page ${pageNum} render error:`, err);
      }
    };

    renderPage();
    return () => {
      if (renderTask) renderTask.cancel();
    };
  }, [pdfDoc, pageNum, zoomScale]);

  // Page specific metrics with bbox
  const pageMetrics = metrics.filter(m => (m.page_number || 1) === pageNum && m.bbox && m.bbox.length === 4);

  return (
    <div 
      className="paddle-pdf-wrapper"
      ref={(el) => {
        wrapperRef.current = el;
        setPageRef(el);
      }}
    >
      <div className="paddle-canvas-box" style={{ width: dimensions.width, height: dimensions.height }}>
        <canvas ref={canvasRef} />

        {/* Render Bounding Box Overlays */}
        {pageMetrics.map((m, idx) => {
          const mId = m.id || `${m.category}-${m.metric_value}-${pageNum}-${idx}`;
          const isActive = activeMetricId === mId;
          let [x0, y0, x1, y1] = m.bbox;
          
          const pageWidth = m.page_width || 612.0;
          const pageHeight = m.page_height || 792.0;

          if (x1 > pageWidth * 1.15 || y1 > pageHeight * 1.15) {
            const scaleFactor = 72.0 / 300.0;
            x0 *= scaleFactor;
            y0 *= scaleFactor;
            x1 *= scaleFactor;
            y1 *= scaleFactor;
          }

          const scaleX = dimensions.width / pageWidth;
          const scaleY = dimensions.height / pageHeight;

          const left = x0 * scaleX;
          const top = y0 * scaleY;
          const width = Math.max(26, (x1 - x0) * scaleX);
          const height = Math.max(16, (y1 - y0) * scaleY);
          const valText = typeof m.metric_value === 'number' ? m.metric_value.toLocaleString() : (m.metric_value || m.category);

          return (
            <div 
              key={mId}
              className={`paddle-bbox ${isActive ? 'active' : ''}`}
              style={{ left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px` }}
              onMouseEnter={() => setActiveMetricId(mId)}
              onClick={() => setActiveMetricId(mId)}
            >
              {isActive && (
                <div className="paddle-copy-tooltip" onClick={(e) => {
                  e.stopPropagation();
                  handleCopyText(valText, mId);
                }}>
                  {copiedId === mId ? <Check size={11} color="#22c55e" /> : <Copy size={11} />}
                  <span>{copiedId === mId ? 'Copied' : 'Copy'}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="paddle-page-footer">Page {pageNum}</div>
    </div>
  );
};

export default TraceabilityViewer;
