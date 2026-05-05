import axios from 'axios';

const isDev = import.meta.env.DEV;
const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

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
};

export default api;
