// lib/store/auth.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  fullName: string;
  username: string;
  email: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  signin: (emailOrUsername: string, password: string) => Promise<boolean>;
  signup: (fullName: string, username: string, email: string, password: string) => Promise<boolean>;
  signout: () => Promise<void>;
  loadUser: () => Promise<void>;
  clearError: () => void;
  setError: (error: string | null) => void;
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      signin: async (emailOrUsername: string, password: string) => {
        set({ isLoading: true, error: null });
        
        try {
          const API_BASE_URL = '/api';
          
          const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              email_or_username: emailOrUsername,
              password,
            }),
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.detail || 'Signin failed');
          }

          if (data.status !== 'ok') {
            throw new Error('Signin failed');
          }

          if (data.user) {
            set({
              user: {
                id: data.user.id,
                fullName: data.user.full_name,
                username: data.user.username,
                email: data.user.email,
              },
              token: null,
              isLoading: false,
              error: null,
            });
          } else {
            // Fallback to /me endpoint
            const meResponse = await fetch(`${API_BASE_URL}/users/me`, {
              credentials: 'include',
            });
            const meData = await meResponse.json();

            if (!meResponse.ok) {
              throw new Error(meData.detail || 'Failed to load user');
            }

            set({
              user: {
                id: meData.id,
                fullName: meData.full_name,
                username: meData.username,
                email: meData.email,
              },
              token: null,
              isLoading: false,
              error: null,
            });
          }

          return true;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Signin failed';
          set({ 
            isLoading: false, 
            error: errorMessage,
            user: null,
            token: null
          });
          return false;
        }
      },

      signup: async (fullName: string, username: string, email: string, password: string) => {
        set({ isLoading: true, error: null });
        
        try {
          const API_BASE_URL = '/api';

          const response = await fetch(`${API_BASE_URL}/auth/signup`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              full_name: fullName,
              username,
              email,
              password,
            }),
          });

          const data = await response.json();

          if (!response.ok) {
            const detail = Array.isArray(data.detail)
              ? data.detail.map((item: { msg: string }) => item.msg).join(', ')
              : data.detail;
            throw new Error(detail || 'Signup failed');
          }

          if (data.status !== 'ok') {
            throw new Error('Signup failed');
          }

          if (data.user) {
            set({
              user: {
                id: data.user.id,
                fullName: data.user.full_name,
                username: data.user.username,
                email: data.user.email,
              },
              token: null,
              isLoading: false,
              error: null,
            });
          } else {
            // Fallback to /me endpoint
            const meResponse = await fetch(`${API_BASE_URL}/users/me`, {
              credentials: 'include',
            });
            const meData = await meResponse.json();

            if (!meResponse.ok) {
              throw new Error(meData.detail || 'Failed to load user');
            }

            set({
              user: {
                id: meData.id,
                fullName: meData.full_name,
                username: meData.username,
                email: meData.email,
              },
              token: null,
              isLoading: false,
              error: null,
            });
          }

          return true;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Signup failed';
          set({ 
            isLoading: false, 
            error: errorMessage,
            user: null,
            token: null
          });
          return false;
        }
      },

      signout: async () => {
        set({
          user: null,
          token: null,
          error: null,
        });
        const API_BASE_URL = '/api';
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          credentials: 'include',
        }).catch(console.error);
      },

      loadUser: async () => {
        try {
          const API_BASE_URL = '/api';
          const response = await fetch(`${API_BASE_URL}/users/me`, {
            credentials: 'include',
          });

          if (!response.ok) {
            set({ user: null, token: null });
            return;
          }

          const data = await response.json();

          set({
            user: {
              id: data.id,
              fullName: data.full_name,
              username: data.username,
              email: data.email,
            },
            token: null,
          });
        } catch (error) {
          set({ user: null, token: null });
        }
      },

      clearError: () => set({ error: null }),
      setError: (error: string | null) => set({ error }),
      
      setUser: (user: User) => set({ user }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user,
        token: state.token 
      }),
    }
  )
);

export const useIsAuthenticated = () => {
  return useAuthStore((state) => !!state.user);
};

export const useCurrentUser = () => {
  return useAuthStore((state) => state.user);
};