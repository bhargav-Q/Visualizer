# 🔍 Codebase Hardcoded Values Audit Report

## Summary Table

| File Category | Total Findings | High Severity | Medium Severity | Low Severity |
| :--- | :---: | :---: | :---: | :---: |
| Backend (`/backend`) | 14 | 4 | 7 | 3 |
| Frontend (`/frontend`) | 11 | 2 | 6 | 3 |
| **Total Repository** | **25** | **6** | **13** | **6** |

---

## Detailed Findings (Sorted by File)

### 📁 `backend/`

#### 1. `backend/main.py`
* **Line 38**: Hardcoded CORS origins list (`"http://localhost:5173,http://localhost:3000"`).
  * **Category**: Secrets, Tokens & Endpoints 🚨 (High Severity)
  * **Current Code**: `allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")`
  * **Recommended Refactor**: Abstract default dev origins into a single environment config object or `backend/config.py`.

* **Line 61**: Raw 16MB file size bitwise calculation `16 * 1024 * 1024`.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `if file_size > 16 * 1024 * 1024:`
  * **Recommended Refactor**: Define `MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024` in `backend/config.py`.

* **Line 180**: Hardcoded `QUANTITATIVE_SIGNALS` set inline in endpoint handler.
  * **Category**: Hardcoded String Literals & Default Categories ⚠️ (Medium Severity)
  * **Current Code**: `QUANTITATIVE_SIGNALS = {'payroll', 'losses', 'premium', 'claim', 'amount', 'revenue', 'cost', ...}`
  * **Recommended Refactor**: Move keyword set to a centralized `backend/constants.py` module to prevent duplicate definitions in `document_extractor.py`.

* **Line 375**: Hardcoded host and port binding in entry script.
  * **Category**: Hardcoded File Paths & System Assumptions 🚨 (High Severity)
  * **Current Code**: `uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)`
  * **Recommended Refactor**: Read `PORT` and `HOST` from `os.getenv("PORT", 8000)`.

---

#### 2. `backend/engine/vision_client.py`
* **Line 17**: Hardcoded model name string literal.
  * **Category**: Hardcoded String Literals & Default Categories ⚠️ (Medium Severity)
  * **Current Code**: `VISION_MODEL_NAME = "meta/llama-3.2-11b-vision-instruct"`
  * **Recommended Refactor**: Allow model override via `os.getenv("NEMOTRON_VISION_MODEL")`.

* **Line 20**: Hardcoded HTTP timeout parameters `15.0` and `5.0`.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `TIMEOUT_CONFIG = httpx.Timeout(15.0, connect=5.0)`
  * **Recommended Refactor**: Define `VISION_API_TIMEOUT_SECONDS = float(os.getenv("VISION_TIMEOUT", 15.0))`.

* **Line 28**: Hardcoded NVIDIA NIM Base URL endpoint string.
  * **Category**: Secrets, Tokens & Endpoints 🚨 (High Severity)
  * **Current Code**: `base_url="https://integrate.api.nvidia.com/v1"`
  * **Recommended Refactor**: Store in `.env` as `NVIDIA_NIM_BASE_URL`.

* **Line 57**: Hardcoded 60-second global circuit breaker duration.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `def disable_vision_api(seconds: float = 60.0):`
  * **Recommended Refactor**: Extract default to `CIRCUIT_BREAKER_COOLDOWN_SECONDS = 60.0`.

---

#### 3. `backend/engine/document_extractor.py`
* **Line 33**: Magic number `3` for partial keyword word length matching.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `words = [w for w in clean_snippet.split() if len(w) > 3]`
  * **Recommended Refactor**: Name constant `MIN_KEYWORD_MATCH_LEN = 3`.

* **Line 365**: Duplicated inline `QUANTITATIVE_SIGNALS` set definition.
  * **Category**: Hardcoded String Literals & Default Categories ⚠️ (Medium Severity)
  * **Current Code**: `QUANTITATIVE_SIGNALS = {'payroll', 'losses', 'premium', 'claim', ...}`
  * **Recommended Refactor**: Import `QUANTITATIVE_SIGNALS` from shared `backend/constants.py`.

---

#### 4. `backend/engine/db.py`
* **Line 32**: Default database relative filename fallback.
  * **Category**: Hardcoded File Paths & System Assumptions 🚨 (High Severity)
  * **Current Code**: `db_path_obj = DATA_DIR / "app_data.duckdb"`
  * **Recommended Refactor**: Store default path in `backend/config.py`.

* **Line 54-74**: Raw SQL table schema strings hardcoded inside function body.
  * **Category**: Hardcoded String Literals & Default Categories 💡 (Low Severity)
  * **Current Code**: `conn.execute("CREATE TABLE IF NOT EXISTS document_metrics (...)")`
  * **Recommended Refactor**: Move SQL DDL queries to a `migrations.py` or `schema.sql` file.

---

#### 5. `backend/parsers/pdf_parser.py`
* **Line 46**: Hardcoded `MAX_OCR_PAGES = 15` limit.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `MAX_OCR_PAGES = 15`
  * **Recommended Refactor**: Read from `int(os.getenv("MAX_OCR_PAGES", 15))`.

* **Line 59**: Hardcoded character density threshold `150`.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `if len(native_text) < 150 and ocr_engine and ocr_pages_scanned < MAX_OCR_PAGES:`
  * **Recommended Refactor**: Name constant `SPARSE_TEXT_THRESHOLD_CHARS = 150`.

---

#### 6. `backend/parsers/spatial_grid.py`
* **Line 11**: Hardcoded confidence threshold default `0.50`.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `def filter_ocr_results_by_confidence(raw_ocr_results: list, min_confidence: float = 0.50)`
  * **Recommended Refactor**: Define `DEFAULT_MIN_CONFIDENCE = 0.50`.

* **Line 57**: Hardcoded pixel gap threshold numbers `6.0` and `0.8`.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `gap_threshold = max(6.0, median_char_w * gap_threshold_ratio)`
  * **Recommended Refactor**: Name constants `MIN_PIXEL_GAP_THRESHOLD = 6.0`.

---

#### 7. `backend/processors/text_processor.py`
* **Line 59-63**: Hardcoded document domain category strings (`"Insurance / Financial Submission"`, `"Curriculum / Syllabus"`, `"Business Document Outline"`).
  * **Category**: Hardcoded String Literals & Default Categories ⚠️ (Medium Severity)
  * **Current Code**: `doc_type = "Insurance / Financial Submission"`
  * **Recommended Refactor**: Define domain categories as an Enum class `DocumentDomain(str, Enum)`.

* **Line 68**: Hardcoded minimum topic title length `len(curr_title) >= 3`.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `if curr_title and len(curr_title) >= 3:`
  * **Recommended Refactor**: Name constant `MIN_TOPIC_TITLE_LEN = 3`.

* **Line 23-36**: Hardcoded English stopword set embedded directly in source file.
  * **Category**: Hardcoded String Literals & Default Categories 💡 (Low Severity)
  * **Current Code**: `ENGLISH_STOPWORDS = {"a", "about", "above", ...}`
  * **Recommended Refactor**: Move to `backend/resources/stopwords.py`.

---

### 📁 `frontend/`

#### 1. `frontend/src/api/config.js`
* **Line 1**: Fallback API Base URL hardcoded as `'http://localhost:8000'`.
  * **Category**: Secrets, Tokens & Endpoints 🚨 (High Severity)
  * **Current Code**: `export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';`
  * **Recommended Refactor**: Ensure fallback is configured via `.env.example` or throw a explicit warning in development mode.

---

#### 2. `frontend/src/App.jsx`
* **Line 36**: Endpoint subpath string hardcoded in axios request call.
  * **Category**: Secrets, Tokens & Endpoints 🚨 (High Severity)
  * **Current Code**: `axios.post(`${API_BASE_URL}/api/upload`, formData, ...)`
  * **Recommended Refactor**: Store API endpoint path constants in `src/api/endpoints.js` (e.g. `ENDPOINTS.UPLOAD`).

* **Line 64**: Hardcoded external GitHub URL.
  * **Category**: Hardcoded String Literals & Default Categories 💡 (Low Severity)
  * **Current Code**: `href="https://github.com/bhargav-Q/Visualizer"`
  * **Recommended Refactor**: Store link in `src/utils/constants.js` as `DOCUMENTATION_URL`.

* **Line 92**: Hardcoded UI subtitle copy string.
  * **Category**: Hardcoded String Literals & Default Categories ⚠️ (Medium Severity)
  * **Current Code**: `We support spreadsheets (.xlsx, .csv) and document files (.pdf, .docx, .txt) up to 16MB.`
  * **Recommended Refactor**: Extract UI copy into a translation/dictionary config `src/locales/en.json`.

---

#### 3. `frontend/src/components/ChartPanel.jsx`
* **Line 9**: Hardcoded hex color palette array.
  * **Category**: Hardcoded String Literals & Default Categories ⚠️ (Medium Severity)
  * **Current Code**: `const PIE_COLORS = ['#6a1b9a', '#9c4dcc', '#2563eb', '#22c55e', '#d97700', '#dc2626'];`
  * **Recommended Refactor**: Import palette from `src/utils/constants.js` or theme CSS variables.

* **Line 58**: Hardcoded layout height dimensions `450`, `320`, and `300`.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `height={isExpanded ? 450 : 320} minHeight={300}`
  * **Recommended Refactor**: Store chart container heights in `src/utils/constants.js`.

---

#### 4. `frontend/src/components/DataTablePreview.jsx`
* **Line 10**: Hardcoded pagination page size default `10`.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `const [pageSize, setPageSize] = useState(10);`
  * **Recommended Refactor**: Import `DEFAULT_PAGE_SIZE = 10` from `src/utils/constants.js`.

---

#### 5. `frontend/src/components/DynamicProcessingConsole.jsx`
* **Line 24**: Hardcoded timer interval delay `10` milliseconds.
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `setInterval(() => { ... }, 10)`
  * **Recommended Refactor**: Define `STOPWATCH_INTERVAL_MS = 10`.

* **Line 45-48**: Hardcoded pipeline stage titles embedded in array.
  * **Category**: Hardcoded String Literals & Default Categories ⚠️ (Medium Severity)
  * **Current Code**: `title: "File Ingestion & Stream Sanitization"`
  * **Recommended Refactor**: Move pipeline stage definitions to `src/utils/constants.js`.

---

#### 6. `frontend/src/components/WordCloud.jsx`
* **Line 18**: Hardcoded min/max font size calculation thresholds (`12` and `24`).
  * **Category**: Magic Numbers & Unnamed Constants ⚠️ (Medium Severity)
  * **Current Code**: `const fontSize = 12 + (score * 12);`
  * **Recommended Refactor**: Name constants `MIN_FONT_SIZE_PX = 12` and `MAX_FONT_SIZE_RANGE_PX = 12`.

---

#### 7. `frontend/src/components/FileUpload.jsx`
* **Line 28**: Hardcoded 16MB file size check inside dropzone event handler.
  * **Category**: Magic Numbers & Unnamed Constants 💡 (Low Severity)
  * **Current Code**: `if (file.size > 16 * 1024 * 1024)`
  * **Recommended Refactor**: Import existing `MAX_FILE_SIZE` constant from `src/utils/constants.js`.

---

## 5. Immediate Top Refactoring Recommendations

1. **Centralize Backend Constants (`backend/constants.py`)**:
   - Move duplicated `QUANTITATIVE_SIGNALS` keyword set (currently in `main.py` and `document_extractor.py`) into `backend/constants.py`.
   - Move document domain strings (`Insurance / Financial Submission`, etc.) into a shared Enum.
2. **Move System Thresholds to `.env` / `backend/config.py`**:
   - `MAX_OCR_PAGES = 15` in `pdf_parser.py`.
   - `16MB` file size limit.
   - `15.0s` HTTPX API timeout in `vision_client.py` and `text_processor.py`.
3. **Abstract Frontend API Endpoints**:
   - Store route paths (`/api/upload`, `/api/health`, `/api/cache/clear`) in `src/api/endpoints.js` rather than interpolating strings directly in components.