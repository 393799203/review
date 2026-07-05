export const DEFAULT_SETTINGS = {
  ladder: { 
    autoRefresh: true, 
    refreshInterval: 30, 
    smartMode: true, 
    showFirstBoard: true, 
    mode: 'ladder' 
  },
  watchlist: { 
    autoRefresh: false, 
    refreshInterval: 30, 
    smartMode: true 
  },
  statistics: { 
    autoRefresh: false, 
    refreshInterval: 30, 
    smartMode: true 
  },
  news: { 
    autoRefresh: true, 
    refreshInterval: 30, 
    smartMode: false, 
    showAllNews: true,
    speechEnabled: true,
    speechSettings: {
      voices: {},
      rate: 1.0,
      pitch: 1.0,
      volume: 1.0
    }
  },
  reports: { 
    autoRefresh: false, 
    refreshInterval: 3600, 
    smartMode: false 
  },
  'hot-stocks': {
    autoRefresh: false,
    refreshInterval: 300,
    smartMode: true
  },
  // DeepSeek API Key（用户在设置页自行配置，找对标功能使用）
  deepseek_api_key: '',
  // DeepSeek 模型选择：deepseek-v4-flash（快） / deepseek-v4-pro（强）
  deepseek_model: 'deepseek-v4-flash',
};
