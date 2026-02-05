import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle 401 and refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const success = await useAuthStore.getState().refreshAccessToken();
      
      if (success) {
        const token = useAuthStore.getState().token;
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;

// API methods
export const authApi = {
  login: (username: string, password: string) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  getMe: () => api.get('/auth/me'),
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    })
};

export const usersApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    is_blocked?: boolean;
    has_custom_limits?: boolean;
  }) => api.get('/users', { params }),
  
  get: (telegramId: number) => api.get(`/users/${telegramId}`),
  
  update: (telegramId: number, data: { is_blocked?: boolean; settings?: object }) =>
    api.patch(`/users/${telegramId}`, data),
  
  updateLimits: (telegramId: number, limits: object) =>
    api.put(`/users/${telegramId}/limits`, limits),
  
  resetLimits: (telegramId: number) =>
    api.delete(`/users/${telegramId}/limits`),
  
  block: (telegramId: number) =>
    api.post(`/users/${telegramId}/block`),
  
  unblock: (telegramId: number) =>
    api.post(`/users/${telegramId}/unblock`),
  
  getRequests: (telegramId: number, limit?: number) =>
    api.get(`/users/${telegramId}/requests`, { params: { limit } }),
  
  sendMessage: (telegramId: number, message: string) =>
    api.post(`/users/${telegramId}/message`, { message })
};

export const statsApi = {
  dashboard: () => api.get('/stats/dashboard'),
  daily: (startDate?: string, endDate?: string) =>
    api.get('/stats/daily', { params: { start_date: startDate, end_date: endDate } }),
  recent: (limit?: number) => api.get('/stats/recent', { params: { limit } }),
  costs: (days?: number) => api.get('/stats/costs', { params: { days } }),
  // API Usage endpoints
  apiUsage: (dailyBudget?: number, monthlyBudget?: number) =>
    api.get('/stats/api-usage', { params: { daily_budget_usd: dailyBudget, monthly_budget_usd: monthlyBudget } }),
  apiUsageDaily: (targetDate?: string) =>
    api.get('/stats/api-usage/daily', { params: { target_date: targetDate } }),
  apiUsageMonthly: (year?: number, month?: number) =>
    api.get('/stats/api-usage/monthly', { params: { year, month } }),
  apiUsageAlerts: (dailyBudget?: number, monthlyBudget?: number) =>
    api.get('/stats/api-usage/alerts', { params: { daily_budget_usd: dailyBudget, monthly_budget_usd: monthlyBudget } }),
  apiUsageByUser: (userId: number, days?: number) =>
    api.get(`/stats/api-usage/user/${userId}`, { params: { days } })
};

export const settingsApi = {
  getAll: () => api.get('/settings'),
  getLimits: () => api.get('/settings/limits'),
  updateLimits: (limits: object) => api.put('/settings/limits', limits),
  getBot: () => api.get('/settings/bot'),
  updateBot: (settings: object) => api.put('/settings/bot', settings),
  getApi: () => api.get('/settings/api'),
  updateApi: (settings: object) => api.put('/settings/api', settings),
  // API Keys management
  getApiKeysStatus: () => api.get('/settings/api-keys/status'),
  updateApiKeys: (keys: { openai_api_key?: string; qwen_api_key?: string }) => 
    api.put('/settings/api-keys', keys)
};

export const tasksApi = {
  queueStats: () => api.get('/tasks/queue/stats'),
  queue: (statusFilter?: string, limit?: number) =>
    api.get('/tasks/queue', { params: { status_filter: statusFilter, limit } }),
  history: (statusFilter?: string, limit?: number) =>
    api.get('/tasks/history', { params: { status_filter: statusFilter, limit } }),
  cancel: (taskId: number) => api.delete(`/tasks/queue/${taskId}`),
  get: (taskId: number) => api.get(`/tasks/${taskId}`)
};
