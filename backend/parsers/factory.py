import logging
from typing import Optional
from parsers.base import BaseParser
from parsers.registry import ParserRegistry, get_global_parser_registry
from parsers.csv_adapter import CSVParser
from parsers.xlsx_adapter import XLSXParser
# from parsers.xls_adapter import XLSParser
from parsers.txt_adapter import TXTParser
from parsers.docx_adapter import DOCXParser
from parsers.pdf_adapter import PDFParser
from utils.file_detector import FileDetector

logger = logging.getLogger(__name__)

class ParserFactory:
    """Factory class for instantiating and looking up parser adapters."""

    def __init__(self, registry: Optional[ParserRegistry] = None):
        self.registry = registry or get_global_parser_registry()
        self._initialize_default_parsers()

    def _initialize_default_parsers(self):
        """Registers all built-in parser adapters if not already present."""
        if not self.registry.get_supported_extensions():
            self.registry.register_parser(CSVParser())
            self.registry.register_parser(XLSXParser())
            self.registry.register_parser(TXTParser())
            self.registry.register_parser(DOCXParser())
            self.registry.register_parser(PDFParser())

    def get_parser(self, file_bytes: bytes, filename: str) -> BaseParser:
        """
        Detects file format via FileDetector and returns the appropriate BaseParser adapter.
        Raises ValueError if no matching parser is registered.
        """
        detected_ext, mime_type = FileDetector.detect_type(file_bytes, filename)
        parser = self.registry.get_parser(detected_ext, mime_type)

        if not parser:
            logger.error(f"No parser registered for detected extension '{detected_ext}' (filename: {filename})")
            raise ValueError(f"Unsupported file format: '{detected_ext}'. Supported formats: {self.registry.get_supported_extensions()}")

        return parser

# Default factory instance
_default_factory = ParserFactory()

def get_parser_factory() -> ParserFactory:
    """Returns the default pre-initialized ParserFactory instance."""
    return _default_factory
