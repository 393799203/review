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
};
