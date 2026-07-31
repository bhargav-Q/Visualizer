# Visualizer

Visualizer extracts, structures, and visualizes documents (.pdf, .xlsx, .csv, .docx) using Mistral OCR for unstructured files, NVIDIA NIM for AI-generated dashboards, and a native pandas path for tabular data. Every chart and KPI links back to the source page range so outputs can be verified against the original document.

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python**: `v3.10+` (tested on `v3.14`)
- **Node.js**: `v18.0+` & **npm**: `v9.0+`

### 1. Setup Backend
```bash
cd backend
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\activate.ps1
# Mac/Linux:
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

### 2. Setup Frontend
```bash
cd frontend
npm install
cp .env.example .env
```

### 3. Running Application Services
* **Backend Service (FastAPI)**:
  ```bash
  cd backend
  python -m uvicorn main:app --reload --port 8000
  ```
* **Frontend Application (React + Vite)**:
  ```bash
  cd frontend
  npm run dev
  ```

---

## 🔑 Required Environment Variables

Configure these variable names in `backend/.env` (keys and values are kept private):

| Variable Name | Description |
|---|---|
| `MISTRAL_API_KEY` | API key for Mistral OCR service (`mistral-ocr-latest`) |
| `NVIDIA_API_KEY` | API key for NVIDIA NIM LLM endpoints (`deepseek-ai/deepseek-v4-flash`) |
| `NVIDIA_NIM_BASE_URL` | Base URL endpoint for NVIDIA NIM API |
| `TEXT_AI_MODEL` | OCR/text model identifier |
| `TABLE_AI_MODEL` | Model identifier for tabular data extraction |
| `MISTRAL_OCR_MODEL` | Official Mistral OCR model identifier (`mistral-ocr-latest`) |
| `MAX_OCR_PAGES` | Maximum PDF page count limit for OCR scanning (default: `15`) |
| `SPARSE_TEXT_THRESHOLD` | Character count threshold for sparse PDF native text detection (default: `150`) |
| `OCR_DPI` | Target resolution DPI for PDF page rendering (default: `350`) |
| `MIN_OCR_CONFIDENCE` | Minimum confidence score threshold for OCR token filtering (default: `0.50`) |
| `DUCKDB_PATH` | Path to embedded DuckDB database file (default: `data/app_data.duckdb`) |
| `ALLOWED_ORIGINS` | Comma-separated list of CORS allowed origins |
| `HOST` | Backend server binding host IP (default: `0.0.0.0`) |
| `PORT` | Backend server binding port (default: `8000`) |

---

## 🧪 Running Automated Tests

Run the complete backend unit & integration test suite using `pytest`:

```bash
cd backend
python -m pytest tests/
```

---

## 📁 Project Structure

```text
Visualizer/
├── backend/
│   ├── main.py                # FastAPI entry point, upload validation, & CORS
│   ├── config.py              # System configuration & env variable loaders
│   ├── parsers/               # Parser engine & factory (.pdf, .xlsx, .csv, .docx)
│   ├── processors/            # Text, keyword, and normalizer processors
│   ├── services/              # Main pipeline, dashboard agent, Mistral OCR, & tabular service
│   ├── engine/                # DuckDB persistence (db.py) & Pydantic models
│   └── tests/                 # Automated pytest suite (20 tests)
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # React root container & file state manager
│   │   ├── components/        # Dashboard, ChartPanel, StatsCards, FileUpload
│   │   └── utils/             # Allowed extensions (.pdf, .xlsx, .csv, .docx) & constants
├── data/                      # Embedded DuckDB database & output storage
├── README.md                  # Project setup documentation
└── ARCHITECTURE.md            # Data flow & architecture notes
```

---

## 🧠 Gotchas & Decisions Log

1. **Restricted File Types (.pdf, .xlsx, .csv, .docx)**:
   * *Decision*: Plain text (`.txt`) and image formats (`.png`, `.jpg`) were removed to streamline the pipeline around structured tabular data and official Mistral PDF OCR scanning.
2. **Dual-Branch Pipeline Architecture (`main_pipeline.py`)**:
   * *Decision*: `.csv` and `.xlsx` bypass OCR entirely and run via native pandas (`process_tabular_file`) in $<0.5\text{s}$. Only `.pdf` and `.docx` route to Mistral OCR + DeepSeek.
3. **Strict Pydantic JSON Schema Validation & Fallback Routing**:
   * *Decision*: Added strict Pydantic validation (`DashboardSpecValidationSchema`) in `dashboard_agent.py`. If DeepSeek returns valid JSON syntax but invalid structures or non-numeric chart `y_data` (e.g. `["100", "N/A"]`), validation fails and safely routes execution to `generate_heuristic_fallback_dashboard_spec` to prevent downstream UI crashes.
4. **Zero-Loss Local Fallback System**:
   * *Decision*: If cloud AI endpoints time out or fail, local heuristic functions generate summaries and charts locally so the UI never crashes.
5. **Context Window Capping (`MAX_INPUT_CONTEXT_LEN = 25000`)**:
   * *Decision*: Input markdown is capped at 25k chars in `dashboard_agent.py` to prevent LLM context window overflows.
6. **Responsive Recharts Label Interval Control**:
   * *Decision*: Minimized cards auto-sample ticks (`interval="preserveStartEnd"`); expanded cards unhide 100% of field labels (`interval={0}`) with $-45^\circ$ rotation.
7. **Custom Scrollable Pie Chart Legend**:
   * *Decision*: Custom HTML flex container (`.pie-custom-legend-wrapper`) with scrollbars keeps 20+ legend categories strictly inside card borders.
8. **Thread-Safe Embedded DuckDB Storage**:
   * *Decision*: `db.py` uses `threading.RLock()` to prevent database file lock contention across async worker threads, with an automatic SQLite3 fallback.
