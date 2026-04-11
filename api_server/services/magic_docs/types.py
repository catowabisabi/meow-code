from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class DocType(str, Enum):
    FUNCTION_DOC = "function_doc"
    CLASS_DOC = "class_doc"
    MODULE_DOC = "module_doc"
    README = "readme"
    MAGIC_DOC = "magic_doc"


class DocFormat(str, Enum):
    MARKDOWN = "markdown"
    PLAIN_TEXT = "plain_text"
    HTML = "html"


@dataclass
class DocRequest:
    code_snippet: str
    doc_type: DocType = DocType.FUNCTION_DOC
    title: Optional[str] = None
    custom_instructions: Optional[str] = None
    source_context: Optional[str] = None


@dataclass
class GeneratedDoc:
    file_path: str
    content: str
    summary: str
    doc_type: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


# Backwards compatibility alias
DocResponse = GeneratedDoc


@dataclass
class DocTemplate:
    title: str
    doc_type: DocType
    sections: List[str]
    format: DocFormat = DocFormat.MARKDOWN
    variables: List[str] = field(default_factory=list)


@dataclass
class MagicDocInfo:
    path: str
    title: str
    instructions: Optional[str] = None
    last_updated: float = field(default_factory=lambda: datetime.utcnow().timestamp())


@dataclass
class MagicDocUpdate:
    doc_path: str
    doc_title: str
    doc_contents: str
    custom_instructions: Optional[str] = None
    user_messages: List[Dict[str, Any]] = field(default_factory=list)