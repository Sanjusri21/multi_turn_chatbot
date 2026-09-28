import { useChatContext } from '../context/ChatContext';

export function useConversations() {
  const {
    conversations,
    currentConversationId,
    setCurrentConversationId,
    createNewChat,
    deleteConversation,
    renameConversation,
    loadConversations,
  } = useChatContext();

  return {
    conversations,
    currentConversationId,
    setCurrentConversationId,
    createNewChat,
    deleteConversation,
    renameConversation,
    refreshConversations: loadConversations,
  };
}
