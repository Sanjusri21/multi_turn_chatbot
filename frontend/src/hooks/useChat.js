import { useChatContext } from '../context/ChatContext';

export function useChat() {
  const {
    messages,
    isSending,
    isTyping,
    setIsTyping,
    sendMessage,
    currentConversationId,
    activeDocumentId,
    setActiveDocumentId,
  } = useChatContext();

  return {
    messages,
    isSending,
    isTyping,
    setIsTyping,
    sendMessage,
    currentConversationId,
    activeDocumentId,
    setActiveDocumentId,
  };
}
