import React from 'react';
import { Activity, Loader2, AlertCircle } from 'lucide-react';
import axios from 'axios';
import FileUpload from './components/FileUpload';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [data, setData] = React.useState(null);

  const handleFileSelect = async (file) => {
    setIsLoading(true);
    setError(null);
    setData(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8000/api/upload", formData, {
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
          {!isLoading && !data && (
            <>
              <h2>Upload a File to Begin</h2>
              <p>We support .xlsx, .pdf, and .docx up to 15MB.</p>
              <FileUpload onFileSelect={handleFileSelect} />
            </>
          )}

          {isLoading && (
            <div className="loading-state flex-col-center">
              <Loader2 className="animate-spin" size={48} color="var(--accent-color)" />
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
        </div>
      </main>
    </div>
  );
}

export default App;
