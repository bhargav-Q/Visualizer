# Requirement — Expected Output Specification

This file defines the **exact JSON structure** the backend returns for each supported file type. The frontend dashboard consumes these responses to render interactive charts, tables, summaries, keyword clouds, and traceability visual overlays.

---

## API Endpoint

```http
POST /api/upload
Content-Type: multipart/form-data
Body: file (max 16 MB, allowed: .xlsx, .pdf, .docx, .doc, .csv, .txt)
``` 

---

## Unified Response Envelope

Every successful response shares this top-level envelope:

```json
{
  "file_name": "string",
  "file_type": "xlsx | csv | pdf | docx | doc | txt",
  "data_category": "tabular | text | mixed",
  "tabular": { ... } | null,
  "text": { ... } | null,
  "analytics": { ... } | null,
  "processing_time": 4.12
}
```

- When `data_category` is `"tabular"` → `tabular` is populated.
- When `data_category` is `"text"` → `text` is populated.
- When `data_category` is `"mixed"` → `tabular`, `text`, and `analytics` are populated.

---

## Expected Output Schema Details

### 1. Tabular Analytics Envelope (`tabular`)

```json
{
  "columns": [
    { "name": "Region", "dtype": "object" },
    { "name": "Revenue", "dtype": "float64" }
  ],
  "preview_rows": [
    ["North", 45000.50],
    ["South", 32000.00]
  ],
  "row_count": 1500,
  "col_count": 2,
  "numeric_summary": {
    "Revenue": {
      "mean": 42350.75,
      "median": 40000.00,
      "min": 1200.00,
      "max": 98000.50,
      "std": 15230.40
    }
  },
  "categorical_summary": {
    "Region": {
      "unique": 4,
      "top_values": [
        { "value": "North", "count": 420 }
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
        { "Region": "North", "Revenue": 189000 }
      ]
    }
  ]
}
```

---

### 2. Document Analytics Envelope (`analytics`)

```json
{
  "document_title": "quarterly_report.pdf",
  "report_date": "2025-06-30",
  "summary": "This quarterly report covers performance across operating regions.",
  "keywords": ["Revenue", "Asia-Pacific", "Growth"],
  "metrics": [
    {
      "category": "Total Revenue",
      "metric_value": 450000.0,
      "unit": "USD",
      "context_snippet": "Total Revenue: $450,000 USD",
      "page_number": 1,
      "bbox": [100.0, 150.0, 300.0, 170.0],
      "page_width": 612.0,
      "page_height": 792.0
    }
  ],
  "key_value_pairs": [
    {
      "key_name": "Invoice Number",
      "value": "INV-2025-001",
      "context_snippet": "Invoice Number: INV-2025-001",
      "page_number": 1
    }
  ],
  "tables": [
    {
      "table_title": "Extracted Table - Page 1",
      "headers": ["Item", "Quantity", "Price"],
      "rows": [
        ["Widget A", "10", "150.00"]
      ],
      "page_number": 1
    }
  ]
}
```

---

## Zero-Downtime Fallback Behavior

When external cloud AI services hit rate limits (503) or time out ($>10\text{s}$):
- `processing_mode` switches to **local deterministic execution**.
- `RapidOCR` scans 100% of spatial character bounding boxes.
- `generate_local_fallback_text_result` builds a local executive summary and term-frequency keyword ranking.
- `parse_tsv_grid` parses tabular rows locally.
- All requests return HTTP status `200` with non-empty analytics.

---

## Health Check & Metrics Query Endpoints

### 1. Health Check
```http
GET /api/health
```
```json
{
  "status": "ok",
  "nvidia_api": "configured"
}
```

### 2. Document Metrics Query (DuckDB)
```http
GET /api/documents/{file_name}/metrics
```
```json
[
  {
    "id": "uuid-string",
    "file_name": "myOwnTestCase.pdf",
    "data_type": "metric",
    "category": "Total Revenue",
    "metric_value": 450000.0,
    "unit": "USD",
    "page_number": 1,
    "bbox": [100.0, 150.0, 300.0, 170.0]
  }
]
```
