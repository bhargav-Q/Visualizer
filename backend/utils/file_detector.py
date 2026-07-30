import os
from typing import Tuple

class FileDetector:
    """Utility for detecting document file type via magic bytes and extension fallback."""

    @staticmethod
    def detect_type(file_bytes: bytes, filename: str) -> Tuple[str, str]:
        """
        Detects (file_extension, mime_type) from raw bytes and filename.
        Returns normalized extension e.g. '.pdf', '.csv', '.xlsx', '.docx', '.txt', '.xls'.
        """
        ext = os.path.splitext(filename or "")[1].lower()
        if not ext and filename:
            ext = f".{filename.lower()}"

        # 1. Magic byte inspection
        header = file_bytes[:16] if file_bytes else b""

        if header.startswith(b"%PDF"):
            return ".pdf", "application/pdf"

        # PK Zip header: could be .xlsx or .docx
        if header.startswith(b"PK\x03\x04"):
            if ext in [".xlsx", ".xlsm"]:
                return ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            if ext in [".docx", ".docm"]:
                return ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            # Fallback to extension if ambiguous
            return ext or ".docx", "application/octet-stream"

        # OLE Binary Header: legacy .xls or .doc
        if header.startswith(b"\xd0\xcf\x11\xe0"):
            if ext == ".xls":
                return ".xls", "application/vnd.ms-excel"
            if ext == ".doc":
                return ".doc", "application/msword"
            return ".xls", "application/vnd.ms-excel"

        # Text file detection fallback
        if ext == ".csv":
            return ".csv", "text/csv"
        if ext == ".txt":
            return ".txt", "text/plain"

        return ext or ".txt", "application/octet-stream"
