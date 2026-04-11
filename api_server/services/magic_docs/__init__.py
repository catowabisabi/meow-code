from api_server.services.magic_docs.types import (
    DocRequest,
    GeneratedDoc,
    DocResponse,
    DocTemplate,
    DocType,
    DocFormat,
    MagicDocInfo,
    MagicDocUpdate,
)
from api_server.services.magic_docs.generator import MagicDocs, MagicDocsService
from api_server.services.magic_docs.prompts import MagicDocsPrompts

__all__ = [
    "DocRequest",
    "GeneratedDoc",
    "DocResponse",
    "DocTemplate",
    "DocType",
    "DocFormat",
    "MagicDocInfo",
    "MagicDocUpdate",
    "MagicDocs",
    "MagicDocsService",
    "MagicDocsPrompts",
]