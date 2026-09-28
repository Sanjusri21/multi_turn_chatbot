import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.core.logging_config import logger

class IntentResult(BaseModel):
    intent_type: str  # "NORMAL", "MEMORY", "REAL_TIME", "REAL_TIME_API"
    requires_realtime: bool
    category: Optional[str] = None  # "weather", "crypto", "sports", "news", "government", "general"
    search_query: str
    confidence: float = 1.0

class IntentService:
    """
    Modular Intent and Freshness Detection Service.
    Accurately classifies queries without triggering web search for normal questions
    or memory retrievals.
    """

    # Time-sensitive keywords & temporal triggers
    TEMPORAL_PATTERNS = [
        r"\bcurrent\b",
        r"\bcurrently\b",
        r"\btoday\b",
        r"\btonight\b",
        r"\bnow\b",
        r"\blatest\b",
        r"\brecent\b",
        r"\brecently\b",
        r"\bthis week\b",
        r"\bthis month\b",
        r"\bthis year\b",
        r"\blive\b",
        r"\breal-?time\b",
        r"\bas of today\b",
        r"\bas of now\b",
        r"\bbreaking news\b",
        r"\bheadlines?\b",
        r"\bwhat is happening\b",
        r"\bwhat happened\b",
        r"\bwho is the current\b",
        r"\bwho is currently\b",
        r"\bwho won\b",
        r"\bscore of\b",
        r"\bmatch score\b",
        r"\bwho is leading\b",
        r"\bcurrent status\b",
        r"\bcurrent price\b",
        r"\bweather\b",
        r"\btemperature\b",
        r"\bstock price\b",
        r"\bwho is the (?:chief minister|cm|prime minister|pm|president|governor|ceo)\b"
    ]

    # Tamil Time-sensitive keywords
    TAMIL_TEMPORAL_PATTERNS = [
        r"தற்போதைய",
        r"இன்றைய",
        r"இப்போதைய",
        r"சமீபத்திய",
        r"இன்று",
        r"இப்போது",
        r"நேரலை",
        r"லைவ்",
        r"யார்\s+(?:முதலமைச்சர்|பிரதமர்|ஆளுநர்|தலைவர்)",
        r"வானிலை",
        r"விலை",
        r"நடப்பு"
    ]

    # Hindi Time-sensitive keywords
    HINDI_TEMPORAL_PATTERNS = [
        r"वर्तमान",
        r"आज",
        r"अभी",
        r"ताजा",
        r"नवीनतम",
        r"हाल\s+ही\s+में",
        r"लाइव",
        r"मौसम",
        r"तापमान",
        r"कीमत",
        r"भाव",
        r"कौन\s+हैं\s+(?:मुख्यमंत्री|प्रधानमंत्री|राष्ट्रपति)"
    ]

    # Memory-specific triggers (Should NOT trigger web search)
    MEMORY_TRIGGERS = [
        r"\bwhat did i tell you\b",
        r"\bwhat was my\b",
        r"\bwhat is my name\b",
        r"\bdo you remember\b",
        r"\bremember that\b",
        r"\bmy name is\b",
        r"\bmy project\b",
        r"\bwe discussed yesterday\b",
        r"\bcontinue the project\b",
        r"\bwhat do you know about me\b",
        r"\bwhat do you remember\b",
        r"\bmy favorite\b",
        r"\bwhere do i study\b",
        r"\bwhat am i studying\b",
        # Tamil Memory
        r"என்\s+(?:பெயர்|திட்டம்|ப்ராஜெக்ட்)",
        r"என்னுடைய\s+(?:பெயர்|திட்டம்)",
        r"நினைவிருக்கிறதா",
        r"நான்\s+சொன்ன",
        # Hindi Memory
        r"मेरा\s+(?:नाम|प्रोजेक्ट)",
        r"याद\s+है",
        r"मैंने\s+बताया"
    ]

    # Conversational / Greetings / Banter (Should NOT trigger web search)
    CONVERSATIONAL_PATTERNS = [
        r"^(?:hello|hi|hey)\s*(?:zara|there)?\s*[!.]*$",
        r"^(?:hello|hi|hey)?\s*,?\s*how are you(?:\s+doing)?(?:\s+today)?[?!.]*$",
        r"^good\s+(?:morning|afternoon|evening|night)\b",
        r"^who are you",
        r"^what can you do",
        r"^thank(?:s|\s+you)",
        r"^bye\b",
        r"^வணக்கம்",
        r"^நன்றி",
        r"^नमस्ते",
        r"^धन्यवाद"
    ]

    # Pure academic / static knowledge patterns (Should NOT trigger web search)
    STATIC_KNOWLEDGE_PATTERNS = [
        r"^what is (?:a |an )?[a-zA-Z\s]+$",  # e.g. "what is python", "what is a cnn", "what is machine learning"
        r"^explain [a-zA-Z\s]+$",              # e.g. "explain cnn", "explain quicksort"
        r"^define [a-zA-Z\s]+$",               # e.g. "define polymorphism"
        r"^how (?:does|do) [a-zA-Z\s]+ work$",  # e.g. "how does cnn work"
        r"^write a (?:python|java|c\+\+|javascript)?\s*(?:function|script|code|program)\b",
        r"^difference between [a-zA-Z\s]+ and [a-zA-Z\s]+$",
        r"^solve\b"
    ]

    def detect_intent(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        language: Optional[str] = None
    ) -> IntentResult:
        """
        Determines query intent and whether live external sources are needed.
        """
        q = query.strip()
        q_lower = q.lower()

        # 1. Check conversational greetings & small talk first
        for pat in self.CONVERSATIONAL_PATTERNS:
            if re.search(pat, q_lower):
                logger.info(f"[Intent] Match conversational: {q[:30]}")
                return IntentResult(
                    intent_type="NORMAL",
                    requires_realtime=False,
                    category="conversational",
                    search_query=q
                )

        # 2. Check personal memory queries
        for pat in self.MEMORY_TRIGGERS:
            if re.search(pat, q_lower):
                logger.info(f"[Intent] Match memory trigger: {q[:30]}")
                return IntentResult(
                    intent_type="MEMORY",
                    requires_realtime=False,
                    category="memory",
                    search_query=q
                )

        # 3. Check for static programming/conceptual questions ("What is Python?", "Explain CNN.")
        # But ensure it doesn't contain freshness words like "latest version of Python" or "today"
        is_freshness_question = any(re.search(p, q_lower) for p in self.TEMPORAL_PATTERNS)
        if not is_freshness_question:
            for pat in self.STATIC_KNOWLEDGE_PATTERNS:
                if re.search(pat, q_lower):
                    logger.info(f"[Intent] Match static conceptual: {q[:30]}")
                    return IntentResult(
                        intent_type="NORMAL",
                        requires_realtime=False,
                        category="knowledge",
                        search_query=q
                    )

        # 4. Check Specialized Real-time categories (weather, crypto)
        if re.search(r"\b(?:weather|temperature|forecast|climate)\b|வானிலை|मौसम|तापमान", q_lower):
            logger.info(f"[Intent] Match specialized weather: {q[:30]}")
            return IntentResult(
                intent_type="REAL_TIME_API",
                requires_realtime=True,
                category="weather",
                search_query=q
            )

        if re.search(r"\b(?:bitcoin|btc|ethereum|eth|solana|crypto(?:currency)?)\s+(?:price|rate|value|today|now)\b", q_lower) or \
           re.search(r"\b(?:current\s+)?(?:bitcoin|crypto)\s+price\b", q_lower):
            logger.info(f"[Intent] Match specialized crypto: {q[:30]}")
            return IntentResult(
                intent_type="REAL_TIME_API",
                requires_realtime=True,
                category="crypto",
                search_query=q
            )

        # 5. Check English freshness patterns
        if is_freshness_question:
            category = self._classify_category(q_lower)
            optimized_query = self._optimize_search_query(q, "en")
            logger.info(f"[Intent] realtime=true category={category} query='{optimized_query}'")
            return IntentResult(
                intent_type="REAL_TIME",
                requires_realtime=True,
                category=category,
                search_query=optimized_query
            )

        # 6. Check Tamil freshness patterns
        for pat in self.TAMIL_TEMPORAL_PATTERNS:
            if re.search(pat, q):
                category = self._classify_category(q)
                optimized_query = self._optimize_search_query(q, "ta")
                logger.info(f"[Intent] realtime=true (Tamil) category={category} query='{optimized_query}'")
                return IntentResult(
                    intent_type="REAL_TIME",
                    requires_realtime=True,
                    category=category,
                    search_query=optimized_query
                )

        # 7. Check Hindi freshness patterns
        for pat in self.HINDI_TEMPORAL_PATTERNS:
            if re.search(pat, q):
                category = self._classify_category(q)
                optimized_query = self._optimize_search_query(q, "hi")
                logger.info(f"[Intent] realtime=true (Hindi) category={category} query='{optimized_query}'")
                return IntentResult(
                    intent_type="REAL_TIME",
                    requires_realtime=True,
                    category=category,
                    search_query=optimized_query
                )

        # 8. Check semantic current officeholder questions even without explicit "current" word
        # e.g., "Who is the Chief Minister of Tamil Nadu?", "Who is the Prime Minister of the UK?"
        officeholder_match = re.search(
            r"\bwho is the (?:chief minister|cm|prime minister|pm|president|governor|chancellor|ceo|pope)\s+of\s+([A-Za-z\s]+?)[?.]*$",
            q_lower
        )
        if officeholder_match:
            entity = officeholder_match.group(1).strip()
            optimized_query = f"current {q_lower.replace('?', '').strip()}"
            logger.info(f"[Intent] realtime=true semantic officeholder query='{optimized_query}'")
            return IntentResult(
                intent_type="REAL_TIME",
                requires_realtime=True,
                category="government",
                search_query=optimized_query
            )

        # Default: Normal knowledge request
        return IntentResult(
            intent_type="NORMAL",
            requires_realtime=False,
            category="general",
            search_query=q
        )

    def _classify_category(self, q: str) -> str:
        q_lower = q.lower()
        if any(w in q_lower for w in ["chief minister", "cm", "prime minister", "pm", "president", "government", "election", "assembly", "முதலமைச்சர்", "मुख्यमंत्री"]):
            return "government"
        if any(w in q_lower for w in ["weather", "temperature", "rain", "வானிலை", "मौसम"]):
            return "weather"
        if any(w in q_lower for w in ["price", "stock", "bitcoin", "crypto", "market"]):
            return "finance"
        if any(w in q_lower for w in ["match", "ipl", "score", "cricket", "football", "cup"]):
            return "sports"
        if any(w in q_lower for w in ["python", "version", "release", "model", "openai", "gemini"]):
            return "technology"
        if any(w in q_lower for w in ["news", "headline", "breaking"]):
            return "news"
        return "general"

    def _optimize_search_query(self, query: str, lang: str) -> str:
        """
        Translates or structures search queries for maximum retrieval accuracy
        from web search engines while preserving entity context.
        """
        q = query.strip()
        # Handle specific common Tamil real-time queries for optimal web retrieval
        if "தமிழ்நாடு" in q and ("முதலமைச்சர்" in q or "முதல்வர்" in q):
            return "Tamil Nadu current Chief Minister official"
        if "இந்தியா" in q and "பிரதமர்" in q:
            return "India current Prime Minister official"
        if "வானிலை" in q:
            return f"current weather {q.replace('வானிலை', '').replace('இன்றைய', '').strip()}"

        # Handle Hindi queries
        if "तमिलनाडु" in q and "मुख्यमंत्री" in q:
            return "Tamil Nadu current Chief Minister official"
        if "भारत" in q and "प्रधानमंत्री" in q:
            return "India current Prime Minister official"

        # English queries: clean punctuation
        cleaned = re.sub(r"[?!.,]", "", q).strip()
        return cleaned
