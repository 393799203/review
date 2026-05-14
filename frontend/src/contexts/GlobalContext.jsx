import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { message } from 'antd';
import dayjs from 'dayjs';
import { stockApi } from '../services/api';
import { useAuth } from './AuthContext';

const GlobalContext = createContext(null);

export const useGlobal = () => {
  const context = useContext(GlobalContext);
  if (!context) {
    throw new Error('useGlobal must be used within GlobalProvider');
  }
  return context;
};

const DEFAULT_SETTINGS = {
  ladder: { autoRefresh: false, refreshInterval: 30, smartMode: true, showFirstBoard: true },
  watchlist: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  statistics: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  news: { autoRefresh: false, refreshInterval: 300, smartMode: true, showAllNews: false },
};

export const GlobalProvider = ({ children }) => {
  const { settings: userSettings, updateSettings } = useAuth();
  const [currentDate, setCurrentDateState] = useState('');
  const [latestDate, setLatestDate] = useState('');
  const [tradingDays, setTradingDays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  const [currentPage, setCurrentPage] = useState('ladder');

  const [autoRefresh, setAutoRefreshState] = useState(
    userSettings?.ladder?.autoRefresh ?? false
  );
  const [refreshInterval, setRefreshIntervalState] = useState(
    userSettings?.ladder?.refreshInterval ?? 30
  );
  const [smartMode, setSmartModeState] = useState(
    userSettings?.ladder?.smartMode ?? true
  );
  const [showFirstBoard, setShowFirstBoardState] = useState(
    userSettings?.ladder?.showFirstBoard ?? true
  );
  const [showAllNews, setShowAllNewsState] = useState(
    userSettings?.news?.showAllNews ?? false
  );

  useEffect(() => {
    if (userSettings && userSettings[currentPage]) {
      setAutoRefreshState(userSettings[currentPage].autoRefresh);
      setRefreshIntervalState(userSettings[currentPage].refreshInterval);
      setSmartModeState(userSettings[currentPage].smartMode);
      if (currentPage === 'ladder') {
        setShowFirstBoardState(userSettings[currentPage].showFirstBoard ?? true);
      }
      if (currentPage === 'news') {
        setShowAllNewsState(userSettings[currentPage].showAllNews ?? false);
      }
    }
  }, [userSettings, currentPage]);

  const currentDateRef = useRef('');

  const setCurrentDate = (date) => {
    setCurrentDateState(date);
    currentDateRef.current = date;
  };

  const loadPageSettings = (page) => {
    setCurrentPage(page);
    if (userSettings && userSettings[page]) {
      setAutoRefreshState(userSettings[page].autoRefresh);
      setRefreshIntervalState(userSettings[page].refreshInterval);
      setSmartModeState(userSettings[page].smartMode);
      if (page === 'ladder') {
        setShowFirstBoardState(userSettings[page].showFirstBoard ?? true);
      }
      if (page === 'news') {
        setShowAllNewsState(userSettings[page].showAllNews ?? false);
      }
    } else {
      const defaultPageSettings = DEFAULT_SETTINGS[page];
      setAutoRefreshState(defaultPageSettings.autoRefresh);
      setRefreshIntervalState(defaultPageSettings.refreshInterval);
      setSmartModeState(defaultPageSettings.smartMode);
      if (page === 'ladder') {
        setShowFirstBoardState(defaultPageSettings.showFirstBoard);
      }
      if (page === 'news') {
        setShowAllNewsState(defaultPageSettings.showAllNews);
      }
    }
  };

  const setAutoRefresh = (value) => {
    setAutoRefreshState(value);
    const newSettings = {
      ...userSettings,
      [currentPage]: {
        ...(userSettings?.[currentPage] || DEFAULT_SETTINGS[currentPage]),
        autoRefresh: value,
      },
    };
    updateSettings(newSettings);
  };

  const setRefreshInterval = (value) => {
    setRefreshIntervalState(value);
    const newSettings = {
      ...userSettings,
      [currentPage]: {
        ...(userSettings?.[currentPage] || DEFAULT_SETTINGS[currentPage]),
        refreshInterval: value,
      },
    };
    updateSettings(newSettings);
  };

  const setSmartMode = (value) => {
    setSmartModeState(value);
    const newSettings = {
      ...userSettings,
      [currentPage]: {
        ...(userSettings?.[currentPage] || DEFAULT_SETTINGS[currentPage]),
        smartMode: value,
      },
    };
    updateSettings(newSettings);
  };

  const setShowFirstBoard = (value) => {
    setShowFirstBoardState(value);
    const newSettings = {
      ...userSettings,
      ladder: {
        ...(userSettings?.ladder || DEFAULT_SETTINGS.ladder),
        showFirstBoard: value,
      },
    };
    updateSettings(newSettings);
  };

  const setShowAllNews = (value) => {
    setShowAllNewsState(value);
    const newSettings = {
      ...userSettings,
      news: {
        ...(userSettings?.news || DEFAULT_SETTINGS.news),
        showAllNews: value,
      },
    };
    updateSettings(newSettings);
  };

  const loadTradingDays = async (dateStr) => {
    try {
      const response = await stockApi.getAdjacentTradingDays(dateStr);
      if (response.data.success) {
        const data = response.data.data;
        const prevDays = data.prev_days || [];
        const nextDays = data.next_days || [];
        const isTradingDay = data.is_trading_day;
        
        let allDays;
        if (isTradingDay) {
          allDays = [...prevDays, dateStr, ...nextDays];
        } else {
          allDays = [...prevDays, ...nextDays];
        }
        
        setTradingDays(allDays);
      }
    } catch (error) {
      console.error('获取交易日失败', error);
    }
  };

  const initLoad = async () => {
    try {
      setLoading(true);
      
      const today = dayjs().format('YYYYMMDD');
      
      const response = await stockApi.getAdjacentTradingDays(today);
      
      if (response.data.success) {
        const data = response.data.data;
        const prevDays = data.prev_days || [];
        const nextDays = data.next_days || [];
        const isTradingDay = data.is_trading_day;
        
        let allDays;
        if (isTradingDay) {
          allDays = [...prevDays, today, ...nextDays];
        } else {
          allDays = [...prevDays, ...nextDays];
        }
        setTradingDays(allDays);
        
        let targetDate = null;
        
        if (isTradingDay) {
          targetDate = today;
        } else if (prevDays.length > 0) {
          targetDate = prevDays[prevDays.length - 1];
        }
        
        if (targetDate) {
          setCurrentDate(targetDate);
          setLatestDate(targetDate);
        }
      }
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDateChange = (date) => {
    if (date) {
      const dateStr = date.format('YYYYMMDD');
      setCurrentDate(dateStr);
      loadTradingDays(dateStr);
    }
  };

  const handlePrevDay = async () => {
    if (!currentDate) return;
    
    try {
      const response = await stockApi.getAdjacentTradingDays(currentDate);
      
      if (response.data.success && response.data.data.prev) {
        const prevDate = response.data.data.prev;
        setCurrentDate(prevDate);
        loadTradingDays(prevDate);
      }
    } catch (error) {
      message.error('获取前一交易日失败');
    }
  };

  const handleNextDay = async () => {
    if (!currentDate) return;
    
    try {
      const response = await stockApi.getAdjacentTradingDays(currentDate);
      
      if (response.data.success && response.data.data.next) {
        const nextDate = response.data.data.next;
        setCurrentDate(nextDate);
        loadTradingDays(nextDate);
      }
    } catch (error) {
      message.error('获取后一交易日失败');
    }
  };

  const refreshCurrentData = async () => {
    const date = currentDateRef.current;
    if (!date) {
      return;
    }
    
    try {
      setLoading(true);
      
      message.loading({ content: `正在刷新 ${date} 数据...`, key: 'refresh' });
      const refreshRes = await stockApi.refreshData(date);
      
      if (refreshRes.data.success) {
        message.success({ content: refreshRes.data.message, key: 'refresh' });
        setRefreshKey(prev => prev + 1);
      } else {
        message.error({ content: '刷新失败：' + refreshRes.data.error, key: 'refresh' });
      }
    } catch (error) {
      message.error({ content: '刷新数据失败：' + error.message, key: 'refresh' });
    } finally {
      setLoading(false);
    }
  };

  const refreshWatchlistPrices = async () => {
    try {
      setLoading(true);
      
      message.loading({ content: '正在刷新自选股列表...', key: 'refresh' });
      const response = await stockApi.getWatchlist();
      
      if (response.data.success) {
        message.success({ content: `刷新成功，已更新 ${response.data.data?.length || 0} 只股票价格`, key: 'refresh' });
      } else {
        message.error({ content: '刷新失败：' + response.data.error, key: 'refresh' });
      }
    } catch (error) {
      message.error({ content: '刷新失败：' + error.message, key: 'refresh' });
    } finally {
      setLoading(false);
    }
  };

  const refreshStatistics = async () => {
    try {
      setLoading(true);
      
      message.loading({ content: '正在刷新统计数据...', key: 'refresh' });
      setRefreshKey(prev => prev + 1);
      message.success({ content: '统计数据已刷新', key: 'refresh' });
    } catch (error) {
      message.error({ content: '刷新失败：' + error.message, key: 'refresh' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    initLoad();
  }, []);

  useEffect(() => {
    if (currentDate) {
      loadTradingDays(currentDate);
    }
  }, [currentDate]);

  const value = {
    currentDate,
    latestDate,
    tradingDays,
    loading,
    setLoading,
    refreshKey,
    autoRefresh,
    setAutoRefresh,
    refreshInterval,
    setRefreshInterval,
    smartMode,
    setSmartMode,
    showFirstBoard,
    setShowFirstBoard,
    showAllNews,
    setShowAllNews,
    settings: userSettings,
    updateSettings,
    loadPageSettings,
    handleDateChange,
    handlePrevDay,
    handleNextDay,
    refreshCurrentData,
    refreshWatchlistPrices,
    refreshStatistics,
  };

  return (
    <GlobalContext.Provider value={value}>
      {children}
    </GlobalContext.Provider>
  );
};

export default GlobalContext;
