import { request } from './api';

export const fileApi = {
  uploadFile: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return await request('/files/upload', {
      method: 'POST',
      body: formData,
    });
  },
};
