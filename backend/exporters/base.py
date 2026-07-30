# ==============================================================================
# BASE EXPORTER (DEPRECATED & COMMENTED OUT FOR MISTRAL OCR)
# All original lines preserved below as comments.
# ==============================================================================
# from abc import ABC, abstractmethod
# from typing import Any
# from ir.document import CanonicalDocumentIR
# 
# class BaseExporter(ABC):
#     """Abstract Base Class for all read-only Canonical Document IR exporters."""
# 
#     @abstractmethod
#     def export(self, doc_ir: CanonicalDocumentIR, **kwargs) -> Any:
#         """Translates CanonicalDocumentIR into a target export format without mutating AST state."""
#         pass

from abc import ABC, abstractmethod
from typing import Any

class BaseExporter(ABC):
    @abstractmethod
    def export(self, doc_ir: Any, **kwargs) -> Any:
        pass
