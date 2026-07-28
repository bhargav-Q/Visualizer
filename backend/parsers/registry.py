import logging
from typing import Dict, List, Optional
from parsers.base import BaseParser

logger = logging.getLogger(__name__)

class ParserRegistry:
    """Central registry maintaining dynamic mappings between file extensions/MIME types and BaseParser adapters."""

    def __init__(self):
        self._extension_map: Dict[str, BaseParser] = {}
        self._mime_map: Dict[str, BaseParser] = {}

    def register_parser(self, parser: BaseParser):
        """Registers a BaseParser instance for its supported extensions and MIME types."""
        for ext in parser.supported_extensions:
            clean_ext = ext.lower()
            if not clean_ext.startswith("."):
                clean_ext = f".{clean_ext}"
            self._extension_map[clean_ext] = parser
            logger.info(f"Registered parser {parser.__class__.__name__} for extension '{clean_ext}'")

        for mime in parser.supported_mimes:
            clean_mime = mime.lower().strip()
            self._mime_map[clean_mime] = parser
            logger.info(f"Registered parser {parser.__class__.__name__} for MIME '{clean_mime}'")

    def get_parser(self, extension: str, mime_type: Optional[str] = None) -> Optional[BaseParser]:
        """Retrieves a parser by extension or MIME type."""
        if mime_type and mime_type.lower() in self._mime_map:
            return self._mime_map[mime_type.lower()]

        clean_ext = extension.lower() if extension else ""
        if clean_ext and not clean_ext.startswith("."):
            clean_ext = f".{clean_ext}"

        return self._extension_map.get(clean_ext)

    def get_supported_extensions(self) -> List[str]:
        """Returns a list of all registered file extensions."""
        return list(self._extension_map.keys())

# Default global registry singleton instance
_default_registry = ParserRegistry()

def get_global_parser_registry() -> ParserRegistry:
    """Returns the pre-initialized global parser registry singleton."""
    return _default_registry
