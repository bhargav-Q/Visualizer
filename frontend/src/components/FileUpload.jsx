import React, { useState, useRef } from 'react';
import { UploadCloud, File, AlertCircle, CheckCircle2 } from 'lucide-react';
import './FileUpload.css';

const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15MB
const ALLOWED_TYPES = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
  'application/pdf': '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
  'text/csv': '.csv',
  'application/vnd.ms-excel': '.csv'
};

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
      setError(`File is too large. Maximum size is 15MB.`);
      return false;
    }

    // Check type by extension as fallback
    const ext = '.' + selectedFile.name.split('.').pop().toLowerCase();
    const isAllowedExt = ['.xlsx', '.pdf', '.docx', '.csv'].includes(ext);
    
    // Check type by mime type
    const isAllowedMime = Object.keys(ALLOWED_TYPES).includes(selectedFile.type);

    if (!isAllowedExt && !isAllowedMime) {
      setError(`Unsupported file type. Please upload a .xlsx, .pdf, .docx, or .csv file.`);
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
          accept=".xlsx,.pdf,.docx,.csv"
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
              <UploadCloud size={48} color="var(--accent-color)" />
            </div>
            <h3>Drag & Drop your file here</h3>
            <p>or click to browse from your computer</p>
            <div className="file-badges">
              <span className="format-badge">XLSX</span>
              <span className="format-badge">PDF</span>
              <span className="format-badge">DOCX</span>
              <span className="format-badge">CSV</span>
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
