"""
Utility functions for prompt management and token estimation.
Handles context window limits intelligently.
"""
import logging

logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text.
    Rough approximation: 1 token ≈ 4 characters for English text.
    More accurate for longer texts.
    """
    # Simple approximation: ~4 chars per token
    # This is conservative and works well for English
    return len(text) // 4

def truncate_prompt_to_fit(
    system_prompt: str,
    context: str,
    max_context_tokens: int,
    max_tokens_to_generate: int = 256,
    safety_buffer: int = 50
) -> str:
    """
    Truncate prompt to fit within context window.
    
    Args:
        system_prompt: The system prompt (always kept)
        context: The context to potentially truncate
        max_context_tokens: Maximum tokens in context window
        max_tokens_to_generate: Tokens to reserve for generation
        safety_buffer: Extra buffer for safety
        
    Returns:
        Truncated prompt that fits within context window
    """
    # Calculate available tokens for prompt
    available_tokens = max_context_tokens - max_tokens_to_generate - safety_buffer
    
    # Estimate tokens for system prompt
    system_tokens = estimate_tokens(system_prompt)
    
    # Calculate how many tokens we have for context
    context_budget = available_tokens - system_tokens
    
    if context_budget <= 0:
        logger.warning(f"[PromptUtils] System prompt ({system_tokens} tokens) exceeds available space ({available_tokens} tokens)")
        # Return just system prompt if it's too long (shouldn't happen)
        return system_prompt
    
    # Estimate context tokens
    context_tokens = estimate_tokens(context)
    
    if context_tokens <= context_budget:
        # Context fits, return full prompt
        return f"{system_prompt}\n\n{context}"
    
    # Context is too long, truncate it
    logger.info(f"[PromptUtils] Context too long ({context_tokens} tokens), truncating to fit ({context_budget} tokens)")
    
    # Calculate how many characters we can keep
    # Use 3 chars per token for truncation (very conservative - actual tokenizers often use more tokens)
    max_context_chars = int(context_budget * 3)
    
    # Truncate from the end (keep most recent context)
    truncated_context = context[-max_context_chars:] if len(context) > max_context_chars else context
    
    # Try to truncate at a sentence boundary if possible
    # Look for last newline or period before the truncation point
    if len(truncated_context) < len(context):
        # Find a good truncation point
        truncate_at = len(context) - max_context_chars
        # Look for newline or period near truncation point
        for i in range(max(0, truncate_at - 100), truncate_at + 100):
            if i < len(context) and context[i] in ['\n', '.']:
                truncated_context = context[i+1:].lstrip()
                break
    
    return f"{system_prompt}\n\n{truncated_context}"

def limit_entries_for_context(
    entries: list,
    max_entries: int = 10,
    max_chars_per_entry: int = 200
) -> list:
    """
    Limit and summarize entries to fit within context.
    
    Args:
        entries: List of entry dictionaries
        max_entries: Maximum number of entries to include
        max_chars_per_entry: Maximum characters per entry summary
        
    Returns:
        Limited list of entries with summarized text
    """
    if len(entries) <= max_entries:
        return entries
    
    # Take most recent entries
    limited = entries[:max_entries]
    
    # Truncate long free_text in each entry
    for entry in limited:
        if 'free_text' in entry and entry['free_text']:
            if len(entry['free_text']) > max_chars_per_entry:
                entry['free_text'] = entry['free_text'][:max_chars_per_entry] + "..."
    
    return limited

def limit_summaries_for_context(
    summaries: list,
    max_summaries: int = 5,
    max_chars_per_summary: int = 300
) -> list:
    """
    Limit and truncate summaries to fit within context.
    
    Args:
        summaries: List of summary dictionaries (week/month/year)
        max_summaries: Maximum number of summaries to include
        max_chars_per_summary: Maximum characters per summary
        
    Returns:
        Limited list of summaries with truncated text
    """
    if len(summaries) <= max_summaries:
        return summaries
    
    # Take most recent summaries
    limited = summaries[:max_summaries]
    
    # Truncate long verdict/evidence in each summary
    for summary in limited:
        summary_data = summary.get('summary', {})
        if 'verdict' in summary_data and summary_data['verdict']:
            if len(summary_data['verdict']) > max_chars_per_summary:
                summary_data['verdict'] = summary_data['verdict'][:max_chars_per_summary] + "..."
        # Limit evidence items
        if 'evidence' in summary_data and summary_data['evidence']:
            summary_data['evidence'] = summary_data['evidence'][:3]  # Max 3 evidence items
    
    return limited

