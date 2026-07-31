import React from 'react';
import { Activity, Sun, Moon, BarChart2, FileText } from 'lucide-react';
// import { Loader2, AlertCircle, Image, Layers } from 'lucide-react';
import axios from 'axios';
import { API_BASE_URL } from './api/config';
import { ENDPOINTS } from './api/endpoints';
import { DOCUMENTATION_URL } from './utils/constants';
import FileUpload from './components/FileUpload';
import Dashboard from './components/Dashboard';
import ErrorBoundary from './components/ErrorBoundary';
import DynamicProcessingConsole from './components/DynamicProcessingConsole';
import './App.css';

function App() {
  const [isLoading, setIsLoading] = React.useState(false);
  const [activeFile, setActiveFile] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [data, setData] = React.useState(null);
  const [theme, setTheme] = React.useState('light');

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const handleFileSelect = async (file) => {
    setIsLoading(true);
    setActiveFile(file);
    setError(null);
    setData(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API_BASE_URL}${ENDPOINTS.UPLOAD}`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      console.log("Success:", response.data);
      setData(response.data);
      setIsLoading(false);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || "An error occurred during upload.");
      // Keep isLoading true so user sees the pinpointed error stage in console
    }
  };


  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header glass-panel">
        <div className="logo-container" onClick={() => { setData(null); setError(null); }}>
          <Activity className="logo-icon" size={28} color="var(--brand-purple)" />
          <h1 className="logo-text">Visualizer</h1>
        </div>

        <div className="header-actions">
          {/* Premium Navigation Links placed left of the toggle button */}
          <nav className="nav-links">
            <a href="#" className="nav-link" onClick={(e) => { e.preventDefault(); setData(null); setError(null); }}>Upload</a>
            {/* <a href="#" className="nav-link" onClick={(e) => { e.preventDefault(); alert("Feature coming soon: Visualizer history logs."); }}>History</a> */}
            <a href={DOCUMENTATION_URL} target="_blank" rel="noopener noreferrer" className="nav-link">Documentation</a>
          </nav>

          {/* <span className="badge">NVIDIA DeepSeek Powered</span> */}
          
          {/* <div className="header-demo-buttons">
            <button className="btn-white" style={{ padding: '6px 14px', fontSize: '0.85rem' }} onClick={() => alert("Simulated: Booking a Demo for Visualizer insights.")}>Book a demo</button>
            <button className="btn-primary" style={{ padding: '6px 14px', fontSize: '0.85rem' }} onClick={() => alert("Simulated: Login dialog.")}>Login</button>
          </div> */}

          <button 
            className="theme-toggle-btn" 
            onClick={toggleTheme}
            aria-label="Toggle dark mode"
            title={theme === 'light' ? "Switch to Dark Mode" : "Switch to Light Mode"}
          >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content animate-fade-in">
        {!isLoading && !data && (
          <div className="hero-two-column">
            {/* Left Column: Title, Subtitle & Capability Cards */}
            <div className="hero-left-col">
              <h2 className="hero-title">Upload a File to Begin</h2>
              <p className="hero-subtitle">We support spreadsheets (.xlsx, .csv) and document files (.pdf, .docx) up to 16MB.</p>

              <div className="capabilities-showcase">
                <h4 className="capabilities-title">What You Can Visualize</h4>
                <div className="capabilities-grid-2col">
                  <div className="capability-card tabular">
                    <div className="capability-icon-wrapper">
                      <BarChart2 size={20} color="var(--color-sales-strategy)" />
                    </div>
                    <h5>Sales & Financial Data</h5>
                    <p className="capability-formats">.XLSX &bull; .CSV</p>
                    <p className="capability-desc">Automated Bar, Line & Pie charts with column statistics.</p>
                  </div>

                  <div className="capability-card text">
                    <div className="capability-icon-wrapper">
                      <FileText size={20} color="var(--color-ai-sales)" />
                    </div>
                    <h5>Document Summaries</h5>
                    <p className="capability-formats">.PDF &bull; .DOCX</p>
                    <p className="capability-desc">Executive AI TL;DR summary & top keyword cloud.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Drag & Drop File Upload Box */}
            <div className="hero-right-col">
              <FileUpload onFileSelect={handleFileSelect} />
            </div>
          </div>
        )}

        {isLoading && (
          <div className="hero-centered-console animate-fade-in">
            <DynamicProcessingConsole 
              file={activeFile} 
              errorState={error}
              onRetry={() => {
                setIsLoading(false);
                setError(null);
                setActiveFile(null);
                setData(null);
              }}
            />
          </div>
        )}


        {data && (
          <ErrorBoundary>
            <Dashboard 
              data={data} 
              onReset={() => {
                setData(null);
                setError(null);
              }} 
            />
          </ErrorBoundary>
        )}
      </main>
    </div>
  );
}

export default App;
