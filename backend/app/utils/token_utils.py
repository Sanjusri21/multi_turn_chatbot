from typing import List, Dict

def estimate_tokens(text: str) -> int:
    """
    Approximates token count for text using standard ~4 characters per token heuristic.
    This provides an efficient, lightweight estimate without external tokenizer overhead.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)

def estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
    """Estimates total token usage for a list of message dicts."""
    total = 0
    for msg in messages:
        total += estimate_tokens(msg.get("role", ""))
        total += estimate_tokens(msg.get("content", ""))
        total += 4  # overhead per message
    return total
