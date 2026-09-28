import { request } from './api';

export const authApi = {
  signup: async ({ name, email, password }) => {
    return await request('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    });
  },

  login: async ({ email, password }) => {
    return await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  getMe: async () => {
    return await request('/auth/me');
  },

  logout: async () => {
    return await request('/auth/logout', {
      method: 'POST',
    });
  },

  changePassword: async ({ current_password, new_password }) => {
    return await request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    });
  },

  deleteAccount: async () => {
    return await request('/auth/account', {
      method: 'DELETE',
    });
  },
};
