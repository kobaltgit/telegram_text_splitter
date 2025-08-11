import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# Safety limit (slightly below Telegram hard limit)
TELEGRAM_MESSAGE_LIMIT = 4000


def find_safe_split(text: str, max_len: int) -> tuple[int, str | None]:
    """
    Find a safe split position in `text` not greater than max_len that does not
    break Markdown code fences (```), inline code (`...`), or LaTeX blocks:
      - inline math: $ ... $
      - display math: $$ ... $$
      - bracketed: \\[ ... \\]
    
    For very long blocks that can't fit in max_len, implements smart splitting:
    - Code blocks: split at max_len-3, add ``` to close, next chunk starts with ```
    - LaTeX blocks: split at max_len-2 (for $$ or \\]) or max_len-1 (for $)
    
    Returns tuple of (split_index, continuation_prefix) where continuation_prefix
    is what should be prepended to the next chunk (None if no continuation needed).
    """
    if len(text) <= max_len:
        return len(text), None

    # Helper: choose initial candidate (prefer paragraph -> line -> space -> forced)
    def initial_candidate(s: str, limit: int) -> int:
        pos = s.rfind("\n\n", 0, limit)
        if pos != -1:
            return pos + 2
        pos = s.rfind("\n", 0, limit)
        if pos != -1:
            return pos + 1
        pos = s.rfind(" ", 0, limit)
        if pos != -1:
            return pos + 1
        return limit

    # Helper: check if substring (prefix up to idx) leaves any unclosed delimiters
    def unsafe_at(prefix: str) -> bool:
        # 1) Fenced code blocks: ```
        fence_count = len(re.findall(r"```", prefix))
        if fence_count % 2 == 1:
            return True

        # 2) LaTeX display $$ ... $$
        # Count unescaped $$ occurrences
        display_dollar_count = len(re.findall(r"(?<!\\)\$\$", prefix))
        if display_dollar_count % 2 == 1:
            return True

        # 3) LaTeX \[ ... \]
        start_bracket_count = len(re.findall(r"(?<!\\)\\\[\s*", prefix))
        end_bracket_count = len(re.findall(r"(?<!\\)\\\]\s*", prefix))
        if start_bracket_count > end_bracket_count:
            return True

        # 4) Inline single $ ... $
        # Remove $$ occurrences so they don't interfere
        without_double = re.sub(r"(?<!\\)\$\$", "", prefix)
        inline_dollar_count = len(re.findall(r"(?<!\\)\$(?!\$)", without_double))
        if inline_dollar_count % 2 == 1:
            return True

        # 5) Inline code using single backticks (` ... `)
        # We should not count backticks that are part of triple backticks (```)
        # First remove all triple-backtick markers to avoid double counting
        tmp = re.sub(r"```", "", prefix)
        # Count single backticks not escaped. This will roughly detect inline code parity.
        single_backtick_count = len(re.findall(r"(?<!`)`(?!`)", tmp))
        if single_backtick_count % 2 == 1:
            return True

        # If none of the above indicate "inside block", then prefix is safe
        return False

    # Helper: detect what type of block we're inside and where it started
    def detect_block_context(prefix: str) -> tuple[str | None, int]:
        """
        Detect if we're inside a block and return (block_type, start_pos).
        block_type can be: 'code_fence', 'inline_code', 'display_math', 'bracket_math', 'inline_math'
        Returns (None, -1) if not inside any block.
        """
        # Check for code fence (last unclosed ```)
        fence_positions = []
        for m in re.finditer(r"```", prefix):
            fence_positions.append(m.start())
        if len(fence_positions) % 2 == 1:  # Inside code fence
            return 'code_fence', fence_positions[-1]
        
        # Check for display math (last unclosed $$)
        display_positions = []
        for m in re.finditer(r"(?<!\\)\$\$", prefix):
            display_positions.append(m.start())
        if len(display_positions) % 2 == 1:  # Inside display math
            return 'display_math', display_positions[-1]
        
        # Check for bracket math (unclosed \[)
        start_bracket_positions = []
        end_bracket_positions = []
        for m in re.finditer(r"(?<!\\)\\\[", prefix):
            start_bracket_positions.append(m.start())
        for m in re.finditer(r"(?<!\\)\\\]", prefix):
            end_bracket_positions.append(m.start())
        if len(start_bracket_positions) > len(end_bracket_positions):
            return 'bracket_math', start_bracket_positions[-1]
        
        # Check for inline code (last unclosed `)
        # Remove triple backticks first
        without_triple = re.sub(r"```", "", prefix)
        backtick_positions = []
        for m in re.finditer(r"(?<!`)`(?!`)", without_triple):
            backtick_positions.append(m.start())
        if len(backtick_positions) % 2 == 1:  # Inside inline code
            # Find actual position in original text
            actual_pos = prefix.rfind("`")
            return 'inline_code', actual_pos
        
        # Check for inline math (last unclosed $)
        without_double = re.sub(r"(?<!\\)\$\$", "", prefix)
        dollar_positions = []
        for m in re.finditer(r"(?<!\\)\$(?!\$)", without_double):
            dollar_positions.append(m.start())
        if len(dollar_positions) % 2 == 1:  # Inside inline math
            # Find actual position in original text
            actual_pos = prefix.rfind("$")
            return 'inline_math', actual_pos
        
        return None, -1

    # Helper: implement smart splitting for oversized blocks
    def smart_split_block(text: str, max_len: int, block_type: str, block_start: int) -> tuple[int, str]:
        """
        Implement smart splitting for blocks that are too large.
        Returns (split_position, continuation_prefix).
        """
        if block_type == 'code_fence':
            # For code blocks, try to split at a newline and preserve language
            # Extract the language from the opening fence
            fence_match = re.search(r"```(\w*)", text[block_start:block_start+20])
            language = fence_match.group(1) if fence_match else ""
            
            # Calculate space needed for closing ``` and opening ```[lang]\n
            continuation_prefix = f"```{language}\n" if language else "```\n"
            closing_delimiter = "```"
            space_needed = len(closing_delimiter)
            
            # Try to find a newline before max_len - space_needed
            target_pos = max_len - space_needed
            
            # Look for the last newline before our target position
            newline_pos = text.rfind('\n', 0, target_pos)
            if newline_pos != -1 and newline_pos > block_start + 10:  # Don't split too close to start
                split_pos = newline_pos + 1  # Split after the newline
            else:
                # No suitable newline found, split at target position
                split_pos = target_pos
            
            return split_pos, continuation_prefix
        
        elif block_type == 'display_math':
            # For display math, prioritize splitting at newlines to preserve formula integrity
            space_needed = 3  # for \n$$
            target_pos = max_len - space_needed
            
            # PRIORITY 1: Look for newlines (best place to split LaTeX)
            newline_pos = text.rfind('\n', 0, target_pos)
            if newline_pos != -1 and newline_pos > block_start + 5:  # Don't split too close to start
                split_pos = newline_pos + 1  # Split after the newline
                return split_pos, "$$\n"
            
            # PRIORITY 2: Look for mathematical break points (after +, -, =, etc.)
            for break_char in ['+', '-', '=', '\\\\']:  # \\\\ is LaTeX line break
                break_pos = text.rfind(break_char, 0, target_pos)
                if break_pos != -1 and break_pos > block_start + 5:
                    split_pos = break_pos + 1
                    return split_pos, "$$\n"
            
            # PRIORITY 3: Look for spaces to avoid breaking within commands
            space_pos = text.rfind(' ', 0, target_pos)
            if space_pos != -1 and space_pos > block_start + 5:
                split_pos = space_pos + 1
                return split_pos, "$$\n"
            
            # LAST RESORT: Split at target position
            split_pos = target_pos
            return split_pos, "$$\n"
        
        elif block_type == 'bracket_math':
            # Similar to display math - prioritize newlines
            space_needed = 3  # for \n\]
            target_pos = max_len - space_needed
            
            # PRIORITY 1: Look for newlines (best place to split LaTeX)
            newline_pos = text.rfind('\n', 0, target_pos)
            if newline_pos != -1 and newline_pos > block_start + 5:
                split_pos = newline_pos + 1
                return split_pos, "\\[\n"
            
            # PRIORITY 2: Look for mathematical break points
            for break_char in ['+', '-', '=', '\\\\']:
                break_pos = text.rfind(break_char, 0, target_pos)
                if break_pos != -1 and break_pos > block_start + 5:
                    split_pos = break_pos + 1
                    return split_pos, "\\[\n"
            
            # PRIORITY 3: Look for spaces
            space_pos = text.rfind(' ', 0, target_pos)
            if space_pos != -1 and space_pos > block_start + 5:
                split_pos = space_pos + 1
                return split_pos, "\\[\n"
            
            # LAST RESORT: Split at target position
            split_pos = target_pos
            return split_pos, "\\[\n"
        
        elif block_type == 'inline_math':
            # Split at max_len-1 to add $
            split_pos = max_len - 1
            return split_pos, "$"
        
        elif block_type == 'inline_code':
            # Split at max_len-1 to add `
            split_pos = max_len - 1
            return split_pos, "`"
        
        # Fallback
        return max_len, None

    # Start with an initial candidate
    candidate = initial_candidate(text, max_len)

    # If candidate would split inside a code/math block, try to roll back to safe boundary
    if unsafe_at(text[:candidate]):
        # First try rolling back to safe boundaries
        original_candidate = candidate
        while candidate > 0 and unsafe_at(text[:candidate]):
            # Try to roll back to previous paragraph, line or space before current candidate
            prev_paragraph = text.rfind("\n\n", 0, candidate - 1)
            if prev_paragraph != -1:
                candidate = prev_paragraph + 2
                continue
            prev_line = text.rfind("\n", 0, candidate - 1)
            if prev_line != -1:
                candidate = prev_line + 1
                continue
            prev_space = text.rfind(" ", 0, candidate - 1)
            if prev_space != -1:
                candidate = prev_space + 1
                continue
            
            # If we've tried everything and still can't find a safe spot,
            # the unsafe block starts at the beginning. Break and try smart splitting.
            candidate = 1
            break
        
        # If we successfully found a safe rollback position, use it
        if candidate > 0 and not unsafe_at(text[:candidate]):
            return min(candidate, len(text)), None
        
        # If rollback failed, check if the block is too large and needs smart splitting
        block_type, block_start = detect_block_context(text[:max_len])
        if block_type is not None:
            # Check if this block extends significantly beyond our limit
            # If it's just slightly over, prefer rollback; if much larger, use smart split
            if block_start >= 0:
                # Use smart splitting for any block that we can't safely roll back from
                logger.info(f"Large {block_type} block detected, using smart splitting")
                split_pos, continuation = smart_split_block(text, max_len, block_type, block_start)
                return split_pos, continuation
        
        # Last resort: force split at max_len
        logger.warning("Forced split inside a code/latex region - block too large for chunk size.")
        return max_len, None

    if candidate <= 0:
        # absolute fallback
        return min(len(text), max_len), None
    return min(candidate, len(text)), None


def split_markdown_into_chunks(text: str, max_chunk_size: int = TELEGRAM_MESSAGE_LIMIT) -> List[str]:
    """
    Split Markdown text into chunks that respect `max_chunk_size` and avoid
    breaking code blocks or LaTeX constructs, preferring:
      1) Paragraph boundaries (\n\n)
      2) Line boundaries (\n)
      3) Spaces
      4) Smart splitting of oversized blocks with proper continuation
    """
    if not text:
        return []

    remaining = text
    chunks: List[str] = []
    pending_prefix = None  # Prefix to add to next chunk for continuation

    while remaining:
        split_pos, continuation_prefix = find_safe_split(remaining, max_chunk_size)
        # If split_pos == 0 (shouldn't happen), break defensively
        if split_pos <= 0:
            logger.error("find_safe_split returned non-positive split position; forcing out.")
            split_pos = min(len(remaining), max_chunk_size)
            continuation_prefix = None

        chunk = remaining[:split_pos]
        
        # Add continuation prefix from previous smart split if any
        current_pending = pending_prefix
        if pending_prefix:
            chunk = pending_prefix + chunk
            pending_prefix = None
        
        # If this chunk needs smart splitting, add the closing delimiter
        if continuation_prefix:
            chunk = chunk + _get_closing_delimiter(continuation_prefix)
            pending_prefix = continuation_prefix
        elif current_pending and not continuation_prefix:
            # We were in a continuation but this chunk doesn't need smart splitting
            # Check if we're actually at the natural end of the block
            if current_pending.startswith("```"):
                # For code blocks, check if chunk ends with ```
                if chunk.rstrip().endswith("```"):
                    # Natural end of code block - don't continue the prefix
                    pending_prefix = None
                else:
                    # Still inside code block, continue the continuation
                    chunk = chunk + _get_closing_delimiter(current_pending)
                    pending_prefix = current_pending
            elif current_pending.startswith("$$"):
                # For display math, check if chunk ends with $$
                if chunk.rstrip().endswith("$$"):
                    # Natural end of display math block - don't continue the prefix
                    pending_prefix = None
                else:
                    # Still inside math block, continue the continuation  
                    chunk = chunk + _get_closing_delimiter(current_pending)
                    pending_prefix = current_pending
            elif current_pending.startswith("\\["):
                # For bracket math, check if chunk ends with \]
                if chunk.rstrip().endswith("\\]"):
                    # Natural end of bracket math block - don't continue the prefix
                    pending_prefix = None
                else:
                    # Still inside math block, continue the continuation  
                    chunk = chunk + _get_closing_delimiter(current_pending)
                    pending_prefix = current_pending
            else:
                # For other types, continue the continuation
                chunk = chunk + _get_closing_delimiter(current_pending)
                pending_prefix = current_pending
        
        chunks.append(chunk)
        
        # Only strip whitespace if we're not in a continuation (smart split)
        # This preserves indentation which is critical for code blocks
        if continuation_prefix or current_pending:
            # Smart split or continuation - preserve exact whitespace/indentation
            remaining = remaining[split_pos:]
        else:
            # Normal split - can safely remove leading whitespace/newlines
            remaining = remaining[split_pos:].lstrip("\n ")
    
    logger.info(f"Markdown text split into {len(chunks)} chunks.")
    return chunks


def _get_closing_delimiter(continuation_prefix: str) -> str:
    """Get the appropriate closing delimiter for the continuation prefix."""
    if continuation_prefix.startswith("```"):
        return "\n```"
    elif continuation_prefix.startswith("$$"):
        return "\n$$"
    elif continuation_prefix.startswith("\\["):
        return "\n\\]"
    elif continuation_prefix == "$":
        return "$"
    elif continuation_prefix == "`":
        return "`"
    return ""