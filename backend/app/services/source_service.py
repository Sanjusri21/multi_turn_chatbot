import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.schemas.chat_schema import SearchSourceItem
from app.core.logging_config import logger

# Authoritative domain patterns and reputation weighting
AUTHORITATIVE_PATTERNS = [
    # Government & Legislative
    (r"\b(?:[a-zA-Z0-9-]+\.)?gov(?:\.[a-zA-Z]{2,3})?\b", 3.0),
    (r"\b(?:[a-zA-Z0-9-]+\.)?nic\.in\b", 3.0),
    (r"\b(?:[a-zA-Z0-9-]+\.)?assembly\.tn\.gov\.in\b", 3.5),
    (r"\b(?:[a-zA-Z0-9-]+\.)?tn\.gov\.in\b", 3.5),
    (r"\b(?:[a-zA-Z0-9-]+\.)?india\.gov\.in\b", 3.5),
    (r"\b(?:[a-zA-Z0-9-]+\.)?parliament\.nic\.in\b", 3.5),
    (r"\b(?:[a-zA-Z0-9-]+\.)?eci\.gov\.in\b", 3.5),
    
    # Official Tech Documentation & Repositories
    (r"\b(?:docs\.)?python\.org\b", 3.0),
    (r"\bgithub\.com\b", 2.5),
    (r"\bdeveloper\.mozilla\.org\b", 2.8),
    (r"\b(?:[a-zA-Z0-9-]+\.)?openai\.com\b", 2.8),
    (r"\b(?:[a-zA-Z0-9-]+\.)?anthropic\.com\b", 2.8),
    (r"\b(?:[a-zA-Z0-9-]+\.)?google\.com\b", 2.5),
    
    # Reputable News & Reference Organizations
    (r"\bthehindu\.com\b", 2.2),
    (r"\bindianexpress\.com\b", 2.0),
    (r"\bndtv\.com\b", 1.9),
    (r"\btimesofindia\.indiatimes\.com\b", 1.8),
    (r"\breuters\.com\b", 2.5),
    (r"\bapnews\.com\b", 2.5),
    (r"\bbbc\.com\b", 2.4),
    (r"\ben\.wikipedia\.org\b", 1.5),
    (r"\biplt20\.com\b", 2.8),
    (r"\bespncricinfo\.com\b", 2.5),
    (r"\bcoingecko\.com\b", 2.5),
]

class SourceService:
    @staticmethod
    def clean_url(raw_url: str) -> str:
        """Strips tracking query parameters (utm_*, ref, etc.) and fragments."""
        if not raw_url:
            return ""
        try:
            parsed = urlparse(raw_url.strip())
            if not parsed.scheme or not parsed.netloc:
                return raw_url.strip()
            # Strip common analytics parameters
            query_params = parse_qs(parsed.query, keep_blank_values=False)
            filtered_params = {
                k: v for k, v in query_params.items()
                if not k.lower().startswith(("utm_", "ref", "fbclid", "gclid", "yclid", "_ga"))
            }
            cleaned_query = urlencode(filtered_params, doseq=True)
            cleaned = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path.rstrip("/") if parsed.path != "/" else "/",
                parsed.params,
                cleaned_query,
                ""  # drop fragment
            ))
            return cleaned
        except Exception:
            return raw_url.strip()

    @staticmethod
    def extract_domain(url: str) -> str:
        """Extracts clean human-readable domain name from URL."""
        if not url:
            return ""
        try:
            netloc = urlparse(url).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    @classmethod
    def calculate_authority_score(cls, url: str, base_score: float = 1.0) -> float:
        """Calculates authority weighting score based on official and reputable domain patterns."""
        score = base_score
        url_lower = url.lower()
        for pattern, weight in AUTHORITATIVE_PATTERNS:
            if re.search(pattern, url_lower):
                score = max(score, weight)
        return round(score, 2)

    @classmethod
    def normalize_sources(
        cls,
        raw_results: List[Any],
        max_results: int = 5
    ) -> List[SearchSourceItem]:
        """
        Normalizes search results:
        - Validates HTTP/HTTPS URLs
        - Strips tracking tokens
        - Deduplicates by URL and normalized title
        - Boosts authoritative sources
        - Limits to max_results to maintain optimal Gemini context size
        """
        seen_urls = set()
        seen_titles = set()
        normalized_items: List[SearchSourceItem] = []

        for item in raw_results:
            # Handle dict, SearchSourceItem, or object with attributes
            if isinstance(item, dict):
                title = (item.get("title") or "").strip()
                raw_url = (item.get("url") or "").strip()
                snippet = (item.get("snippet") or item.get("content") or "").strip()
                source_name = item.get("source_name")
                published_at = item.get("published_at")
                base_score = float(item.get("relevance_score") or 1.0)
            else:
                title = getattr(item, "title", "").strip()
                raw_url = getattr(item, "url", "").strip()
                snippet = (getattr(item, "snippet", "") or getattr(item, "content", "")).strip()
                source_name = getattr(item, "source_name", None)
                published_at = getattr(item, "published_at", None)
                base_score = float(getattr(item, "relevance_score", 1.0) or 1.0)

            # Skip results lacking required attributes
            if not title or not raw_url or not snippet:
                continue

            # Must be a valid web URL
            if not (raw_url.startswith("http://") or raw_url.startswith("https://")):
                continue

            cleaned_url = cls.clean_url(raw_url)
            if not cleaned_url or cleaned_url in seen_urls:
                continue

            # Title normalization for deduplication
            clean_title_key = re.sub(r"[^\w\s]", "", title.lower()).strip()
            if not clean_title_key or clean_title_key in seen_titles:
                continue

            seen_urls.add(cleaned_url)
            seen_titles.add(clean_title_key)

            domain = cls.extract_domain(cleaned_url)
            final_source_name = source_name or domain or "Web Source"
            relevance_score = cls.calculate_authority_score(cleaned_url, base_score)

            normalized_items.append(
                SearchSourceItem(
                    title=title,
                    url=cleaned_url,
                    snippet=snippet,
                    source_name=final_source_name,
                    published_at=str(published_at) if published_at else None,
                    relevance_score=relevance_score
                )
            )

        # Sort by relevance score descending
        normalized_items.sort(key=lambda s: s.relevance_score or 0.0, reverse=True)
        return normalized_items[:max_results]

    @classmethod
    def format_sources_for_prompt(cls, sources: List[SearchSourceItem]) -> str:
        """
        Constructs the source-aware context directive for Gemini prompt.
        Follows strict prompt engineering to prevent model hallucination and enforce source reliance.
        """
        if not sources:
            return ""

        parts = [
            "REAL-TIME INFORMATION RULE:",
            "The following information was retrieved from current web sources.",
            "",
            "Use the retrieved sources when answering the user's current-information question.",
            "Do not claim that you know something from your internal knowledge when the answer is based on retrieved sources.",
            "Do not invent facts that are not supported by the retrieved information.",
            "",
            "If the sources disagree:",
            "- identify the disagreement",
            "- prefer authoritative and recent sources",
            "- do not silently combine conflicting claims.",
            "",
            "If the retrieved information is insufficient:",
            "say that the available sources do not provide enough information.",
            "",
            "Retrieved sources:"
        ]

        for i, src in enumerate(sources, 1):
            source_block = f"Source {i}: {src.title} (Domain: {src.source_name or cls.extract_domain(src.url)})"
            if src.published_at:
                source_block += f" [Published: {src.published_at}]"
            source_block += f"\nURL: {src.url}\nContent: {src.snippet}"
            parts.append(source_block)

        return "\n".join(parts)

    @classmethod
    def format_citations_markdown(cls, sources: List[SearchSourceItem]) -> str:
        """
        Formats clean, clickable markdown citations for the end of a response.
        Ensures all URLs are authentic and clickable.
        """
        if not sources:
            return ""

        lines = ["\n\n**Sources:**"]
        for i, src in enumerate(sources, 1):
            domain = src.source_name or cls.extract_domain(src.url)
            title = src.title.replace("[", "").replace("]", "")
            date_str = f" ({src.published_at})" if src.published_at else ""
            lines.append(f"{i}. [{title}]({src.url}) — {domain}{date_str}")

        return "\n".join(lines)
