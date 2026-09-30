import { request } from './api';

export const adminApi = {
  getUsers: async (status = null) => {
    const endpoint = status ? `/admin/users?status=${encodeURIComponent(status)}` : '/admin/users';
    return await request(endpoint);
  },

  getPendingUsers: async () => {
    return await request('/admin/users/pending');
  },

  approveUser: async (userId) => {
    return await request(`/admin/users/${userId}/approve`, {
      method: 'POST',
    });
  },

  rejectUser: async (userId) => {
    return await request(`/admin/users/${userId}/reject`, {
      method: 'POST',
    });
  },

  suspendUser: async (userId) => {
    return await request(`/admin/users/${userId}/suspend`, {
      method: 'POST',
    });
  },

  restoreUser: async (userId) => {
    return await request(`/admin/users/${userId}/restore`, {
      method: 'POST',
    });
  },
};
