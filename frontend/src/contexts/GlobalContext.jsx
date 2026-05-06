import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { message } from 'antd';
import dayjs from 'dayjs';
import { stockApi } from '../services/api';

const GlobalContext = createContext(null);

export const useGlobal = () => {
  const context = useContext(GlobalContext);
  if (!context) {
    throw new Error('useGlobal must be used within GlobalProvider');
  }
  return context;
};

const SETTINGS_KEY = 'stockAppSettings';

const getDefaultSettings = () => ({
  ladder: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  watchlist: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  statistics: { autoRefresh: false, refreshInterval: 30, smartMode: true },
});

const loadAllSettings = () => {
  try {
    const saved = localStorage.getItem(SETTINGS_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return { ...getDefaultSettings(), ...parsed };
    }
  } catch (error) {
    console.error('加载设置失败', error);
  }
  return getDefaultSettings();
};

const saveAllSettings = (settings) => {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch (error) {
    console.error('保存设置失败', error);
  }
};

export const GlobalProvider = ({ children }) => {
  const [currentDate, setCurrentDateState] = useState('');
  const [latestDate, setLatestDate] = useState('');
  const [tradingDays, setTradingDays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  
  const [allSettings, setAllSettings] = useState(() => loadAllSettings());
  const [currentPage, setCurrentPage] = useState('ladder');
  
  const [autoRefresh, setAutoRefreshState] = useState(() => {
    const settings = loadAllSettings();
    return settings.ladder.autoRefresh;
  });
  const [refreshInterval, setRefreshIntervalState] = useState(() => {
    const settings = loadAllSettings();
    return settings.ladder.refreshInterval;
  });
  const [smartMode, setSmartModeState] = useState(() => {
    const settings = loadAllSettings();
    return settings.ladder.smartMode;
  });
  
  const intervalRef = useRef(null);
  const currentDateRef = useRef('');
  
  const setCurrentDate = (date) => {
    setCurrentDateState(date);
    currentDateRef.current = date;
  };

  const loadPageSettings = (page) => {
    const pageSettings = allSettings[page] || getDefaultSettings()[page];
    setAutoRefreshState(pageSettings.autoRefresh);
    setRefreshIntervalState(pageSettings.refreshInterval);
    setSmartModeState(pageSettings.smartMode);
    setCurrentPage(page);
  };

  const setAutoRefresh = (value) => {
    setAutoRefreshState(value);
    setAllSettings(prev => {
      const newSettings = {
        ...prev,
        [currentPage]: {
          ...prev[currentPage],
          autoRefresh: value,
        },
      };
      saveAllSettings(newSettings);
      return newSettings;
    });
  };

  const setRefreshInterval = (value) => {
    setRefreshIntervalState(value);
    setAllSettings(prev => {
      const newSettings = {
        ...prev,
        [currentPage]: {
          ...prev[currentPage],
          refreshInterval: value,
        },
      };
      saveAllSettings(newSettings);
      return newSettings;
    });
  };

  const setSmartMode = (value) => {
    setSmartModeState(value);
    setAllSettings(prev => {
      const newSettings = {
        ...prev,
        [currentPage]: {
          ...prev[currentPage],
          smartMode: value,
        },
      };
      saveAllSettings(newSettings);
      return newSettings;
    });
  };

  const loadTradingDays = async (dateStr) => {
    try {
      const response = await stockApi.getAdjacentTradingDays(dateStr);
      if (response.data.success) {
        const data = response.data.data;
        const allDays = [...(data.prev_days || []), ...(data.next_days || [])];
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
      console.log('初始化加载，今天日期:', today);
      
      const response = await stockApi.getAdjacentTradingDays(today);
      
      if (response.data.success) {
        const data = response.data.data;
        const prevDays = data.prev_days || [];
        const nextDays = data.next_days || [];
        const isTradingDay = data.is_trading_day;
        
        console.log('交易日数据:', {
          isTradingDay,
          prevDays: prevDays.length,
          nextDays: nextDays.length
        });
        
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
        
        console.log('目标日期:', targetDate);
        
        if (targetDate) {
          setCurrentDate(targetDate);
          setLatestDate(targetDate);
          console.log('日期初始化完成:', targetDate);
        } else {
          console.warn('无法确定目标日期');
        }
      } else {
        console.error('获取交易日失败:', response.data.error);
      }
    } catch (error) {
      console.error('加载数据失败:', error);
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
      console.log('等待日期初始化...');
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

  const autoRefreshCallback = useRef(null);

  const setAutoRefreshCallback = (callback) => {
    autoRefreshCallback.current = callback;
  };

  const isInTradingTime = () => {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentTime = hours * 60 + minutes;
    
    const morningStart = 9 * 60 + 15;
    const morningEnd = 11 * 60 + 30;
    const afternoonStart = 13 * 60;
    const afternoonEnd = 15 * 60;
    
    return (currentTime >= morningStart && currentTime <= morningEnd) ||
           (currentTime >= afternoonStart && currentTime <= afternoonEnd);
  };

  useEffect(() => {
    if (autoRefresh && autoRefreshCallback.current && currentDate) {
      const shouldRefresh = smartMode ? isInTradingTime() : true;
      
      if (shouldRefresh) {
        intervalRef.current = setInterval(() => {
          const stillInTime = smartMode ? isInTradingTime() : true;
          if (stillInTime && autoRefreshCallback.current) {
            autoRefreshCallback.current();
          }
        }, refreshInterval * 1000);
      }
    }
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, refreshInterval, smartMode, currentDate]);

  useEffect(() => {
    if (smartMode && autoRefresh && currentDate) {
      const checkInterval = setInterval(() => {
        const inTime = isInTradingTime();
        if (!inTime && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        } else if (inTime && !intervalRef.current && autoRefreshCallback.current) {
          intervalRef.current = setInterval(() => {
            if (isInTradingTime() && autoRefreshCallback.current) {
              autoRefreshCallback.current();
            }
          }, refreshInterval * 1000);
        }
      }, 60000);
      
      return () => clearInterval(checkInterval);
    }
  }, [smartMode, autoRefresh, refreshInterval, currentDate]);

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
    setAutoRefreshCallback,
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
