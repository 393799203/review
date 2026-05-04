import React, { createContext, useContext, useState, useEffect } from 'react';
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

export const GlobalProvider = ({ children }) => {
  const [currentDate, setCurrentDate] = useState('');
  const [latestDate, setLatestDate] = useState('');
  const [tradingDays, setTradingDays] = useState([]);
  const [loading, setLoading] = useState(false);

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
      const response = await stockApi.getAdjacentTradingDays(today);
      
      if (response.data.success) {
        const data = response.data.data;
        const prevDays = data.prev_days || [];
        const nextDays = data.next_days || [];
        const allDays = [...prevDays, ...nextDays];
        setTradingDays(allDays);
        
        let targetDate = null;
        
        if (nextDays.length > 0) {
          targetDate = nextDays[nextDays.length - 1];
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
    if (!currentDate) {
      message.error('请先选择日期');
      return;
    }
    
    try {
      setLoading(true);
      
      message.loading({ content: `正在刷新 ${currentDate} 数据...`, key: 'refresh' });
      const refreshRes = await stockApi.refreshData(currentDate);
      
      if (refreshRes.data.success) {
        message.success({ content: refreshRes.data.message, key: 'refresh' });
      } else {
        message.error({ content: '刷新失败：' + refreshRes.data.error, key: 'refresh' });
      }
    } catch (error) {
      message.error({ content: '刷新数据失败：' + error.message, key: 'refresh' });
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
    handleDateChange,
    handlePrevDay,
    handleNextDay,
    refreshCurrentData,
  };

  return (
    <GlobalContext.Provider value={value}>
      {children}
    </GlobalContext.Provider>
  );
};

export default GlobalContext;
