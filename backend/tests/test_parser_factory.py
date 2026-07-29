"""
Parser Layer Modernization & Factory Tests — Phase 2 & Phase 3 Verification
"""
import pytest
from parsers.factory import get_parser_factory
from parsers.csv_adapter import CSVParser
from parsers.pdf_adapter import PDFParser
from parsers.docx_adapter import DOCXParser
from parsers.txt_adapter import TXTParser
from parsers.xlsx_adapter import XLSXParser
from parsers.xls_adapter import XLSParser
from utils.file_detector import FileDetector

def test_file_detector_pdf():
    pdf_bytes = b"%PDF-1.4 sample content"
    ext, mime = FileDetector.detect_type(pdf_bytes, "sample.pdf")
    assert ext == ".pdf"
    assert mime == "application/pdf"

def test_file_detector_csv():
    csv_bytes = b"Date,Sales\n2025-01-01,100"
    ext, mime = FileDetector.detect_type(csv_bytes, "report.csv")
    assert ext == ".csv"
    assert mime == "text/csv"

def test_parser_factory_lookup():
    factory = get_parser_factory()
    
    csv_bytes = b"ColA,ColB\n1,2"
    parser = factory.get_parser(csv_bytes, "data.csv")
    assert isinstance(parser, CSVParser)

    pdf_bytes = b"%PDF-1.5 test document"
    parser = factory.get_parser(pdf_bytes, "doc.pdf")
    assert isinstance(parser, PDFParser)

def test_csv_adapter_execution():
    factory = get_parser_factory()
    csv_bytes = b"Category,Value\nWidget,49.99\nGadget,19.99"
    parser = factory.get_parser(csv_bytes, "sales.csv")
    
    content = parser.parse(csv_bytes, "sales.csv")
    assert len(content.tables) == 1
    assert content.tables[0].headers == ["Category", "Value"]
    assert len(content.tables[0].rows) == 2

def test_txt_adapter_execution():
    factory = get_parser_factory()
    txt_bytes = b"Quarterly Review\n\nRevenue grew by 15%."
    parser = factory.get_parser(txt_bytes, "review.txt")
    
    content = parser.parse(txt_bytes, "review.txt")
    assert "Quarterly Review" in content.raw_text
    assert content.paragraph_count >= 1
