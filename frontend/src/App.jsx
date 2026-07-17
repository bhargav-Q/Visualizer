import React from 'react';
import { Activity, Loader2, AlertCircle, Sun, Moon } from 'lucide-react';
import axios from 'axios';
import FileUpload from './components/FileUpload';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  const [isLoading, setIsLoading] = React.useState(false);
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
    setError(null);
    setData(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8001/api/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      console.log("Success:", response.data);
      setData(response.data);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || err.message || "An error occurred during upload.");
    } finally {
      setIsLoading(false);
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
            <a href="https://github.com/bhargav-Q/Visualizer" target="_blank" rel="noopener noreferrer" className="nav-link">Documentation</a>
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
          <div className="placeholder-hero">
            <h2>Upload a File to Begin</h2>
            <p>We support .xlsx, .pdf, .docx, and .csv up to 15MB.</p>
            <FileUpload onFileSelect={handleFileSelect} />
          </div>
        )}

        {isLoading && (
          <div className="loading-state flex-col-center">
            <Loader2 className="animate-spin" size={48} color="var(--brand-purple)" />
            <h3 style={{ marginTop: '16px' }}>Processing File...</h3>
            <p style={{ color: 'var(--text-secondary)' }}>Extracting data and running AI models.</p>
          </div>
        )}

        {error && (
          <div className="error-toast">
            <AlertCircle size={20} />
            <span>{error}</span>
            <button onClick={() => setError(null)}>Try Again</button>
          </div>
        )}

        {data && (
          <Dashboard 
            data={data} 
            onReset={() => {
              setData(null);
              setError(null);
            }} 
          />
        )}
      </main>
    </div>
  );
}

export default App;
