/**
 * Application Constants
 */

export const MAX_FILE_SIZE = 16 * 1024 * 1024; // 16MB

export const ALLOWED_TYPES = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
  'application/pdf': '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
  'text/csv': '.csv',
  'text/plain': '.txt'
};

export const ALLOWED_EXTENSIONS = ['.xlsx', '.csv', '.pdf', '.docx', '.txt'];

// UI Design Tokens & Palettes
export const PIE_COLORS = ['#6a1b9a', '#9c4dcc', '#2563eb', '#22c55e', '#d97700', '#dc2626'];

// Component Defaults
export const DEFAULT_PAGE_SIZE = 10;
export const STOPWATCH_INTERVAL_MS = 10;
export const MIN_WORD_CLOUD_FONT_SIZE = 12;
export const MAX_WORD_CLOUD_FONT_RANGE = 12;

// External Links
export const DOCUMENTATION_URL = 'https://github.com/bhargav-Q/Visualizer';

// Processing Stepper Stage Definitions
export const PIPELINE_STAGES = [
  { id: 1, title: 'File Ingestion & Stream Sanitization', desc: 'Validating stream seek(0) buffers & DuckDB cache' },
  { id: 2, title: 'Spatial Grid & Coordinate OCR Scanning', desc: 'Running RapidOCR Y-clustering & 2D TSV grid layout' },
  { id: 3, title: 'Async Parallel AI Data Normalization', desc: 'Dispatching Llama 3.1 70B clean extraction tasks' },
  { id: 4, title: 'UI Dashboard & Chart JSON Assembly', desc: 'Building pure Python metrics & Recharts SVG configs' }
];
