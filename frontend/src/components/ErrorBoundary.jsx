import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Component Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '20px', color: '#ff6b6b', background: 'rgba(255,0,0,0.1)', borderRadius: '8px' }}>
          <h4>Visualization Error</h4>
          <p>This component failed to render. Please try again.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
