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

  addWatchlist: (data) => api.post('/watchlist', data),

  updateAlertPrice: (data) => api.put('/watchlist/alert-price', data),

  batchDeleteWatchlist: (stockCodes) => api.post('/watchlist/batch-delete', { stock_codes: stockCodes }),

  getScreeningDates: () => api.get('/screening/dates'),

  runScreening: (params) => api.post('/screening/run', params, { timeout: 60000 }),

  generateStrategy: (data) => api.post('/strategy-gen/generate', data, { timeout: 120000 }),

  getAutoScreeningConfig: () => api.get('/auto-screening/config'),

  saveAutoScreeningConfig: (data) => api.put('/auto-screening/config', data),

  getAutoScreeningLogs: () => api.get('/auto-screening/logs'),

  runAutoScreeningNow: () => api.post('/auto-screening/run-now', {}, { timeout: 120000 }),

  updateWatchlistPrices: () => api.post('/watchlist/update-prices'),

  buyStock: (data) => api.post('/watchlist/buy', data),

  sellStock: (data) => api.post('/watchlist/sell', data),

  getStockKline: (stockCode, days = 60, endDate = '') => api.get(`/stock/kline/${stockCode}?days=${days}${endDate ? `&end_date=${endDate}` : ''}`),

  getStockIntraday: (stockCode, date = '') => api.get(`/stock/intraday/${stockCode}${date ? `?date=${date}` : ''}`),

  getStockQuote: (stockCode) => api.get(`/stock/quote/${stockCode}`),

  analyzeStock: (stockCode, force = false, date = null, checkOnly = false) => {
    let url = `/stock/analyze/${stockCode}?force=${force}`;
    if (date) {
      url += `&date=${date}`;
    }
    if (checkOnly) {
      url += `&check_only=true`;
    }
    return api.get(url, { timeout: checkOnly ? 5000 : 120000 });
  },

  batchAnalyzeStocks: (stocks) => api.post('/stocks/analyze', { stocks }, { timeout: 120000 }),

  sendStockReport: (stockCode, tradeDate = null) => {
    let url = `/stock/report/${stockCode}`;
    const params = {};
    if (tradeDate) params.date = tradeDate;
    return api.post(url, params, { timeout: 180000 });
  },

  login: (username, password) => api.post('/auth/login', { username, password }),

  guestLogin: () => api.post('/auth/guest'),

  register: (username, email, password, nickname) => api.post('/auth/register', { username, email, password, nickname }),

  getCurrentUser: () => api.get('/auth/me'),

  updateSettings: (settings) => api.put('/auth/settings', { settings }),

  logout: () => api.post('/auth/logout'),

  getHotStocks: (listType = 'normal') => api.get(`/hot-stocks?list_type=${listType}`),

  saveMarketAlerts: (data, tradeDate) => {
    const params = tradeDate ? { trade_date: tradeDate } : {};
    return api.post('/market-alerts/save', data, { params });
  },
  
  getMarketAlertsHistory: (params) => api.get('/market-alerts/history', { params }),

  getKeywordAnalysis: (dateStr) => api.get(`/keyword-analysis/${dateStr}`),

  analyzeKeywords: (data) => api.post('/keyword-analysis', data, { timeout: 120000 }),
};

export default api;
