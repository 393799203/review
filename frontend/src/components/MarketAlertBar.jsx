import { useState, useEffect, useRef, useCallback } from 'react';
import { Modal, Tag, Empty } from 'antd';
import { BellOutlined, CloseOutlined } from '@ant-design/icons';
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
  const isDateJustChangedRef = useRef(false);
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
        // 使用页面导航选中的日期，而非当天日期
        const tradeDate = currentDate ? currentDate.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3') : null;
        stockApi.saveMarketAlerts(alertsToSave, tradeDate).catch(err => {
          console.error('保存市场动态失败:', err);
        });
      }
    }

    autoHideTimerRef.current = setTimeout(() => {
      hideAlertBar();
    }, DISPLAY_DURATION);
  }, [hideAlertBar, currentDate]);

  useEffect(() => {
    if (!marketAlerts || marketAlerts.length === 0) return;

    const prevAlerts = prevAlertsRef.current;
    
    if (isFirstLoadRef.current) {
      prevAlertsRef.current = marketAlerts.map(a => ({ ...a, hasShownFirstTime: true }));
      isFirstLoadRef.current = false;
      prevDateRef.current = currentDate;
      return;
    }

    // 日期切换：立即清空旧基准与旧提示条。
    // 对比只在同一天内进行，新日期的第一批数据只作为基准线，不触发任何提示。
    if (currentDate && prevDateRef.current !== currentDate) {
      if (autoHideTimerRef.current) clearTimeout(autoHideTimerRef.current);
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current);
      prevAlertsRef.current = [];
      prevDateRef.current = currentDate;
      isDateJustChangedRef.current = true;
      setAlerts([]);
      setIsVisible(false);
      setDisplayedAlerts([]);
      setIsFadingOut(false);
      return;
    }

    // 日期切换后的第一批数据：只同步基准线，不触发对比
    if (isDateJustChangedRef.current) {
      prevAlertsRef.current = marketAlerts.map(a => ({ ...a, hasShownFirstTime: true }));
      isDateJustChangedRef.current = false;
      return;
    }

    const processedAlerts = marketAlerts.map(alert => {
      const prevAlert = prevAlerts.find(p => p.code === alert.code);

      let status = alert.status;
      let changed = false;
      let alertType = null;

      if (prevAlert) {
        if (prevAlert.status === 'close' && alert.status === 'open') {
          status = 'open';
          changed = true;
          alertType = 'break板';
        } else if (prevAlert.status === 'open' && alert.status === 'close') {
          status = 'reclose';
          changed = true;
          alertType = '回封';
        } else if (prevAlert.status === 'close' && alert.status === 'close') {
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
        } else if (alert.status === 'open') {
          status = 'opened';
          changed = true;
          alertType = '开板';
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

      showAlertWithAnimation(changedAlerts);
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
      // 使用页面导航选中的日期查询历史记录
      const tradeDate = currentDate ? currentDate.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3') : undefined;
      stockApi.getMarketAlertsHistory({ limit: 100, trade_date: tradeDate }).then(response => {
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
  }, [modalVisible, currentDate]);

  const formatTime = (timeStr) => {
    if (!timeStr) return '';
    if (timeStr.length === 5) return timeStr;
    if (timeStr.length === 8) return timeStr.substring(0, 5);
    return timeStr;
  };

  const getStatusTag = (status) => {
    switch (status) {
      case 'open':
      case 'opened':
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

  return (
    <>
      {isVisible && displayedAlerts.length > 0 && (
        <div
          style={{
            position: 'fixed',
            top: isMobile ? 46 : 64,
            right: isMobile ? 8 : 16,
            width: isMobile ? 'calc(100% - 16px)' : 380,
            zIndex: 99,
            background: '#fff',
            borderRadius: 10,
            overflow: 'hidden',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.18)',
            border: '1px solid #e6f4ff',
            opacity: isFadingOut ? 0 : 1,
            transform: isFadingOut ? 'translateY(-10px)' : 'translateY(0)',
            transition: `opacity ${FADE_DURATION}ms ease-out, transform ${FADE_DURATION}ms ease-out`,
          }}
        >
          {/* 标题栏：点击打开弹窗 */}
          <div
            onClick={() => setModalVisible(true)}
            style={{
              background: 'linear-gradient(135deg, #1677ff 0%, #0958d9 100%)',
              color: '#fff',
              padding: '9px 14px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600 }}>
              <BellOutlined style={{ fontSize: 14 }} />
              市场动态
              <span
                style={{
                  background: 'rgba(255,255,255,0.25)',
                  borderRadius: 8,
                  padding: '0 7px',
                  fontSize: 11,
                }}
              >
                {alerts.length}
              </span>
            </div>
            <div style={{ fontSize: 12, opacity: 0.92 }}>查看全部 ›</div>
          </div>

          {/* 条目列表 */}
          <div style={{ maxHeight: isMobile ? '42vh' : '60vh', overflowY: 'auto' }}>
            {displayedAlerts.map((alert) => (
              <div
                key={`${alert.code}_${alert.time}`}
                onClick={() => setModalVisible(true)}
                style={{
                  padding: '8px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  borderBottom: '1px solid #f5f5f5',
                  cursor: 'pointer',
                }}
              >
                {/* 时间徽章 */}
                <div
                  style={{
                    minWidth: 46,
                    textAlign: 'center',
                    background: '#f5f5f5',
                    borderRadius: 6,
                    padding: '2px 4px',
                    fontFamily: 'monospace',
                    fontSize: 11,
                    fontWeight: 600,
                    color: '#595959',
                    flexShrink: 0,
                  }}
                >
                  {formatTime(alert.time) || '--:--'}
                </div>
                {/* 名称 + 连板 */}
                <div
                  style={{
                    flex: 1,
                    minWidth: 0,
                    fontSize: 13,
                    color: '#262626',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{alert.name || '-'}</span>{' '}
                  <span style={{ color: '#ff4d4f', fontWeight: 700, fontSize: 12 }}>
                    {alert.continuous_days || 1}连板
                  </span>
                </div>
                {/* 状态标签 */}
                <div style={{ flexShrink: 0 }}>{getStatusTag(alert.status)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Modal
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={isMobile ? '95vw' : 620}
        style={{ top: isMobile ? 50 : 80 }}
        styles={{
          body: { padding: 0, maxHeight: isMobile ? '70vh' : '72vh', overflow: 'auto' },
          content: { borderRadius: 12, overflow: 'hidden' },
        }}
        className="market-alert-modal"
      >
        {/* 头部渐变栏 */}
        <div
          style={{
            background: 'linear-gradient(135deg, #1677ff 0%, #0958d9 100%)',
            color: '#fff',
            padding: '14px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 10,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <BellOutlined style={{ fontSize: 18 }} />
            <span style={{ fontSize: 16, fontWeight: 600 }}>市场动态</span>
            <span
              style={{
                background: 'rgba(255,255,255,0.25)',
                borderRadius: 10,
                padding: '1px 10px',
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {alerts.length} 条
            </span>
          </div>
          <button
            onClick={() => setModalVisible(false)}
            style={{
              background: 'rgba(255,255,255,0.15)',
              border: 'none',
              cursor: 'pointer',
              width: 28,
              height: 28,
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 13,
            }}
          >
            <CloseOutlined />
          </button>
        </div>

        {alerts.length === 0 ? (
          <div style={{ padding: '60px 0' }}>
            <Empty description="暂无市场动态" />
          </div>
        ) : (
          <>
            {/* 状态统计 */}
            <div style={{ display: 'flex', gap: 10, padding: '14px 20px 4px' }}>
              {[
                { label: '涨停', count: alerts.filter(a => ['close', 'still_close', 'new'].includes(a.status)).length, color: '#ff4d4f', bg: '#fff1f0' },
                { label: '开板', count: alerts.filter(a => ['open', 'opened', 'still_open'].includes(a.status)).length, color: '#fa8c16', bg: '#fff7e6' },
                { label: '回封', count: alerts.filter(a => a.status === 'reclose').length, color: '#52c41a', bg: '#f6ffed' },
              ].map((s) => (
                <div
                  key={s.label}
                  style={{
                    flex: 1,
                    background: s.bg,
                    borderRadius: 8,
                    padding: '8px 0',
                    textAlign: 'center',
                  }}
                >
                  <div style={{ fontSize: 20, fontWeight: 700, color: s.color, lineHeight: 1.2 }}>
                    {s.count}
                  </div>
                  <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* 列表 */}
            <div style={{ padding: '12px 20px 20px' }}>
              {alerts.map((item, index) => (
                <div
                  key={`${item.code}_${item.time}_${index}`}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '10px 12px',
                    marginBottom: 8,
                    borderRadius: 8,
                    background: item.changed ? '#fffbe6' : '#fafafa',
                    border: `1px solid ${item.changed ? '#ffe58f' : '#f0f0f0'}`,
                  }}
                >
                  {/* 时间 */}
                  <div
                    style={{
                      minWidth: 52,
                      textAlign: 'center',
                      background: '#fff',
                      border: '1px solid #f0f0f0',
                      borderRadius: 6,
                      padding: '3px 6px',
                      fontFamily: 'monospace',
                      fontSize: 12,
                      fontWeight: 600,
                      color: '#595959',
                      flexShrink: 0,
                    }}
                  >
                    {formatTime(item.time) || '--:--'}
                  </div>
                  {/* 名称 + 代码 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 600, fontSize: 14, color: '#262626' }}>{item.name || '-'}</div>
                    <div style={{ fontSize: 11, color: '#8c8c8c', fontFamily: 'monospace' }}>
                      {item.code || ''}
                    </div>
                  </div>
                  {/* 连板 + 状态 */}
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ color: '#ff4d4f', fontWeight: 700, fontSize: 13 }}>
                      {item.continuous_days || 1}连板
                    </div>
                    <div style={{ marginTop: 2 }}>{getStatusTag(item.status)}</div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </Modal>
    </>
  );
};

export default MarketAlertBar;