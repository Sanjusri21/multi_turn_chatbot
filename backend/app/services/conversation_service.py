from typing import List, Optional
from sqlalchemy.orm import Session
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.models.conversation import Conversation

class ConversationService:
    def __init__(self, db: Session):
        self.conv_repo = ConversationRepository(db)
        self.msg_repo = MessageRepository(db)

    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        return self.conv_repo.get(conversation_id, user_id=user_id)

    def list_conversations(self, user_id: str) -> List[Conversation]:
        return self.conv_repo.list_by_user(user_id)

    def create_conversation(self, user_id: str, title: Optional[str] = None) -> Conversation:
        clean_title = (title or "New Conversation").strip()
        return self.conv_repo.create(user_id=user_id, title=clean_title)

    def update_conversation(self, conversation_id: str, user_id: str, title: Optional[str] = None) -> Optional[Conversation]:
        return self.conv_repo.update(conversation_id, user_id=user_id, title=title)

    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        return self.conv_repo.delete(conversation_id, user_id=user_id)

    def search_conversations(self, user_id: str, query: str) -> List[Conversation]:
        return self.conv_repo.search(user_id=user_id, query=query)

    def auto_title_from_message(self, conversation_id: str, user_id: str, first_message: str) -> None:
        """Derives a friendly, concise title from the user's first message."""
        conv = self.conv_repo.get(conversation_id, user_id=user_id)
        if not conv or conv.title != "New Conversation":
            return

        cleaned = first_message.strip()
        # Clean common prefixes like 'can you explain', 'explain', 'what is', etc.
        import re
        simplified = re.sub(r"^(can you\s+)?(please\s+)?(explain|tell me about|what is|how to|describe)\s+", "", cleaned, flags=re.IGNORECASE).strip()
        display_text = simplified if simplified else cleaned

        if len(display_text) > 36:
            words = display_text.split()
            truncated = " ".join(words[:6])
            title = f"{truncated.title()}..."
        else:
            title = display_text.title() if len(display_text.split()) <= 4 else display_text

        self.conv_repo.update(conversation_id, user_id=user_id, title=title)

