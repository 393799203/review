import React, { createContext, useContext, useState, useEffect } from 'react';
import { message } from 'antd';
import { stockApi } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const DEFAULT_SETTINGS = {
  ladder: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  watchlist: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  statistics: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  news: { autoRefresh: false, refreshInterval: 30, smartMode: false, showAllNews: false },
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [isVip, setIsVip] = useState(false);
  const [userRole, setUserRole] = useState('user');
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);

  const fetchCurrentUser = async () => {
    try {
      const response = await stockApi.getCurrentUser();

      if (response.data.success) {
        const userData = response.data.data;
        setUser(userData);
        setIsVip(userData.isVip || false);
        setUserRole(userData.role || 'user');

        if (userData.settings) {
          setSettings({ ...DEFAULT_SETTINGS, ...userData.settings });
        } else {
          setSettings(DEFAULT_SETTINGS);
        }

        localStorage.setItem('user', JSON.stringify(userData));
        return userData;
      } else {
        if (response.data.code === 'UNAUTHORIZED') {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          setToken(null);
          setUser(null);
          setIsVip(false);
          setUserRole('user');
          setSettings(DEFAULT_SETTINGS);
        }
        return null;
      }
    } catch (error) {
      console.error('获取用户信息失败:', error);
      return null;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('token');

      if (savedToken) {
        const userData = await fetchCurrentUser();
        if (!userData) {
          setLoading(false);
          return;
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username, password) => {
    try {
      const response = await stockApi.login(username, password);

      if (response.data.success) {
        const { token: newToken, user: userData } = response.data.data;

        localStorage.setItem('token', newToken);
        localStorage.setItem('user', JSON.stringify(userData));
        setToken(newToken);
        setUser(userData);

        const currentUserData = await fetchCurrentUser();

        if (currentUserData) {
          message.success('登录成功');
          return true;
        } else {
          message.error('登录成功但获取用户信息失败');
          return false;
        }
      } else {
        message.error(response.data.error || '登录失败');
        return false;
      }
    } catch (error) {
      message.error(error.response?.data?.error || '登录失败');
      return false;
    }
  };

  const register = async (username, email, password, nickname) => {
    try {
      const response = await stockApi.register(username, email, password, nickname);

      if (response.data.success) {
        message.success('注册成功，请登录');
        return true;
      } else {
        message.error(response.data.error || '注册失败');
        return false;
      }
    } catch (error) {
      message.error(error.response?.data?.error || '注册失败');
      return false;
    }
  };

  const logout = () => {
    localStorage.clear();
    setToken(null);
    setUser(null);
    setIsVip(false);
    setUserRole('user');
    setSettings(DEFAULT_SETTINGS);
    message.success('已退出登录');
  };

  const updateSettings = async (newSettings) => {
    try {
      const updatedSettings = { ...settings, ...newSettings };
      setSettings(updatedSettings);

      const response = await stockApi.updateSettings(updatedSettings);

      if (response.data.success) {
        return true;
      } else {
        return false;
      }
    } catch (error) {
      console.error('更新设置失败:', error);
      return false;
    }
  };

  const updateLadderSettings = async (ladderSettings) => {
    const newSettings = {
      ...settings,
      ladder: {
        ...(settings.ladder || DEFAULT_SETTINGS.ladder),
        ...ladderSettings,
      },
    };
    return await updateSettings(newSettings);
  };

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    fetchCurrentUser,
    updateSettings,
    updateLadderSettings,
    settings,
    isAuthenticated: !!user && !!token,
    isVip,
    userRole,
    isAdmin: userRole === 'admin',
    isVipUser: userRole === 'vip' || isVip,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
