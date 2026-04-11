"""
Prompt building for the 4-phase memory consolidation dream.

Phase 1: Orient - Understand the current memory structure
Phase 2: Gather - Review recent sessions and extract patterns
Phase 3: Consolidate - Synthesize new memories from patterns
Phase 4: Prune - Remove outdated or redundant memories
"""
from typing import List


MEMORY_CONSOLIDATION_PROMPT = """You are performing a memory consolidation dream. Your task is to synthesize and organize memories from recent sessions.

## Phase 1: Orient
First, explore the memory directory structure to understand what memories already exist:
- Read the memory index (MEMORY.md)
- List existing memory files to understand the current knowledge base
- Note the types, ages, and topics of existing memories

## Phase 2: Gather
Review recent sessions that have been created since last consolidation:
- Look at session files in the transcript directory
- Identify patterns in user requests, successful solutions, and recurring topics
- Note any important decisions or facts that should be preserved

## Phase 3: Consolidate
Based on your review, create new memories for:
- Important facts learned from recent sessions
- Patterns in user preferences and working patterns
- Solutions to recurring problems
- Context that would help future sessions

Write memory files to the memory directory with proper frontmatter.
Use this format:
---
id: <12-char hash>
type: <fact|preference|context|pattern>
name: <brief name>
description: <1-2 sentence description>
createdAt: <timestamp>
updatedAt: <timestamp>
---
<memory content>

## Phase 4: Prune
Review existing memories and:
- Update any that are now outdated or incorrect
- Merge similar memories that could be combined
- Note any memories that should be deleted (outdated, wrong, redundant)

Output a summary of what you found, created, updated, and pruned.
"""


def build_consolidation_prompt(
    memory_root: str,
    transcript_dir: str,
    extra: str = "",
) -> str:
    """
    Build the 4-phase consolidation prompt with specific paths.
    
    Args:
        memory_root: Path to the memory directory.
        transcript_dir: Path to the transcript/sessions directory.
        extra: Optional extra context or instructions.
    
    Returns:
        The formatted consolidation prompt string.
    """
    base_prompt = MEMORY_CONSOLIDATION_PROMPT
    
    context_section = f"""
## Current Paths
- Memory directory: {memory_root}
- Transcript directory: {transcript_dir}
"""
    
    extra_section = ""
    if extra:
        extra_section = f"""
## Extra Context
{extra}
"""
    
    full_prompt = f"""{base_prompt}{context_section}{extra_section}

Begin Phase 1: Orient. Explore the memory structure first, then proceed through each phase.
"""
    
    return full_prompt


def build_minimal_consolidation_prompt(
    sessions_summary: List[str],
) -> str:
    """
    Build a minimal consolidation prompt when we have session summaries.
    
    Args:
        sessions_summary: List of session summaries to consolidate.
    
    Returns:
        The formatted minimal consolidation prompt.
    """
    sessions_text = "\n".join(f"- {s}" for s in sessions_summary)
    
    return f"""You are performing a quick memory consolidation.

Recent sessions to review:
{sessions_text}

Based on these sessions:
1. Identify key facts, patterns, and context to remember
2. Create memory entries for important information
3. Update any existing memories that need revision

Output memories in the standard format with proper frontmatter.
"""
