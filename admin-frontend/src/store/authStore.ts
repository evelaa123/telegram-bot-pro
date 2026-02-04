import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';

interface Admin {
  id: number;
  username: string;
  role: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  admin: Admin | null;
  isAuthenticated: boolean;
  
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<boolean>;
  fetchCurrentAdmin: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      admin: null,
      isAuthenticated: false,
      
      login: async (username: string, password: string) => {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await api.post('/auth/login', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        
        const { access_token, refresh_token } = response.data;
        
        set({
          token: access_token,
          refreshToken: refresh_token,
          isAuthenticated: true
        });
        
        // Fetch admin info
        await get().fetchCurrentAdmin();
      },
      
      logout: () => {
        set({
          token: null,
          refreshToken: null,
          admin: null,
          isAuthenticated: false
        });
      },
      
      refreshAccessToken: async () => {
        const { refreshToken } = get();
        
        if (!refreshToken) {
          get().logout();
          return false;
        }
        
        try {
          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken
          });
          
          const { access_token, refresh_token } = response.data;
          
          set({
            token: access_token,
            refreshToken: refresh_token
          });
          
          return true;
        } catch {
          get().logout();
          return false;
        }
      },
      
      fetchCurrentAdmin: async () => {
        try {
          const response = await api.get('/auth/me');
          set({ admin: response.data });
        } catch {
          // Ignore errors
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        admin: state.admin,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
);
