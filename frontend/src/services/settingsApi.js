import { request } from './api';

export const settingsApi = {
  getSettings: async () => {
    return await request('/settings');
  },

  updateSettings: async (data) => {
    return await request('/settings', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },
};
