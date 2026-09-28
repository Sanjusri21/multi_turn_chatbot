import { request } from './api';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const chatApi = {
  sendMessage: async ({ message, conversation_id = null, attachment_ids = null, language = null }) => {
    return await request('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, conversation_id, attachment_ids, language }),
    });
  },

  streamMessage: async ({
    message,
    conversation_id = null,
    attachment_ids = null,
    language = null,
    onInit,
    onChunk,
    onDone,
    onError,
    signal,
  }) => {
    const token = localStorage.getItem('token');
    const headers = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${BASE_URL}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message, conversation_id, attachment_ids, language }),
        signal,
      });

      if (!response.ok) {
        let errMsg = 'Failed to stream response.';
        try {
          const errJson = await response.json();
          errMsg = errJson.detail || errMsg;
        } catch {
          errMsg = response.statusText || errMsg;
        }
        throw new Error(errMsg);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split('\n\n');
        buffer = blocks.pop() || '';

        for (const block of blocks) {
          const trimmed = block.trim();
          if (!trimmed.startsWith('data: ')) continue;
          const jsonStr = trimmed.substring(6);
          try {
            const data = JSON.parse(jsonStr);
            if (data.type === 'init' && onInit) {
              onInit(data);
            } else if (data.type === 'chunk' && onChunk) {
              onChunk(data.chunk);
            } else if (data.type === 'done' && onDone) {
              onDone(data);
            } else if (data.type === 'error') {
              if (onError) onError(new Error(data.message || 'Stream interrupted.'));
              return;
            }
          } catch (e) {
            console.warn('SSE parse error:', e, jsonStr);
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        console.log('Stream generation aborted by user.');
        return;
      }
      if (onError) onError(err);
      throw err;
    }
  },

  regenerateResponse: async ({ conversation_id, message_id = null, language = null }) => {
    return await request('/chat/regenerate', {
      method: 'POST',
      body: JSON.stringify({ conversation_id, message_id, language }),
    });
  },

  submitFeedback: async ({ message_id, feedback }) => {
    return await request('/chat/feedback', {
      method: 'POST',
      body: JSON.stringify({ message_id, feedback }),
    });
  },

  getDebugContext: async (conversation_id = null) => {
    const q = conversation_id ? `?conversation_id=${encodeURIComponent(conversation_id)}` : '';
    return await request(`/chat/debug-context${q}`);
  },

  getConversations: async (search = '') => {
    const q = search ? `?q=${encodeURIComponent(search)}` : '';
    return await request(`/conversations${q}`);
  },

  searchConversations: async (query) => {
    return await request(`/conversations/search?q=${encodeURIComponent(query)}`);
  },

  getConversation: async (id) => {
    return await request(`/conversations/${id}`);
  },

  getConversationMessages: async (id) => {
    return await request(`/conversations/${id}/messages`);
  },

  createConversation: async (title = 'New Conversation') => {
    return await request('/conversations', {
      method: 'POST',
      body: JSON.stringify({ title }),
    });
  },

  updateConversation: async (id, title) => {
    return await request(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    });
  },

  deleteConversation: async (id) => {
    return await request(`/conversations/${id}`, {
      method: 'DELETE',
    });
  },
};
