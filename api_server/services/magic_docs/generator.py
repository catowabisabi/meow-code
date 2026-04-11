from typing import Optional, List, Dict, Any
from datetime import datetime
import re
import os

from api_server.services.magic_docs.types import (
    GeneratedDoc,
    DocResponse,
    DocTemplate,
    DocType,
    DocFormat,
    MagicDocInfo,
)
from api_server.services.magic_docs.prompts import MagicDocsPrompts


MAGIC_DOC_HEADER_PATTERN = re.compile(r"^#\s*MAGIC\s+DOC:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
ITALICS_PATTERN = re.compile(r"^[_*](.+?)[_*]\s*$", re.MULTILINE)

_tracked_magic_docs: Dict[str, MagicDocInfo] = {}

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rb", ".cs"}


class MagicDocs:
    _generated_docs: List[GeneratedDoc] = []
    _max_docs: int = 50

    @classmethod
    def detect_magic_doc_header(cls, content: str) -> Optional[Dict[str, Any]]:
        match = MAGIC_DOC_HEADER_PATTERN.match(content)
        if not match or not match.group(1):
            return None

        title = match.group(1).strip()
        header_end_index = match.start(1) + len(match.group(0))
        after_header = content[header_end_index:]
        next_line_match = re.match(r"^\s*\n(?:\s*\n)?(.+?)(?:\n|$)", after_header)

        if next_line_match and next_line_match.group(1):
            next_line = next_line_match.group(1)
            italics_match = ITALICS_PATTERN.match(next_line)
            if italics_match and italics_match.group(1):
                instructions = italics_match.group(1).strip()
                return {"title": title, "instructions": instructions}

        return {"title": title}

    @classmethod
    def register_magic_doc(cls, file_path: str, info: MagicDocInfo) -> None:
        if file_path not in _tracked_magic_docs:
            _tracked_magic_docs[file_path] = info

    @classmethod
    def unregister_magic_doc(cls, file_path: str) -> None:
        _tracked_magic_docs.pop(file_path, None)

    @classmethod
    def get_tracked_magic_docs(cls) -> Dict[str, MagicDocInfo]:
        return dict(_tracked_magic_docs)

    @classmethod
    def clear_tracked_magic_docs(cls) -> None:
        _tracked_magic_docs.clear()

    @classmethod
    async def generate_docs(
        cls,
        code_snippet: str,
        doc_type: str = "function_doc",
        title: Optional[str] = None,
        custom_instructions: Optional[str] = None,
    ) -> GeneratedDoc:
        lines = code_snippet.split("\n")
        first_line = lines[0] if lines else ""

        doc_title = title or "Generated Documentation"
        if "def " in first_line:
            func_name = first_line.split("def ")[-1].split("(")[0].strip()
            doc_title = f"Function: {func_name}"
        elif "class " in first_line:
            class_name = first_line.split("class ")[-1].split("(")[0].strip()
            doc_title = f"Class: {class_name}"

        content = f"# {doc_title}\n\n"
        content += f"**Type:** {doc_type}\n"
        content += f"**Generated:** {datetime.fromtimestamp(datetime.utcnow().timestamp()).isoformat()}\n\n"
        content += "## Code\n\n```python\n"
        content += code_snippet
        content += "\n```\n\n"
        content += "## Summary\n\n"
        content += "Auto-generated documentation from code analysis."

        doc = GeneratedDoc(
            file_path="",
            content=content,
            summary=doc_title,
            doc_type=doc_type,
        )

        cls._generated_docs.append(doc)
        if len(cls._generated_docs) > cls._max_docs:
            cls._generated_docs = cls._generated_docs[-cls._max_docs:]

        return doc

    @classmethod
    async def format_docs(
        cls,
        doc_response: GeneratedDoc,
        format_type: str = "markdown",
    ) -> str:
        if format_type == "markdown":
            return doc_response.content
        elif format_type == "plain_text":
            lines = doc_response.content.split("\n")
            plain_lines = []
            for line in lines:
                line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
                line = re.sub(r"\*([^*]+)\*", r"\1", line)
                line = re.sub(r"^#+\s*", "", line)
                plain_lines.append(line)
            return "\n".join(plain_lines)
        elif format_type == "html":
            html = doc_response.content
            html = re.sub(r"^#\s+(.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
            html = re.sub(r"^##\s+(.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
            html = re.sub(r"^###\s+(.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
            html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
            html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
            html = re.sub(r"```python\n(.+?)```", r"<pre><code>\1</code></pre>", html, flags=re.DOTALL)
            html = re.sub(r"```\n(.+?)```", r"<pre><code>\1</code></pre>", html, flags=re.DOTALL)
            return html
        return doc_response.content

    @classmethod
    def get_doc_template(cls, doc_type: str) -> DocTemplate:
        templates = {
            "function_doc": DocTemplate(
                title="Function Template",
                doc_type=DocType.FUNCTION_DOC,
                sections=["description", "parameters", "returns"],
                format=DocFormat.MARKDOWN,
                variables=["title", "description", "parameters", "return_value"],
            ),
            "class_doc": DocTemplate(
                title="Class Template",
                doc_type=DocType.CLASS_DOC,
                sections=["description", "attributes", "methods"],
                format=DocFormat.MARKDOWN,
                variables=["title", "description", "attributes", "methods"],
            ),
            "module_doc": DocTemplate(
                title="Module Template",
                doc_type=DocType.MODULE_DOC,
                sections=["overview", "exports", "usage"],
                format=DocFormat.MARKDOWN,
                variables=["title", "overview", "exports", "usage"],
            ),
            "readme": DocTemplate(
                title="README Template",
                doc_type=DocType.README,
                sections=["overview", "installation", "usage", "contributing"],
                format=DocFormat.MARKDOWN,
                variables=["title", "overview", "installation", "usage", "contributing"],
            ),
            "magic_doc": DocTemplate(
                title="Magic Doc Template",
                doc_type=DocType.MAGIC_DOC,
                sections=["header", "content"],
                format=DocFormat.MARKDOWN,
                variables=["title", "content"],
            ),
        }
        return templates.get(doc_type, templates["function_doc"])

    @classmethod
    async def build_update_prompt(
        cls,
        doc_contents: str,
        doc_path: str,
        doc_title: str,
        instructions: Optional[str] = None,
    ) -> str:
        return MagicDocsPrompts.get_generation_prompt(
            doc_contents=doc_contents,
            doc_path=doc_path,
            doc_title=doc_title,
            custom_instructions=instructions,
        )


class MagicDocsService:
    _instance: Optional["MagicDocsService"] = None

    def __init__(self) -> None:
        self._docs_cache: Dict[str, GeneratedDoc] = {}

    @classmethod
    def get_instance(cls) -> "MagicDocsService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_supported(self, file_path: str) -> bool:
        _, ext = os.path.splitext(file_path)
        return ext.lower() in SUPPORTED_EXTENSIONS

    async def generate_docs(self, file_path: str, force: bool = False) -> GeneratedDoc:
        if not force and file_path in self._docs_cache:
            return self._docs_cache[file_path]

        if not os.path.exists(file_path):
            return GeneratedDoc(
                file_path=file_path,
                content="",
                summary="File not found",
                success=False,
                error_message="File not found",
            )

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return GeneratedDoc(
                file_path=file_path,
                content="",
                summary="Error reading file",
                success=False,
                error_message=str(e),
            )

        doc = await MagicDocs.generate_docs(
            code_snippet=content,
            doc_type=self._get_doc_type(file_path),
        )
        doc.file_path = file_path
        self._docs_cache[file_path] = doc
        return doc

    async def update_docs(self, file_path: str, changes: List[Dict[str, Any]]) -> GeneratedDoc:
        existing = self._docs_cache.get(file_path)
        if existing:
            updated_content = existing.content
            for change in changes:
                if change.get("type") == "replace":
                    updated_content = updated_content.replace(
                        change.get("old_text", ""),
                        change.get("new_text", ""),
                    )
            existing.content = updated_content
            return existing

        return await self.generate_docs(file_path, force=True)

    def _get_doc_type(self, file_path: str) -> str:
        _, ext = os.path.splitext(file_path)
        ext_map = {
            ".py": "function_doc",
            ".js": "function_doc",
            ".ts": "function_doc",
            ".jsx": "function_doc",
            ".tsx": "function_doc",
            ".go": "function_doc",
            ".java": "class_doc",
            ".rb": "function_doc",
            ".cs": "class_doc",
        }
        return ext_map.get(ext.lower(), "function_doc")