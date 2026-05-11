import axios from 'axios';

const isDev = import.meta.env.DEV;
const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');

    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }

    if (user) {
      try {
        const userData = JSON.parse(user);
        if (userData.uid) {
          config.headers['X-User-Uid'] = userData.uid;
        }
      } catch (e) {
        console.error('解析用户数据失败:', e);
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const stockApi = {
  getLatestDate: () => api.get('/latest'),

  getDataByDate: (dateStr) => api.get(`/data/${dateStr}`),

  getAdjacentTradingDays: (dateStr) => api.get(`/adjacent-trading-days/${dateStr}`),

  getLadderByDate: (dateStr) => api.get(`/ladder/${dateStr}`),

  getStatistics: (dateStr) => api.get(`/statistics/${dateStr}`),

  getAvailableDates: () => api.get('/dates'),

  healthCheck: () => api.get('/health'),

  refreshData: (dateStr) => api.post('/refresh', { date: dateStr }, { timeout: 60000 }),

  getWatchlist: () => api.get('/watchlist'),

  updateWatchlistPrices: () => api.post('/watchlist/update-prices'),

  buyStock: (data) => api.post('/watchlist/buy', data),

  sellStock: (data) => api.post('/watchlist/sell', data),

  getStockKline: (stockCode, days = 60) => api.get(`/stock/kline/${stockCode}?days=${days}`),

  getStockIntraday: (stockCode) => api.get(`/stock/intraday/${stockCode}`),

  analyzeStock: (stockCode, force = false) => api.get(`/stock/analyze/${stockCode}?force=${force}`, { timeout: 120000 }),

  batchAnalyzeStocks: (stocks) => api.post('/stocks/analyze', { stocks }, { timeout: 120000 }),

  login: (username, password) => api.post('/auth/login', { username, password }),

  register: (username, email, password, nickname) => api.post('/auth/register', { username, email, password, nickname }),

  getCurrentUser: () => api.get('/auth/me'),

  updateSettings: (settings) => api.put('/auth/settings', { settings }),

  logout: () => api.post('/auth/logout'),
};

export default api;
