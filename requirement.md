# Requirement — Expected Output Specification

This file defines the **exact JSON structure** the backend will return for each supported file type. The frontend dashboard will consume these responses to render charts, tables, summaries, and keyword clouds.

---

## API Endpoint

```
POST /api/upload
Content-Type: multipart/form-data
Body: file (max 16 MB, allowed: .xlsx, .pdf, .docx, .csv, .txt)
``` 

---

## Unified Response Envelope

Every successful response shares this top-level shape:

```json
{
  "file_name": "string",
  "file_type": "xlsx | pdf | docx | csv | txt",
  "data_category": "tabular | text",
  "tabular": { ... } | null,
  "text": { ... } | null
}
```

- When `data_category` is `"tabular"` → `tabular` is populated, `text` is `null`
- When `data_category` is `"text"` → `text` is populated, `tabular` is `null`

---

## Expected Output: XLSX (Spreadsheet)

**`data_category`: `"tabular"`**

```json
{
  "file_name": "sales_report_2025.xlsx",
  "file_type": "xlsx",
  "data_category": "tabular",
  "tabular": {
    "columns": [
      { "name": "Region", "dtype": "object" },
      { "name": "Product", "dtype": "object" },
      { "name": "Revenue", "dtype": "float64" },
      { "name": "Units Sold", "dtype": "int64" },
      { "name": "Date", "dtype": "datetime64[ns]" }
    ],
    "preview_rows": [
      ["North", "Widget A", 45000.50, 120, "2025-01-15"],
      ["South", "Widget B", 32000.00, 85, "2025-01-16"],
      ["East", "Widget A", 51000.75, 140, "2025-01-17"],
      ["West", "Widget C", 28000.25, 70, "2025-01-18"]
    ],
    "row_count": 1500,
    "col_count": 5,
    "numeric_summary": {
      "Revenue": {
        "mean": 42350.75,
        "median": 40000.00,
        "min": 1200.00,
        "max": 98000.50,
        "std": 15230.40
      },
      "Units Sold": {
        "mean": 105,
        "median": 98,
        "min": 10,
        "max": 350,
        "std": 45.2
      }
    },
    "categorical_summary": {
      "Region": {
        "unique": 4,
        "top_values": [
          { "value": "North", "count": 420 },
          { "value": "South", "count": 390 },
          { "value": "East", "count": 370 },
          { "value": "West", "count": 320 }
        ]
      },
      "Product": {
        "unique": 3,
        "top_values": [
          { "value": "Widget A", "count": 600 },
          { "value": "Widget B", "count": 500 },
          { "value": "Widget C", "count": 400 }
        ]
      }
    },
    "charts": [
      {
        "type": "bar",
        "title": "Revenue by Region",
        "x_key": "Region",
        "y_key": "Revenue",
        "data": [
          { "Region": "North", "Revenue": 189000 },
          { "Region": "South", "Revenue": 156000 },
          { "Region": "East", "Revenue": 172000 },
          { "Region": "West", "Revenue": 134000 }
        ]
      },
      {
        "type": "line",
        "title": "Revenue over Time",
        "x_key": "Date",
        "y_key": "Revenue",
        "data": [
          { "Date": "2025-01", "Revenue": 120000 },
          { "Date": "2025-02", "Revenue": 145000 },
          { "Date": "2025-03", "Revenue": 138000 },
          { "Date": "2025-04", "Revenue": 162000 }
        ]
      },
      {
        "type": "pie",
        "title": "Units Sold by Product",
        "x_key": "Product",
        "y_key": "Units Sold",
        "data": [
          { "Product": "Widget A", "Units Sold": 600 },
          { "Product": "Widget B", "Units Sold": 500 },
          { "Product": "Widget C", "Units Sold": 400 }
        ]
      }
    ]
  },
  "text": null
}
```

### Field Descriptions — Tabular

| Field | Type | Description |
|-------|------|-------------|
| `columns` | `list[ColumnInfo]` | Column name and pandas dtype for each column |
| `preview_rows` | `list[list]` | First 100 rows as arrays (preserves column order). `NaN` → `null`, dates → ISO strings |
| `row_count` | `int` | Total number of rows in the spreadsheet |
| `col_count` | `int` | Total number of columns |
| `numeric_summary` | `dict[str, NumericSummary]` | Per-column statistics for all numeric columns |
| `categorical_summary` | `dict[str, CategoricalSummary]` | Unique count and top values for all categorical (object) columns |
| `charts` | `list[ChartData]` | Up to 4 auto-generated chart suggestions, each with type, title, axis keys, and pre-aggregated data |

---

## Expected Output: PDF (Text Document)

**`data_category`: `"text"`**

```json
{
  "file_name": "quarterly_report_Q2.pdf",
  "file_type": "pdf",
  "data_category": "text",
  "tabular": null,
  "text": {
    "summary": "This quarterly report covers the company's Q2 2025 performance. Revenue increased 12% year-over-year, driven primarily by expansion in the Asia-Pacific region. Operating expenses remained flat, resulting in improved profit margins. The report highlights three strategic initiatives planned for Q3, including a new product launch and two key partnerships.",
    "keywords": [
      { "word": "revenue", "score": 0.95 },
      { "word": "quarterly performance", "score": 0.91 },
      { "word": "Asia-Pacific", "score": 0.87 },
      { "word": "profit margins", "score": 0.84 },
      { "word": "strategic initiatives", "score": 0.80 },
      { "word": "operating expenses", "score": 0.78 },
      { "word": "product launch", "score": 0.75 },
      { "word": "partnerships", "score": 0.72 },
      { "word": "year-over-year", "score": 0.70 },
      { "word": "expansion", "score": 0.68 },
      { "word": "market share", "score": 0.65 },
      { "word": "customer acquisition", "score": 0.62 },
      { "word": "supply chain", "score": 0.58 },
      { "word": "digital transformation", "score": 0.55 },
      { "word": "sustainability", "score": 0.52 },
      { "word": "workforce", "score": 0.48 },
      { "word": "compliance", "score": 0.45 },
      { "word": "innovation", "score": 0.42 },
      { "word": "risk management", "score": 0.38 },
      { "word": "stakeholders", "score": 0.35 }
    ],
    "word_count": 3200,
    "page_count": 12,
    "paragraph_count": null,
    "ai_model": "deepseek-ai/deepseek-v4-pro"
  }
}
```

---

## Expected Output: DOCX (Word Document)

**`data_category`: `"text"`**

```json
{
  "file_name": "project_proposal.docx",
  "file_type": "docx",
  "data_category": "text",
  "tabular": null,
  "text": {
    "summary": "The proposal outlines a machine learning pipeline for automated customer churn prediction. It details a three-phase approach: data collection and cleaning, model training using gradient boosting, and deployment via a REST API. The estimated timeline is 8 weeks with a team of 4 engineers.",
    "keywords": [
      { "word": "machine learning", "score": 0.93 },
      { "word": "churn prediction", "score": 0.90 },
      { "word": "gradient boosting", "score": 0.86 },
      { "word": "data pipeline", "score": 0.82 },
      { "word": "REST API", "score": 0.78 },
      { "word": "deployment", "score": 0.74 },
      { "word": "model training", "score": 0.71 },
      { "word": "data cleaning", "score": 0.67 },
      { "word": "customer retention", "score": 0.63 },
      { "word": "feature engineering", "score": 0.60 },
      { "word": "cross-validation", "score": 0.56 },
      { "word": "accuracy metrics", "score": 0.52 },
      { "word": "production environment", "score": 0.48 },
      { "word": "scalability", "score": 0.45 },
      { "word": "monitoring", "score": 0.42 },
      { "word": "stakeholder review", "score": 0.38 },
      { "word": "sprint planning", "score": 0.35 },
      { "word": "technical debt", "score": 0.32 },
      { "word": "documentation", "score": 0.28 },
      { "word": "team capacity", "score": 0.25 }
    ],
    "word_count": 1850,
    "page_count": null,
    "paragraph_count": 45,
    "ai_model": "deepseek-ai/deepseek-v4-pro"
  }
}
```

### Field Descriptions — Text

| Field | Type | Description |
|-------|------|-------------|
| `summary` | `string` | AI-generated TL;DR summary (3-5 sentences) via DeepSeek V4 Pro |
| `keywords` | `list[KeywordItem]` | Top 20 keywords with relevance scores (0.0–1.0), sorted by score descending |
| `word_count` | `int` | Total word count of extracted text |
| `page_count` | `int \| null` | Number of pages (PDF only, `null` for DOCX) |
| `paragraph_count` | `int \| null` | Number of non-empty paragraphs (DOCX only, `null` for PDF) |
| `ai_model` | `string` | The AI model used for summarization: `"deepseek-ai/deepseek-v4-pro"` |

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

### Error Scenarios

| Scenario | HTTP Status | Example Response |
|----------|-------------|------------------|
| Unsupported file type | `400` | `{"detail": "Unsupported file type '.txt'. Allowed: .xlsx, .pdf, .docx, .csv"}` |
| File too large | `413` | `{"detail": "File size exceeds 15 MB limit"}` |
| Corrupt / unreadable file | `422` | `{"detail": "Could not parse file. The file may be corrupted or password-protected."}` |
| Empty file / no data | `422` | `{"detail": "File contains no extractable data"}` |
| NVIDIA API key missing | `500` | `{"detail": "AI service not configured. Set NVIDIA_API_KEY in .env"}` |
| NVIDIA API timeout/error | `502` | `{"detail": "AI service temporarily unavailable"}` |

> **Note on AI failures:** When the NVIDIA API is unreachable, the response still returns `text` data with `word_count`, `page_count`, and `paragraph_count` populated, but `summary` will contain a fallback message like `"Summary unavailable — AI service is temporarily down."` and `keywords` will be an empty list. The request does **not** fail entirely.

---

## Health Check

```
GET /api/health
```

```json
{
  "status": "ok",
  "nvidia_api": "configured | missing"
}
```
