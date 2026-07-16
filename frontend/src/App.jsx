import React from 'react';
import { Activity } from 'lucide-react';
import FileUpload from './components/FileUpload';
import './App.css';

function App() {
  const handleFileSelect = (file) => {
    console.log("File selected:", file);
    // TODO: Upload to backend in Commit 9
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header glass-panel">
        <div className="logo-container">
          <Activity className="logo-icon" size={28} color="var(--accent-color)" />
          <h1 className="logo-text">Visualizer</h1>
        </div>
        <div className="header-actions">
          <span className="badge">NVIDIA DeepSeek Powered</span>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content animate-fade-in">
        <div className="placeholder-hero">
          <h2>Upload a File to Begin</h2>
          <p>We support .xlsx, .pdf, and .docx up to 15MB.</p>
          <FileUpload onFileSelect={handleFileSelect} />
        </div>
      </main>
    </div>
  );
}

export default App;
