import React, { useState, useRef } from 'react';
import { UploadCloud, File, AlertCircle, CheckCircle2 } from 'lucide-react';
import { MAX_FILE_SIZE, ALLOWED_TYPES, ALLOWED_EXTENSIONS } from '../utils/constants';
import './FileUpload.css';

const FileUpload = ({ onFileSelect }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState(null);
  const [file, setFile] = useState(null);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const validateFile = (selectedFile) => {
    setError(null);
    
    if (!selectedFile) return false;

    // Check size
    if (selectedFile.size > MAX_FILE_SIZE) {
      setError(`File is too large. Maximum size is 16MB.`);
      return false;
    }

    // Check type by extension as fallback
    const ext = '.' + selectedFile.name.split('.').pop().toLowerCase();
    const isAllowedExt = ALLOWED_EXTENSIONS.includes(ext);
    
    // Check type by mime type
    const isAllowedMime = Object.keys(ALLOWED_TYPES).includes(selectedFile.type);

    if (!isAllowedExt && !isAllowedMime) {
      setError(`Unsupported file type. Please upload a supported document, image, or spreadsheet.`);
      return false;
    }

    return true;
  };

  const processFile = (selectedFile) => {
    if (validateFile(selectedFile)) {
      setFile(selectedFile);
      if (onFileSelect) {
        onFileSelect(selectedFile);
      }
    } else {
      setFile(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  const triggerSelect = () => {
    fileInputRef.current.click();
  };

  return (
    <div className="upload-container">
      <div 
        className={`upload-zone glass-panel ${isDragging ? 'dragging' : ''} ${file ? 'has-file' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={triggerSelect}
      >
        <input 
          type="file"
          ref={fileInputRef}
          onChange={handleFileInput}
          accept=".xlsx,.csv,.pdf,.docx,.doc,.txt"
          className="hidden-input"
        />
        
        {file ? (
          <div className="upload-content success">
            <div className="icon-wrapper">
              <CheckCircle2 size={48} color="var(--success)" />
            </div>
            <h3>File Ready to Process</h3>
            <p className="file-name"><File size={16}/> {file.name}</p>
            <p className="file-size">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
            <span className="change-file-text">Click to change file</span>
          </div>
        ) : (
          <div className="upload-content">
            <div className="icon-wrapper pulse-animation">
              <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="14" y="6" width="36" height="52" rx="6" fill="var(--svg-doc-bg)" stroke="var(--svg-doc-border)" strokeWidth="2.5" />
                <path d="M34 6H48C49.1046 6 50 6.89543 50 8V20H38V6H34Z" fill="var(--svg-doc-border)" opacity="0.2" />
                <line x1="22" y1="28" x2="42" y2="28" stroke="var(--svg-doc-lines)" strokeWidth="3" strokeLinecap="round" />
                <line x1="22" y1="36" x2="36" y2="36" stroke="var(--svg-doc-lines)" strokeWidth="3" strokeLinecap="round" />
                <line x1="22" y1="44" x2="30" y2="44" stroke="var(--svg-doc-lines)" strokeWidth="3" strokeLinecap="round" />
                <circle cx="44" cy="44" r="10" fill="var(--svg-badge-circle)" stroke="var(--svg-badge-border)" strokeWidth="2.5" />
                <path d="M40 45L42.5 42.5L45 45L48 41" stroke="var(--svg-badge-check)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <h3>Drag & Drop your file here</h3>
            <p>or click to browse from your computer</p>
            <div className="file-badges">
              <span className="format-badge xlsx">XLSX / CSV</span>
              <span className="format-badge pdf">PDF</span>
              <span className="format-badge docx">DOCX / DOC</span>
              <span className="format-badge txt">TXT</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message animate-fade-in">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
