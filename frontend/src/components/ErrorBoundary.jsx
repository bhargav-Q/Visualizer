import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Visualization Component Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ 
          padding: '28px', 
          color: '#ef4444', 
          background: 'rgba(239, 68, 68, 0.08)', 
          border: '1px solid rgba(239, 68, 68, 0.25)', 
          borderRadius: '12px',
          margin: '20px auto',
          maxWidth: '600px',
          textAlign: 'center'
        }}>
          <h4 style={{ margin: '0 0 8px 0', fontSize: '1.2rem', fontWeight: 600 }}>Visualization Error</h4>
          <p style={{ margin: '0 0 16px 0', color: 'var(--text-secondary, #666)', fontSize: '0.9rem' }}>
            {this.state.error?.message || "This component failed to render due to invalid or missing data attributes."}
          </p>
          <button 
            style={{
              background: 'var(--brand-purple, #6a1b9a)',
              color: '#fff',
              border: 'none',
              padding: '8px 18px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 500
            }}
            onClick={() => {
              this.setState({ hasError: false, error: null });
              if (window.location) window.location.reload();
            }}
          >
            Try Another File
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
