import os
import json
import uuid
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any
from engine.pydantic_models import DocumentAnalytics, ExtractedMetric, KeyValuePair, ExtractedTable

logger = logging.getLogger(__name__)

# Attempt to import DuckDB. Fall back to standard sqlite3 if DuckDB DLL load fails (e.g. AppControl policy)
try:
    import duckdb
    HAS_DUCKDB = True
except Exception as _duckdb_err:
    import sqlite3
    HAS_DUCKDB = False
    logger.warning(f"DuckDB unavailable ({_duckdb_err}). Falling back to SQLite3 for persistence.")

# Global reentrant thread locks for DB operations
db_write_lock = threading.RLock()
db_read_lock = threading.RLock()

# Ensure data directory exists
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = (ROOT_DIR / "data").resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_db_path() -> str:
    raw = os.getenv("DUCKDB_PATH")
    if raw:
        if raw == ":memory:":
            return ":memory:"
        p = Path(raw)
        if not p.is_absolute():
            p = (ROOT_DIR / raw).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        return str(p)
    ext = "duckdb" if HAS_DUCKDB else "sqlite3"
    default_p = (DATA_DIR / f"visualizer.{ext}").resolve()
    default_p.parent.mkdir(parents=True, exist_ok=True)
    return str(default_p)

_shared_conn = None

def get_db_connection(read_only: bool = False):
    """Returns a connection to DuckDB or SQLite3. Uses shared in-memory connection when DUCKDB_PATH == ':memory:'."""
    global _shared_conn
    db_path = get_db_path()
    if HAS_DUCKDB:
        if db_path == ":memory:":
            if _shared_conn is None:
                _shared_conn = duckdb.connect(":memory:")
            return _shared_conn
        return duckdb.connect(db_path)
    else:
        if db_path == ":memory:":
            if _shared_conn is None:
                _shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            return _shared_conn
        return sqlite3.connect(db_path, check_same_thread=False)

def close_db_connection(conn):
    """Closes DB connection (committing changes if SQLite3) if not running in shared :memory: mode."""
    if get_db_path() != ":memory:" and conn is not None:
        try:
            if hasattr(conn, 'commit'):
                try:
                    conn.commit()
                except Exception:
                    pass
            conn.close()
        except Exception:
            pass

_db_initialized = False

def init_db():
    """Initializes the DuckDB document_metrics table schema once."""
    global _db_initialized
    with db_write_lock:
        conn = get_db_connection(read_only=False)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_metrics (
                    id VARCHAR PRIMARY KEY,
                    file_name VARCHAR NOT NULL,
                    data_type VARCHAR NOT NULL,
                    category VARCHAR NOT NULL,
                    metric_value DOUBLE,
                    unit VARCHAR,
                    context_snippet VARCHAR,
                    page_number INTEGER,
                    bbox_json VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_cache (
                    file_hash VARCHAR PRIMARY KEY,
                    file_name VARCHAR NOT NULL,
                    analytics_json VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            existing_cols = [r[1] for r in conn.execute("PRAGMA table_info('document_metrics')").fetchall()]
            if "page_width" not in existing_cols:
                conn.execute("ALTER TABLE document_metrics ADD COLUMN page_width DOUBLE;")
            if "page_height" not in existing_cols:
                conn.execute("ALTER TABLE document_metrics ADD COLUMN page_height DOUBLE;")
            _db_initialized = True
        except Exception as e:
            logger.error(f"DuckDB init_db error: {e}")
        finally:
            close_db_connection(conn)

def save_document_analytics(file_name: str, analytics: DocumentAnalytics) -> int:
    """
    Persists all extracted metrics, key-value pairs, and table records into DuckDB.
    Returns the total number of records inserted.
    """
    with db_write_lock:
        init_db()
        conn = get_db_connection(read_only=False)
        inserted_count = 0
        try:
            conn.execute("DELETE FROM document_metrics WHERE file_name = ?", [file_name])

            rows_to_insert = []

            for m in analytics.metrics:
                bbox_str = json.dumps(m.bbox) if m.bbox else None
                rows_to_insert.append((
                    str(uuid.uuid4()),
                    file_name,
                    "metric",
                    m.category or "General Metric",
                    float(m.metric_value),
                    m.unit or "",
                    m.context_snippet or "",
                    int(m.page_number or 1),
                    bbox_str,
                    m.page_width,
                    m.page_height
                ))

            for kv in analytics.key_value_pairs:
                rows_to_insert.append((
                    str(uuid.uuid4()),
                    file_name,
                    "kv_pair",
                    kv.key_name or "Attribute",
                    None,
                    "",
                    f"{kv.key_name}: {kv.value} | {kv.context_snippet or ''}",
                    int(kv.page_number or 1),
                    None,
                    None,
                    None
                ))

            if analytics.summary:
                rows_to_insert.append((
                    str(uuid.uuid4()),
                    file_name,
                    "summary",
                    "Executive Summary",
                    None,
                    "",
                    analytics.summary,
                    1,
                    None,
                    None,
                    None
                ))

            for tbl in analytics.tables:
                tbl_json = json.dumps({"headers": tbl.headers, "rows": tbl.rows})
                rows_to_insert.append((
                    str(uuid.uuid4()),
                    file_name,
                    "table",
                    tbl.table_title or "Table Grid",
                    None,
                    "",
                    tbl_json,
                    int(tbl.page_number or 1),
                    None,
                    None,
                    None
                ))

            if rows_to_insert:
                conn.executemany("""
                    INSERT INTO document_metrics 
                    (id, file_name, data_type, category, metric_value, unit, context_snippet, page_number, bbox_json, page_width, page_height)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, rows_to_insert)
                inserted_count = len(rows_to_insert)
                logger.info(f"DuckDB saved {inserted_count} analytics entries for file '{file_name}'")

        except Exception as e:
            logger.error(f"Error saving analytics to DuckDB for '{file_name}': {e}")
        finally:
            close_db_connection(conn)

        return inserted_count

def get_metrics_by_file(file_name: str) -> List[Dict[str, Any]]:
    """Retrieves all metric entries for a specified file from DuckDB."""
    init_db()
    with db_read_lock:
        conn = get_db_connection(read_only=True)
        try:
            res = conn.execute("""
                SELECT id, file_name, data_type, category, metric_value, unit, context_snippet, page_number, bbox_json, page_width, page_height, created_at
                FROM document_metrics
                WHERE file_name = ?
                ORDER BY page_number ASC, created_at DESC;
            """, [file_name]).fetchall()

            results = []
            for r in res:
                bbox = json.loads(r[8]) if r[8] else None
                results.append({
                    "id": r[0],
                    "file_name": r[1],
                    "data_type": r[2],
                    "category": r[3],
                    "metric_value": r[4],
                    "unit": r[5],
                    "context_snippet": r[6],
                    "page_number": r[7],
                    "bbox": bbox,
                    "page_width": r[9],
                    "page_height": r[10],
                    "created_at": str(r[11])
                })
            return results
        except Exception as e:
            logger.error(f"Error querying DuckDB metrics for file '{file_name}': {e}")
            return []
        finally:
            close_db_connection(conn)

def get_analytics_summary() -> Dict[str, Any]:
    """Returns high-level DuckDB analytical metrics across all ingested documents."""
    init_db()
    with db_read_lock:
        conn = get_db_connection(read_only=True)
        try:
            total_files = conn.execute("SELECT COUNT(DISTINCT file_name) FROM document_metrics").fetchone()[0]
            total_metrics = conn.execute("SELECT COUNT(*) FROM document_metrics WHERE data_type = 'metric'").fetchone()[0]
            avg_metric_val = conn.execute("SELECT AVG(metric_value) FROM document_metrics WHERE data_type = 'metric'").fetchone()[0] or 0.0
            
            top_categories = conn.execute("""
                SELECT category, COUNT(*) as cnt 
                FROM document_metrics 
                WHERE data_type = 'metric' 
                GROUP BY category 
                ORDER BY cnt DESC 
                LIMIT 5;
            """).fetchall()

            return {
                "total_files": total_files,
                "total_metrics": total_metrics,
                "avg_metric_value": round(avg_metric_val, 2),
                "top_categories": [{"category": r[0], "count": r[1]} for r in top_categories]
            }
        except Exception as e:
            logger.error(f"Error executing DuckDB analytics summary: {e}")
            return {"total_files": 0, "total_metrics": 0, "avg_metric_value": 0.0, "top_categories": []}
        finally:
            close_db_connection(conn)

def get_cached_analytics(file_hash: str) -> dict | None:
    """Retrieves cached analytics JSON from DuckDB by file hash."""
    init_db()
    with db_read_lock:
        conn = get_db_connection(read_only=True)
        try:
            res = conn.execute("SELECT analytics_json FROM document_cache WHERE file_hash = ?", [file_hash]).fetchone()
            if res:
                return json.loads(res[0])
        except Exception as e:
            logger.error(f"Error querying DuckDB cache for hash '{file_hash}': {e}")
        finally:
            close_db_connection(conn)
        return None

def save_cached_analytics(file_hash: str, file_name: str, analytics_dict: dict):
    """Caches parsed analytics JSON in DuckDB by file hash."""
    with db_write_lock:
        init_db()
        conn = get_db_connection(read_only=False)
        try:
            analytics_json = json.dumps(analytics_dict)
            conn.execute("""
                INSERT OR REPLACE INTO document_cache (file_hash, file_name, analytics_json, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP);
            """, [file_hash, file_name, analytics_json])
            logger.info(f"Successfully cached analytics for hash '{file_hash}' ({file_name})")
        except Exception as e:
            logger.error(f"Error caching analytics in DuckDB for hash '{file_hash}': {e}")
        finally:
            close_db_connection(conn)
