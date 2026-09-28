import React, { useRef, useEffect } from 'react';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';
import { MessageInput } from './MessageInput';
import { WelcomeScreen } from './WelcomeScreen';
import { useChatContext } from '../../context/ChatContext';

export function ChatWindow() {
  const {
    messages,
    isSending,
    sendMessage,
    regenerateResponse,
  } = useChatContext();

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const lastAssistantIndex = messages.map((m) => m.role).lastIndexOf('assistant');
  const hasEmptyStreamingMessage = messages.some((m) => m.role === 'assistant' && !m.content);
  const showTypingIndicator = isSending && (messages.length === 0 || messages[messages.length - 1].role === 'user' || hasEmptyStreamingMessage);

  return (
    <div className="chat-main">
      {/* Messages Scroll Area */}
      <div className="messages-scroll-area">
        {messages.length === 0 ? (
          <WelcomeScreen onSelectPrompt={(prompt) => sendMessage(prompt)} />
        ) : (
          messages
            .filter((msg) => msg.role !== 'assistant' || msg.content) // don't show empty bubble before chunks arrive
            .map((msg, idx) => (
              <MessageBubble
                key={msg.id || idx}
                message={msg}
                isLastAssistant={idx === lastAssistantIndex}
                onRegenerate={(id) => regenerateResponse(id)}
                isRegenerating={Boolean(msg.isRegenerating)}
              />
            ))
        )}

        {showTypingIndicator && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <MessageInput onSendMessage={sendMessage} />
    </div>
  );
}
