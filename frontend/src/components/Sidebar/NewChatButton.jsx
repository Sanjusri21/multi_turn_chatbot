import React from 'react';
import { Plus } from 'lucide-react';
import { useChatContext } from '../../context/ChatContext';

export function NewChatButton() {
  const { createNewChat } = useChatContext();

  return (
    <button className="new-chat-btn" onClick={createNewChat}>
      <Plus size={18} strokeWidth={2.5} />
      <span>New Conversation</span>
    </button>
  );
}
