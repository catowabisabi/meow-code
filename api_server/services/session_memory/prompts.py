"""
Prompt templates for SessionMemory service.
"""

import re

from .utils import (
    get_default_template,
    MAX_SECTION_LENGTH,
    MAX_TOTAL_SESSION_MEMORY_TOKENS,
    estimate_token_count,
    analyze_section_sizes,
)


def substitute_variables(template: str, variables: dict[str, str]) -> str:
    """Substitute {{variable}} placeholders in template."""
    return template.replace(
        r'\{\{(\w+)\}\}',
        lambda m: variables.get(m.group(1), m.group(0))
    )


def get_default_update_prompt() -> str:
    """Return the default prompt for updating session memory."""
    return """IMPORTANT: This message and these instructions are NOT part of the actual user conversation. Do NOT include any references to "note-taking", "session notes extraction", or these update instructions in the notes content.

Based on the user conversation above (EXCLUDING this note-taking instruction message as well as system prompt, claude.md entries, or any past session summaries), update the session notes file.

The file {{notesPath}} has already been read for you. Here are its current contents:
<current_notes_content>
{{currentNotes}}
</current_notes_content>

Your ONLY task is to use the Edit tool to update the notes file, then stop. You can make multiple edits (update every section as needed) - make all Edit tool calls in parallel in a single message. Do not call any other tools.

CRITICAL RULES FOR EDITING:
- The file must maintain its exact structure with all sections, headers, and italic descriptions intact
-- NEVER modify, delete, or add section headers (the lines starting with '#' like # Task specification)
-- NEVER modify or delete the italic _section description_ lines (these are the lines in italics immediately following each header - they start and end with underscores)
-- The italic _section descriptions_ are TEMPLATE INSTRUCTIONS that must be preserved exactly as-is - they guide what content belongs in each section
-- ONLY update the actual content that appears BELOW the italic _section descriptions_ within each existing section
-- Do NOT add any new sections, summaries, or information outside the existing structure
- Do NOT reference this note-taking process or instructions anywhere in the notes
- It's OK to skip updating a section if there are no substantial new insights to add. Do not add filler content like "No info yet", just leave sections blank/unedited if appropriate.
- Write DETAILED, INFO-DENSE content for each section - include specifics like file paths, function names, error messages, exact commands, technical details, etc.
- For "Key results", include the complete, exact output the user requested (e.g., full table, full answer, etc.)
- Do not include information that's already in the CLAUDE.md files included in the context
- Keep each section under ~{MAX_SECTION_LENGTH} tokens/words - if a section is approaching this limit, condense it by cycling out less important details while preserving the most critical information
- Focus on actionable, specific information that would help someone understand or recreate the work discussed in the conversation
- IMPORTANT: Always update "Current State" to reflect the most recent work - this is critical for continuity after compaction

Use the Edit tool with file_path: {{notesPath}}

STRUCTURE PRESERVATION REMINDER:
Each section has TWO parts that must be preserved exactly as they appear in the current file:
1. The section header (line starting with #)
2. The italic description line (the _italicized text_ immediately after the header - this is a template instruction)

You ONLY update the actual content that comes AFTER these two preserved lines. The italic description lines starting and ending with underscores are part of the template structure, NOT content to be edited or removed.

REMEMBER: Use the Edit tool in parallel and stop. Do not continue after the edits. Only include insights from the actual user conversation, never from these note-taking instructions. Do not delete or change section headers or italic _section descriptions_.""".format(MAX_SECTION_LENGTH=MAX_SECTION_LENGTH)


def generate_section_reminders(section_sizes: dict[str, int], total_tokens: int) -> str:
    """Generate reminders for sections that are too long."""
    over_budget = total_tokens > MAX_TOTAL_SESSION_MEMORY_TOKENS
    oversized = [
        f'- "{section}" is ~{tokens} tokens (limit: {MAX_SECTION_LENGTH})'
        for section, tokens in section_sizes.items()
        if tokens > MAX_SECTION_LENGTH
    ]
    oversized.sort(key=lambda x: -int(re.search(r'~(\\d+)', x).group(1) if re.search(r'~(\\d+)', x) else '0'))
    
    if not oversized and not over_budget:
        return ''
    
    parts = []
    if over_budget:
        parts.append(
            f"\\n\\nCRITICAL: The session memory file is currently ~{total_tokens} tokens, "
            f"which exceeds the maximum of {MAX_TOTAL_SESSION_MEMORY_TOKENS} tokens. "
            "You MUST condense the file to fit within this budget."
        )
    
    if oversized:
        label = 'Oversized sections to condense' if over_budget else 'IMPORTANT: The following sections exceed the per-section limit and MUST be condensed'
        parts.append(f"\\n\\n{label}:\\n" + '\\n'.join(oversized))
    
    return ''.join(parts)


class SessionMemoryPrompts:
    """Prompt templates for session memory operations."""
    
    @staticmethod
    async def get_memory_summary_prompt(
        current_notes: str,
        notes_path: str,
    ) -> str:
        """Build prompt for summarizing/updating session memory."""
        prompt_template = get_default_update_prompt()
        
        section_sizes = analyze_section_sizes(current_notes)
        total_tokens = estimate_token_count(current_notes)
        section_reminders = generate_section_reminders(section_sizes, total_tokens)
        
        variables = {
            'currentNotes': current_notes,
            'notesPath': notes_path,
        }
        
        base_prompt = substitute_variables(prompt_template, variables)
        return base_prompt + section_reminders
    
    @staticmethod
    async def get_memory_retrieval_prompt(query: str) -> str:
        """Build prompt for retrieving relevant memories."""
        return f"""Based on the following query, retrieve relevant information from session memory:

Query: {query}

Search through session memory for information relevant to this query. Return the most relevant sections and any key findings."""
    
    @staticmethod
    def get_template() -> str:
        """Get the default session memory template."""
        return get_default_template()
    
    @staticmethod
    async def load_custom_template() -> str:
        """Load custom template if available."""
        return get_default_template()
    
    @staticmethod
    async def load_custom_prompt() -> str:
        """Load custom prompt if available."""
        return get_default_update_prompt()


__all__ = [
    "SessionMemoryPrompts",
    "substitute_variables",
    "get_default_update_prompt",
    "generate_section_reminders",
]