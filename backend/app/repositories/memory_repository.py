from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.memory import Memory

class MemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, memory_id: str, user_id: str) -> Optional[Memory]:
        return self.db.query(Memory).filter(
            Memory.id == memory_id,
            Memory.user_id == user_id
        ).first()

    def get_by_key(self, user_id: str, key: str) -> Optional[Memory]:
        k_clean = key.strip().lower()
        aliases = [k_clean]
        if k_clean in ("project", "current_project", "my_project"):
            aliases = ["current_project", "project", "my_project"]
        elif k_clean in ("field_of_study", "education", "major", "degree"):
            aliases = ["field_of_study", "education", "major", "degree"]
        elif k_clean in ("technologies", "technology", "tech_stack", "skill", "skills"):
            aliases = ["technologies", "technology", "tech_stack", "skill", "skills"]
        elif k_clean in ("programming_language", "language", "favorite_language"):
            aliases = ["programming_language", "favorite_language", "language"]

        return self.db.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.key.in_(aliases)
        ).first()

    def list_by_user(self, user_id: str) -> List[Memory]:
        return self.db.query(Memory).filter(
            Memory.user_id == user_id
        ).order_by(Memory.category.asc(), Memory.key.asc()).all()

    def list_by_category(self, user_id: str, category: str) -> List[Memory]:
        return self.db.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.category == category.strip().lower()
        ).all()

    def create(
        self,
        user_id: str,
        key: str,
        value: str,
        category: str = "other",
        conversation_id: Optional[str] = None,
        source_conversation_id: Optional[str] = None,
        memory_text: Optional[str] = None,
        importance: Optional[str] = "normal"
    ) -> Memory:
        effective_source_conv = source_conversation_id or conversation_id
        effective_text = memory_text or f"{key.replace('_', ' ').title()}: {value.strip()}"
        cat_clean = (category or "other").strip().lower()
        memory = Memory(
            user_id=user_id,
            conversation_id=effective_source_conv,
            source_conversation_id=effective_source_conv,
            key=key.strip().lower(),
            value=value.strip(),
            memory_text=effective_text,
            memory_type=cat_clean,
            importance=importance or "normal",
            category=cat_clean
        )
        self.db.add(memory)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def upsert(
        self,
        user_id: str,
        key: str,
        value: str,
        category: str = "other",
        conversation_id: Optional[str] = None,
        source_conversation_id: Optional[str] = None,
        memory_text: Optional[str] = None,
        importance: Optional[str] = "normal"
    ) -> Memory:
        existing = self.get_by_key(user_id, key)
        effective_source_conv = source_conversation_id or conversation_id
        effective_text = memory_text or f"{key.replace('_', ' ').title()}: {value.strip()}"
        cat_clean = (category or "other").strip().lower()
        if existing:
            existing.value = value.strip()
            existing.memory_text = effective_text
            if category:
                existing.category = cat_clean
                existing.memory_type = cat_clean
            if effective_source_conv:
                existing.conversation_id = effective_source_conv
                existing.source_conversation_id = effective_source_conv
            if importance:
                existing.importance = importance
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            return self.create(
                user_id=user_id,
                key=key,
                value=value,
                category=cat_clean,
                conversation_id=effective_source_conv,
                source_conversation_id=effective_source_conv,
                memory_text=effective_text,
                importance=importance
            )

    def update(
        self,
        memory_id: str,
        user_id: str,
        key: Optional[str] = None,
        value: Optional[str] = None,
        category: Optional[str] = None,
        conversation_id: Optional[str] = None,
        source_conversation_id: Optional[str] = None,
        memory_text: Optional[str] = None,
        importance: Optional[str] = None
    ) -> Optional[Memory]:
        memory = self.get(memory_id, user_id=user_id)
        if not memory:
            return None
        if key is not None:
            memory.key = key.strip().lower()
        if value is not None:
            memory.value = value.strip()
            if not memory_text:
                memory.memory_text = f"{memory.key.replace('_', ' ').title()}: {value.strip()}"
        if memory_text is not None:
            memory.memory_text = memory_text
        if category is not None:
            cat_clean = category.strip().lower()
            memory.category = cat_clean
            memory.memory_type = cat_clean
        if conversation_id is not None:
            memory.conversation_id = conversation_id
        if source_conversation_id is not None:
            memory.source_conversation_id = source_conversation_id
        if importance is not None:
            memory.importance = importance
        memory.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(memory)
        return memory

    def retrieve_relevant(self, user_id: str, query: str, limit: int = 10) -> List[Memory]:
        """
        Retrieves persistent memories belonging to user_id relevant to query.
        Strictly isolated to user_id. Supports English, Tamil, and Hindi intent cues.
        """
        import re

        all_mems = self.list_by_user(user_id)
        if not all_mems:
            return []

        clean_query = (query or "").lower().strip()
        if not clean_query:
            return all_mems[:limit]

        # Extract alphanumeric and unicode word tokens
        tokens = [t.lower() for t in re.findall(r"[\w]+", clean_query) if len(t) >= 2]

        # Topic cue maps for cross-lingual intent detection
        is_project_query = any(k in clean_query for k in [
            "project", "திட்டம்", "பிராஜக்ட்", "प्रोजेक्ट", "परियोजना", "app", "application", "signaura", "alina"
        ])
        is_name_query = any(k in clean_query for k in [
            "name", "பெயர்", "நாம்", "नाम", "who am i", "call me"
        ])
        is_edu_query = any(k in clean_query for k in [
            "study", "studying", "learn", "learning", "college", "degree", "படிப்பு", "படி", "पढ़ाई", "सीख"
        ])
        is_tech_query = any(k in clean_query for k in [
            "python", "fastapi", "react", "code", "programming", "language", "tech", "தொழில்நுட்பம்", "भाषा", "प्रोग्रामिंग"
        ])
        is_broad_query = any(k in clean_query for k in [
            "remember", "know about me", "tell me about me", "என் பற்றி", "मेरे बारे में"
        ])

        scored = []
        for mem in all_mems:
            score = 0
            k_lower = (mem.key or "").lower()
            v_lower = (mem.value or "").lower()
            t_lower = (mem.memory_text or "").lower()
            c_lower = (mem.category or "").lower()

            # Cross-lingual intent boosts
            if is_project_query and ("project" in k_lower or c_lower == "project"):
                score += 15
            if is_name_query and (k_lower == "name" or c_lower == "personal" or c_lower == "identity"):
                score += 15
            if is_edu_query and (c_lower == "education" or "study" in k_lower or "major" in k_lower):
                score += 15
            if is_tech_query and (c_lower == "technology" or "tech" in k_lower or "language" in k_lower):
                score += 15

            # Direct token overlap
            for token in tokens:
                if token in k_lower:
                    score += 5
                if token in v_lower:
                    score += 8
                if token in t_lower:
                    score += 4
                if token in c_lower:
                    score += 3

            # Importance boost
            if mem.importance == "high":
                score += 2

            # If broad query or small memory set, give base score
            if is_broad_query or len(all_mems) <= 8:
                score += 1

            if score > 0:
                scored.append((score, mem))

        if not scored:
            # If no specific match found, fallback to all user memories up to limit
            return all_mems[:limit]

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:limit]]


    def delete(self, memory_id: str, user_id: str) -> bool:
        memory = self.get(memory_id, user_id=user_id)
        if not memory:
            return False
        self.db.delete(memory)
        self.db.commit()
        return True

    def delete_all(self, user_id: str) -> int:
        count = self.db.query(Memory).filter(Memory.user_id == user_id).delete()
        self.db.commit()
        return count
