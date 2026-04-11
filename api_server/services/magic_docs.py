from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class GeneratedDoc:
    doc_id: str
    title: str
    content: str
    doc_type: str
    created_at: float
    source_context: str
    format: str = "markdown"


class MagicDocsService:
    _generated_docs: List[GeneratedDoc] = []
    _max_docs: int = 50
    
    @classmethod
    async def generate_from_code(
        cls,
        code_snippet: str,
        doc_type: str = "function_doc",
    ) -> GeneratedDoc:
        doc_id = f"doc_{datetime.utcnow().timestamp()}"
        
        lines = code_snippet.split("\n")
        first_line = lines[0] if lines else ""
        
        title = "Generated Documentation"
        if "def " in first_line:
            title = first_line.split("def ")[-1].split("(")[0].strip()
            title = f"Function: {title}"
        elif "class " in first_line:
            title = first_line.split("class ")[-1].split("(")[0].strip()
            title = f"Class: {title}"
        
        content = f"# {title}\n\n"
        content += f"**Type:** {doc_type}\n"
        content += f"**Generated:** {datetime.fromtimestamp(datetime.utcnow().timestamp()).isoformat()}\n\n"
        content += "## Code\n\n```python\n"
        content += code_snippet
        content += "\n```\n\n"
        content += "## Summary\n\n"
        content += "Auto-generated documentation from code analysis."
        
        doc = GeneratedDoc(
            doc_id=doc_id,
            title=title,
            content=content,
            doc_type=doc_type,
            created_at=datetime.utcnow().timestamp(),
            source_context=code_snippet[:200],
        )
        
        cls._generated_docs.append(doc)
        if len(cls._generated_docs) > cls._max_docs:
            cls._generated_docs = cls._generated_docs[-cls._max_docs:]
        
        return doc
    
    @classmethod
    async def generate_readme(cls, project_path: str) -> GeneratedDoc:
        doc_id = f"doc_{datetime.utcnow().timestamp()}"
        
        content = f"# Project Documentation\n\n"
        content += f"**Generated:** {datetime.fromtimestamp(datetime.utcnow().timestamp()).isoformat()}\n\n"
        content += "## Overview\n\n"
        content += "Auto-generated README for project.\n\n"
        content += "## Structure\n\n"
        content += "- Source files\n"
        content += "- Tests\n"
        content += "- Documentation\n"
        
        doc = GeneratedDoc(
            doc_id=doc_id,
            title="README",
            content=content,
            doc_type="readme",
            created_at=datetime.utcnow().timestamp(),
            source_context=project_path,
        )
        
        cls._generated_docs.append(doc)
        return doc
    
    @classmethod
    async def get_doc(cls, doc_id: str) -> Optional[GeneratedDoc]:
        return next((d for d in cls._generated_docs if d.doc_id == doc_id), None)
    
    @classmethod
    async def get_recent_docs(cls, limit: int = 10) -> List[GeneratedDoc]:
        return cls._generated_docs[-limit:]
    
    @classmethod
    async def delete_doc(cls, doc_id: str) -> bool:
        for i, d in enumerate(cls._generated_docs):
            if d.doc_id == doc_id:
                cls._generated_docs.pop(i)
                return True
        return False
    
    @classmethod
    async def clear_docs(cls) -> None:
        cls._generated_docs.clear()