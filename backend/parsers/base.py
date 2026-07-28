from abc import ABC, abstractmethod
from typing import List, Optional
from contracts.document import DocumentContent

class BaseParser(ABC):
    """Abstract Base Class for all document parser adapters."""
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of lower-case file extensions supported by this parser e.g. ['.pdf']."""
        pass

    @property
    def supported_mimes(self) -> List[str]:
        """List of MIME types supported by this parser (optional)."""
        return []

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> DocumentContent:
        """
        Parses raw document bytes and returns a standardized DocumentContent instance.
        """
        pass
