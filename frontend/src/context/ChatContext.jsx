import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { chatApi } from '../services/chatApi';
import { memoryApi } from '../services/memoryApi';
import { settingsApi } from '../services/settingsApi';
import { ttsService, speakText, stopSpeaking as stopTTS } from '../services/ttsService';
import { useAuth } from '../hooks/useAuth';

const ChatContext = createContext(null);

export function ChatProvider({ children }) {
  const { isAuthenticated, user } = useAuth();

  // Conversations & Messages
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [searchingStatus, setSearchingStatus] = useState(null);

  // Memories
  const [memories, setMemories] = useState([]);

  // User Settings
  const [userSettings, setUserSettings] = useState(() => {
    const savedRobot = localStorage.getItem('show_floating_robot');
    return {
      theme: 'dark',
      language: 'en',
      response_style: 'balanced',
      enter_behavior: 'send',
      accent_style: 'blue_violet',
      animations_enabled: true,
      memory_enabled: true,
      auto_save_memory: true,
      show_floating_robot: savedRobot !== null ? savedRobot === 'true' : true,
    };
  });

  // Zara Multilingual & TTS state
  const [selectedLanguage, setSelectedLanguageState] = useState(() => {
    return localStorage.getItem('zara_language') || 'en';
  });
  const [autoVoiceEnabled, setAutoVoiceEnabledState] = useState(() => {
    const saved = localStorage.getItem('zara_auto_voice');
    return saved !== null ? saved === 'true' : true;
  });
  const [ttsPlayingMessageId, setTtsPlayingMessageId] = useState(null);

  const setSelectedLanguage = useCallback((lang) => {
    setSelectedLanguageState(lang);
    localStorage.setItem('zara_language', lang);
  }, []);

  const setAutoVoiceEnabled = useCallback((enabled) => {
    setAutoVoiceEnabledState(enabled);
    localStorage.setItem('zara_auto_voice', enabled ? 'true' : 'false');
  }, []);

  const speakMessage = useCallback((messageId, text, language = null) => {
    const langToUse = language || selectedLanguage;
    console.log("TTS input text:", text);
    console.log("TTS selected language:", langToUse);
    speakText(text, langToUse, { messageId });
  }, [selectedLanguage]);

  const stopSpeaking = useCallback(() => {
    stopTTS();
  }, []);

  const pauseSpeaking = useCallback(() => {
    ttsService.pause();
  }, []);

  const resumeSpeaking = useCallback(() => {
    ttsService.resume();
  }, []);

  useEffect(() => {
    const unsubscribe = ttsService.subscribe(({ state, messageId }) => {
      if (state === 'speaking') {
        setTtsPlayingMessageId(messageId);
      } else if (state === 'paused') {
        setTtsPlayingMessageId(messageId);
      } else {
        setTtsPlayingMessageId(null);
      }
    });
    return unsubscribe;
  }, []);

  // RotoBot Robot State (maintained for welcome page / status)
  const [rotoBotState, setRotoBotState] = useState('IDLE');
  const [rotoBotBubble, setRotoBotBubble] = useState(null);

  // Toast notifications
  const [toasts, setToasts] = useState([]);

  // Stream abort controller ref
  const abortControllerRef = useRef(null);

  // Inactivity tracking
  const idleTimerRef = useRef(null);
  const returnIdleTimerRef = useRef(null);

  const showToast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  // Connect TTS warning handler to show user-friendly toasts when voices are missing
  useEffect(() => {
    ttsService.setWarningHandler((msg) => {
      showToast(msg, 'warning');
    });
  }, [showToast]);

  const triggerRotoBotReaction = useCallback((state, bubbleText = null, returnAfterMs = 4000) => {
    setRotoBotState(state);
    if (bubbleText) setRotoBotBubble(bubbleText);

    if (returnIdleTimerRef.current) clearTimeout(returnIdleTimerRef.current);
    if (returnAfterMs && state !== 'IDLE' && state !== 'SLEEPING') {
      returnIdleTimerRef.current = setTimeout(() => {
        setRotoBotState('IDLE');
        setRotoBotBubble(null);
      }, returnAfterMs);
    }
  }, []);

  const resetInactivityTimer = useCallback(() => {
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    idleTimerRef.current = setTimeout(() => {
      setRotoBotState('SLEEPING');
    }, 90000);
  }, []);

  // Load User Settings
  const loadSettings = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await settingsApi.getSettings();
      const savedRobot = localStorage.getItem('show_floating_robot');
      setUserSettings((prev) => ({
        ...prev,
        ...data,
        show_floating_robot: savedRobot !== null ? savedRobot === 'true' : true,
      }));
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  }, [isAuthenticated]);

  const updateUserSettings = async (updates) => {
    if ('show_floating_robot' in updates) {
      localStorage.setItem('show_floating_robot', updates.show_floating_robot ? 'true' : 'false');
    }
    setUserSettings((prev) => ({ ...prev, ...updates }));

    const { show_floating_robot, ...backendUpdates } = updates;
    if (Object.keys(backendUpdates).length > 0) {
      try {
        const updated = await settingsApi.updateSettings(backendUpdates);
        setUserSettings((prev) => ({ ...prev, ...updated }));
        showToast('Settings saved', 'success');
      } catch (err) {
        showToast('Failed to save settings', 'error');
      }
    } else {
      showToast('Settings saved', 'success');
    }
  };

  // Sync Theme & Animations with HTML body
  useEffect(() => {
    const theme = userSettings.theme || 'dark';
    if (theme === 'light') {
      document.body.classList.add('theme-light');
      document.body.classList.remove('theme-dark');
    } else if (theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (prefersDark) {
        document.body.classList.add('theme-dark');
        document.body.classList.remove('theme-light');
      } else {
        document.body.classList.add('theme-light');
        document.body.classList.remove('theme-dark');
      }
    } else {
      document.body.classList.add('theme-dark');
      document.body.classList.remove('theme-light');
    }

    if (userSettings.animations_enabled === false) {
      document.body.classList.add('no-animations');
    } else {
      document.body.classList.remove('no-animations');
    }
  }, [userSettings.theme, userSettings.animations_enabled]);

  // Load conversations & memories
  const loadConversations = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await chatApi.getConversations();
      setConversations(data);
      if (data.length > 0 && !currentConversationId) {
        setCurrentConversationId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, [isAuthenticated, currentConversationId]);

  const loadMemories = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await memoryApi.getMemories();
      setMemories(data);
    } catch (err) {
      console.error('Failed to load memories:', err);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      loadSettings();
      loadConversations();
      loadMemories();
      resetInactivityTimer();
    } else {
      setConversations([]);
      setMessages([]);
      setMemories([]);
      setCurrentConversationId(null);
    }

    const handleUserActivity = () => resetInactivityTimer();
    window.addEventListener('mousemove', handleUserActivity);
    window.addEventListener('keydown', handleUserActivity);

    return () => {
      window.removeEventListener('mousemove', handleUserActivity);
      window.removeEventListener('keydown', handleUserActivity);
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
      if (returnIdleTimerRef.current) clearTimeout(returnIdleTimerRef.current);
    };
  }, [isAuthenticated]);

  // Load messages for active conversation
  useEffect(() => {
    if (!currentConversationId || !isAuthenticated) {
      setMessages([]);
      return;
    }

    const fetchDetail = async () => {
      try {
        const detail = await chatApi.getConversation(currentConversationId);
        setMessages(detail.messages || []);
      } catch (err) {
        console.error('Failed to load messages for conversation:', err);
      }
    };
    fetchDetail();
  }, [currentConversationId, isAuthenticated]);

  const createNewChat = async () => {
    try {
      const newConv = await chatApi.createConversation("New Conversation");
      setConversations((prev) => [newConv, ...prev]);
      setCurrentConversationId(newConv.id);
      setMessages([]);
    } catch (err) {
      showToast('Failed to create new conversation', 'error');
    }
  };

  const deleteConversation = async (id) => {
    try {
      await chatApi.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (currentConversationId === id) {
        const remaining = conversations.filter((c) => c.id !== id);
        setCurrentConversationId(remaining.length > 0 ? remaining[0].id : null);
        setMessages([]);
      }
      showToast('Conversation deleted', 'info');
    } catch (err) {
      showToast('Failed to delete conversation', 'error');
    }
  };

  const renameConversation = async (id, newTitle) => {
    try {
      const updated = await chatApi.updateConversation(id, newTitle);
      setConversations((prev) => prev.map((c) => (c.id === id ? updated : c)));
      showToast('Conversation renamed', 'success');
    } catch (err) {
      showToast('Failed to rename conversation', 'error');
    }
  };

  const stopGenerating = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setSearchingStatus(null);
    setIsSending(false);
  };

  const sendMessage = async (content, attachments = []) => {
    const text = content ? content.trim() : '';
    if ((!text && attachments.length === 0) || isSending) return;

    resetInactivityTimer();
    setIsSending(true);

    const attachmentIds = attachments.map((a) => a.id);
    const userDisplayContent = text || (attachments.length > 0 ? `Sent ${attachments.length} attachment(s)` : '');

    const tempUserMsgId = `temp-${Date.now()}`;
    const streamingAssistantId = `stream-${Date.now()}`;

    const tempUserMsg = {
      id: tempUserMsgId,
      conversation_id: currentConversationId,
      role: 'user',
      content: userDisplayContent,
      attachments: attachments,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let hasReceivedChunk = false;
    let accumulatedContent = '';

    try {
      // 1. Attempt streaming via SSE
      await chatApi.streamMessage({
        message: text || `Analyze the attached file(s): ${attachments.map((a) => a.filename).join(', ')}`,
        conversation_id: currentConversationId,
        attachment_ids: attachmentIds.length > 0 ? attachmentIds : null,
        language: selectedLanguage,
        signal: controller.signal,
        onInit: (initData) => {
          if (!currentConversationId || currentConversationId !== initData.conversation_id) {
            setCurrentConversationId(initData.conversation_id);
          }
          // Replace temp user message with persisted user message and add empty streaming bubble
          setMessages((prev) => [
            ...prev.filter((m) => m.id !== tempUserMsgId),
            initData.user_message,
            {
              id: streamingAssistantId,
              conversation_id: initData.conversation_id,
              role: 'assistant',
              content: '',
              timestamp: new Date().toISOString(),
            }
          ]);
        },
        onStatus: (statusData) => {
          setSearchingStatus(statusData);
        },
        onChunk: (chunk) => {
          hasReceivedChunk = true;
          setSearchingStatus(null);
          accumulatedContent += chunk;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamingAssistantId
                ? { ...m, content: accumulatedContent }
                : m
            )
          );
        },
        onDone: (doneData) => {
          setSearchingStatus(null);
          const assistantResponse = doneData.assistant_message?.content || doneData.response || '';
          console.log("Selected chat language:", selectedLanguage);
          console.log("Assistant response:", assistantResponse);

          setMessages((prev) => [
            ...prev.filter((m) => m.id !== streamingAssistantId),
            {
              ...doneData.assistant_message,
              language: doneData.language,
              memory_used: doneData.memory_used,
              extracted_memories: doneData.extracted_memories,
              sources: doneData.sources || doneData.assistant_message?.sources,
              is_realtime: doneData.is_realtime,
            }
          ]);

          loadConversations();
          loadMemories();

          if (doneData.extracted_memories && doneData.extracted_memories.length > 0) {
            const memorySummary = doneData.extracted_memories.map((m) => `${m.key}: ${m.value}`).join(', ');
            showToast(`✨ Memory saved: ${memorySummary}`, 'success');
          }

          // Zara Auto Voice output
          if (autoVoiceEnabled && assistantResponse) {
            console.log("TTS input text:", assistantResponse);
            console.log("TTS selected language:", selectedLanguage);
            speakText(
              assistantResponse,
              selectedLanguage,
              { messageId: doneData.assistant_message?.id }
            );
          }
        },
        onError: async (err) => {
          setSearchingStatus(null);
          if (controller.signal.aborted) return;
          console.warn('Streaming error:', err);

          const isQuota =
            err.code === 429 ||
            err.error_type === 'quota_exhausted' ||
            /quota|resource_exhausted|429/i.test(err.message || '');

          if (isQuota) {
            const quotaMsg =
              err.message ||
              "Zara is temporarily unavailable because the Gemini API quota has been exhausted. Please try again after the quota resets.";
            showToast(quotaMsg, 'error');
            setMessages((prev) => [
              ...prev.filter((m) => m.id !== streamingAssistantId),
              {
                id: `err-${Date.now()}`,
                role: 'assistant',
                content: `⚠️ ${quotaMsg}`,
                timestamp: new Date().toISOString(),
              }
            ]);
            return;
          }

          // If stream failed before any chunk, fallback to standard synchronous endpoint
          if (!hasReceivedChunk) {
            try {
              const fallbackResponse = await chatApi.sendMessage({
                message: text || `Analyze the attached file(s): ${attachments.map((a) => a.filename).join(', ')}`,
                conversation_id: currentConversationId,
                attachment_ids: attachmentIds.length > 0 ? attachmentIds : null,
                language: selectedLanguage,
              });

              const assistantResponse = fallbackResponse.assistant_message?.content || fallbackResponse.response || '';
              console.log("Selected chat language:", selectedLanguage);
              console.log("Assistant response:", assistantResponse);

              if (!currentConversationId || currentConversationId !== fallbackResponse.conversation_id) {
                setCurrentConversationId(fallbackResponse.conversation_id);
              }

              setMessages((prev) => [
                ...prev.filter((m) => m.id !== tempUserMsgId && m.id !== streamingAssistantId),
                fallbackResponse.user_message,
                {
                  ...fallbackResponse.assistant_message,
                  language: fallbackResponse.language,
                  memory_used: fallbackResponse.memory_used,
                  extracted_memories: fallbackResponse.extracted_memories,
                  sources: fallbackResponse.sources || fallbackResponse.assistant_message?.sources,
                  is_realtime: fallbackResponse.is_realtime,
                },
              ]);

              loadConversations();
              loadMemories();
              if (fallbackResponse.extracted_memories?.length > 0) {
                const memList = fallbackResponse.extracted_memories.map((m) => `${m.key}: ${m.value}`).join(', ');
                showToast(`✨ Memory saved: ${memList}`, 'success');
              }

              // Zara Auto Voice output
              if (autoVoiceEnabled && assistantResponse) {
                console.log("TTS input text:", assistantResponse);
                console.log("TTS selected language:", selectedLanguage);
                speakText(
                  assistantResponse,
                  selectedLanguage,
                  { messageId: fallbackResponse.assistant_message?.id }
                );
              }
              return;
            } catch (fallbackErr) {
              console.error('Fallback chat error:', fallbackErr);
              const isFallbackQuota = /quota|resource_exhausted|429/i.test(fallbackErr.message || '');
              const displayMsg = isFallbackQuota
                ? (fallbackErr.message || "Zara is temporarily unavailable because the Gemini API quota has been exhausted. Please try again after the quota resets.")
                : (fallbackErr.message || "Zara couldn't reach the AI service. Please check your connection or try again.");
              showToast(displayMsg, 'error');
              setMessages((prev) => [
                ...prev.filter((m) => m.id !== streamingAssistantId),
                {
                  id: `err-${Date.now()}`,
                  role: 'assistant',
                  content: `⚠️ ${displayMsg}`,
                  timestamp: new Date().toISOString(),
                }
              ]);
              return;
            }
          }

          const friendlyMsg = err.message || "The response stream was interrupted. Try regenerating the response.";
          showToast(friendlyMsg, 'error');
          setMessages((prev) => [
            ...prev.filter((m) => m.id !== streamingAssistantId),
            {
              id: `err-${Date.now()}`,
              role: 'assistant',
              content: `⚠️ ${friendlyMsg}`,
              timestamp: new Date().toISOString(),
            }
          ]);
        }
      });
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted.');
      } else {
        console.error('Chat error:', err);
        const isQuota = /quota|resource_exhausted|429/i.test(err.message || '');
        const errorMsg = isQuota
          ? (err.message || "Zara is temporarily unavailable because the Gemini API quota has been exhausted. Please try again after the quota resets.")
          : (err.message || "Zara couldn't reach the AI service. Please check your connection or try again.");
        showToast(errorMsg, 'error');
        setMessages((prev) => [
          ...prev.filter((m) => m.id !== streamingAssistantId),
          {
            id: `err-${Date.now()}`,
            role: 'assistant',
            content: `⚠️ ${errorMsg}`,
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    } finally {
      setIsSending(false);
      abortControllerRef.current = null;
    }
  };

  const regenerateResponse = async (messageId = null) => {
    if (isSending || !currentConversationId) return;

    setIsSending(true);

    // Mark the message as regenerating
    setMessages((prev) =>
      prev.map((m) =>
        (!messageId && m.role === 'assistant') || m.id === messageId
          ? { ...m, isRegenerating: true }
          : m
      )
    );

    try {
      const response = await chatApi.regenerateResponse({
        conversation_id: currentConversationId,
        message_id: messageId,
        language: selectedLanguage,
      });

      const assistantResponse = response.assistant_message?.content || response.response || '';
      console.log("Selected chat language:", selectedLanguage);
      console.log("Assistant response:", assistantResponse);

      setMessages((prev) =>
        prev.map((m) =>
          m.id === response.assistant_message?.id
            ? {
                ...response.assistant_message,
                sources: response.sources || response.assistant_message?.sources,
                is_realtime: response.is_realtime,
                isRegenerating: false,
              }
            : m
        )
      );

      loadConversations();
      showToast('Response regenerated', 'success');

      if (autoVoiceEnabled && assistantResponse) {
        console.log("TTS input text:", assistantResponse);
        console.log("TTS selected language:", selectedLanguage);
        speakText(
          assistantResponse,
          selectedLanguage,
          { messageId: response.assistant_message?.id }
        );
      }
    } catch (err) {
      console.error('Failed to regenerate response:', err);
      showToast(err.message || 'Failed to regenerate response', 'error');
      setMessages((prev) =>
        prev.map((m) => (m.isRegenerating ? { ...m, isRegenerating: false } : m))
      );
    } finally {
      setIsSending(false);
    }
  };

  const regenerateLastResponse = async () => {
    const assistantMsgs = messages.filter((m) => m.role === 'assistant');
    if (assistantMsgs.length === 0) return;
    const lastAssistant = assistantMsgs[assistantMsgs.length - 1];
    await regenerateResponse(lastAssistant.id);
  };

  return (
    <ChatContext.Provider
      value={{
        conversations,
        setConversations,
        currentConversationId,
        setCurrentConversationId,
        messages,
        isSending,
        isTyping,
        setIsTyping,
        memories,
        userSettings,
        updateUserSettings,
        rotoBotState,
        setRotoBotState,
        rotoBotBubble,
        setRotoBotBubble,
        triggerRotoBotReaction,
        toasts,
        showToast,
        createNewChat,
        deleteConversation,
        renameConversation,
        sendMessage,
        stopGenerating,
        regenerateResponse,
        regenerateLastResponse,
        loadMemories,
        loadConversations,
        selectedLanguage,
        setSelectedLanguage,
        autoVoiceEnabled,
        setAutoVoiceEnabled,
        ttsPlayingMessageId,
        speakMessage,
        stopSpeaking,
        pauseSpeaking,
        resumeSpeaking,
        searchingStatus,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}
