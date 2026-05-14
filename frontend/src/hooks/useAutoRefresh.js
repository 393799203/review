import { useEffect, useRef } from 'react';
import dayjs from 'dayjs';

export const useAutoRefresh = ({
  autoRefresh,
  refreshInterval,
  smartMode,
  currentPage,
  tradingDays,
  callback,
}) => {
  const intervalRef = useRef(null);

  const isInTradingTime = () => {
    const now = new Date();
    const today = dayjs().format('YYYYMMDD');
    
    if (!tradingDays.includes(today)) {
      return false;
    }
    
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
    if (autoRefresh && callback) {
      const shouldRefresh = smartMode ? isInTradingTime() : true;
      
      if (shouldRefresh) {
        intervalRef.current = setInterval(() => {
          const stillInTime = smartMode ? isInTradingTime() : true;
          if (stillInTime && callback) {
            callback();
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
  }, [autoRefresh, refreshInterval, smartMode, currentPage, callback, tradingDays]);

  useEffect(() => {
    if (smartMode && autoRefresh) {
      const checkInterval = setInterval(() => {
        const inTime = isInTradingTime();
        if (!inTime && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        } else if (inTime && !intervalRef.current && callback) {
          intervalRef.current = setInterval(() => {
            if (isInTradingTime() && callback) {
              callback();
            }
          }, refreshInterval * 1000);
        }
      }, 60000);
      
      return () => clearInterval(checkInterval);
    }
  }, [smartMode, autoRefresh, refreshInterval, currentPage, callback, tradingDays]);
};
