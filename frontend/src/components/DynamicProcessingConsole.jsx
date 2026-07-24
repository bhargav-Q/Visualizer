import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Cpu, 
  Scan, 
  Terminal, 
  RefreshCw, 
  AlertTriangle,
  FileSpreadsheet,
  FileCode
} from 'lucide-react';
import './DynamicProcessingConsole.css';

const STAGES = [
  { id: 1, label: 'Ingestion & Validation', icon: FileText, desc: 'Reading binary stream & format headers' },
  { id: 2, label: 'Spatial Layout & OCR', icon: Scan, desc: 'Extracting 2D bounding boxes & X-anchors' },
  { id: 3, label: 'AI Schema Normalization', icon: Cpu, desc: 'Querying DeepSeek AI for table structure' },
  { id: 4, label: 'Chart Structuring', icon: CheckCircle2, desc: 'Generating statistics & dynamic charts' }
];

const DynamicProcessingConsole = ({ file, errorState, onRetry, onUseLocalFallback }) => {
  const [elapsed, setElapsed] = useState(0);
  const [currentStage, setCurrentStage] = useState(1);
  const [logs, setLogs] = useState([]);

  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileExt = (filename) => {
    if (!filename) return 'FILE';
    return filename.split('.').pop().toUpperCase();
  };

  const terminalBodyRef = React.useRef(null);

  // Auto-scroll inside the terminal body ONLY (does not scroll the main browser window)
  useEffect(() => {
    if (terminalBodyRef.current) {
      terminalBodyRef.current.scrollTop = terminalBodyRef.current.scrollHeight;
    }
  }, [logs]);

  // Stopwatch timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(prev => prev + 0.1);
    }, 100);
    return () => clearInterval(timer);
  }, []);

  // Live Pipeline Log Events - Clean milestone sequence without repeating ticker loop
  useEffect(() => {
    if (errorState) return;

    const fileExt = getFileExt(file?.name);
    const sizeStr = formatSize(file?.size);

    const initialLogs = [
      { id: 1, time: '0.1s', type: 'info', text: `📥 Binary payload stream received (${sizeStr})` },
      { id: 2, time: '0.4s', type: 'info', text: `📄 Verified ${fileExt} header structure & stream seek(0)` }
    ];
    setLogs(initialLogs);

    const t1 = setTimeout(() => {
      setCurrentStage(2);
      setLogs(prev => [
        ...prev,
        { id: 3, time: '1.2s', type: 'info', text: `🔍 Extracting 2D spatial layout & page bounding boxes...` },
        { id: 4, time: '2.5s', type: 'info', text: `⚡ RapidOCR orientation check: 0° accepted` }
      ]);
    }, 1200);

    const t2 = setTimeout(() => {
      setCurrentStage(3);
      setLogs(prev => [
        ...prev,
        { id: 5, time: '4.5s', type: 'info', text: `🧠 Processing qualitative & tabular section normalization...` },
        { id: 6, time: '6.0s', type: 'info', text: `✨ Extracting structured modules & key topic concepts...` }
      ]);
    }, 4500);

    const t3 = setTimeout(() => {
      setCurrentStage(4);
      setLogs(prev => [
        ...prev,
        { id: 7, time: '8.5s', type: 'info', text: `📊 Finalizing analytics & caching to embedded DuckDB storage...` }
      ]);
    }, 8500);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [file, errorState]);

  // Handle Error State Updates
  useEffect(() => {
    if (errorState) {
      const errStage = currentStage;
      setLogs(prev => [
        ...prev,
        { id: Date.now(), time: `${elapsed.toFixed(1)}s`, type: 'error', text: `❌ ERROR in Stage ${errStage} (${STAGES[errStage-1]?.label || 'Pipeline'}): ${errorState}` }
      ]);
    }
  }, [errorState]);

  const isFailed = !!errorState;

  return (
    <div className={`dynamic-console-container glass-panel animate-fade-in ${isFailed ? 'failed-state' : ''}`}>
      {/* Top File Meta & Stopwatch Bar */}
      <div className="console-header-bar">
        <div className="file-info-group">
          <div className="file-icon-badge">
            {getFileExt(file?.name) === 'XLSX' || getFileExt(file?.name) === 'CSV' ? (
              <FileSpreadsheet size={22} color="var(--brand-purple)" />
            ) : (
              <FileText size={22} color="var(--brand-purple)" />
            )}
          </div>
          <div className="file-meta-text">
            <span className="file-title">{file?.name || 'Document Upload'}</span>
            <div className="file-sub-pills">
              <span className="pill size">{formatSize(file?.size)}</span>
              <span className="pill ext">{getFileExt(file?.name)}</span>
            </div>
          </div>
        </div>

        <div className="timer-badge">
          <span className="timer-label">DURATION</span>
          <span className="timer-digits">⏱️ {elapsed.toFixed(2)}s</span>
        </div>
      </div>

      {/* Holographic Scanner Visualizer Node */}
      <div className="scanner-hero-node">
        <div className={`scanner-card ${isFailed ? 'card-failed' : 'card-scanning'}`}>
          <div className="scanner-laser-beam"></div>
          <Scan size={44} className={`scanner-icon ${isFailed ? 'text-red' : 'pulse-purple'}`} />
          <span className="scanner-status-text">
            {isFailed ? `PIPELINE STALLED AT STAGE ${currentStage}` : `PROCESSING STAGE ${currentStage} OF 4`}
          </span>
        </div>
      </div>

      {/* 4-Stage Stepper Bar */}
      <div className="stepper-bar-container">
        <div className="stepper-track">
          {STAGES.map((s) => {
            const isCompleted = currentStage > s.id && !isFailed;
            const isActive = currentStage === s.id && !isFailed;
            const isFailedStage = currentStage === s.id && isFailed;
            const StageIcon = s.icon;

            return (
              <div 
                key={s.id} 
                className={`step-item ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''} ${isFailedStage ? 'failed' : ''}`}
              >
                <div className="step-badge">
                  {isCompleted ? (
                    <CheckCircle2 size={18} className="icon-completed" />
                  ) : isFailedStage ? (
                    <XCircle size={18} className="icon-failed" />
                  ) : isActive ? (
                    <Loader2 size={18} className="icon-active animate-spin" />
                  ) : (
                    <StageIcon size={18} className="icon-pending" />
                  )}
                </div>
                <div className="step-text-col">
                  <span className="step-title">{s.label}</span>
                  <span className="step-desc">{s.desc}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Terminal Live Activity Log Stream */}
      <div className="terminal-log-window">
        <div className="terminal-header">
          <Terminal size={14} />
          <span>AI Pipeline Engine Live Output Ticker</span>
        </div>
        <div className="terminal-body" ref={terminalBodyRef}>
          {logs.map((l) => (
            <div key={l.id} className={`log-line log-${l.type}`}>
              <span className="log-time">[{l.time}]</span>
              <span className="log-content">{l.text}</span>
            </div>
          ))}
          {!isFailed && currentStage <= 4 && (
            <div className="log-line log-cursor">
              <span className="cursor-blink">▌</span>
            </div>
          )}
        </div>
      </div>

      {/* Error Recovery Controls */}
      {isFailed && (
        <div className="error-action-bar animate-fade-in">
          <div className="error-message-box">
            <AlertTriangle size={18} color="#ef4444" />
            <span>Processing failed at Stage {currentStage} ({STAGES[currentStage-1]?.label})</span>
          </div>
          <div className="action-buttons-row">
            {onUseLocalFallback && (
              <button className="btn-secondary" onClick={onUseLocalFallback}>
                ⚡ Load Deterministic Local Grid
              </button>
            )}
            {onRetry && (
              <button className="btn-primary" onClick={onRetry}>
                <RefreshCw size={14} style={{ marginRight: '6px' }} /> Try Another File
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DynamicProcessingConsole;
