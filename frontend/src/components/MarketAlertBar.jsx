import { useState, useEffect, useRef, useCallback } from 'react';
import { Modal, List, Tag, Empty } from 'antd';
import { BellOutlined, FireOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useGlobal } from '../contexts/GlobalContext';
import { stockApi } from '../services/api';

const DISPLAY_DURATION = 10000;
const FADE_DURATION = 300;

const MarketAlertBar = () => {
  const { marketAlerts, currentDate } = useGlobal();
  const [alerts, setAlerts] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [displayedAlerts, setDisplayedAlerts] = useState([]);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const autoHideTimerRef = useRef(null);
  const fadeTimerRef = useRef(null);
  const prevAlertsRef = useRef([]);
  const isFirstLoadRef = useRef(true);
  const prevDateRef = useRef('');

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const hideAlertBar = useCallback(() => {
    setIsFadingOut(true);
    fadeTimerRef.current = setTimeout(() => {
      setIsVisible(false);
      setDisplayedAlerts([]);
      setIsFadingOut(false);
    }, FADE_DURATION);
  }, []);

  const showAlertWithAnimation = useCallback((newAlerts) => {
    if (autoHideTimerRef.current) {
      clearTimeout(autoHideTimerRef.current);
    }
    if (fadeTimerRef.current) {
      clearTimeout(fadeTimerRef.current);
    }

    setDisplayedAlerts(newAlerts);
    setIsFadingOut(false);
    setIsVisible(true);

    if (newAlerts && newAlerts.length > 0) {
      const alertsToSave = newAlerts
        .filter(alert => alert.changed || alert.isNew)
        .map(alert => ({
          stock_code: alert.code,
          stock_name: alert.name,
          continuous_days: alert.continuous_days,
          alert_time: alert.time,
          alert_type: alert.alertType,
          status: alert.status
        }));

      if (alertsToSave.length > 0) {
        const today = new Date().toISOString().split('T')[0];
        stockApi.saveMarketAlerts(alertsToSave, today).catch(err => {
          console.error('保存市场动态失败:', err);
        });
      }
    }

    autoHideTimerRef.current = setTimeout(() => {
      hideAlertBar();
    }, DISPLAY_DURATION);
  }, [hideAlertBar]);

  useEffect(() => {
    if (!marketAlerts || marketAlerts.length === 0) return;

    const prevAlerts = prevAlertsRef.current;
    
    if (isFirstLoadRef.current && prevAlerts.length === 0) {
      prevAlertsRef.current = marketAlerts.map(a => ({ ...a, hasShownFirstTime: true }));
      isFirstLoadRef.current = false;
      prevDateRef.current = currentDate;
      return;
    }

    if (currentDate && prevDateRef.current !== currentDate) {
      prevAlertsRef.current = marketAlerts.map(a => ({ ...a, hasShownFirstTime: true }));
      prevDateRef.current = currentDate;
      return;
    }

    const processedAlerts = marketAlerts.map(alert => {
      const prevAlert = prevAlerts.find(p => p.code === alert.code);

      let status = alert.status;
      let changed = false;
      let alertType = null;

      if (prevAlert) {
        if (prevAlert.status === 'close' && alert.status === 'close' && !prevAlert.hasShownFirstTime) {
          status = 'new';
          changed = true;
          alertType = 'limit_up';
        } else if (prevAlert.status === 'close' && alert.status === 'open') {
          status = 'open';
          changed = true;
          alertType = 'break板';
        } else if (prevAlert.status === 'open' && alert.status === 'close') {
          status = 'reclose';
          changed = true;
          alertType = '回封';
        } else if (prevAlert.status === 'close' && alert.status === 'close' && prevAlert.hasShownFirstTime) {
          status = 'still_close';
          changed = false;
        } else if (prevAlert.status === 'open' && alert.status === 'open') {
          status = 'still_open';
          changed = false;
        }
      } else {
        if (alert.status === 'close') {
          status = 'new';
          changed = true;
          alertType = 'limit_up';
        }
      }

      return {
        ...alert,
        status,
        changed,
        alertType,
        isNew: !prevAlert,
        hasShownFirstTime: prevAlert ? true : false
      };
    });

    prevAlertsRef.current = marketAlerts.map(a => ({ ...a, hasShownFirstTime: true }));

    const changedAlerts = processedAlerts.filter(a => a.changed || a.isNew);
    if (changedAlerts.length > 0) {
      setAlerts(prev => {
        const existingCodes = new Set(prev.map(a => `${a.code}_${a.time}`));
        const uniqueNew = changedAlerts.filter(a => !existingCodes.has(`${a.code}_${a.time}`));
        if (uniqueNew.length === 0) return prev;
        return [...uniqueNew, ...prev].slice(0, 100);
      });

      showAlertWithAnimation(changedAlerts.slice(0, 5));
    }
  }, [marketAlerts, showAlertWithAnimation]);

  useEffect(() => {
    return () => {
      if (autoHideTimerRef.current) {
        clearTimeout(autoHideTimerRef.current);
      }
      if (fadeTimerRef.current) {
        clearTimeout(fadeTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (modalVisible) {
      stockApi.getMarketAlertsHistory({ limit: 100 }).then(response => {
        if (response.data.success && response.data.data) {
          const historyData = response.data.data.map(item => ({
            code: item.stock_code,
            name: item.stock_name,
            continuous_days: item.continuous_days,
            time: item.alert_time,
            status: item.status,
            alertType: item.alert_type,
            changed: false
          }));
          if (historyData.length > 0) {
            setAlerts(historyData);
          }
        }
      }).catch(err => console.error('加载历史市场动态失败:', err));
    }
  }, [modalVisible]);

  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    if (timeStr.length === 5) return timeStr;
    if (timeStr.length === 8) return timeStr.substring(0, 5);
    return timeStr;
  };

  const getStatusTag = (status) => {
    switch (status) {
      case 'open':
        return <Tag color="orange">开板</Tag>;
      case 'reclose':
        return <Tag color="green">回封</Tag>;
      case 'close':
      case 'still_close':
        return <Tag color="red">涨停</Tag>;
      case 'still_open':
        return <Tag color="orange">仍开板</Tag>;
      case 'new':
        return <Tag color="blue">首板</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  const getAlertTypeIcon = (alertType) => {
    if (alertType === 'limit_up') {
      return <FireOutlined style={{ color: '#ff4d4f' }} />;
    } else if (alertType === 'break板') {
      return <ThunderboltOutlined style={{ color: '#fa8c16' }} />;
    }
    return <BellOutlined style={{ color: '#fff' }} />;
  };

  return (
    <>
      {isVisible && displayedAlerts.length > 0 && (
        <div
          onClick={() => setModalVisible(true)}
          style={{
            position: 'fixed',
            top: isMobile ? 46 : 64,
            left: isMobile ? 0 : 200,
            right: 0,
            zIndex: 99,
            background: 'linear-gradient(90deg, #1890ff 0%, #096dd9 100%)',
            color: '#fff',
            cursor: 'pointer',
            boxShadow: '0 2px 12px rgba(0, 0, 0, 0.3)',
            opacity: isFadingOut ? 0 : 1,
            transform: isFadingOut ? 'translateY(-10px)' : 'translateY(0)',
            transition: `opacity ${FADE_DURATION}ms ease-out, transform ${FADE_DURATION}ms ease-out`,
          }}
        >
          {displayedAlerts.map((alert) => (
            <div
              key={`${alert.code}_${alert.time}`}
              style={{
                padding: isMobile ? '6px 12px' : '8px 16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: isMobile ? 12 : 14,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                {getAlertTypeIcon(alert.alertType)}
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  <span style={{ fontWeight: 500 }}>{formatTime(alert.time)}</span>
                  {' '}
                  <span>{alert.name}</span>
                  {' '}
                  <span style={{ color: '#ffd700' }}>{alert.continuous_days}连板</span>
                  {' '}
                  {getStatusTag(alert.status)}
                </span>
              </div>
              <span style={{ fontSize: isMobile ? 10 : 12, opacity: 0.8, flexShrink: 0 }}>
                点击查看全部 ({alerts.length})
              </span>
            </div>
          ))}
        </div>
      )}

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>市场动态消息 ({alerts.length})</span>
            <button
              onClick={() => setModalVisible(false)}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                fontSize: 18,
                color: '#999',
                padding: '0 4px',
              }}
            >
              ✕
            </button>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={isMobile ? '95vw' : 600}
        style={{ top: isMobile ? 60 : 80 }}
        styles={{
          body: { maxHeight: isMobile ? '60vh' : '70vh', overflow: 'auto' }
        }}
      >
        {alerts.length === 0 ? (
          <Empty description="暂无市场动态" />
        ) : (
          <List
            dataSource={alerts}
            renderItem={(item, index) => (
              <List.Item
                key={`${item.code}_${item.time}_${index}`}
                style={{
                  padding: '12px 0',
                  borderBottom: '1px solid #f0f0f0',
                  background: item.changed ? '#fffbe6' : 'transparent',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: 12 }}>
                  <span style={{ color: '#999', fontSize: 12, minWidth: 50 }}>
                    {formatTime(item.time)}
                  </span>
                  <span style={{ fontWeight: 500, minWidth: 80 }}>
                    {item.name}
                  </span>
                  <span style={{ color: '#ff4d4f', minWidth: 60 }}>
                    {item.continuous_days}连板
                  </span>
                  {getStatusTag(item.status)}
                </div>
              </List.Item>
            )}
          />
        )}
      </Modal>
    </>
  );
};

export default MarketAlertBar;