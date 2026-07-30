import React from 'react';
import { FileText, Copy, Check } from 'lucide-react';
import './DocumentReader.css';

const DocumentReader = ({ rawMarkdown, fileName }) => {
  const [copied, setCopied] = React.useState(false);

  if (!rawMarkdown) {
    return (
      <div className="document-reader-empty glass-panel">
        <p>No extracted Markdown content available for this document.</p>
      </div>
    );
  }

  const handleCopyMarkdown = () => {
    navigator.clipboard.writeText(rawMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Convert raw Markdown text to styled paragraphs, headings, blockquotes, and tables
  const lines = rawMarkdown.split('\n');
  const renderedElements = [];
  let inTable = false;
  let tableRows = [];

  const flushTable = (keyPrefix) => {
    if (tableRows.length === 0) return;
    const headers = tableRows[0].strip("|").split("|").map(h => h.trim());
    const dataRows = tableRows.slice(2).map(r => r.strip("|").split("|").map(c => c.trim()));
    
    renderedElements.push(
      <div key={`table-${keyPrefix}`} className="reader-table-wrapper">
        <table className="reader-table">
          <thead>
            <tr>
              {headers.map((h, i) => <th key={i}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, rIdx) => (
              <tr key={rIdx}>
                {row.map((cell, cIdx) => <td key={cIdx}>{cell}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
    tableRows = [];
    inTable = false;
  };

  return (
    <div className="document-reader-container glass-panel animate-fade-in">
      <div className="reader-header">
        <div className="reader-title-group">
          <FileText size={20} color="var(--brand-purple)" />
          <h4>Document Inspector & Markdown Reader</h4>
          <span className="reader-file-tag">{fileName}</span>
        </div>
        <button className="btn-white btn-copy-md" onClick={handleCopyMarkdown}>
          {copied ? <Check size={14} color="#22c55e" /> : <Copy size={14} />}
          <span>{copied ? 'Copied Markdown' : 'Copy Raw .md'}</span>
        </button>
      </div>

      <div className="reader-body-content">
        <div className="markdown-formatted-text">
          {rawMarkdown.split('\n\n').map((paragraph, pIdx) => {
            const trimmed = paragraph.trim();
            if (!trimmed) return null;

            if (trimmed.startsWith('# ')) {
              return <h1 key={pIdx} className="md-h1">{trimmed.replace(/^#\s+/, '')}</h1>;
            }
            if (trimmed.startsWith('## ')) {
              return <h2 key={pIdx} className="md-h2">{trimmed.replace(/^##\s+/, '')}</h2>;
            }
            if (trimmed.startsWith('### ')) {
              return <h3 key={pIdx} className="md-h3">{trimmed.replace(/^###\s+/, '')}</h3>;
            }
            if (trimmed.startsWith('> ')) {
              return <blockquote key={pIdx} className="md-blockquote">{trimmed.replace(/^>\s+/, '')}</blockquote>;
            }
            if (trimmed.startsWith('---')) {
              return <hr key={pIdx} className="md-hr" />;
            }
            return <p key={pIdx} className="md-p">{trimmed}</p>;
          })}
        </div>
      </div>
    </div>
  );
};

export default DocumentReader;
