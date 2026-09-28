import re
from typing import List, Dict, Any

def clean_text(text: str) -> str:
    """Removes excessive whitespace and standardizes line breaks."""
    if not text:
        return ""
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def format_memories_for_prompt(memories: List[Any]) -> str:
    """Formats a list of Memory records into a clean bulleted markdown list grouped by category."""
    if not memories:
        return "None recorded yet."

    categories: Dict[str, List[str]] = {}
    for m in memories:
        cat = getattr(m, "category", "other").capitalize()
        key = getattr(m, "key", "").replace("_", " ").title()
        val = getattr(m, "value", "")
        categories.setdefault(cat, []).append(f"- {key}: {val}")

    lines = []
    for cat, items in sorted(categories.items()):
        lines.append(f"[{cat}]")
        lines.extend(items)
    return "\n".join(lines)

def detect_language(text: str) -> str:
    """
    Detects language using Unicode script ranges:
    - Tamil: \u0B80-\u0BFF -> 'ta'
    - Hindi / Devanagari: \u0900-\u097F -> 'hi'
    - Default / Latin: 'en'
    """
    if not text:
        return "en"
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "ta"
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"
    return "en"

