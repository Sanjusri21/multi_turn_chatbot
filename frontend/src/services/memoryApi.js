import { request } from './api';

export const memoryApi = {
  getMemories: async (category = null) => {
    const query = category ? `?category=${encodeURIComponent(category)}` : '';
    return await request(`/memories${query}`);
  },

  createMemory: async ({ key, value, category = 'other' }) => {
    return await request('/memories', {
      method: 'POST',
      body: JSON.stringify({ key, value, category }),
    });
  },

  updateMemory: async (id, { key, value, category }) => {
    return await request(`/memories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ key, value, category }),
    });
  },

  deleteMemory: async (id) => {
    return await request(`/memories/${id}`, {
      method: 'DELETE',
    });
  },

  clearAllMemories: async () => {
    return await request('/memories', {
      method: 'DELETE',
    });
  },
};
