import {create} from 'zustand';
import {persist, createJSONStorage} from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import {stockApi} from '../services/api';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isAuthenticated: false,

      login: async (username, password) => {
        try {
          const response = await stockApi.login(username, password);
          if (response.data.success) {
            const {token, user} = response.data;
            set({
              token,
              user,
              isAuthenticated: true,
            });
            return {success: true};
          } else {
            return {
              success: false,
              error: response.data.error || '登录失败',
            };
          }
        } catch (error) {
          return {
            success: false,
            error: error.response?.data?.error || error.message || '登录失败',
          };
        }
      },

      register: async (username, email, password, nickname) => {
        try {
          const response = await stockApi.register(
            username,
            email,
            password,
            nickname,
          );
          if (response.data.success) {
            return {success: true};
          } else {
            return {
              success: false,
              error: response.data.error || '注册失败',
            };
          }
        } catch (error) {
          return {
            success: false,
            error: error.response?.data?.error || error.message || '注册失败',
          };
        }
      },

      logout: async () => {
        try {
          await stockApi.logout();
        } catch (error) {
          console.error('登出失败:', error);
        } finally {
          set({
            token: null,
            user: null,
            isAuthenticated: false,
          });
        }
      },

      getCurrentUser: async () => {
        try {
          const response = await stockApi.getCurrentUser();
          if (response.data.success) {
            set({user: response.data.user});
            return {success: true};
          }
          return {success: false};
        } catch (error) {
          return {success: false};
        }
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => AsyncStorage),
    },
  ),
);
