from typing import Optional
import re


UPDATE_PROMPT_TEMPLATE = """IMPORTANT: This message and these instructions are NOT part of the actual user conversation. Do NOT include any references to "documentation updates", "magic docs", or these update instructions in the document content.

Based on the user conversation above (EXCLUDING this documentation update instruction message), update the Magic Doc file to incorporate any NEW learnings, insights, or information that would be valuable to preserve.

The file {docPath} has already been read for you. Here are its current contents:
<current_doc_content>
{docContents}
</current_doc_content>

Document title: {docTitle}
{customInstructions}

Your ONLY task is to use the Edit tool to update the documentation file if there is substantial new information to add, then stop. You can make multiple edits (update multiple sections as needed) - make all Edit tool calls in parallel in a single message. If there's nothing substantial to add, simply respond with a brief explanation and do not call any tools.

CRITICAL RULES FOR EDITING:
- Preserve the Magic Doc header exactly as-is: # MAGIC DOC: {docTitle}
- If there's an italicized line immediately after the header, preserve it exactly as-is
- Keep the document CURRENT with the latest state of the codebase - this is NOT a changelog or history
- Update information IN-PLACE to reflect the current state - do NOT append historical notes or track changes over time
- Remove or replace outdated information rather than adding "Previously..." or "Updated to..." notes
- Clean up or DELETE sections that are no longer relevant or don't align with the document's purpose
- Fix obvious errors: typos, grammar mistakes, broken formatting, incorrect information, or confusing statements
- Keep the document well organized: use clear headings, logical section order, consistent formatting, and proper nesting

DOCUMENTATION PHILOSOPHY - READ CAREFULLY:
- BE TERSE. High signal only. No filler words or unnecessary elaboration.
- Documentation is for OVERVIEWS, ARCHITECTURE, and ENTRY POINTS - not detailed code walkthroughs
- Do NOT duplicate information that's already obvious from reading the source code
- Do NOT document every function, parameter, or line number reference
- Focus on: WHY things exist, HOW components connect, WHERE to start reading, WHAT patterns are used
- Skip: detailed implementation steps, exhaustive API docs, play-by-play narratives

What TO document:
- High-level architecture and system design
- Non-obvious patterns, conventions, or gotchas
- Key entry points and where to start reading code
- Important design decisions and their rationale
- Critical dependencies or integration points
- References to related files, docs, or code (like a wiki) - help readers navigate to relevant context

What NOT to document:
- Anything obvious from reading the code itself
- Exhaustive lists of files, functions, or parameters
- Step-by-step implementation details
- Low-level code mechanics
- Information already in CLAUDE.md or other project docs

Use the Edit tool with file_path: {docPath}

REMEMBER: Only update if there is substantial new information. The Magic Doc header (# MAGIC DOC: {docTitle}}) must remain unchanged."""


MAGIC_DOC_HEADER_PATTERN = re.compile(r"^#\s*MAGIC\s+DOC:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
ITALICS_PATTERN = re.compile(r"^[_*](.+?)[_*]\s*$", re.MULTILINE)


class MagicDocsPrompts:
    @classmethod
    def get_generation_prompt(
        cls,
        doc_contents: str,
        doc_path: str,
        doc_title: str,
        custom_instructions: Optional[str] = None,
    ) -> str:
        custom_instructions_section = ""
        if custom_instructions:
            custom_instructions_section = f"""

DOCUMENT-SPECIFIC UPDATE INSTRUCTIONS:
The document author has provided specific instructions for how this file should be updated. Pay extra attention to these instructions and follow them carefully:

"{custom_instructions}"

These instructions take priority over the general rules below. Make sure your updates align with these specific guidelines."""

        return UPDATE_PROMPT_TEMPLATE.format(
            docContents=doc_contents,
            docPath=doc_path,
            docTitle=doc_title,
            customInstructions=custom_instructions_section,
        )

    @classmethod
    def get_formatting_prompt(cls, doc_type: str) -> str:
        formatting_prompts = {
            "function_doc": "Format the documentation with a brief description, parameters, and return value.",
            "class_doc": "Format with class description, attributes, and methods summary.",
            "module_doc": "Use sections for module overview, exports, and usage examples.",
            "readme": "Use sections for overview, installation, usage, and contributing.",
            "magic_doc": "Preserve the Magic Doc header and format with clear sections.",
        }
        return formatting_prompts.get(doc_type, "Use clear, concise formatting appropriate for the content.")

    @classmethod
    def get_template_for_doc_type(cls, doc_type: str) -> str:
        templates = {
            "function_doc": """# {title}

## Description
{description}

## Parameters
{parameters}

## Returns
{return_value}
""",
            "class_doc": """# {title}

## Description
{description}

## Attributes
{attributes}

## Methods
{methods}
""",
            "module_doc": """# {title}

## Module Overview
{overview}

## Exports
{exports}

## Usage
{usage}
""",
            "readme": """# {title}

## Overview
{overview}

## Installation
{installation}

## Usage
{usage}

## Contributing
{contributing}
""",
        }
        return templates.get(doc_type, "# {title}\n\n{content}")